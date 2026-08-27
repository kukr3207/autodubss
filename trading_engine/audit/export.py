"""JSON Lines audit export with atomic replacement and integrity metadata."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, Tuple

from ..errors import ValidationError
from .hashchain import ChainedEvent, build_chain, verify_chain
from .store import EventStore


def export_jsonl(store: EventStore, path) -> int:
    if not isinstance(store, EventStore):
        raise ValidationError("store must be EventStore")
    target = Path(path)
    if target.exists() and target.is_dir():
        raise ValidationError("audit export path cannot be a directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    chain = build_chain(store.stream())
    temporary = target.with_name(".%s.tmp" % target.name)
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for item in chain:
                handle.write(json.dumps(item.as_dict(), sort_keys=True, separators=(",", ":")))
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(target))
    finally:
        if temporary.exists():
            temporary.unlink()
    return len(chain)


def read_jsonl(path) -> Tuple[dict, ...]:
    target = Path(path)
    if not target.is_file():
        raise ValidationError("audit export does not exist")
    result = []
    with target.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValidationError(
                    "invalid audit JSON on line %d" % line_number,
                    details={"line": line_number, "reason": str(exc)},
                )
            if not isinstance(item, dict):
                raise ValidationError("audit records must be JSON objects")
            result.append(item)
    return tuple(result)
