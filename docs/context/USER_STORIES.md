> **NIUEXA** | AI-Powered Business Automation  
> *N2O DVR Automation Platform — Project Documentation*  
> Version 1.0 | April 2026 | Gregor Maric  
> Confidential — Niuexa & N2O SRL

---

# User Stories

## Personas

### Operatore sul Campo (Field Operator)
Safety consultant who visits client sites to conduct surveys and collect data. Uses tablet/smartphone.

### Operatore in Ufficio (Office Operator)
Safety consultant who reviews AI-generated documents, adjusts risk scores, and finalizes documentation.

### Amministratore (Admin)
Manages client portfolio, oversees document generation, handles billing and delivery.

---

## Epic 1: Digital Survey (Scheda di Rilevazione Digitale)

### Field Data Collection
- **US-1.1**: As a field operator, I want to fill in structured company data fields (ragione sociale, sede, ATECO code) so that I don't have to re-type this info later
- **US-1.2**: As a field operator, I want dynamic equipment checklists that change based on environment type (office, warehouse, kitchen) so I only see relevant items
- **US-1.3**: As a field operator, I want to upload photos of each work environment and equipment so they can be referenced during document generation
- **US-1.4**: As a field operator, I want to register employees with their roles, assignments to environments, and qualifications in a structured form
- **US-1.5**: As a field operator, I want a contextualized risk list (not the full generic decree list) so I can quickly mark applicable risks per environment
- **US-1.6**: As a field operator, I want the client to digitally countersign the completed survey on my device
- **US-1.7**: As a field operator, I want to assign safety roles (RSPP, RLS, primo soccorso, antincendio, preposto) to personnel during the survey

### Chemical SDS Upload
- **US-1.8**: As an operator, I want to batch upload up to 20 chemical SDS PDFs at a time
- **US-1.9**: As an operator, I want AI to automatically extract product name, manufacturer, pictograms, mixture state, and H/P phrases from each SDS
- **US-1.10**: As an operator, I want to review and correct AI-extracted chemical data in a table before it's finalized

---

## Epic 2: DVR Master Generation

- **US-2.1**: As an office operator, I want the system to auto-generate the company description from survey data + visura + website using AI
- **US-2.2**: As an office operator, I want territorial context (seismic zone, local regulations) auto-populated
- **US-2.3**: As an office operator, I want risk tables pre-populated per environment with contextualized severity scores that I can review and adjust
- **US-2.4**: As an office operator, I want the equipment list with CE marking auto-filled from the survey
- **US-2.5**: As an office operator, I want employee tables with roles and environment assignments auto-generated
- **US-2.6**: As an office operator, I want AI-suggested improvement measures based on identified risks that I can accept, modify, or reject
- **US-2.7**: As an office operator, I want to set P (probability) and D (damage) scores for each risk and have the system calculate I = 2*D + P automatically
- **US-2.8**: As an office operator, I want the final DVR output as a professionally formatted .docx with cover page, logo, and table of contents
- **US-2.9**: As an office operator, I want version tracking for document revisions

---

## Epic 3: DVR Attachments

### MMC (Manual Handling - NIOSH)
- **US-3.1**: As an operator, I want to input lifting parameters per worker (height, displacement, distance, angle, grip, frequency, duration, actual weight)
- **US-3.2**: As an operator, I want the system to auto-derive CP (weight constant) from worker sex and age
- **US-3.3**: As an operator, I want automatic PLR and IR calculation with Green/Yellow/Red classification

### VDT (Display Screen Equipment)
- **US-3.4**: As an operator, I want to enter weekly VDT hours per worker and have the system classify Exposed/Not Exposed (threshold: 20h/week)
- **US-3.5**: As an operator, I want automatic determination of mandatory health surveillance

### Stress Lavoro-Correlato (Work Stress)
- **US-3.6**: As an operator, I want a digital checklist with ~50 INAIL indicators (SI/NO) across 3 areas (A, B, C)
- **US-3.7**: As an operator, I want real-time score calculation and automatic risk level (Low/Medium/High)
- **US-3.8**: As an operator, I want auto-generated corrective measures based on risk level

### Gestanti (Pregnant Workers)
- **US-3.9**: As an operator, I want automatic cross-reference between female worker roles and D.Lgs. 151/2001 risk factors
- **US-3.10**: As an operator, I want auto-identification of incompatible tasks and relocation proposals

### Rischio Incendio (Fire Risk)
- **US-3.11**: As an operator, I want to input INF/SI/PI scores (1-3 each) per homogeneous area
- **US-3.12**: As an operator, I want automatic risk level calculation (Low/Medium/High) and required fire safety measures

### Microclima (Thermal Comfort)
- **US-3.13**: As an operator, I want to input 6 environmental parameters and get automatic PMV/PPD calculation per environment
- **US-3.14**: For severe heat environments, I want PHS calculation with maximum exposure time (Dlim)

### Rischio Biologico (Biological Risk)
- **US-3.15**: As an operator, I want to select the sector type (nursery, food, dental, etc.) and get auto-populated biological agents and prevention measures

---

## Epic 4: Complementary Documents

### PEE (Emergency Plan)
- **US-4.1**: As an operator, I want the PEE auto-generated from DVR data (environments, emergency teams, assembly points)
- **US-4.2**: As an operator, I want standard emergency procedures (A-E) for each event type pre-filled

### HACCP
- **US-4.3**: As an operator, I want the HACCP manual auto-generated based on food activity type with customized CCP analysis
- **US-4.4**: As an operator, I want all 16 self-check forms (SA-01 to SA-16) generated as fillable templates

### DUVRI (Contractor Interference)
- **US-4.5**: As an operator, I want principal company data auto-filled from the DVR and contractor data entered separately
- **US-4.6**: As an operator, I want interference analysis per equipment type with suggested prevention measures

### POS (Construction Site Plan)
- **US-4.7**: As an operator, I want to define construction phases with specific risks, NIOSH calculations, and noise/vibration levels per phase
- **US-4.8**: As an operator, I want a detailed job description matrix with DPI per role per phase

---

## Epic 5: Cross-cutting

- **US-5.1**: As an admin, I want to manage multiple client companies and their document packages
- **US-5.2**: As any user, I want all documents generated from the same shared data (enter once, use everywhere)
- **US-5.3**: As an operator, I want AI-generated content clearly marked so I know what to review carefully
- **US-5.4**: As an admin, I want secure cloud hosting with daily backups (replacing the USB stick)

---

*© 2026 Niuexa. Confidential — prepared for N2O SRL.*
