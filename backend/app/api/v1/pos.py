"""POS CRUD + DPI matrix endpoints (US-4.8).

The DPI matrix lives on the Pos row so each client has their own
customised cells. The global rules engine (services/dpi_rules.py) is only
ever read — operator overrides never bleed back into the global suggestions.

Route order matters: the ``/meta/dpi-catalog`` literal must be declared
before ``/{pos_id}`` so FastAPI doesn't try to parse ``meta`` as a UUID.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from pydantic import BaseModel as PydanticBaseModel

from app.core.exceptions import AIError, NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org
from app.models.azienda import Azienda
from app.models.pos import Pos
from app.schemas.pos import (
    DpiCatalogResponse,
    DpiMatrixUpdate,
    PosCreate,
    PosResponse,
    PosUpdate,
)
from app.schemas.pos_phase import PosPhasesUpdate
from app.services.dpi_rules import (
    DPI_CATALOG,
    PHASES_CONSTRUCTION,
    ROLES_CONSTRUCTION,
    build_default_matrix,
)
from app.services.pos_phases import (
    PosPhaseError,
    normalize_ordering,
    validate_phases,
)

router = APIRouter(prefix="/aziende/{azienda_id}/pos", tags=["pos"])


# --- Helpers --------------------------------------------------------------


async def _get_azienda(
    azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> Azienda:
    result = await db.execute(
        select(Azienda).where(
            Azienda.id == azienda_id, Azienda.organization_id == org_id
        )
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


async def _get_pos(
    pos_id: uuid.UUID, azienda_id: uuid.UUID, db: AsyncSession
) -> Pos:
    result = await db.execute(
        select(Pos).where(Pos.id == pos_id, Pos.azienda_id == azienda_id)
    )
    pos = result.scalar_one_or_none()
    if not pos:
        raise NotFoundError("POS non trovato")
    return pos


# --- Meta (must come before /{pos_id}) ------------------------------------


@router.get("/meta/dpi-catalog", response_model=DpiCatalogResponse)
async def get_dpi_catalog(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> DpiCatalogResponse:
    """Return the canonical roles / phases / DPI label map.

    Powers the three matrix editor cards on the frontend (role selector,
    phase selector, per-cell DPI chip picker). Static for now but routed
    per-azienda so the frontend uses the same ``/aziende/.../pos`` base URL
    everywhere.
    """
    await _get_azienda(azienda_id, org_id, db)
    return DpiCatalogResponse(
        roles=list(ROLES_CONSTRUCTION),
        phases=list(PHASES_CONSTRUCTION),
        dpi_catalog=dict(DPI_CATALOG),
    )


# --- CRUD -----------------------------------------------------------------


@router.get("", response_model=list[PosResponse])
async def list_pos(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[Pos]:
    await _get_azienda(azienda_id, org_id, db)
    result = await db.execute(
        select(Pos).where(Pos.azienda_id == azienda_id).order_by(Pos.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=PosResponse, status_code=status.HTTP_201_CREATED)
async def create_pos(
    azienda_id: uuid.UUID,
    body: PosCreate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Pos:
    await _get_azienda(azienda_id, org_id, db)
    payload: dict[str, Any] = body.model_dump(exclude_none=True)
    pos = Pos(azienda_id=azienda_id, **payload)
    db.add(pos)
    await db.commit()
    await db.refresh(pos)
    return pos


@router.get("/{pos_id}", response_model=PosResponse)
async def get_pos(
    azienda_id: uuid.UUID,
    pos_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Pos:
    await _get_azienda(azienda_id, org_id, db)
    return await _get_pos(pos_id, azienda_id, db)


@router.put("/{pos_id}", response_model=PosResponse)
async def update_pos(
    azienda_id: uuid.UUID,
    pos_id: uuid.UUID,
    body: PosUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Pos:
    await _get_azienda(azienda_id, org_id, db)
    pos = await _get_pos(pos_id, azienda_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(pos, field, value)
    await db.commit()
    await db.refresh(pos)
    return pos


@router.delete("/{pos_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pos(
    azienda_id: uuid.UUID,
    pos_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_azienda(azienda_id, org_id, db)
    pos = await _get_pos(pos_id, azienda_id, db)
    await db.delete(pos)
    await db.commit()


# --- DPI matrix sub-resource ---------------------------------------------


@router.post("/{pos_id}/dpi-matrix", response_model=PosResponse)
async def update_dpi_matrix(
    azienda_id: uuid.UUID,
    pos_id: uuid.UUID,
    body: DpiMatrixUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Pos:
    """Regenerate or persist the DPI matrix for this POS.

    * ``matrix=None`` → rebuild defaults from the rules engine (the
      "Rigenera dai default" action). Overwrites any operator edits.
    * ``matrix`` provided → persist as-is (cell overrides). Global rules
      are untouched, as required by US-4.8 AC2.
    """
    await _get_azienda(azienda_id, org_id, db)
    pos = await _get_pos(pos_id, azienda_id, db)

    pos.dpi_matrix_roles = list(body.roles)
    pos.dpi_matrix_phases = list(body.phases)
    if body.matrix is None:
        pos.dpi_matrix = build_default_matrix(body.roles, body.phases)
    else:
        pos.dpi_matrix = body.matrix

    # JSONB columns need an explicit dirty flag when we reassign a dict/list
    # that Python might consider the same identity.
    flag_modified(pos, "dpi_matrix")
    flag_modified(pos, "dpi_matrix_roles")
    flag_modified(pos, "dpi_matrix_phases")

    await db.commit()
    await db.refresh(pos)
    return pos


# --- Phase-builder sub-resource (US-4.7) ---------------------------------


@router.put("/{pos_id}/fasi", response_model=PosResponse)
async def update_phases(
    azienda_id: uuid.UUID,
    pos_id: uuid.UUID,
    body: PosPhasesUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Pos:
    """Replace the POS phase list with a validated, ordered payload.

    The frontend phase-builder (US-4.7) owns the full list — drag-drop
    reorder, per-phase NIOSH/rumore/vibrazioni snapshots, and dependency
    links. This endpoint is the single write surface for that state.

    Structural rules live in ``services/pos_phases.py``:
      * unique phase ids
      * ``dipende_da`` references existing phases only
      * no self-dependencies, no dependency cycles

    On save we renumber ``ordine`` to ``0..n-1`` so the persisted JSONB
    is dense and sorted. Soft inconsistencies (a dependency placed
    *after* the phase that depends on it) are allowed — the generator
    footnotes them — because blocking on soft violations would punish
    iterative editing.
    """
    await _get_azienda(azienda_id, org_id, db)
    pos = await _get_pos(pos_id, azienda_id, db)

    try:
        validate_phases(body.fasi)
    except PosPhaseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    normalized = normalize_ordering(body.fasi)
    # Persist as plain dicts so the JSONB column stays provider-agnostic
    # (same shape the generator reads back via ``f.get("...")``).
    pos.fasi_lavorative = [p.model_dump(mode="json") for p in normalized]
    flag_modified(pos, "fasi_lavorative")

    await db.commit()
    await db.refresh(pos)
    return pos


# --- AI phase suggestion endpoint ------------------------------------------


class PhaseSuggestRequest(PydanticBaseModel):
    """Request body for AI-powered phase detail suggestions."""
    fase_nome: str


class PhaseSuggestResponse(PydanticBaseModel):
    """AI-generated phase details."""
    descrizione: str
    rischi: list[str]
    dpi: list[str]


@router.post("/meta/suggest-phase", response_model=PhaseSuggestResponse)
async def suggest_phase_details(
    azienda_id: uuid.UUID,
    body: PhaseSuggestRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> PhaseSuggestResponse:
    """Generate AI suggestions for a POS construction phase.

    Given a phase name (e.g. "Scavo", "Montaggio ponteggi"), returns a
    suggested description, list of typical risks, and required DPI. The
    operator reviews and can edit before saving.
    """
    await _get_azienda(azienda_id, org_id, db)

    if not body.fase_nome.strip():
        raise HTTPException(
            status_code=400,
            detail="Nome fase richiesto per la generazione AI.",
        )

    from app.services.ai.pos_phase_suggester import suggest_phase_details as _suggest

    try:
        result = await _suggest(body.fase_nome.strip())
    except AIError as exc:
        raise HTTPException(status_code=502, detail=exc.detail) from exc

    return PhaseSuggestResponse(
        descrizione=result.descrizione,
        rischi=result.rischi,
        dpi=result.dpi,
    )


# --- AI DPI matrix suggestion endpoint (feedback #64/#50) ------------------


class DpiMatrixSuggestRequest(PydanticBaseModel):
    """Request body for AI-powered DPI matrix auto-fill.

    The frontend sends the current role/phase keys (``dpi_matrix_roles`` /
    ``dpi_matrix_phases``) so the AI suggests DPI for exactly the cells the
    operator sees. No personal data — roles/phases only.
    """

    roles: list[str]
    phases: list[str]


class DpiMatrixSuggestResponse(PydanticBaseModel):
    """AI-suggested DPI matrix, same ``{phase: {role: [codes]}}`` shape as
    ``Pos.dpi_matrix``. The frontend merges this into empty cells only."""

    matrix: dict[str, dict[str, list[str]]]


@router.post("/meta/suggest-dpi-matrix", response_model=DpiMatrixSuggestResponse)
async def suggest_dpi_matrix(
    azienda_id: uuid.UUID,
    body: DpiMatrixSuggestRequest,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> DpiMatrixSuggestResponse:
    """AI auto-fill for the POS DPI matrix (feedback #64/#50).

    Given the current roles + phases, returns a suggested
    ``{phase: {role: [dpi_codes]}}`` map. Codes are validated against
    ``DPI_CATALOG`` server-side; the operator reviews and the frontend only
    writes suggestions into cells that are still empty (never overwriting an
    operator's choice, including the "non effettua" sentinel).
    """
    azienda = await _get_azienda(azienda_id, org_id, db)

    roles = [r for r in body.roles if r and r.strip()]
    phases = [p for p in body.phases if p and p.strip()]
    if not roles or not phases:
        raise HTTPException(
            status_code=400,
            detail="Seleziona almeno un ruolo e una fase per la compilazione AI.",
        )

    # Non-PII grounding context: ATECO + activity description only.
    context_parts: list[str] = []
    if azienda.codice_ateco:
        context_parts.append(f"Codice ATECO: {azienda.codice_ateco}")
    if azienda.attivita:
        context_parts.append(f"Attivita': {azienda.attivita}")
    if azienda.descrizione_attivita:
        context_parts.append(f"Descrizione: {azienda.descrizione_attivita}")
    azienda_context = "\n".join(context_parts) or None

    from app.services.ai.pos_dpi_matrix_suggester import (
        suggest_dpi_matrix as _suggest,
    )

    try:
        matrix = await _suggest(
            ruoli=roles,
            fasi=phases,
            azienda_context=azienda_context,
        )
    except AIError as exc:
        raise HTTPException(status_code=502, detail=exc.detail) from exc

    return DpiMatrixSuggestResponse(matrix=matrix)
