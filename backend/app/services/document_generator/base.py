"""
Abstract base class for all document generators.

Every document type (DVR Master, MMC, VDT, etc.) extends this class
and implements the `generate` method to produce a .docx file.
"""

import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ambiente import Ambiente
from app.models.attrezzatura import Attrezzatura
from app.models.azienda import Azienda
from app.models.organization import Organization
from app.models.persona import Persona
from app.models.sostanza_chimica import SostanzaChimica
from app.models.valutazione_rischio import ValutazioneRischio
from app.services.document_generator.branding import Branding
from app.config import settings


class BaseDocumentGenerator(ABC):
    """Base class for generating workplace safety documents.

    Subclasses must implement the `generate` method which produces
    a .docx file and returns the file path.
    """

    def __init__(
        self,
        azienda_id: uuid.UUID,
        db_session: AsyncSession,
        options: dict | None = None,
    ):
        """Initialize the generator.

        Args:
            azienda_id: UUID of the company to generate the document for.
            db_session: Async SQLAlchemy session for database access.
            options: Optional per-generation config (e.g. HACCP forms
                ``selected_codes``). ``None`` when not supplied.
        """
        self.azienda_id = azienda_id
        self.db = db_session
        # US-4.4: options dict forwarded from the POST body via the
        # DocumentoGenerato.options JSONB column. Generators that don't need
        # per-run config can simply ignore this attribute.
        self.options: dict = options or {}
        # Consultancy branding (logo + letterhead). Defaults to the N2O
        # fallback so generators have a usable value even before load_data()
        # runs — and so the DB-free test harness (which patches load_data)
        # produces unchanged output. Populated per-org in load_data().
        self.branding: Branding = Branding.default()

    @abstractmethod
    async def generate(self) -> str:
        """Generate the document and return the file path.

        Returns:
            Absolute path to the generated .docx file.
        """
        pass

    async def load_data(self) -> dict:
        """Load all azienda data needed for document generation.

        Queries the database for the company and all related entities:
        persone, ambienti (with their risk assessments), attrezzature,
        and sostanze chimiche.

        Returns:
            dict with keys:
                - azienda: Azienda model instance
                - persone: list of Persona instances
                - ambienti: list of Ambiente instances (with valutazioni_rischio loaded)
                - attrezzature: list of Attrezzatura instances
                - sostanze_chimiche: list of SostanzaChimica instances
                - generated_at: datetime of generation

        Raises:
            ValueError: If the azienda_id does not exist in the database.
        """
        # Load azienda
        stmt = select(Azienda).where(Azienda.id == self.azienda_id)
        result = await self.db.execute(stmt)
        azienda = result.scalar_one_or_none()

        if azienda is None:
            raise ValueError(f"Azienda with id {self.azienda_id} not found")

        # Load persone (with ambienti assignments for DVR Parte I grid).
        stmt = (
            select(Persona)
            .where(Persona.azienda_id == self.azienda_id)
            .options(selectinload(Persona.ambienti))
            .order_by(Persona.nominativo)
        )
        result = await self.db.execute(stmt)
        persone = list(result.scalars().all())

        # Load ambienti with their risk assessments + assigned persone
        # (persone needed by DVR Parte III addetti table per env).
        stmt = (
            select(Ambiente)
            .where(Ambiente.azienda_id == self.azienda_id)
            .options(
                # Phase 3 (1:N): hydrate the per-pericolo children so the
                # DVR generator can emit one row per pericolo_valutazione.
                selectinload(Ambiente.valutazioni_rischio).selectinload(
                    ValutazioneRischio.pericoli
                ),
                selectinload(Ambiente.persone),
            )
            .order_by(Ambiente.nome)
        )
        result = await self.db.execute(stmt)
        ambienti = list(result.scalars().all())

        # Load attrezzature
        stmt = (
            select(Attrezzatura)
            .where(Attrezzatura.azienda_id == self.azienda_id)
            .order_by(Attrezzatura.descrizione)
        )
        result = await self.db.execute(stmt)
        attrezzature = list(result.scalars().all())

        # Load sostanze chimiche
        stmt = (
            select(SostanzaChimica)
            .where(SostanzaChimica.azienda_id == self.azienda_id)
            .order_by(SostanzaChimica.nome_prodotto)
        )
        result = await self.db.execute(stmt)
        sostanze_chimiche = list(result.scalars().all())

        # Resolve the consultancy branding for this azienda's organization.
        self.branding = await self._load_branding(azienda)

        return {
            "azienda": azienda,
            "persone": persone,
            "ambienti": ambienti,
            "attrezzature": attrezzature,
            "sostanze_chimiche": sostanze_chimiche,
            "branding": self.branding,
            "generated_at": datetime.now(),
        }

    async def _load_branding(self, azienda) -> Branding:
        """Load per-organization branding for ``azienda``, defensively.

        Any problem (no org_id, missing row, query error) degrades to the N2O
        default so document generation never crashes on branding.
        """
        try:
            org_id = getattr(azienda, "organization_id", None)
            if org_id is None:
                return Branding.default()
            result = await self.db.execute(
                select(Organization).where(Organization.id == org_id)
            )
            org = result.scalar_one_or_none()
            return Branding.from_organization(org)
        except Exception:
            return Branding.default()

    def _get_output_dir(self) -> str:
        """Get the output directory for this azienda, creating it if needed.

        Returns:
            Path to the directory: {FILE_STORAGE_PATH}/documents/{azienda_id}/
        """
        output_dir = os.path.join(
            settings.FILE_STORAGE_PATH, "documents", str(self.azienda_id)
        )
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
