"""Italian seismic zone lookup (US-2.2).

Maps comune (municipality) names to the four-zone seismic classification
established by OPCM 3519/2006 and refined by regional ordinanze. Values:

  1  — alto rischio (high)
  2  — medio rischio (medium)
  3  — basso rischio (low)
  4  — molto basso (very low)

Scope is intentionally pragmatic: ~100 of the most populated Italian comuni
plus all regional capitals. Operators working in an unclassified comune hit
the "Comune non trovato - inserisci manualmente" fallback per AC2 and can
enter the zone manually in the Azienda form.

Expanding the table later is a drop-in: any new entry here is immediately
picked up by ``GET /api/v1/lookup/seismic-zone``. Keys are normalised to
``_normalize`` (lowercase, stripped, apostrophe-free) so lookups tolerate
casing and typography variations.

Source references:
  - OPCM 3519/2006 (classificazione sismica)
  - INGV Istituto Nazionale di Geofisica e Vulcanologia
  - Protezione Civile — elenco comuni per zona sismica
"""

from __future__ import annotations

from typing import Literal

SeismicZone = Literal[1, 2, 3, 4]


def _normalize(value: str) -> str:
    """Normalise a comune name so lookups tolerate casing + apostrophes."""
    return (
        value.strip()
        .lower()
        .replace("'", "")
        .replace("'", "")
        .replace("`", "")
    )


# Populated from OPCM 3519/2006 + regional updates. Prefixed comments group
# by Italian region to keep the list auditable. Where a comune spans multiple
# zones (e.g. large metropolitan areas), we use the dominant / administratively
# assigned zone.
_RAW: dict[str, SeismicZone] = {
    # --- Abruzzo ---
    "L'Aquila": 1,
    "Pescara": 3,
    "Teramo": 2,
    "Chieti": 2,
    "Avezzano": 1,
    "Sulmona": 1,
    # --- Basilicata ---
    "Potenza": 1,
    "Matera": 3,
    "Melfi": 2,
    # --- Calabria ---
    "Catanzaro": 2,
    "Reggio Calabria": 1,
    "Cosenza": 2,
    "Crotone": 2,
    "Vibo Valentia": 2,
    "Lamezia Terme": 2,
    "Castrovillari": 2,
    # --- Campania ---
    "Napoli": 2,
    "Salerno": 2,
    "Caserta": 2,
    "Avellino": 1,
    "Benevento": 1,
    "Torre del Greco": 2,
    "Giugliano in Campania": 2,
    "Pozzuoli": 2,
    "Portici": 2,
    "Castellammare di Stabia": 2,
    "Afragola": 2,
    "Battipaglia": 2,
    "Ercolano": 2,
    "Casoria": 2,
    # --- Emilia-Romagna ---
    "Bologna": 3,
    "Modena": 3,
    "Parma": 3,
    "Reggio Emilia": 3,
    "Ravenna": 2,
    "Ferrara": 3,
    "Rimini": 2,
    "Forli": 2,
    "Cesena": 2,
    "Piacenza": 3,
    "Imola": 2,
    "Carpi": 3,
    # --- Friuli-Venezia Giulia ---
    "Trieste": 4,
    "Udine": 3,
    "Pordenone": 3,
    "Gorizia": 3,
    # --- Lazio ---
    "Roma": 3,
    "Latina": 3,
    "Frosinone": 3,
    "Rieti": 2,
    "Viterbo": 2,
    "Tivoli": 3,
    "Fiumicino": 3,
    "Aprilia": 3,
    "Pomezia": 3,
    "Guidonia Montecelio": 3,
    "Civitavecchia": 3,
    "Velletri": 2,
    "Albano Laziale": 3,
    # --- Liguria ---
    "Genova": 3,
    "La Spezia": 3,
    "Savona": 3,
    "Imperia": 3,
    "Sanremo": 3,
    # --- Lombardia ---
    "Milano": 4,
    "Brescia": 3,
    "Bergamo": 3,
    "Monza": 4,
    "Como": 3,
    "Varese": 4,
    "Pavia": 4,
    "Cremona": 4,
    "Mantova": 3,
    "Lecco": 4,
    "Lodi": 4,
    "Sondrio": 4,
    "Busto Arsizio": 4,
    "Cinisello Balsamo": 4,
    "Sesto San Giovanni": 4,
    "Legnano": 4,
    "Rho": 4,
    "Vigevano": 3,
    # --- Marche ---
    "Ancona": 2,
    "Pesaro": 2,
    "Macerata": 2,
    "Ascoli Piceno": 2,
    "Fermo": 2,
    # --- Molise ---
    "Campobasso": 2,
    "Isernia": 1,
    # --- Piemonte ---
    "Torino": 4,
    "Novara": 4,
    "Alessandria": 3,
    "Asti": 3,
    "Cuneo": 3,
    "Biella": 4,
    "Vercelli": 4,
    "Verbania": 4,
    "Moncalieri": 4,
    # --- Puglia ---
    "Bari": 3,
    "Taranto": 3,
    "Foggia": 2,
    "Lecce": 4,
    "Brindisi": 4,
    "Andria": 3,
    "Barletta": 3,
    "Bisceglie": 3,
    "Cerignola": 2,
    "Bitonto": 3,
    "Molfetta": 3,
    "Manfredonia": 2,
    # --- Sardegna ---
    "Cagliari": 4,
    "Sassari": 4,
    "Nuoro": 4,
    "Oristano": 4,
    "Olbia": 4,
    "Alghero": 4,
    # --- Sicilia ---
    "Palermo": 2,
    "Catania": 2,
    "Messina": 1,
    "Siracusa": 2,
    "Ragusa": 2,
    "Trapani": 3,
    "Enna": 2,
    "Caltanissetta": 2,
    "Agrigento": 3,
    "Marsala": 3,
    "Acireale": 2,
    "Gela": 2,
    # --- Toscana ---
    "Firenze": 3,
    "Prato": 3,
    "Pisa": 3,
    "Livorno": 3,
    "Arezzo": 2,
    "Pistoia": 3,
    "Siena": 3,
    "Lucca": 3,
    "Grosseto": 4,
    "Massa": 3,
    "Carrara": 3,
    "Viareggio": 3,
    # --- Trentino-Alto Adige ---
    "Trento": 3,
    "Bolzano": 4,
    # --- Umbria ---
    "Perugia": 2,
    "Terni": 2,
    "Foligno": 1,
    # --- Valle d'Aosta ---
    "Aosta": 4,
    # --- Veneto ---
    "Venezia": 4,
    "Verona": 3,
    "Padova": 4,
    "Vicenza": 3,
    "Treviso": 3,
    "Rovigo": 4,
    "Belluno": 3,
    "Valdagno": 3,
}


_NORMALISED: dict[str, SeismicZone] = {
    _normalize(name): zone for name, zone in _RAW.items()
}

# Reverse lookup so the endpoint can echo back the canonical spelling.
_CANONICAL: dict[str, str] = {_normalize(name): name for name in _RAW}


def lookup_zone(comune: str) -> tuple[str, SeismicZone] | None:
    """Return (canonical_name, zone) for ``comune``, or None if not found.

    The lookup is case-insensitive and tolerant of leading/trailing whitespace
    and apostrophe variations (L'Aquila vs L'Aquila vs LAquila).
    """
    if not comune:
        return None
    norm = _normalize(comune)
    zone = _NORMALISED.get(norm)
    if zone is None:
        return None
    return _CANONICAL[norm], zone


def table_size() -> int:
    """Exposed primarily for monitoring / tests."""
    return len(_RAW)
