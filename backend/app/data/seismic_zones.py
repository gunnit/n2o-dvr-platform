"""Italian seismic zone + regione lookup (US-2.2).

Maps comune (municipality) names to:
  1. the four-zone seismic classification established by OPCM 3519/2006
     and refined by regional ordinanze - values 1 (high) through 4 (very low)
  2. the Italian regione the comune sits in - used to look up applicable
     regional regulations in ``app.data.regional_regulations``

Data source: Protezione Civile - "classificazione sismica aggiornata maggio
2025" (~7891 comuni). Comuni with sub-zones (1a/1b, 2A/2B, 3S, hybrids) are
normalised to the most conservative base zone (lowest digit = highest risk)
since the DVR Master only renders the four-zone classification.

The companion JSON ``seismic_zones_data.json`` is generated from the source
CSV. To refresh: drop a new CSV in ``credentials/`` and re-run the import
script that produced the JSON.

Source references:
  - OPCM 3519/2006 (classificazione sismica)
  - INGV Istituto Nazionale di Geofisica e Vulcanologia
  - Protezione Civile - elenco comuni per zona sismica (May 2025 release)
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

SeismicZone = Literal[1, 2, 3, 4]

_DATA_PATH = Path(__file__).with_name("seismic_zones_data.json")


def _normalize(value: str) -> str:
    """Normalise a comune name so lookups tolerate casing + apostrophes + accents.

    Operators routinely type "Aglie", "L'Aquila" or "L Aquila" - we want all
    three to match the canonical "Agliè" / "L'Aquila".
    """
    import unicodedata

    no_accents = "".join(
        ch
        for ch in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(ch)
    )
    return (
        no_accents.strip()
        .lower()
        .replace("'", "")
        .replace("’", "")
        .replace("‘", "")
        .replace("`", "")
        .replace("  ", " ")
    )


@lru_cache(maxsize=1)
def _load_table() -> tuple[
    dict[str, tuple[SeismicZone, str]],
    dict[str, str],
]:
    """Load comune -> (zone, regione) and comune -> canonical-name maps.

    Cached for the lifetime of the process; the JSON is ~235 KB so this is a
    one-time cost at first call.
    """
    with _DATA_PATH.open(encoding="utf-8") as fh:
        raw: dict[str, list[object]] = json.load(fh)
    normalised: dict[str, tuple[SeismicZone, str]] = {}
    canonical: dict[str, str] = {}
    for comune, payload in raw.items():
        zone_raw, regione = payload
        zone = int(zone_raw)
        if zone not in (1, 2, 3, 4):
            continue
        key = _normalize(comune)
        normalised[key] = (zone, regione)  # type: ignore[assignment]
        canonical[key] = comune
    return normalised, canonical


def lookup_zone(comune: str) -> tuple[str, SeismicZone] | None:
    """Return (canonical_name, zone) for ``comune``, or None if not found."""
    if not comune:
        return None
    normalised, canonical = _load_table()
    norm = _normalize(comune)
    entry = normalised.get(norm)
    if entry is None:
        return None
    zone, _regione = entry
    return canonical[norm], zone


def lookup_regione(comune: str) -> str | None:
    """Return the Italian regione for ``comune``, or None if not in the table."""
    if not comune:
        return None
    normalised, _canonical = _load_table()
    entry = normalised.get(_normalize(comune))
    if entry is None:
        return None
    _zone, regione = entry
    return regione


def table_size() -> int:
    """Exposed primarily for monitoring / tests."""
    normalised, _canonical = _load_table()
    return len(normalised)


def _build_raw() -> dict[str, tuple[SeismicZone, str]]:
    """Back-compat shim: tests + scripts that need to iterate every comune.

    Built lazily from the JSON; keeps the canonical (non-normalised) name as
    the dict key, mirroring what the old hand-curated _RAW dict did.
    """
    with _DATA_PATH.open(encoding="utf-8") as fh:
        raw = json.load(fh)
    out: dict[str, tuple[SeismicZone, str]] = {}
    for comune, payload in raw.items():
        zone_raw, regione = payload
        zone = int(zone_raw)
        if zone in (1, 2, 3, 4):
            out[comune] = (zone, regione)  # type: ignore[assignment]
    return out


# Back-compat: existing tests import _RAW directly. Expose it as a lazily
# materialised module-level mapping so callers keep working without paying
# the JSON load cost unless they actually iterate it.
class _LazyRaw:
    _cache: dict[str, tuple[SeismicZone, str]] | None = None

    def _ensure(self) -> dict[str, tuple[SeismicZone, str]]:
        if self._cache is None:
            self._cache = _build_raw()
        return self._cache

    def __iter__(self):
        return iter(self._ensure())

    def keys(self):
        return self._ensure().keys()

    def values(self):
        return self._ensure().values()

    def items(self):
        return self._ensure().items()

    def __len__(self):
        return len(self._ensure())

    def __contains__(self, key):
        return key in self._ensure()

    def __getitem__(self, key):
        return self._ensure()[key]


_RAW = _LazyRaw()
