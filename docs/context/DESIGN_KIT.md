# Design kit — the layout of every generated document

All 17 documents share one look, taken from N2O's DVR model of 20 Oct 2026. Spec (binding): `docs/superpowers/specs/2026-11-10-document-layout-redesign-design.md`. Visual ground truth for the DVR: `templates/dvr_modello_luca_2026-10-20/DVR_RISCHIO MASTER.pdf`. The DVR's page map, row by row: `DVR_TEMPLATE_MAPPING.md`, section "Page map".

The kit is two modules: `backend/app/services/document_generator/design.py` (page types, running header and footer, art) and `docx_utils.py` (tokens, table builders, paragraphs).

## Tokens

- **Arial in every slot.** `FONT_FAMILY` (ascii, hAnsi, eastAsia, cs; theme fonts dropped). Never Calibri or Avenir: N2O wants a document that does not reflow between Windows and Mac.
- **Sizes come from `TYPE_SCALE`**: body 12, tables 10, section title 25, sub-title 12, part label 9, header 9, footer 8.5. No literal `Pt()` sizes in generators.
- **Colours**: `BRAND_NAVY` 003D74 (titles, labels), `BRAND_TABLE_HEADER` 4F81BD (table header rows), `BRAND_SURFACE_HEX` F6F9FC (zebra), `RISK_COLORS` for levels via `level_cell`.

## Setting up and finishing a document

- `setup_document(doc, profile="dvr" | "attachment")`: A4, margins, Arial on every style, the heading roles. The DVR profile makes Heading 2 the 25 pt centred section title; the attachment profile keeps 16/13/12 pt chapter headings.
- `finish_document(...)` last, before `doc.save`: running header and footer on every section, file properties, orphaned donor parts pruned, and (`fill_cover=True`) a donor's cover forms filled.
- Running header: document title | client, navy capitals over a hairline. Footer: the organization's uploaded logo, else the VERA mark (an unreadable logo prints the firm name), then "Rev. NN del gg/mm/aaaa" and "Pag. X di Y". A section whose first paragraph is an art page has an empty first-page header and footer; every other first page carries them.

## Page types (design.py)

| Function | Use it for |
|---|---|
| `add_art_cover(doc, key)` | The DVR's picture-only cover (title baked into the art) |
| `add_cover(doc, title=…, azienda=…, …)` | Every attachment: VERA art behind a live title block |
| `add_divider(doc, title, key, part_label=None)` | A topic on its own section, opening on a full-page photo; title is Heading 2 mid-page |
| `add_section_title(doc, title, part_label=None)` | The in-page title on a new page (Heading 2) |
| `add_sub_title(doc, text, in_toc=True, new_page=False)` | Heading 3; `in_toc=False` for captions the index leaves out |
| `add_back_cover(doc)` | The closing art page, last |

`add_revision_table` (the one-row Storico: Rev. · Motivazione · Data) and `add_toc` / `finalize_toc` (a real TOC field with a cached outline) complete the front matter. Generators write their own headings with `docx_utils.add_heading`, which writes one paragraph even when a donor lacks the `Heading N` style.

## Art

- `ART` in `design.py` maps each key to a file in `backend/assets/document_art/`; `backend/scripts/extract_document_art.py` re-extracts them from N2O's model DOCX.
- Every art picture is anchored behind the text at page size, alone in an empty paragraph whose `wp:docPr` is named `vera-art:<role>:<key>` (role `cover`, `divider` or `back_cover`). The running header/footer logic and the editor's preview parser (`backend/app/services/document_preview.py`) find art pages by that marker. **Never rename it.**
- Missing or unreadable art never fails generation: a divider falls back to `div_generico`, then to a white page with its title; an attachment cover is white with its live title; the DVR cover and the back cover are left out. A cover never borrows a divider photo. Each case logs a warning.

## Tables (docx_utils.py)

- `add_data_table(doc, headers, rows, column_widths_cm=…)`: header row 4F81BD with white bold text (`style_header_row`), repeating on every page; zebra rows; black ½ pt borders; numbers and dashes centred.
- `add_kv_table(doc, rows, variant="blue" | "light")`, `add_role_band`, `add_signature_grid`, `level_cell(cell, level)`, `add_bullets` (real list numbering, also inside cells).
- **Never `cantSplit` on a data row.** LibreOffice loops forever on a keep-together row taller than a page (commit `e0875fa`). Only header rows and short label rows are kept together.

## Donor templates (donor_cover.py)

Gestanti, Incendio, Stress, DUVRI, POS, both PEE and the HACCP manual open one of N2O's completed documents from `templates/`: `strip_donor_cover` removes the donor's cover, `insert_kit_cover_at_top` puts the kit cover in its place (after the body is complete; `revision_table=True` adds the kit's Storico on the next page for the donors whose own sat on the stripped cover: Incendio, Stress, both PEE, POS), `normalize_fonts` sets Arial on styles, runs and list levels at the donor's own sizes (Symbol, Wingdings and Webdings bullets keep their font). Then `add_back_cover` and `finish_document`, with `fill_cover=True` where the donor keeps label | value forms to fill. The HACCP record forms get Arial and the running header and footer only: no cover, no back cover.

## Checking a change

`python -m scripts.verify_all_generators <outdir>` (17/17) and `python -m scripts.verify_dvr_luca_fixture --output-dir <outdir>` (every key true), from `backend/`. Then render through LibreOffice (`soffice --headless --convert-to pdf`) and look at the pages; tests: `test_design_kit.py`, `test_donor_cover.py`, `test_document_preview.py`.
