"""Immutable domain events for traceable automated decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional

from ..errors import ValidationError
from ..validation import aware_time, clean_text
from ..domain.identifiers import EventId


def _json_value(value: Any, path: str = "payload") -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list) or isinstance(value, tuple):
        return [_json_value(item, "%s[]" % path) for item in value]
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError("%s keys must be strings" % path)
            result[key] = _json_value(item, "%s.%s" % (path, key))
        return result
    raise ValidationError("%s contains a non-JSON value" % path)


@dataclass(frozen=True)
class DomainEvent:
    event_id: EventId
    event_type: str
    aggregate_type: str
    aggregate_id: str
    occurred_at: datetime
    payload: Mapping[str, Any]
    actor: str = "system"
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, EventId):
            raise ValidationError("event_id must be an EventId")
        for field in ("event_type", "aggregate_type", "aggregate_id", "actor"):
            object.__setattr__(
                self,
                field,
                clean_text(getattr(self, field), field, max_length=120),
            )
        object.__setattr__(self, "occurred_at", aware_time(self.occurred_at, "occurred_at"))
        checked = _json_value(dict(self.payload))
        object.__setattr__(self, "payload", MappingProxyType(checked))
        for field in ("correlation_id", "causation_id"):
            if getattr(self, field) is not None:
                object.__setattr__(self, field, clean_text(getattr(self, field), field, max_length=120))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "eventId": str(self.event_id),
            "eventType": self.event_type,
            "aggregateType": self.aggregate_type,
            "aggregateId": self.aggregate_id,
            "occurredAt": self.occurred_at.isoformat(),
            "payload": dict(self.payload),
            "actor": self.actor,
            "correlationId": self.correlation_id,
            "causationId": self.causation_id,
        }
