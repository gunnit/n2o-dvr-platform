> **NIUEXA** | AI-Powered Business Automation  
> *N2O DVR Automation Platform — Project Documentation*  
> Version 1.0 | April 2026 | Gregor Maric  
> Confidential — Niuexa & N2O SRL

---

# Automation Plan

## Phase 2: Core Development

### Module 1: Scheda di Rilevazione Digitale
- **Description**: Web form for tablet/smartphone replacing paper survey. Structured fields, dynamic checklists by environment type, photo upload, digital countersignature
- **Operator Input**: Company data, safety figures, environments, equipment (checklists), employees with roles, risks (contextualized list), photos, PPE
- **Generated Output**: Structured JSON with all data for DVR + attachment generation
- **Method**: Dynamic form - equipment checklists change based on environment type (office, warehouse, kitchen). Risk list filtered by context
- **Time Savings**: ~85% (from 30-45 min to 5 min for company description)
- **Complexity**: MEDIUM-HIGH

### Module 2: DVR Master Generation Engine
- **Description**: From survey data, generates complete .docx with all 4 parts, risk tables per environment, equipment/chemical lists, PPE per worker
- **Operator Input**: Survey data + P/D scores per risk
- **Generated Output**: Professional .docx (~187 pages) with cover, TOC, formatted tables, signatures
- **Method**: Template .docx with placeholders. AI for company description and improvement measures. Formula I=2*D+P for risk indices
- **Time Savings**: ~70% overall (60-90% per section)
- **Complexity**: HIGH

### Module 3: AI Chemical SDS Extraction
- **Description**: Batch upload chemical safety data sheet PDFs. AI extracts key data into human-review table
- **Operator Input**: Upload up to 20 PDFs at a time
- **Generated Output**: Table: Product name, Manufacturer, Pictograms, Mixture state, H/P phrases. Human review before insertion
- **Method**: OpenAI/Claude for structured data extraction from PDF. OCR if needed
- **Time Savings**: ~90% (from 3-4 days to 2-4 hours for 600 sheets)
- **Complexity**: MEDIUM

---

## Phase 3: DVR Attachments

### Module 4: MMC (NIOSH)
- **Input**: Per worker: height, displacement, distance, angle, grip, frequency, duration, actual weight
- **Output**: Assessment table per worker + summary + Green/Yellow/Red classification
- **Method**: PLR = CP x A x B x C x D x E x F. IR = P/PLR. Lookup table for Factor F. CP from sex/age
- **Savings**: ~70% | **Complexity**: MEDIUM

### Module 5: VDT
- **Input**: Per worker: VDT workstation, hours/week
- **Output**: Table per worker + summary + health surveillance obligation
- **Method**: Threshold: >= 20h/week = Exposed
- **Savings**: ~60% | **Complexity**: LOW

### Module 6: Stress Lavoro-Correlato
- **Input**: ~50 SI/NO responses for organizational indicators
- **Output**: Score per area, LOW/MEDIUM/HIGH classification, Phase 3 necessity, improvement plan
- **Method**: Sum indicators per area. Thresholds: A(0-10/11-20/21-40), B(0-8/9-17/18-26), C(0-13/14-25/26-36). Total: 0-17/18-34/>=35
- **Savings**: ~60% | **Complexity**: MEDIUM

### Module 7: Gestanti
- **Input**: Female employee roles (already in system), DVR risk assessments
- **Output**: Document with risk mapping, effects on pregnancy, provisions. Acknowledgment form per worker
- **Method**: Qualitative mapping: role -> DVR risks -> comparison with Annexes A/B/C of D.Lgs. 151/2001
- **Savings**: ~50% | **Complexity**: LOW

### Module 8: Rischio Incendio
- **Input**: Per area: activity type, materials, construction, dimensions, occupancy, ignition sources + INF/SI/PI scores
- **Output**: Sheets per area + summary table + prevention measures
- **Method**: INF+SI+PI (1-3 each). Sum: 3-4=Low, 5-7=Medium, 8-9=High
- **Savings**: ~60% | **Complexity**: MEDIUM

### Module 9: Microclima (Moderate)
- **Input**: Per environment: Ta, Tr, Va, Ur + per worker group: M(met), Icl(clo)
- **Output**: Table with PMV, PPD, To, thermal judgment per environment. Corrective measures
- **Method**: PMV/PPD formula from UNI EN ISO 7730. Open source implementations available
- **Savings**: ~60% | **Complexity**: MEDIUM

### Module 10: Microclima Caldo Severo
- **Input**: Environmental parameters + activity (metabolism, walking speed, clothing, acclimatization)
- **Output**: Maximum exposure time (Dlim) per role, based on 3 criteria
- **Method**: PHS method (UNI EN ISO 7933). Thermal balance equation. pythermalcomfort library
- **Savings**: ~50% | **Complexity**: HIGH

### Module 11: Rischio Biologico
- **Input**: Environment/sector type selection (nursery, food, dental, hospital, etc.)
- **Output**: Document with relevant biological agents, pathologies, prevention measures
- **Method**: Sector-specific biological agent database. Mapping: sector -> agents -> pathologies -> prevention
- **Savings**: ~65% | **Complexity**: MEDIUM

---

## Phase 4: Complementary Documents

### Module 12: PEE (Piano Emergenze)
- **Input**: Emergency teams (already in system), assembly point, escape routes per environment
- **Output**: Complete PEE (~28 pages) with A-E procedures, first aid, emergency numbers
- **Method**: 80% boilerplate. Dynamic insertion: company data, environments with fire risk class, teams, assembly point
- **Savings**: ~80% | **Complexity**: LOW-MEDIUM

### Module 13: HACCP Manuale
- **Input**: Company data, food activity type, specific equipment, cleaning products, custom CCPs
- **Output**: Complete manual (~90 pages) + 16 self-check forms
- **Method**: 85% boilerplate. AI for specific CCP analysis. SOP templates per restaurant type
- **Savings**: ~85% | **Complexity**: MEDIUM

### Module 14: DUVRI
- **Input**: Principal data (from DVR) + contractor data + contract scope + equipment lists + schedule
- **Output**: Complete DUVRI (~45 pages) with interference analysis per equipment, safety costs
- **Method**: 60% boilerplate. Interference analysis requires specific input. AI for measure suggestions possible
- **Savings**: ~60% | **Complexity**: HIGH

### Module 15: POS (Piano Operativo Sicurezza)
- **Input**: Site data, work phases (descriptions), NIOSH parameters per phase, noise/vibration levels, equipment per phase
- **Output**: Complete POS (~110 pages) with job descriptions, risks per phase, PPE per phase, NIOSH calculations
- **Method**: 50% boilerplate. Formula I=2*D+P for risks. NIOSH for MMC. Noise/vibration tables
- **Savings**: ~50% | **Complexity**: VERY HIGH

---

## Summary

| Phase | Modules | Total Savings Range | Complexity Range |
|-------|---------|-------------------|------------------|
| 2 - Core | Survey, DVR Master, SDS AI | 70-90% | MED to HIGH |
| 3 - Attachments | MMC, VDT, Stress, Gestanti, Incendio, Microclima, Microclima Caldo Severo, Biologico | 50-70% | LOW to HIGH |
| 4 - Complementary | PEE, HACCP, DUVRI, POS | 50-85% | LOW-MED to VERY HIGH |

---

*© 2026 Niuexa. Confidential — prepared for N2O SRL.*
