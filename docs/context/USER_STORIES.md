> **NIUEXA** | AI-Powered Business Automation  
> *N2O DVR Automation Platform — Project Documentation*  
> Version 1.1 | April 2026 | Gregor Maric  
> Confidential — Niuexa & N2O SRL

---

# User Stories

Each story follows the format `As a <persona>, I want <capability>, so that <benefit>` and is paired with **Acceptance Criteria** expressed as Given/When/Then scenarios. UI labels are quoted in Italian to match the production interface; the surrounding prose is in English.

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

#### US-1.1
As a field operator, I want to fill in structured company data fields (ragione sociale, sede, ATECO code) so that I don't have to re-type this info later.

**Acceptance Criteria:**

- **Given** I am on Step 1 "Azienda" of the survey wizard, **When** I enter ragione sociale, partita IVA, indirizzo sede, and codice ATECO, **Then** the data is auto-saved as a draft within 2 seconds and persists across sessions
- **Given** I leave a required field empty, **When** I attempt to advance to Step 2, **Then** the field is highlighted in red with an inline message "Campo obbligatorio" and navigation is blocked
- **Given** I enter an invalid partita IVA (not 11 digits) or ATECO code (not matching `NN.NN.NN` format), **When** the field loses focus, **Then** an inline error appears and the field is excluded from auto-save until corrected

#### US-1.2
As a field operator, I want dynamic equipment checklists that change based on environment type (office, warehouse, kitchen) so I only see relevant items.

**Acceptance Criteria:**

- **Given** I am on Step 4 "Attrezzature" with an environment of type "Ufficio", **When** the equipment panel loads, **Then** I see only office-relevant items (scrivania, sedia ergonomica, monitor, tastiera, mouse, stampante)
- **Given** I switch the environment type from "Ufficio" to "Magazzino", **When** the change is confirmed, **Then** the checklist refreshes to show warehouse items (scaffalatura, transpallet, muletto, casco) and previously checked office items are preserved on the original environment
- **Given** I am working on an environment whose type is not in the predefined list, **When** the checklist loads, **Then** I see a generic checklist with an "Aggiungi attrezzatura" button to enter custom items

#### US-1.3
As a field operator, I want to upload photos of each work environment and equipment so they can be referenced during document generation.

**Acceptance Criteria:**

- **Given** I am on Step 3 "Ambienti" and have selected an environment, **When** I tap "Aggiungi foto", **Then** the device camera opens and I can capture or select up to 10 photos per environment
- **Given** I have uploaded a photo, **When** the upload completes, **Then** the photo appears as a thumbnail with a delete icon, the original filename, and the file size
- **Given** I attempt to upload a file larger than 10 MB or in an unsupported format (not JPG/PNG/HEIC), **When** the upload is triggered, **Then** I see an inline toast "Formato non supportato o file troppo grande (max 10 MB)" and the file is rejected
- **Given** my network connection drops mid-upload, **When** connectivity is restored, **Then** the upload retries automatically and I see a persistent "Caricamento in corso" indicator

#### US-1.4
As a field operator, I want to register employees with their roles, assignments to environments, and qualifications in a structured form.

**Acceptance Criteria:**

- **Given** I am on Step 2 "Persone", **When** I tap "Aggiungi persona", **Then** a modal opens with fields nome, cognome, codice fiscale, mansione, ambienti assegnati (multi-select), and qualifiche
- **Given** I enter a codice fiscale that does not match the 16-character alphanumeric pattern, **When** the field loses focus, **Then** an inline error "Codice fiscale non valido" is shown and Save is disabled
- **Given** I save a valid person, **When** the modal closes, **Then** the person appears as a row in the Persone table with a hover action menu (Edit, Delete)
- **Given** I tap Delete on a person, **When** the confirmation modal appears, **Then** I must explicitly confirm "Elimina" before the row is removed (no soft delete in MVP)

#### US-1.5
As a field operator, I want a contextualized risk list (not the full generic decree list) so I can quickly mark applicable risks per environment.

**Acceptance Criteria:**

- **Given** I am on Step 5 "Rischi" with environments and equipment already declared, **When** the risk list loads, **Then** only risks contextually relevant to the selected environments and equipment categories are shown (filtered from the full D.Lgs. 81 catalog)
- **Given** I tap a risk to mark it applicable to an environment, **When** the toggle activates, **Then** the summary bar at the bottom updates the count "X rischi selezionati"
- **Given** I return to Step 3 "Ambienti" and add or remove an environment after marking risks, **When** I navigate back to Step 5, **Then** I see a banner "Ambienti modificati - rivedi le selezioni" prompting me to reconfirm

#### US-1.6
As a field operator, I want the client to digitally countersign the completed survey on my device so I have legal proof of acceptance.

**Acceptance Criteria:**

- **Given** I am on Step 7 "Riepilogo" and all previous steps are complete, **When** I scroll to the countersignature section, **Then** a signature canvas is enabled and a timestamp field is auto-populated
- **Given** any earlier step is incomplete, **When** I open Step 7, **Then** the signature canvas is disabled and a banner lists the missing items as clickable links
- **Given** the client has drawn a signature and I tap "Conferma firma", **When** the action completes, **Then** the signature is stored as a PNG against the survey with a server-side timestamp and the survey lifecycle moves to status "Firmato"
- **Given** the survey is already signed, **When** any user tries to edit a step, **Then** all fields become read-only and an "Apri revisione" button is offered for an audited modification flow

#### US-1.7
As a field operator, I want to assign safety roles (RSPP, RLS, primo soccorso, antincendio, preposto) to personnel during the survey so the DVR header is auto-populated.

**Acceptance Criteria:**

- **Given** I open the Add/Edit Person modal, **When** I tick one or more of the role checkboxes (RSPP, RLS, ASPP, addetto primo soccorso, addetto antincendio, preposto), **Then** the role badges appear next to the person's name in the Persone table
- **Given** the survey has zero persons marked as RSPP, **When** I attempt to advance to Step 7, **Then** validation blocks me with "È richiesto almeno un RSPP per completare la survey"
- **Given** one person holds multiple roles, **When** the DVR is generated, **Then** all of their roles appear in the corresponding tables of the DVR Master without duplication

### Chemical SDS Upload

#### US-1.8
As an operator, I want to batch upload up to 20 chemical SDS PDFs at a time so I don't have to process them one by one.

**Acceptance Criteria:**

- **Given** I am on Step 6 "Sostanze Chimiche", **When** I drag 20 PDF files onto the upload zone, **Then** all 20 files are queued for upload with individual progress bars
- **Given** I attempt to upload a 21st file in the same batch, **When** the file is added, **Then** an inline message "Massimo 20 file per caricamento" appears and the file is rejected
- **Given** I drop a file that is not a PDF or exceeds 10 MB, **When** the file enters the queue, **Then** it is immediately marked failed with the reason and no extraction is attempted

#### US-1.9
As an operator, I want AI to automatically extract product name, manufacturer, pictograms, mixture state, and H/P phrases from each SDS so I don't have to transcribe them.

**Acceptance Criteria:**

- **Given** an SDS PDF has finished uploading, **When** the extraction job runs, **Then** the file row shows status "Estrazione in corso" with a spinner, then "Completata" with the extracted fields populated
- **Given** the AI cannot extract a field with high confidence, **When** the extraction completes, **Then** that field is left blank, marked with a yellow warning icon, and a tooltip says "Confidenza bassa - inserisci manualmente"
- **Given** extraction fails entirely (e.g., scanned image with no OCR), **When** the job ends, **Then** the row shows status "Estrazione fallita" and a "Inserisci manualmente" button opens an empty editable row

#### US-1.10
As an operator, I want to review and correct AI-extracted chemical data in a table before it's finalized so I can catch errors.

**Acceptance Criteria:**

- **Given** AI extraction has completed for at least one SDS, **When** I open the Extraction Review Table, **Then** every cell is editable inline and AI-generated values are visually marked with an "AI" badge
- **Given** I edit an AI-generated cell, **When** I commit the change, **Then** the AI badge is removed and replaced by a "Revisionato" indicator with my user ID
- **Given** I tap "Conferma estrazione", **When** the action completes, **Then** the chemicals are persisted to the database and the Step 6 indicator turns green

---

## Epic 2: DVR Master Generation

#### US-2.1
As an office operator, I want the system to auto-generate the company description from survey data + visura + website using AI so I don't have to write boilerplate.

**Acceptance Criteria:**

- **Given** the survey is signed and a visura PDF is attached, **When** I click "Genera descrizione azienda", **Then** the AI produces a 200-400 word Italian description and shows it in a rich text editor with an "AI" badge
- **Given** I edit the generated text, **When** I save, **Then** the badge changes to "Modificato dall'utente" and the original AI version is retained in the version history
- **Given** the AI call fails or times out (>30s), **When** the error surfaces, **Then** I see "Generazione fallita - riprova o inserisci manualmente" with a Retry button and the editor remains usable for manual entry

#### US-2.2
As an office operator, I want territorial context (seismic zone, local regulations) auto-populated so I don't have to look it up per municipality.

**Acceptance Criteria:**

- **Given** I have entered the comune in Step 1 "Azienda", **When** the DVR generation starts, **Then** the system fetches seismic zone (1-4) and applicable regional regulations from a local lookup table and inserts them into the Parte I context section
- **Given** the comune is not in the lookup table, **When** the lookup fails, **Then** the field is left blank with a warning "Comune non trovato - inserisci manualmente"
- **Given** territorial data is auto-populated, **When** I view it in the editor, **Then** it is read-only by default with an "Override" button to enable manual edit

#### US-2.3
As an office operator, I want risk tables pre-populated per environment with contextualized severity scores that I can review and adjust.

**Acceptance Criteria:**

- **Given** I open the Risk Scoring Interface for a generated DVR, **When** the table loads, **Then** every environment appears as a grouped section with risks pre-filled from a default scoring matrix
- **Given** I adjust the P or D value for a risk, **When** the value changes, **Then** I = 2*D + P is recomputed in real time and the row's color band updates accordingly
- **Given** I want to revert my changes, **When** I click the "Reset al default" icon on a row, **Then** the original AI-suggested score is restored and the override flag is cleared

#### US-2.4
As an office operator, I want the equipment list with CE marking auto-filled from the survey so I don't duplicate data entry.

**Acceptance Criteria:**

- **Given** equipment was declared in Step 4 of the survey, **When** the DVR is generated, **Then** the equipment table in Parte II is populated with the marca, modello, anno, and CE checkbox values
- **Given** an item lacks CE marking, **When** the table renders, **Then** the row is highlighted in red and a footnote is automatically added to the DVR mentioning the non-conformity
- **Given** I edit a row inline (e.g., add a missing modello), **When** I save, **Then** the change propagates back to the survey data so it is reused in subsequent generations

#### US-2.5
As an office operator, I want employee tables with roles and environment assignments auto-generated so the personnel section requires no manual work.

**Acceptance Criteria:**

- **Given** persons were declared in Step 2 with mansioni, ambienti, and qualifiche, **When** the DVR is generated, **Then** the personnel section lists every person grouped by ambiente with their mansione, qualifiche, and role badges (RSPP/RLS/etc.)
- **Given** the survey is updated after a DVR was generated, **When** I regenerate the same document, **Then** the personnel table reflects the new survey state and a diff is shown in the version log
- **Given** the table is rendered in the final .docx, **When** I open it in Word, **Then** the table uses the official N2O style (header row in dark gray, alternating row shading)

#### US-2.6
As an office operator, I want AI-suggested improvement measures based on identified risks that I can accept, modify, or reject.

**Acceptance Criteria:**

- **Given** a risk row is expanded in the Risk Scoring Interface, **When** the misure di prevenzione panel loads, **Then** the AI returns 2-5 suggestions with Accetta / Modifica / Rifiuta buttons per item
- **Given** I accept a suggestion, **When** the action completes, **Then** the measure is added to the DVR text with an "AI - accettato" tag and saved to a per-client measures library for reuse
- **Given** I reject a suggestion, **When** the action completes, **Then** the measure is removed from view and a thumbs-down feedback signal is recorded for future model fine-tuning
- **Given** I want to add my own measure, **When** I click "Aggiungi misura personalizzata", **Then** an empty editable row appears and the saved measure is tagged "Manuale"

#### US-2.7
As an office operator, I want to set P (probability) and D (damage) scores for each risk and have the system calculate I = 2*D + P automatically.

**Acceptance Criteria:**

- **Given** I am on a risk row with empty P and D, **When** I enter P=2 and D=3, **Then** the I column displays 8 with the orange "Grave" band
- **Given** I attempt to enter a value outside the range 1-4 in either P or D field, **When** the field loses focus, **Then** the value is rejected and a tooltip "Valore consentito: 1-4" is shown (Note: Fire risk INF/SI/PI uses 1-3 separately — see US-3.11)
- **Given** I have selected multiple rows via checkbox, **When** I use the bulk action "Imposta P/D", **Then** the chosen P and D are applied to every selected row and I is recomputed for each
- **Given** I change a value that triggers a band change (e.g., I goes from 8 "Grave" to 9 "Gravissimo"), **When** the recalculation finishes, **Then** the row animates the color transition over 200 ms

#### US-2.8
As an office operator, I want the final DVR output as a professionally formatted .docx with cover page, logo, and table of contents.

**Acceptance Criteria:**

- **Given** all DVR sections are complete and reviewed, **When** I click "Genera DVR finale", **Then** a background job produces a .docx containing cover page (logo + ragione sociale + data), table of contents, all four parts (I-IV), and ~111 tables according to the template mapping
- **Given** the generation finishes successfully, **When** the file is ready, **Then** I receive a desktop notification and the file is downloadable from the document drawer with a versioned filename `DVR_<ragione_sociale>_<YYYYMMDD>_v<N>.docx`
- **Given** the generation fails halfway, **When** the error is captured, **Then** the partial file is discarded, the document status is rolled back to "Bozza", and the error is logged with a user-friendly message

#### US-2.9
As an office operator, I want version tracking for document revisions so I can audit changes over time.

**Acceptance Criteria:**

- **Given** I have generated a DVR at least twice, **When** I open the Version History panel, **Then** I see a chronological list with version number, user, timestamp, and a "Differenze" button
- **Given** I click "Differenze" between v2 and v3, **When** the diff loads, **Then** I see a side-by-side comparison highlighting added, removed, and modified text/tables
- **Given** I want to restore an earlier version, **When** I click "Ripristina versione", **Then** a new version is created from the historical snapshot (no destructive overwrite)

---

## Epic 3: DVR Attachments

### MMC (Manual Handling - NIOSH)

#### US-3.1
As an operator, I want to input lifting parameters per worker (height, displacement, distance, angle, grip, frequency, duration, actual weight) so I can compute the NIOSH index.

**Acceptance Criteria:**

- **Given** I open the MMC form for a worker, **When** the form loads, **Then** all 8 NIOSH parameters are presented with units (cm for distances, ° for angle, kg for weight, lifts/min for frequency)
- **Given** I enter a value outside the valid range for a parameter (e.g., displacement > 175 cm), **When** the field loses focus, **Then** an inline error explains the valid range and the value is excluded from calculation
- **Given** a worker performs multiple distinct lifting tasks, **When** I click "Aggiungi sollevamento", **Then** an additional parameter set is added and computed independently

#### US-3.2
As an operator, I want the system to auto-derive CP (weight constant) from worker sex and age so I don't have to look it up.

**Acceptance Criteria:**

- **Given** the worker's sex is Maschio and age is "adulto" (18-45), **When** the MMC form opens, **Then** CP is auto-filled with 25 kg per the NIOSH reference table
- **Given** the worker's sex is Femmina and age is "giovane" (15-18), **When** the form opens, **Then** CP is auto-filled with 15 kg
- **Given** the user wants to override the default CP, **When** they click "Modifica CP", **Then** the field becomes editable and a free-text "Motivazione" field is required to save

#### US-3.3
As an operator, I want automatic PLR and IR calculation with Green/Yellow/Red classification.

**Acceptance Criteria:**

- **Given** all 8 parameters and CP are entered, **When** the calculation runs, **Then** PLR = CP × A × B × C × D × E × F is computed and IR = peso effettivo / PLR is shown to 2 decimals
- **Given** IR is 0.50, **When** the result renders, **Then** the row shows a green band "Accettabile" (IR ≤ 0.75)
- **Given** IR is 0.85, **When** the result renders, **Then** the row shows a yellow band "Da ridurre" (0.75 < IR ≤ 1.00)
- **Given** IR is 1.20, **When** the result renders, **Then** the row shows a red band "Non accettabile" (IR > 1.00) and a mandatory measures section appears below

### VDT (Display Screen Equipment)

#### US-3.4
As an operator, I want to enter weekly VDT hours per worker and have the system classify Exposed/Not Exposed (threshold: 20h/week).

**Acceptance Criteria:**

- **Given** I enter 22 hours/week for a worker, **When** the field loses focus, **Then** the worker is automatically classified as "Esposto" with a green check
- **Given** I enter 18 hours/week for a worker, **When** the field loses focus, **Then** the worker is classified as "Non esposto"
- **Given** I have a CSV with VDT hours per worker, **When** I use "Importa da CSV", **Then** the system bulk-imports and classifies all rows in one operation

#### US-3.5
As an operator, I want automatic determination of mandatory health surveillance so workers requiring visits are flagged.

**Acceptance Criteria:**

- **Given** a worker is classified "Esposto", **When** the VDT module finishes, **Then** the worker record is flagged "Sorveglianza sanitaria obbligatoria" with the next visit due date computed (5 years for under-50, 2 years for 50+)
- **Given** a worker has an upcoming visit due in less than 60 days, **When** the dashboard loads, **Then** the worker appears in the "Visite in scadenza" widget
- **Given** the visit due date has passed, **When** the dashboard loads, **Then** the worker appears in the "Visite scadute" widget with red highlighting

### Stress Lavoro-Correlato (Work Stress)

#### US-3.6
As an operator, I want a digital checklist with ~50 INAIL indicators (SI/NO) across 3 areas (A, B, C) so I can score work-related stress.

**Acceptance Criteria:**

- **Given** I open the Stress assessment, **When** the page loads, **Then** all indicators are grouped under areas A (Eventi sentinella), B (Contenuto del lavoro), C (Contesto del lavoro) with SI/NO toggles
- **Given** I am partway through and close the page, **When** I reopen it, **Then** my previous answers are restored from the saved draft
- **Given** I attempt to finalize with unanswered indicators, **When** I click "Conferma valutazione", **Then** the unanswered items are highlighted and the action is blocked

#### US-3.7
As an operator, I want real-time score calculation and automatic risk level (Low/Medium/High) so I see the impact of each answer.

**Acceptance Criteria:**

- **Given** I toggle an indicator from NO to SI, **When** the toggle commits, **Then** the area score and overall risk band update within 200 ms
- **Given** the overall score crosses a threshold band (e.g., from "Basso" to "Medio"), **When** the recalculation completes, **Then** the band header animates the color change and a tooltip shows the threshold rule
- **Given** I hover the score widget, **When** the tooltip appears, **Then** it shows the per-area sub-totals and the overall formula

#### US-3.8
As an operator, I want auto-generated corrective measures based on risk level so I don't write them from scratch.

**Acceptance Criteria:**

- **Given** the assessment finalizes at "Medio" risk, **When** I open the corrective measures section, **Then** a predefined list of measures appropriate for "Medio" is shown with edit and remove icons
- **Given** I edit the suggested text, **When** I save, **Then** the measure is tagged "Personalizzato" and saved to the per-client library
- **Given** I want to add a measure not in the library, **When** I click "Aggiungi misura", **Then** an empty editable row appears

### Gestanti (Pregnant Workers)

#### US-3.9
As an operator, I want automatic cross-reference between female worker roles and D.Lgs. 151/2001 risk factors.

**Acceptance Criteria:**

- **Given** the survey contains female workers with declared mansioni, **When** the Gestanti module runs, **Then** each mansione is cross-checked against the D.Lgs. 151/2001 incompatible risk list and matches are flagged
- **Given** a worker holds a mansione with no matching risks, **When** the report renders, **Then** the worker is shown with a green "Nessun rischio identificato" indicator
- **Given** new risks are added to the survey after the Gestanti report was generated, **When** I regenerate, **Then** previously cleared workers may surface as new matches and are clearly marked "Nuovo"

#### US-3.10
As an operator, I want auto-identification of incompatible tasks and relocation proposals so I can act on them quickly.

**Acceptance Criteria:**

- **Given** an incompatible task is detected for a worker, **When** the report renders, **Then** the row shows the incompatible task and a system-suggested alternate role from the same client
- **Given** I accept a relocation suggestion, **When** the action completes, **Then** it is recorded in the Allegato Gestanti with a justification field
- **Given** I reject a suggestion, **When** the action completes, **Then** I am required to enter a free-text "Misura alternativa" before saving

### Rischio Incendio (Fire Risk)

#### US-3.11
As an operator, I want to input INF/SI/PI scores (1-3 each) per homogeneous area so the fire classification is computed.

**Acceptance Criteria:**

- **Given** I am on the Fire Risk form for an area, **When** I enter INF=2, SI=2, PI=1, **Then** the sum 5 is shown live below the inputs
- **Given** I enter a value outside 1-3, **When** the field loses focus, **Then** the value is rejected with the tooltip "Valore consentito: 1-3"
- **Given** I have multiple homogeneous areas, **When** I use "Duplica area", **Then** the parameters from the current area are copied as a starting point

#### US-3.12
As an operator, I want automatic risk level calculation (Low/Medium/High) and required fire safety measures.

**Acceptance Criteria:**

- **Given** the sum INF+SI+PI is 4, **When** the calculation runs, **Then** the band shows "Basso" with the corresponding measures list
- **Given** the sum is 6, **When** the calculation runs, **Then** the band shows "Medio"
- **Given** the sum is 8, **When** the calculation runs, **Then** the band shows "Alto" and a banner "Richiesta valutazione approfondita VVF" is displayed
- **Given** the band changes after editing scores, **When** the recalculation completes, **Then** the measures list updates accordingly

### Microclima (Thermal Comfort)

#### US-3.13
As an operator, I want to input 6 environmental parameters and get automatic PMV/PPD calculation per environment.

**Acceptance Criteria:**

- **Given** I enter air temperature, mean radiant temperature, air velocity, relative humidity, metabolic rate, and clothing insulation, **When** all 6 fields are valid, **Then** PMV and PPD are computed via pythermalcomfort and displayed with the comfort band (Comfortable / Slightly warm / Hot / etc.)
- **Given** any of the 6 parameters is outside its valid physical range, **When** the field loses focus, **Then** a validation error explains the range and calculation is paused
- **Given** I have multiple environments, **When** I save, **Then** PMV/PPD is computed and stored per environment independently

#### US-3.14
For severe heat environments, I want PHS calculation with maximum exposure time (Dlim).

**Acceptance Criteria:**

- **Given** an environment is flagged "Calore severo", **When** I open its microclima panel, **Then** the form switches to PHS mode with the additional parameters required by ISO 7933
- **Given** I enter all PHS parameters, **When** the calculation runs, **Then** Dlim (max exposure minutes) is shown alongside core temperature and water loss estimates
- **Given** Dlim is below 30 minutes, **When** the result renders, **Then** a red warning banner "Esposizione critica - misure obbligatorie" is shown above the result

### Rischio Biologico (Biological Risk)

#### US-3.15
As an operator, I want to select the sector type (nursery, food, dental, etc.) and get auto-populated biological agents and prevention measures.

**Acceptance Criteria:**

- **Given** I open the Biological Risk module, **When** I select sector "Asilo nido", **Then** the form pre-fills with the standard biological agents (virus respiratori, batteri intestinali, etc.) and prevention measures for that sector
- **Given** my client's activity is not covered by a predefined sector, **When** I select "Altro", **Then** the form provides empty editable lists for me to enter agents and measures manually
- **Given** I edit the auto-populated lists, **When** I save, **Then** my changes are stored against the client without modifying the global sector template

---

## Epic 4: Complementary Documents

### PEE (Emergency Plan)

#### US-4.1
As an operator, I want the PEE auto-generated from DVR data (environments, emergency teams, assembly points).

**Acceptance Criteria:**

- **Given** a DVR exists for the client and emergency team members are assigned, **When** I click "Genera PEE", **Then** the system produces a .docx with environments, team roster, assembly points, and contact procedures pre-filled
- **Given** no DVR exists yet, **When** I attempt to generate the PEE, **Then** the action is blocked with the message "Genera prima il DVR Master"
- **Given** the floor plan image was uploaded with the DVR, **When** the PEE is generated, **Then** it is embedded in the document at the designated section; otherwise a placeholder "Inserire planimetria" is shown

#### US-4.2
As an operator, I want standard emergency procedures (A-E) for each event type pre-filled.

**Acceptance Criteria:**

- **Given** the PEE is being generated, **When** the procedures section is built, **Then** each event type (incendio, terremoto, allagamento, fuga di gas, evacuazione generale) is pre-filled with procedures A-E from the standard template
- **Given** I want to customize a procedure for this client, **When** I edit it in place, **Then** the customization is saved per client and reused on the next generation
- **Given** I want to revert customizations, **When** I click "Reset alle procedure standard", **Then** the customized text is replaced with the global template after a confirmation dialog

### HACCP

#### US-4.3
As an operator, I want the HACCP manual auto-generated based on food activity type with customized CCP analysis.

**Acceptance Criteria:**

- **Given** I select food activity type (e.g., "Ristorante con cucina"), **When** I generate the HACCP manual, **Then** the system pre-loads CCPs relevant to that activity (cottura, conservazione, scongelamento)
- **Given** I edit a CCP entry (e.g., change a critical temperature limit), **When** I save, **Then** the change is reflected in both the on-screen review and the generated .docx
- **Given** the activity type is changed after the manual was generated, **When** I regenerate, **Then** I am warned that customizations may be lost and given the option to merge

#### US-4.4
As an operator, I want all 16 self-check forms (SA-01 to SA-16) generated as fillable templates.

**Acceptance Criteria:**

- **Given** the HACCP manual is generated for a client, **When** I click "Genera schede di autocontrollo", **Then** all 16 forms (SA-01 to SA-16) are produced as fillable .docx templates pre-branded with client logo and ragione sociale
- **Given** I want only a subset of forms, **When** I open the generation dialog, **Then** I can deselect specific forms before generation
- **Given** the forms are ready, **When** the job finishes, **Then** they are bundled in a single .zip download for convenience

### DUVRI (Contractor Interference)

#### US-4.5
As an operator, I want principal company data auto-filled from the DVR and contractor data entered separately.

**Acceptance Criteria:**

- **Given** a DVR exists for the principal company, **When** I create a new DUVRI, **Then** all principal data (ragione sociale, sede, RSPP, datore di lavoro) is auto-populated and read-only
- **Given** I want to add a contractor, **When** I click "Aggiungi appaltatore", **Then** a new contractor section opens with empty fields for the contractor's data and scope of work
- **Given** the DVR principal data changes, **When** I open the DUVRI again, **Then** the principal section updates automatically and a banner notes "Dati committente aggiornati"

#### US-4.6
As an operator, I want interference analysis per equipment type with suggested prevention measures.

**Acceptance Criteria:**

- **Given** the principal and contractor have declared their equipment, **When** the interference analysis runs, **Then** combinations of overlapping equipment types produce suggested prevention measures from a rules engine
- **Given** I review a suggested measure, **When** I tap Accept or Reject per row, **Then** my decision is recorded and only accepted measures appear in the final DUVRI
- **Given** no overlapping equipment exists, **When** the analysis runs, **Then** the section displays "Nessuna interferenza rilevata" and a manual entry option is offered

### POS (Construction Site Plan)

#### US-4.7
As an operator, I want to define construction phases with specific risks, NIOSH calculations, and noise/vibration levels per phase.

**Acceptance Criteria:**

- **Given** I am building a POS, **When** I add a phase (e.g., "Scavo", "Getto calcestruzzo", "Montaggio impalcature"), **Then** I can attach phase-specific risks, NIOSH parameters, and noise/vibration measurements
- **Given** I want phases in a specific order, **When** I drag and drop them, **Then** the order is persisted and reflected in the generated .docx
- **Given** a phase depends on another phase being complete, **When** I link them, **Then** the dependency is shown both in the UI and in the printed Gantt-like overview

#### US-4.8
As an operator, I want a detailed job description matrix with DPI per role per phase.

**Acceptance Criteria:**

- **Given** a phase has assigned roles (carpentiere, manovale, gruista), **When** the matrix is generated, **Then** each role × phase cell is pre-populated with DPI suggestions from the rules engine (casco, scarpe antinfortunistiche, imbragatura, etc.)
- **Given** I want to override the suggested DPI for a specific cell, **When** I edit it inline, **Then** the override is saved against this client only and the global suggestions remain unchanged
- **Given** the matrix is exported to .docx, **When** I open the file, **Then** the matrix appears as a formatted table with merged cells where appropriate

---

## Epic 5: Cross-cutting

#### US-5.1
As an admin, I want to manage multiple client companies and their document packages from a single dashboard.

**Acceptance Criteria:**

- **Given** I am logged in as admin, **When** I open the dashboard, **Then** I see KPI cards (clienti attivi, documenti in lavorazione, scadenze imminenti) and a paginated client table sortable by ragione sociale, ATECO, ultimo aggiornamento, scadenza DVR
- **Given** I type into the dashboard search box, **When** I enter at least 2 characters, **Then** the table filters in real time matching against ragione sociale, partita IVA, and comune
- **Given** I am a non-admin user, **When** I try to access the "Aggiungi cliente" or "Elimina cliente" actions, **Then** the actions are hidden and the API returns 403 if accessed directly

#### US-5.2
As any user, I want all documents generated from the same shared data (enter once, use everywhere).

**Acceptance Criteria:**

- **Given** I update a person's mansione in the survey, **When** I regenerate any downstream document (DVR, PEE, DUVRI), **Then** the new mansione appears without manual re-entry
- **Given** survey data is changed while a generation job is in flight, **When** the job completes, **Then** I receive a warning that the snapshot may be stale and I can choose to regenerate
- **Given** I want to know which documents currently consume a specific data field, **When** I open the field's tooltip, **Then** a list of dependent documents is shown

#### US-5.3
As an operator, I want AI-generated content clearly marked so I know what to review carefully.

**Acceptance Criteria:**

- **Given** any document section was produced by AI, **When** I view it in the editor, **Then** a subtle background tint and an "AI" badge are shown alongside the section
- **Given** I hover the AI badge, **When** the tooltip appears, **Then** it reads "Generato da AI - revisiona prima della pubblicazione" and shows a timestamp
- **Given** I want to filter the editor to AI-only content, **When** I toggle "Mostra solo contenuto AI", **Then** non-AI sections are visually dimmed and AI sections remain interactive

#### US-5.4
As an admin, I want secure cloud hosting with daily backups (replacing the USB stick).

**Acceptance Criteria:**

- **Given** the platform is in production, **When** I check the backup status panel, **Then** I see the timestamp of the last successful backup, the destination region, and the retention period
- **Given** the daily backup job fails, **When** the failure is detected, **Then** an alert is sent to the admin email and the failure appears in the audit log within 5 minutes
- **Given** I need to restore data, **When** I open the restore wizard, **Then** I can pick any backup point from the retention window and the system performs the restore against an isolated test environment first

---

*© 2026 Niuexa. Confidential — prepared for N2O SRL.*
