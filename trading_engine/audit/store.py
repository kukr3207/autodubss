"""Append-only event store with aggregate versions and optimistic checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from ..errors import ValidationError
from ..validation import aware_time, clean_text, integer_value
from .events import DomainEvent


@dataclass(frozen=True)
class StoredEvent:
    sequence: int
    aggregate_version: int
    event: DomainEvent

    def as_dict(self):
        result = self.event.as_dict()
        result.update(
            {"sequence": self.sequence, "aggregateVersion": self.aggregate_version}
        )
        return result


class EventStore:
    def __init__(self) -> None:
        self._events: List[StoredEvent] = []
        self._event_ids: Dict[str, int] = {}
        self._versions: Dict[Tuple[str, str], int] = {}
        self._lock = RLock()

    def append(self, event: DomainEvent, *, expected_version: Optional[int] = None) -> StoredEvent:
        if not isinstance(event, DomainEvent):
            raise ValidationError("event must be a DomainEvent")
        expected = (
            None
            if expected_version is None
            else integer_value(expected_version, "expected_version", minimum=0)
        )
        key = (event.aggregate_type, event.aggregate_id)
        with self._lock:
            if str(event.event_id) in self._event_ids:
                raise ValidationError("event id already exists")
            version = self._versions.get(key, 0)
            if expected is not None and expected != version:
                raise ValidationError(
                    "aggregate version conflict",
                    details={"expected": expected, "actual": version},
                )
            if self._events and event.occurred_at < self._events[-1].event.occurred_at:
                raise ValidationError("events must be appended chronologically")
            stored = StoredEvent(len(self._events) + 1, version + 1, event)
            self._events.append(stored)
            self._event_ids[str(event.event_id)] = stored.sequence
            self._versions[key] = stored.aggregate_version
            return stored

    def append_many(
        self,
        events: Iterable[DomainEvent],
        *,
        expected_version: Optional[int] = None,
    ) -> Tuple[StoredEvent, ...]:
        batch = tuple(events)
        if not batch:
            raise ValidationError("event batch cannot be empty")
        first_key = (batch[0].aggregate_type, batch[0].aggregate_id)
        if any((event.aggregate_type, event.aggregate_id) != first_key for event in batch):
            raise ValidationError("event batch must target one aggregate")
        with self._lock:
            current = self.version(*first_key)
            if expected_version is not None and expected_version != current:
                raise ValidationError("aggregate version conflict")
            result = []
            for event in batch:
                result.append(self.append(event, expected_version=current))
                current += 1
            return tuple(result)

    def version(self, aggregate_type: str, aggregate_id: str) -> int:
        key = (
            clean_text(aggregate_type, "aggregate_type"),
            clean_text(aggregate_id, "aggregate_id"),
        )
        with self._lock:
            return self._versions.get(key, 0)

    def get(self, sequence: int) -> StoredEvent:
        checked = integer_value(sequence, "sequence", minimum=1)
        with self._lock:
            if checked > len(self._events):
                raise KeyError("unknown event sequence %d" % checked)
            return self._events[checked - 1]

    def stream(
        self,
        *,
        aggregate_type: Optional[str] = None,
        aggregate_id: Optional[str] = None,
        event_type: Optional[str] = None,
        after_sequence: int = 0,
        occurred_from: Optional[datetime] = None,
        occurred_to: Optional[datetime] = None,
    ) -> Tuple[StoredEvent, ...]:
        after = integer_value(after_sequence, "after_sequence", minimum=0)
        start = aware_time(occurred_from, "occurred_from") if occurred_from else None
        end = aware_time(occurred_to, "occurred_to") if occurred_to else None
        if start and end and end < start:
            raise ValidationError("occurred_to cannot predate occurred_from")
        with self._lock:
            return tuple(
                item
                for item in self._events
                if item.sequence > after
                and (aggregate_type is None or item.event.aggregate_type == aggregate_type)
                and (aggregate_id is None or item.event.aggregate_id == aggregate_id)
                and (event_type is None or item.event.event_type == event_type)
                and (start is None or item.event.occurred_at >= start)
                and (end is None or item.event.occurred_at <= end)
            )

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)
