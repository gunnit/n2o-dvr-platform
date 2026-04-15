"""Reference-data lookups (US-2.2 seismic zones, future: ATECO, CAP, ...)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.data.seismic_zones import lookup_zone
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/lookup", tags=["lookup"])


class SeismicZoneResponse(BaseModel):
    comune_query: str
    comune_matched: str | None
    zona: int | None
    found: bool
    source: str


@router.get("/seismic-zone", response_model=SeismicZoneResponse)
async def seismic_zone(
    comune: str = Query(..., min_length=1, max_length=120),
    _: User = Depends(get_current_user),
) -> SeismicZoneResponse:
    """Resolve a comune to its OPCM 3519/2006 seismic zone (1-4).

    Returns ``found=False`` for unmapped comuni so the frontend can surface
    the "Comune non trovato - inserisci manualmente" fallback (AC2) without
    treating the miss as an error.
    """
    match = lookup_zone(comune)
    if match is None:
        return SeismicZoneResponse(
            comune_query=comune,
            comune_matched=None,
            zona=None,
            found=False,
            source="OPCM 3519/2006",
        )
    canonical, zona = match
    return SeismicZoneResponse(
        comune_query=comune,
        comune_matched=canonical,
        zona=zona,
        found=True,
        source="OPCM 3519/2006",
    )
