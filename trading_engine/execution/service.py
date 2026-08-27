"""Application service coordinating risk, broker, orders, and portfolio."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from ..clock import Clock, SystemClock
from ..errors import BrokerError, OrderStateError, ValidationError
from ..domain.fills import Fill
from ..domain.identifiers import OrderId, TradeId
from ..domain.money import Money
from ..domain.orders import Order, OrderRequest, OrderStatus
from ..domain.portfolio import Portfolio
from ..market.models import Quote
from ..risk.engine import RiskEngine
from .broker import BrokerGateway, BrokerOrder, BrokerOrderState
from .repository import OrderRepository


_BROKER_TO_ORDER = {
    BrokerOrderState.ACCEPTED: OrderStatus.ACCEPTED,
    BrokerOrderState.PARTIALLY_FILLED: OrderStatus.PARTIALLY_FILLED,
    BrokerOrderState.FILLED: OrderStatus.FILLED,
    BrokerOrderState.CANCELLED: OrderStatus.CANCELLED,
    BrokerOrderState.REJECTED: OrderStatus.REJECTED,
}


class ExecutionService:
    def __init__(
        self,
        broker: BrokerGateway,
        repository: OrderRepository,
        portfolio: Portfolio,
        risk_engine: RiskEngine,
        *,
        clock: Optional[Clock] = None,
    ) -> None:
        if not isinstance(broker, BrokerGateway):
            raise ValidationError("broker must implement BrokerGateway")
        if not isinstance(repository, OrderRepository):
            raise ValidationError("repository must be OrderRepository")
        if not isinstance(portfolio, Portfolio):
            raise ValidationError("portfolio must be Portfolio")
        if not isinstance(risk_engine, RiskEngine):
            raise ValidationError("risk_engine must be RiskEngine")
        self.broker = broker
        self.repository = repository
        self.portfolio = portfolio
        self.risk_engine = risk_engine
        self.clock = clock or SystemClock()

    def submit(self, request: OrderRequest, quote: Quote) -> Order:
        if request.account_id != self.portfolio.account_id:
            raise ValidationError("order account does not match portfolio")
        now = self.clock.now()
        self.risk_engine.require_allowed(
            request,
            self.portfolio.snapshot(),
            quote,
            now,
            open_order_count=len(self.repository.open_orders()),
        )
        order = Order(OrderId.new(), request, OrderStatus.PENDING, now, now)
        self.repository.add(order)
        try:
            response = self.broker.submit(order.order_id, request)
        except Exception as exc:
            failed = order.transition(OrderStatus.REJECTED, self.clock.now(), message=str(exc))
            self.repository.save(failed)
            if isinstance(exc, BrokerError):
                raise
            raise BrokerError("broker submission failed", details={"reason": str(exc)})
        return self._synchronize(order, response)

    def refresh(self, order_id: OrderId) -> Order:
        order = self.repository.get(order_id)
        if not order.broker_order_id:
            return order
        response = self.broker.get(order.broker_order_id)
        return self._synchronize(order, response)

    def cancel(self, order_id: OrderId) -> Order:
        order = self.repository.get(order_id)
        if not order.broker_order_id:
            raise OrderStateError("order has not been accepted by a broker")
        response = self.broker.cancel(order.broker_order_id)
        return self._synchronize(order, response)

    def _synchronize(self, order: Order, response: BrokerOrder) -> Order:
        current = order
        if current.status is OrderStatus.PENDING:
            accepted_at = (
                response.fills[0].executed_at
                if response.fills
                else response.updated_at
            )
            current = current.transition(
                OrderStatus.ACCEPTED,
                accepted_at,
                broker_order_id=response.broker_order_id,
            )
        known_quantity = current.filled_quantity
        cumulative = 0
        for broker_fill in response.fills:
            cumulative += broker_fill.quantity
            if cumulative <= known_quantity:
                continue
            new_quantity = cumulative - max(known_quantity, cumulative - broker_fill.quantity)
            fill = Fill(
                trade_id=TradeId.new(),
                order_id=current.order_id,
                instrument=current.request.instrument,
                side=current.request.side,
                quantity=new_quantity,
                price=broker_fill.price,
                executed_at=broker_fill.executed_at,
                commission=Money(
                    broker_fill.commission,
                    current.request.instrument.contract.price_currency,
                ),
                venue_trade_id=broker_fill.venue_trade_id,
            )
            current = current.apply_fill(new_quantity, broker_fill.price, broker_fill.executed_at)
            self.portfolio.apply_fill(fill)
            known_quantity = current.filled_quantity
        target = _BROKER_TO_ORDER[response.state]
        if target != current.status:
            if target in {OrderStatus.CANCELLED, OrderStatus.REJECTED}:
                current = current.transition(
                    target,
                    response.updated_at,
                    broker_order_id=response.broker_order_id,
                    message=response.message,
                )
            elif target is not OrderStatus.FILLED and current.status is not OrderStatus.PARTIALLY_FILLED:
                current = current.transition(
                    target,
                    response.updated_at,
                    broker_order_id=response.broker_order_id,
                    message=response.message,
                )
        self.repository.save(current)
        return current
