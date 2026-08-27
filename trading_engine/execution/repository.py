"""Thread-safe order repository with client-id idempotency."""

from __future__ import annotations

from threading import RLock
from typing import Dict, Iterable, Optional, Tuple

from ..errors import DuplicateRequestError, ValidationError
from ..domain.identifiers import ClientOrderId, OrderId
from ..domain.orders import Order, OrderStatus


class OrderRepository:
    def __init__(self) -> None:
        self._orders: Dict[str, Order] = {}
        self._by_client: Dict[str, str] = {}
        self._lock = RLock()

    def add(self, order: Order) -> Order:
        if not isinstance(order, Order):
            raise ValidationError("order must be an Order")
        order_key = str(order.order_id)
        client_key = str(order.request.client_order_id)
        with self._lock:
            if order_key in self._orders:
                raise DuplicateRequestError("order id already exists")
            if client_key in self._by_client:
                raise DuplicateRequestError("client order id already exists")
            self._orders[order_key] = order
            self._by_client[client_key] = order_key
            return order

    def save(self, order: Order) -> Order:
        if not isinstance(order, Order):
            raise ValidationError("order must be an Order")
        key = str(order.order_id)
        with self._lock:
            current = self._orders.get(key)
            if current is None:
                raise KeyError("unknown order %s" % key)
            if current.request.client_order_id != order.request.client_order_id:
                raise ValidationError("client order id cannot change")
            if order.updated_at < current.updated_at:
                raise ValidationError("cannot save an older order version")
            self._orders[key] = order
            return order

    def get(self, order_id: OrderId) -> Order:
        if not isinstance(order_id, OrderId):
            raise ValidationError("order_id must be an OrderId")
        with self._lock:
            try:
                return self._orders[str(order_id)]
            except KeyError:
                raise KeyError("unknown order %s" % order_id)

    def get_by_client(self, client_order_id: ClientOrderId) -> Order:
        if not isinstance(client_order_id, ClientOrderId):
            raise ValidationError("client_order_id must be a ClientOrderId")
        with self._lock:
            try:
                key = self._by_client[str(client_order_id)]
                return self._orders[key]
            except KeyError:
                raise KeyError("unknown client order %s" % client_order_id)

    def list(
        self,
        *,
        statuses: Optional[Iterable[OrderStatus]] = None,
        instrument_key: Optional[str] = None,
    ) -> Tuple[Order, ...]:
        accepted = None if statuses is None else set(statuses)
        with self._lock:
            result = [
                order
                for order in self._orders.values()
                if (accepted is None or order.status in accepted)
                and (instrument_key is None or order.request.instrument.key == instrument_key)
            ]
        return tuple(sorted(result, key=lambda item: (item.created_at, str(item.order_id))))

    def open_orders(self) -> Tuple[Order, ...]:
        return self.list(
            statuses={
                OrderStatus.PENDING,
                OrderStatus.ACCEPTED,
                OrderStatus.PARTIALLY_FILLED,
            }
        )

    def count(self) -> int:
        with self._lock:
            return len(self._orders)
