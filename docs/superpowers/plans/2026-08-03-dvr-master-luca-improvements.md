# DVR Master Luca Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all eleven approved Luca corrections in DVR Master, prove the resulting DOCX/PDF faithfully renders saved data, and deploy the exact verified Git commit to the production API and worker.

**Architecture:** Keep the behavior DVR-specific while adding one database-backed normalized photo derivative that bridges Render's separate API and worker disks. Normalize DVR input once, render from explicit pure helpers, synchronize child-risk parent state as defense in depth, and isolate all page-layout changes inside the DVR generator.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, PostgreSQL, Celery/Redis, python-docx, Pillow, pillow-heif 1.5.0, pytest/pytest-asyncio, LibreOffice, Poppler, GitHub Actions, Render.

## Global Constraints

- Scope every branding, ordering, grouping, content, and layout change to `DVRMasterGenerator`; MMC, VDT, HACCP, POS, DUVRI, PEE, and every other generator retain their existing behavior.
- Preserve the N2O risk-index invariant `I = 2*D + P`; call the existing `calculate_risk_index` implementation and do not introduce a second formula.
- Preserve Luca's exact tagline: `Valutazione Evoluta dei Rischi Aziendali`.
- Do not commit Luca's email attachments, annotated screenshots, generated customer documents, temporary images, browser downloads, or credentials.
- Do not send workplace photos, identity data, codice fiscale values, or health data to an AI service.
- Continue accepting at most 10 original JPG, PNG, or HEIC photos per environment, each at most 10 MB.
- Normalize document derivatives to JPEG, longest edge at most 2000 pixels without enlargement, initial quality 88, and final payload at most 3 MB.
- Prefer normalized database bytes in the worker and use the legacy local path only as a local-development or unmigrated-installation fallback.
- A missing or undecodable legacy photo must not abort generation; render a filename-specific unavailable marker and log photo UUID plus a sanitized filename.
- Saved people and environment order is `(ordine, created_at, id)`, with null order values after valid values.
- An external safety consultant is exactly `is_esterno AND (ruolo_rspp OR ruolo_medico_competente)`.
- Use the full people list for safety roles, emergency roles, declaration, and signatures; use the filtered employee list for occupational rows, worker counts, worker thresholds, training, environment assignments, and person-specific risks.
- With child hazards present, applicable children are authoritative and there is no parent fallback when every child is disabled; a childless applicable parent remains a supported legacy source.
- Every level-2 DVR topic receives one separator page; level-3 subsections remain inline.
- The employer declaration content starts on a fresh page after its separator, and every signature row has at least 3 cm signing height and cannot split.
- Deployment is complete only after GitHub CI is green, `origin/main` equals the reviewed merge SHA, both Render services deploy that exact SHA, production generation succeeds, and bounded post-deploy logs contain no new error for the smoke generation.

---

## File Structure

- Create `backend/assets/n2o_vera_dvr.png`: cleaned DVR-only cover image derived from Luca's attachment.
- Create `backend/app/services/ambiente_photo.py`: pure image normalization plus legacy-photo database backfill shared by upload and document-generation endpoints.
- Create `backend/alembic/versions/a9b0c1d2e3f4_add_document_image_to_ambiente_foto.py`: additive nullable photo-derivative migration.
- Create `backend/tests/test_dvr_luca_improvements.py`: DVR-only ordering, consultant classification, equipment, cover, risks, person rows, DPI, layout, improvement, and declaration regression tests.
- Create `backend/tests/test_ambiente_photo.py`: image normalization, upload transaction, content fallback, and legacy backfill tests.
- Create `backend/tests/test_pericoli_parent_sync.py`: child CRUD and replace-all synchronization tests.
- Create `backend/scripts/verify_dvr_luca_fixture.py`: deterministic local integration fixture and structural DOCX audit; all generated files are written outside the repository.
- Modify `backend/app/services/document_generator/dvr_master.py`: DVR normalization, faithful rendering, and topic/page layout.
- Modify `backend/app/models/ambiente_foto.py`: two nullable derivative columns.
- Modify `backend/app/api/v1/ambienti.py`: normalize uploads, clean up failed writes, and serve database fallback bytes.
- Modify `backend/app/api/v1/documents.py`: run the DVR photo preflight before every single or batch dispatch.
- Modify `backend/app/api/v1/pericoli.py`: synchronize parent applicability after every child write path.
- Modify `backend/requirements.txt`: pin `pillow-heif==1.5.0`.
- Modify `backend/tests/test_dvr_persona_dpi_rischi.py`: replace obsolete role-union expectations with per-person expectations while preserving DPI-per-role coverage.
- Modify `backend/tests/test_generators.py`: update the seven-column improvement-table contract and retain all-generator regression coverage.

---

### Task 1: Clean DVR-only VERA asset and cover

**Files:**
- Create: `backend/assets/n2o_vera_dvr.png`
- Create: `backend/tests/test_dvr_luca_improvements.py`
- Modify: `backend/app/services/document_generator/dvr_master.py` (`_add_cover_page`)

**Interfaces:**
- Consumes: Luca's source attachment at `/tmp/luca-dvr-master.MVo8Lz/Progetto senza titolo.png`, SHA-256 `d7dee7636231486729ca46f36795263f934f8d9546c9adcd2fd4a94592ba1656`.
- Produces: module constant `_DVR_VERA_LOGO_PATH: Path`; `_add_vera_logo(doc: Document) -> None`; `_add_cover_page(doc: Document, azienda, generated_at: datetime, version: int) -> None` embeds only that asset and falls back to `[LOGO N2O VERA NON DISPONIBILE]`.

- [ ] **Step 1: Write the failing cover regression test**

```python
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _new_generator() -> DVRMasterGenerator:
    return DVRMasterGenerator.__new__(DVRMasterGenerator)


def _cover_azienda():
    return SimpleNamespace(
        ragione_sociale="AZIENDA TEST SRL",
        sede_legale_via="Via Test 1",
        sede_legale_citta="Roma",
        cap_legale="00100",
        provincia_legale="RM",
        partita_iva="00000000000",
        codice_ateco="00.00.00",
    )


def _all_text(doc: Document) -> str:
    paragraph_text = [paragraph.text for paragraph in doc.paragraphs]
    table_text = [cell.text for table in doc.tables for row in table.rows for cell in row.cells]
    return "\n".join(paragraph_text + table_text)


def test_dvr_cover_embeds_vera_asset_and_omits_consultancy(tmp_path):
    gen = _new_generator()
    gen.branding = Branding(
        firm_name="CONSULTANCY SENTINEL",
        indirizzo="SENTINEL ADDRESS",
        logo_bytes=(BACKEND_ROOT / "assets" / "logo.png").read_bytes(),
        logo_content_type="image/png",
    )
    doc = Document()
    gen._add_cover_page(doc, _cover_azienda(), datetime(2026, 8, 3), 1)
    target = tmp_path / "cover.docx"
    doc.save(target)

    with ZipFile(target) as archive:
        media = [archive.read(name) for name in archive.namelist() if name.startswith("word/media/")]
    expected = (BACKEND_ROOT / "assets" / "n2o_vera_dvr.png").read_bytes()
    assert expected in media
    assert (BACKEND_ROOT / "assets" / "logo.png").read_bytes() not in media
    text = _all_text(doc)
    assert "DOCUMENTO DI VALUTAZIONE DEI RISCHI" in text
    assert "Documento elaborato da" not in text
    assert "CONSULTANCY SENTINEL" not in text
```

- [ ] **Step 2: Run the cover test and verify it fails because the DVR-specific asset does not exist or is not embedded**

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_dvr_luca_improvements.py::test_dvr_cover_embeds_vera_asset_and_omits_consultancy -q`

Expected: FAIL on the missing `backend/assets/n2o_vera_dvr.png` or because the current cover embeds configured organization branding.

- [ ] **Step 3: Generate and inspect the cleaned asset**

Use the image-generation editor with the source attachment as the only referenced image and this exact instruction:

```text
Edit this image in place. Remove only the small Gemini watermark/sparkle at the far right of the tagline. Reconstruct the plain white background beneath it. Preserve every other pixel as closely as possible: the N2O flame, silver N2O wordmark, green and red bars, VERA lettering, exact tagline "Valutazione Evoluta dei Rischi Aziendali", canvas proportions, colors, and white background. Do not redesign, sharpen, recolor, retype, crop, resize, or add anything.
```

Copy the accepted output to `backend/assets/n2o_vera_dvr.png`. Inspect the source and result at original resolution. Use an image-difference mask to confirm changed pixels are confined to the Gemini-mark region; reject any result that changes the logo, tagline glyphs, dimensions, or colors.

- [ ] **Step 4: Implement the DVR-only cover source and visible failure marker**

```python
_DVR_VERA_LOGO_PATH = Path(__file__).resolve().parents[3] / "assets" / "n2o_vera_dvr.png"


def _add_vera_logo(self, doc: Document) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    try:
        run.add_picture(str(_DVR_VERA_LOGO_PATH), width=Inches(4.8))
    except Exception:
        run.text = "[LOGO N2O VERA NON DISPONIBILE]"
        run.font.size = Pt(14)
        run.font.italic = True
        run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
```

Call `self._add_vera_logo(doc)` where the current branding logo block sits. Retain the existing title, legal subtitle, company identity, revision, and date code byte-for-byte except for spacing needed by the wider VERA image. Delete the consultancy block at the end of `_add_cover_page`. Remove the now-unused branding imports from this file only. Do not change `branding.py`, `backend/assets/logo.png`, or any other generator.

- [ ] **Step 5: Run the focused cover and shared branding tests**

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_dvr_luca_improvements.py::test_dvr_cover_embeds_vera_asset_and_omits_consultancy tests/test_branding.py tests/test_organizations_branding.py -q`

Expected: PASS; shared branding precedence remains green.

- [ ] **Step 6: Commit the asset and cover behavior**

```bash
git add backend/assets/n2o_vera_dvr.png backend/app/services/document_generator/dvr_master.py backend/tests/test_dvr_luca_improvements.py
git commit -m "feat: apply VERA branding to DVR cover"
```

---

### Task 2: Normalize saved order, classify employees, and consolidate global equipment

**Files:**
- Modify: `backend/app/services/document_generator/dvr_master.py` (`generate`, `_load_dvr_extras`, Part I/III helpers, global equipment helper)
- Modify: `backend/tests/test_dvr_luca_improvements.py`

**Interfaces:**
- Consumes: model attributes `ordine`, `created_at`, `id`, `is_esterno`, `ruolo_rspp`, `ruolo_medico_competente`, `ambiente_id`, `descrizione`, `marcatura_ce`, and `verifiche_periodiche`.
- Produces: `_saved_order_key(entity: object) -> tuple[bool, int, float, str]`; `_is_external_safety_consultant(person: object) -> bool`; `_employee_persons(persons: list) -> list`; `_global_equipment_rows(attrezzature: list, ambienti: list) -> list[list[str]]`; `_add_part_i(doc, azienda, persons, employee_persons, attrezzature, sostanze_chimiche, ambienti) -> None`; `_add_ambienti_summary_table(doc, ambienti, employee_persons) -> None`; `_add_env_addetti_table(doc, ambiente, employee_persons) -> None`.

- [ ] **Step 1: Write failing pure-helper and renderer tests**

```python
def test_saved_order_places_null_after_explicit_order_and_uses_stable_ties():
    rows = [
        SimpleNamespace(nome="Zulu", ordine=2, created_at=datetime(2026, 1, 3), id=uuid.UUID(int=3)),
        SimpleNamespace(nome="Alpha", ordine=1, created_at=datetime(2026, 1, 2), id=uuid.UUID(int=2)),
        SimpleNamespace(nome="Beta", ordine=None, created_at=datetime(2026, 1, 1), id=uuid.UUID(int=1)),
    ]
    assert [r.nome for r in sorted(rows, key=_saved_order_key)] == ["Alpha", "Zulu", "Beta"]


def test_external_rspp_and_medico_are_not_employees_but_remain_role_holders():
    internal_rspp = SimpleNamespace(nominativo="Interno", is_esterno=False, ruolo_rspp=True, ruolo_medico_competente=False)
    external_rspp = SimpleNamespace(nominativo="RSPP Esterno", is_esterno=True, ruolo_rspp=True, ruolo_medico_competente=False)
    external_medico = SimpleNamespace(nominativo="Medico Esterno", is_esterno=True, ruolo_rspp=False, ruolo_medico_competente=True)
    employees = _employee_persons([external_medico, internal_rspp, external_rspp])
    assert employees == [internal_rspp]


def test_global_equipment_groups_description_and_orders_environment_names():
    ambienti = [
        SimpleNamespace(id=uuid.UUID(int=1), nome="Reparto B"),
        SimpleNamespace(id=uuid.UUID(int=2), nome="Reparto A"),
    ]
    rows = _global_equipment_rows(
        [
            SimpleNamespace(descrizione=" Trapano   a colonna ", ambiente_id=ambienti[1].id, marcatura_ce=True, verifiche_periodiche=False),
            SimpleNamespace(descrizione="TRAPANO A COLONNA", ambiente_id=ambienti[0].id, marcatura_ce=False, verifiche_periodiche=False),
        ],
        ambienti,
    )
    assert rows == [["TRAPANO A COLONNA", "REPARTO B, REPARTO A", "MISTO", "NO"]]


def test_employee_tables_keep_saved_order_and_external_consultants_keep_roles():
    gen = DVRMasterGenerator.__new__(DVRMasterGenerator)
    internal = SimpleNamespace(
        nominativo="Zulu Interno", mansione="Operaio", is_esterno=False,
        ruolo_datore_lavoro=True, ruolo_rspp=False, ruolo_rls=False,
        ruolo_medico_competente=False, ruolo_primo_soccorso=False,
        ruolo_antincendio=False, ambienti=[], codice_fiscale=None,
        tipologia_contrattuale=None,
    )
    external = SimpleNamespace(
        nominativo="Alpha RSPP", mansione="RSPP", is_esterno=True,
        ruolo_datore_lavoro=False, ruolo_rspp=True, ruolo_rls=False,
        ruolo_medico_competente=False, ruolo_primo_soccorso=False,
        ruolo_antincendio=False, ambienti=[], codice_fiscale=None,
        tipologia_contrattuale=None,
    )
    employees = _employee_persons([internal, external])
    doc = Document()
    gen._add_dati_occupazionali_table(doc, employees)
    gen._add_single_role_title_table(doc, "Responsabile del Servizio di Prevenzione e Protezione", [external])
    assert [row.cells[0].text for row in doc.tables[0].rows[1:]] == ["ZULU INTERNO"]
    assert "ALPHA RSPP (ESTERNO)" in doc.tables[1].cell(1, 0).text
```

- [ ] **Step 2: Run the new tests and verify current alphabetical sorting and duplicate equipment fail them**

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_dvr_luca_improvements.py -k 'saved_order or external_rspp or global_equipment or occupational' -q`

Expected: FAIL because the helpers do not exist, the shared loader order is retained, and global rows are one-for-one.

- [ ] **Step 3: Implement deterministic DVR normalization and employee filtering**

```python
def _saved_order_key(entity: object) -> tuple[bool, int, float, str]:
    order = getattr(entity, "ordine", None)
    created = getattr(entity, "created_at", None)
    created_key = created.timestamp() if created is not None else float("inf")
    return (order is None, order if order is not None else 0, created_key, str(getattr(entity, "id", "")))


def _is_external_safety_consultant(person: object) -> bool:
    return bool(
        getattr(person, "is_esterno", False)
        and (
            getattr(person, "ruolo_rspp", False)
            or getattr(person, "ruolo_medico_competente", False)
        )
    )


def _employee_persons(persons: list) -> list:
    return [person for person in persons if not _is_external_safety_consultant(person)]


def _assigned_employee_persons(ambiente: object, employees: list) -> list:
    ambiente_id = getattr(ambiente, "id", None)
    return [
        person
        for person in employees
        if any(getattr(item, "id", None) == ambiente_id for item in (getattr(person, "ambienti", None) or []))
    ]
```

In `generate`, replace the raw data setup with:

```python
data = dict(await self.load_data())
data["persone"] = sorted(list(data.get("persone") or []), key=_saved_order_key)
data["ambienti"] = sorted(list(data.get("ambienti") or []), key=_saved_order_key)
employee_persons = _employee_persons(data["persone"])
data["employee_persons"] = employee_persons
extras = await self._load_dvr_extras(data)
```

Inside `_load_dvr_extras`, set `employees = data.get("employee_persons", data.get("persone", []))` and use `len(employees)` for worker-count thresholds. Change the Part I call to pass both `data["persone"]` and `employee_persons`; use employees for `_add_dati_occupazionali_table`, employee counts, `_add_servizi_igienico_assistenziali_section`, and `_add_ambienti_summary_table`, but keep the full list for safety/emergency-role tables. Pass employees to Part III, its environment addetti/counts, person-specific risks, DPI, and training. Keep the full list in Part IV for declaration and signatures.

- [ ] **Step 4: Implement global equipment grouping**

```python
def _normalize_equipment_description(value: str | None) -> str:
    collapsed = " ".join((value or "").split()) or "—"
    return collapsed.casefold()


def _mixed_flag(values: list[bool]) -> str:
    unique = set(values)
    return "MISTO" if len(unique) > 1 else ("SI" if True in unique else "NO")


def _global_equipment_rows(attrezzature: list, ambienti: list) -> list[list[str]]:
    environment_position = {item.id: index for index, item in enumerate(ambienti)}
    environment_name = {item.id: (item.nome or "—").upper() for item in ambienti}
    groups: dict[str, dict] = {}
    for source_position, item in enumerate(attrezzature):
        display = " ".join((item.descrizione or "").split()) or "—"
        key = _normalize_equipment_description(display)
        group = groups.setdefault(key, {
            "display": display.upper(),
            "source_position": source_position,
            "environment_ids": [],
            "ce": [],
            "checks": [],
        })
        environment_id = getattr(item, "ambiente_id", None)
        if environment_id not in group["environment_ids"]:
            group["environment_ids"].append(environment_id)
        group["ce"].append(bool(item.marcatura_ce))
        group["checks"].append(bool(item.verifiche_periodiche))

    def group_key(group: dict) -> tuple[int, int]:
        positions = [environment_position.get(item, len(ambienti)) for item in group["environment_ids"]]
        return (min(positions, default=len(ambienti)), group["source_position"])

    rows = []
    for group in sorted(groups.values(), key=group_key):
        ids = sorted(group["environment_ids"], key=lambda item: environment_position.get(item, len(ambienti)))
        names = [environment_name.get(item, "—") for item in ids]
        rows.append([group["display"], ", ".join(dict.fromkeys(names)), _mixed_flag(group["ce"]), _mixed_flag(group["checks"])])
    return rows
```

Feed these rows into the global `_add_attrezzature_table`. Leave `_add_env_attrezzature_table` unchanged.

- [ ] **Step 5: Run the focused ordering/classification/equipment tests and existing DVR tests**

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_dvr_luca_improvements.py -k 'saved_order or external_rspp or global_equipment or occupational' tests/test_dvr_persona_dpi_rischi.py tests/test_document_revision_number.py -q`

Expected: PASS; internal RSPP/Medico remain employees, external consultants remain role holders, and mixed flags render `MISTO`.

- [ ] **Step 6: Commit normalized DVR inputs**

```bash
git add backend/app/services/document_generator/dvr_master.py backend/tests/test_dvr_luca_improvements.py
git commit -m "fix: preserve DVR order and employee semantics"
```

---

### Task 3: Add bounded document-image normalization and upload persistence

**Files:**
- Create: `backend/app/services/ambiente_photo.py`
- Create: `backend/alembic/versions/a9b0c1d2e3f4_add_document_image_to_ambiente_foto.py`
- Create: `backend/tests/test_ambiente_photo.py`
- Modify: `backend/app/models/ambiente_foto.py`
- Modify: `backend/app/api/v1/ambienti.py` (`upload_ambiente_foto`)
- Modify: `backend/requirements.txt`

**Interfaces:**
- Consumes: original upload `bytes` after the existing 10 MB/type checks.
- Produces: `DocumentImageNormalizationError`; `NormalizedDocumentImage(content: bytes, content_type: str)`; `normalize_document_image(content: bytes) -> NormalizedDocumentImage`; nullable `AmbienteFoto.document_image_bytes` and `AmbienteFoto.document_image_content_type`.

- [ ] **Step 1: Write failing JPEG/PNG/HEIC normalization and bound tests**

```python
def _image_bytes(image: Image.Image, image_format: str, **save_kwargs) -> bytes:
    output = BytesIO()
    image.save(output, format=image_format, **save_kwargs)
    return output.getvalue()


@pytest.fixture
def heic_fixture_bytes() -> bytes:
    output = BytesIO()
    pillow_heif.from_pillow(Image.new("RGB", (48, 32), "green")).save(output)
    return output.getvalue()


def test_png_normalizes_to_bounded_white_background_jpeg():
    source_image = Image.new("RGBA", (4000, 1200), (0, 0, 0, 0))
    source = _image_bytes(source_image, "PNG")
    result = normalize_document_image(source)
    assert result.content_type == "image/jpeg"
    assert len(result.content) <= 3 * 1024 * 1024
    with Image.open(BytesIO(result.content)) as image:
        assert image.mode == "RGB"
        assert max(image.size) == 2000
        assert all(channel >= 250 for channel in image.getpixel((0, 0)))


def test_exif_orientation_is_applied():
    source_image = Image.new("RGB", (40, 20), "red")
    exif = Image.Exif()
    exif[274] = 6
    result = normalize_document_image(_image_bytes(source_image, "JPEG", exif=exif))
    with Image.open(BytesIO(result.content)) as image:
        assert image.size == (20, 40)


def test_small_image_is_not_enlarged():
    result = normalize_document_image(_image_bytes(Image.new("RGB", (320, 200), "blue"), "PNG"))
    with Image.open(BytesIO(result.content)) as image:
        assert image.size == (320, 200)


def test_payload_fallback_reduces_dimensions(monkeypatch):
    noisy = Image.effect_noise((2000, 2000), 100).convert("RGB")
    monkeypatch.setattr("app.services.ambiente_photo.MAX_DOCUMENT_IMAGE_BYTES", 200_000)
    result = normalize_document_image(_image_bytes(noisy, "PNG"))
    assert len(result.content) <= 200_000
    with Image.open(BytesIO(result.content)) as image:
        assert max(image.size) < 2000


def test_heic_normalizes_to_jpeg(heic_fixture_bytes):
    result = normalize_document_image(heic_fixture_bytes)
    assert result.content[:2] == b"\xff\xd8"


def test_invalid_image_raises_typed_error():
    with pytest.raises(DocumentImageNormalizationError):
        normalize_document_image(b"not an image")
```

Generate the HEIC fixture during the test with `pillow_heif.from_pillow(image).save(buffer)` so no binary customer asset enters the repository.

- [ ] **Step 2: Run the normalization tests and verify the service/import is absent**

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_ambiente_photo.py -k 'normalize or heic or invalid' -q`

Expected: FAIL with `ModuleNotFoundError` for `app.services.ambiente_photo` or `pillow_heif`.

- [ ] **Step 3: Pin/install HEIF support and implement the pure normalizer**

Add `pillow-heif==1.5.0` directly after Pillow in `backend/requirements.txt`, install it in the ignored project virtualenv, then implement:

```python
MAX_DOCUMENT_IMAGE_BYTES = 3 * 1024 * 1024
MAX_DOCUMENT_IMAGE_EDGE = 2000
MIN_DOCUMENT_IMAGE_EDGE = 640
JPEG_QUALITIES = (88, 82, 76, 70, 64, 58, 52, 46, 40)


class DocumentImageNormalizationError(ValueError):
    pass


@dataclass(frozen=True)
class NormalizedDocumentImage:
    content: bytes
    content_type: str


def normalize_document_image(content: bytes) -> NormalizedDocumentImage:
    register_heif_opener()
    try:
        with Image.open(BytesIO(content)) as opened:
            image = ImageOps.exif_transpose(opened).copy()
    except (OSError, ValueError, UnidentifiedImageError) as exc:
        raise DocumentImageNormalizationError("Immagine non decodificabile") from exc
    image = _flatten_to_rgb(image)
    image.thumbnail((MAX_DOCUMENT_IMAGE_EDGE, MAX_DOCUMENT_IMAGE_EDGE), Image.Resampling.LANCZOS)
    while True:
        for quality in JPEG_QUALITIES:
            output = BytesIO()
            image.save(output, format="JPEG", quality=quality, optimize=True)
            if output.tell() <= MAX_DOCUMENT_IMAGE_BYTES:
                return NormalizedDocumentImage(output.getvalue(), "image/jpeg")
        longest = max(image.size)
        if longest <= MIN_DOCUMENT_IMAGE_EDGE:
            raise DocumentImageNormalizationError("Immagine normalizzata oltre il limite di 3 MB")
        scale = max(MIN_DOCUMENT_IMAGE_EDGE / longest, 0.85)
        image = image.resize(
            (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
            Image.Resampling.LANCZOS,
        )


def _flatten_to_rgb(image: Image.Image) -> Image.Image:
    if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
        foreground = image.convert("RGBA")
        background = Image.new("RGBA", foreground.size, (255, 255, 255, 255))
        background.alpha_composite(foreground)
        return background.convert("RGB")
    return image.convert("RGB")
```

- [ ] **Step 4: Write the failing migration/model and upload-transaction tests**

```python
def test_photo_model_has_nullable_document_derivative_columns():
    table = AmbienteFoto.__table__
    assert table.c.document_image_bytes.nullable is True
    assert table.c.document_image_content_type.nullable is True


def test_photo_migration_upgrades_and_downgrades_disposable_sqlite(monkeypatch):
    migration_path = BACKEND_ROOT / "alembic" / "versions" / "a9b0c1d2e3f4_add_document_image_to_ambiente_foto.py"
    spec = importlib.util.spec_from_file_location("photo_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE ambienti_foto (id INTEGER PRIMARY KEY)")
        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(migration, "op", operations)
        migration.upgrade()
        upgraded = {column["name"] for column in inspect(connection).get_columns("ambienti_foto")}
        assert {"document_image_bytes", "document_image_content_type"} <= upgraded
        migration.downgrade()
        downgraded = {column["name"] for column in inspect(connection).get_columns("ambienti_foto")}
        assert downgraded == {"id"}


@pytest.mark.asyncio
async def test_upload_persists_normalized_bytes(tmp_path, monkeypatch):
    class CountResult:
        def scalar_one(self):
            return 0

    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = CountResult()
    db.add = Mock()
    db.refresh = AsyncMock()
    monkeypatch.setattr(settings, "FILE_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr("app.api.v1.ambienti._get_ambiente_for_org", AsyncMock())
    upload = UploadFile(
        filename="reparto.png",
        file=BytesIO(_image_bytes(Image.new("RGB", (32, 32), "blue"), "PNG")),
        headers={"content-type": "image/png"},
    )
    with patch("app.api.v1.ambienti.normalize_document_image") as normalize:
        normalize.return_value = NormalizedDocumentImage(b"jpeg", "image/jpeg")
        photo = await upload_ambiente_foto(
            uuid.uuid4(), uuid.uuid4(), upload, uuid.uuid4(), db
        )
    assert photo.document_image_bytes == b"jpeg"
    assert photo.document_image_content_type == "image/jpeg"
    assert Path(photo.file_path).read_bytes()


@pytest.mark.asyncio
async def test_upload_removes_only_new_file_when_commit_fails(tmp_path, monkeypatch):
    class CountResult:
        def scalar_one(self):
            return 0

    azienda_id, ambiente_id, org_id, file_id = [uuid.uuid4() for _ in range(4)]
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = CountResult()
    db.add = Mock()
    db.commit.side_effect = RuntimeError("database unavailable")
    monkeypatch.setattr(settings, "FILE_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr("app.api.v1.ambienti._get_ambiente_for_org", AsyncMock())
    monkeypatch.setattr("app.api.v1.ambienti.uuid.uuid4", lambda: file_id)
    upload = UploadFile(
        filename="reparto.png",
        file=BytesIO(_image_bytes(Image.new("RGB", (32, 32), "blue"), "PNG")),
        headers={"content-type": "image/png"},
    )
    with pytest.raises(RuntimeError, match="database unavailable"):
        await upload_ambiente_foto(azienda_id, ambiente_id, upload, org_id, db)
    assert not (tmp_path / "foto_ambienti" / str(ambiente_id) / f"{file_id}.png").exists()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_image_creates_no_row(tmp_path, monkeypatch):
    class CountResult:
        def scalar_one(self):
            return 0

    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = CountResult()
    db.add = Mock()
    monkeypatch.setattr(settings, "FILE_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr("app.api.v1.ambienti._get_ambiente_for_org", AsyncMock())
    upload = UploadFile(
        filename="guasto.jpg",
        file=BytesIO(b"not-an-image"),
        headers={"content-type": "image/jpeg"},
    )
    with pytest.raises(BadRequestError, match="Formato non supportato o file troppo grande"):
        await upload_ambiente_foto(
            uuid.uuid4(), uuid.uuid4(), upload, uuid.uuid4(), db
        )
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_failure_keeps_file_after_successful_commit(tmp_path, monkeypatch):
    class CountResult:
        def scalar_one(self):
            return 0

    azienda_id, ambiente_id, org_id, file_id = [uuid.uuid4() for _ in range(4)]
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = CountResult()
    db.add = Mock()
    db.refresh.side_effect = RuntimeError("refresh failed")
    monkeypatch.setattr(settings, "FILE_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr("app.api.v1.ambienti._get_ambiente_for_org", AsyncMock())
    monkeypatch.setattr("app.api.v1.ambienti.uuid.uuid4", lambda: file_id)
    upload = UploadFile(
        filename="reparto.png",
        file=BytesIO(_image_bytes(Image.new("RGB", (32, 32), "blue"), "PNG")),
        headers={"content-type": "image/png"},
    )
    with pytest.raises(RuntimeError, match="refresh failed"):
        await upload_ambiente_foto(azienda_id, ambiente_id, upload, org_id, db)
    assert (tmp_path / "foto_ambienti" / str(ambiente_id) / f"{file_id}.png").exists()
    db.rollback.assert_not_awaited()
```

These tests use generated pixels only; no attachment bytes enter the fixture.

- [ ] **Step 5: Add the model fields, reversible migration, and transactional upload integration**

```python
document_image_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
document_image_content_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

Migration revision `a9b0c1d2e3f4` revises `f8a9b0c1d2e3` and uses:

```python
def upgrade() -> None:
    op.add_column("ambienti_foto", sa.Column("document_image_bytes", sa.LargeBinary(), nullable=True))
    op.add_column("ambienti_foto", sa.Column("document_image_content_type", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("ambienti_foto", "document_image_content_type")
    op.drop_column("ambienti_foto", "document_image_bytes")
```

Normalize before writing the original, populate both derivative fields, and use this exact transaction boundary:

```python
try:
    await db.commit()
except Exception:
    await db.rollback()
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Unable to remove uncommitted photo file", extra={"photo_id": str(file_id)})
    raise
await db.refresh(foto)
```

Never unlink after `commit` succeeds, even when `refresh` fails. Map `DocumentImageNormalizationError` to `BadRequestError("Formato non supportato o file troppo grande (max 10 MB)")`.

- [ ] **Step 6: Run photo, migration-head, and schema-drift tests**

Run: `cd backend && LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_ambiente_photo.py tests/test_plan_catalogue.py tests/test_schema_drift_db.py -q`

Run: `cd backend && LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m alembic heads | tee /tmp/dvr-alembic-heads.txt && test "$(wc -l < /tmp/dvr-alembic-heads.txt | tr -d ' ')" = 1 && rg '^a9b0c1d2e3f4 \(head\)$' /tmp/dvr-alembic-heads.txt`

Expected: PASS, or `test_schema_drift_db.py` skips only when its documented PostgreSQL test service is unavailable; `python -m alembic heads` prints only `a9b0c1d2e3f4 (head)`.

- [ ] **Step 7: Commit document-image persistence**

```bash
git add backend/requirements.txt backend/app/services/ambiente_photo.py backend/app/models/ambiente_foto.py backend/app/api/v1/ambienti.py backend/alembic/versions/a9b0c1d2e3f4_add_document_image_to_ambiente_foto.py backend/tests/test_ambiente_photo.py
git commit -m "feat: persist normalized environment photos"
```

---

### Task 4: Backfill legacy photos before dispatch and embed all ten from shared bytes

**Files:**
- Modify: `backend/app/services/ambiente_photo.py`
- Modify: `backend/app/api/v1/ambienti.py` (`get_ambiente_foto_content`)
- Modify: `backend/app/api/v1/documents.py` (`generate_document`, `batch_generate_documents`)
- Modify: `backend/app/services/document_generator/dvr_master.py` (`_add_env_foto_block`)
- Modify: `backend/tests/test_ambiente_photo.py`
- Modify: `backend/tests/test_dvr_luca_improvements.py`

**Interfaces:**
- Consumes: `normalize_document_image(content: bytes) -> NormalizedDocumentImage` from Task 3.
- Produces: `PhotoBackfillResult(attempted: int, stored: int, unavailable: int, failed: int)`; `backfill_document_images_for_dvr(azienda_id: UUID, db: AsyncSession) -> PhotoBackfillResult`; `_preflight_dvr_photo_transport(azienda_id: UUID, requested_types: Collection[str], db: AsyncSession) -> PhotoBackfillResult | None`; `_photo_image_sources(photo: object) -> list[BytesIO | str]`.

- [ ] **Step 1: Write failing backfill, endpoint fallback, and dispatch tests**

```python
@pytest.mark.asyncio
async def test_backfill_reads_legacy_api_disk_and_commits_before_return(tmp_path):
    class ScalarRows:
        def __init__(self, rows):
            self.rows = rows

        def scalars(self):
            return self

        def all(self):
            return self.rows

    source = tmp_path / "legacy.png"
    source.write_bytes(_image_bytes(Image.new("RGB", (64, 32), "blue"), "PNG"))
    photo = SimpleNamespace(
        id=uuid.uuid4(),
        filename="legacy.png",
        file_path=str(source),
        document_image_bytes=None,
        document_image_content_type=None,
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = ScalarRows([photo])
    result = await backfill_document_images_for_dvr(uuid.uuid4(), db)
    assert result == PhotoBackfillResult(attempted=1, stored=1, unavailable=0, failed=0)
    assert photo.document_image_bytes.startswith(b"\xff\xd8")
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_photo_content_falls_back_to_database_bytes_when_disk_is_missing(tmp_path):
    class OneRow:
        def __init__(self, row):
            self.row = row

        def scalar_one_or_none(self):
            return self.row

    photo = SimpleNamespace(
        id=uuid.uuid4(),
        filename="foto.jpg",
        file_path=str(tmp_path / "missing.jpg"),
        content_type="image/jpeg",
        document_image_bytes=b"jpeg-from-db",
        document_image_content_type="image/jpeg",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = OneRow(photo)
    ids = [uuid.uuid4() for _ in range(3)]
    with patch("app.api.v1.ambienti._get_ambiente_for_org", new=AsyncMock()):
        response = await get_ambiente_foto_content(ids[0], ids[1], photo.id, ids[2], db)
    assert isinstance(response, Response)
    assert response.body == photo.document_image_bytes
    assert response.media_type == "image/jpeg"


@pytest.mark.asyncio
async def test_preflight_calls_backfill_only_when_dvr_is_requested():
    db = AsyncMock(spec=AsyncSession)
    azienda_id = uuid.uuid4()
    result = PhotoBackfillResult(1, 1, 0, 0)
    with patch(
        "app.api.v1.documents.backfill_document_images_for_dvr",
        new=AsyncMock(return_value=result),
    ) as backfill:
        assert await _preflight_dvr_photo_transport(
            azienda_id, ["dvr_master", "allegato_vdt"], db
        ) == result
        assert await _preflight_dvr_photo_transport(
            azienda_id, ["allegato_vdt"], db
        ) is None
    backfill.assert_awaited_once_with(azienda_id, db)


def test_single_and_batch_routes_preflight_before_dispatch():
    for endpoint in (generate_document, batch_generate_documents):
        source = inspect.getsource(endpoint)
        assert source.index("await _preflight_dvr_photo_transport") < source.index("_enqueue_generation")
```

Exercise single `dvr_master`, batch containing `dvr_master`, single non-DVR, and batch without DVR. Assert preflight is called exactly once only for requests that include DVR.

- [ ] **Step 2: Run the new API/backfill tests and verify they fail**

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_ambiente_photo.py -k 'backfill or falls_back or preflight' -q`

Expected: FAIL because the backfill helper and database response path do not exist.

- [ ] **Step 3: Implement bounded legacy backfill and endpoint fallback**

```python
@dataclass(frozen=True)
class PhotoBackfillResult:
    attempted: int
    stored: int
    unavailable: int
    failed: int


async def backfill_document_images_for_dvr(
    azienda_id: UUID, db: AsyncSession
) -> PhotoBackfillResult:
    photos = (await db.execute(
        select(AmbienteFoto)
        .join(Ambiente, Ambiente.id == AmbienteFoto.ambiente_id)
        .where(
            Ambiente.azienda_id == azienda_id,
            AmbienteFoto.document_image_bytes.is_(None),
        )
        .order_by(AmbienteFoto.created_at, AmbienteFoto.id)
    )).scalars().all()
    stored = unavailable = failed = 0
    for photo in photos:
        safe_name = Path(photo.filename or str(photo.id)).name[:255]
        source = Path(photo.file_path)
        if not source.is_file():
            unavailable += 1
            logger.warning(
                "Legacy DVR photo file is unavailable",
                extra={"photo_id": str(photo.id), "filename": safe_name},
            )
            continue
        try:
            normalized = normalize_document_image(source.read_bytes())
        except (OSError, DocumentImageNormalizationError):
            failed += 1
            logger.warning(
                "Legacy DVR photo normalization failed",
                extra={"photo_id": str(photo.id), "filename": safe_name},
                exc_info=True,
            )
            continue
        photo.document_image_bytes = normalized.content
        photo.document_image_content_type = normalized.content_type
        stored += 1
    await db.commit()
    return PhotoBackfillResult(len(photos), stored, unavailable, failed)
```

Return the following only when the disk file is absent and bytes exist; preserve `FileResponse` when the original exists and preserve the authenticated tenant checks:

```python
safe_name = quote(Path(foto.filename or str(foto.id)).name)
return Response(
    content=foto.document_image_bytes,
    media_type=foto.document_image_content_type or "image/jpeg",
    headers={"Content-Disposition": f"inline; filename*=UTF-8''{safe_name}"},
)
```

- [ ] **Step 4: Call preflight on both DVR dispatch paths**

Add the shared routing helper:

```python
async def _preflight_dvr_photo_transport(
    azienda_id: uuid.UUID,
    requested_types: Collection[str],
    db: AsyncSession,
) -> PhotoBackfillResult | None:
    if "dvr_master" not in requested_types:
        return None
    return await backfill_document_images_for_dvr(azienda_id, db)
```

In `generate_document`, after authorization/completeness gates and before creating the document row:

```python
await _preflight_dvr_photo_transport(azienda_id, [body.tipo_documento], db)
```

In `batch_generate_documents`, after all batch gates and before creating any rows:

```python
await _preflight_dvr_photo_transport(azienda_id, body.tipi_documento, db)
```

Leave `_enqueue_generation` synchronous and dispatch-only.

- [ ] **Step 5: Write failing renderer tests for ten images and explicit failures**

```python
def _jpeg_bytes(color: str = "blue") -> bytes:
    output = BytesIO()
    Image.new("RGB", (24, 24), color).save(output, "JPEG")
    return output.getvalue()


def test_dvr_embeds_all_ten_database_photos():
    photos = [
        SimpleNamespace(
            id=uuid.uuid4(), filename=f"foto-{index}.jpg",
            document_image_bytes=_jpeg_bytes(), file_path=None,
        )
        for index in range(10)
    ]
    doc = Document()
    _new_generator()._add_env_foto_block(doc, "REPARTO", photos)
    assert len(doc.inline_shapes) == 10
    assert "Fig. 10 — foto-9.jpg" in _all_text(doc)


def test_dvr_renders_one_filename_specific_marker_per_unavailable_photo(caplog):
    photos = [
        SimpleNamespace(id=uuid.UUID(int=1), filename="assente-a.heic", document_image_bytes=None, file_path="/private/missing-a.heic"),
        SimpleNamespace(id=uuid.UUID(int=2), filename="assente-b.jpg", document_image_bytes=None, file_path="/private/missing-b.jpg"),
    ]
    doc = Document()
    _new_generator()._add_env_foto_block(doc, "REPARTO", photos)
    text = _all_text(doc)
    assert "[Foto non disponibile: assente-a.heic]" in text
    assert "[Foto non disponibile: assente-b.jpg]" in text
    warnings = [record for record in caplog.records if record.levelno >= logging.WARNING]
    assert {(record.photo_id, record.filename) for record in warnings} == {
        (str(uuid.UUID(int=1)), "assente-a.heic"),
        (str(uuid.UUID(int=2)), "assente-b.jpg"),
    }
    assert all("/private/" not in record.getMessage() for record in warnings)


def test_corrupt_database_derivative_falls_back_to_valid_local_file(tmp_path):
    local = tmp_path / "legacy.jpg"
    local.write_bytes(_jpeg_bytes("green"))
    photo = SimpleNamespace(
        id=uuid.UUID(int=3), filename="legacy.jpg",
        document_image_bytes=b"corrupt", file_path=str(local),
    )
    doc = Document()
    _new_generator()._add_env_foto_block(doc, "REPARTO", [photo])
    assert len(doc.inline_shapes) == 1
    assert "[Foto non disponibile" not in _all_text(doc)
```

- [ ] **Step 6: Run the renderer tests and verify the three-photo truncation fails**

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_dvr_luca_improvements.py -k 'ten_database_photos or filename_specific_marker' -q`

Expected: FAIL because only three local paths are attempted and exceptions are swallowed.

- [ ] **Step 7: Implement shared-byte-first DVR photo rendering**

```python
def _photo_image_sources(photo: object) -> list[BytesIO | str]:
    sources: list[BytesIO | str] = []
    content = getattr(photo, "document_image_bytes", None)
    if content:
        sources.append(BytesIO(content))
    path = getattr(photo, "file_path", None)
    if path and os.path.isfile(path):
        sources.append(path)
    return sources
```

Iterate `foto[:10]`. For each photo, attempt candidates in returned order until one `run.add_picture(source, width=Cm(12))` succeeds; log each failed candidate with photo UUID and sanitized basename, but continue to the disk candidate. Caption a successful photo once. If every candidate fails or the list is empty, add `[Foto non disponibile: {sanitized_basename}]` and one warning when no candidate previously produced a warning. Never log paths or bytes, and do not collapse multiple unavailable photos into one marker.

```python
embedded_count = 0
for photo in foto[:10]:
    safe_name = Path(getattr(photo, "filename", None) or str(photo.id)).name[:255]
    embedded = False
    warned = False
    for source in _photo_image_sources(photo):
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        try:
            paragraph.add_run().add_picture(source, width=Cm(12))
        except Exception:
            paragraph._element.getparent().remove(paragraph._element)
            warned = True
            logger.warning(
                "DVR photo candidate could not be embedded",
                extra={"photo_id": str(photo.id), "filename": safe_name},
                exc_info=True,
            )
            continue
        embedded = True
        embedded_count += 1
        caption = doc.add_paragraph(f"Fig. {embedded_count} — {safe_name}")
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        break
    if embedded:
        continue
    doc.add_paragraph(f"[Foto non disponibile: {safe_name}]")
    if not warned:
        logger.warning(
            "DVR photo unavailable",
            extra={"photo_id": str(photo.id), "filename": safe_name},
        )
```

- [ ] **Step 8: Run all photo and focused DVR tests**

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_ambiente_photo.py tests/test_dvr_luca_improvements.py -k 'photo or foto or preflight or content' -q`

Expected: PASS, including generated HEIC derivative embedding.

- [ ] **Step 9: Commit the cross-service photo bridge**

```bash
git add backend/app/services/ambiente_photo.py backend/app/api/v1/ambienti.py backend/app/api/v1/documents.py backend/app/services/document_generator/dvr_master.py backend/tests/test_ambiente_photo.py backend/tests/test_dvr_luca_improvements.py
git commit -m "fix: render DVR photos across service disks"
```

---

### Task 5: Emit every effective risk, retain person identity, and align DPI placeholders

**Files:**
- Create: `backend/tests/test_pericoli_parent_sync.py`
- Modify: `backend/app/services/document_generator/dvr_master.py`
- Modify: `backend/app/api/v1/pericoli.py`
- Modify: `backend/tests/test_dvr_luca_improvements.py`
- Modify: `backend/tests/test_dvr_persona_dpi_rischi.py`

**Interfaces:**
- Consumes: `ValutazioneRischio.pericoli`, child/parent `applicabile`, saved employee list from Task 2, existing reference catalogs and risk calculator.
- Produces: `_effective_risk_sources(parent: object) -> list`; `_lock_parent(rischio_id: UUID, ambiente_id: UUID, db: AsyncSession) -> ValutazioneRischio`; `_sync_parent_applicabile(parent: ValutazioneRischio, db: AsyncSession) -> None`; person table headers `Nominativo | Mansione | Rischio specifico`.

- [ ] **Step 1: Write failing effective-risk tests**

```python
def test_parent_false_applicable_children_are_effective_in_relationship_order():
    parent = SimpleNamespace(
        applicabile=False,
        pericoli=[
            SimpleNamespace(pericolo="A", applicabile=True),
            SimpleNamespace(pericolo="B", applicabile=False),
            SimpleNamespace(pericolo="C", applicabile=True),
        ],
    )
    assert [row.pericolo for row in _effective_risk_sources(parent)] == ["A", "C"]


def test_all_disabled_children_do_not_resurrect_parent():
    parent = SimpleNamespace(
        applicabile=True,
        pericoli=[SimpleNamespace(pericolo="A", applicabile=False)],
    )
    assert _effective_risk_sources(parent) == []


def test_childless_applicable_parent_remains_effective():
    parent = SimpleNamespace(applicabile=True, pericoli=[])
    assert _effective_risk_sources(parent) == [parent]


def test_parent_false_applicable_children_render_once_and_mark_checklist_yes():
    applicable = SimpleNamespace(
        pericolo="CHILD APPLICABLE SENTINEL", applicabile=True,
        condizioni_esposizione="COND", rischio="RISK", misure_prevenzione="MEASURE",
        probabilita_p=2, danno_d=3, livello_rischio="GRAVE",
    )
    disabled = SimpleNamespace(pericolo="CHILD DISABLED SENTINEL", applicabile=False)
    parent = SimpleNamespace(
        categoria_rischio="Macchine", applicabile=False,
        pericoli=[applicable, disabled],
    )
    ambiente = SimpleNamespace(valutazioni_rischio=[parent])
    doc = Document()
    gen = _new_generator()
    gen._add_env_risk_checklist(doc, ambiente)
    gen._add_env_risk_tables(doc, ambiente)
    text = _all_text(doc)
    assert text.count("CHILD APPLICABLE SENTINEL") == 1
    assert "CHILD DISABLED SENTINEL" not in text
    assert any("SI" in cell.text for table in doc.tables for row in table.rows for cell in row.cells)
```

- [ ] **Step 2: Run risk tests and verify the current parent-first filter fails**

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_dvr_luca_improvements.py -k 'effective or applicable_children or disabled_children' -q`

Expected: FAIL because the current renderer discards a false parent before reading children and falls back to parent when all children are disabled.

- [ ] **Step 3: Implement and use one effective-source helper**

```python
def _effective_risk_sources(parent: object) -> list:
    children = list(getattr(parent, "pericoli", None) or [])
    if children:
        return [child for child in children if getattr(child, "applicabile", False)]
    return [parent] if getattr(parent, "applicabile", False) else []
```

Use the same computed map in both renderer paths:

```python
effective_by_parent = {
    id(parent): _effective_risk_sources(parent)
    for parent in (getattr(ambiente, "valutazioni_rischio", None) or [])
}
applicable_categories = {
    parent.categoria_rischio
    for parent in (getattr(ambiente, "valutazioni_rischio", None) or [])
    if effective_by_parent[id(parent)]
}
```

The checklist marks a category `SI` only when it is in `applicable_categories`. The risk-table loop skips parents with an empty effective list and iterates `effective_by_parent[id(parent)]` otherwise. Keep VDT synthetic rows independent and preserve the existing `calculate_risk_index(probabilita_p, danno_d)` call for each emitted row.

- [ ] **Step 4: Write failing parent-sync tests for create, update, delete, and batch replacement**

```python
@pytest.mark.asyncio
@pytest.mark.parametrize("count, expected", [(1, True), (0, False)])
async def test_sync_parent_uses_persisted_applicable_child_count(count, expected):
    class CountResult:
        def scalar_one(self):
            return count

    parent = SimpleNamespace(id=uuid.uuid4(), applicabile=not expected)
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = CountResult()
    await _sync_parent_applicabile(parent, db)
    db.flush.assert_awaited_once()
    assert parent.applicabile is expected


def test_every_child_write_endpoint_locks_parent_then_syncs_before_commit():
    endpoints = (
        create_pericolo_valutazione,
        update_pericolo_valutazione,
        delete_pericolo_valutazione,
        batch_upsert_pericoli,
    )
    for endpoint in endpoints:
        source = inspect.getsource(endpoint)
        assert source.index("parent = await _lock_parent") < source.index("await _sync_parent_applicabile")
        assert source.index("await _sync_parent_applicabile") < source.index("await db.commit()")
```

- [ ] **Step 5: Implement parent synchronization inside every transaction**

```python
async def _lock_parent(
    rischio_id: uuid.UUID,
    ambiente_id: uuid.UUID,
    db: AsyncSession,
) -> ValutazioneRischio:
    parent = (await db.execute(
        select(ValutazioneRischio)
        .where(
            ValutazioneRischio.id == rischio_id,
            ValutazioneRischio.ambiente_id == ambiente_id,
        )
        .with_for_update()
    )).scalar_one_or_none()
    if parent is None:
        raise NotFoundError("Valutazione rischio not found")
    return parent


async def _sync_parent_applicabile(
    parent: ValutazioneRischio,
    db: AsyncSession,
) -> None:
    await db.flush()
    any_applicable = bool((await db.execute(
        select(func.count(PericoloValutazione.id)).where(
            PericoloValutazione.valutazione_rischio_id == parent.id,
            PericoloValutazione.applicabile.is_(True),
        )
    )).scalar_one())
    parent.applicabile = any_applicable
```

In every child endpoint, replace the initial `_verify_valutazione` call with `parent = await _lock_parent(rischio_id, ambiente_id, db)` before mutating children. Call `_sync_parent_applicabile(parent, db)` after mutation and before commit. The parent row lock serializes competing child transactions; the helper's flush makes deletes and replace-all batches visible to the count. Do not change parent-only endpoints.

- [ ] **Step 6: Replace the obsolete role-union test with person-level risk tests**

```python
def test_specific_risks_render_one_row_per_exposed_person_without_cross_inheritance():
    mario = _FakePersona("p1", "Mario Rossi", "Operaio", rischi_specifici_codes=["af_rumore"])
    anna = _FakePersona("p2", "Anna Bianchi", "Operaio", rischi_specifici_codes=["mmc"])
    doc = Document()
    _new_generator()._add_mansioni_rischi_specifici_section(doc, [mario, anna], {"vdt_esposti_persona_ids": set()})
    table = doc.tables[-1]
    assert [cell.text for cell in table.rows[0].cells] == ["Nominativo", "Mansione", "Rischio specifico"]
    assert [cell.text for cell in table.rows[1].cells][:2] == ["MARIO ROSSI", "OPERAIO"]
    assert "Rumore" in table.rows[1].cells[2].text and "Movimentazione" not in table.rows[1].cells[2].text
    assert [cell.text for cell in table.rows[2].cells][:2] == ["ANNA BIANCHI", "OPERAIO"]
    assert "Movimentazione" in table.rows[2].cells[2].text and "Rumore" not in table.rows[2].cells[2].text
```

Retain the existing DPI-per-mansione union tests because request 7 changes only the specific-risk table.

- [ ] **Step 7: Implement one person row per exposed employee**

```python
_ATTREZZATURA_RISK_LABELS = {
    "lavori_in_quota": "Lavori in quota",
    "trabattelli": "Utilizzo di trabattelli",
    "ponteggi": "Utilizzo di ponteggi",
    "carrello_elevatore": "Utilizzo di carrelli elevatori",
    "ple": "Utilizzo di piattaforme di lavoro elevabili (PLE)",
    "gru": "Utilizzo di gru",
    "ruspa_escavatore": "Utilizzo di ruspe ed escavatori",
    "patente_cde": "Guida professionale (patente C/D/E)",
    "adr": "Trasporto merci pericolose (ADR)",
}


def _person_specific_risk_labels(person: object, vdt_ids: set) -> list[str]:
    from app.services.reference_data import RISCHI_SPECIFICI_CATALOG

    labels: list[str] = []

    def add(label: str) -> None:
        if label and label not in labels:
            labels.append(label)

    if getattr(person, "id", None) in vdt_ids:
        add("Videoterminali")
    for code in getattr(person, "attrezzature_speciali", None) or []:
        add(_ATTREZZATURA_RISK_LABELS.get(code, code))
    for code in getattr(person, "rischi_specifici_codes", None) or []:
        item = RISCHI_SPECIFICI_CATALOG.get(code, {})
        add(item.get("etichetta", code))
    return labels
```

In `_add_mansioni_rischi_specifici_section`, replace the mansione union with:

```python
headers = ["Nominativo", "Mansione", "Rischio specifico"]
rows = []
vdt_ids = extras.get("vdt_esposti_persona_ids", set())
for person in persone:
    labels = _person_specific_risk_labels(person, vdt_ids)
    if labels:
        rows.append([
            (person.nominativo or "—").upper(),
            (person.mansione or "—").upper(),
            "; ".join(labels),
        ])
if rows:
    self._add_data_table(doc, headers, rows)
else:
    doc.add_paragraph("Nessun lavoratore esposto a rischi specifici configurato.")
```

Never aggregate through `mansione`.

- [ ] **Step 8: Write and satisfy the targeted DPI placeholder alignment test**

```python
def test_only_dpi_marca_modello_dash_is_centered_both_ways():
    doc = Document()
    _new_generator()._add_dpi_per_mansione_section(doc, [_FakePersona("p", "Mario", "Operaio")], {})
    table = next(
        table
        for table in doc.tables
        if table.rows and "Marca / Modello" in [cell.text.strip() for cell in table.rows[0].cells]
    )
    column = [cell.text.strip() for cell in table.rows[0].cells].index("Marca / Modello")
    dash_cell = table.rows[1].cells[column]
    assert dash_cell.paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert dash_cell.vertical_alignment == WD_CELL_VERTICAL_ALIGNMENT.CENTER
    assert table.rows[1].cells[0].vertical_alignment != WD_CELL_VERTICAL_ALIGNMENT.CENTER
```

Change `_add_data_table` to return the created `Table` without altering any existing caller, and invoke this helper only for DPI tables:

```python
def _center_dpi_brand_model_placeholders(table: Table) -> None:
    headers = [cell.text.strip() for cell in table.rows[0].cells]
    if "Marca / Modello" not in headers:
        return
    column = headers.index("Marca / Modello")
    for row in table.rows[1:]:
        cell = row.cells[column]
        if cell.text.strip() not in {"-", "—"}:
            continue
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
```

End `_add_data_table` with `return table`. In `_add_dpi_per_mansione_section`, replace the bare call with:

```python
dpi_table = self._add_data_table(doc, headers, rows)
_center_dpi_brand_model_placeholders(dpi_table)
```

- [ ] **Step 9: Run the complete focused risk/person/DPI suite**

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_pericoli_parent_sync.py tests/test_dvr_persona_dpi_rischi.py tests/test_dvr_luca_improvements.py -k 'risk or rischio or pericolo or dpi or external' -q`

Expected: PASS with exact per-person identity, no phantom fallback, and localized alignment.

- [ ] **Step 10: Commit risk and person fidelity**

```bash
git add backend/app/services/document_generator/dvr_master.py backend/app/api/v1/pericoli.py backend/tests/test_pericoli_parent_sync.py backend/tests/test_dvr_persona_dpi_rischi.py backend/tests/test_dvr_luca_improvements.py
git commit -m "fix: preserve evaluated risks and person attribution"
```

---

### Task 6: Add level-2 separator pages, complete improvement fields, and enlarge signatures

**Files:**
- Modify: `backend/app/services/document_generator/dvr_master.py`
- Modify: `backend/tests/test_dvr_luca_improvements.py`
- Modify: `backend/tests/test_generators.py`

**Interfaces:**
- Consumes: every existing DVR level-2 topic and ordered `MisuraMiglioramento` rows.
- Produces: `_last_content_element(self, doc: Document) -> BaseOxmlElement | None`; `_ensure_page_boundary(self, doc: Document) -> None`; `_add_topic_separator(self, doc: Document, heading: str, *, part_heading: str | None = None, part_label: str | None = None) -> None`; seven-column landscape improvement table; 3 cm non-splitting signature rows.

- [ ] **Step 1: Write failing DOCX/XML separator tests**

```python
def _load_verify():
    path = BACKEND_ROOT / "scripts" / "verify_all_generators.py"
    spec = importlib.util.spec_from_file_location("verify_all_generators_luca", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def full_dvr_doc(tmp_path):
    module = _load_verify()
    fixture = module.build_fixture()
    fixture["persone"].append(module.mk(
        nominativo="Dott.ssa Test Medico", mansione="Medico Competente",
        ordine=99, created_at=datetime(2026, 1, 10), is_esterno=True,
        ruolo_medico_competente=True, ruolo_datore_lavoro=False,
        ruolo_rspp=False, ruolo_rls=False, ruolo_primo_soccorso=False,
        ruolo_antincendio=False, ruolo_preposto=False, ambienti=[],
        dpi_codes=[], rischi_specifici_codes=[], attrezzature_speciali=[],
    ))
    module.patch_generators(fixture, str(tmp_path))
    ok, path, message = asyncio.run(module.run_one("DVR_MASTER", fixture["azienda"].id))
    assert ok, message
    return Document(path), fixture


def _next_paragraph_has_page_break(paragraph) -> bool:
    following = paragraph._p.getnext()
    return bool(following is not None and following.xpath('.//w:br[@w:type="page"]'))


def _document_xml_has_adjacent_page_breaks(doc: Document) -> bool:
    flags = [bool(paragraph._p.xpath('.//w:br[@w:type="page"]')) for paragraph in doc.paragraphs]
    return any(left and right for left, right in zip(flags, flags[1:]))


def test_every_level_two_heading_is_a_single_separator_without_adjacent_page_breaks(full_dvr_doc):
    doc, fixture = full_dvr_doc
    headings = [p for p in doc.paragraphs if p.style.name == "Heading 2"]
    expected = {
        "1. Presentazione dell'Azienda", "2. Anagrafica Aziendale",
        "3. Dati Occupazionali", "4. Organizzazione Aziendale della Sicurezza",
        "5. Ambienti di Lavoro", "6. Servizi Igienico-Assistenziali",
        "7. Macchine, Attrezzature ed Impianti", "8. Sostanze, Prodotti e Preparati Chimici",
        "9. Elenco Fattori di Pericolo (Riferimento)", "2.1 Descrizione dell'Attività",
        "2.2 Definizioni", "2.3 Metodologia di Valutazione dei Rischi",
        "2.4 Scala di Probabilità (P)", "2.5 Scala del Danno (D)",
        "Mansioni che espongono i lavoratori a rischi specifici",
        "DPI in dotazione per Mansione", "Segnaletica di Sicurezza",
        "Programma di Informazione, Formazione e Addestramento",
        "4.1 Programma e Procedure di attuazione delle Misure di Miglioramento",
        "Documenti correlati al presente DVR", "4.13 Dichiarazione del Datore di Lavoro",
    }
    expected.update(spec.heading for spec in _PART_IV_PROCEDURAL_SECTIONS)
    expected.update(
        f"Identificazione dell'Ambiente di Lavoro e degli Addetti — {(ambiente.nome or '—').upper()}"
        for ambiente in fixture["ambienti"]
    )
    assert collections.Counter(paragraph.text for paragraph in headings) == collections.Counter(expected)
    for heading in headings:
        assert _next_paragraph_has_page_break(heading)
    assert not _document_xml_has_adjacent_page_breaks(doc)


def test_each_part_h1_occurs_once_and_shares_its_first_topic_separator(full_dvr_doc):
    doc, _fixture = full_dvr_doc
    h1 = [p for p in doc.paragraphs if p.style.name == "Heading 1"]
    h1_text = [p.text for p in h1]
    assert h1_text.count("PARTE I — DATI GENERALI DELL'AZIENDA") == 1
    assert h1_text.count("PARTE II — DESCRIZIONE DELL'ATTIVITÀ E METODOLOGIA DI VALUTAZIONE") == 1
    assert h1_text.count("PARTE III — VALUTAZIONE DEI RISCHI PER AMBIENTE DI LAVORO") == 1
    assert h1_text.count("PARTE IV — PROGRAMMA DI MIGLIORAMENTO") == 1
    assert all(paragraph.runs[0].font.size == Pt(11) for paragraph in h1 if paragraph.text.startswith("PARTE "))
```

- [ ] **Step 2: Run separator tests and verify current inline headings fail**

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_dvr_luca_improvements.py -k 'separator or part_h1' -q`

Expected: FAIL because current H2 content follows on the same page.

- [ ] **Step 3: Implement a single separator abstraction and replace every H2 emission**

```python
def _last_content_element(self, doc: Document):
    for element in reversed(doc._element.body):
        if element.tag != qn("w:sectPr"):
            return element
    return None


def _ensure_page_boundary(self, doc: Document) -> None:
    last = self._last_content_element(doc)
    if last is not None and last.tag == qn("w:p"):
        if last.xpath('.//w:br[@w:type="page"]') or last.xpath('./w:pPr/w:sectPr'):
            return
    doc.add_page_break()


def _add_topic_separator(
    self,
    doc: Document,
    heading: str,
    *,
    part_heading: str | None = None,
    part_label: str | None = None,
) -> None:
    self._ensure_page_boundary(doc)
    if part_heading:
        part = doc.add_heading(part_heading, level=1)
        part.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in part.runs:
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    elif part_label:
        context = doc.add_paragraph()
        context.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = context.add_run(part_label)
        run.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = _HEADER_BG
    topic = doc.add_heading(heading, level=2)
    topic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    topic.paragraph_format.space_before = Cm(6)
    for run in topic.runs:
        run.font.size = Pt(24)
        run.font.bold = True
    doc.add_page_break()
```

`_ensure_page_boundary` treats either an explicit page break or a section-break `sectPr` as an existing boundary. Remove caller-owned trailing/leading page breaks that would duplicate it. Route Part I topics 1–9, Part II topics 2.1–2.5, every Part III environment plus the four Part III tail topics, Part IV 4.1–4.13, and `Documenti correlati al presente DVR` through this helper. Keep all level-3 headings inline.

- [ ] **Step 4: Write failing complete improvement-table tests**

```python
def test_improvement_table_prints_all_saved_fields_in_order_and_restores_portrait():
    rows = [
        SimpleNamespace(id=uuid.UUID(int=2), created_at=datetime(2026, 1, 2), ordine=2, priorita="MODESTO", misura="R2", misura_miglioramento="M2", procedura="P2", risorse="S2", responsabile="A2", scadenza="D2"),
        SimpleNamespace(id=uuid.UUID(int=1), created_at=datetime(2026, 1, 1), ordine=1, priorita="GRAVE", misura="R1", misura_miglioramento="M1", procedura="P1", risorse="S1", responsabile="A1", scadenza="D1"),
    ]
    doc = Document()
    _new_generator()._add_improvement_program_table(doc, rows)
    table = doc.tables[-1]
    assert [c.text for c in table.rows[0].cells] == [
        "Priorità", "Rischio", "Misura di Miglioramento", "Attività / Procedura", "Risorse", "Responsabile", "Scadenza"
    ]
    assert [c.text for c in table.rows[1].cells] == ["GRAVE", "R1", "M1", "P1", "S1", "A1", "D1"]
    assert doc.sections[-2].orientation == WD_ORIENT.LANDSCAPE
    assert doc.sections[-1].orientation == WD_ORIENT.PORTRAIT
```

- [ ] **Step 5: Implement the seven-column landscape section**

```python
def _start_landscape_section(doc: Document):
    section = doc.add_section(WD_SECTION.CONTINUOUS)
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.left_margin = Cm(1.2)
    section.right_margin = Cm(1.2)
    return section


def _restore_portrait_section(doc: Document):
    section = doc.add_section(WD_SECTION.NEW_PAGE)
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width, section.page_height = section.page_height, section.page_width
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.0)
    return section
```

Within `_add_improvement_program_table`, sort rows with `_saved_order_key`, start the landscape section, and use:

```python
headers = [
    "Priorità",
    "Rischio",
    "Misura di Miglioramento",
    "Attività / Procedura",
    "Risorse",
    "Responsabile",
    "Scadenza",
]
widths = [Cm(2.0), Cm(3.5), Cm(5.2), Cm(5.2), Cm(3.0), Cm(3.2), Cm(2.8)]
values = [
    m.priorita or "—",
    m.misura or "—",
    m.misura_miglioramento or "—",
    m.procedura or "—",
    m.risorse or "—",
    m.responsabile or "—",
    m.scadenza or "—",
]
header_properties = table.rows[0]._tr.get_or_add_trPr()
repeat = OxmlElement("w:tblHeader")
repeat.set(qn("w:val"), "true")
header_properties.append(repeat)
for row in table.rows:
    for column, width in enumerate(widths):
        row.cells[column].width = width
_restore_portrait_section(doc)
```

Print `—` for only the corresponding empty field. Keep priority text plus the existing priority color.

- [ ] **Step 6: Write failing declaration/signature structure tests**

```python
def test_declaration_has_fresh_content_page_and_signature_rows_are_signable(full_dvr_doc):
    doc, _fixture = full_dvr_doc
    declaration = next(
        paragraph for paragraph in doc.paragraphs
        if paragraph.text == "4.13 Dichiarazione del Datore di Lavoro"
    )
    assert _next_paragraph_has_page_break(declaration)
    signature = next(
        table for table in doc.tables
        if len(table.rows) == 2
        and len(table.rows[0].cells) == 3
        and "Il Datore di Lavoro" in " ".join(cell.text for cell in table.rows[0].cells)
    )
    signature_text = " ".join(cell.text for row in signature.rows for cell in row.cells)
    for expected in ("MARIO ROSSI", "LUCA BIANCHI", "DOTT.SSA TEST MEDICO", "GIULIA VERDI"):
        assert expected in signature_text
    for row in signature.rows:
        assert row.height >= Cm(3)
        assert row.height_rule == WD_ROW_HEIGHT_RULE.AT_LEAST
        assert row._tr.xpath("./w:trPr/w:cantSplit")
    final_clause = next(paragraph for paragraph in doc.paragraphs if paragraph.text.startswith("di impegnarsi a rielaborare"))
    place_date = next(paragraph for paragraph in doc.paragraphs if ", li " in paragraph.text)
    assert final_clause._p.xpath("./w:pPr/w:keepNext")
    assert place_date._p.xpath("./w:pPr/w:keepNext")
```

- [ ] **Step 7: Implement declaration pagination and signature space**

Let the topic separator own the fresh page. Capture the final clause paragraph and apply:

```python
last_clause.paragraph_format.keep_with_next = True
luogo_data.paragraph_format.keep_with_next = True
```

After populating the existing 2×3 signature grid and preserving all names, apply:

```python
for row in table.rows:
    row.height = Cm(3)
    row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
    self._set_row_cant_split(row)
```

- [ ] **Step 8: Run layout, generator, TOC, and revision tests**

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_dvr_luca_improvements.py tests/test_dvr_toc_cached_body.py tests/test_generators.py tests/test_document_revision_number.py -q`

Expected: PASS; update only the obsolete five-column assertion in `test_generators.py` to the exact seven-column header.

- [ ] **Step 9: Commit the DVR pagination and final tables**

```bash
git add backend/app/services/document_generator/dvr_master.py backend/tests/test_dvr_luca_improvements.py backend/tests/test_generators.py
git commit -m "feat: complete DVR topic and signature layout"
```

---

### Task 7: Build the Luca-style integration fixture and verify DOCX/PDF output

**Files:**
- Create: `backend/scripts/verify_dvr_luca_fixture.py`
- Modify: `backend/tests/test_dvr_luca_improvements.py`
- Modify: `docs/superpowers/specs/2026-08-03-dvr-master-luca-improvements-design.md` (status only)

**Interfaces:**
- Consumes: all Task 1–6 public helpers and the existing `scripts/verify_all_generators.py` fixture/patch approach.
- Produces: `build_luca_fixture() -> dict`; `audit_luca_docx(path: Path, fixture: dict) -> dict[str, bool]`; `build_and_audit(output_dir: Path) -> dict[str, bool]`; an exit-zero audit command and ephemeral `DVR_Luca_Fixture.docx`/PDF under a `mktemp -d` directory, never in Git.

- [ ] **Step 1: Write the failing end-to-end fixture audit test**

```python
def test_luca_fixture_auditor_reports_all_acceptance_checks(tmp_path):
    report = build_and_audit(tmp_path)
    assert report == {
        "acme_regression": True,
        "vera_cover": True,
        "saved_people_order": True,
        "saved_environment_order": True,
        "external_roles": True,
        "grouped_equipment": True,
        "all_ten_photos": True,
        "effective_risks": True,
        "person_specific_risks": True,
        "dpi_dash_alignment": True,
        "topic_separators": True,
        "complete_improvements": True,
        "declaration_signatures": True,
    }
```

- [ ] **Step 2: Run the audit test and verify the integration builder is absent**

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_dvr_luca_improvements.py::test_luca_fixture_auditor_reports_all_acceptance_checks -q`

Expected: FAIL because `build_and_audit` is not defined.

- [ ] **Step 3: Implement the deterministic integration fixture and structural auditor**

Build two out-of-alphabetical environments, three ordered employees, an external RSPP, an external Medico, duplicated equipment with mixed flags, ten generated JPG/PNG/HEIC derivatives, stale parent flags with applicable children, same-role workers with divergent risks, and two fully populated improvement rows. Use generated colored rectangles and fictional names only.

```python
import argparse
import asyncio
import json
import shutil
import sys
import uuid
from collections import Counter
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pillow_heif
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm
from PIL import Image

from app.services.ambiente_photo import normalize_document_image
from app.services.document_generator.dvr_master import DVRMasterGenerator
from scripts.verify_all_generators import build_fixture, mk, patch_generators, run_one

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _image_bytes(image: Image.Image, image_format: str) -> bytes:
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def _next_paragraph_has_page_break(paragraph) -> bool:
    following = paragraph._p.getnext()
    return bool(following is not None and following.xpath('.//w:br[@w:type="page"]'))


def build_luca_fixture() -> dict:
    fixture = build_fixture()
    fixture["azienda"].ragione_sociale = "LUCA FIXTURE INDUSTRIA SRL"
    fixture["generated_at"] = datetime(2026, 8, 3, 9, 0, 0)
    zulu_env, alpha_env = fixture["ambienti"][:2]
    zulu_env.nome, zulu_env.ordine, zulu_env.created_at = "Zulu Reparto", 1, datetime(2026, 1, 1)
    alpha_env.nome, alpha_env.ordine, alpha_env.created_at = "Alpha Reparto", 2, datetime(2026, 1, 2)
    fixture["ambienti"] = [alpha_env, zulu_env]

    ddl = mk(
        nominativo="Datore Fixture", mansione="Datore", ordine=0,
        created_at=datetime(2026, 1, 1), is_esterno=False,
        ruolo_datore_lavoro=True, ruolo_rspp=False, ruolo_rls=False,
        ruolo_medico_competente=False, ruolo_primo_soccorso=False,
        ruolo_antincendio=False, ruolo_preposto=False,
        ambienti=[zulu_env, alpha_env], dpi_codes=[], rischi_specifici_codes=[],
        attrezzature_speciali=[],
    )
    zulu_worker = mk(
        nominativo="Zulu Worker", mansione="Operaio", ordine=1,
        created_at=datetime(2026, 1, 2), is_esterno=False,
        ruolo_datore_lavoro=False, ruolo_rspp=False, ruolo_rls=False,
        ruolo_medico_competente=False, ruolo_primo_soccorso=False,
        ruolo_antincendio=False, ruolo_preposto=False,
        ambienti=[zulu_env], dpi_codes=[], rischi_specifici_codes=["af_rumore"],
        attrezzature_speciali=[],
    )
    alpha_worker = mk(
        nominativo="Alpha Worker", mansione="Operaio", ordine=2,
        created_at=datetime(2026, 1, 3), is_esterno=False,
        ruolo_datore_lavoro=False, ruolo_rspp=False, ruolo_rls=True,
        ruolo_medico_competente=False, ruolo_primo_soccorso=False,
        ruolo_antincendio=False, ruolo_preposto=False,
        ambienti=[alpha_env], dpi_codes=[], rischi_specifici_codes=["mmc"],
        attrezzature_speciali=[],
    )
    external_rspp = mk(
        nominativo="Consulente RSPP", mansione="RSPP", ordine=3,
        created_at=datetime(2026, 1, 4), is_esterno=True,
        ruolo_datore_lavoro=False, ruolo_rspp=True, ruolo_rls=False,
        ruolo_medico_competente=False, ruolo_primo_soccorso=False,
        ruolo_antincendio=False, ruolo_preposto=False,
        ambienti=[], dpi_codes=[], rischi_specifici_codes=[], attrezzature_speciali=[],
    )
    external_medico = mk(
        nominativo="Consulente Medico", mansione="Medico", ordine=4,
        created_at=datetime(2026, 1, 5), is_esterno=True,
        ruolo_datore_lavoro=False, ruolo_rspp=False, ruolo_rls=False,
        ruolo_medico_competente=True, ruolo_primo_soccorso=False,
        ruolo_antincendio=False, ruolo_preposto=False,
        ambienti=[], dpi_codes=[], rischi_specifici_codes=[], attrezzature_speciali=[],
    )
    fixture["persone"] = [external_medico, alpha_worker, external_rspp, zulu_worker, ddl]
    zulu_env.persone = [ddl, zulu_worker]
    alpha_env.persone = [ddl, alpha_worker]

    fixture["attrezzature"] = [
        mk(descrizione=" Trapano   a colonna ", ambiente_id=alpha_env.id, marcatura_ce=True, verifiche_periodiche=False),
        mk(descrizione="TRAPANO A COLONNA", ambiente_id=zulu_env.id, marcatura_ce=False, verifiche_periodiche=False),
    ]
    applicable = mk(
        pericolo="RISK APPLICABLE SENTINEL", applicabile=True, ordine=1,
        condizioni_esposizione="Condizione", rischio="Rischio",
        misure_prevenzione="Misura", probabilita_p=2, danno_d=3,
        livello_rischio="GRAVE",
    )
    disabled = mk(pericolo="RISK DISABLED SENTINEL", applicabile=False, ordine=2)
    zulu_env.valutazioni_rischio = [
        mk(categoria_rischio="Macchine", applicabile=False, pericoli=[applicable, disabled])
    ]
    alpha_env.valutazioni_rischio = []

    photos = []
    for index in range(10):
        image = Image.new("RGB", (60 + index, 40 + index), (20 * index, 80, 160))
        if index % 3 == 0:
            filename, source = f"foto-{index}.jpg", _image_bytes(image, "JPEG")
        elif index % 3 == 1:
            filename, source = f"foto-{index}.png", _image_bytes(image, "PNG")
        else:
            heif = pillow_heif.from_pillow(image)
            output = BytesIO()
            heif.save(output)
            filename, source = f"foto-{index}.heic", output.getvalue()
        normalized = normalize_document_image(source)
        photos.append(mk(
            filename=filename, file_path="/not-shared-on-worker/" + filename,
            document_image_bytes=normalized.content,
            document_image_content_type=normalized.content_type,
            created_at=datetime(2026, 1, 1, 9, index),
        ))

    measures = [
        mk(id=uuid.UUID(int=2), ordine=2, created_at=datetime(2026, 1, 2), priorita="MODESTO", misura="R2", misura_miglioramento="M2", procedura="P2", risorse="S2", responsabile="A2", scadenza="D2"),
        mk(id=uuid.UUID(int=1), ordine=1, created_at=datetime(2026, 1, 1), priorita="GRAVE", misura="R1", misura_miglioramento="M1", procedura="P1", risorse="S1", responsabile="A1", scadenza="D1"),
    ]
    fixture["dvr_extras"] = {
        "foto_by_ambiente": {zulu_env.id: photos},
        "vdt_esposti_persona_ids": set(),
        "allegati_presenti": [],
        "misure_miglioramento": measures,
    }
    fixture["expected_people"] = ["DATORE FIXTURE", "ZULU WORKER", "ALPHA WORKER"]
    fixture["expected_environments"] = ["ZULU REPARTO", "ALPHA REPARTO"]
    return fixture


def _table_with_headers(doc: Document, headers: list[str]):
    return next(
        table for table in doc.tables
        if table.rows and [cell.text.strip() for cell in table.rows[0].cells] == headers
    )


def _text(doc: Document) -> str:
    return "\n".join(
        [paragraph.text for paragraph in doc.paragraphs]
        + [cell.text for table in doc.tables for row in table.rows for cell in row.cells]
    )


def _audit_vera_cover(path: Path, doc: Document) -> bool:
    with ZipFile(path) as archive:
        media = [archive.read(name) for name in archive.namelist() if name.startswith("word/media/")]
    return (
        (BACKEND_ROOT / "assets" / "n2o_vera_dvr.png").read_bytes() in media
        and (BACKEND_ROOT / "assets" / "logo.png").read_bytes() not in media
        and "Documento elaborato da" not in _text(doc)
    )


def _audit_saved_people_order(doc: Document, fixture: dict) -> bool:
    table = _table_with_headers(doc, ["Nominativo", "Mansione", "Ambiente di Lavoro", "Codice Fiscale", "Tipologia contrattuale"])
    return [row.cells[0].text.strip() for row in table.rows[1:]] == fixture["expected_people"]


def _audit_saved_environment_order(doc: Document, fixture: dict) -> bool:
    headings = [paragraph.text for paragraph in doc.paragraphs]
    positions = [headings.index(next(text for text in headings if text.endswith(name))) for name in fixture["expected_environments"]]
    return positions == sorted(positions)


def _audit_external_roles(doc: Document, fixture: dict) -> bool:
    occupational = _table_with_headers(doc, ["Nominativo", "Mansione", "Ambiente di Lavoro", "Codice Fiscale", "Tipologia contrattuale"])
    occupational_text = " ".join(cell.text for row in occupational.rows for cell in row.cells)
    full = _text(doc)
    return (
        "CONSULENTE RSPP (ESTERNO)" in full
        and "CONSULENTE MEDICO (ESTERNO)" in full
        and "CONSULENTE RSPP" not in occupational_text
        and "CONSULENTE MEDICO" not in occupational_text
    )


def _audit_grouped_equipment(doc: Document, fixture: dict) -> bool:
    table = _table_with_headers(doc, ["Macchine, Attrezzature ed Impianti", "Ambiente", "Marcata CE", "Verifiche Periodiche"])
    matches = [row for row in table.rows[1:] if row.cells[0].text == "TRAPANO A COLONNA"]
    return len(matches) == 1 and [cell.text for cell in matches[0].cells[1:]] == ["ZULU REPARTO, ALPHA REPARTO", "MISTO", "NO"]


def _audit_effective_risks(doc: Document, fixture: dict) -> bool:
    full = _text(doc)
    return full.count("RISK APPLICABLE SENTINEL") == 1 and "RISK DISABLED SENTINEL" not in full


def _audit_person_specific_risks(doc: Document, fixture: dict) -> bool:
    table = _table_with_headers(doc, ["Nominativo", "Mansione", "Rischio specifico"])
    rows = {row.cells[0].text: row.cells[2].text for row in table.rows[1:]}
    return "Rumore" in rows["ZULU WORKER"] and "Movimentazione" not in rows["ZULU WORKER"] and "Movimentazione" in rows["ALPHA WORKER"] and "Rumore" not in rows["ALPHA WORKER"]


def _audit_dpi_dash_alignment(doc: Document) -> bool:
    table = next(table for table in doc.tables if table.rows and "Marca / Modello" in [cell.text for cell in table.rows[0].cells])
    column = [cell.text for cell in table.rows[0].cells].index("Marca / Modello")
    cells = [row.cells[column] for row in table.rows[1:] if row.cells[column].text.strip() in {"-", "—"}]
    return bool(cells) and all(cell.vertical_alignment == WD_CELL_VERTICAL_ALIGNMENT.CENTER and all(p.alignment == WD_ALIGN_PARAGRAPH.CENTER for p in cell.paragraphs) for cell in cells)


def _audit_topic_separators(doc: Document) -> bool:
    headings = [paragraph for paragraph in doc.paragraphs if paragraph.style.name == "Heading 2"]
    flags = [bool(paragraph._p.xpath('.//w:br[@w:type="page"]')) for paragraph in doc.paragraphs]
    return bool(headings) and all(_next_paragraph_has_page_break(item) for item in headings) and not any(a and b for a, b in zip(flags, flags[1:]))


def _audit_complete_improvements(doc: Document, fixture: dict) -> bool:
    headers = ["Priorità", "Rischio", "Misura di Miglioramento", "Attività / Procedura", "Risorse", "Responsabile", "Scadenza"]
    table = _table_with_headers(doc, headers)
    return [cell.text for cell in table.rows[1].cells] == ["GRAVE", "R1", "M1", "P1", "S1", "A1", "D1"] and [cell.text for cell in table.rows[2].cells] == ["MODESTO", "R2", "M2", "P2", "S2", "A2", "D2"] and any(section.orientation == WD_ORIENT.LANDSCAPE for section in doc.sections) and doc.sections[-1].orientation == WD_ORIENT.PORTRAIT


def _audit_declaration_signatures(doc: Document, fixture: dict) -> bool:
    declaration = next(paragraph for paragraph in doc.paragraphs if paragraph.text == "4.13 Dichiarazione del Datore di Lavoro")
    signature = next(table for table in doc.tables if len(table.rows) == 2 and "Il Datore di Lavoro" in " ".join(cell.text for cell in table.rows[0].cells))
    return _next_paragraph_has_page_break(declaration) and all(row.height >= Cm(3) and row.height_rule == WD_ROW_HEIGHT_RULE.AT_LEAST and row._tr.xpath("./w:trPr/w:cantSplit") for row in signature.rows)


def _has_caption(doc: Document, prefix: str) -> bool:
    return any(paragraph.text.startswith(prefix) for paragraph in doc.paragraphs)


def build_and_audit(output_dir: Path) -> dict[str, bool]:
    acme = build_fixture()
    patch_generators(acme, str(output_dir))
    acme_ok, acme_path, acme_message = asyncio.run(
        run_one("DVR_MASTER", acme["azienda"].id)
    )
    if not acme_ok:
        raise AssertionError(acme_message)
    stable_acme = output_dir / "DVR_Acme_Regression.docx"
    shutil.copy2(acme_path, stable_acme)

    fixture = build_luca_fixture()
    patch_generators(fixture, str(output_dir))

    async def rich_dvr_extras(self, data):
        return fixture["dvr_extras"]

    DVRMasterGenerator._load_dvr_extras = rich_dvr_extras
    ok, generated_path, message = asyncio.run(
        run_one("DVR_MASTER", fixture["azienda"].id)
    )
    if not ok:
        raise AssertionError(message)
    stable_path = output_dir / "DVR_Luca_Fixture.docx"
    shutil.copy2(generated_path, stable_path)
    report = audit_luca_docx(stable_path, fixture)
    report["acme_regression"] = len(Document(stable_acme).tables) >= 50
    return {key: report[key] for key in (
        "acme_regression", "vera_cover", "saved_people_order",
        "saved_environment_order", "external_roles", "grouped_equipment",
        "all_ten_photos", "effective_risks", "person_specific_risks",
        "dpi_dash_alignment", "topic_separators", "complete_improvements",
        "declaration_signatures",
    )}


def audit_luca_docx(path: Path, fixture: dict) -> dict[str, bool]:
    doc = Document(path)
    return {
        "vera_cover": _audit_vera_cover(path, doc),
        "saved_people_order": _audit_saved_people_order(doc, fixture),
        "saved_environment_order": _audit_saved_environment_order(doc, fixture),
        "external_roles": _audit_external_roles(doc, fixture),
        "grouped_equipment": _audit_grouped_equipment(doc, fixture),
        "all_ten_photos": len(doc.inline_shapes) >= 10 and _has_caption(doc, "Fig. 10"),
        "effective_risks": _audit_effective_risks(doc, fixture),
        "person_specific_risks": _audit_person_specific_risks(doc, fixture),
        "dpi_dash_alignment": _audit_dpi_dash_alignment(doc),
        "topic_separators": _audit_topic_separators(doc),
        "complete_improvements": _audit_complete_improvements(doc, fixture),
        "declaration_signatures": _audit_declaration_signatures(doc, fixture),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = build_and_audit(args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(report.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
```

All fixture identities and pixels are synthetic. No real name, photo, or company data enters this script.

- [ ] **Step 4: Run all focused and full backend tests**

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_dvr_luca_improvements.py tests/test_ambiente_photo.py tests/test_pericoli_parent_sync.py tests/test_dvr_persona_dpi_rischi.py tests/test_dvr_toc_cached_body.py tests/test_branding.py tests/test_document_revision_number.py -q`

Run: `cd backend && /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest -q`

Expected: both commands PASS with no failures. Treat any unrelated baseline-only failure separately by reproducing it on base SHA before deciding whether it is in scope.

- [ ] **Step 5: Exercise the migration in both directions against a disposable database**

```bash
cd backend
/Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest tests/test_ambiente_photo.py::test_photo_migration_upgrades_and_downgrades_disposable_sqlite -q
LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 /Users/macbookair/Documents/DVR/backend/.venv/bin/python -m alembic heads | tee /tmp/dvr-alembic-heads.txt
test "$(wc -l < /tmp/dvr-alembic-heads.txt | tr -d ' ')" = 1
rg '^a9b0c1d2e3f4 \(head\)$' /tmp/dvr-alembic-heads.txt
```

Expected: the in-memory SQLite test performs upgrade and downgrade and proves only the two new columns are removed; Alembic reports exactly one head. Never run downgrade against a URL from shell settings, Render, or any persistent database.

- [ ] **Step 6: Generate, audit, convert, and visually inspect the local document**

```bash
audit_dir="$(mktemp -d /tmp/dvr-luca-audit.XXXXXX)"
cd backend
/Users/macbookair/Documents/DVR/backend/.venv/bin/python scripts/verify_dvr_luca_fixture.py --output-dir "$audit_dir"
soffice --headless --convert-to pdf --outdir "$audit_dir" "$audit_dir/DVR_Luca_Fixture.docx"
soffice --headless --convert-to pdf --outdir "$audit_dir" "$audit_dir/DVR_Acme_Regression.docx"
pdftoppm -png -r 120 "$audit_dir/DVR_Luca_Fixture.pdf" "$audit_dir/page"
pdftoppm -png -r 120 "$audit_dir/DVR_Acme_Regression.pdf" "$audit_dir/acme-page"
/Users/macbookair/Documents/DVR/backend/.venv/bin/python - "$audit_dir" <<'PY'
import sys
from pathlib import Path
from pypdf import PdfReader

root = Path(sys.argv[1])
for name in ("DVR_Luca_Fixture.pdf", "DVR_Acme_Regression.pdf"):
    reader = PdfReader(root / name)
    assert reader.pages, name
    blank = [index + 1 for index, page in enumerate(reader.pages) if not (page.extract_text() or "").strip()]
    assert not blank, f"{name} has blank pages: {blank}"
    print(name, len(reader.pages))
PY
```

This isolated full-Acme plus Luca-fixture gate is the pre-production staging gate; no Render staging service exists in the verified service inventory. Inspect both covers and representative Acme pages, then inspect Luca's two separator pages, ordered roster/environment pages, global equipment, all photo pages, effective risk tables, person-specific risk table, DPI dash, landscape improvement table, and declaration/signature page. Record both page counts and reject blank pages, duplicate adjacent separators, clipped columns, split signature rows, changed VERA text/colors, or distorted photos.

- [ ] **Step 7: Run repository hygiene and diff checks**

```bash
git diff --check
git status --short
unexpected="$(git diff --name-only --diff-filter=A origin/main...HEAD | rg 'luca-dvr-master|Progetto senza titolo|DVR_(Luca_Fixture|Acme_Regression)|\.heic$|\.docx$|\.pdf$' || true)"
test -z "$unexpected"
```

Expected: `git diff --check` is clean; only intended source/tests/docs/asset are tracked; no generated artifact or source attachment appears.

- [ ] **Step 8: Mark the design implemented and commit the integration evidence code**

Change the design status to `Implemented and locally verified; pending production rollout`, then:

```bash
git add backend/scripts/verify_dvr_luca_fixture.py backend/tests/test_dvr_luca_improvements.py docs/superpowers/specs/2026-08-03-dvr-master-luca-improvements-design.md
git commit -m "test: verify Luca DVR improvements end to end"
```

---

### Task 8: Review, publish, deploy the exact SHA, and run production smoke tests

**Files:**
- No product-file edits are expected after review; any finding returns to the relevant task and receives its own test-first commit.

**Interfaces:**
- Consumes: fully green branch `codex/dvr-master-luca-improvements`; GitHub repository `gunnit/n2o-dvr-platform`; Render API service `srv-d7glpedckfvc73fvagk0`; Render worker service `srv-d7glpedckfvc73fvagkg`; production API `https://n2o-dvr-api.onrender.com`.
- Produces: reviewed merge SHA on `origin/main`, successful API/worker deployments of that SHA, and production DOCX/PDF/log evidence.

- [ ] **Step 1: Run independent specification and code-quality reviews**

Dispatch one reviewer against the approved design and Git diff to list missing or over-scoped behavior, then a second reviewer for code quality, security, migration safety, transaction behavior, privacy, and test validity. Resolve every high/medium finding with a reproducing test and focused commit; rerun the affected task suite after each fix.

- [ ] **Step 2: Perform the final local verification gate**

```bash
cd backend
/Users/macbookair/Documents/DVR/backend/.venv/bin/python -m pytest -q
cd ..
git diff --check
git status --short --branch
git log --oneline --decorate origin/main..HEAD
```

Expected: full suite PASS, clean diff check, no unstaged files, and only intentional commits above `origin/main`.

- [ ] **Step 3: Push the branch and open a ready pull request**

```bash
git push -u origin codex/dvr-master-luca-improvements
/Users/macbookair/.local/bin/gh pr create --base main --head codex/dvr-master-luca-improvements --title "Fix all Luca DVR Master improvements" --body-file docs/superpowers/specs/2026-08-03-dvr-master-luca-improvements-design.md
```

Expected: push succeeds and GitHub returns one pull-request URL.

- [ ] **Step 4: Wait for GitHub checks and merge only the reviewed head**

```bash
pr_number="$(/Users/macbookair/.local/bin/gh pr view codex/dvr-master-luca-improvements --json number --jq .number)"
/Users/macbookair/.local/bin/gh pr checks "$pr_number" --watch --fail-fast
reviewed_head="$(/Users/macbookair/.local/bin/gh pr view "$pr_number" --json headRefOid --jq .headRefOid)"
test "$reviewed_head" = "$(git rev-parse HEAD)"
/Users/macbookair/.local/bin/gh pr view "$pr_number" --json mergeable --jq '.mergeable == "MERGEABLE"' | rg '^true$'
/Users/macbookair/.local/bin/render services --output json > /tmp/dvr-services-before.json
/usr/bin/python3 - /tmp/dvr-services-before.json <<'PY'
import json, sys
wanted = {"srv-d7glpedckfvc73fvagk0", "srv-d7glpedckfvc73fvagkg"}
rows = json.load(open(sys.argv[1]))
services = {row.get("service", row)["id"]: row.get("service", row) for row in rows if row.get("service", row).get("id") in wanted}
assert set(services) == wanted
assert all(service.get("autoDeploy") == "yes" for service in services.values())
PY
/Users/macbookair/.local/bin/render services update srv-d7glpedckfvc73fvagk0 --auto-deploy=false --confirm --output json
/Users/macbookair/.local/bin/render services update srv-d7glpedckfvc73fvagkg --auto-deploy=false --confirm --output json
if ! /Users/macbookair/.local/bin/gh pr merge "$pr_number" --squash --delete-branch --match-head-commit "$reviewed_head"; then
  /Users/macbookair/.local/bin/render services update srv-d7glpedckfvc73fvagk0 --auto-deploy --confirm --output json
  /Users/macbookair/.local/bin/render services update srv-d7glpedckfvc73fvagkg --auto-deploy --confirm --output json
  exit 1
fi
merge_sha="$(/Users/macbookair/.local/bin/gh pr view "$pr_number" --json mergeCommit --jq .mergeCommit.oid)"
git fetch origin main
remote_sha="$(git ls-remote origin refs/heads/main | awk '{print $1}')"
test "$(git rev-parse origin/main)" = "$merge_sha"
test "$merge_sha" = "$remote_sha"
```

Expected: all required checks pass; the reviewed head is pinned; API and worker auto-deploy are held before the merge; and local `origin/main` equals live GitHub `main`. If merge fails, both services are restored to auto-deploy before exiting.

- [ ] **Step 5: Deploy that exact merge SHA to API and worker**

```bash
merge_sha="$(git rev-parse origin/main)"
/Users/macbookair/.local/bin/render deploys create srv-d7glpedckfvc73fvagk0 --commit "$merge_sha" --wait --confirm --output json
/Users/macbookair/.local/bin/render deploys list srv-d7glpedckfvc73fvagk0 --output json > /tmp/dvr-api-deploys.json
/usr/bin/python3 - "$merge_sha" /tmp/dvr-api-deploys.json <<'PY'
import json, sys
sha, path = sys.argv[1:]
latest = json.load(open(path))[0]
assert latest["status"] == "live", latest
assert latest["commit"]["id"] == sha, latest
print(latest["id"], latest["commit"]["id"], latest["status"])
PY
/Users/macbookair/.local/bin/render deploys create srv-d7glpedckfvc73fvagkg --commit "$merge_sha" --wait --confirm --output json
/Users/macbookair/.local/bin/render deploys list srv-d7glpedckfvc73fvagkg --output json > /tmp/dvr-worker-deploys.json
/usr/bin/python3 - "$merge_sha" /tmp/dvr-worker-deploys.json <<'PY'
import json, sys
sha, path = sys.argv[1:]
latest = json.load(open(path))[0]
assert latest["status"] == "live", latest
assert latest["commit"]["id"] == sha, latest
print(latest["id"], latest["commit"]["id"], latest["status"])
PY
/Users/macbookair/.local/bin/render services update srv-d7glpedckfvc73fvagk0 --auto-deploy --confirm --output json
/Users/macbookair/.local/bin/render services update srv-d7glpedckfvc73fvagkg --auto-deploy --confirm --output json
/Users/macbookair/.local/bin/render services --output json > /tmp/dvr-services-after.json
/usr/bin/python3 - /tmp/dvr-services-after.json <<'PY'
import json, sys
wanted = {"srv-d7glpedckfvc73fvagk0", "srv-d7glpedckfvc73fvagkg"}
rows = json.load(open(sys.argv[1]))
services = {row.get("service", row)["id"]: row.get("service", row) for row in rows if row.get("service", row).get("id") in wanted}
assert set(services) == wanted
assert all(service.get("autoDeploy") == "yes" for service in services.values())
PY
```

Expected: the API deploy is `live` at the exact merge SHA and applies Alembic before the worker deploy starts; the worker then becomes `live` at the same SHA; auto-deploy is restored only after both assertions pass. On a failed production deploy, keep auto-deploy held, diagnose/fix the same branch, and do not proceed to smoke claims.

- [ ] **Step 6: Run unauthenticated production health and route checks**

```bash
curl --fail --silent --show-error https://n2o-dvr-api.onrender.com/health
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' https://n2o-dvr-api.onrender.com/api/v1/aziende
```

Expected: health returns 200; the protected route returns 401 rather than 404/500.

- [ ] **Step 7: Generate and inspect one production DVR in the designated smoke-test company**

Using the existing authenticated N2O browser session, open the designated `Deploy Smoke Test` company, confirm it contains no customer data, and generate only `dvr_master`. Poll the returned document status until `completed`, download its DOCX, and record document ID, version, file size, and generation timestamps. If no designated smoke-test company exists, stop before creating production data and request the exact company from the user.

Open the downloaded DOCX and exported PDF. Confirm the VERA cover, absence of consultancy/Gemini marks, saved ordering, external-role handling, grouped equipment, available photos, evaluated risks, named specific-risk rows, centered DPI dash, topic separators, seven improvement fields, and declaration/signature page. The smoke tenant may legitimately omit a table when it has no corresponding saved data; verify the empty-state marker rather than inventing production data.

- [ ] **Step 8: Correlate bounded production logs to the smoke document**

```bash
deploy_started="$(/usr/bin/python3 - /tmp/dvr-api-deploys.json /tmp/dvr-worker-deploys.json <<'PY'
import json, sys
rows = [json.load(open(path))[0] for path in sys.argv[1:]]
print(min(row["createdAt"] for row in rows))
PY
)"
log_end="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
/Users/macbookair/.local/bin/render logs --resources srv-d7glpedckfvc73fvagk0,srv-d7glpedckfvc73fvagkg --start "$deploy_started" --end "$log_end" --limit 1000 --output json
```

Expected: migration and startup succeed; the recorded document ID reaches completed generation; no traceback, unhandled image decode error, database-column error, Celery failure, or HTTP 5xx correlates with the smoke request. Filename-specific legacy-photo warnings are acceptable only when the document contains the matching visible unavailable marker.

- [ ] **Step 9: Record rollout evidence and final repository state**

Capture the PR URL, reviewed head SHA, merge SHA, API deploy ID/status/SHA, worker deploy ID/status/SHA, health result, smoke document ID/version/size, PDF page count, inspected pages, and log time window in the task handoff. Verify the saved checkout remains clean and aligned:

```bash
test -z "$(git -C /Users/macbookair/Documents/DVR status --porcelain)"
test "$(git -C /Users/macbookair/Documents/DVR branch --show-current)" = "main"
test "$(git -C /Users/macbookair/Documents/DVR remote get-url origin)" = "https://github.com/gunnit/n2o-dvr-platform.git"
git -C /Users/macbookair/Documents/DVR fetch origin main
git -C /Users/macbookair/Documents/DVR merge --ff-only origin/main
git -C /Users/macbookair/Documents/DVR rev-parse HEAD
git -C /Users/macbookair/Documents/DVR rev-parse origin/main
git -C /Users/macbookair/Documents/DVR status --short --branch
```

Expected: the saved checkout is first proven clean, on `main`, and pointed at the exact repository; only then is it fast-forwarded. The two final SHAs match and status remains clean.

---

## Final Self-Review Checklist

- [x] Luca items 1–11 each map to at least one failing regression test, implementation task, and end-to-end audit key.
- [x] The only shared platform behavior change is the photo derivative/transport and parent applicability synchronization; document presentation changes remain DVR-only.
- [x] Every referenced function, type, model attribute, migration ID, service ID, branch, and command is spelled consistently across tasks.
- [x] The plan contains no deferred implementation placeholder and every code-changing task includes red, green, regression, and commit steps.
- [x] Production completion requires exact GitHub/Render SHA correlation, an authenticated existing smoke tenant, downloaded document inspection, and bounded logs.
