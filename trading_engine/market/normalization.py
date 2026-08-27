"""Normalize unordered provider payloads before they enter the data store."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from ..errors import MarketDataError, ValidationError
from ..validation import clean_text, integer_value
from ..domain.instruments import Instrument
from .models import Quote, TradeTick


@dataclass(frozen=True)
class ProviderSchema:
    bid: str = "bid"
    ask: str = "ask"
    bid_size: str = "bid_size"
    ask_size: str = "ask_size"
    timestamp: str = "timestamp"
    price: str = "price"
    quantity: str = "quantity"
    trade_id: str = "trade_id"

    def __post_init__(self) -> None:
        for field in self.__dataclass_fields__:
            object.__setattr__(self, field, clean_text(getattr(self, field), field))


def parse_provider_time(value: Any, field: str = "timestamp") -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        numeric = float(value)
        if abs(numeric) > 100000000000:
            numeric /= 1000
        try:
            result = datetime.fromtimestamp(numeric, timezone.utc)
        except (OverflowError, OSError, ValueError):
            raise ValidationError("%s epoch is outside supported bounds" % field)
    elif isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            result = datetime.fromisoformat(normalized)
        except ValueError:
            raise ValidationError("%s must be an ISO timestamp or epoch" % field)
    else:
        raise ValidationError("%s must be a timestamp" % field)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValidationError("%s must include a timezone" % field)
    return result.astimezone(timezone.utc)


class ProviderNormalizer:
    def __init__(
        self,
        provider: str,
        instrument: Instrument,
        schema: ProviderSchema = ProviderSchema(),
    ) -> None:
        self.provider = clean_text(provider, "provider", max_length=60).lower()
        if not isinstance(instrument, Instrument):
            raise ValidationError("instrument must be an Instrument")
        if not isinstance(schema, ProviderSchema):
            raise ValidationError("schema must be ProviderSchema")
        self.instrument = instrument
        self.schema = schema

    @staticmethod
    def _field(payload: Mapping[str, Any], name: str) -> Any:
        if name not in payload:
            raise MarketDataError("provider payload is missing %s" % name)
        return payload[name]

    def quote(self, payload: Mapping[str, Any]) -> Quote:
        if not isinstance(payload, Mapping):
            raise ValidationError("provider payload must be a mapping")
        return Quote(
            self.instrument,
            self._field(payload, self.schema.bid),
            self._field(payload, self.schema.ask),
            int(self._field(payload, self.schema.bid_size)),
            int(self._field(payload, self.schema.ask_size)),
            parse_provider_time(self._field(payload, self.schema.timestamp)),
            self.provider,
        )

    def tick(self, payload: Mapping[str, Any]) -> TradeTick:
        if not isinstance(payload, Mapping):
            raise ValidationError("provider payload must be a mapping")
        return TradeTick(
            self.instrument,
            self._field(payload, self.schema.price),
            int(self._field(payload, self.schema.quantity)),
            parse_provider_time(self._field(payload, self.schema.timestamp)),
            self.provider,
            payload.get(self.schema.trade_id),
        )

    def quotes(
        self,
        payloads: Iterable[Mapping[str, Any]],
        *,
        drop_duplicates: bool = True,
    ) -> Tuple[Quote, ...]:
        result = []
        seen = set()
        for index, payload in enumerate(payloads):
            try:
                quote = self.quote(payload)
            except (ValidationError, MarketDataError) as exc:
                raise MarketDataError(
                    "invalid quote at provider index %d" % index,
                    details={"index": index, "cause": exc.as_dict()},
                )
            identity = (quote.observed_at, quote.bid, quote.ask, quote.bid_size, quote.ask_size)
            if not drop_duplicates or identity not in seen:
                result.append(quote)
                seen.add(identity)
        return tuple(sorted(result, key=lambda item: item.observed_at))
