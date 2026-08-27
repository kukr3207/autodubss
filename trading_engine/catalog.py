"""Thread-safe instrument catalog with symbol and asset-class searches."""

from __future__ import annotations

from threading import RLock
from typing import Dict, Iterable, Optional, Tuple

from .errors import DuplicateRequestError, ValidationError
from .validation import clean_code, clean_text, enum_value, integer_value
from .domain.instruments import AssetClass, Instrument


class InstrumentCatalog:
    def __init__(self, instruments: Iterable[Instrument] = ()) -> None:
        self._items: Dict[str, Instrument] = {}
        self._aliases: Dict[str, str] = {}
        self._lock = RLock()
        for instrument in instruments:
            self.add(instrument)

    def add(self, instrument: Instrument, aliases: Iterable[str] = ()) -> Instrument:
        if not isinstance(instrument, Instrument):
            raise ValidationError("instrument must be an Instrument")
        normalized_aliases = tuple(
            clean_code(alias, "alias", max_length=50) for alias in aliases
        )
        with self._lock:
            if instrument.key in self._items:
                raise DuplicateRequestError("instrument already exists")
            conflicts = [alias for alias in normalized_aliases if alias in self._aliases]
            if conflicts:
                raise DuplicateRequestError(
                    "instrument alias already exists",
                    details={"aliases": conflicts},
                )
            self._items[instrument.key] = instrument
            for alias in normalized_aliases:
                self._aliases[alias] = instrument.key
            return instrument

    def remove(self, instrument_key: str) -> Instrument:
        key = clean_text(instrument_key, "instrument_key")
        with self._lock:
            try:
                removed = self._items.pop(key)
            except KeyError:
                raise KeyError("unknown instrument %s" % key)
            for alias in [name for name, target in self._aliases.items() if target == key]:
                del self._aliases[alias]
            return removed

    def get(self, instrument_key: str) -> Instrument:
        key = clean_text(instrument_key, "instrument_key")
        with self._lock:
            try:
                return self._items[key]
            except KeyError:
                alias = key.upper()
                target = self._aliases.get(alias)
                if target is not None:
                    return self._items[target]
                raise KeyError("unknown instrument %s" % key)

    def find(
        self,
        query: Optional[str] = None,
        *,
        exchange: Optional[str] = None,
        asset_class: Optional[AssetClass] = None,
        limit: int = 100,
    ) -> Tuple[Instrument, ...]:
        term = None if query is None else clean_text(query, "query").lower()
        venue = None if exchange is None else clean_code(exchange, "exchange", max_length=20)
        kind = None if asset_class is None else enum_value(asset_class, AssetClass, "asset_class")
        checked_limit = integer_value(limit, "limit", minimum=1, maximum=1000)
        with self._lock:
            values = [
                item
                for item in self._items.values()
                if (venue is None or item.exchange == venue)
                and (kind is None or item.asset_class is kind)
                and (
                    term is None
                    or term in item.symbol.lower()
                    or term in (item.description or "").lower()
                )
            ]
        return tuple(sorted(values, key=lambda item: item.key)[:checked_limit])

    def aliases_for(self, instrument_key: str) -> Tuple[str, ...]:
        instrument = self.get(instrument_key)
        with self._lock:
            return tuple(
                sorted(alias for alias, target in self._aliases.items() if target == instrument.key)
            )

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
