"""Allegato Rischio Biologico - settore alimentare (Reg. CE 852/2004)."""

from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator._biologico_common import build_biologico_document
from app.services.document_generator.reference_data_biologico import (
    ALIMENTARE_AGENTI, ALIMENTARE_DPI, ALIMENTARE_MISURE, ALIMENTARE_PROTOCOLLO,
)


class AllegatoBiologicoAlimentareGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        return await build_biologico_document(
            self,
            settore_key="alimentare",
            titolo="ALLEGATO RISCHIO BIOLOGICO ALIMENTARE",
            agenti_default=ALIMENTARE_AGENTI,
            misure_default=ALIMENTARE_MISURE,
            dpi_default=ALIMENTARE_DPI,
            protocollo_default=ALIMENTARE_PROTOCOLLO,
            tipo_doc="allegato_biologico_alimentare",
            tipo_aliases=["ALLEGATO_BIOLOGICO_ALIMENTARE"],
        )
