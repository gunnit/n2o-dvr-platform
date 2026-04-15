"""Reference-data lookups (US-2.2 seismic zones + regional regulations)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.data.regional_regulations import get_regulations_for_comune
from app.data.seismic_zones import lookup_regione, lookup_zone
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/lookup", tags=["lookup"])


class Regulation(BaseModel):
    titolo: str
    riferimento: str
    ambito: str


class SeismicZoneResponse(BaseModel):
    comune_query: str
    comune_matched: str | None
    zona: int | None
    found: bool
    source: str
    # US-2.2 AC1 (second half): the operator needs the regione + applicable
    # regional regulations alongside the seismic zone so both parts of
    # "Contesto Territoriale" resolve from a single fetch.
    regione: str | None = None
    regolamenti_regionali: list[Regulation] = []


@router.get("/seismic-zone", response_model=SeismicZoneResponse)
async def seismic_zone(
    comune: str = Query(..., min_length=1, max_length=120),
    _: User = Depends(get_current_user),
) -> SeismicZoneResponse:
    """Resolve a comune to its OPCM 3519/2006 seismic zone + regional regs.

    Returns ``found=False`` (and empty ``regolamenti_regionali``) for
    unmapped comuni so the frontend can surface the "Comune non trovato -
    inserisci manualmente" fallback (AC2) without treating the miss as
    an error. When the comune IS known we additionally return the regione
    and the list of applicable regional regulations (empty list if the
    regione has no mapped regulations).
    """
    match = lookup_zone(comune)
    if match is None:
        return SeismicZoneResponse(
            comune_query=comune,
            comune_matched=None,
            zona=None,
            found=False,
            source="OPCM 3519/2006",
            regione=None,
            regolamenti_regionali=[],
        )
    canonical, zona = match
    regione = lookup_regione(comune)
    _, regulations = get_regulations_for_comune(comune)
    return SeismicZoneResponse(
        comune_query=comune,
        comune_matched=canonical,
        zona=zona,
        found=True,
        source="OPCM 3519/2006",
        regione=regione,
        regolamenti_regionali=[Regulation(**r) for r in regulations],
    )


class RegionalRegulationsResponse(BaseModel):
    comune_query: str
    comune_matched: str | None
    regione: str | None
    found: bool
    regolamenti: list[Regulation]


@router.get("/regional-regulations", response_model=RegionalRegulationsResponse)
async def regional_regulations(
    comune: str = Query(..., min_length=1, max_length=120),
    _: User = Depends(get_current_user),
) -> RegionalRegulationsResponse:
    """Return applicable regional safety regulations for a comune.

    Companion to ``/lookup/seismic-zone`` for callers that only care
    about the regolamenti list (e.g. the DVR generator invoking the
    lookup at build time without needing the seismic zone re-echoed).
    """
    match = lookup_zone(comune)
    canonical = match[0] if match else None
    regione, regulations = get_regulations_for_comune(comune)
    return RegionalRegulationsResponse(
        comune_query=comune,
        comune_matched=canonical,
        regione=regione,
        found=regione is not None,
        regolamenti=[Regulation(**r) for r in regulations],
    )
