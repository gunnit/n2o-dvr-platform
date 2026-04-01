> **NIUEXA** | AI-Powered Business Automation  
> *N2O DVR Automation Platform — Project Documentation*  
> Version 1.0 | April 2026 | Gregor Maric  
> Confidential — Niuexa & N2O SRL

---

# Data Model

## Entity Overview

```
Azienda (1) ─────┬──── Persona (N)          ──── MMC_Valutazione (per worker)
                  │                               VDT_Valutazione (per worker)
                  ├──── Ambiente (N)          ──── ValutazioneRischio (per env)
                  │                               Incendio_Valutazione (per env)
                  │                               Microclima_Valutazione (per env)
                  ├──── Attrezzatura (N)
                  ├──── SostanzaChimica (N)
                  └──── Stress_Valutazione (per gruppo omogeneo)
```

---

## Azienda (Company - Master Entity)

Used in: **ALL 16 documents**

| Field | Type | Example | Used In | Notes |
|-------|------|---------|---------|-------|
| ragione_sociale | Text | N2O SRL | ALL | Enter once, propagate everywhere |
| sede_legale_via | Text | VIA DEI CHIOSI 4 | ALL | |
| sede_legale_citta | Text | GORGONZOLA (MI) | ALL | |
| sede_operativa_via | Text | VIA MONZA 107/30 | ALL | |
| sede_operativa_citta | Text | GESSATE (MI) | ALL | |
| attivita | Text | Commercio all'ingrosso articoli antincendio | DVR, MMC, VDT, Stress, Incendio | |
| codice_ateco | Text | 46.69.94 | DVR, Microclima | |
| datore_lavoro | FK -> Persona | CIARAMITARO AMALIA | ALL (except HACCP) | |
| orario_lavoro | Text | Lun-Ven 08:30-13:00 / 14:00-19:00 | DVR, PEE | |
| metratura_totale | Number | 1000 | DVR, Incendio | |
| zona_sismica | Enum (1-4) | ZONA SISMICA 3 | DVR, MMC, VDT | |
| descrizione_attivita | Long text | N2O specializza in sicurezza... | DVR, MMC, VDT | **AI-generatable** (site + visura) |
| contesto_territoriale | Long text | ... | DVR | **AI-generatable** (Maps + regulations) |

---

## Persona (People - Employees & Safety Figures)

Used in: **ALL documents**

| Field | Type | Example | Used In | Privacy |
|-------|------|---------|---------|---------|
| nominativo | Text | MARCHETTI LUCA | ALL | |
| codice_fiscale | Text (16 chars) | MRCLCU93S03M052M | DVR, MMC, VDT, Stress | **NEVER send to AI** |
| mansione | Text | IMPIEGATO-DOCENTE FORMATORE | ALL | Determines specific risks |
| tipologia_contrattuale | Enum | IMPIEGATO / OPERAIO / DdL / COLLABORATORE | DVR, MMC, VDT, POS | |
| sesso | Enum (M/F) | M | MMC (for CP), Gestanti | M: CP=25kg, F: CP=15kg |
| fascia_eta | Enum | >18 / 15-18 | MMC (for CP) | Changes NIOSH weight constant |
| ruolo_rspp | Boolean | SI/NO | DVR, MMC, VDT, Stress, Incendio, PEE, DUVRI, POS | |
| ruolo_rls | Boolean | SI/NO | Same as RSPP | |
| ruolo_primo_soccorso | Boolean | SI/NO | DVR, Incendio, PEE, POS | |
| ruolo_antincendio | Boolean | SI/NO | DVR, Incendio, PEE, POS | |
| ruolo_preposto | Boolean | SI/NO | DVR, POS | Per environment |

---

## Ambiente (Work Environment)

Used in: DVR, Incendio, PEE, Microclima

| Field | Type | Example | Used In | Notes |
|-------|------|---------|---------|-------|
| nome | Text | UFFICIO AMMINISTRATIVO | DVR, Incendio, PEE, Microclima | |
| tipo | Enum | Ufficio / Magazzino / Sala Corsi / Esterno | DVR, Incendio | Determines preset risks |
| superficie_mq | Number | 50 | Incendio, Microclima | |
| preposto | FK -> Persona | MARCHETTI LUCA | DVR | |
| descrizione_attivita | Text | AMMINISTRAZIONE | DVR | |
| classe_rischio_incendio | Enum (1/2/3) | 2 | PEE, Incendio | From fire assessment |

---

## ValutazioneRischio (Risk Assessment - per Environment)

Used in: DVR, POS

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| ambiente_id | FK -> Ambiente | | |
| categoria_rischio | Enum | Strutture / Macchine / Elettrici / Incendio / Chimici / Fisici / Biologici / Cancerogeni / Organizzazione / Psicologici / Ergonomici | 11 categories, SI/NO per env |
| applicabile | Boolean | SI/NO | Matrix: 11 flags per environment |
| pericolo | Text | Presenza di ingombri ad altezza d'uomo | From standard risk library |
| condizioni_esposizione | Text | Durante la normale circolazione | From standard library |
| rischio | Text | Infortuni al capo | From standard library |
| misure_prevenzione | Long text | Segnalazione ingombri con nastro... | Customizable + AI suggestions |
| probabilita_P | Int (1-4) | 2 | 1=Low, 2=Med-Low, 3=Med-High, 4=High |
| danno_D | Int (1-4) | 2 | 1=Negligible, 2=Modest, 3=Notable, 4=Severe |
| indice_I | Int (3-12) | 6 | **Calculated: I = 2*D + P** |
| livello_rischio | Enum | ACCETTABILE / MODESTO / GRAVE / GRAVISSIMO | 3-4=Acc, 5-6=Mod, 7-8=Grave, 9-12=Grav |

---

## Attrezzatura (Equipment)

Used in: DVR, DUVRI, POS

| Field | Type | Example |
|-------|------|---------|
| descrizione | Text | FURGONE MOD.JUMPY TARGA FZ909GN |
| marcatura_ce | Boolean | SI/NO |
| verifiche_periodiche | Boolean | SI/NO |

---

## SostanzaChimica (Chemical Substance)

Used in: DVR. **All fields AI-extractable from SDS PDFs.**

| Field | Type | Example |
|-------|------|---------|
| nome_prodotto | Text | WD-40 LUBRIFICANTE AL SILICONE |
| produttore | Text | LUBRIFICANTI 4WD ITALIA |
| attivita_uso | Long text | PRODOTTO MULTIFUNZIONE... |
| pittogrammi | List | GHS02, GHS07 |
| stato_miscela | Enum | Liquido / Solido / Gas |

---

## Assessment-Specific Entities

### MMC_Valutazione (per Worker)

| Field | Type | Notes |
|-------|------|-------|
| persona_id | FK -> Persona | |
| cp_kg | Number | M>18=25, F>18=15 |
| altezza_cm | Number | Factor A |
| spostamento_cm | Number | Factor B |
| distanza_orizzontale_cm | Number | Factor C |
| angolo_asimmetria_gradi | Number | Factor D |
| qualita_presa | Enum (Buona/Sufficiente/Scarsa) | Factor E (1.0/0.95/0.9) |
| frequenza_azioni_min | Number | Factor F (lookup table) |
| durata_min | Number | For F lookup |
| peso_reale_kg | Number | P in IR calculation |
| **plr_calcolato** | Calc | PLR = CP x A x B x C x D x E x F |
| **ir_calcolato** | Calc | IR = P / PLR |
| **area_rischio** | Calc | <=0.75=Green, 0.75-1=Yellow, >1=Red |

### VDT_Valutazione (per Worker)

| Field | Type | Notes |
|-------|------|-------|
| persona_id | FK -> Persona | |
| postazione_vdt | Text | PC AMMINISTRAZIONE |
| attivita | Text | AMMINISTRAZIONE |
| ore_settimana | Number | 35 |
| **esposto** | Calc Boolean | >= 20 hours = Exposed |

### Stress_Valutazione (per Homogeneous Group)

| Field | Type | Notes |
|-------|------|-------|
| gruppo_omogeneo | Text | DIPENDENTI |
| area_a_punteggio | Calc Int | 10 company indicators (0/1/4 each) |
| area_b_punteggio | Calc Int | 30 context indicators (SI=0/NO=1) |
| area_c_punteggio | Calc Int | 36 content indicators (SI=0/NO=1) |
| **punteggio_totale** | Calc Int | Sum A+B+C |
| **livello_rischio** | Calc Enum | 0-17=LOW, 18-34=MEDIUM, >=35=HIGH |

### Incendio_Valutazione (per Area)

| Field | Type | Notes |
|-------|------|-------|
| ambiente_id | FK -> Ambiente | |
| inf_score | Int (1-3) | Flammability |
| si_score | Int (1-3) | Fire development |
| pi_score | Int (1-3) | Propagation |
| **livello_rischio** | Calc Enum | Sum 3-4=Low, 5-7=Medium, 8-9=High |

### Microclima_Valutazione (per Environment)

| Field | Type | Notes |
|-------|------|-------|
| ambiente_id | FK -> Ambiente | |
| ta_celsius | Number | Air temperature |
| tr_celsius | Number | Mean radiant temperature |
| va_ms | Number | Air velocity |
| ur_percent | Number | Relative humidity |
| m_met | Number | Metabolic rate |
| icl_clo | Number | Clothing insulation |
| **pmv_calcolato** | Calc Number | PMV (ISO 7730) |
| **ppd_calcolato** | Calc Number | PPD (ISO 7730) |
| **giudizio** | Calc Enum | From PMV scale |

---

*© 2026 Niuexa. Confidential — prepared for N2O SRL.*
