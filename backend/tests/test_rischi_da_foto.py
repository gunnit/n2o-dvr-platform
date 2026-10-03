"""AI risk proposal from the ambiente photos (segnalazione 2026-10-02)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from app.services.ai import rischi_suggester
from app.services.ai.rischi_suggester import RischiSuggeriti, RischioSuggerito
from app.services.ambiente_photo import photos_digest
from app.services.reference_data import RISK_CATEGORY_SHORT_NAMES


def _ambiente():
    return SimpleNamespace(
        id="amb-1", nome="Cucina", tipo="Cucina", descrizione=None,
        descrizione_attivita=None, superficie_mq=None, piano=None,
    )


def _azienda():
    return SimpleNamespace(
        id="az-1", ragione_sociale="Trattoria Rossi", attivita="Ristorazione",
        codice_ateco=None, descrizione_attivita=None,
    )


def test_photo_proposal_sends_the_photos_and_keeps_all_11_categories(monkeypatch, tmp_path):
    seen = {}

    async def fake_extract(image_paths, *, schema, instructions, system, reasoning_effort, **kw):
        seen["paths"] = list(image_paths)
        seen["instructions"] = instructions
        return RischiSuggeriti(
            items=[
                RischioSuggerito(
                    categoria_rischio="Incendio", applicabile=True,
                    pericolo="Friggitrice a gas vicino a carta", probabilita_p=2,
                    danno_d=3, motivazione="Visibile nella foto 1",
                ),
                RischioSuggerito(
                    categoria_rischio="Inventata", applicabile=True, pericolo="x",
                    probabilita_p=1, danno_d=1, motivazione="",
                ),
            ],
            sintesi="Cucina professionale",
        )

    monkeypatch.setattr(rischi_suggester, "extract_from_images", fake_extract)
    foto = tmp_path / "cucina.jpg"
    foto.write_bytes(b"jpeg")

    result = asyncio.run(
        rischi_suggester.suggest_rischi_from_photos(_ambiente(), _azienda(), [], [foto])
    )

    assert seen["paths"] == [foto]
    assert "foto" in seen["instructions"].lower()
    cats = [i.categoria_rischio for i in result.items]
    assert sorted(cats) == sorted(RISK_CATEGORY_SHORT_NAMES)  # unknown dropped, gaps filled
    incendio = next(i for i in result.items if i.categoria_rischio == "Incendio")
    assert incendio.applicabile and "Friggitrice" in incendio.pericolo


def test_photos_digest_is_order_independent_and_changes_with_the_set():
    a, b, c = Path("/x/a.jpg"), Path("/x/b.jpg"), Path("/x/c.jpg")
    assert photos_digest([a, b]) == photos_digest([b, a])
    assert photos_digest([a, b]) != photos_digest([a, b, c])
