"""Append-only domain history and tamper-evident exports."""

from .events import DomainEvent
from .export import export_jsonl, read_jsonl
from .hashchain import (
    GENESIS_HASH,
    ChainedEvent,
    build_chain,
    canonical_json,
    event_digest,
    verify_chain,
)
from .store import EventStore, StoredEvent

__all__ = [
    "ChainedEvent",
    "DomainEvent",
    "EventStore",
    "GENESIS_HASH",
    "StoredEvent",
    "build_chain",
    "canonical_json",
    "event_digest",
    "export_jsonl",
    "read_jsonl",
    "verify_chain",
]
