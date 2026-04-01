> **NIUEXA** | AI-Powered Business Automation  
> *N2O DVR Automation Platform — Project Documentation*  
> Version 1.0 | April 2026 | Gregor Maric  
> Confidential — Niuexa & N2O SRL

---

# Document Catalog

## Overview

The system generates **16 distinct documents** across **13 document types** (biological risk has 3 sector variants; emergency plan has 2 variants). All share a common data layer. The DVR Master is the source of truth; all other documents pull from the same entities.

---

## Main Documents

| # | Document | Type | Phase | Pages | Tables | Boilerplate | Dynamic | Complexity | Data Shared with DVR |
|---|----------|------|-------|-------|--------|-------------|---------|------------|---------------------|
| 1 | DVR Rischio Master | Master Document | 2 | ~187 | 111 | 60% | 40% | HIGH | Source of all data |
| | **DVR ATTACHMENTS** | | | | | | | | |
| 2 | Allegato Rischio MMC | DVR Attachment | 3 | ~35 | 29 | 55% | 45% | MED-HIGH | Anagrafica, Dipendenti, Ambienti, Org. Sicurezza |
| 3 | Allegato Rischio VDT | DVR Attachment | 3 | ~40 | 21 | 65% | 35% | LOW | Anagrafica, Dipendenti, Ambienti, Org. Sicurezza |
| 4 | Allegato Stress Lavoro-Correlato | DVR Attachment | 3 | ~30 | 47 | 50% | 50% | MED-HIGH | Anagrafica, Dipendenti, Org. Sicurezza |
| 5 | Allegato Gestanti | DVR Attachment | 3 | ~12 | 5 | 70% | 30% | LOW | Anagrafica, Mansioni dipendenti |
| 6 | Allegato Rischio Incendio | DVR Attachment | 3 | ~15 | 28 | 55% | 45% | MED | Anagrafica, Dipendenti, Ambienti, Org. Sicurezza |
| 7 | Allegato Microclima | DVR Attachment | 3 | ~10 | 5 | 60% | 40% | MED | Anagrafica, SPP |
| 8 | Allegato Microclima Caldo Severo | DVR Attachment | 3 | ~8 | 5 | 50% | 50% | HIGH | Org. Sicurezza (firme) |
| 9 | Allegato Rischio Biologico (Asilo) | DVR Attachment | 3 | ~17 | 6 | 65% | 35% | MED | Anagrafica |
| 10 | Allegato Rischio Biologico (Alimentare) | DVR Attachment | 3 | ~65 | N/A | 80% | 20% | MED | Anagrafica |
| 11 | Allegato Rischio Biologico (Dentisti) | DVR Attachment | 3 | ~84 | N/A | 75% | 25% | MED | Anagrafica |
| | **COMPLEMENTARY DOCUMENTS** | | | | | | | | |
| 12 | Piano Gestione Emergenze (Azienda) | Complementary | 4 | ~28 | 15 | 80% | 20% | LOW-MED | Anagrafica, Dipendenti, Ambienti, Org. Sicurezza, Squadre |
| 13 | Piano Gestione Emergenze (Comune/Evento) | Complementary | 4 | ~40 | 10 | 65% | 35% | MED | Adapted (volunteers instead of employees) |
| 14 | HACCP Manuale Autocontrollo | Complementary | 4 | ~90 | 20 | 85% | 15% | MED-HIGH | Ragione Sociale, Sede, Rappresentante Legale |
| 15 | DUVRI | Complementary | 4 | ~45 | 19 | 60% | 40% | HIGH | Anagrafica Committente, Dipendenti, Org. Sicurezza |
| 16 | POS | Complementary | 4 | ~110 | 81 | 50% | 50% | VERY HIGH | Anagrafica, Dipendenti, Org. Sicurezza, Risk Factors |

## Key Notes per Document

### 1. DVR Rischio Master
- Heart of the system. 4 parts: Presentazione, Metodologia, Valutazione Rischi per Ambiente, Procedure Miglioramento
- Formula: I = 2*D + P (NOT P x D)
- 11 risk categories per environment (SI/NO matrix)

### 2. Allegato MMC
- NIOSH method. Calculates PLR per worker. IR = P/PLR
- Classification: Green (<=0.75) / Yellow (0.75-1.0) / Red (>1.0)
- CP depends on sex/age: M>18=25kg, F>18=15kg

### 3. Allegato VDT
- Simple threshold: >= 20 hours/week = Exposed
- Per worker + VDT workstation assessment

### 4. Allegato Stress Lavoro-Correlato
- INAIL checklist method, 3 phases
- 3 areas (A, B, C) with ~50 SI/NO indicators
- Automatic score calculation: 0-17=Low, 18-34=Medium, >=35=High

### 5. Allegato Gestanti
- Qualitative. Maps risks vs D.Lgs. 151/2001
- Requires acknowledgment signature from each female worker

### 6. Allegato Rischio Incendio
- Method: INF+SI+PI (1-3 each). Sum 3-9 determines level
- Per homogeneous area. Low (3-4) / Medium (5-7) / High (8-9)

### 7-8. Allegato Microclima
- Moderate: PMV/PPD method (UNI EN ISO 7730). 6 parameters
- Severe heat: PHS method (UNI EN ISO 7933). Complex thermal balance. Dlim calculation

### 9-11. Allegato Rischio Biologico
- Sector-specific knowledge base (nursery, food/meat, dental)
- Maps biological agents -> pathologies -> prevention
- Dental variant includes HBV/HCV/HIV protocols (84 pages)
- Food/meat variant is Lombardy region specific, legacy .doc format

### 12-13. Piano Gestione Emergenze (PEE)
- Standard procedures A-E per emergency type
- Azienda version: employees, detailed first aid
- Comune version: for public events, volunteers, RCP procedures

### 14. HACCP Manuale Autocontrollo
- Longest document (~90 pages). 25+ SOP sections
- Blast chiller procedures for 8 food types. CCP analysis
- Almost entirely boilerplate (85%)

### 15. DUVRI
- Dual company registration (principal + contractor)
- Interference analysis per equipment. Schedule. Safety costs
- 40% dynamic content

### 16. POS
- Most complex document. Per construction site
- 8 work phases with dedicated risks. NIOSH per phase
- Noise/vibration. Detailed job descriptions
- 50% dynamic, 81 tables

---

## HACCP Self-Check Forms (16 modules)

| # | Form Name | Code | Frequency | Type | Notes |
|---|-----------|------|-----------|------|-------|
| 1 | Controllo Temperature | SA-01 | Daily | Monthly grid | C=compliant. IoT sensor integration possible |
| 2 | Registro Sanificazione | SA-02 | Daily | Daily log | Original is .xlsx |
| 3 | Controllo Prodotti Detergenti | SA-03 | One-time | Registry | Updated when products change |
| 4 | Elenco Fornitori Qualificati | SA-04 | Quarterly | Registry | Updated with new suppliers |
| 5 | Elenco Ordini di Acquisto | SA-05 | Per delivery | Log | Lot traceability. Expiry alerts possible |
| 6 | Elenco Personale Addetto | SA-06 | Per hire/exit | Registry | Linkable to DVR Persona table |
| 7 | Monitoraggio Disinfestazione | SA-07 | Monthly/quarterly | Log | Coordination with pest control |
| 8 | Prove Funzionalita Impianti | SA-08 | Monthly | Log | Scheduled maintenance |
| 9 | Scheda Abbattitore HACCP | SA-09 | Per use | Detailed log | Positive/negative cycles. Time limits from HACCP manual |
| 10 | Scheda Apertura Confezione | SA-10 | Per opening | Log | Post-opening shelf-life management |
| 11 | Scheda Non Conformita Attrezzature | SA-11 | Per event | NC registry | Linkable to equipment list |
| 12 | Scheda Prodotti Congelati | SA-12 | Per delivery | Receipt log | Cold chain control |
| 13 | Scheda Prodotti Freschi poi Congelati | SA-13 | Per freezing | Log | Tracks in-house freezing date |
| 14 | Schede Materie Prime Non Conformi | SA-14 | Per event | Single report | Template with free fields |
| 15 | Sostanze Allergeniche (Avviso) | SA-15 | Never (poster) | Poster | 100% boilerplate except company name. 14 allergens per EU Reg. 1169/2011 |
| 16 | Procedura Sottovuoto | SA-16 | Per batch | Checklist | 7 specific vacuum checks |

Total HACCP forms: ~25 pages combined, 32 tables, 90% boilerplate, LOW complexity.

---

*© 2026 Niuexa. Confidential — prepared for N2O SRL.*
