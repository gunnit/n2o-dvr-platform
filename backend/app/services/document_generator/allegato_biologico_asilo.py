"""Allegato Rischio Biologico - settore asilo nido / scuola infanzia."""

from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator._biologico_common import build_biologico_document
from app.services.document_generator.reference_data_biologico import (
    ASILO_AGENTI, ASILO_DPI, ASILO_MISURE, ASILO_PROTOCOLLO,
)


class AllegatoBiologicoAsiloGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        return await build_biologico_document(
            self,
            settore_key="asilo",
            titolo="ALLEGATO RISCHIO BIOLOGICO - ASILO NIDO / SCUOLA INFANZIA",
            agenti_default=ASILO_AGENTI,
            misure_default=ASILO_MISURE,
            dpi_default=ASILO_DPI,
            protocollo_default=ASILO_PROTOCOLLO,
            tipo_doc="allegato_biologico_asilo",
            tipo_aliases=["ALLEGATO_BIOLOGICO_ASILO"],
        )
