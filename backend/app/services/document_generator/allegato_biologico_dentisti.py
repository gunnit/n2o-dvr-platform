"""Allegato Rischio Biologico - studio odontoiatrico."""

from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator._biologico_common import build_biologico_document
from app.services.document_generator.reference_data_biologico import (
    DENTISTI_AGENTI, DENTISTI_DPI, DENTISTI_MISURE, DENTISTI_PROTOCOLLO,
)


class AllegatoBiologicoDentistiGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        return await build_biologico_document(
            self,
            settore_key="dentisti",
            titolo="ALLEGATO RISCHIO BIOLOGICO - STUDIO ODONTOIATRICO",
            agenti_default=DENTISTI_AGENTI,
            misure_default=DENTISTI_MISURE,
            dpi_default=DENTISTI_DPI,
            protocollo_default=DENTISTI_PROTOCOLLO,
            tipo_doc="allegato_biologico_dentisti",
            tipo_aliases=["ALLEGATO_BIOLOGICO_DENTISTI"],
        )
