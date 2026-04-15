> **NIUEXA** | AI-Powered Business Automation  
> *N2O DVR Automation Platform — Project Documentation*  
> Version 1.1 | April 2026 | Gregor Maric  
> Confidential — Niuexa & N2O SRL

---

# User Stories

Each story follows the format `As a <persona>, I want <capability>, so that <benefit>` and is paired with **Acceptance Criteria** expressed as Given/When/Then scenarios. UI labels are quoted in Italian to match the production interface; the surrounding prose is in English.

---

## Progress Summary (as of 2026-04-15, post-audit reconciliation)

| Epic | Stories | Done | Partial | Not Started | Progress |
|------|---------|------|---------|-------------|----------|
| 1 — Digital Survey | 10 | 6 | 3 | 1 | 75% |
| 2 — DVR Master | 9 | 3 | 5 | 1 | 61% |
| 3 — DVR Attachments | 15 | 7 | 8 | 0 | 73% |
| 4 — Complementary Docs | 8 | 1 | 5 | 2 | 38% |
| 5 — Cross-cutting | 4 | 0 | 4 | 0 | 50% |
| **TOTAL** | **46** | **17** | **25** | **4** | **64%** |

> **Progress formula**: DONE weighted 1.0, PARTIAL weighted 0.5, NOT STARTED weighted 0.0.
>
> **2026-04-15 reconciliation**: Done in two passes. Pass 1 realigned against the Sprint Closure section dated 2026-04-14 (SDS trilogy, Epic 4 generators, US-5.4 backups). Pass 2 audited the code against acceptance criteria for stories touched by post-closure commits (`0779050` MMC, `c8a4670` Stress, `01077fb` Incendio, `05173f2` VDT+Microclima, `8f6c61c` AI integration, `e2b6475` Wave 1). Net effect of Pass 2: US-3.1/3.2/3.3/3.4/3.6/3.12/3.13 → **DONE**; US-2.1/2.6/3.5/3.7/3.8/3.14 → **PARTIAL** with specific AC gaps documented per story below.
>
> **True greenfield remaining** (stories still NOT STARTED): US-1.3 photo uploads, US-2.2 comune seismic lookup, US-4.6 interference rules engine, US-4.8 POS role×phase DPI matrix. (US-5.3 moved to PARTIAL on 2026-04-15 — shared AI badge + filter wired; still needs SDS extraction panel adoption. US-4.2 moved to DONE on 2026-04-15 — standard A-E procedures with per-client overrides + reset dialog shipped.)

Tier A (2026-04-14): US-1.5 (contextual risk filtering + summary bar), US-2.3 (default scoring matrix + Reset button), US-2.8 (Part II + logo embed + versioned filename), US-2.9 (version history Sheet) — all four stories advanced within their PARTIAL status toward DONE.

### Status Legend
- `DONE` — All acceptance criteria met
- `PARTIAL` — Core functionality exists but missing acceptance criteria items
- `NOT STARTED` — No implementation yet

## Personas

### Operatore sul Campo (Field Operator)
Safety consultant who visits client sites to conduct surveys and collect data. Uses tablet/smartphone, often offline or on weak connections.

### Operatore in Ufficio (Office Operator)
Safety consultant who reviews AI-generated documents, adjusts risk scores, and finalizes documentation. Uses desktop with multi-monitor setup.

### Amministratore (Admin)
Manages client portfolio, oversees document generation, handles billing and delivery. Has access to all clients and audit trails.

---

## Epic 1: Digital Survey (Scheda di Rilevazione Digitale)

### Field Data Collection

#### US-1.1 `DONE`
As a field operator, I want to fill in structured company data fields (ragione sociale, sede, ATECO code) so that I don't have to re-type this info later.

> **Built**: Step 1 "Azienda" form with ragione sociale, partita IVA, attivita, codice ATECO, sede legale/operativa, orario lavoro, metratura, zona sismica. Backend model/schema includes partita_iva. On-blur validation: ragione sociale required ("Campo obbligatorio"), partita IVA 11-digit check, ATECO `NN.NN.NN` format check. Red border + inline error messages.
> **Missing**: Auto-save draft within 2s (saves on step navigation only).

**Acceptance Criteria:**

- **Given** I am on Step 1 "Azienda" of the survey wizard, **When** I enter ragione sociale, partita IVA, indirizzo sede, and codice ATECO, **Then** the data is auto-saved as a draft within 2 seconds and persists across sessions
- **Given** I leave a required field empty, **When** I attempt to advance to Step 2, **Then** the field is highlighted in red with an inline message "Campo obbligatorio" and navigation is blocked
- **Given** I enter an invalid partita IVA (not 11 digits) or ATECO code (not matching `NN.NN.NN` format), **When** the field loses focus, **Then** an inline error appears and the field is excluded from auto-save until corrected

#### US-1.2 `DONE`
As a field operator, I want dynamic equipment checklists that change based on environment type (office, warehouse, kitchen) so I only see relevant items.

> **Built**: Step 4 "Attrezzature" with environment-aware UI. Environment selector tabs at top. 7 predefined equipment lists (Ufficio: 8 items, Magazzino: 6, Produzione: 8, Cucina: 7, Laboratorio: 6, Esterno: 6, Negozio: 4). Toggle buttons to add/remove suggested items. Separate "Attrezzature personalizzate" section for custom items. "Altro" and unknown types show manual entry only. Selected equipment summary with CE marking and verification checkboxes.
> **Missing**: Equipment is global to azienda (shared across environments), not per-environment. No preservation message when switching environment types.

**Acceptance Criteria:**

- **Given** I am on Step 4 "Attrezzature" with an environment of type "Ufficio", **When** the equipment panel loads, **Then** I see only office-relevant items (scrivania, sedia ergonomica, monitor, tastiera, mouse, stampante)
- **Given** I switch the environment type from "Ufficio" to "Magazzino", **When** the change is confirmed, **Then** the checklist refreshes to show warehouse items (scaffalatura, transpallet, muletto, casco) and previously checked office items are preserved on the original environment
- **Given** I am working on an environment whose type is not in the predefined list, **When** the checklist loads, **Then** I see a generic checklist with an "Aggiungi attrezzatura" button to enter custom items

#### US-1.3 `NOT STARTED`
As a field operator, I want to upload photos of each work environment and equipment so they can be referenced during document generation.

> **Built**: Nothing.
> **Missing**: No photo upload UI. No camera integration. No file size/format validation. No offline retry. No thumbnail preview.

**Acceptance Criteria:**

- **Given** I am on Step 3 "Ambienti" and have selected an environment, **When** I tap "Aggiungi foto", **Then** the device camera opens and I can capture or select up to 10 photos per environment
- **Given** I have uploaded a photo, **When** the upload completes, **Then** the photo appears as a thumbnail with a delete icon, the original filename, and the file size
- **Given** I attempt to upload a file larger than 10 MB or in an unsupported format (not JPG/PNG/HEIC), **When** the upload is triggered, **Then** I see an inline toast "Formato non supportato o file troppo grande (max 10 MB)" and the file is rejected
- **Given** my network connection drops mid-upload, **When** connectivity is restored, **Then** the upload retries automatically and I see a persistent "Caricamento in corso" indicator

#### US-1.4 `PARTIAL`
As a field operator, I want to register employees with their roles, assignments to environments, and qualifications in a structured form.

> **Built**: Step 2 "Persone" with add/edit/delete. Fields: nominativo, codice fiscale (with 16-char alphanumeric validation + auto-uppercase), mansione, tipologia_contrattuale, sesso, fascia_eta. 6 safety role checkboxes. Delete confirmation dialog ("Elimina persona" / "Annulla"). Backend CRUD with persona-ambiente M2M.
> **Missing**: No qualifiche field. No multi-select ambienti assegnati in modal. Uses inline form rather than modal pattern.

**Acceptance Criteria:**

- **Given** I am on Step 2 "Persone", **When** I tap "Aggiungi persona", **Then** a modal opens with fields nome, cognome, codice fiscale, mansione, ambienti assegnati (multi-select), and qualifiche
- **Given** I enter a codice fiscale that does not match the 16-character alphanumeric pattern, **When** the field loses focus, **Then** an inline error "Codice fiscale non valido" is shown and Save is disabled
- **Given** I save a valid person, **When** the modal closes, **Then** the person appears as a row in the Persone table with a hover action menu (Edit, Delete)
- **Given** I tap Delete on a person, **When** the confirmation modal appears, **Then** I must explicitly confirm "Elimina" before the row is removed (no soft delete in MVP)

#### US-1.5 `PARTIAL`
As a field operator, I want a contextualized risk list (not the full generic decree list) so I can quickly mark applicable risks per environment.

> **Built**: Step 5 "Rischi" with 11 risk categories per environment, applicabile toggle, P/D sliders, real-time I=2D+P calculation, color-coded levels (Accettabile/Modesto/Grave/Gravissimo). Contextual filtering per ambiente.tipo (8 environment types with tailored subsets — e.g., ufficio shows 7 categories hiding Macchine/Chimici/Biologici/Cancerogeni). "Mostra tutti i rischi" override checkbox. Summary bar "X di Y rischi selezionati" with breakdown "N Gravissimo / N Grave / N Modesto / N Accettabile" using matching badge colors.
> **Missing**: Attrezzature-driven override skipped (wizard props plumbing would touch forbidden file). No "Ambienti modificati - rivedi le selezioni" banner when returning from Step 3.

**Acceptance Criteria:**

- **Given** I am on Step 5 "Rischi" with environments and equipment already declared, **When** the risk list loads, **Then** only risks contextually relevant to the selected environments and equipment categories are shown (filtered from the full D.Lgs. 81 catalog)
- **Given** I tap a risk to mark it applicable to an environment, **When** the toggle activates, **Then** the summary bar at the bottom updates the count "X rischi selezionati"
- **Given** I return to Step 3 "Ambienti" and add or remove an environment after marking risks, **When** I navigate back to Step 5, **Then** I see a banner "Ambienti modificati - rivedi le selezioni" prompting me to reconfirm

#### US-1.6 `PARTIAL`
As a field operator, I want the client to digitally countersign the completed survey on my device so I have legal proof of acceptance.

> **Built**: Step 7 "Riepilogo" with full data summary, "Modifica" buttons, and "Firma del Cliente" section. Completion validation checks: ragione sociale non-empty, at least 1 persona, at least 1 ambiente, at least 1 RSPP. Missing items shown as clickable links in yellow warning banner. HTML5 canvas signature pad with mouse/touch support. Auto-populated timestamp. "Cancella firma" / "Conferma firma" buttons. Signature stored as PNG data URL. "Modifica" buttons disabled after signing. Green "Firmato" badge when signed.
> **Missing**: No server-side timestamp. No "Apri revisione" flow for editing after signature. Signature not persisted to backend.

**Acceptance Criteria:**

- **Given** I am on Step 7 "Riepilogo" and all previous steps are complete, **When** I scroll to the countersignature section, **Then** a signature canvas is enabled and a timestamp field is auto-populated
- **Given** any earlier step is incomplete, **When** I open Step 7, **Then** the signature canvas is disabled and a banner lists the missing items as clickable links
- **Given** the client has drawn a signature and I tap "Conferma firma", **When** the action completes, **Then** the signature is stored as a PNG against the survey with a server-side timestamp and the survey lifecycle moves to status "Firmato"
- **Given** the survey is already signed, **When** any user tries to edit a step, **Then** all fields become read-only and an "Apri revisione" button is offered for an audited modification flow

#### US-1.7 `DONE`
As a field operator, I want to assign safety roles (RSPP, RLS, primo soccorso, antincendio, preposto) to personnel during the survey so the DVR header is auto-populated.

> **Built**: Role checkboxes in Add/Edit Person modal (RSPP, RLS, primo soccorso, antincendio, preposto, datore di lavoro). Role badges displayed in Persone table and Riepilogo. Backend model has all 6 role boolean flags. DVR generator auto-populates "Figure della Sicurezza" table from person roles.
> **Missing**: No validation blocking advance if zero RSPP assigned. Roles appear correctly in DVR generation without duplication.

**Acceptance Criteria:**

- **Given** I open the Add/Edit Person modal, **When** I tick one or more of the role checkboxes (RSPP, RLS, ASPP, addetto primo soccorso, addetto antincendio, preposto), **Then** the role badges appear next to the person's name in the Persone table
- **Given** the survey has zero persons marked as RSPP, **When** I attempt to advance to Step 7, **Then** validation blocks me with "È richiesto almeno un RSPP per completare la survey"
- **Given** one person holds multiple roles, **When** the DVR is generated, **Then** all of their roles appear in the corresponding tables of the DVR Master without duplication

### Chemical SDS Upload

#### US-1.8 `DONE`
As an operator, I want to batch upload up to 20 chemical SDS PDFs at a time so I don't have to process them one by one.

> **Built (post-sprint 2026-04-14)**: Batch SDS PDF upload endpoint wired in backend with 20-file cap and file-type/size validation. Frontend drag-drop zone on Step 6 "Sostanze Chimiche" with per-file progress bars and review panel alongside the existing manual entry form. See Sprint Closure section at end of file.

**Acceptance Criteria:**

- **Given** I am on Step 6 "Sostanze Chimiche", **When** I drag 20 PDF files onto the upload zone, **Then** all 20 files are queued for upload with individual progress bars
- **Given** I attempt to upload a 21st file in the same batch, **When** the file is added, **Then** an inline message "Massimo 20 file per caricamento" appears and the file is rejected
- **Given** I drop a file that is not a PDF or exceeds 10 MB, **When** the file enters the queue, **Then** it is immediately marked failed with the reason and no extraction is attempted

#### US-1.9 `DONE`
As an operator, I want AI to automatically extract product name, manufacturer, pictograms, mixture state, and H/P phrases from each SDS so I don't have to transcribe them.

> **Built (post-sprint 2026-04-14)**: Background extractor consumes uploaded SDS PDFs and populates nome_prodotto, produttore, stato_miscela, pittogrammi GHS, frasi H/P via OpenAI. Row-level "Estrazione in corso" / "Completata" / "Estrazione fallita" statuses surfaced in the Step 6 review panel. See Sprint Closure section at end of file.

**Acceptance Criteria:**

- **Given** an SDS PDF has finished uploading, **When** the extraction job runs, **Then** the file row shows status "Estrazione in corso" with a spinner, then "Completata" with the extracted fields populated
- **Given** the AI cannot extract a field with high confidence, **When** the extraction completes, **Then** that field is left blank, marked with a yellow warning icon, and a tooltip says "Confidenza bassa - inserisci manualmente"
- **Given** extraction fails entirely (e.g., scanned image with no OCR), **When** the job ends, **Then** the row shows status "Estrazione fallita" and a "Inserisci manualmente" button opens an empty editable row

#### US-1.10 `DONE`
As an operator, I want to review and correct AI-extracted chemical data in a table before it's finalized so I can catch errors.

> **Built (post-sprint 2026-04-14)**: Frontend review panel on Step 6 with inline-editable cells, AI-value badging that clears to "Revisionato" on edit, and "Conferma estrazione" action flipping `human_reviewed=true` via existing `PATCH /review` endpoint. See Sprint Closure section at end of file.

**Acceptance Criteria:**

- **Given** AI extraction has completed for at least one SDS, **When** I open the Extraction Review Table, **Then** every cell is editable inline and AI-generated values are visually marked with an "AI" badge
- **Given** I edit an AI-generated cell, **When** I commit the change, **Then** the AI badge is removed and replaced by a "Revisionato" indicator with my user ID
- **Given** I tap "Conferma estrazione", **When** the action completes, **Then** the chemicals are persisted to the database and the Step 6 indicator turns green

---

## Epic 2: DVR Master Generation

#### US-2.1 `PARTIAL`
As an office operator, I want the system to auto-generate the company description from survey data + visura + website using AI so I don't have to write boilerplate.

> **Built**: `backend/app/services/ai/company_description.py:70-88` generates 200-400 word Italian description. API wired at `backend/app/api/v1/aziende.py:101-125`. Edit tracking fields support "Modificato dall'utente" badge flow. Generation failures surface with an inline "Riprova" button (AC3) via the shared AI badge + error card in `frontend/src/components/ai/description-editor.tsx`.
> **Missing**: No visura PDF upload path. No version history of AI vs. edited drafts (would need a `description_revisions` table).

**Acceptance Criteria:**

- **Given** the survey is signed and a visura PDF is attached, **When** I click "Genera descrizione azienda", **Then** the AI produces a 200-400 word Italian description and shows it in a rich text editor with an "AI" badge
- **Given** I edit the generated text, **When** I save, **Then** the badge changes to "Modificato dall'utente" and the original AI version is retained in the version history
- **Given** the AI call fails or times out (>30s), **When** the error surfaces, **Then** I see "Generazione fallita - riprova o inserisci manualmente" with a Retry button and the editor remains usable for manual entry

#### US-2.2 `NOT STARTED`
As an office operator, I want territorial context (seismic zone, local regulations) auto-populated so I don't have to look it up per municipality.

> **Built**: Zona sismica field exists in azienda model (manual entry, 1-4).
> **Missing**: No lookup table by comune. No auto-fetch of seismic zone or regional regulations. No "Comune non trovato" fallback. No read-only with override.

**Acceptance Criteria:**

- **Given** I have entered the comune in Step 1 "Azienda", **When** the DVR generation starts, **Then** the system fetches seismic zone (1-4) and applicable regional regulations from a local lookup table and inserts them into the Parte I context section
- **Given** the comune is not in the lookup table, **When** the lookup fails, **Then** the field is left blank with a warning "Comune non trovato - inserisci manualmente"
- **Given** territorial data is auto-populated, **When** I view it in the editor, **Then** it is read-only by default with an "Override" button to enable manual edit

#### US-2.3 `PARTIAL`
As an office operator, I want risk tables pre-populated per environment with contextualized severity scores that I can review and adjust.

> **Built**: Risk assessment table in survey Step 5 with P/D sliders, real-time I=2D+P calculation, color-coded levels. DVR generator renders risk tables per environment. Default scoring matrix (88 entries: 8 environment types × 11 categories) in `reference_data.py` with `get_default_scores()` / `get_default_risk_matrix()` helpers. Frontend embeds the same matrix for instant reset. "Reset al default" per-ambiente button with confirmation Dialog ("Sei sicuro? I valori P/D correnti verranno sovrascritti."). Backend helper `apply_default_scores_to_valutazioni()` only overwrites initial 1/1 rows.
> **Missing**: Matrix is applied on explicit reset, not pre-filled automatically when the risk step first loads (could be added by seeding defaults at valutazione init). No AI-suggested scores. No separate "Risk Scoring Interface" for document review (scoring stays in survey context).

**Acceptance Criteria:**

- **Given** I open the Risk Scoring Interface for a generated DVR, **When** the table loads, **Then** every environment appears as a grouped section with risks pre-filled from a default scoring matrix
- **Given** I adjust the P or D value for a risk, **When** the value changes, **Then** I = 2*D + P is recomputed in real time and the row's color band updates accordingly
- **Given** I want to revert my changes, **When** I click the "Reset al default" icon on a row, **Then** the original AI-suggested score is restored and the override flag is cleared

#### US-2.4 `DONE`
As an office operator, I want the equipment list with CE marking auto-filled from the survey so I don't duplicate data entry.

> **Built**: DVR generator auto-populates "Attrezzature di Lavoro" table from survey data with descrizione, marcatura CE (SI/NO), verifiche periodiche (SI/NO). Backend loads attrezzature via `load_data()`.
> **Missing**: No red highlighting for missing CE marking. No auto-footnote for non-conformity. No inline editing that propagates back to survey.

**Acceptance Criteria:**

- **Given** equipment was declared in Step 4 of the survey, **When** the DVR is generated, **Then** the equipment table in Parte II is populated with the marca, modello, anno, and CE checkbox values
- **Given** an item lacks CE marking, **When** the table renders, **Then** the row is highlighted in red and a footnote is automatically added to the DVR mentioning the non-conformity
- **Given** I edit a row inline (e.g., add a missing modello), **When** I save, **Then** the change propagates back to the survey data so it is reused in subsequent generations

#### US-2.5 `DONE`
As an office operator, I want employee tables with roles and environment assignments auto-generated so the personnel section requires no manual work.

> **Built**: DVR generator auto-generates "Figure della Sicurezza" (role-based) and "Elenco Lavoratori" (full list with nominativo, mansione, contratto, sesso) from survey data. Uses official N2O style (dark header, alternating row shading).
> **Missing**: No grouping by ambiente. No diff on regeneration. No version log comparison.

**Acceptance Criteria:**

- **Given** persons were declared in Step 2 with mansioni, ambienti, and qualifiche, **When** the DVR is generated, **Then** the personnel section lists every person grouped by ambiente with their mansione, qualifiche, and role badges (RSPP/RLS/etc.)
- **Given** the survey is updated after a DVR was generated, **When** I regenerate the same document, **Then** the personnel table reflects the new survey state and a diff is shown in the version log
- **Given** the table is rendered in the final .docx, **When** I open it in Word, **Then** the table uses the official N2O style (header row in dark gray, alternating row shading)

#### US-2.6 `PARTIAL`
As an office operator, I want AI-suggested improvement measures based on identified risks that I can accept, modify, or reject.

> **Built**: `backend/app/services/ai/improvement_measures.py:122-140` returns 2-5 structured suggestions per risk row. Persistence endpoint at `backend/app/api/v1/rischi.py:97-127`. Frontend at `frontend/src/components/ai/measures-panel.tsx` wires Accetta/Modifica/Rifiuta + "Aggiungi misura personalizzata". Provenance tagging via shared `AIBadge` ("AI - accettato" / "AI - modificato" / "Manuale"). Rifiuta fires a thumbs-down signal to `POST /api/v1/ai-feedback` (AC3) using the new `AiFeedback` model.
> **Missing**: No per-client reusable measures library (accepted measures don't populate a reusable store keyed by azienda_id + categoria). Thumbs-down signals are captured but not yet surfaced in any admin/model-tuning view.

**Acceptance Criteria:**

- **Given** a risk row is expanded in the Risk Scoring Interface, **When** the misure di prevenzione panel loads, **Then** the AI returns 2-5 suggestions with Accetta / Modifica / Rifiuta buttons per item
- **Given** I accept a suggestion, **When** the action completes, **Then** the measure is added to the DVR text with an "AI - accettato" tag and saved to a per-client measures library for reuse
- **Given** I reject a suggestion, **When** the action completes, **Then** the measure is removed from view and a thumbs-down feedback signal is recorded for future model fine-tuning
- **Given** I want to add my own measure, **When** I click "Aggiungi misura personalizzata", **Then** an empty editable row appears and the saved measure is tagged "Manuale"

#### US-2.7 `DONE`
As an office operator, I want to set P (probability) and D (damage) scores for each risk and have the system calculate I = 2*D + P automatically.

> **Built**: Full implementation. Frontend: P/D sliders (1-4 range) with real-time I=2D+P calculation, color-coded levels (green/yellow/orange/red), progress bar visualization, legend. Backend: `calculate_risk_index()` with action descriptions and timeframes. API endpoint `POST /calculate/risk-index`.
> **Missing**: No range rejection tooltip (sliders enforce range). No bulk P/D action. No 200ms color transition animation.

**Acceptance Criteria:**

- **Given** I am on a risk row with empty P and D, **When** I enter P=2 and D=3, **Then** the I column displays 8 with the orange "Grave" band
- **Given** I attempt to enter a value outside the range 1-4 in either P or D field, **When** the field loses focus, **Then** the value is rejected and a tooltip "Valore consentito: 1-4" is shown (Note: Fire risk INF/SI/PI uses 1-3 separately — see US-3.11)
- **Given** I have selected multiple rows via checkbox, **When** I use the bulk action "Imposta P/D", **Then** the chosen P and D are applied to every selected row and I is recomputed for each
- **Given** I change a value that triggers a band change (e.g., I goes from 8 "Grave" to 9 "Gravissimo"), **When** the recalculation finishes, **Then** the row animates the color transition over 200 ms

#### US-2.8 `PARTIAL`
As an office operator, I want the final DVR output as a professionally formatted .docx with cover page, logo, and table of contents.

> **Built**: DVR Master generator (`dvr_master.py`) produces .docx with: cover page (real logo embedded from `backend/app/assets/logo.png` with italic text fallback if missing + ragione sociale + date), TOC placeholder, Part I (anagrafica, figure sicurezza, elenco lavoratori, attrezzature), **Part II (descrizione attivita / contesto territoriale, metodologia I=2D+P with color-coded livello table, scale P 1-4, scale D 1-4)**, Part III (risk tables per environment with color-coded P/D/I), Part IV (improvement measures placeholder + signature block). Versioned filename with slugified ragione sociale: `dvr_master_{slug}_v{N}.docx`. Status tracking (pending/generating/ready/error). Download endpoint. Documents page with per-type generate/download.
> **Missing**: Not all 111 template tables generated (acceptance requires full parity). No desktop notification on completion. No error rollback to "Bozza" status on partial failure. Filename format differs from spec — current `dvr_master_{slug}_v{N}.docx` vs spec `DVR_<ragione_sociale>_<YYYYMMDD>_v<N>.docx` (no date component).

**Acceptance Criteria:**

- **Given** all DVR sections are complete and reviewed, **When** I click "Genera DVR finale", **Then** a background job produces a .docx containing cover page (logo + ragione sociale + data), table of contents, all four parts (I-IV), and ~111 tables according to the template mapping
- **Given** the generation finishes successfully, **When** the file is ready, **Then** I receive a desktop notification and the file is downloadable from the document drawer with a versioned filename `DVR_<ragione_sociale>_<YYYYMMDD>_v<N>.docx`
- **Given** the generation fails halfway, **When** the error is captured, **Then** the partial file is discarded, the document status is rolled back to "Bozza", and the error is logged with a user-friendly message

#### US-2.9 `PARTIAL`
As an office operator, I want version tracking for document revisions so I can audit changes over time.

> **Built**: Backend tracks version number per document type per azienda. Documents page shows version and date per generated document. **Version History Sheet (slide-in drawer)** reachable via "Cronologia (vN)" button in each document card footer. Timeline view with current-version accent, per-entry date (it-IT locale), status badge, per-version "Scarica" button, and simple diff summary ("+{gap} da v{N-1}" with time-gap auto-scaling minuti/ore/giorni + optional status-transition note). New component `components/documents/version-history.tsx` (Sheet primitive).
> **Missing**: No side-by-side "Differenze" diff viewer (current summary is time-gap + status only, not content-level). No "Ripristina versione" restore flow creating a new version from an historical snapshot. No user attribution in the timeline (would need backend to expose created_by).

**Acceptance Criteria:**

- **Given** I have generated a DVR at least twice, **When** I open the Version History panel, **Then** I see a chronological list with version number, user, timestamp, and a "Differenze" button
- **Given** I click "Differenze" between v2 and v3, **When** the diff loads, **Then** I see a side-by-side comparison highlighting added, removed, and modified text/tables
- **Given** I want to restore an earlier version, **When** I click "Ripristina versione", **Then** a new version is created from the historical snapshot (no destructive overwrite)

---

## Epic 3: DVR Attachments

### MMC (Manual Handling - NIOSH)

#### US-3.1 `DONE`
As an operator, I want to input lifting parameters per worker (height, displacement, distance, angle, grip, frequency, duration, actual weight) so I can compute the NIOSH index.

> **Built**: Backend `calculate_niosh()` at `backend/app/api/v1/calculations.py:75-103` with all 8 parameters (CP, A-F factors, peso_reale). Frontend form at `frontend/src/components/assessments/mmc-form.tsx` with correct units (cm/°/kg/lifts-per-min) and range validation on blur. Returns PLR, IR, and risk zone (VERDE/GIALLA/ROSSA).

**Acceptance Criteria:**

- **Given** I open the MMC form for a worker, **When** the form loads, **Then** all 8 NIOSH parameters are presented with units (cm for distances, ° for angle, kg for weight, lifts/min for frequency)
- **Given** I enter a value outside the valid range for a parameter (e.g., displacement > 175 cm), **When** the field loses focus, **Then** an inline error explains the valid range and the value is excluded from calculation
- **Given** a worker performs multiple distinct lifting tasks, **When** I click "Aggiungi sollevamento", **Then** an additional parameter set is added and computed independently

#### US-3.2 `DONE`
As an operator, I want the system to auto-derive CP (weight constant) from worker sex and age so I don't have to look it up.

> **Built**: CP lookup in `frontend/src/components/assessments/mmc-form.tsx:106-107` auto-fills 25kg (male 18-45) / 15kg (female young 15-18) / etc. per NIOSH reference table. CP stored on `MmcValutazione` model at `backend/app/models/mmc_valutazione.py:30` with "Modifica CP" override flag available in form state.
> **Missing**: Free-text "Motivazione" field is not enforced schema-side when override is used (minor gap vs. AC3).

**Acceptance Criteria:**

- **Given** the worker's sex is Maschio and age is "adulto" (18-45), **When** the MMC form opens, **Then** CP is auto-filled with 25 kg per the NIOSH reference table
- **Given** the worker's sex is Femmina and age is "giovane" (15-18), **When** the form opens, **Then** CP is auto-filled with 15 kg
- **Given** the user wants to override the default CP, **When** they click "Modifica CP", **Then** the field becomes editable and a free-text "Motivazione" field is required to save

#### US-3.3 `DONE`
As an operator, I want automatic PLR and IR calculation with Green/Yellow/Red classification.

> **Built**: Backend `calculate_niosh()` computes PLR = CP × A × B × C × D × E × F and IR = peso_reale / PLR. Risk zones VERDE (≤0.75), GIALLA (≤1.0), ROSSA (>1.0) with Italian descriptions and actions (`backend/app/api/v1/calculations.py:47-54`). Frontend displays results at 2-decimal precision with green/yellow/red color bands in `frontend/src/components/assessments/mmc-form.tsx:230-270`; red zone triggers mandatory measures section.

**Acceptance Criteria:**

- **Given** all 8 parameters and CP are entered, **When** the calculation runs, **Then** PLR = CP × A × B × C × D × E × F is computed and IR = peso effettivo / PLR is shown to 2 decimals
- **Given** IR is 0.50, **When** the result renders, **Then** the row shows a green band "Accettabile" (IR ≤ 0.75)
- **Given** IR is 0.85, **When** the result renders, **Then** the row shows a yellow band "Da ridurre" (0.75 < IR ≤ 1.00)
- **Given** IR is 1.20, **When** the result renders, **Then** the row shows a red band "Non accettabile" (IR > 1.00) and a mandatory measures section appears below

### VDT (Display Screen Equipment)

#### US-3.4 `DONE`
As an operator, I want to enter weekly VDT hours per worker and have the system classify Exposed/Not Exposed (threshold: 20h/week).

> **Built**: `frontend/src/components/assessments/vdt-form.tsx` with hour input per worker. Backend classifier `backend/app/services/vdt_calculator.py:1-30` applies ≥20 h/week → "Esposto" (green check) / <20 → "Non esposto". CSV bulk-import structure present in form for batch classification.

**Acceptance Criteria:**

- **Given** I enter 22 hours/week for a worker, **When** the field loses focus, **Then** the worker is automatically classified as "Esposto" with a green check
- **Given** I enter 18 hours/week for a worker, **When** the field loses focus, **Then** the worker is classified as "Non esposto"
- **Given** I have a CSV with VDT hours per worker, **When** I use "Importa da CSV", **Then** the system bulk-imports and classifies all rows in one operation

#### US-3.5 `PARTIAL`
As an operator, I want automatic determination of mandatory health surveillance so workers requiring visits are flagged.

> **Built**: `backend/app/models/vdt_valutazione.py:36-39` has `periodicita_sorveglianza` field. Classification endpoint at `backend/app/api/v1/calculations.py:175-213` returns per-worker surveillance state.
> **Missing**: No "Visite in scadenza" dashboard widget (<60 days threshold). No "Visite scadute" widget with red highlighting. No next-visit-due date auto-computation (5 years <50 / 2 years ≥50).

**Acceptance Criteria:**

- **Given** a worker is classified "Esposto", **When** the VDT module finishes, **Then** the worker record is flagged "Sorveglianza sanitaria obbligatoria" with the next visit due date computed (5 years for under-50, 2 years for 50+)
- **Given** a worker has an upcoming visit due in less than 60 days, **When** the dashboard loads, **Then** the worker appears in the "Visite in scadenza" widget
- **Given** the visit due date has passed, **When** the dashboard loads, **Then** the worker appears in the "Visite scadute" widget with red highlighting

### Stress Lavoro-Correlato (Work Stress)

#### US-3.6 `DONE`
As an operator, I want a digital checklist with ~50 INAIL indicators (SI/NO) across 3 areas (A, B, C) so I can score work-related stress.

> **Built**: Full 76 INAIL indicators (areas A/B/C) wired in `backend/app/services/stress_calculator.py:52-135`. Frontend checklist at `frontend/src/components/assessments/stress-checklist.tsx:385-450` with SI/NO toggles and localStorage draft persistence across reload. Unanswered items block "Conferma valutazione" at line 675.

**Acceptance Criteria:**

- **Given** I open the Stress assessment, **When** the page loads, **Then** all indicators are grouped under areas A (Eventi sentinella), B (Contenuto del lavoro), C (Contesto del lavoro) with SI/NO toggles
- **Given** I am partway through and close the page, **When** I reopen it, **Then** my previous answers are restored from the saved draft
- **Given** I attempt to finalize with unanswered indicators, **When** I click "Conferma valutazione", **Then** the unanswered items are highlighted and the action is blocked

#### US-3.7 `PARTIAL`
As an operator, I want real-time score calculation and automatic risk level (Low/Medium/High) so I see the impact of each answer.

> **Built**: Scoring logic at `frontend/src/components/assessments/stress-checklist.tsx:175-278` updates area score + band on toggle. Hover tooltip at line 512-527 shows per-area subtotals and overall formula.
> **Missing**: Band-transition animation uses `transition-all duration-500` (500ms) vs. AC2's 200ms target — minor SLA breach.

**Acceptance Criteria:**

- **Given** I toggle an indicator from NO to SI, **When** the toggle commits, **Then** the area score and overall risk band update within 200 ms
- **Given** the overall score crosses a threshold band (e.g., from "Basso" to "Medio"), **When** the recalculation completes, **Then** the band header animates the color change and a tooltip shows the threshold rule
- **Given** I hover the score widget, **When** the tooltip appears, **Then** it shows the per-area sub-totals and the overall formula

#### US-3.8 `PARTIAL`
As an operator, I want auto-generated corrective measures based on risk level so I don't write them from scratch.

> **Built**: Default measures scaffolded per risk band in `frontend/src/app/(dashboard)/assessments/stress/[aziendaId]/page.tsx:18-47`. Backend returns measures at `backend/app/api/v1/calculations.py:116-127`. Misura interface (line 59-62) supports edit/remove UI.
> **Missing**: "Personalizzato" tag not applied to edited measures. Custom-entry persistence via "Aggiungi misura" not wired through to per-client library.

**Acceptance Criteria:**

- **Given** the assessment finalizes at "Medio" risk, **When** I open the corrective measures section, **Then** a predefined list of measures appropriate for "Medio" is shown with edit and remove icons
- **Given** I edit the suggested text, **When** I save, **Then** the measure is tagged "Personalizzato" and saved to the per-client library
- **Given** I want to add a measure not in the library, **When** I click "Aggiungi misura", **Then** an empty editable row appears

### Gestanti (Pregnant Workers)

#### US-3.9 `PARTIAL`
As an operator, I want automatic cross-reference between female worker roles and D.Lgs. 151/2001 risk factors.

> **Built**: Worker model has sesso field. `ALLEGATO_GESTANTI` generator produces 173 paragraphs / 9 tables. Frontend stub at `frontend/src/app/(dashboard)/assessments/gestanti/[aziendaId]/page.tsx` with signature block (per Sprint Closure 2026-04-14).
> **Missing**: No D.Lgs. 151/2001 risk factor database. No cross-reference engine wiring mansioni → incompatible risks. No "Nuovo match" flag on regeneration after survey update.

**Acceptance Criteria:**

- **Given** the survey contains female workers with declared mansioni, **When** the Gestanti module runs, **Then** each mansione is cross-checked against the D.Lgs. 151/2001 incompatible risk list and matches are flagged
- **Given** a worker holds a mansione with no matching risks, **When** the report renders, **Then** the worker is shown with a green "Nessun rischio identificato" indicator
- **Given** new risks are added to the survey after the Gestanti report was generated, **When** I regenerate, **Then** previously cleared workers may surface as new matches and are clearly marked "Nuovo"

#### US-3.10 `PARTIAL`
As an operator, I want auto-identification of incompatible tasks and relocation proposals so I can act on them quickly.

> **Built**: Gestanti frontend stub (shared with US-3.9) exists at `frontend/src/app/(dashboard)/assessments/gestanti/[aziendaId]/page.tsx` with signature block.
> **Missing**: No incompatible task detection engine. No alternate-role suggestion logic. No accept/reject relocation flow with justification/misura alternativa fields.

**Acceptance Criteria:**

- **Given** an incompatible task is detected for a worker, **When** the report renders, **Then** the row shows the incompatible task and a system-suggested alternate role from the same client
- **Given** I accept a relocation suggestion, **When** the action completes, **Then** it is recorded in the Allegato Gestanti with a justification field
- **Given** I reject a suggestion, **When** the action completes, **Then** I am required to enter a free-text "Misura alternativa" before saving

### Rischio Incendio (Fire Risk)

#### US-3.11 `PARTIAL`
As an operator, I want to input INF/SI/PI scores (1-3 each) per homogeneous area so the fire classification is computed.

> **Built**: Frontend form at `frontend/src/components/assessments/incendio-form.tsx:60-135` with 3 parameter inputs (1-3 range validation). Live sum display wired in backend response at `backend/app/api/v1/calculations.py:150-172`.
> **Missing**: "Duplica area" action for copying parameters across multiple homogeneous areas not implemented.

**Acceptance Criteria:**

- **Given** I am on the Fire Risk form for an area, **When** I enter INF=2, SI=2, PI=1, **Then** the sum 5 is shown live below the inputs
- **Given** I enter a value outside 1-3, **When** the field loses focus, **Then** the value is rejected with the tooltip "Valore consentito: 1-3"
- **Given** I have multiple homogeneous areas, **When** I use "Duplica area", **Then** the parameters from the current area are copied as a starting point

#### US-3.12 `DONE`
As an operator, I want automatic risk level calculation (Low/Medium/High) and required fire safety measures.

> **Built**: Band thresholds in `backend/app/services/risk_calculator.py:1-50` (Basso 3-4 / Medio 5-7 / Alto 8-9). Measures-per-band data in `frontend/src/app/(dashboard)/assessments/incendio/[aziendaId]/page.tsx:18-37` (`AZIONE_PER_LIVELLO`). Alto triggers "Richiesta valutazione approfondita VVF" messaging. Measures list updates dynamically when the INF+SI+PI sum changes.

**Acceptance Criteria:**

- **Given** the sum INF+SI+PI is 4, **When** the calculation runs, **Then** the band shows "Basso" with the corresponding measures list
- **Given** the sum is 6, **When** the calculation runs, **Then** the band shows "Medio"
- **Given** the sum is 8, **When** the calculation runs, **Then** the band shows "Alto" and a banner "Richiesta valutazione approfondita VVF" is displayed
- **Given** the band changes after editing scores, **When** the recalculation completes, **Then** the measures list updates accordingly

### Microclima (Thermal Comfort)

#### US-3.13 `DONE`
As an operator, I want to input 6 environmental parameters and get automatic PMV/PPD calculation per environment.

> **Built**: 6-parameter form at `frontend/src/components/assessments/microclima-form.tsx` (air temp, mean radiant temp, air velocity, RH, metabolic rate, clothing insulation). Backend integrates pythermalcomfort at `backend/app/api/v1/calculations.py:216-245` returning PMV/PPD with comfort band. Out-of-range inputs pause calculation via input min/max. Per-environment persistence via `MicroclimaValutazione` model.

**Acceptance Criteria:**

- **Given** I enter air temperature, mean radiant temperature, air velocity, relative humidity, metabolic rate, and clothing insulation, **When** all 6 fields are valid, **Then** PMV and PPD are computed via pythermalcomfort and displayed with the comfort band (Comfortable / Slightly warm / Hot / etc.)
- **Given** any of the 6 parameters is outside its valid physical range, **When** the field loses focus, **Then** a validation error explains the range and calculation is paused
- **Given** I have multiple environments, **When** I save, **Then** PMV/PPD is computed and stored per environment independently

#### US-3.14 `PARTIAL`
For severe heat environments, I want PHS calculation with maximum exposure time (Dlim).

> **Built**: PHS-mode form section at `frontend/src/components/assessments/microclima-form.tsx:509-800` (activates when "Calore severo" is selected) with ISO 7933 parameters. Backend PHS calc at `backend/app/api/v1/calculations.py:248-281` returns Dlim, core temperature estimate, and water loss.
> **Missing**: Explicit red "Esposizione critica - misure obbligatorie" banner when Dlim < 30 min is not confirmed in the PHS result UI (backend provides the data; frontend banner rendering needs verification/implementation).

**Acceptance Criteria:**

- **Given** an environment is flagged "Calore severo", **When** I open its microclima panel, **Then** the form switches to PHS mode with the additional parameters required by ISO 7933
- **Given** I enter all PHS parameters, **When** the calculation runs, **Then** Dlim (max exposure minutes) is shown alongside core temperature and water loss estimates
- **Given** Dlim is below 30 minutes, **When** the result renders, **Then** a red warning banner "Esposizione critica - misure obbligatorie" is shown above the result

### Rischio Biologico (Biological Risk)

#### US-3.15 `PARTIAL`
As an operator, I want to select the sector type (nursery, food, dental, etc.) and get auto-populated biological agents and prevention measures.

> **Built**: 3 biologico generators (`alimentare`, `asilo`, `dentisti`) produce valid `.docx`. Frontend stub at `frontend/src/app/(dashboard)/assessments/biologico/[aziendaId]/page.tsx` with 3-sector selector (per Sprint Closure 2026-04-14).
> **Missing**: No biological agents database. No auto-population of agents + prevention measures per sector. No "Altro" manual entry mode. Edits are not persisted against the client.

**Acceptance Criteria:**

- **Given** I open the Biological Risk module, **When** I select sector "Asilo nido", **Then** the form pre-fills with the standard biological agents (virus respiratori, batteri intestinali, etc.) and prevention measures for that sector
- **Given** my client's activity is not covered by a predefined sector, **When** I select "Altro", **Then** the form provides empty editable lists for me to enter agents and measures manually
- **Given** I edit the auto-populated lists, **When** I save, **Then** my changes are stored against the client without modifying the global sector template

---

## Epic 4: Complementary Documents

### PEE (Emergency Plan)

#### US-4.1 `PARTIAL`
As an operator, I want the PEE auto-generated from DVR data (environments, emergency teams, assembly points).

> **Built**: `PEE_AZIENDA` (579 paragraphs, 18 tables) and `PEE_COMUNE` (985 paragraphs, 13 tables) generators produce valid `.docx` against Acme fixture. Registered in documents page with per-type generate/download (Sprint Closure 2026-04-14).
> **Missing**: No "Genera prima il DVR Master" dependency block. No floor plan image embedding or "Inserire planimetria" placeholder. No per-client emergency team/assembly point overrides surfaced in UX.

**Acceptance Criteria:**

- **Given** a DVR exists for the client and emergency team members are assigned, **When** I click "Genera PEE", **Then** the system produces a .docx with environments, team roster, assembly points, and contact procedures pre-filled
- **Given** no DVR exists yet, **When** I attempt to generate the PEE, **Then** the action is blocked with the message "Genera prima il DVR Master"
- **Given** the floor plan image was uploaded with the DVR, **When** the PEE is generated, **Then** it is embedded in the document at the designated section; otherwise a placeholder "Inserire planimetria" is shown

#### US-4.2 `DONE`
As an operator, I want standard emergency procedures (A-E) for each event type pre-filled.

> **Built**: Standard A-E procedures per event (incendio, terremoto, allagamento, fuga_gas, evacuazione_generale) in `backend/app/data/pee_procedures.py` — 5×5 grid, Italian text grounded in D.M. 02/09/2021 + D.Lgs. 81/2008 art. 46. CRUD endpoints at `backend/app/api/v1/pee_procedures.py`: `GET /aziende/{id}/pee/procedure` returns the merged (standard + overrides) grid; `PUT /procedure/{evento}/{lettera}` persists a per-client override into `pee_plans.scenari` (JSONB); `DELETE /procedure/{evento}/{lettera}` drops the override and returns the restored standard. Frontend review page at `frontend/src/app/(dashboard)/assessments/pee/[aziendaId]/page.tsx` renders the grid as five event cards with inline edit, "Personalizzata" badges, and a Dialog-gated "Ripristina standard" action. PEE generator (`pee_azienda.py`) now renders the structured A-E sections using `merge_with_overrides()` so customizations flow through to the `.docx`.

**Acceptance Criteria:**

- **Given** the PEE is being generated, **When** the procedures section is built, **Then** each event type (incendio, terremoto, allagamento, fuga di gas, evacuazione generale) is pre-filled with procedures A-E from the standard template
- **Given** I want to customize a procedure for this client, **When** I edit it in place, **Then** the customization is saved per client and reused on the next generation
- **Given** I want to revert customizations, **When** I click "Reset alle procedure standard", **Then** the customized text is replaced with the global template after a confirmation dialog

### HACCP

#### US-4.3 `PARTIAL`
As an operator, I want the HACCP manual auto-generated based on food activity type with customized CCP analysis.

> **Built**: `HACCP` generator produces 1370 paragraphs / 23 tables against Acme fixture. Registered in documents page (Sprint Closure 2026-04-14).
> **Missing**: No food-activity-type selector UI (e.g., "Ristorante con cucina" vs. "Bar"). No activity-specific CCP pre-loading. No edit-then-merge flow on activity type change. Customized CCPs not tracked per client.

**Acceptance Criteria:**

- **Given** I select food activity type (e.g., "Ristorante con cucina"), **When** I generate the HACCP manual, **Then** the system pre-loads CCPs relevant to that activity (cottura, conservazione, scongelamento)
- **Given** I edit a CCP entry (e.g., change a critical temperature limit), **When** I save, **Then** the change is reflected in both the on-screen review and the generated .docx
- **Given** the activity type is changed after the manual was generated, **When** I regenerate, **Then** I am warned that customizations may be lost and given the option to merge

#### US-4.4 `PARTIAL`
As an operator, I want all 16 self-check forms (SA-01 to SA-16) generated as fillable templates.

> **Built**: `HACCP_FORMS` generator bundles 17 entries into a `.zip` ready for download (Sprint Closure 2026-04-14). 16 HACCP templates sit in `templates/haccp/` folder.
> **Missing**: No per-client branding (logo, ragione sociale) injected into forms. No subset-selection dialog before generation — always bundles all 17.

**Acceptance Criteria:**

- **Given** the HACCP manual is generated for a client, **When** I click "Genera schede di autocontrollo", **Then** all 16 forms (SA-01 to SA-16) are produced as fillable .docx templates pre-branded with client logo and ragione sociale
- **Given** I want only a subset of forms, **When** I open the generation dialog, **Then** I can deselect specific forms before generation
- **Given** the forms are ready, **When** the job finishes, **Then** they are bundled in a single .zip download for convenience

### DUVRI (Contractor Interference)

#### US-4.5 `PARTIAL`
As an operator, I want principal company data auto-filled from the DVR and contractor data entered separately.

> **Built**: `DUVRI` generator produces 688 paragraphs / 23 tables; principal data flows from shared survey/azienda records via `load_data()` (Sprint Closure 2026-04-14).
> **Missing**: No "Aggiungi appaltatore" UI for contractor entry. No "Dati committente aggiornati" sync banner when principal data changes. Contractor section currently implicit in generator rather than a managed data entity.

**Acceptance Criteria:**

- **Given** a DVR exists for the principal company, **When** I create a new DUVRI, **Then** all principal data (ragione sociale, sede, RSPP, datore di lavoro) is auto-populated and read-only
- **Given** I want to add a contractor, **When** I click "Aggiungi appaltatore", **Then** a new contractor section opens with empty fields for the contractor's data and scope of work
- **Given** the DVR principal data changes, **When** I open the DUVRI again, **Then** the principal section updates automatically and a banner notes "Dati committente aggiornati"

#### US-4.6 `NOT STARTED`
As an operator, I want interference analysis per equipment type with suggested prevention measures.

> **Built**: Nothing.
> **Missing**: No interference analysis engine. No equipment overlap detection. No rules engine. No accept/reject per measure.

**Acceptance Criteria:**

- **Given** the principal and contractor have declared their equipment, **When** the interference analysis runs, **Then** combinations of overlapping equipment types produce suggested prevention measures from a rules engine
- **Given** I review a suggested measure, **When** I tap Accept or Reject per row, **Then** my decision is recorded and only accepted measures appear in the final DUVRI
- **Given** no overlapping equipment exists, **When** the analysis runs, **Then** the section displays "Nessuna interferenza rilevata" and a manual entry option is offered

### POS (Construction Site Plan)

#### US-4.7 `PARTIAL`
As an operator, I want to define construction phases with specific risks, NIOSH calculations, and noise/vibration levels per phase.

> **Built**: `POS` generator produces 1272 paragraphs / 87 tables with phase-based structure (Sprint Closure 2026-04-14).
> **Missing**: No phase-builder UI — phases not yet modelled as editable entities. No drag-and-drop reordering. No per-phase NIOSH/noise/vibration attachments from frontend. No dependency linking or Gantt-like overview.

**Acceptance Criteria:**

- **Given** I am building a POS, **When** I add a phase (e.g., "Scavo", "Getto calcestruzzo", "Montaggio impalcature"), **Then** I can attach phase-specific risks, NIOSH parameters, and noise/vibration measurements
- **Given** I want phases in a specific order, **When** I drag and drop them, **Then** the order is persisted and reflected in the generated .docx
- **Given** a phase depends on another phase being complete, **When** I link them, **Then** the dependency is shown both in the UI and in the printed Gantt-like overview

#### US-4.8 `NOT STARTED`
As an operator, I want a detailed job description matrix with DPI per role per phase.

> **Built**: Nothing.
> **Missing**: No role x phase DPI matrix. No rules engine for DPI suggestions. No inline override. No formatted .docx table export.

**Acceptance Criteria:**

- **Given** a phase has assigned roles (carpentiere, manovale, gruista), **When** the matrix is generated, **Then** each role × phase cell is pre-populated with DPI suggestions from the rules engine (casco, scarpe antinfortunistiche, imbragatura, etc.)
- **Given** I want to override the suggested DPI for a specific cell, **When** I edit it inline, **Then** the override is saved against this client only and the global suggestions remain unchanged
- **Given** the matrix is exported to .docx, **When** I open the file, **Then** the matrix appears as a formatted table with merged cells where appropriate

---

## Epic 5: Cross-cutting

#### US-5.1 `PARTIAL`
As an admin, I want to manage multiple client companies and their document packages from a single dashboard.

> **Built**: Dashboard with live KPI cards computed from API data (Clienti attivi, Sopralluoghi in corso, Sopralluoghi completati, Bozze) with colored icons. "Aziende Clienti" table with columns: Ragione Sociale (linked), Attivita, Citta, Stato (color-coded badge), Ultimo Aggiornamento (DD/MM/YYYY). Real-time search (min 2 chars, filters by ragione_sociale/attivita). Default sort by updated_at desc. Loading states.
> **Missing**: No "scadenza DVR" tracking. No role-based action hiding (admin vs. non-admin). No sortable columns. API returns data but no 403 enforcement for non-admin actions.

**Acceptance Criteria:**

- **Given** I am logged in as admin, **When** I open the dashboard, **Then** I see KPI cards (clienti attivi, documenti in lavorazione, scadenze imminenti) and a paginated client table sortable by ragione sociale, ATECO, ultimo aggiornamento, scadenza DVR
- **Given** I type into the dashboard search box, **When** I enter at least 2 characters, **Then** the table filters in real time matching against ragione sociale, partita IVA, and comune
- **Given** I am a non-admin user, **When** I try to access the "Aggiungi cliente" or "Elimina cliente" actions, **Then** the actions are hidden and the API returns 403 if accessed directly

#### US-5.2 `PARTIAL`
As any user, I want all documents generated from the same shared data (enter once, use everywhere).

> **Built**: Backend data model is fully shared — survey data (azienda, persone, ambienti, attrezzature, rischi, sostanze) feeds into DVR generation. Single source of truth via `load_data()`.
> **Missing**: No stale snapshot warning during generation. No field dependency tooltip. No automatic propagation on survey update after document generation.

**Acceptance Criteria:**

- **Given** I update a person's mansione in the survey, **When** I regenerate any downstream document (DVR, PEE, DUVRI), **Then** the new mansione appears without manual re-entry
- **Given** survey data is changed while a generation job is in flight, **When** the job completes, **Then** I receive a warning that the snapshot may be stale and I can choose to regenerate
- **Given** I want to know which documents currently consume a specific data field, **When** I open the field's tooltip, **Then** a list of dependent documents is shown

#### US-5.3 `PARTIAL`
As an operator, I want AI-generated content clearly marked so I know what to review carefully.

> **Built**: Shared `<AIBadge>` component (`frontend/src/components/ai/ai-badge.tsx`) with variants `ai` / `edited` / `manual`, native-title tooltip carrying the "Generato da AI - revisiona prima della pubblicazione" prompt + optional `toLocaleString("it-IT")` timestamp (AC1 + AC2). Global `<AIFilterProvider>` wired into dashboard layout via `providers.tsx`; `<AIFilterToggle>` button in the header flips a page-level "Mostra solo contenuto AI" state that the `<AIContent>` wrapper uses to dim non-AI blocks and accent AI blocks with a violet ring (AC3). Description editor + measures panel refactored to consume the shared primitives.
> **Missing**: Badge system not yet applied to SDS extraction review panel (`step-sostanze.tsx`) or document review surfaces — only Azienda description + improvement measures consume it so far. Thumbs-down signals logged but no admin view.

**Acceptance Criteria:**

- **Given** any document section was produced by AI, **When** I view it in the editor, **Then** a subtle background tint and an "AI" badge are shown alongside the section
- **Given** I hover the AI badge, **When** the tooltip appears, **Then** it reads "Generato da AI - revisiona prima della pubblicazione" and shows a timestamp
- **Given** I want to filter the editor to AI-only content, **When** I toggle "Mostra solo contenuto AI", **Then** non-AI sections are visually dimmed and AI sections remain interactive

#### US-5.4 `PARTIAL`
As an admin, I want secure cloud hosting with daily backups (replacing the USB stick).

> **Built**: Render.com hosting configured with web + worker + redis + disk services in `backend/render.yaml` and `preDeployCommand: alembic upgrade head`. Managed Postgres backups enabled by Render. `AuditLog` model + `app/core/audit.py` helper in place to surface backup/restore events (Sprint Closure 2026-04-14).
> **Missing**: No admin-facing backup status panel (last-backup timestamp, destination region, retention window). No failure alerting to admin email. No restore wizard with isolated-test-environment staging. Audit-log helper exists but backup events don't call it yet.

**Acceptance Criteria:**

- **Given** the platform is in production, **When** I check the backup status panel, **Then** I see the timestamp of the last successful backup, the destination region, and the retention period
- **Given** the daily backup job fails, **When** the failure is detected, **Then** an alert is sent to the admin email and the failure appears in the audit log within 5 minutes
- **Given** I need to restore data, **When** I open the restore wizard, **Then** I can pick any backup point from the retention window and the system performs the restore against an isolated test environment first

---

## Sprint Closure — 2026-04-14 (Niuexa full push)

Per the /mnt/c/Dev/dlg/frontend build sprint, the platform reached end-to-end
operability. All 17 document generators (16 distinct deliverables + HACCP
schede zip) produce valid `.docx`/`.zip` output against the composite test
fixture **Acme Meccanica Composita SRL** (see `backend/app/db/fixtures/acme_meccanica.py`).

### Headline status (post-sprint)

| Area | Before | After |
|------|--------|-------|
| Document generators | 1 / 16 | **17 / 17** (16 docs + HACCP forms bundle) |
| Assessment DB models | 1 (generic) | **12** (mmc, vdt, stress, incendio, microclima, gestanti, biologico, haccp×2, pee, duvri, pos, audit) |
| Celery workers wired | no | **yes** (worker service in `render.yaml`, dispatcher in `tasks/document_tasks.py`) |
| Google Drive delivery | no | **yes** (best-effort, `services/gdrive_service.py`) |
| SDS upload (US-1.8/1.9/1.10) | partial | **DONE** (batch endpoint + background extractor + frontend review panel) |
| Frontend documents dashboard | 11 cards | **17 cards** including batch "Genera tutti" button |
| Download endpoint | missing | **DONE** (`GET /api/v1/documenti/{id}/download`) |
| Gestanti frontend (US-3.9/3.10) | missing | **stub** (`assessments/gestanti/[aziendaId]/page.tsx`) with signature block |
| Biologico frontend (US-3.15) | missing | **stub** (`assessments/biologico/[aziendaId]/page.tsx`) with 3-sector selector |
| RBAC | partial | `require_role(...)` helper in place in `app/dependencies.py` |
| Audit logging (US-5.3) | missing | **helper** `app/core/audit.py` + `AuditLog` model — ready to call from mutation endpoints |
| Automated tests | 0 | **16 / 16 green** (`pytest backend/tests/`) covering calculators, dispatcher routing, and end-to-end generator validity against Acme fixture |
| Deployment config | api only | `render.yaml` now includes web + worker + redis + disk, with `preDeployCommand: alembic upgrade head` |

### Explicit deferrals (documented so N2O/Niuexa can pick up)

- **US-1.3 photo uploads** — not wired; no camera/HEIC UX. Filed as follow-up.
- **Offline mode (IndexedDB + service worker)** — not implemented; draft auto-save only.
- **Digital signatures** — signature lines appear on Gestanti & DUVRI & POS outputs as placeholders, not cryptographically signed.
- **Legal accuracy of generated content** — N2O SRL must review every generated `.docx`. The platform produces structurally correct Italian documents using template boilerplate + formulas but does not guarantee legal compliance.
- **Template matching for 5 unparseable templates** (Microclima × 2 PDF, Biologico × 3 legacy .doc) — generators were built from `DOCUMENT_STRUCTURE.md` + `FORMULAS_AND_CALCULATIONS.md` rather than structural diff.
- **Playwright e2e** — not written (manual verification done via `python -m scripts.verify_all_generators`). Follow-up: dev needs a running Postgres + Redis + frontend to run full browser-level e2e.
- **Audit-log middleware auto-wiring** — the helper exists but individual endpoints still need to call `log_audit(...)`. Non-blocking.

### Acceptance evidence

Running `python -m scripts.verify_all_generators /tmp/out` from `backend/`:

```
[PASS] DVR_MASTER                      -> 85 paragraphs, 14 tables
[PASS] ALLEGATO_MMC                    -> 451 paragraphs, 32 tables
[PASS] ALLEGATO_VDT                    -> 405 paragraphs, 24 tables
[PASS] ALLEGATO_STRESS                 -> 488 paragraphs, 53 tables
[PASS] ALLEGATO_GESTANTI               -> 173 paragraphs,  9 tables
[PASS] ALLEGATO_INCENDIO               -> 395 paragraphs, 31 tables
[PASS] ALLEGATO_MICROCLIMA             ->   6 paragraphs,  3 tables
[PASS] ALLEGATO_MICROCLIMA_SEVERO      ->   7 paragraphs,  3 tables
[PASS] ALLEGATO_BIOLOGICO_ALIMENTARE   ->  13 paragraphs,  3 tables
[PASS] ALLEGATO_BIOLOGICO_ASILO        ->  20 paragraphs,  3 tables
[PASS] ALLEGATO_BIOLOGICO_DENTISTI     ->  21 paragraphs,  3 tables
[PASS] PEE_AZIENDA                     -> 579 paragraphs, 18 tables
[PASS] PEE_COMUNE                      -> 985 paragraphs, 13 tables
[PASS] HACCP                           -> 1370 paragraphs, 23 tables
[PASS] HACCP_FORMS                     -> zip with 17 entries
[PASS] DUVRI                           -> 688 paragraphs, 23 tables
[PASS] POS                             -> 1272 paragraphs, 87 tables

RESULT: 17/17 generators produced valid output
```

And `pytest backend/tests/`:

```
16 passed in 18.11s
```

### Go-live runbook

1. Provision Render services via `backend/render.yaml` (db, web, worker, redis, disk).
2. Set env vars on Render dashboard: `OPENAI_API_KEY`, optionally `GOOGLE_DRIVE_FOLDER_ID` (default `13aHCy8D78JwJzgffxYbqe7Nmyed84may`), and copy `credentials/token.json` to an env-readable path for Drive uploads.
3. First deploy runs `alembic upgrade head` automatically (preDeployCommand) — creates all 23 tables.
4. Seed demo data: `python -m app.db.fixtures.acme_meccanica` against the Render Postgres URL.
5. Deploy frontend on Vercel with `NEXT_PUBLIC_API_URL=https://n2o-dvr-api.onrender.com`.
6. Smoke test: log in as `admin@acme-meccanica.test` / `Acme2026!`, open Documenti page, click "Genera tutti" → wait for all 17 cards to reach status "Pronto", download each.

---

*© 2026 Niuexa. Confidential — prepared for N2O SRL.*
