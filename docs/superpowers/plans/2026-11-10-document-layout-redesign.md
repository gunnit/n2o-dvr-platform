# Document layout redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generated documents look like N2O's 20 Oct DVR model (Arial), and the
in-browser editor shows them the way they print.

**Architecture:**
- **Design kit.** One kit in `design.py` + `docx_utils.py`: tokens, page types
  (art cover, divider, in-page title, back cover, header/footer with logo) and
  table builders.
- **Generators.** The DVR Master is rebuilt on the kit's page map. The other 16
  documents take the kit's look.
- **Editor.** The preview parser reports page roles, resolved typography and
  furniture, and the editor renders sheets from them.
- **Company photo.** A new `azienda_foto_presentazione` table and endpoint feed
  the DVR.

**Tech Stack:** Python 3.12+/3.14, python-docx 1.2, FastAPI, SQLAlchemy async,
Alembic, Pillow/pillow-heif; Next.js 16 + React + TypeScript (frontend).

**Spec:** `docs/superpowers/specs/2026-11-10-document-layout-redesign-design.md`
(read it first; section numbers below refer to it).

**Delivery (changed from spec §7):** Gregor approved the spec on 2026-11-10
with "implement, no more questions, deploy, test". All three phases ship in one
PR, #91, with one commit series per phase, and merge once everything is green.
The spec's three sequential PRs would have serialised work that runs in
parallel here.

## Global Constraints

- Font: `Arial` in every slot (ascii, hAnsi, eastAsia, cs) of every style and kit
  run. Never Calibri or Avenir.
- Sizes (pt): body 12, table 10, table_header 10 bold, section_title 25 bold
  capitals centred, sub_title 12 bold centred, part_label 9 bold capitals
  centred, front_heading 14 bold left, cover_title 26, header 9 bold capitals,
  footer 8.5, note 10 italic.
- Colours:

  | Use | Value |
  |---|---|
  | navy | `003D74` |
  | table header | `4F81BD` with white text |
  | zebra and light labels | `F6F9FC` |
  | ink | `061B31` |
  | footer text | `64748D` |
  | hairlines (header/footer only) | `C9D3DF` |
  | notes | `666666` |
  | table borders | single, sz 4, colour `auto` |
  | risk levels | `RISK_COLORS` (unchanged) |

- Geometry: A4 portrait, margins 2.0/2.0/2.5/2.0 cm, header and footer at
  1.0 cm. No landscape section in the DVR.
- Art marker: `wp:docPr/@name = "vera-art:<role>:<key>"`, where role ∈
  {`cover`, `divider`, `back_cover`}. The art always sits in its own empty
  paragraph.
- `cantSplit` only on header rows and short label rows, never on data rows
  (commit `e0875fa`).
- Generated text is Italian. Code, identifiers and commit messages are English.
- `app/services/document_generator/**` never imports `app.billing`
  (`.importlinter` contract, `test_generators_and_calculators_never_import_billing`).
- Read and download endpoints are never role-gated or paywalled. New write
  endpoints use `require_capability(...)`.
- Commands here:
  - backend: `cd backend && $VENV/bin/python -m pytest -q`
  - frontend: `cd frontend && node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json`
    and `node node_modules/next/dist/bin/next build`

  `$VENV` = `/tmp/claude-0/-home-user-n2o-dvr-platform/6fcec86f-7ce6-5f8d-9e64-e29539e31210/scratchpad/venv`.
  DB-backed tests skip without Postgres; CI runs them.

## Review Focus

1. **Documents generated before this change** must preview, edit and download
   exactly as today. Test: golden parse of an old fixture document (Task 5).
2. **Sparse data** must not crash or print placeholders: no environments, no
   people, no photos, no allegati, missing Medico/RLS, unreadable org logo
   bytes. Tests: Task 2 (logo, art), Task 3 (sparse fixture).
3. **A data row taller than a page** must not hang LibreOffice. Test: Task 2,
   long cell text rendered with LibreOffice under a timeout.
4. **Editing a divider title** must land in the downloaded `.docx`, with all
   other addresses unchanged. Test: Task 5, apply an override on a kit document.
5. **Company photo edge cases** (HEIC, EXIF rotation, replace, other org's
   azienda) end normalised, replaced and isolated. Tests: Task 4.

---

### Task 1: Art assets

**Files:**
- Create: `backend/scripts/extract_document_art.py`
- Create: `backend/assets/document_art/*` (files listed in spec Appendix A)

**Interfaces:**
- Produces files named `<key>.jpg` for every key in spec Appendix A, plus:
  - `vera_italia_mark.png`, kept as PNG with alpha;
  - `sign_divieto.jpg`, `sign_avvertimento.jpg`, `sign_obbligo.jpg`,
    `sign_emergenza.jpg`, `sign_antincendio.jpg`.

- [ ] **Step 1:** Write `extract_document_art.py <model.docx> <out_dir>`.
  - Unzip `word/media`.
  - Take the `cover_dvr` bitmap from the single STRETCHDIBITS record of
    `image1.emf`.
  - Centre-crop every page art (cover, back cover, dividers) to aspect 0.7071.
  - Resize page art to 1654 px wide. Keep the cover's native 1055 px; never
    upscale.
  - Save JPEG quality 80, progressive (cover quality 90).
  - Sign panels: keep size, JPEG quality 85.
  - Mark: PNG as-is.
- [ ] **Step 2:** Run it on the scratchpad copy (`…/scratchpad/ref-dl/DVR_RISCHIO_MASTER.docx`).
  - Expected: 21 `div_*.jpg` + `div_generico.jpg`, `cover_dvr.jpg`,
    `back_vera.jpg`, 5 `sign_*.jpg`, `vera_italia_mark.png`.
  - Total size ≤ 3.5 MB.
- [ ] **Step 3: Legacy preview fixture.** This must run before Task 2 changes
  any generator. Copy `…/scratchpad/current-out/DVR_Acme_Regression.docx` (made
  by `main`'s generator from fictional data) to
  `backend/tests/fixtures/preview_legacy_dvr.docx`. Write
  `parse_docx_to_blocks(...)` of it, from the current parser, to
  `backend/tests/fixtures/preview_legacy_dvr.blocks.json`.
- [ ] **Step 4:** Commit: `feat(documents): extract the artwork of N2O's DVR model; freeze a legacy preview fixture`.

### Task 2: Design kit

**Files:**
- Modify: `backend/app/services/document_generator/docx_utils.py` (tokens, table builders)
- Modify: `backend/app/services/document_generator/design.py` (page types, furniture, art manifest)
- Modify: `backend/app/services/document_generator/branding.py` (fallback logo)
- Test: `backend/tests/test_design_kit.py`

**Interfaces (Produces):**
- `docx_utils`:
  - Constants: `FONT_FAMILY = "Arial"`; `TYPE_SCALE` with the keys of Global
    Constraints (keep the legacy keys `h1`=16, `h2`=13, `h3`=12,
    `cover_subtitle`=12, `cover_client`=16, `small`=8.5);
    `BRAND_TABLE_HEADER_HEX = "4F81BD"`; `NOTE_GREY = RGBColor(0x66,0x66,0x66)`;
    `LOGO_PATH = BACKEND_ROOT/"assets"/"document_art"/"vera_italia_mark.png"`.
  - Changed defaults: `style_header_row(row, bg_hex=BRAND_TABLE_HEADER_HEX, …)`;
    `set_table_borders(table, color_hex="auto", size=4)`.
  - `add_kv_table(doc, rows, *, variant: str = "blue", width_label_cm=5.0, width_value_cm=11.5) -> Table`.
    `"blue"` = label `4F81BD` white bold; `"light"` = label navy bold on `F6F9FC`.
  - `add_data_table(doc, headers, data_rows, *, column_widths_cm=None) -> Table`:
    same signature, new colours.
  - `add_role_band(doc, title: str, value: str) -> Table`
  - `add_signature_grid(doc, cells: list[tuple[str, str]], *, sign_height_cm: float = 2.5) -> Table`:
    two (role, name) pairs per grid row.
  - `level_cell(cell, level: str) -> None`
  - `add_body_paragraph(doc, text: str) -> Paragraph`: justified.
- `design`:
  - `ART_DIR`, `ART: dict[str, str]` (key → filename), `art_path(key: str) -> Path | None`
    (falls back to `div_generico`; `None` if even that is missing),
    `ART_MARKER_PREFIX = "vera-art:"`.
  - `setup_document(doc, *, landscape: bool = False, profile: str = "attachment") -> None`;
    profile `"dvr"` or `"attachment"` per spec §4.1.4.
  - `add_art_cover(doc, art_key: str) -> None`: DVR, no text.
  - `add_cover(doc, *, title, azienda, branding, version, generated_at, subtitle=None, legal_basis=None, eyebrow=..., logo_width_cm=5.0, show_consultancy=True) -> None`:
    same signature. It now draws `cover_vera` art plus the live title block
    (spec §4.1.2). `logo_width_cm` is accepted and ignored.
  - `add_divider(doc, title: str, art_key: str, *, part_label: str | None = None) -> Paragraph`
    (returns the title paragraph).
  - `add_section_title(doc, title: str, *, part_label: str | None = None, new_page: bool = True) -> Paragraph`
  - `add_sub_title(doc, text: str, *, in_toc: bool = True, new_page: bool = False) -> Paragraph`
  - `add_back_cover(doc, art_key: str = "back_vera") -> None`
  - `add_running_header_footer(...)` and `finish_document(...)`: same signatures.
    New furniture per spec §4.1.2. The first-page header and footer are empty on
    every section whose first paragraph carries an art marker.
  - `finalize_toc`: cached entries get a right tab with a dot leader at the
    text width.

- [ ] **Step 1: Write failing tests** in `test_design_kit.py`. Build tiny docs
  with the kit and assert on XML:
  - `test_styles_use_arial_everywhere`: Normal and Heading 1–3 `rFonts` ascii,
    hAnsi, eastAsia and cs are all `"Arial"`.
  - `test_dvr_profile_section_title_is_25pt_centered_caps`: `Heading 2`
    sz=50, jc=center, caps.
  - `test_data_table_header_fill_and_borders`: header `w:shd/@w:fill=="4F81BD"`;
    `tblBorders` edges `val=single sz=4 color=auto`; no `cantSplit` on data rows.
  - `test_kv_table_variants`: blue label fill `4F81BD` with white run; light
    label fill `F6F9FC` with navy run.
  - `test_divider_starts_new_section_with_clean_first_page`: after
    `add_divider`, the new section has `titlePg`. After `finish_document`, its
    first-page header has no text, and its default header contains the title
    and client in capitals.
  - `test_art_anchor_shape`: anchor `behindDoc="1"`; positionH/V relativeFrom
    `page` with offset 0; extent equals the section page size; docPr name
    `vera-art:divider:div_leggi`. The art paragraph has no text, and the title
    is in the next paragraph.
  - `test_footer_has_logo_rev_and_page_fields`: the footer paragraph has an
    inline `a:blip`, text `Rev. 00 del`, instrText `PAGE` and `NUMPAGES`, and
    the text `Pag.`.
  - `test_missing_art_degrades_to_title_only`: with `ART_DIR` monkeypatched to
    an empty dir, `add_divider` emits the title, no drawing and no exception.
  - `test_unreadable_logo_bytes_fall_back_to_firm_name`:
    `Branding(logo_bytes=b"not-an-image")`; the footer shows the firm name text.
  - `test_long_cell_does_not_hang_libreoffice`: a 1-row table whose cell holds
    ~6000 words. Save, then
    `soffice --headless --convert-to pdf` under `timeout 120`. Exit 0. Skip if
    `soffice` is absent.
  - `test_art_manifest_files_exist`: every `ART` value exists under `ART_DIR`.
- [ ] **Step 2:** Run `pytest tests/test_design_kit.py -q`. Expected: FAIL.
- [ ] **Step 3:** Implement the interfaces above.
  - Anchors are built as `wp:anchor` XML from an inline picture: python-docx
    creates the `wp:inline`, then it is converted.
  - Art sections come from `doc.add_section(WD_SECTION.NEW_PAGE)` with
    `different_first_page_header_footer = True`.
  - `add_running_header_footer` detects art sections by scanning each section's
    first body paragraph for the marker.
- [ ] **Step 4:** Run `pytest tests/test_design_kit.py tests/test_generators.py tests/test_branding.py tests/test_donor_front_matter.py -q`.
  Expected: PASS. Fix any older assertion that pinned Calibri, `C9D3DF` table
  borders or navy table headers, updating it to the new tokens.
- [ ] **Step 5:** Commit: `feat(documents): design kit — Arial tokens, art pages, VERA furniture, table builders`.

### Task 3: DVR Master on the kit (spec §4.2)

**Files:**
- Modify: `backend/app/services/document_generator/dvr_master.py`
- Modify: `backend/scripts/verify_dvr_luca_fixture.py`
- Modify: `backend/tests/test_dvr_luca_improvements.py`, `test_dvr_toc_cached_body.py`,
  `test_dvr_persona_dpi_rischi.py` (expectations only)

**Interfaces:**
- Consumes: all Task 2 functions; `ART` keys from spec Appendix A;
  `load_foto_presentazione` from Task 4 (call it inside `_load_dvr_extras` via
  `extras["foto_presentazione"]: tuple[bytes, str] | None`; tolerate the import
  being absent with `extras.get`).
- Produces: a DVR whose page sequence is spec §4.2.1.

- [ ] **Step 1: Failing audit.** Extend `verify_dvr_luca_fixture.py` with these
  report keys, then run the script. Expected: the new keys report `false`.
  - `page_map_dividers`: the 23 divider titles of §4.2.1 in order, each preceded
    by its art marker key.
  - `in_page_titles`: rows 4–10 and 15–18 present as Heading 2 with no
    numbering.
  - `part_ii_renamed`
  - `split_people_tables`: DATI ANAGRAFICI columns =
    [Nominativo, Codice Fiscale, Tipologia contrattuale]; DATI OCCUPAZIONALI =
    [Nominativo, Mansione, Ambiente di Lavoro].
  - `improvement_table_4_cols`: headers = [Misura di Miglioramento, Risorse,
    Responsabile, Priorità]; no landscape section anywhere.
  - `no_repeated_azienda_table`: the "Azienda | Sede Legale" table occurs only
    on pages 4 and 5.
  - `no_photo_captions`: no paragraph matching `^Fig\. \d+ — `.
  - `sign_panels`: 5 sub-titles plus 5 inline images.
  - `signature_grid`: 4 role headers.
  - `cover_and_back_art`: first and last section start with the `cover_dvr` /
    `back_vera` markers.
  - `company_photo`: present when the fixture gives bytes, absent when it
    doesn't.

  Also add `test_dvr_sparse_azienda_generates` to `tests/test_dvr_luca_improvements.py`
  (Review Focus 2): an azienda with no environments, people, photos, allegati
  or misure. Assert that it generates, starts with `cover_dvr`, ends with
  `back_vera`, the signature grid shows "—" names, and no paragraph contains
  `None`.
- [ ] **Step 2: Implement the page map** (spec §4.2.1 and §4.2.2):
  - Replace `_add_cover_page` with `add_art_cover(doc, "cover_dvr")`.
  - Use `setup_document(doc, profile="dvr")` in `_setup_styles`. Drop the
    Calibri/10 pt overrides.
  - Replace every `_add_topic_separator` call with `add_divider` (rows 11–14,
    19, 21–28) or `add_section_title` (all other titles). Titles are uppercase
    and unnumbered.
  - Move the Part II §2.1 content into PRESENTAZIONE DELL'AZIENDA after the
    light identity strip and the photo. Rename Part II.
  - Split `_add_dati_occupazionali_table` into DATI ANAGRAFICI and DATI
    OCCUPAZIONALI (bulleted environments).
  - Remove the `_add_azienda_header_table` calls except pages 4–5, where it
    becomes `add_kv_table(variant="light")`.
  - Rebuild the improvement table with 4 columns, coloured with `level_cell`.
    Delete `_start_landscape_section` and `_restore_portrait_section`.
  - Remove the photo captions. Add the 5 sign panels after FORMA E CATEGORIE DEI
    CARTELLI, two per page, each with `add_sub_title(in_toc=False)` and the
    picture at 15.3 cm width.
  - Environment sub-blocks and each risk category start on a new page. Category
    captions use `add_sub_title(in_toc=False)`.
  - Rebuild the DICHIARAZIONE signature table with `add_signature_grid`. Use "—"
    when a role has no name.
  - Route all DVR tables through the kit builders or the kit tokens; the
    private `_add_data_table` and `_add_key_value_table` delegate to the kit.
  - Call `add_back_cover(doc)` before `finish_document`.
- [ ] **Step 3:** Run the fixture script. Expected: every report key `true`.
  Then run `pytest tests/test_dvr_*.py tests/test_generators.py -q`. Expected:
  PASS, after updating expectations that pinned the old separators, numbering
  or landscape section.
- [ ] **Step 4: Visual check.** Convert `DVR_Luca_Fixture.docx` with LibreOffice,
  tile it at 40 dpi next to `templates/dvr_modello_luca_2026-10-20/DVR_RISCHIO MASTER.pdf`,
  and look at it. Cover, index, titles, dividers, tables, header, footer,
  signature page and back cover must match the model's page types. Fix
  deviations, then re-render.
- [ ] **Step 5:** Commit: `feat(dvr): rebuild the DVR Master on N2O's 20 Oct model`.

### Task 4: Company photo ("foto di presentazione")

**Files:**
- Create: `backend/app/models/azienda_foto_presentazione.py`
  (export it in `app/models/__init__.py` if models are registered there)
- Create: `backend/alembic/versions/<rev>_add_azienda_foto_presentazione.py`
  (`down_revision` = current head)
- Create: `backend/app/api/v1/azienda_foto_presentazione.py`
  (router registered under `/api/v1/aziende`)
- Modify: `backend/app/services/document_generator/data_loader.py`
- Create: `frontend/src/components/aziende/foto-presentazione-card.tsx`;
  modify: `frontend/src/components/aziende/tabs/panoramica-tab.tsx`
- Test: `backend/tests/test_azienda_foto_presentazione.py`

**Interfaces:**
- Produces:
  - Table `azienda_foto_presentazione` with columns `id` uuid pk, `azienda_id`
    (fk `aziende.id` ondelete CASCADE, unique), `document_image_bytes`
    LargeBinary not null, `content_type` String(64), `size_bytes` Integer,
    `created_at`, `updated_at`.
  - `PUT /api/v1/aziende/{azienda_id}/foto-presentazione` (multipart `file`)
    → 200 `{azienda_id, content_type, size_bytes, updated_at}`.
  - `GET …/foto-presentazione` → the image bytes, or 404.
  - `DELETE …/foto-presentazione` → 204.
  - PUT and DELETE depend on `require_capability(SURVEY_WRITE)`. All three are
    org-scoped the way `ambienti._get_ambiente_for_org` is.
  - Files: JPG, PNG or HEIC up to 10 MB, with the ambiente error strings. Bytes
    pass through `normalize_document_image`.
  - `load_foto_presentazione(db, azienda_id) -> tuple[bytes, str] | None`.
- Frontend card:
  - Title "Foto di presentazione".
  - Help text "Compare nel DVR sotto «Presentazione dell'azienda». JPG, PNG o
    HEIC fino a 10 MB."
  - Buttons "Carica foto" / "Sostituisci" / "Rimuovi", shown only with the
    survey-write capability from `usePermissions()`.
  - Preview via `fetchImageBlobUrl`.

- [ ] **Step 1: Write failing tests** (DB-backed, skip without Postgres):
  - `test_put_stores_normalised_bytes`
  - `test_put_replaces_existing`
  - `test_get_returns_image_or_404`
  - `test_delete_removes`
  - `test_other_org_gets_404`
  - `test_field_operator_without_survey_write_gets_403` (if a role lacks
    `SURVEY_WRITE`; otherwise assert the dependency is declared)
  - `test_rejects_gif_and_over_10mb`
  - `test_heic_is_converted_to_jpeg`

  Plus a non-DB test that the PUT and DELETE routes declare the capability
  dependency.
- [ ] **Step 2:** Run the tests. Expected: FAIL (import errors).
- [ ] **Step 3:** Implement the model, migration (upgrade and downgrade),
  router, loader and frontend card.
- [ ] **Step 4:** Run `pytest tests/test_azienda_foto_presentazione.py tests/test_permissions.py tests/test_billing_enforcement.py -q`
  and `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
  (CI does this against Postgres; locally run the test file and the import
  checks). Run `tsc --noEmit`. Expected: PASS.
- [ ] **Step 5:** Commit: `feat(aziende): foto di presentazione for the DVR`.

### Task 5: Preview contract (spec §4.3.1)

**Files:**
- Modify: `backend/app/services/document_preview.py`
- Modify: `backend/app/schemas/document.py`
- Modify: `backend/app/api/v1/documents.py` (preview response, part-scoped image ids)
- Test: `backend/tests/test_document_preview.py`

**Interfaces (Produces, all optional, backward compatible):**
- `DocumentPreviewResponse` adds:
  - `furniture: {header_left, header_right, footer_text, footer_logo_image_id} | None`
  - `page_setup: {width_pt, height_pt, margin_top_pt, margin_bottom_pt, margin_left_pt, margin_right_pt}`
  - `style_props: dict[str, StyleProps]`
- `StyleProps` = `{font_size_pt, bold, italic, caps, color, alignment, space_before_pt, space_after_pt, indent_left_pt, outline_level}`,
  all optional.
- Paragraph adds `outline_level`, `direct: StyleProps | None`,
  `list: {level, glyph} | None`, `page_role`, `background_image_id`,
  `section_break_after`. Run adds `caps`.
- Table adds `col_widths_pct: list[float] | None`; cell adds
  `v_align: "top" | "center" | "bottom" | None`.
- `parse_docx_to_blocks(docx_bytes)` keeps its signature. A new
  `parse_docx_preview(docx_bytes) -> dict` returns blocks plus furniture,
  page_setup and style_props, and the endpoint uses it.
- `extract_image_fast(docx_bytes, image_id)` also accepts `hdr:<part>:<rId>` and
  `ftr:<part>:<rId>`; part = `header1.xml`, `footer2.xml`, …

- [ ] **Step 1: Write failing tests.** Build a kit document via the Task 2
  functions:
  - `test_art_paragraph_reports_page_role_not_inline_image`
  - `test_furniture_reads_header_footer_and_logo`
  - `test_page_setup_from_final_section`
  - `test_style_props_resolve_chain_to_doc_defaults` (Heading 2 → 25 pt, caps,
    center, `003D74`)
  - `test_list_paragraph_reports_bullet_glyph`
  - `test_table_col_widths_and_valign`
  - `test_footer_image_served_by_part_scoped_id`
  - `test_override_on_divider_title_applies_and_other_addresses_stable`
    (Review Focus 4)
  - `test_old_document_parse_unchanged`: parse a document generated by `main`'s
    code. Commit a small `.docx` fixture made from the current `main` generator,
    `tests/fixtures/preview_legacy_dvr.docx`, before Task 2 lands, and compare
    `blocks` with a stored JSON snapshot (Review Focus 1).
- [ ] **Step 2:** Run `pytest tests/test_document_preview.py -q`. Expected: FAIL.
- [ ] **Step 3:** Implement. Resolve styles by walking `basedOn` to
  `docDefaults`. Lists come from `numPr` → `numbering.xml`
  (`abstractNum/lvl/lvlText`). Anchors with the `vera-art:` docPr name are
  excluded from `images`.
- [ ] **Step 4:** Run `pytest tests/test_document_preview.py tests/test_document_gdoc_editing.py -q`.
  Expected: PASS.
- [ ] **Step 5:** Commit: `feat(preview): page roles, resolved typography and furniture in the preview contract`.

### Task 6: Editor renders the document look (spec §4.3.2)

**Files:**
- Modify: `frontend/src/types/index.ts` (preview types mirror Task 5)
- Modify: `frontend/src/components/documents/editor/block-renderer.tsx`,
  `editable-paragraph.tsx`, `editor-toc.tsx`
- Modify: `frontend/src/app/(dashboard)/documents/[documentId]/page.tsx`
- Create: `frontend/src/components/documents/editor/sheet.tsx` (sheet frame: art
  background, header and footer bands)
- Create: `frontend/src/components/documents/editor/doc-typography.ts`
  (effective props → CSS)

**Interfaces:**
- Consumes: Task 5 response fields.
- `groupIntoSheets(blocks): Sheet[]`, where
  `Sheet = {role: "cover" | "divider" | "back_cover" | "content", backgroundImageId: string | null, blocks: PreviewBlock[]}`.
  A new sheet starts at `page_break_before`, after `section_break_after`, or at a
  block with `page_role`.
- `effectiveParagraphStyle(p, styleProps): CSSProperties` and
  `effectiveRunStyle(run, paragraphEffective): CSSProperties`, in pt units with
  `font-family: Arial, "Liberation Sans", Helvetica, sans-serif`.
- Sheet geometry from `page_setup` at 96 dpi; fall back to A4 at 2.0/2.0/2.5/2.0
  cm when absent (old cached responses).
- Art sheets have no header or footer bands. Content sheets get the bands from
  `furniture`. No page numbers.
- The TOC sidebar uses `outline_level ?? heading_level`.
- Editing behaviour (click, debounce, overrides, "Modificato", "Ripristina") is
  unchanged.

- [ ] **Step 1:** Update the types, then run `tsc --noEmit`. Expected: errors
  at the old call sites.
- [ ] **Step 2:** Implement the sheets, typography, art sheets, bands, tables
  (`col_widths_pct`, `v_align`, black ½ pt borders) and the narrow-screen scale
  (no horizontal scroll at 390 px).
- [ ] **Step 3:** Run `tsc --noEmit` and `next build`. Expected: both clean.
- [ ] **Step 4:** Playwright check against a local stack, or a static harness
  page that renders a saved preview JSON of the fixture DVR. Take screenshots at
  1280 and 390 wide.
  - Expected: cover and divider sheets show their art; content sheets show the
    header and footer bands; Arial 25 pt titles; blue table headers.
  - Expected: an old-document preview JSON still renders.
- [ ] **Step 5:** Commit: `feat(editor): documents render with their own look in the browser`.

### Task 7: Code-built attachments adopt the kit (spec §4.4)

**Files:**
- Modify: `allegato_mmc.py`, `allegato_vdt.py`, `allegato_microclima.py`,
  `allegato_microclima_severo.py`, `_biologico_common.py`
  (all under `backend/app/services/document_generator/`)

**Interfaces:**
- Consumes: `setup_document(profile="attachment")`, `add_cover`, the table
  builders, `add_back_cover` and `finish_document` from Task 2.

- [ ] **Step 1:** Write `test_attachments_use_kit` in `tests/test_generators.py`.
  For each of the 7 documents via `scripts/verify_all_generators` fixtures:
  - the first section starts with the `cover_vera` marker and the last with
    `back_vera`;
  - no run declares a font other than Arial;
  - table headers fill `4F81BD`.

  Run it. Expected: FAIL.
- [ ] **Step 2:** Replace the hard-coded `Pt(...)`, `font.name` and navy header
  literals with `TYPE_SCALE` roles and kit builders. Call `add_back_cover`
  before `finish_document`.
- [ ] **Step 3:** Run `pytest tests/test_generators.py -q` and
  `python -m scripts.verify_all_generators <out>`. Render each document with
  LibreOffice and look at the cover, a table page and the back cover. Expected:
  PASS.
- [ ] **Step 4:** Commit: `feat(documents): the seven code-built attachments take the new look`.

### Task 8: Donor-template attachments and HACCP forms (spec §4.4)

**Files:**
- Create: `backend/app/services/document_generator/donor_cover.py`. Port
  `strip_donor_cover` from PR #82 (`git show af2a5d5:backend/app/services/document_generator/design.py`)
  together with its tests from `af2a5d5:backend/tests/test_document_cover.py`
  that cover stripping.
- Modify: `allegato_gestanti.py`, `allegato_incendio.py`, `allegato_stress.py`,
  `duvri.py`, `pos.py`, `pee_azienda.py`, `pee_comune.py`, `haccp_manuale.py`,
  `haccp_forms.py`
- Test: `backend/tests/test_donor_cover.py`

**Interfaces:**
- `strip_donor_cover(doc) -> bool`: same contract as in PR #82.
- `normalize_fonts(doc, family: str = FONT_FAMILY) -> int`: sets `rFonts`
  (ascii, hAnsi, eastAsia, cs) on every style and on every run in body, headers
  and footers. Returns the number of runs changed. Never touches sizes.
- HACCP forms: `normalize_fonts` plus `finish_document` only. No cover, no back
  cover.

- [ ] **Step 1:** Write failing tests:
  - `test_strip_donor_cover_on_real_templates` (ported)
  - `test_normalize_fonts_sets_arial_keeps_sizes`
  - `test_donor_attachments_get_kit_cover_and_back_cover`
  - `test_haccp_forms_have_no_cover_art`
- [ ] **Step 2:** Implement and wire into the 8 donor generators: strip the
  donor cover, `add_cover` at the top, `normalize_fonts`, `add_back_cover`,
  `finish_document`.
- [ ] **Step 3:** Run `pytest tests/test_donor_cover.py tests/test_donor_front_matter.py tests/test_generators.py tests/test_duvri_body.py -q`
  and `verify_all_generators`. Render all 8 with LibreOffice and look at them;
  Arial is ~8–10 % wider, so check that no table overflows the page. Expected:
  PASS.
- [ ] **Step 4:** Commit: `feat(documents): donor-template attachments take the new cover, Arial and back cover`.

### Task 9: Documentation, verification, delivery

**Files:**
- Modify: `.claude/rules/document-generation.md`,
  `docs/context/DVR_TEMPLATE_MAPPING.md` (new page map section), `CLAUDE.md`
  (one line: documents use Arial — N2O requirement; never Calibri or Avenir)

- [ ] **Step 1:** Update the docs. Commit: `docs: the design kit and the new DVR page map`.
- [ ] **Step 2:** Run the full backend suite, `lint-imports --config .importlinter`,
  `verify_all_generators`, `verify_dvr_luca_fixture`, frontend `tsc` and
  `next build`. Expected: all green.
- [ ] **Step 3:** Render all 17 documents and the side-by-side DVR comparison.
  Attach the comparison image to the PR description.
- [ ] **Step 4:** Whole-branch review by a fresh reviewer subagent. Fix findings.
- [ ] **Step 5:** Push, update PR #91 (title, body, test plan), and wait for
  Backend CI and claude-review to go green. Fix anything red.
- [ ] **Step 6:** Deploy: mark the PR ready and merge it to `main` (the Render
  blueprint auto-deploys `main`; `alembic upgrade head` runs pre-deploy).
- [ ] **Step 7:** Smoke-test production:
  - API `/docs` responds and the frontend loads.
  - The new route appears in the OpenAPI schema.
  - Report what could and could not be verified without production
    credentials.
