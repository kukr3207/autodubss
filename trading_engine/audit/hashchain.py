"""Tamper-evident hash chaining for exported audit records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

from ..errors import ValidationError
from .store import StoredEvent


GENESIS_HASH = "0" * 64


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class ChainedEvent:
    stored_event: StoredEvent
    previous_hash: str
    event_hash: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "record": self.stored_event.as_dict(),
            "previousHash": self.previous_hash,
            "eventHash": self.event_hash,
        }


def event_digest(stored: StoredEvent, previous_hash: str) -> str:
    if len(previous_hash) != 64:
        raise ValidationError("previous_hash must be a SHA-256 digest")
    body = canonical_json(stored.as_dict()).encode("utf-8")
    return hashlib.sha256(previous_hash.encode("ascii") + b":" + body).hexdigest()


def build_chain(events: Iterable[StoredEvent]) -> Tuple[ChainedEvent, ...]:
    result = []
    previous = GENESIS_HASH
    expected_sequence = 1
    for stored in events:
        if stored.sequence != expected_sequence:
            raise ValidationError("events must form a contiguous sequence")
        digest = event_digest(stored, previous)
        result.append(ChainedEvent(stored, previous, digest))
        previous = digest
        expected_sequence += 1
    return tuple(result)


def verify_chain(chain: Iterable[ChainedEvent]) -> bool:
    previous = GENESIS_HASH
    expected_sequence = 1
    for item in chain:
        if not isinstance(item, ChainedEvent):
            return False
        if item.stored_event.sequence != expected_sequence:
            return False
        if item.previous_hash != previous:
            return False
        if item.event_hash != event_digest(item.stored_event, previous):
            return False
        previous = item.event_hash
        expected_sequence += 1
    return True
