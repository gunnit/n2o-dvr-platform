# Document layout redesign — N2O's DVR model of 20 Oct 2026 — Design Spec

**Date:** 2026-11-10
**Author:** Gregor Maric (Niuexa) + Claude
**Status:** Draft — awaiting review
**Supersedes:** the table-based cover of draft PR #82 (unmerged, 2026-09-07). Its
donor-cover stripping is reused (§4.4).

## Goal

Make every generated document look like the model N2O sent, and make the
in-browser editor show documents the way they print. Luca's brief for the model
(email of 2026-10-20): *"il documento prodotto rispecchi il più possibile il
modello che ti sto inviando, senza necessità di ulteriori interventi manuali."*

Success means:

1. The DVR Master generated for N2O's test company matches the model page type
   by page type: cover, index, titles, dividers, tables, header, footer,
   signature page, back cover. Nobody has to touch it in Word.
2. The other 16 documents share the same visual language (type, colour, tables,
   header, footer, covers). Their own structure waits for N2O's models.
3. `/documents/[id]` shows any document in that same look and stays
   click-to-edit.

## 1. Source material

| Date | From | Content |
|---|---|---|
| 2026-05-12 | Luca Marchetti | "LOGHI + IMPAGINAZIONE DVR": logo images and screenshots |
| 2026-07-27 | Eliana Esposito (cc Luca) | Logo and blue tone. *Font Arial (bold when needed), size 10; the document must not change between Windows and Mac* |
| 2026-08-03 | Luca | 11 fixes to the printed RISCHIO MASTER, including a divider cover per topic and a page of its own for the employer's declaration (implemented 2026-08-14) |
| 2026-09-11 | Gregor | Before/after of the unified layout. Open point 3: what the DVR cover shows for consultancies other than N2O |
| 2026-10-06 | Luca | "rivediamo il layout delle grafiche dei documenti e ti mandiamo i definitivi" |
| **2026-10-20** | **Luca** | **The model: `DVR_RISCHIO MASTER.pdf` (98 pp.) and `.docx` (78 MB), sent as iCloud Mail Drop links that expire 2026-11-19** |
| 2026-10-22 | Luca | Once the MASTER layout is ready, N2O tests it and then prepares the other attachments |
| 2026-10-29 | N2O | Asks whether the "grafica … del Rischio Master" is feasible |

The PDF is archived as
`templates/dvr_modello_luca_2026-10-20/DVR_RISCHIO MASTER.pdf` (sha256
`6774414a…d21661e`), following the dated-folder convention of
`templates/allegato_chimico_luca_2026-05-19/`. It is not the same file as the
old donor `templates/DVR RISCHIO MASTER.docx`.
The 78 MB DOCX stays out of git. Its artwork is extracted into
`backend/assets/document_art/` (§4.1.5). Both PDF and DOCX contain N2O staff
names and codici fiscali, like the other completed documents in `templates/`.

## 2. What the model is (verified facts)

**It is our own output, restyled by hand.** It is the DVR v4 our platform
generated on 2026-10-06 for the test company N2O S.R.L. (org "Niuexa Test",
"Rev. 03 del 06/10/2026"), re-laid out in Word for Microsoft 365. Evidence:
`header1/3/5.xml` and `footer1/3/5.xml` are our `design._write_running`
output byte for byte. `styles.xml` still holds our Calibri styles. The new
look is direct formatting applied run by run.

**Geometry:** A4 portrait, margins 2.0 / 2.0 / 2.5 / 2.0 cm (top, bottom,
left, right), header and footer at 1.0 cm. This equals `design.py` today. The
model's last section has 2.5 cm top and bottom margins, but that is an
artifact of our `_restore_portrait_section` after the landscape improvement
table, which the model turned back to portrait.

**Typography:**
- Avenir Next LT Pro for everything, Demi for titles and headers. It is not
  embedded in the file.
- 12 pt for body and table text (≈60 k characters).
- Section titles 25 pt, running header 9 pt, footer 8.5 pt.

**Colours:**

| Use | Colour |
|---|---|
| Titles, labels, header | navy `003D74` |
| Table header rows | `4F81BD` with white text (149 cells) |
| Zebra rows | `F6F9FC` |
| Risk levels (accettabile, modesto, grave, gravissimo) | `15BE53`, `F59E0B`, `F97316`, `EF4444` |
| Notes | `666666` italic |

Table borders come from the Table Grid style: thin black.

**Page types:**
- **Cover:** one flat bitmap, 1055×1491 px (≈128 dpi). The title,
  "D.LGS. 81/08", the illustration and the **VERA ITALIA SRL** mark are all
  baked into the picture.
- **23 dividers** using 21 distinct pale-blue photos. Each photo is anchored
  behind the text at page size, and the title is live text.
- **In-page 25 pt titles** for every other section.
- **Back cover:** flat 1792×2400 art with the VERA mark.

**Running header:**
- Left: "DOCUMENTO DI VALUTAZIONE DEI RISCHI"
- Right: client name
- 9 pt bold navy capitals, hairline `C9D3DF` below.

**Footer:**
- VERA logo (2.4 × 0.85 cm), then "Rev. 03 del 06/10/2026"
- Right: "Pag. X di Y"
- Hairline above.

**Deliberate edits N2O made by hand.** Git history shows our generator had
produced the original forms since 2026-08-07, so N2O removed or changed these
on purpose:
- Titles in capitals and unnumbered ("1. Presentazione dell'Azienda" →
  "PRESENTAZIONE DELL'AZIENDA").
- Separator pages only for 23 topics; every other section opens with an
  in-page title.
- The activity description moves from Part II §2.1 into "Presentazione
  dell'azienda". Part II is renamed "PARTE II — METODOLOGIA DI VALUTAZIONE".
- "Dati occupazionali" is split into **DATI ANAGRAFICI** (Nominativo, Codice
  Fiscale, Tipologia contrattuale) and **DATI OCCUPAZIONALI** (Nominativo,
  Mansione, Ambiente di lavoro as a bulleted list).
- The company identity table that repeated at the start of Parts II–IV and of
  each environment is gone.
- The improvement table has 4 columns (Misura di Miglioramento, Risorse,
  Responsabile, Priorità) in portrait, with Priorità coloured.
- The "Fig. N — filename" captions under environment photos are gone.
- The "ex art. 17 …" line under "DOCUMENTO ELABORATO SUGLI ESITI DELLA
  VALUTAZIONE DEI RISCHI" is gone.
- Five signage panels were added: divieto, avvertimento, obbligo, emergenza
  and evacuazione, prevenzione incendi.
- A company photo was added under "Presentazione dell'azienda".
- Each environment sub-block and each risk category starts on a new page.

**Not copied:**
- Avenir Next LT Pro (decision 1).
- Empty-paragraph spacers.
- The "R IUNIONE PERIODICA" typo.
- A stray copy of an art image on the last "Mansioni" page.
- The incomplete index; ours is built from headings.
- The 2.5 cm section.
- The four example rows of the revision history, which carry future dates. We
  keep printing the real history.

**Only one environment** (UFFICIO AMMINISTRATIVO) is laid out in Part III. How
the layout repeats per environment is extrapolated in §4.2.

## 3. Decisions (Gregor, 2026-11-10)

| # | Decision | Choice | Why |
|---|---|---|---|
| 1 | Font | **Arial** in every slot, as one constant | The July requirement is functional: no reflow between Windows and Mac. Avenir Next LT Pro is a Microsoft 365 cloud font and isn't embedded, so LibreOffice, Google Docs and Word without 365 substitute it. Arial is everywhere; Liberation Sans has its metrics. |
| 2 | Sizes | **12 pt body, 10 pt tables**, model hierarchy for titles | At 12 pt the model's five-column risk tables break words mid-word (p. 37, "corrispondenz / a"). 10 pt is the July size. |
| 3 | Branding | **VERA cover and back cover for every org. Footer shows the org's uploaded logo, else the VERA mark.** White-label cover later | The cover art is one flat bitmap with the mark baked in. A white-label cover needs layered art from N2O. |
| 4 | Editor | **Same look, flexible sheets**, no page numbers on screen | A browser can't reproduce Word's pagination. Wrong page numbers would mislead reviewers. |
| 5 | Approach | **A: design kit in code**, direct formatting, roles in heading styles | One place to change the look. Renders the same in Word, LibreOffice, Google Docs and the preview parser. |
| 6 | Company photo | **New upload, in phase 1** | The model has one, and "senza interventi manuali" requires a source for it. |
| 7 | Model archive | PDF in `templates/` | iCloud links expire 2026-11-19. |
| 8 | Phasing | 3 PRs: kit + DVR + photo → editor → other 16 documents | N2O is waiting to test the MASTER. |

Rejected approaches:
- **B, Word template with named styles.** Table-style conditional formatting
  imports unreliably in LibreOffice and Google Docs. It would also bring back
  the donor-template baggage the 2026-09-03 audit removed.
- **C, restyle pass after generation.** It infers each element's role from
  text and formatting, which is fragile.

## 4. Design

### 4.1 Design kit (`design.py`, `docx_utils.py`)

#### 4.1.1 Tokens

| Token | Value |
|---|---|
| `FONT_FAMILY` | `"Arial"`, set on ascii, hAnsi, eastAsia and cs, on styles and on every run the kit writes |
| `TYPE_SCALE.body` | 12 pt, line spacing 1.08, 4 pt after. Body paragraphs are justified by the kit's `add_body_paragraph` helper, **not** on the Normal style, so table cells (which inherit Normal) stay left-aligned |
| `TYPE_SCALE.table` / `table_header` | 10 pt / 10 pt bold white |
| `TYPE_SCALE.section_title` | 25 pt bold navy, capitals, centred |
| `TYPE_SCALE.sub_title` | 12 pt bold navy, centred |
| `TYPE_SCALE.part_label` | 9 pt bold navy, capitals, centred |
| `TYPE_SCALE.front_heading` | 14 pt bold navy, left (INDICE, Premessa) |
| `TYPE_SCALE.cover_title` | 26 pt bold navy (attachment covers only) |
| `TYPE_SCALE.header` / `footer` | 9 pt bold navy capitals / 8.5 pt slate `64748D` |
| `TYPE_SCALE.note` | 10 pt italic `666666` |
| `BRAND_NAVY` | `003D74` (unchanged) |
| `BRAND_TABLE_HEADER` (new) | `4F81BD` |
| `BRAND_SURFACE` | `F6F9FC` (zebra rows, light label cells) |
| `BRAND_DEEP` | `061B31` body ink (unchanged) |
| `BRAND_RULE` | `C9D3DF`, header and footer hairlines only |
| Table borders | single, size 4 (½ pt), colour auto (black). Was `C9D3DF` |
| Geometry | A4 portrait, 2.0 / 2.0 / 2.5 / 2.0 cm, header and footer at 1.0 cm. **No landscape sections in the DVR** |

#### 4.1.2 Page types

Each page type is one kit function. Every one degrades gracefully: a missing
asset or bad data never crashes generation.

- **`add_art_cover(doc, art_key, *, title_block=None)`.** A full-page picture
  anchored to the page origin, behind text, with no wrapping. It is sized to
  the section's actual page dimensions, not to constants, because donor
  templates keep their own page setup (§4.4). It opens the first section,
  which gets no header or footer on its first page.
  - DVR: `art_key="cover_dvr"` with no title block. The title is in the art.
  - Attachments: `art_key="cover_vera"` (the back-cover art) plus a live title
    block in the upper third. The block holds the eyebrow, the title
    (`cover_title`), the legal basis, the client (name, seat, P.IVA, ATECO),
    "Revisione NN · gg/mm/aaaa", and the "Documento elaborato da" letterhead,
    as today.
- **`add_divider(doc, title, art_key, *, part_label=None)`.** Starts a **new
  section on a new page**. That section shows no header or footer on its first
  page and the running header and footer after it.
  - Content: the art in its own empty paragraph, then an optional part label,
    then the title as **Heading 2** (`section_title`), set ~11 cm from the top
    so it sits mid-page.
  - The art lives in a separate paragraph, so the title stays editable in the
    editor and override addresses don't shift.
- **`add_section_title(doc, title, *, part_label=None, new_page=True)`.** The
  in-page title: page-break-before, optional part label (Heading 1 with direct
  formatting), title as Heading 2.
- **`add_sub_title(doc, text, *, in_toc=True)`.** Heading 3 when `in_toc`,
  otherwise a plain paragraph with the same look (used for risk-category
  captions).
- **`add_back_cover(doc, art_key="back_vera")`.** New section, one page, no
  header or footer, art at full page.
- **`add_running_header_footer(...)`** is replaced:
  - **Header:** document title in capitals | client name in capitals, over a
    hairline.
  - **Footer:** inline logo (height ≤ 0.85 cm, width ≤ 2.4 cm), two spaces,
    "Rev. NN del gg/mm/aaaa", a right tab, "Pag. {PAGE} di {NUMPAGES}", under a
    hairline.
  - Every section gets the running header and footer. The first-page
    header/footer is empty **exactly on the sections whose first paragraph
    carries an art marker** (cover, dividers, back cover). Header and footer
    suppression is therefore explicit per section, not a side effect of the
    picture covering the header.
- **Art marker.** Every art picture gets `wp:docPr name="vera-art:<role>:<key>"`
  with role `cover`, `divider` or `back_cover`. The preview parser (§4.3) and
  `finish_document` read it.

#### 4.1.3 Table builders

All tables:
- Table Grid with black ½ pt borders, centred, full text width.
- Header rows repeat on every page, and no row splits across a page break
  (`cantSplit`, as today).
- 10 pt text, left-aligned. Header cells, numbers, levels and "—" are centred.

| Builder | Look | Used for |
|---|---|---|
| `add_data_table(headers, rows, widths)` | header `4F81BD` with white bold text, zebra `F6F9FC` | most tables |
| `add_kv_table(rows, variant="blue")` | label column `4F81BD` with white bold text; value white | Anagrafica, environment identity |
| `add_kv_table(rows, variant="light")` | label navy bold on `F6F9FC` | identity strips on pp. 4–5 |
| `add_role_band(title, value)` | full-width `4F81BD` band with white bold centred text, value row centred | Organizzazione aziendale della sicurezza |
| `add_signature_grid(cells)` | 2-column grid: navy `003D74` header, name row, 2.5 cm blank signing row | Timbro e Firma, declaration |
| `level_cell(cell, level)` | fill with the risk or priority colour, white bold centred | risk index, priority |

Bulleted lists inside cells use real list numbering with "▪"/"•", as in the
model. They are not typed characters.

#### 4.1.4 Roles and styles

Each document's `styles.xml` is set up by `setup_document(doc, profile)`:

| Role | DVR profile | Attachment profile |
|---|---|---|
| Heading 1 | front-matter heading (14 pt, left). Part labels apply direct formatting on top | chapter heading, 16 pt bold navy, left |
| Heading 2 | section title (25 pt, capitals, centred) | 13 pt bold navy, left |
| Heading 3 | sub-title (12 pt bold navy, centred) | 12 pt bold navy, left |
| Normal | Arial 12, ink `061B31` | Arial 12, ink `061B31` |

The index field stays `TOC \o "1-3" \h \z \u`. `finalize_toc` keeps building
its cached entries from Heading 1–3. Risk-category captions are kept out of the
index.

#### 4.1.5 Assets (`backend/assets/document_art/`)

- **Extraction.** Pictures come from the model DOCX. Each is centre-cropped to
  A4 proportion (0.7071) and resized to 1654 px wide (200 dpi at 21 cm).
- **Encoding.** JPEG quality 80, progressive. Measured totals: dividers ≈2.1 MB,
  cover 134 KB, back cover 211 KB.
- **File size.** A DVR grows from ~0.2 MB to ~2.6 MB. python-docx stores
  repeated pictures once per file, so extra environments add almost nothing.
- **Manifest.** `ART` in `design.py` maps keys to files (Appendix A). An unknown
  key falls back to `divider_generico`. A missing file produces a white divider
  with the title only, plus a warning log.
- **Logo.** `vera_italia_mark.png` (640×226) becomes the default document logo
  and replaces `logo.png` as the fallback in `resolve_logo_source`.
  `n2o_vera_dvr.png` (the old "N2O VERA" mark) is retired.

### 4.2 DVR Master

#### 4.2.1 Page map

Legend: **D** = divider page with art; **T** = in-page title; *italic* = part
label.

| # | Type | Content |
|---|---|---|
| 1 | art | Cover (`cover_dvr`). No client identity, as in the model |
| 2 | — | **INDICE** (front heading), full index with dot leaders. Word refreshes page numbers on open |
| 3 | — | **Premessa** (front heading) |
| 4 | T | DOCUMENTO ELABORATO SUGLI ESITI DELLA VALUTAZIONE DEI RISCHI. Light identity strip (Azienda, Sede Legale, Sede Operativa), revision history (navy header), Timbro e Firma |
| 5 | T | *PARTE I — DATI GENERALI DELL'AZIENDA*. PRESENTAZIONE DELL'AZIENDA: light identity strip, **company photo** (≤ 16.5 × 11 cm, centred, if present), then the activity description, ATECO/ciclo produttivo and regional references (moved from Part II §2.1) |
| 6 | T | ANAGRAFICA AZIENDALE: blue key/value table |
| 7 | T | DATI ANAGRAFICI: Nominativo, Codice Fiscale, Tipologia contrattuale |
| 8 | T | DATI OCCUPAZIONALI: Nominativo, Mansione, Ambiente di lavoro (bulleted) |
| 9 | T | ORGANIZZAZIONE AZIENDALE DELLA SICUREZZA: role bands for Datore di Lavoro, RSPP, RLS, Medico Competente; then the Addetti Primo Soccorso and Antincendio tables |
| 10 | T | AMBIENTI DI LAVORO: table plus italic note |
| 11 | D | SERVIZI IGIENICO-ASSISTENZIALI → text |
| 12 | D | MACCHINE, ATTREZZATURE ED IMPIANTI → global table (one row per equipment, environments listed in the cell) |
| 13 | D | SOSTANZE, PRODOTTI E PREPARATI CHIMICI → table plus hazard notes |
| 14 | D | ELENCO FATTORI DI PERICOLO (Riferimento) → reference tables |
| 15 | T | *PARTE II — METODOLOGIA DI VALUTAZIONE*. DEFINIZIONI |
| 16 | T | METODOLOGIA DI VALUTAZIONE DEI RISCHI, with the level table (I, Livello, Azione, Tempistica) |
| 17 | T | SCALA DI PROBABILITÀ (P) |
| 18 | T | SCALA DEL DANNO (D) |
| 19 | D | *PARTE III — VALUTAZIONE DEI RISCHI PER AMBIENTE DI LAVORO*. IDENTIFICAZIONE DELL'AMBIENTE DI LAVORO E DEGLI ADDETTI (**once**) |
| 20 | T | For each environment in saved order: **name** as section title, with blue identity table and addetti table |
| 20a | new page | Sub-title "Macchine, Attrezzature ed Impianti — ‹ENV›" plus table |
| 20b | new page | Sub-title "Foto e Planimetrie — ‹ENV›" plus photos at 12 × 9 cm, **no filename captions** |
| 20c | new page | Sub-title "Identificazione dei Fattori di Rischio — ‹ENV›" plus checklist |
| 20d | new page each | One per applicable risk category: caption (STRUTTURE, MACCHINE, …; not in the index) plus the five-column risk table |
| 21 | D | MANSIONI CHE ESPONGONO I LAVORATORI A RISCHI SPECIFICI → table |
| 22 | D | DISPOSITIVI DI PROTEZIONE INDIVIDUALE (DPI) → one sub-title per person plus DPI table |
| 23 | D | SEGNALETICA DI SICUREZZA → text, colour code, sign shapes, **5 sign panels** with sub-titles, two per page |
| 24 | D | PROGRAMMA DI INFORMAZIONE, FORMAZIONE E ADDESTRAMENTO → status note plus table |
| 25 | D | *PARTE IV — PROGRAMMA DI MIGLIORAMENTO*. PROGRAMMA E PROCEDURE DI ATTUAZIONE DELLE MISURE DI MIGLIORAMENTO → intro plus **4-column** table, portrait |
| 26 | D ×11 | GESTIONE LEGGI E REGOLAMENTI · SORVEGLIANZA SANITARIA (with occupational diseases by mansione) · INFORMAZIONE, FORMAZIONE ED ADDESTRAMENTO · RIUNIONE PERIODICA · INFORTUNI · COMPORTAMENTI SCORRETTI DEI LAVORATORI · DPI · INFRASTRUTTURE · LAVORATORI PARTICOLARMENTE SENSIBILI AL RISCHIO · ACQUISTI · LAVORAZIONI AFFIDATE IN APPALTO |
| 27 | D | DOCUMENTI CORRELATI AL PRESENTE DVR → navy bold bullet list of attachments |
| 28 | D | DICHIARAZIONE DEL DATORE DI LAVORO → declaration, "DICHIARA" (bold navy, centred), the numbered statements, "‹COMUNE›, lì ‹data›" (bold navy), 2×2 signature grid (Datore di Lavoro, Responsabile del S.P.P., Medico Competente, RLS) |
| 29 | art | Back cover (`back_vera`) |

#### 4.2.2 Changes against today's generator

- `_add_topic_separator` is replaced by `add_divider` (rows 11–14, 19, 21–28)
  or `add_section_title` (all other titles). Numbering ("1.", "2.3", "4.10")
  disappears and titles are in capitals.
- Part II §2.1 is removed and its content moves into row 5. Part II's label
  changes.
- `_add_dati_occupazionali_table` splits into two tables (rows 7–8). The data
  is unchanged.
- `_add_azienda_header_table` is no longer called at the start of Parts II–IV
  or per environment. It survives only as the identity strip on pages 4–5.
- `_add_improvement_program_table`: 4 columns, portrait, priority cell
  coloured. `_start_landscape_section` and `_restore_portrait_section` are
  deleted. Rischio, Attività/Procedura and Scadenza leave the printed table;
  the data stays in the database.
  - Legal check: art. 28 c.2 lett. c (programme over time) is met by the intro,
    which maps priority to timing. Lett. d (procedures and roles) is met by
    Responsabile plus the GESTIONE sections. Flagged to N2O (§7).
- Environment photos lose the "Fig. N — filename" captions.
- New static content: 5 sign panels.
- New data: the company photo (§4.2.4).
- The VERA cover image changes. The fixture audit's `vera_cover` hash
  expectation moves to the new art.

#### 4.2.3 Extrapolations from a one-environment model (to confirm with N2O)

- The Part III divider appears **once**. Each environment opens with its name as
  a section title.
- Each environment sub-block and each risk category starts on a new page, as in
  the model. This costs pages: the model spends 17 pages on one environment.

#### 4.2.4 Company photo ("foto di presentazione")

- **Storage:** new table `azienda_foto_presentazione`, 1:1 with the azienda
  (unique `azienda_id`, cascade delete). Columns: `document_image_bytes`
  (LargeBinary, normalised through `normalize_document_image`, which also
  converts HEIC), `content_type`, `size_bytes`, `created_at`, `updated_at`.
  Bytes live in the database, like `AmbienteFoto.document_image_bytes`, because
  the Celery worker doesn't share the API's disk. It is a separate table so
  azienda list queries never load the bytes.
- **API:** `PUT/GET/DELETE /api/v1/aziende/{azienda_id}/foto-presentazione`.
  - PUT and DELETE: `require_capability(SURVEY_WRITE)` plus org scoping, the
    same gates as environment photos. It is survey data, not billable work, so
    there is no entitlement gate; that matches the existing classification.
  - GET: org-scoped read, never role-gated.
  - Accepts JPG, PNG or HEIC up to 10 MB, with the environment-photo error
    strings.
- **UI:** a "Foto di presentazione" card on the azienda page (Panoramica tab):
  preview, Sostituisci, Rimuovi.
- **Generator:** `data_loader` loads it. Row 5 prints it when present; otherwise
  there is no photo slot.

### 4.3 Editor (`document_preview.py` + `/documents/[id]`)

#### 4.3.1 Preview contract additions

All additions are optional fields, so existing clients and old documents keep
working.

- **Response:**
  - `furniture`: `header_left`, `header_right`, `footer_text` (the revision
    line) and `footer_logo_image_id`. Read from the default header and footer
    of the body's final section.
  - `page_setup`: `width_pt`, `height_pt`, `margin_top_pt`,
    `margin_bottom_pt`, `margin_left_pt`, `margin_right_pt`, from the body's
    final `sectPr`. The 8 donor-template generators don't call
    `setup_document` and keep their template's geometry, so the editor must
    not assume the kit's margins.
  - `style_props`: a table keyed by paragraph style name, holding each style's
    *resolved* properties (style chain and docDefaults): `font_size_pt`,
    `bold`, `italic`, `caps`, `color`, `alignment`, `space_before_pt`,
    `space_after_pt`, `indent_left_pt`, `outline_level`. Paragraphs and runs
    send only their direct formatting, which keeps the payload small.
- **Paragraph** (top-level and cell):
  - `outline_level` (1–9 or null), used for the sidebar index.
  - `direct` (direct paragraph formatting, same keys as `style_props`).
  - `list` (`{level, glyph}` or null), from `numPr` and `numbering.xml`.
  - `page_role` (`cover`, `divider`, `back_cover` or null) and
    `background_image_id`. These are set on the paragraph that carries a
    `vera-art:` anchor; the anchor is **not** reported as an inline image.
  - `section_break_after` (bool).
- **Run:** adds `caps`. `size` (pt, null when inherited) and `color` are
  unchanged.
- **Table:** `col_widths_pct` from `tblGrid`. **Cell:** `v_align`.
- **Image endpoint:** keeps main-part ids (`rIdN`) and adds part-scoped ids for
  header and footer pictures (`ftr:<part>:<rId>`, `hdr:<part>:<rId>`), resolved
  through that part's `.rels`.

#### 4.3.2 Frontend behaviour

- **Sheets.** A new sheet starts at `page_break_before`, after
  `section_break_after`, or at a paragraph with a `page_role`. Each sheet's
  width, minimum height and padding come from `page_setup`, converted at
  96 dpi (A4 is 794 × 1123 px). It grows for long sections. There are no page
  numbers on screen.
- **Typography** is scoped to the sheet: Arial, sizes in pt (effective = style
  props, then paragraph direct, then run direct), colours, capitals, spacing,
  justification, list glyphs and indents. The app's own design system (Stripe
  look, `DESIGN.md`) stays outside the sheet.
- **Art sheets:** the background image is full-bleed (`object-fit: cover`,
  lazy-loaded), the content is rendered on top, and there are no header or
  footer bands.
- **Content sheets:** header band (title | client, 9 pt navy capitals,
  hairline) and footer band (logo · revision line), drawn from `furniture`.
- **Tables:** column widths from `col_widths_pct`, black ½ pt borders, cell
  shading and vertical alignment. Header rows keep their fills (already in
  `shading`).
- **Editing is unchanged:** click to edit, debounced autosave, the
  "Modificato" badge, "Ripristina", "Salva come nuova versione". The edit ring
  stays a UI overlay.
- The sidebar index uses `outline_level` (falling back to `heading_level`).
- On narrow screens the sheet scales down to fit the width. There is no
  horizontal scroll.

#### 4.3.3 Out of scope

Pagination like Word; editing tables, images or styles; and the legacy Google
Docs flow (unchanged).

### 4.4 The other 16 documents (phase 3)

They get the kit's *look* now and keep their current *structure* until N2O
sends a model for each.

- **Code-built (7):** MMC, VDT, Microclima, Microclima severo, Biologico ×3.
  - `setup_document(doc, profile="attachment")`, `add_art_cover("cover_vera",
    title_block=…)`, `finish_document` (new header and footer) and
    `add_back_cover`.
  - Hard-coded font names, sizes and colours (e.g. MMC and VDT have 9 each) are
    replaced by kit roles and builders.
  - No dividers.
- **Donor templates (8):** Gestanti, Incendio, Stress, DUVRI, POS,
  PEE azienda, PEE comune, HACCP manuale.
  - Port `strip_donor_cover` from PR #82 (tested there on the real templates)
    and insert the kit cover in its place.
  - `normalize_fonts(doc)` sets Arial in every style and on every run's
    `rFonts` in body, header and footer. Donor **sizes are kept**, so pages
    don't jump.
  - New header and footer, and the back cover.
  - Visual check of all 8 (Arial is ~8–10 % wider than Calibri).
- **HACCP forms:** fonts, header and footer only. No cover or back cover on
  sheets meant to be printed and filled in.

## 5. Error handling and degradation

- A missing or unreadable art file gives a white divider or cover with the live
  title, plus a warning log. Generation never fails on art.
- An unreadable org logo prints the firm name as text in the footer (today's
  behaviour).
- With no company photo, row 5 prints without a photo slot. A missing
  Medico Competente or RLS prints "—" in the signature grid's name row; the grid
  never disappears.
- The preview parser ignores anchors without the `vera-art:` marker.
  Documents generated before this change parse exactly as today (golden test).

## 6. Testing and verification

- **`tests/test_design_kit.py` (new):**
  - Arial on all four slots of styles and kit runs.
  - Token sizes and fills; ½ pt black table borders.
  - Each art section has `titlePg` with an empty first-page header and footer.
  - Art anchors: page-relative, page-sized, `behindDoc`, marker name.
  - Footer has an inline logo plus PAGE/NUMPAGES fields.
  - `add_divider` keeps the title outside the art paragraph.
- **DVR structure audit:** extend `scripts/verify_dvr_luca_fixture.py` and
  `tests/test_dvr_luca_improvements.py` to assert the §4.2.1 map:
  - divider titles and art keys, in-page titles, no numbering
  - Part II renamed; the split tables
  - the 4-column portrait improvement table and no landscape section
  - no photo captions; sign panels present; signature grid
  - company photo present when given, absent otherwise
- **Visual check:** render the fixture DVR through LibreOffice, tile it next to
  the archived model, and attach the image to each PR.
- **Preview:** extend `tests/test_document_preview.py` with page roles, art not
  reported as inline images, `furniture`, `style_props`, lists, column widths,
  part-scoped image ids, and a golden snapshot of an old document.
- **Company photo:** `tests/test_azienda_foto_presentazione.py` covers
  upload/replace/delete, org isolation, 403 for roles without `SURVEY_WRITE`,
  type and size limits, and HEIC normalisation.
  `test_permissions.py` and `test_billing_enforcement.py` stay green.
- **Existing suites** stay green: `test_generators.py`, `test_dvr_*`,
  `test_document_*`, `test_donor_front_matter.py`,
  `scripts/verify_all_generators.py`.
- **Frontend:** `tsc --noEmit`, `next build`, and a Playwright screenshot of
  `/documents/[id]` for a regenerated DVR and an old document (desktop and
  phone width).

## 7. Rollout

1. **PR 1:** spec, kit, DVR Master, company photo (backend migration and
   endpoints, frontend card). After merge, regenerate the DVR for N2O's test
   company and send it to Luca to test, as he asked on 2026-10-22.
2. **PR 2:** editor (preview contract and `/documents/[id]`).
3. **PR 3:** the other 16 documents.

The PRs are sequential on `claude/jolly-davinci-o3immw`; the branch restarts
from `main` after each merge. Existing documents are not regenerated
automatically. Operators regenerate to get the new layout, and version history
is kept. Draft PR #82 is superseded once `strip_donor_cover` is ported; close
it with a note.

**Documentation:**
- Update `.claude/rules/document-generation.md` (kit usage, roles, art
  manifest) and `docs/context/DVR_TEMPLATE_MAPPING.md` (the new page map).
- Add a CLAUDE.md line: documents use Arial (N2O requirement); do not
  reintroduce Calibri or Avenir.

**For N2O** (not blocking):
1. The cover and back cover at print resolution (≥ 2480 × 3508 px). The current
   cover is ≈128 dpi.
2. Layered versions without title and logo, for the white-label cover.
3. Confirmation that they hold the rights to the artwork and sign panels.
4. Our choices: Arial instead of Avenir; 10 pt tables; the 4-column improvement
   table with its legal reading (§4.2.2); the per-environment extrapolation
   (§4.2.3).
5. Models for the other attachments, when ready.
6. Check the logo in Impostazioni. The model's footer shows the VERA mark,
   while decision 3 prints an org's *uploaded* logo first. If N2O has uploaded
   its own logo, remove it or replace it with the VERA mark to match the
   model.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Word and LibreOffice treat page-anchored art in `titlePg` sections differently | Explicit empty first-page parts; LibreOffice render in tests; N2O checks in Word |
| DVR gets longer (new pages per category, 12 pt body, Arial wider than Calibri) | 10 pt tables; told to N2O; page count recorded in the PR |
| Preview payload grows | `style_props` table plus direct deltas; the existing LRU cache |
| Donor pagination shifts after the font pass | Sizes kept; visual check of all 8 |
| Cover prints soft at 128 dpi | Ask N2O for print resolution (§7) |
| Artwork rights | N2O confirmation before the white-label work |
| PR #82 conflicts with `main` | Port the function, don't merge the branch |

## 9. Out of scope

- White-label cover, until N2O sends layered art.
- Structural redesign of the 16 attachments, until N2O's models arrive.
- Word-like pagination in the editor, and editing tables, images or styles.
- PDF export.
- Google Docs flow changes.
- Regenerating existing documents.

## Appendix A — Art manifest (source: model DOCX `word/media/`)

| Key | Source | Used by |
|---|---|---|
| `cover_dvr` | `image1.emf` (its single bitmap) | DVR cover |
| `back_vera` / `cover_vera` | `image33.jpeg` | Back cover (all documents); attachment covers |
| `div_servizi_igienici` | `image3.png` | SERVIZI IGIENICO-ASSISTENZIALI |
| `div_macchine` | `image4.png` | MACCHINE, ATTREZZATURE ED IMPIANTI |
| `div_sostanze` | `image5.png` | SOSTANZE, PRODOTTI E PREPARATI CHIMICI |
| `div_fattori_pericolo` | `image6.png` | ELENCO FATTORI DI PERICOLO |
| `div_ambienti` | `image7.jpeg` | Part III; DOCUMENTI CORRELATI |
| `div_mansioni` | `image10.png` | MANSIONI CHE ESPONGONO I LAVORATORI A RISCHI SPECIFICI |
| `div_dpi` | `image12.png` | DISPOSITIVI DI PROTEZIONE INDIVIDUALE (DPI) |
| `div_segnaletica` | `image13.png` | SEGNALETICA DI SICUREZZA |
| `div_formazione` | `image19.png` | PROGRAMMA DI INFORMAZIONE…; GESTIONE INFORMAZIONE… |
| `div_miglioramento` | `image20.jpeg` | Part IV programme |
| `div_leggi` | `image22.png` | GESTIONE LEGGI E REGOLAMENTI |
| `div_sorveglianza` | `image23.png` | GESTIONE SORVEGLIANZA SANITARIA |
| `div_riunione` | `image24.png` | RIUNIONE PERIODICA |
| `div_infortuni` | `image25.png` | GESTIONE DEGLI INFORTUNI |
| `div_comportamenti` | `image26.png` | GESTIONE COMPORTAMENTI SCORRETTI DEI LAVORATORI |
| `div_gestione_dpi` | `image27.png` | GESTIONE DPI |
| `div_infrastrutture` | `image28.png` | GESTIONE INFRASTRUTTURE |
| `div_sensibili` | `image29.png` | GESTIONE DEI LAVORATORI PARTICOLARMENTE SENSIBILI |
| `div_acquisti` | `image30.png` | GESTIONE ACQUISTI |
| `div_appalti` | `image31.png` | GESTIONE DELLE LAVORAZIONI AFFIDATE IN APPALTO |
| `div_dichiarazione` | `image32.png` | DICHIARAZIONE DEL DATORE DI LAVORO |
| `div_generico` | `image7.jpeg` | Fallback for unknown keys |
| `sign_divieto` | `image14.jpeg` | CARTELLI DI DIVIETO |
| `sign_avvertimento` | `image15.jpeg` | CARTELLI DI AVVERTIMENTO |
| `sign_obbligo` | `image16.jpeg` | CARTELLI DI OBBLIGO |
| `sign_emergenza` | `image17.jpeg` | SEGNALI DI EMERGENZA ED EVACUAZIONE |
| `sign_antincendio` | `image18.jpeg` | SEGNALI DI PREVENZIONE INCENDI |
| `vera_italia_mark` | `image21.png` (footer part) | Default document logo |

`image11.jpeg` is a stray copy N2O left on the last "Mansioni" page. It is not
used.
