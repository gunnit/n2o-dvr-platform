"""Deterministic fingerprinting of an azienda's full survey state (US-5.2).

Used by the document generation pipeline to detect when survey data has
drifted between job-start and job-complete. Two helpers:

* :func:`compute_survey_snapshot_hash` — load the relevant tables and
  return a SHA-256 hex digest of the canonical JSON. Stable: re-running on
  the same DB state yields the same hash regardless of insertion order.

* :func:`mark_documents_stale_for` — convenience used by the survey
  PUT/PATCH endpoints (and tests) to flip ``stale_snapshot=True`` on every
  completed document for an azienda whose survey has changed. We do this
  reactively (on document load) AND proactively (on survey save) so the
  flag is correct regardless of which side of the race the operator hits.

The hash is intentionally NOT cryptographic-strength — collision
resistance is plenty for "did this survey change". SHA-256 is used because
it's already in stdlib + has no false-negative concerns.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ambiente import Ambiente
from app.models.attrezzatura import Attrezzatura
from app.models.azienda import Azienda
from app.models.documento_generato import DocumentoGenerato
from app.models.persona import Persona
from app.models.sostanza_chimica import SostanzaChimica
from app.models.valutazione_rischio import ValutazioneRischio


# Fields that, when changed, should invalidate any downstream document.
# Anything NOT in these lists is treated as immaterial to document
# generation — e.g. ``updated_at`` columns, raw signature PNG bytes, the
# survey lifecycle string ("draft" → "in_progress" doesn't change the
# generated DVR content).
_AZIENDA_FIELDS = (
    "ragione_sociale",
    "partita_iva",
    "sede_legale_via",
    "sede_legale_citta",
    "sede_operativa_via",
    "sede_operativa_citta",
    "attivita",
    "codice_ateco",
    "orario_lavoro",
    "metratura_totale",
    "zona_sismica",
    "descrizione_attivita",
    "contesto_territoriale",
)
_PERSONA_FIELDS = (
    "nominativo",
    "mansione",
    "tipologia_contrattuale",
    "sesso",
    "fascia_eta",
    "ruolo_rspp",
    "ruolo_rls",
    "ruolo_primo_soccorso",
    "ruolo_antincendio",
    "ruolo_preposto",
    "ruolo_datore_lavoro",
)
_AMBIENTE_FIELDS = (
    "nome",
    "tipo",
    "superficie_mq",
    "preposto_id",
    "descrizione_attivita",
)
_ATTREZZATURA_FIELDS = (
    "ambiente_id",
    "descrizione",
    "marcatura_ce",
    "verifiche_periodiche",
)
_SOSTANZA_FIELDS = (
    "nome_prodotto",
    "produttore",
    "destinazione_uso",
    "stato_miscela",
    "pittogrammi",
    "frasi_h",
    "frasi_p",
)
_RISCHIO_FIELDS = (
    "ambiente_id",
    "categoria_rischio",
    "applicabile",
    "pericolo",
    "condizioni_esposizione",
    "rischio",
    "misure_prevenzione",
    "probabilita_p",
    "danno_d",
    "indice_i",
    "livello_rischio",
)


def _row_to_dict(row: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in fields:
        v = getattr(row, f, None)
        if isinstance(v, uuid.UUID):
            v = str(v)
        # Numeric (Decimal) values must be serialised; cast to float for
        # consistency with what the API returns.
        elif hasattr(v, "as_tuple") and hasattr(v, "is_finite"):
            v = float(v)
        out[f] = v
    return out


def _id_or_zero(row: Any) -> str:
    rid = getattr(row, "id", None)
    return str(rid) if rid else ""


def _canonical_json(payload: dict[str, Any]) -> str:
    """``json.dumps`` with sorted keys + UTF-8 + no ASCII escapes.

    Stable across Python versions and across SQLAlchemy load order.
    """
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)


async def compute_survey_snapshot_hash(
    azienda_id: uuid.UUID, db: AsyncSession
) -> str:
    """Compute a deterministic SHA-256 digest of the survey state.

    Loads everything that feeds the document generators (anagrafica,
    ambienti, attrezzature, persone, sostanze, valutazioni rischio) in
    sorted order so the same data set always yields the same digest.

    Returns a 64-char lowercase hex string. Empty surveys (no rows except
    the azienda) still produce a stable hash.
    """
    az = (
        await db.execute(select(Azienda).where(Azienda.id == azienda_id))
    ).scalar_one_or_none()
    if not az:
        return hashlib.sha256(b"missing").hexdigest()

    persone = (
        (
            await db.execute(
                select(Persona).where(Persona.azienda_id == azienda_id)
            )
        )
        .scalars()
        .all()
    )
    ambienti = (
        (
            await db.execute(
                select(Ambiente).where(Ambiente.azienda_id == azienda_id)
            )
        )
        .scalars()
        .all()
    )
    attrezzature = (
        (
            await db.execute(
                select(Attrezzatura).where(Attrezzatura.azienda_id == azienda_id)
            )
        )
        .scalars()
        .all()
    )
    sostanze = (
        (
            await db.execute(
                select(SostanzaChimica).where(SostanzaChimica.azienda_id == azienda_id)
            )
        )
        .scalars()
        .all()
    )
    # Risks are joined to their ambiente, which is azienda-scoped.
    rischi_q = await db.execute(
        select(ValutazioneRischio).join(
            Ambiente, Ambiente.id == ValutazioneRischio.ambiente_id
        ).where(Ambiente.azienda_id == azienda_id)
    )
    rischi = rischi_q.scalars().all()

    payload = {
        "azienda": _row_to_dict(az, _AZIENDA_FIELDS),
        "persone": sorted(
            (_row_to_dict(p, _PERSONA_FIELDS) | {"id": _id_or_zero(p)} for p in persone),
            key=lambda d: d["id"],
        ),
        "ambienti": sorted(
            (_row_to_dict(a, _AMBIENTE_FIELDS) | {"id": _id_or_zero(a)} for a in ambienti),
            key=lambda d: d["id"],
        ),
        "attrezzature": sorted(
            (
                _row_to_dict(a, _ATTREZZATURA_FIELDS) | {"id": _id_or_zero(a)}
                for a in attrezzature
            ),
            key=lambda d: d["id"],
        ),
        "sostanze": sorted(
            (
                _row_to_dict(s, _SOSTANZA_FIELDS) | {"id": _id_or_zero(s)}
                for s in sostanze
            ),
            key=lambda d: d["id"],
        ),
        "rischi": sorted(
            (
                _row_to_dict(r, _RISCHIO_FIELDS) | {"id": _id_or_zero(r)}
                for r in rischi
            ),
            key=lambda d: d["id"],
        ),
    }
    canonical = _canonical_json(payload).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


async def mark_documents_stale_for(
    azienda_id: uuid.UUID, db: AsyncSession
) -> int:
    """Flag every completed document for an azienda whose snapshot drifted.

    Called from the survey PUT/PATCH endpoints once the change has been
    persisted. Returns the number of rows affected (useful in tests + as
    an audit log signal).

    Implementation: compute the live hash, then UPDATE every completed
    document whose ``survey_snapshot_hash`` is non-null and differs.
    Bozza / pending rows are left alone — they're already going to
    re-snapshot when retried.
    """
    live_hash = await compute_survey_snapshot_hash(azienda_id, db)
    result = await db.execute(
        update(DocumentoGenerato)
        .where(
            DocumentoGenerato.azienda_id == azienda_id,
            DocumentoGenerato.status == "completed",
            DocumentoGenerato.survey_snapshot_hash.is_not(None),
            DocumentoGenerato.survey_snapshot_hash != live_hash,
            DocumentoGenerato.stale_snapshot.is_(False),
        )
        .values(stale_snapshot=True)
    )
    return result.rowcount or 0
