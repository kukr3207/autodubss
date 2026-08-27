"""Strict JSON codecs for core instruments, quotes, bars, and requests."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from .errors import ValidationError
from .domain.identifiers import AccountId, ClientOrderId
from .domain.instruments import AssetClass, ContractSpec, Instrument
from .domain.orders import OrderRequest, OrderType, Side, TimeInForce
from .market.models import Bar, Quote


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError("%s must be an object" % field)
    return value


def _required(value: Mapping[str, Any], key: str) -> Any:
    if key not in value:
        raise ValidationError("missing required field %s" % key, details={"field": key})
    return value[key]


def _time(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValidationError("%s must be an ISO timestamp" % field)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        raise ValidationError("%s must be an ISO timestamp" % field)


def decode_instrument(value: Any) -> Instrument:
    item = _mapping(value, "instrument")
    contract_data = _mapping(item.get("contract", {}), "contract")
    contract = ContractSpec(
        lot_size=contract_data.get("lotSize", 1),
        tick_size=contract_data.get("tickSize", "0.01"),
        multiplier=contract_data.get("multiplier", "1"),
        price_currency=contract_data.get("priceCurrency", "INR"),
    )
    return Instrument(
        symbol=_required(item, "symbol"),
        exchange=_required(item, "exchange"),
        asset_class=_required(item, "assetClass"),
        contract=contract,
        description=item.get("description"),
    )


def decode_quote(value: Any) -> Quote:
    item = _mapping(value, "quote")
    return Quote(
        instrument=decode_instrument(_required(item, "instrument")),
        bid=_required(item, "bid"),
        ask=_required(item, "ask"),
        bid_size=_required(item, "bidSize"),
        ask_size=_required(item, "askSize"),
        observed_at=_time(_required(item, "observedAt"), "observedAt"),
        provider=_required(item, "provider"),
    )


def decode_bar(value: Any) -> Bar:
    item = _mapping(value, "bar")
    seconds = _required(item, "intervalSeconds")
    if isinstance(seconds, bool) or not isinstance(seconds, int):
        raise ValidationError("intervalSeconds must be an integer")
    return Bar(
        instrument=decode_instrument(_required(item, "instrument")),
        interval=timedelta(seconds=seconds),
        opened_at=_time(_required(item, "openedAt"), "openedAt"),
        closed_at=_time(_required(item, "closedAt"), "closedAt"),
        open=_required(item, "open"),
        high=_required(item, "high"),
        low=_required(item, "low"),
        close=_required(item, "close"),
        volume=_required(item, "volume"),
        trade_count=_required(item, "tradeCount"),
        provider=_required(item, "provider"),
    )


def decode_order_request(value: Any) -> OrderRequest:
    item = _mapping(value, "order request")
    return OrderRequest(
        account_id=AccountId(_required(item, "accountId")),
        client_order_id=ClientOrderId(_required(item, "clientOrderId")),
        instrument=decode_instrument(_required(item, "instrument")),
        side=_required(item, "side"),
        quantity=_required(item, "quantity"),
        order_type=item.get("orderType", OrderType.MARKET.value),
        time_in_force=item.get("timeInForce", TimeInForce.DAY.value),
        limit_price=item.get("limitPrice"),
        stop_price=item.get("stopPrice"),
        strategy_id=item.get("strategyId"),
    )


def encode(value: Any) -> Dict[str, Any]:
    method = getattr(value, "as_dict", None)
    if not callable(method):
        raise ValidationError("value does not support engine serialization")
    result = method()
    if not isinstance(result, dict):
        raise ValidationError("serialized engine values must be objects")
    return result


def dumps(value: Any, *, indent: int = None) -> str:
    if isinstance(value, (list, tuple)):
        payload = [encode(item) for item in value]
    else:
        payload = encode(value)
    return json.dumps(payload, indent=indent, sort_keys=True, separators=None if indent else (",", ":"))


def loads_many(payload: str, decoder) -> Tuple[Any, ...]:
    if not isinstance(payload, str):
        raise ValidationError("payload must be JSON text")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            "payload contains invalid JSON",
            details={"line": exc.lineno, "column": exc.colno},
        )
    if not isinstance(data, list):
        raise ValidationError("payload must contain a JSON array")
    if not callable(decoder):
        raise ValidationError("decoder must be callable")
    result = []
    for index, item in enumerate(data):
        try:
            result.append(decoder(item))
        except ValidationError as exc:
            raise ValidationError(
                "invalid item at index %d: %s" % (index, exc.message),
                details={"index": index, "cause": exc.as_dict()},
            )
    return tuple(result)
