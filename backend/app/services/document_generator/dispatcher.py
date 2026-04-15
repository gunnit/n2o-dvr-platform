"""Dispatch tipo_documento -> generator class.

Each new generator registers here. Called from Celery task.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.document_generator.base import BaseDocumentGenerator


# Lazy imports to keep import graph clean at module load time.
def get_generator_for(
    tipo_documento: str,
    azienda_id: uuid.UUID,
    db: AsyncSession,
    options: dict | None = None,
) -> BaseDocumentGenerator:
    """Return a generator instance for the given tipo_documento string.

    tipo_documento values match DOCUMENT_TYPES keys in reference_data.py:
      DVR_MASTER, ALLEGATO_MMC, ALLEGATO_VDT, ALLEGATO_STRESS, ALLEGATO_GESTANTI,
      ALLEGATO_INCENDIO, ALLEGATO_MICROCLIMA, ALLEGATO_MICROCLIMA_SEVERO,
      ALLEGATO_BIOLOGICO_ALIMENTARE, ALLEGATO_BIOLOGICO_ASILO,
      ALLEGATO_BIOLOGICO_DENTISTI, PEE_AZIENDA, PEE_COMUNE, HACCP,
      HACCP_FORMS, DUVRI, POS.

    The optional ``options`` dict is forwarded to the generator so per-run
    config (e.g. HACCP forms ``selected_codes``) can flow from the API
    request through the Celery task into the generator (US-4.4).
    """
    t = (tipo_documento or "").upper().replace("-", "_")

    if t == "DVR_MASTER":
        from app.services.document_generator.dvr_master import DVRMasterGenerator
        return DVRMasterGenerator(azienda_id, db)

    if t == "ALLEGATO_MMC":
        from app.services.document_generator.allegato_mmc import AllegatoMmcGenerator
        return AllegatoMmcGenerator(azienda_id, db)

    if t == "ALLEGATO_VDT":
        from app.services.document_generator.allegato_vdt import AllegatoVdtGenerator
        return AllegatoVdtGenerator(azienda_id, db)

    if t == "ALLEGATO_STRESS":
        from app.services.document_generator.allegato_stress import AllegatoStressGenerator
        return AllegatoStressGenerator(azienda_id, db)

    if t == "ALLEGATO_GESTANTI":
        from app.services.document_generator.allegato_gestanti import AllegatoGestantiGenerator
        return AllegatoGestantiGenerator(azienda_id, db)

    if t == "ALLEGATO_INCENDIO":
        from app.services.document_generator.allegato_incendio import AllegatoIncendioGenerator
        return AllegatoIncendioGenerator(azienda_id, db)

    if t == "ALLEGATO_MICROCLIMA":
        from app.services.document_generator.allegato_microclima import AllegatoMicroclimaGenerator
        return AllegatoMicroclimaGenerator(azienda_id, db)

    if t == "ALLEGATO_MICROCLIMA_SEVERO":
        from app.services.document_generator.allegato_microclima_severo import AllegatoMicroclimaSeveroGenerator
        return AllegatoMicroclimaSeveroGenerator(azienda_id, db)

    if t == "ALLEGATO_BIOLOGICO_ALIMENTARE":
        from app.services.document_generator.allegato_biologico_alimentare import AllegatoBiologicoAlimentareGenerator
        return AllegatoBiologicoAlimentareGenerator(azienda_id, db)

    if t == "ALLEGATO_BIOLOGICO_ASILO":
        from app.services.document_generator.allegato_biologico_asilo import AllegatoBiologicoAsiloGenerator
        return AllegatoBiologicoAsiloGenerator(azienda_id, db)

    if t == "ALLEGATO_BIOLOGICO_DENTISTI":
        from app.services.document_generator.allegato_biologico_dentisti import AllegatoBiologicoDentistiGenerator
        return AllegatoBiologicoDentistiGenerator(azienda_id, db)

    if t == "PEE_AZIENDA":
        from app.services.document_generator.pee_azienda import PeeAziendaGenerator
        return PeeAziendaGenerator(azienda_id, db)

    if t == "PEE_COMUNE":
        from app.services.document_generator.pee_comune import PeeComuneGenerator
        return PeeComuneGenerator(azienda_id, db)

    if t == "HACCP":
        from app.services.document_generator.haccp_manuale import HaccpManualeGenerator
        return HaccpManualeGenerator(azienda_id, db)

    if t == "HACCP_FORMS":
        from app.services.document_generator.haccp_forms import HaccpFormsGenerator
        # US-4.4: subset selection comes via options.selected_codes.
        return HaccpFormsGenerator(azienda_id, db, options=options)

    if t == "DUVRI":
        from app.services.document_generator.duvri import DuvriGenerator
        return DuvriGenerator(azienda_id, db)

    if t == "POS":
        from app.services.document_generator.pos import PosGenerator
        return PosGenerator(azienda_id, db)

    raise ValueError(f"Unknown tipo_documento: {tipo_documento}")


# The 17 document types exposed on the dashboard (16 documents + HACCP_FORMS bundle as one deliverable).
ALL_DOCUMENT_TYPES: list[str] = [
    "DVR_MASTER",
    "ALLEGATO_MMC",
    "ALLEGATO_VDT",
    "ALLEGATO_STRESS",
    "ALLEGATO_GESTANTI",
    "ALLEGATO_INCENDIO",
    "ALLEGATO_MICROCLIMA",
    "ALLEGATO_MICROCLIMA_SEVERO",
    "ALLEGATO_BIOLOGICO_ALIMENTARE",
    "ALLEGATO_BIOLOGICO_ASILO",
    "ALLEGATO_BIOLOGICO_DENTISTI",
    "PEE_AZIENDA",
    "PEE_COMUNE",
    "HACCP",
    "HACCP_FORMS",
    "DUVRI",
    "POS",
]
