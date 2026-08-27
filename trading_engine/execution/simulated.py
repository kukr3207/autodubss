"""In-memory broker used for paper trading and historical simulation."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from threading import RLock
from typing import Dict, Optional, Tuple

from ..clock import Clock, SystemClock
from ..errors import BrokerError, DuplicateRequestError, ValidationError
from ..validation import clean_text
from ..domain.identifiers import OrderId
from ..domain.orders import OrderRequest, OrderType, Side, TimeInForce
from ..market.models import Quote
from .broker import BrokerFill, BrokerGateway, BrokerOrder, BrokerOrderState
from .commission import CommissionModel, NoCommission
from .slippage import NoSlippage, SlippageModel


class SimulatedBroker(BrokerGateway):
    name = "simulated"

    def __init__(
        self,
        *,
        clock: Optional[Clock] = None,
        commission: Optional[CommissionModel] = None,
        slippage: Optional[SlippageModel] = None,
    ) -> None:
        self.clock = clock or SystemClock()
        self.commission = commission or NoCommission()
        self.slippage = slippage or NoSlippage()
        self._quotes: Dict[str, Quote] = {}
        self._orders: Dict[str, BrokerOrder] = {}
        self._requests: Dict[str, OrderRequest] = {}
        self._client_orders: Dict[str, str] = {}
        self._next_order = 1
        self._next_trade = 1
        self._lock = RLock()

    def update_quote(self, quote: Quote) -> None:
        if not isinstance(quote, Quote):
            raise ValidationError("quote must be a Quote")
        with self._lock:
            previous = self._quotes.get(quote.instrument.key)
            if previous is not None and quote.observed_at < previous.observed_at:
                raise BrokerError("simulated quotes must be chronological")
            self._quotes[quote.instrument.key] = quote
            self._match_instrument(quote.instrument.key)

    def submit(self, order_id: OrderId, request: OrderRequest) -> BrokerOrder:
        if not isinstance(order_id, OrderId):
            raise ValidationError("order_id must be an OrderId")
        if not isinstance(request, OrderRequest):
            raise ValidationError("request must be an OrderRequest")
        client_key = str(request.client_order_id)
        with self._lock:
            if client_key in self._client_orders:
                raise DuplicateRequestError(
                    "client order id has already been submitted",
                    details={"clientOrderId": client_key},
                )
            broker_id = "sim-%08d" % self._next_order
            self._next_order += 1
            order = BrokerOrder(
                broker_order_id=broker_id,
                state=BrokerOrderState.ACCEPTED,
                updated_at=self.clock.now(),
            )
            self._orders[broker_id] = order
            self._requests[broker_id] = request
            self._client_orders[client_key] = broker_id
            matched = self._try_match(broker_id)
            if request.time_in_force in {TimeInForce.IOC, TimeInForce.FOK} and matched.state is BrokerOrderState.ACCEPTED:
                matched = replace(
                    matched,
                    state=BrokerOrderState.CANCELLED,
                    updated_at=self.clock.now(),
                    message="immediate order had no executable liquidity",
                )
                self._orders[broker_id] = matched
            return matched

    def _is_executable(self, request: OrderRequest, quote: Quote) -> bool:
        if request.order_type is OrderType.MARKET:
            return True
        if request.order_type is OrderType.LIMIT:
            if request.side is Side.BUY:
                return quote.ask <= request.limit_price
            return quote.bid >= request.limit_price
        if request.order_type is OrderType.STOP:
            if request.side is Side.BUY:
                return quote.ask >= request.stop_price
            return quote.bid <= request.stop_price
        stop_triggered = (
            quote.ask >= request.stop_price
            if request.side is Side.BUY
            else quote.bid <= request.stop_price
        )
        limit_executable = (
            quote.ask <= request.limit_price
            if request.side is Side.BUY
            else quote.bid >= request.limit_price
        )
        return stop_triggered and limit_executable

    def _try_match(self, broker_order_id: str) -> BrokerOrder:
        order = self._orders[broker_order_id]
        if order.state not in {
            BrokerOrderState.ACCEPTED,
            BrokerOrderState.PARTIALLY_FILLED,
        }:
            return order
        request = self._requests[broker_order_id]
        quote = self._quotes.get(request.instrument.key)
        if quote is None or not self._is_executable(request, quote):
            return order
        available = quote.ask_size if request.side is Side.BUY else quote.bid_size
        if available <= 0:
            return order
        remaining = request.quantity - order.filled_quantity
        fill_quantity = min(remaining, available)
        if request.time_in_force is TimeInForce.FOK and fill_quantity < remaining:
            return order
        price = self.slippage.execution_price(request, quote, fill_quantity)
        commission = self.commission.calculate(request, price, fill_quantity)
        fill = BrokerFill(
            quantity=fill_quantity,
            price=price,
            executed_at=self.clock.now(),
            venue_trade_id="sim-trade-%08d" % self._next_trade,
            commission=commission,
        )
        self._next_trade += 1
        state = (
            BrokerOrderState.FILLED
            if fill_quantity == remaining
            else BrokerOrderState.PARTIALLY_FILLED
        )
        updated = replace(
            order,
            state=state,
            updated_at=self.clock.now(),
            fills=order.fills + (fill,),
        )
        self._orders[broker_order_id] = updated
        return updated

    def _match_instrument(self, instrument_key: str) -> None:
        for broker_id, request in tuple(self._requests.items()):
            if request.instrument.key == instrument_key:
                self._try_match(broker_id)

    def cancel(self, broker_order_id: str) -> BrokerOrder:
        key = clean_text(broker_order_id, "broker_order_id")
        with self._lock:
            order = self.get(key)
            if order.state not in {BrokerOrderState.ACCEPTED, BrokerOrderState.PARTIALLY_FILLED}:
                raise BrokerError("only open orders can be cancelled")
            updated = replace(order, state=BrokerOrderState.CANCELLED, updated_at=self.clock.now())
            self._orders[key] = updated
            return updated

    def get(self, broker_order_id: str) -> BrokerOrder:
        key = clean_text(broker_order_id, "broker_order_id")
        with self._lock:
            try:
                return self._orders[key]
            except KeyError:
                raise KeyError("unknown broker order %s" % key)

    def list_open(self) -> Tuple[BrokerOrder, ...]:
        with self._lock:
            return tuple(
                order
                for _, order in sorted(self._orders.items())
                if order.state in {BrokerOrderState.ACCEPTED, BrokerOrderState.PARTIALLY_FILLED}
            )
