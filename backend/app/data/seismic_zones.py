"""Italian seismic zone + regione lookup (US-2.2).

Maps comune (municipality) names to:
  1. the four-zone seismic classification established by OPCM 3519/2006
     and refined by regional ordinanze — values 1 (high) through 4 (very low)
  2. the Italian regione the comune sits in — used to look up applicable
     regional regulations in ``app.data.regional_regulations``

Scope is intentionally pragmatic: ~150 of the most populated Italian comuni
plus all regional capitals. Operators working in an unclassified comune hit
the "Comune non trovato - inserisci manualmente" fallback per AC2 and can
enter the zone manually in the Azienda form.

Expanding the table later is a drop-in: any new entry here is immediately
picked up by ``GET /api/v1/lookup/seismic-zone`` AND by the regulations
lookup — the regione annotation keeps both lookups in sync from one source.

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
        .replace("\u2019", "")  # right single quotation mark
        .replace("\u2018", "")  # left single quotation mark
        .replace("`", "")
    )


# Populated from OPCM 3519/2006 + regional updates. Comments group by Italian
# regione to keep the list auditable; the second tuple element carries the
# regione explicitly so a single update here feeds both lookups in sync.
# Where a comune spans multiple zones (e.g. large metropolitan areas), we
# use the dominant / administratively assigned zone.
_RAW: dict[str, tuple[SeismicZone, str]] = {
    # --- Abruzzo ---
    "L'Aquila": (1, "Abruzzo"),
    "Pescara": (3, "Abruzzo"),
    "Teramo": (2, "Abruzzo"),
    "Chieti": (2, "Abruzzo"),
    "Avezzano": (1, "Abruzzo"),
    "Sulmona": (1, "Abruzzo"),
    # --- Basilicata ---
    "Potenza": (1, "Basilicata"),
    "Matera": (3, "Basilicata"),
    "Melfi": (2, "Basilicata"),
    # --- Calabria ---
    "Catanzaro": (2, "Calabria"),
    "Reggio Calabria": (1, "Calabria"),
    "Cosenza": (2, "Calabria"),
    "Crotone": (2, "Calabria"),
    "Vibo Valentia": (2, "Calabria"),
    "Lamezia Terme": (2, "Calabria"),
    "Castrovillari": (2, "Calabria"),
    # --- Campania ---
    "Napoli": (2, "Campania"),
    "Salerno": (2, "Campania"),
    "Caserta": (2, "Campania"),
    "Avellino": (1, "Campania"),
    "Benevento": (1, "Campania"),
    "Torre del Greco": (2, "Campania"),
    "Giugliano in Campania": (2, "Campania"),
    "Pozzuoli": (2, "Campania"),
    "Portici": (2, "Campania"),
    "Castellammare di Stabia": (2, "Campania"),
    "Afragola": (2, "Campania"),
    "Battipaglia": (2, "Campania"),
    "Ercolano": (2, "Campania"),
    "Casoria": (2, "Campania"),
    # --- Emilia-Romagna ---
    "Bologna": (3, "Emilia-Romagna"),
    "Modena": (3, "Emilia-Romagna"),
    "Parma": (3, "Emilia-Romagna"),
    "Reggio Emilia": (3, "Emilia-Romagna"),
    "Ravenna": (2, "Emilia-Romagna"),
    "Ferrara": (3, "Emilia-Romagna"),
    "Rimini": (2, "Emilia-Romagna"),
    "Forli": (2, "Emilia-Romagna"),
    "Cesena": (2, "Emilia-Romagna"),
    "Piacenza": (3, "Emilia-Romagna"),
    "Imola": (2, "Emilia-Romagna"),
    "Carpi": (3, "Emilia-Romagna"),
    # --- Friuli-Venezia Giulia ---
    "Trieste": (4, "Friuli-Venezia Giulia"),
    "Udine": (3, "Friuli-Venezia Giulia"),
    "Pordenone": (3, "Friuli-Venezia Giulia"),
    "Gorizia": (3, "Friuli-Venezia Giulia"),
    # --- Lazio ---
    "Roma": (3, "Lazio"),
    "Latina": (3, "Lazio"),
    "Frosinone": (3, "Lazio"),
    "Rieti": (2, "Lazio"),
    "Viterbo": (2, "Lazio"),
    "Tivoli": (3, "Lazio"),
    "Fiumicino": (3, "Lazio"),
    "Aprilia": (3, "Lazio"),
    "Pomezia": (3, "Lazio"),
    "Guidonia Montecelio": (3, "Lazio"),
    "Civitavecchia": (3, "Lazio"),
    "Velletri": (2, "Lazio"),
    "Albano Laziale": (3, "Lazio"),
    # --- Liguria ---
    "Genova": (3, "Liguria"),
    "La Spezia": (3, "Liguria"),
    "Savona": (3, "Liguria"),
    "Imperia": (3, "Liguria"),
    "Sanremo": (3, "Liguria"),
    # --- Lombardia ---
    "Milano": (4, "Lombardia"),
    "Brescia": (3, "Lombardia"),
    "Bergamo": (3, "Lombardia"),
    "Monza": (4, "Lombardia"),
    "Como": (3, "Lombardia"),
    "Varese": (4, "Lombardia"),
    "Pavia": (4, "Lombardia"),
    "Cremona": (4, "Lombardia"),
    "Mantova": (3, "Lombardia"),
    "Lecco": (4, "Lombardia"),
    "Lodi": (4, "Lombardia"),
    "Sondrio": (4, "Lombardia"),
    "Busto Arsizio": (4, "Lombardia"),
    "Cinisello Balsamo": (4, "Lombardia"),
    "Sesto San Giovanni": (4, "Lombardia"),
    "Legnano": (4, "Lombardia"),
    "Rho": (4, "Lombardia"),
    "Vigevano": (3, "Lombardia"),
    # --- Marche ---
    "Ancona": (2, "Marche"),
    "Pesaro": (2, "Marche"),
    "Macerata": (2, "Marche"),
    "Ascoli Piceno": (2, "Marche"),
    "Fermo": (2, "Marche"),
    # --- Molise ---
    "Campobasso": (2, "Molise"),
    "Isernia": (1, "Molise"),
    # --- Piemonte ---
    "Torino": (4, "Piemonte"),
    "Novara": (4, "Piemonte"),
    "Alessandria": (3, "Piemonte"),
    "Asti": (3, "Piemonte"),
    "Cuneo": (3, "Piemonte"),
    "Biella": (4, "Piemonte"),
    "Vercelli": (4, "Piemonte"),
    "Verbania": (4, "Piemonte"),
    "Moncalieri": (4, "Piemonte"),
    # --- Puglia ---
    "Bari": (3, "Puglia"),
    "Taranto": (3, "Puglia"),
    "Foggia": (2, "Puglia"),
    "Lecce": (4, "Puglia"),
    "Brindisi": (4, "Puglia"),
    "Andria": (3, "Puglia"),
    "Barletta": (3, "Puglia"),
    "Bisceglie": (3, "Puglia"),
    "Cerignola": (2, "Puglia"),
    "Bitonto": (3, "Puglia"),
    "Molfetta": (3, "Puglia"),
    "Manfredonia": (2, "Puglia"),
    # --- Sardegna ---
    "Cagliari": (4, "Sardegna"),
    "Sassari": (4, "Sardegna"),
    "Nuoro": (4, "Sardegna"),
    "Oristano": (4, "Sardegna"),
    "Olbia": (4, "Sardegna"),
    "Alghero": (4, "Sardegna"),
    # --- Sicilia ---
    "Palermo": (2, "Sicilia"),
    "Catania": (2, "Sicilia"),
    "Messina": (1, "Sicilia"),
    "Siracusa": (2, "Sicilia"),
    "Ragusa": (2, "Sicilia"),
    "Trapani": (3, "Sicilia"),
    "Enna": (2, "Sicilia"),
    "Caltanissetta": (2, "Sicilia"),
    "Agrigento": (3, "Sicilia"),
    "Marsala": (3, "Sicilia"),
    "Acireale": (2, "Sicilia"),
    "Gela": (2, "Sicilia"),
    # --- Toscana ---
    "Firenze": (3, "Toscana"),
    "Prato": (3, "Toscana"),
    "Pisa": (3, "Toscana"),
    "Livorno": (3, "Toscana"),
    "Arezzo": (2, "Toscana"),
    "Pistoia": (3, "Toscana"),
    "Siena": (3, "Toscana"),
    "Lucca": (3, "Toscana"),
    "Grosseto": (4, "Toscana"),
    "Massa": (3, "Toscana"),
    "Carrara": (3, "Toscana"),
    "Viareggio": (3, "Toscana"),
    # --- Trentino-Alto Adige ---
    "Trento": (3, "Trentino-Alto Adige"),
    "Bolzano": (4, "Trentino-Alto Adige"),
    # --- Umbria ---
    "Perugia": (2, "Umbria"),
    "Terni": (2, "Umbria"),
    "Foligno": (1, "Umbria"),
    # --- Valle d'Aosta ---
    "Aosta": (4, "Valle d'Aosta"),
    # --- Veneto ---
    "Venezia": (4, "Veneto"),
    "Verona": (3, "Veneto"),
    "Padova": (4, "Veneto"),
    "Vicenza": (3, "Veneto"),
    "Treviso": (3, "Veneto"),
    "Rovigo": (4, "Veneto"),
    "Belluno": (3, "Veneto"),
    "Valdagno": (3, "Veneto"),
}


_NORMALISED: dict[str, tuple[SeismicZone, str]] = {
    _normalize(name): entry for name, entry in _RAW.items()
}

# Reverse lookup so the endpoint can echo back the canonical spelling.
_CANONICAL: dict[str, str] = {_normalize(name): name for name in _RAW}


def lookup_zone(comune: str) -> tuple[str, SeismicZone] | None:
    """Return (canonical_name, zone) for ``comune``, or None if not found.

    The lookup is case-insensitive and tolerant of leading/trailing whitespace
    and apostrophe variations (L'Aquila vs L\u2019Aquila vs LAquila).
    """
    if not comune:
        return None
    norm = _normalize(comune)
    entry = _NORMALISED.get(norm)
    if entry is None:
        return None
    zone, _regione = entry
    return _CANONICAL[norm], zone


def lookup_regione(comune: str) -> str | None:
    """Return the Italian regione for ``comune``, or None if not in the table.

    Uses the same case-insensitive matching as ``lookup_zone`` so the two
    helpers always agree on whether a comune is known.
    """
    if not comune:
        return None
    entry = _NORMALISED.get(_normalize(comune))
    if entry is None:
        return None
    _zone, regione = entry
    return regione


def table_size() -> int:
    """Exposed primarily for monitoring / tests."""
    return len(_RAW)
