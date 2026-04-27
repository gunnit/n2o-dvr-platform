"""Sector-based pre-population from prior DVRs — Phase 8.4.

When an operator starts (or revises) a survey for an azienda, this service
mines other aziende in the same organization that share a sector signal
(matching codice ATECO prefix or attivita string) AND have at least one
completed DVR. From that cohort it aggregates:

  * the most common attrezzature per ambiente.tipo
  * the most common applicable rischi categorie per ambiente.tipo
    (with average P/D scores)
  * the most common sostanze chimiche

The endpoint returns aggregates only — it does NOT auto-insert anything.
The wizard surfaces suggestions and the operator picks. This preserves the
review-not-data-entry principle.

Multi-tenancy: scope is always the azienda's `organization_id`. We never
mix data across organizations even when the codice ATECO matches.

Privacy: aggregated counts only. No azienda names, no person names, no
company-specific identifiers cross the boundary.
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ambiente import Ambiente
from app.models.attrezzatura import Attrezzatura
from app.models.azienda import Azienda
from app.models.documento_generato import DocumentoGenerato
from app.models.sostanza_chimica import SostanzaChimica
from app.models.valutazione_rischio import ValutazioneRischio


# Treat any DVR document type as a maturity proxy. The first 3 chars of
# the ATECO code (sector level) are the matching key — exact match is too
# narrow (e.g. 56.10.11 vs 56.10.20 are both restaurant variants).
_DVR_TYPES = ("dvr_master",)
_ATECO_PREFIX_LEN = 3
# Cap how many sostanze / attrezzature we emit — anything past the long
# tail is noise the operator wouldn't tick anyway.
_TOP_N_ATTREZZATURE = 12
_TOP_N_SOSTANZE = 8


def _ateco_prefix(codice: str | None) -> str | None:
    if not codice:
        return None
    # Strip any non-alphanumeric (codes vary: "56.10", "5610", "56.10.11").
    digits = "".join(ch for ch in codice if ch.isalnum())
    if len(digits) < _ATECO_PREFIX_LEN:
        return None
    return digits[:_ATECO_PREFIX_LEN]


async def _find_similar_aziende_ids(
    azienda: Azienda, db: AsyncSession
) -> list[uuid.UUID]:
    """Return azienda IDs in the same org with matching sector + a DVR.

    Excludes the input azienda itself so the suggestions don't collapse
    into the operator's own (in-progress) data.
    """
    prefix = _ateco_prefix(azienda.codice_ateco)
    org_id = azienda.organization_id

    # Step 1: aziende in the same org with at least one completed DVR.
    # The completed-DVR filter is what makes them a "good prior" — surveys
    # that were never finished don't get to teach the suggester.
    completed_q = select(DocumentoGenerato.azienda_id).where(
        DocumentoGenerato.tipo_documento.in_(_DVR_TYPES),
        DocumentoGenerato.status == "completed",
    ).distinct()
    result = await db.execute(completed_q)
    completed_azienda_ids = {row[0] for row in result.all()}
    if not completed_azienda_ids:
        return []

    # Step 2: filter by org + sector signal. If we have an ATECO prefix we
    # use it; otherwise fall back to attivita LIKE matching so a brand-new
    # azienda missing ATECO still gets *some* prior. The fallback is wider
    # but the org_id scope keeps the result set bounded.
    base_q = select(Azienda.id, Azienda.codice_ateco, Azienda.attivita).where(
        Azienda.organization_id == org_id,
        Azienda.id != azienda.id,
        Azienda.id.in_(completed_azienda_ids),
    )
    rows = (await db.execute(base_q)).all()

    matches: list[uuid.UUID] = []
    target_attivita = (azienda.attivita or "").strip().lower()
    for row_id, row_ateco, row_attivita in rows:
        row_prefix = _ateco_prefix(row_ateco)
        if prefix and row_prefix == prefix:
            matches.append(row_id)
            continue
        # Fallback: when no ATECO match, accept attivita string equality
        # (case-insensitive). Looser than substring on purpose — substring
        # matches like "bar" inside "bar pasticceria" cause false hits.
        if not prefix and target_attivita and row_attivita:
            if (row_attivita or "").strip().lower() == target_attivita:
                matches.append(row_id)
    return matches


async def gather_sector_summary(
    azienda: Azienda, db: AsyncSession
) -> dict[str, Any]:
    """Aggregate per-sector data from prior aziende's completed DVRs.

    Shape returned (all keys always present):

    ``{
        "sector_size": N,
        "ateco_prefix": "56" | null,
        "attrezzature_by_tipo": { "Cucina": [{descrizione, count}, ...] },
        "rischi_by_tipo": {
            "Cucina": [{categoria_rischio, applicabile_count, total, avg_p, avg_d}],
        },
        "top_sostanze": [{nome_prodotto, count}, ...],
    }``

    If `sector_size == 0` the other dicts/lists are empty and the wizard
    should fall back to its static defaults.
    """
    similar_ids = await _find_similar_aziende_ids(azienda, db)
    summary: dict[str, Any] = {
        "sector_size": len(similar_ids),
        "ateco_prefix": _ateco_prefix(azienda.codice_ateco),
        "attrezzature_by_tipo": {},
        "rischi_by_tipo": {},
        "top_sostanze": [],
    }
    if not similar_ids:
        return summary

    # Pull the full ambiente snapshot for the matched aziende. Eager-load
    # attrezzature + valutazioni_rischio so we don't N+1 over each ambiente
    # in the aggregation loop below.
    ambienti_q = (
        select(Ambiente)
        .where(Ambiente.azienda_id.in_(similar_ids))
        .options(
            selectinload(Ambiente.attrezzature),
            selectinload(Ambiente.valutazioni_rischio),
        )
    )
    ambienti = (await db.execute(ambienti_q)).scalars().all()

    # Bucket equipment counts and risk stats by lowercase ambiente.tipo so
    # the wizard can key off whatever the operator chose for the new env.
    att_counter: dict[str, Counter[str]] = defaultdict(Counter)
    rischio_acc: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(
            lambda: {
                "applicabile_count": 0,
                "total": 0,
                "p_sum": 0,
                "d_sum": 0,
                "p_count": 0,
                "d_count": 0,
            }
        )
    )

    for amb in ambienti:
        tipo = (amb.tipo or "").strip().lower()
        if not tipo:
            continue
        for att in amb.attrezzature or []:
            descr = (att.descrizione or "").strip()
            if not descr:
                continue
            # Normalize on title-case so "Forno" and "forno" don't split.
            att_counter[tipo][descr.title()] += 1
        for r in amb.valutazioni_rischio or []:
            cat = (r.categoria_rischio or "").strip()
            if not cat:
                continue
            slot = rischio_acc[tipo][cat]
            slot["total"] += 1
            if getattr(r, "applicabile", False):
                slot["applicabile_count"] += 1
            if r.probabilita_p is not None:
                slot["p_sum"] += int(r.probabilita_p)
                slot["p_count"] += 1
            if r.danno_d is not None:
                slot["d_sum"] += int(r.danno_d)
                slot["d_count"] += 1

    summary["attrezzature_by_tipo"] = {
        tipo: [
            {"descrizione": descr, "count": count}
            for descr, count in counter.most_common(_TOP_N_ATTREZZATURE)
        ]
        for tipo, counter in att_counter.items()
    }
    summary["rischi_by_tipo"] = {
        tipo: sorted(
            [
                {
                    "categoria_rischio": cat,
                    "applicabile_count": slot["applicabile_count"],
                    "total": slot["total"],
                    "avg_p": (
                        round(slot["p_sum"] / slot["p_count"], 1)
                        if slot["p_count"]
                        else None
                    ),
                    "avg_d": (
                        round(slot["d_sum"] / slot["d_count"], 1)
                        if slot["d_count"]
                        else None
                    ),
                }
                for cat, slot in slots.items()
            ],
            # Most-applicable-first so the wizard can render in priority order.
            key=lambda r: (-r["applicabile_count"], r["categoria_rischio"]),
        )
        for tipo, slots in rischio_acc.items()
    }

    # Sostanze are global to an azienda (no ambiente FK), so aggregate
    # azienda-wide instead of per-tipo.
    sostanze_q = select(SostanzaChimica.nome_prodotto).where(
        SostanzaChimica.azienda_id.in_(similar_ids)
    )
    sostanze_rows = (await db.execute(sostanze_q)).scalars().all()
    sostanze_counter = Counter(
        (n or "").strip().title() for n in sostanze_rows if n
    )
    summary["top_sostanze"] = [
        {"nome_prodotto": name, "count": count}
        for name, count in sostanze_counter.most_common(_TOP_N_SOSTANZE)
        if name
    ]

    return summary
