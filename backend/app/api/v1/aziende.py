import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.session import get_db
from app.dependencies import get_current_org, get_current_user
from app.models.azienda import Azienda
from app.models.description_revision import (
    SOURCE_AI,
    SOURCE_MANUAL,
    DescriptionRevision,
)
from app.models.documento_generato import DocumentoGenerato
from app.models.user import User
from app.schemas.azienda import (
    AziendaAutofillResponse,
    AziendaCreate,
    AziendaResponse,
    AziendaUpdate,
)
from app.schemas.description_revision import (
    DescriptionRevisionResponse,
    DescriptionRevisionRestoreResponse,
    VisuraUploadResponse,
)
from app.services.ai import generate_company_description
from app.services.azienda_autofill import autofill_from_piva
from app.services.sector_prepopulator import gather_sector_summary
from app.services.visura_extractor import extract_visura_text


class DescriptionResponse(BaseModel):
    description: str


class DashboardKpis(BaseModel):
    clienti_attivi: int
    sopralluoghi_in_corso: int
    sopralluoghi_completati: int
    bozze: int
    scadenze_imminenti: int
    # B5 — ops-only counter: aziende with a signed survey but no completed
    # DVR yet. Surfaces the gap between "operator finished the sopralluogo"
    # and "documents are actually produced", so dashboards stop claiming
    # 100% Firmato when the documents tab is empty.
    firmati_senza_documenti: int = 0


class SectorAttrezzatura(BaseModel):
    descrizione: str
    count: int


class SectorRischio(BaseModel):
    categoria_rischio: str
    applicabile_count: int
    total: int
    avg_p: float | None = None
    avg_d: float | None = None


class SectorSostanza(BaseModel):
    nome_prodotto: str
    count: int


class SectorSummaryResponse(BaseModel):
    sector_size: int
    ateco_prefix: str | None = None
    attrezzature_by_tipo: dict[str, list[SectorAttrezzatura]]
    rischi_by_tipo: dict[str, list[SectorRischio]]
    top_sostanze: list[SectorSostanza]


router = APIRouter(prefix="/aziende", tags=["aziende"])


def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Solo gli amministratori possono creare clienti",
        )


@router.get("", response_model=list[AziendaResponse])
async def list_aziende(
    search: str | None = Query(None),
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Azienda).where(Azienda.organization_id == org_id)

    if search:
        q = f"%{search}%"
        stmt = stmt.where(
            or_(
                Azienda.ragione_sociale.ilike(q),
                Azienda.partita_iva.ilike(q),
                Azienda.sede_legale_citta.ilike(q),
                Azienda.sede_operativa_citta.ilike(q),
            )
        )

    stmt = stmt.order_by(Azienda.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


# Literal `/dashboard/kpis` must be declared BEFORE any `/{azienda_id}` route
# so FastAPI doesn't try to parse "dashboard" as a UUID (mirrors the
# batch-upload pattern in sostanze_chimiche.py).
@router.get("/dashboard/kpis", response_model=DashboardKpis)
async def dashboard_kpis(
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Return dashboard KPIs for the current org.

    Aggregates azienda survey_status counts and the "scadenze imminenti"
    figure — aziende whose DVR expires within the next 30 days (inclusive)
    and hasn't already expired. US-5.1 acceptance criteria.

    M7 — "clienti_attivi" definition: every azienda row in the org that
    isn't archived/deleted. We don't currently model an archived state so
    in practice this is the same lifetime count as the admin "Clienti
    Creati" stat (users.py /users/stats). The two figures must agree —
    when archival lands (Phase 5) both queries need the same exclusion
    predicate.
    """
    total_stmt = select(func.count(Azienda.id)).where(Azienda.organization_id == org_id)
    total = (await db.execute(total_stmt)).scalar() or 0

    def _count_by_status(status: str):
        return select(func.count(Azienda.id)).where(
            Azienda.organization_id == org_id,
            Azienda.survey_status == status,
        )

    in_progress = (await db.execute(_count_by_status("in_progress"))).scalar() or 0
    # B5 — "completati" must reflect documents-on-disk, not just a flag the
    # operator clicked. We count aziende whose survey is at least signed
    # AND that have at least one DVR Master in completed/ready state. This
    # is the contract the dashboard implicitly promised; the previous
    # implementation reported "Lavanderia completato" while its Documenti
    # tab was empty.
    completed_stmt = (
        select(func.count(func.distinct(Azienda.id)))
        .join(DocumentoGenerato, DocumentoGenerato.azienda_id == Azienda.id)
        .where(
            Azienda.organization_id == org_id,
            Azienda.survey_status.in_(("completed", "firmato")),
            DocumentoGenerato.tipo_documento == "dvr_master",
            DocumentoGenerato.status.in_(("completed", "ready")),
        )
    )
    completed = (await db.execute(completed_stmt)).scalar() or 0

    # Operational gap: signed surveys without a generated DVR yet. Useful
    # to spot stuck/abandoned generations without conflating them with
    # "completati".
    signed_total_stmt = select(func.count(Azienda.id)).where(
        Azienda.organization_id == org_id,
        Azienda.survey_status.in_(("completed", "firmato")),
    )
    signed_total = (await db.execute(signed_total_stmt)).scalar() or 0
    firmati_senza_documenti = max(signed_total - completed, 0)

    drafts = (await db.execute(_count_by_status("draft"))).scalar() or 0

    today = date.today()
    horizon = today + timedelta(days=30)
    scadenze_stmt = select(func.count(Azienda.id)).where(
        Azienda.organization_id == org_id,
        Azienda.data_scadenza_dvr.is_not(None),
        Azienda.data_scadenza_dvr >= today,
        Azienda.data_scadenza_dvr <= horizon,
    )
    scadenze_imminenti = (await db.execute(scadenze_stmt)).scalar() or 0

    return DashboardKpis(
        clienti_attivi=total,
        sopralluoghi_in_corso=in_progress,
        sopralluoghi_completati=completed,
        bozze=drafts,
        scadenze_imminenti=scadenze_imminenti,
        firmati_senza_documenti=firmati_senza_documenti,
    )


class AutofillRequest(BaseModel):
    """Body for POST /aziende/autofill — only takes the P.IVA.

    Validation deliberately NOT shared with AziendaCreate.partita_iva so the
    button can call this with whatever the user typed; we return a 400 with
    a friendly message if it's malformed instead of leaking pydantic chatter.
    """

    partita_iva: str


@router.post("/autofill", response_model=AziendaAutofillResponse)
async def autofill_azienda(
    body: AutofillRequest,
    user: User = Depends(get_current_user),
):
    """Suggest Azienda field values from a P.IVA via VIES + Google + AI.

    Does NOT persist. Frontend takes the response, shows ✨ AI badges per
    field, and posts to ``POST /aziende`` once the operator confirms.

    Privacy: VIES + Serper + Firecrawl + AI consolidator only see public
    web data — same posture as the visura snippet flow. No PII is sent.
    """
    _require_admin(user)
    piva = (body.partita_iva or "").strip()
    if not piva.isdigit() or len(piva) != 11:
        raise BadRequestError("Partita IVA deve essere di 11 cifre")
    return await autofill_from_piva(piva)


@router.post("", response_model=AziendaResponse, status_code=201)
async def create_azienda(
    body: AziendaCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    azienda = Azienda(
        **body.model_dump(),
        organization_id=user.organization_id,
        created_by_user_id=user.id,
    )
    db.add(azienda)
    await db.commit()
    await db.refresh(azienda)
    return azienda


@router.get("/{azienda_id}", response_model=AziendaResponse)
async def get_azienda(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    return azienda


@router.put("/{azienda_id}", response_model=AziendaResponse)
async def update_azienda(
    azienda_id: uuid.UUID,
    body: AziendaUpdate,
    org_id: uuid.UUID = Depends(get_current_org),
    user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")

    payload = body.model_dump(exclude_unset=True)
    # US-2.1 AC2 — snapshot a manual revision when the descrizione_attivita
    # actually changes. We only snapshot non-empty new values to avoid
    # filling the table with empty rows on incidental clears, and we skip
    # the snapshot when the operator isn't actually editing the description
    # (e.g. updating only ATECO + saving). Restored revisions skip this
    # path because they POST to /restore and create their own row.
    new_desc = payload.get("descrizione_attivita")
    if (
        "descrizione_attivita" in payload
        and isinstance(new_desc, str)
        and new_desc.strip()
        and new_desc != (azienda.descrizione_attivita or "")
    ):
        db.add(
            DescriptionRevision(
                azienda_id=azienda.id,
                source=SOURCE_MANUAL,
                content=new_desc,
                generated_by=getattr(user, "id", None),
            )
        )

    for field, value in payload.items():
        setattr(azienda, field, value)

    await db.commit()
    await db.refresh(azienda)
    return azienda


@router.delete("/{azienda_id}", status_code=204)
async def delete_azienda(
    azienda_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    result = await db.execute(
        select(Azienda).where(
            Azienda.id == azienda_id, Azienda.organization_id == user.organization_id
        )
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")

    await db.delete(azienda)
    await db.commit()


@router.post("/{azienda_id}/genera-descrizione", response_model=DescriptionResponse)
async def genera_descrizione(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI company description for DVR Part I (US-2.1).

    Returns the generated text. The caller (frontend editor) is responsible
    for persisting it via PUT /aziende/{id} with descrizione_attivita set.
    This lets the user review/edit before committing.

    Side effect (US-2.1 AC2): every successful AI generation snapshots a
    ``DescriptionRevision`` row tagged ``source='ai'`` so the operator can
    later see "what the AI suggested before I edited" and restore it.
    """
    result = await db.execute(
        select(Azienda)
        .where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
        .options(
            selectinload(Azienda.ambienti),
            selectinload(Azienda.persone),
        )
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")

    description = await generate_company_description(azienda)

    db.add(
        DescriptionRevision(
            azienda_id=azienda.id,
            source=SOURCE_AI,
            content=description,
            generated_by=getattr(user, "id", None),
        )
    )
    await db.commit()
    return DescriptionResponse(description=description)


# ---------------------------------------------------------------------------
# US-2.1 AC1 — Visura camerale upload
# ---------------------------------------------------------------------------

# Mirrors the SDS upload pattern in sostanze_chimiche.py: 10 MB cap, .pdf
# only, content-type tolerant for browsers that send octet-stream.
_VISURA_MAX_BYTES = 10 * 1024 * 1024


@router.post("/{azienda_id}/visura", response_model=VisuraUploadResponse)
async def upload_visura(
    azienda_id: uuid.UUID,
    file: UploadFile = File(...),
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Upload a visura camerale PDF for an azienda (US-2.1 AC1).

    The PDF is persisted under ``FILE_STORAGE_PATH/visure/{azienda_id}/`` and
    a redacted text snippet is cached on the azienda row so the AI prompt
    can use it without re-parsing on every Genera con AI click. PII (codice
    fiscale, email, telefono) is stripped *before* the snippet is stored —
    nothing PII-shaped ever ends up in the column or the AI request body.
    """
    result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")

    filename = file.filename or "visura.pdf"
    is_pdf = (
        file.content_type == "application/pdf"
        or filename.lower().endswith(".pdf")
    )
    if not is_pdf:
        raise BadRequestError("Solo file PDF ammessi")

    content = await file.read()
    if len(content) == 0:
        raise BadRequestError("File vuoto")
    if len(content) > _VISURA_MAX_BYTES:
        raise BadRequestError(
            f"Visura troppo grande (max {_VISURA_MAX_BYTES // (1024 * 1024)} MB)"
        )

    visure_dir = Path(settings.FILE_STORAGE_PATH) / "visure" / str(azienda_id)
    visure_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    file_path = visure_dir / f"{file_id}.pdf"
    file_path.write_bytes(content)

    try:
        extraction = extract_visura_text(file_path)
    except ValueError as exc:
        # Unreadable PDF — clean up the stored file and surface the
        # operator-friendly Italian error.
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise BadRequestError(str(exc)) from exc

    azienda.visura_pdf_path = str(file_path)
    azienda.visura_extracted_text = extraction.snippet
    azienda.visura_uploaded_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(azienda)

    return VisuraUploadResponse(
        visura_uploaded_at=azienda.visura_uploaded_at,
        extracted_chars=extraction.snippet_chars,
        pages=extraction.pages,
    )


# ---------------------------------------------------------------------------
# US-2.1 AC2 — Description revision history
# ---------------------------------------------------------------------------


async def _list_revisions(
    azienda_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> list[DescriptionRevisionResponse]:
    """Shared helper — returns revisions joined with the operator name."""
    # Tenancy guard: ensure the azienda belongs to the current org.
    az_check = await db.execute(
        select(Azienda.id).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    if az_check.scalar_one_or_none() is None:
        raise NotFoundError("Azienda not found")

    rows = await db.execute(
        select(DescriptionRevision, User.full_name)
        .outerjoin(User, User.id == DescriptionRevision.generated_by)
        .where(DescriptionRevision.azienda_id == azienda_id)
        .order_by(DescriptionRevision.created_at.desc())
    )
    out: list[DescriptionRevisionResponse] = []
    for rev, name in rows.all():
        out.append(
            DescriptionRevisionResponse(
                id=rev.id,
                azienda_id=rev.azienda_id,
                source=rev.source,
                content=rev.content,
                generated_by=rev.generated_by,
                generated_by_name=name,
                created_at=rev.created_at,
            )
        )
    return out


@router.get(
    "/{azienda_id}/description-revisions",
    response_model=list[DescriptionRevisionResponse],
)
async def list_description_revisions(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """List the company-description history (US-2.1 AC2).

    Returned newest-first. The frontend ``description-history.tsx`` renders
    one row per revision with an Apri / Ripristina action and the AI/Manual
    badge derived from ``source``.
    """
    return await _list_revisions(azienda_id, org_id, db)


@router.post(
    "/{azienda_id}/description-revisions/{revision_id}/restore",
    response_model=DescriptionRevisionRestoreResponse,
)
async def restore_description_revision(
    azienda_id: uuid.UUID,
    revision_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Restore a historical revision into ``Azienda.descrizione_attivita``.

    Snapshots a fresh ``manual`` revision so the restore itself is part of
    the history (mirrors the US-2.9 document restore semantics — never
    destroy what was there before).
    """
    az_result = await db.execute(
        select(Azienda).where(Azienda.id == azienda_id, Azienda.organization_id == org_id)
    )
    azienda = az_result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")

    rev_result = await db.execute(
        select(DescriptionRevision).where(
            DescriptionRevision.id == revision_id,
            DescriptionRevision.azienda_id == azienda_id,
        )
    )
    source_rev = rev_result.scalar_one_or_none()
    if not source_rev:
        raise NotFoundError("Revisione non trovata")

    azienda.descrizione_attivita = source_rev.content

    new_rev = DescriptionRevision(
        azienda_id=azienda.id,
        source=SOURCE_MANUAL,
        content=source_rev.content,
        generated_by=getattr(user, "id", None),
    )
    db.add(new_rev)
    await db.commit()
    await db.refresh(new_rev)

    return DescriptionRevisionRestoreResponse(
        descrizione_attivita=source_rev.content,
        revision=DescriptionRevisionResponse(
            id=new_rev.id,
            azienda_id=new_rev.azienda_id,
            source=new_rev.source,
            content=new_rev.content,
            generated_by=new_rev.generated_by,
            generated_by_name=getattr(user, "full_name", None),
            created_at=new_rev.created_at,
        ),
    )


@router.get(
    "/{azienda_id}/sector-summary",
    response_model=SectorSummaryResponse,
)
async def sector_summary(
    azienda_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Phase 8.4 — aggregate sector data from prior DVRs in this org.

    Returns counts of typical attrezzature and rischi categories per
    ambiente.tipo, plus the most common sostanze chimiche, drawn from
    other aziende in the same organization that share an ATECO prefix
    (or an exact attivita string when ATECO is missing) AND have at
    least one completed DVR.

    The wizard uses this to offer pre-population suggestions; nothing
    is auto-inserted server-side.
    """
    result = await db.execute(
        select(Azienda).where(
            Azienda.id == azienda_id, Azienda.organization_id == org_id
        )
    )
    azienda = result.scalar_one_or_none()
    if not azienda:
        raise NotFoundError("Azienda not found")
    summary = await gather_sector_summary(azienda, db)
    return summary
