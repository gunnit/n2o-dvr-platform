"""Assessment-data loaders used by multiple generators.

Each function returns a list of model instances for the azienda.
Loads are async, reused across generators to avoid N+1 in Celery task.
"""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.biologico_valutazione import BiologicoValutazione
from app.models.duvri import Duvri
from app.models.gestanti_valutazione import GestantiValutazione
from app.models.haccp_form import HaccpConfig, HaccpFormState
from app.models.incendio_valutazione import IncendioValutazione
from app.models.microclima_valutazione import MicroclimaValutazione
from app.models.mmc_valutazione import MmcValutazione
from app.models.pee_plan import PeePlan
from app.models.pos import Pos
from app.models.stress_valutazione import StressValutazione
from app.models.vdt_valutazione import VdtValutazione


async def load_mmc(db: AsyncSession, azienda_id: uuid.UUID) -> list[MmcValutazione]:
    r = await db.execute(select(MmcValutazione).where(MmcValutazione.azienda_id == azienda_id))
    return list(r.scalars().all())


async def load_vdt(db: AsyncSession, azienda_id: uuid.UUID) -> list[VdtValutazione]:
    r = await db.execute(select(VdtValutazione).where(VdtValutazione.azienda_id == azienda_id))
    return list(r.scalars().all())


async def load_stress(db: AsyncSession, azienda_id: uuid.UUID) -> StressValutazione | None:
    r = await db.execute(select(StressValutazione).where(StressValutazione.azienda_id == azienda_id).limit(1))
    return r.scalar_one_or_none()


async def load_incendio(db: AsyncSession, azienda_id: uuid.UUID) -> list[IncendioValutazione]:
    r = await db.execute(select(IncendioValutazione).where(IncendioValutazione.azienda_id == azienda_id))
    return list(r.scalars().all())


async def load_microclima(db: AsyncSession, azienda_id: uuid.UUID) -> list[MicroclimaValutazione]:
    r = await db.execute(select(MicroclimaValutazione).where(MicroclimaValutazione.azienda_id == azienda_id))
    return list(r.scalars().all())


async def load_gestanti(db: AsyncSession, azienda_id: uuid.UUID) -> list[GestantiValutazione]:
    # selectinload persona so the allegato generator can render
    # `g.persona.nominativo` without triggering MissingGreenlet in the
    # async session. Feedback #32 — without this the lavoratrice's
    # name silently rendered as "—" on every scheda.
    r = await db.execute(
        select(GestantiValutazione)
        .options(selectinload(GestantiValutazione.persona))
        .where(GestantiValutazione.azienda_id == azienda_id)
    )
    return list(r.scalars().all())


async def load_biologico(db: AsyncSession, azienda_id: uuid.UUID, settore: str | None = None) -> list[BiologicoValutazione]:
    stmt = select(BiologicoValutazione).where(BiologicoValutazione.azienda_id == azienda_id)
    if settore:
        stmt = stmt.where(BiologicoValutazione.settore == settore)
    r = await db.execute(stmt)
    return list(r.scalars().all())


async def load_haccp(db: AsyncSession, azienda_id: uuid.UUID) -> tuple[HaccpConfig | None, list[HaccpFormState]]:
    r = await db.execute(select(HaccpConfig).where(HaccpConfig.azienda_id == azienda_id).limit(1))
    config = r.scalar_one_or_none()
    r = await db.execute(
        select(HaccpFormState).where(HaccpFormState.azienda_id == azienda_id).order_by(HaccpFormState.form_code)
    )
    forms = list(r.scalars().all())
    return config, forms


async def load_pee(db: AsyncSession, azienda_id: uuid.UUID, tipo: str = "azienda") -> PeePlan | None:
    r = await db.execute(
        select(PeePlan).where(PeePlan.azienda_id == azienda_id, PeePlan.tipo == tipo).limit(1)
    )
    return r.scalar_one_or_none()


async def load_duvri(db: AsyncSession, azienda_id: uuid.UUID) -> list[Duvri]:
    r = await db.execute(select(Duvri).where(Duvri.azienda_id == azienda_id))
    return list(r.scalars().all())


async def load_pos(db: AsyncSession, azienda_id: uuid.UUID) -> list[Pos]:
    r = await db.execute(select(Pos).where(Pos.azienda_id == azienda_id))
    return list(r.scalars().all())
