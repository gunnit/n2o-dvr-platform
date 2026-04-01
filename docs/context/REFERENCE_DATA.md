> **NIUEXA** | AI-Powered Business Automation  
> *N2O DVR Automation Platform — Reference Data*  
> Version 1.0 | April 2026 | Gregor Maric  
> Confidential — Niuexa & N2O SRL

---

# Reference Data — Lookup Tables, Risk Libraries & Indicator Lists

All data in this document was extracted directly from N2O's completed template documents (`.docx` files in `templates/`). This data will be seeded into the database as the foundation for the digital survey form and document generation engine.

**Source documents:**
- `ALLEGATO RISCHIO MMC.docx` — NIOSH manual handling assessment
- `DVR RISCHIO MASTER.docx` — Master risk assessment document
- `ALLEGATO STRESS DA LAVORO CORRELATO.docx` — INAIL stress indicators
- `ALLEGATO RISCHIO INCENDIO.docx` — Fire risk assessment
- `ALLEGATO RISCHIO VDT.docx` — Display screen equipment assessment

**Unparseable files (PDF or .doc format, skipped):**
- `ALLEGATO MICROCLIMA CALDO SEVERO.pdf`
- `ALLEGATO MICROCLIMA.pdf`
- `ALLEGATO RISCHIO BIOLOGICO ALIMENTARE.doc` (.doc binary format)
- `RISCHIO BIOLOGICO - ASILO.pdf`
- `RISCHIO BIOLOGICO - DENTISTI.doc` (.doc binary format)

---

## 1. NIOSH Lookup Tables (MMC — Movimentazione Manuale Carichi)

**Formula**: `PLR = CP x A x B x C x D x E x F`  
**Risk Index**: `IR = P / PLR` (P = actual weight lifted)

### 1.1 CP — Costante di Peso (Weight Constant)

| Eta / Age | Maschi / Males (kg) | Femmine / Females (kg) |
|-----------|--------------------|-----------------------|
| > 18 anni | 25 | 20 |
| 15–18 anni | 15 | 10 |

### 1.2 Factor A — Fattore Altezza (Height Multiplier)

**Description**: Altezza da terra delle mani all'inizio del sollevamento (height of hands from floor at start of lift)  
**Formula**: `A = 1 - (0.003 * |V - 75|)` where V = height of hands from floor (cm)  
**Optimal**: V = 75 cm (knuckle height), A = 1.00

| Altezza (cm) | Fattore A |
|-------------|-----------|
| 0 | 0.78 |
| 25 | 0.85 |
| 50 | 0.93 |
| 75 | **1.00** |
| 100 | 0.93 |
| 125 | 0.85 |
| 150 | 0.78 |
| >175 | **0.00** |

### 1.3 Factor B — Fattore Dislocazione Verticale (Vertical Displacement)

**Description**: Dislocazione verticale del peso fra inizio e fine del sollevamento (vertical displacement of load)  
**Formula**: `B = 0.82 + (4.5 / X)` where X = vertical displacement (cm)

| Dislocazione (cm) | Fattore B |
|-------------------|-----------|
| 25 | **1.00** |
| 30 | 0.97 |
| 40 | 0.93 |
| 50 | 0.91 |
| 70 | 0.88 |
| 100 | 0.87 |
| 170 | 0.85 |
| >175 | **0.00** |

### 1.4 Factor C — Fattore Orizzontale (Horizontal Distance)

**Description**: Distanza orizzontale tra le mani e il punto di mezzo delle caviglie (horizontal distance from body to load center)  
**Formula**: `C = 25 / H` where H = horizontal distance (cm)

| Distanza (cm) | Fattore C |
|---------------|-----------|
| 25 | **1.00** |
| 30 | 0.83 |
| 40 | 0.63 |
| 50 | 0.50 |
| 55 | 0.45 |
| 60 | 0.42 |
| >63 | **0.00** |

### 1.5 Factor D — Fattore Dislocazione Angolare (Asymmetry)

**Description**: Angolo di asimmetria del peso in gradi (angle of asymmetry of load)  
**Formula**: `D = 1 - (0.0032 * y)` where y = angle of asymmetry (degrees)

| Angolo (gradi) | Fattore D |
|-----------------|-----------|
| 0° | **1.00** |
| 30° | 0.90 |
| 60° | 0.81 |
| 90° | 0.71 |
| 120° | 0.62 |
| 135° | 0.57 |
| >135° | **0.00** |

### 1.6 Factor E — Fattore Presa (Grip Quality)

**Description**: Giudizio sulla presa del carico (grip quality judgment)

| Giudizio / Judgment | Fattore E |
|---------------------|-----------|
| Buono / Good | **1.00** |
| Discreto / Fair | 0.95 |
| Scarso / Poor | 0.90 |

**Grip quality criteria:**
- **Buono**: Handles 2–4 cm diameter, 11.5 cm length, cylindrical/elliptical, non-slip surface; or optimal box dimensions
- **Scarso**: Extreme upper limb positions or excessive grip force required

### 1.7 Factor F — Fattore Frequenza (Frequency)

**Description**: Frequenza dei gesti (n. atti al minuto) in relazione alla durata del lavoro  
**Full lookup table (18 rows):**

| Frequenza (azioni/min) | Breve durata / <1 ora | Media durata / 1–2 ore | Lunga durata / 2–8 ore |
|------------------------|----------------------|----------------------|----------------------|
| 0.2 | 1.00 | 0.95 | 0.85 |
| 0.5 | 0.97 | 0.92 | 0.81 |
| 1 | 0.94 | 0.88 | 0.75 |
| 2 | 0.91 | 0.84 | 0.65 |
| 3 | 0.88 | 0.79 | 0.55 |
| 4 | 0.84 | 0.72 | 0.45 |
| 5 | 0.80 | 0.60 | 0.35 |
| 6 | 0.75 | 0.50 | 0.27 |
| 7 | 0.70 | 0.42 | 0.22 |
| 8 | 0.60 | 0.35 | 0.18 |
| 9 | 0.52 | 0.30 | 0.15 |
| 10 | 0.45 | 0.26 | 0.13 |
| 11 | 0.41 | 0.23 | 0.00 |
| 12 | 0.37 | 0.21 | 0.00 |
| 13 | 0.34 | 0.00 | 0.00 |
| 14 | 0.31 | 0.00 | 0.00 |
| 15 | 0.28 | 0.00 | 0.00 |
| >15 | 0.00 | 0.00 | 0.00 |

**Duration categories:**
- **Breve durata (<1 ora)**: Lifting task <= 1 hour, followed by recovery period >= 1.2x the lifting duration. For occasional lifts (< 1 per 10 min), always use short duration, F = 1.
- **Media durata (1–2 ore)**: Lifting task 1–2 hours, followed by recovery period >= 0.3x the lifting duration.
- **Lunga durata (2–8 ore)**: Lifting task 2–8 hours with normal work breaks.

### 1.8 NIOSH Risk Index Classification

| IR Range | Zona / Zone | Descrizione / Description | Azione / Action |
|----------|-------------|--------------------------|-----------------|
| IR <= 0.75 | Verde / Green | Situazione accettabile | Nessun intervento specifico richiesto |
| 0.75 < IR <= 1.0 | Gialla / Yellow | Situazione si avvicina ai limiti; 1–10% della popolazione potrebbe essere a rischio | Attivare sorveglianza sanitaria, formazione specifica, interventi strutturali |
| IR > 1.0 | Rossa / Red | Rischio per quote crescenti di popolazione | Intervento di prevenzione primaria: riprogettazione postazioni, riduzione carichi, ausili meccanici |

**Additional NIOSH correction factors:**
- Sollevamento con un solo arto (single-arm lift): apply factor = 0.6
- Sollevamento da 2 persone (two-person lift): apply factor = 0.85 (consider actual weight / 2)

---

## 2. Risk Categories & Standard Library (DVR Master)

### 2.1 Risk Index Formula

**Formula**: `I = P + 2*D` (NOT P x D)  
**Range**: 3–12

> **Note**: This deviates from the common P x D formula. The DVR Master uses `I = P + 2*D`, giving heavier weight to the severity of damage (D).

### 2.2 Risk Level Classification (Classificazione dei Rischi)

| Indice I | Livello di Rischio | Azione da Intraprendere | Tempistica |
|----------|-------------------|------------------------|------------|
| I = 3–4 | **ACCETTABILE** | Instaurare un sistema di verifica che consenta di mantenere nel tempo le condizioni di sicurezza preventivate | Ongoing |
| I = 5–6 | **MODESTO** | Predisporre gli strumenti necessari a minimizzare il rischio ed a verificare la efficacia delle azioni preventivate | 1 anno |
| I = 7–8 | **GRAVE** | Sensibilizzazione del personale. Controllo attuazione misure di prevenzione. Ricerca di ulteriori misure tecnico-organizzative | 6 mesi |
| I = 9–12 | **GRAVISSIMO** | Sensibilizzazione del personale. Controllo attuazione misure. Ricerca urgente di ulteriori misure | Immediatamente |

### 2.3 Scala P — Probabilita (Probability Scale)

| P | Livello | Criteri |
|---|---------|---------|
| 4 | **ELEVATA** | Correlazione diretta tra mancanza e danno. Si sono gia verificati danni per la stessa mancanza. Il verificarsi del danno non susciterebbe alcuno stupore. |
| 3 | **MEDIO ALTA** | La mancanza puo provocare danno, non in modo automatico/diretto. Noto qualche episodio. Il danno susciterebbe moderata sorpresa. |
| 2 | **MEDIO BASSA** | La mancanza puo provocare danno solo in circostanze sfortunate. Noti solo rarissimi episodi. Il danno susciterebbe grande sorpresa. |
| 1 | **BASSA** | La mancanza puo provocare danno per concomitanza di piu eventi poco probabili indipendenti. Non sono noti episodi. Il danno susciterebbe incredulita. |

### 2.4 Scala D — Danno (Damage/Severity Scale)

| D | Livello | Criteri |
|---|---------|---------|
| 4 | **INGENTE** | Infortunio/esposizione con effetti letali o invalidita permanente. Esposizione cronica con effetti letali/totalmente invalidanti. |
| 3 | **NOTEVOLE** | Infortunio/esposizione con invalidita parziale. Esposizione cronica con effetti irreversibili/parzialmente invalidanti. |
| 2 | **MODESTA** | Infortunio/esposizione con inabilita reversibile. Esposizione cronica con effetti reversibili. |
| 1 | **TRASCURABILE** | Infortunio/esposizione con inabilita rapidamente reversibile. Esposizione cronica con effetti rapidamente reversibili. |

### 2.5 Risk Category Checklist (SI/NO per Ambiente)

The following 11 risk categories are evaluated per work environment, each marked SI or NO:

| # | Macro-Categoria | Categoria | field_key |
|---|----------------|-----------|-----------|
| 1 | Rischi per la Sicurezza | Strutture | `risk_structures` |
| 2 | Rischi per la Sicurezza | Macchine | `risk_machines` |
| 3 | Rischi per la Sicurezza | Impianti Elettrici | `risk_electrical` |
| 4 | Rischi per la Sicurezza | Incendio-Esplosioni | `risk_fire` |
| 5 | Rischi per la Salute | Agenti Chimici | `risk_chemical` |
| 6 | Rischi per la Salute | Agenti Fisici | `risk_physical` |
| 7 | Rischi per la Salute | Agenti Biologici | `risk_biological` |
| 8 | Rischi per la Salute | Agenti Cancerogeni | `risk_carcinogenic` |
| 9 | Rischi Trasversali | Organizzazione del Lavoro | `risk_work_org` |
| 10 | Rischi Trasversali | Fattori Psicologici | `risk_psychological` |
| 11 | Rischi Trasversali | Fattori Ergonomici | `risk_ergonomic` |

### 2.6 Standard Hazard Library (Fattori di Pericolo)

Each risk category has a standard set of specific hazards/items that are checked. These form the master checklist for the survey:

#### 2.6.1 Rischi per la Sicurezza — Strutture (13 items)

| # | Fattore di Pericolo |
|---|-------------------|
| 1 | Altezza dell'Ambiente |
| 2 | Superficie dell'Ambiente |
| 3 | Volume dell'Ambiente |
| 4 | Illuminazione (normale e in emergenza) |
| 5 | Pavimenti (lisci o sconnessi) |
| 6 | Pareti (semplici o attrezzate: scaffalatura, apparecchiatura) |
| 7 | Viabilita interna, esterna; movimentazione manuale dei carichi |
| 8 | Solai (stabilita) |
| 9 | Soppalchi (destinazione, praticabilita, tenuta, portata) |
| 10 | Botole (visibili e con chiusura a sicurezza) |
| 11 | Uscite (in numero sufficiente in funzione del personale) |
| 12 | Porte (in numero sufficiente in funzione del personale) |
| 13 | Locali sotterranei (dimensioni, ricambi d'aria) |

#### 2.6.2 Rischi per la Sicurezza — Macchine (10 items)

| # | Fattore di Pericolo |
|---|-------------------|
| 1 | Protezione degli organi di avviamento |
| 2 | Protezione degli organi di trasmissione |
| 3 | Protezione degli organi di lavoro |
| 4 | Protezione degli organi di comando |
| 5 | Macchine con marchio CE |
| 6 | Macchine rispondenti ai requisiti di sicurezza |
| 7 | Protezione nell'uso di apparecchi di sollevamento |
| 8 | Protezione nell'uso di ascensori e montacarchi |
| 9 | Protezione nell'uso di apparecchi a pressione (bombole e circuiti) |
| 10 | Protezione nell'accesso a vasche, serbatoi e simili |

#### 2.6.3 Rischi per la Sicurezza — Impianti Elettrici (4 items)

| # | Fattore di Pericolo |
|---|-------------------|
| 1 | Idoneita del progetto |
| 2 | Idoneita d'uso |
| 3 | Impianti a sicurezza intrinseca in atmosfere a rischio di incendio o di esplosione |
| 4 | Impianti speciali a carattere di ridondanza |

#### 2.6.4 Rischi per la Sicurezza — Incendio-Esplosioni (5 items)

| # | Fattore di Pericolo |
|---|-------------------|
| 1 | Presenza di materiali infiammabili d'uso |
| 2 | Presenza di armadi di conservazione (caratteristiche strutturali e di aerazione) |
| 3 | Presenza di depositi di materiali infiammabili (caratteristiche strutturali e di ricambi d'aria) |
| 4 | Carenza di sistemi antincendio |
| 5 | Carenza di segnaletica di sicurezza |

#### 2.6.5 Rischi per la Salute — Agenti Chimici (1 item)

| # | Fattore di Pericolo |
|---|-------------------|
| 1 | Rischi di esposizione connessi con l'impiego di sostanze chimiche, tossiche o nocive (ingestione, contatto cutaneo, inalazione — polveri, fumi, nebbie, gas, vapori) |

#### 2.6.6 Rischi per la Salute — Agenti Fisici (8 items)

| # | Fattore di Pericolo |
|---|-------------------|
| 1 | Rumore |
| 2 | Vibrazioni |
| 3 | Radiazioni non ionizzanti |
| 4 | Microclima (temperatura, umidita relativa, ventilazione, calore radiante, condizionamento) |
| 5 | Illuminazione (livelli di illuminamento ambientale e dei posti di lavoro) |
| 6 | VDT (posizionamento, illuminotecnica, postura, microclima) |
| 7 | Radiazioni ionizzanti |
| 8 | (reserved — not found in template) |

#### 2.6.7 Rischi per la Salute — Agenti Biologici (4 items)

| # | Fattore di Pericolo |
|---|-------------------|
| 1 | Emissione involontaria (impianto di condizionamento, polveri organiche) |
| 2 | Emissione involontaria (repeat entry in template — same category) |
| 3 | Emissione incontrollata (impianti depurazione acque, materiali infetti, rifiuti) |
| 4 | Trattamento o manipolazione volontaria (biotecnologie) |

#### 2.6.8 Rischi per la Salute — Agenti Cancerogeni (5 items)

| # | Fattore di Pericolo |
|---|-------------------|
| 1 | Materie prime nel ciclo produttivo |
| 2 | Materie ausiliarie nel ciclo produttivo |
| 3 | Trattamento o manipolazione volontaria nel ciclo produttivo |
| 4 | Emissione incontrollata da componenti strutturali (es. amianto) |
| 5 | Emissione incontrollata da componenti impiantistiche (es. PCB) |

#### 2.6.9 Rischi Trasversali — Organizzazione del Lavoro (6 items)

| # | Fattore di Pericolo |
|---|-------------------|
| 1 | Processi di lavoro usuranti: lavori in continuo, sistemi di turni, lavoro notturno |
| 2 | Pianificazione degli aspetti attinenti alla sicurezza e la salute |
| 3 | Manutenzione degli impianti, comprese le attrezzature di sicurezza |
| 4 | Procedure adeguate per far fronte a incidenti e situazioni di emergenza |
| 5 | Movimentazione manuale dei carichi |
| 6 | Lavoro ai VDT (Data Entry) |

#### 2.6.10 Rischi Trasversali — Fattori Psicologici (4 items)

| # | Fattore di Pericolo |
|---|-------------------|
| 1 | Intensita, monotonia, solitudine, ripetitivita del lavoro |
| 2 | Carenze di contributo al processo decisionale e situazioni di conflittualita |
| 3 | Complessita delle mansioni e carenza di controllo |
| 4 | Reattivita anomala a condizioni di emergenza |

#### 2.6.11 Rischi Trasversali — Fattori Ergonomici (4 items)

| # | Fattore di Pericolo |
|---|-------------------|
| 1 | Fattori Ergonomici (general) |
| 2 | Sistemi di sicurezza e affidabilita delle informazioni |
| 3 | Conoscenze e capacita del personale |
| 4 | Norme di comportamento |
| 5 | Soddisfacente comunicazione e istruzioni corrette in condizioni variabili |

### 2.7 Risk Assessment Table Structure (per Ambiente)

Each risk entry in the per-environment assessment tables has these columns:

| Column | field_key | Description |
|--------|-----------|-------------|
| PERICOLO | `hazard` | Specific hazard identified |
| CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE | `exposure_conditions` | When/how exposure occurs |
| RISCHIO | `risk_description` | Potential injury/health effect |
| MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E DPI ADOTTATI | `prevention_measures` | Current prevention measures and PPE |
| I = P + 2*D | `risk_index` | Risk index calculation result (format: "P = X; D = Y; I = Z; LEVEL") |

---

## 3. INAIL Stress Indicators (Stress Lavoro-Correlato)

**Method**: Metodo Indicatori Oggettivi (Objective Indicators Method per INAIL)  
**Three-phase process**: Phase 1 = checklist scoring, Phase 2 = risk level identification, Phase 3 = worker perception survey (only if HIGH)

### 3.1 Area A — Indicatori Aziendali (10 indicators)

**Scoring**: DIMINUITO=0, INALTERATO=1, AUMENTATO=4  
**Note**: Indicators marked (*) — if INALTERATO corresponds to 0 events, mark as DIMINUITO (0)

| # | Indicatore | Diminuito | Inalterato | Aumentato |
|---|-----------|-----------|------------|-----------|
| 1 | Indici infortunistici (*) | 0 | 1 | 4 |
| 2 | Assenteismo (% ore assenza / ore lavorative) | 0 | 1 | 4 |
| 3 | Assenza per malattia (escluso maternita, allattamento, congedo matrimoniale) | 0 | 1 | 4 |
| 4 | % Ferie non godute | 0 | 1 | 4 |
| 5 | % Rotazione del personale non programmata | 0 | 1 | 4 |
| 6 | Cessazione rapporti di lavoro / turnover (*) | 0 | 1 | 4 |
| 7 | Procedimenti / sanzioni disciplinari (*) | 0 | 1 | 4 |
| 8 | Richieste visite mediche straordinarie dal medico competente (*) | 0 | 1 | 4 |
| 9 | Segnalazioni scritte medico competente di condizioni stress al lavoro | No=0 | No=0 | Si=4 |
| 10 | Istanze giudiziarie per licenziamento / demansionamento | No=0 | No=0 | Si=4 |

**Max score**: 40

### 3.2 Area B — Contesto del Lavoro (6 sub-areas, ~40 indicators)

**Scoring**: Each indicator is SI=0 or NO=1 (positive condition present = no stress points).  
**Exception**: Items with "1-..." in CORREZIONE column have inverted scoring (SI=1, NO=0) — these are negative conditions.

#### B1. Funzione e Cultura Organizzativa (11 indicators)

| # | Indicatore | SI | NO |
|---|-----------|----|----|
| 1 | Diffusione organigramma aziendale | 0 | 1 |
| 2 | Presenza di procedure aziendali | 0 | 1 |
| 3 | Diffusione delle procedure aziendali ai lavoratori | 0 | 1 |
| 4 | Diffusione degli obiettivi aziendali ai lavoratori | 0 | 1 |
| 5 | Sistema di gestione della sicurezza aziendale. Certificazioni SA8000 e BS OHSAS 18001:2007 | 0 | 1 |
| 6 | Presenza di un sistema di comunicazione aziendale (bacheca, internet, busta paga, volantini...) | 0 | 1 |
| 7 | Effettuazione riunioni/incontri tra dirigenti e lavoratori | 0 | 1 |
| 8 | Presenza di un piano formativo per la crescita professionale dei lavoratori | 0 | 1 |
| 9 | Presenza di momenti di comunicazione dell'azienda a tutto il personale | 0 | 1 |
| 10 | Presenza di codice etico e di comportamento | 0 | 1 |
| 11 | Presenza di sistemi per il recepimento e la gestione dei casi di disagio lavorativo | 0 | 1 |

**Max score**: 11

#### B2. Ruolo nell'Ambito dell'Organizzazione (4 indicators)

| # | Indicatore | SI | NO | Inverted? |
|---|-----------|----|----|-----------|
| 1 | I lavoratori conoscono la linea gerarchica aziendale | 0 | 1 | No |
| 2 | I ruoli sono chiaramente definiti | 0 | 1 | No |
| 3 | Vi e una sovrapposizione di ruoli differenti sulle stesse persone | 0 | 1 | **Yes** (1-...) |
| 4 | Accade di frequente che dirigenti/preposti forniscano informazioni contrastanti | 0 | 1 | **Yes** (1-...) |

**Max score**: 4

#### B3. Evoluzione della Carriera (3 indicators)

| # | Indicatore | SI | NO |
|---|-----------|----|----|
| 1 | Sono definiti i criteri per l'avanzamento di carriera | 0 | 1 |
| 2 | Esistono sistemi premianti in relazione alla corretta gestione del personale | 0 | 1 |
| 3 | Esistono sistemi premianti in relazione al raggiungimento degli obiettivi di sicurezza | 0 | 1 |

**Max score**: 3

#### B4. Autonomia Decisionale — Controllo del Lavoro (5 indicators)

| # | Indicatore | SI | NO | Inverted? |
|---|-----------|----|----|-----------|
| 1 | Il lavoro dipende da compiti precedentemente svolti da altri | 0 | 1 | **Yes** (1-...) |
| 2 | I lavoratori hanno sufficiente autonomia per l'esecuzione dei compiti | 0 | 1 | No |
| 3 | I lavoratori hanno a disposizione le informazioni sulle decisioni aziendali | 0 | 1 | No |
| 4 | Sono predisposti strumenti di partecipazione decisionale dei lavoratori | 0 | 1 | No |
| 5 | Sono presenti rigidi protocolli di supervisione sul lavoro svolto | 0 | 1 | **Yes** (1-...) |

**Max score**: 5

#### B5. Rapporti Interpersonali sul Lavoro (3 indicators)

| # | Indicatore | SI | NO | Inverted? |
|---|-----------|----|----|-----------|
| 1 | Possibilita di comunicare con i dirigenti di grado superiore | 0 | 1 | No |
| 2 | Vengono gestiti eventuali comportamenti prevaricatori o illeciti | 0 | 1 | No |
| 3 | Vi e la segnalazione frequente di conflitti / litigi | 0 | 1 | **Yes** (1-...) |

**Max score**: 3

#### B6. Interfaccia Casa Lavoro — Conciliazione Vita/Lavoro (4 indicators)

| # | Indicatore | SI | NO |
|---|-----------|----|----|
| 1 | Possibilita di effettuare la pausa pasto in luogo adeguato / mensa aziendale | 0 | 1 |
| 2 | Possibilita di orario flessibile | 0 | 1 |
| 3 | Possibilita di raggiungere il posto di lavoro con mezzi pubblici / navetta | 0 | 1 |
| 4 | Possibilita di svolgere lavoro part-time verticale/orizzontale | 0 | 1 |

**Special scoring rule**: If total = 0, insert -1 in the final summary table. If total > 0, insert 0.

### 3.3 Area C — Contenuto del Lavoro (4 sub-areas, ~46 indicators)

#### C1. Ambiente di Lavoro ed Attrezzature di Lavoro (13 indicators)

| # | Indicatore | SI | NO | Inverted? |
|---|-----------|----|----|-----------|
| 1 | Esposizione a rumore sup. al secondo livello d'azione | 0 | 1 | **Yes** |
| 2 | Inadeguato comfort acustico (ambiente non industriale) | 0 | 1 | **Yes** |
| 3 | Rischio cancerogeno/chimico non irrilevante | 0 | 1 | **Yes** |
| 4 | Microclima adeguato | 0 | 1 | No |
| 5 | Adeguato illuminamento con particolare riguardo alle attivita ad elevato impegno visivo | 0 | 1 | No |
| 6 | Rischio movimentazione manuale dei carichi | 0 | 1 | **Yes** |
| 7 | Disponibilita adeguati e confortevoli DPI | 0 | 1 | No (Se non previsto segnare Si) |
| 8 | Lavoro a rischio di aggressione fisica / lavoro solitario | 0 | 1 | **Yes** |
| 9 | Segnaletica di sicurezza chiara, immediata e pertinente ai rischi | 0 | 1 | No |
| 10 | Esposizione a vibrazione superiore al limite d'azione | 0 | 1 | **Yes** |
| 11 | Adeguata manutenzione macchine ed attrezzature | 0 | 1 | No |
| 12 | Esposizione a radiazioni ionizzanti | 0 | 1 | **Yes** |
| 13 | Esposizione a rischio biologico | 0 | 1 | **Yes** |

**Max score**: 13

#### C2. Pianificazione dei Compiti (6 indicators)

| # | Indicatore | SI | NO | Inverted? |
|---|-----------|----|----|-----------|
| 1 | Il lavoro subisce frequenti interruzioni | 0 | 1 | **Yes** |
| 2 | Adeguatezza delle risorse strumentali necessarie | 0 | 1 | No |
| 3 | E presente un lavoro caratterizzato da alta monotonia | 0 | 1 | **Yes** |
| 4 | Lo svolgimento della mansione richiede di eseguire piu compiti contemporaneamente | 0 | 1 | **Yes** |
| 5 | Chiara definizione dei compiti | 0 | 1 | No |
| 6 | Adeguatezza delle risorse umane necessarie | 0 | 1 | No |

**Max score**: 6

#### C3. Carico di Lavoro — Ritmo di Lavoro (9 indicators)

| # | Indicatore | SI | NO | Inverted? |
|---|-----------|----|----|-----------|
| 1 | I lavoratori hanno autonomia nella esecuzione dei compiti | 0 | 1 | No |
| 2 | Ci sono variazioni imprevedibili della quantita di lavoro | 0 | 1 | **Yes** |
| 3 | Vi e assenza di compiti per lunghi periodi nel turno lavorativo | 0 | 1 | **Yes** |
| 4 | E presente un lavoro caratterizzato da alta ripetitivita | 0 | 1 | **Yes** |
| 5 | Il ritmo lavorativo per l'esecuzione del compito e prefissato | 0 | 1 | **Yes** |
| 6 | Il lavoratore non puo agire sul ritmo della macchina | 0 | 1 | **Yes** (Se non previsto segnare NO) |
| 7 | I lavoratori devono prendere decisioni rapide | 0 | 1 | **Yes** |
| 8 | Lavoro con utilizzo di macchine ed attrezzature ad alto rischio | 0 | 1 | **Yes** |
| 9 | Lavoro con elevata responsabilita per terzi, impianti e produzione | 0 | 1 | **Yes** |

**Max score**: 9

#### C4. Orario di Lavoro (8 indicators)

| # | Indicatore | SI | NO | Inverted? |
|---|-----------|----|----|-----------|
| 1 | E presente regolarmente un orario lavorativo superiore alle 8 ore | 0 | 1 | **Yes** |
| 2 | Viene abitualmente svolto lavoro straordinario | 0 | 1 | **Yes** |
| 3 | E presente orario di lavoro rigido (non flessibile)? | 0 | 1 | **Yes** |
| 4 | La programmazione dell'orario varia frequentemente | 0 | 1 | **Yes** |
| 5 | Le pause di lavoro non sono chiaramente definite | 0 | 1 | No |
| 6 | E presente il lavoro a turni | 0 | 1 | **Yes** |
| 7 | E presente il lavoro a turni notturni | 0 | 1 | **Yes** |
| 8 | E presente il turno notturno fisso o a rotazione | 0 | 1 | **Yes** |

**Max score**: 8

### 3.4 Area Threshold Tables (Soglie per Area)

#### Area A — Indicatori Aziendali

| Score Range | % Range | Livello | Convert to |
|-------------|---------|---------|------------|
| 0–10 | 0–25% | BASSO | 0 |
| 11–20 | 25–50% | MEDIO | 2 |
| 21–40 | 50–100% | ALTO | 5 |

#### Area B — Contesto del Lavoro (sub-area thresholds)

| Indicatore | Basso (DA–A) | Medio (DA–A) | Alto (DA–A) |
|-----------|-------------|-------------|------------|
| Funzione e cultura organizzativa | 0–4 | 5–7 | 8–11 |
| Ruolo nell'ambito dell'organizzazione | 0–1 | 2–3 | 4 |
| Evoluzione della carriera | 0–1 | 2 | 3 |
| Autonomia decisionale / controllo del lavoro | 0–1 | 2–3 | 4–5 |
| Rapporti interpersonali sul lavoro | 0–1 | 2 | 3 |
| Interfaccia casa lavoro * | (special rule) | (special rule) | (special rule) |
| **TOTALE B** | **0–8** | **9–17** | **18–26** |

#### Area C — Contenuto del Lavoro

| Indicatore | Basso (DA–A) | Medio (DA–A) | Alto (DA–A) |
|-----------|-------------|-------------|------------|
| Ambiente di lavoro ed attrezzature | 0–5 | 6–9 | 10–13 |
| Pianificazione dei compiti | 0–2 | 3–4 | 5–6 |
| Carico di lavoro / ritmo di lavoro | 0–4 | 5–7 | 8–9 |
| Orario di lavoro | 0–2 | 3–5 | 6–8 |
| **TOTALE C** | **0–13** | **14–25** | **26–36** |

### 3.5 Final Risk Level Classification

Total score = sum of converted Area A score + Area B total + Area C total.

| Score Range (DA–A) | % Range | Livello di Rischio | Azione |
|--------------------|---------|-------------------|--------|
| 0–17 | <= 25% | **RISCHIO BASSO** | Nessun approfondimento richiesto. Ripetere valutazione entro 2 anni. |
| 18–34 | 25–50% | **RISCHIO MEDIO** | Adottare azioni di miglioramento mirate. Se non migliorano entro 1 anno, procedere al 2o livello (questionari lavoratori). Ripetere entro 2 anni. |
| 35–67 | > 50% | **RISCHIO ALTO** | Effettuare 2o livello (percezione lavoratori). Verificare efficacia azioni entro 1 anno. Ripetere entro 2 anni. |

**Max possible score**: 67 (40 area A raw -> 5 converted, + 26 area B + 36 area C = 67)

---

## 4. Fire Risk Scoring (Rischio Incendio)

**Method**: D.M. 03.09.2021 ex D.M. 10.03.1998  
**Formula**: `Livello = INF + SI + PI` (sum of three parameters, each 1–3)

### 4.1 Parametri di Valutazione (Assessment Parameters)

| Parametro | Livello | Valore |
|-----------|---------|--------|
| **INF** — Caratteristiche di infiammabilita delle sostanze presenti | A basso tasso di infiammabilita | 1 |
| **INF** | Infiammabili | 2 |
| **INF** | Altamente infiammabili | 3 |
| **SI** — Possibilita di sviluppo di incendio | Bassa | 1 |
| **SI** | Limitata | 2 |
| **SI** | Notevole | 3 |
| **PI** — Probabilita di propagazione dell'incendio | Basso | 1 |
| **PI** | Medio | 2 |
| **PI** | Elevato | 3 |

### 4.2 Classificazione del Livello di Rischio Incendio

| Somma INF + SI + PI | Livello di Rischio |
|---------------------|-------------------|
| 3–4 | **Basso** |
| 5–6–7 | **Medio** |
| 8–9 | **Elevato** |

### 4.3 Risk Level Definitions

**Basso** — Luoghi con sostanze a basso tasso di infiammabilita, scarse possibilita di sviluppo incendio, probabilita di propagazione limitata.

**Medio** — Luoghi con sostanze infiammabili e/o condizioni che possono favorire lo sviluppo di incendi, ma con limitata probabilita di propagazione.

**Elevato** — Luoghi con sostanze altamente infiammabili e/o condizioni con notevoli probabilita di sviluppo incendi e nella fase iniziale non e possibile la completa evacuazione. Comprende:
- Aree con utilizzo di sostanze altamente infiammabili o fiamme libere
- Aree con deposito/manipolazione di sostanze chimiche esotermiche
- Aree con deposito di sostanze esplosive/altamente infiammabili
- Aree con notevole quantita di materiali combustibili facilmente incendiabili
- Edifici interamente in legno

### 4.4 Per-Environment Assessment Template

Each work environment (area omogenea) is assessed with these fields:

| Campo | field_key |
|-------|-----------|
| Ambiente di Lavoro | `environment_name` |
| Tipo di Attivita | `activity_type` |
| Materiali immagazzinati e manipolati | `stored_materials` |
| Attrezzature presenti nel luogo di lavoro compresi gli arredi | `equipment_furniture` |
| Caratteristiche costruttive del luogo di lavoro compresi i materiali di rivestimento | `construction_characteristics` |
| Dimensione ed articolazione del luogo di lavoro | `dimensions` |
| Numero di persone presenti (dipendenti ed altre persone) | `num_people` |
| Possibili sorgenti di innesco | `ignition_sources` |
| Criteri per ridurre i pericoli causati da materiali e sostanze infiammabili/combustibili | `material_reduction_criteria` |
| Misure per ridurre i pericoli causati da sorgenti di calore | `heat_source_measures` |

### 4.5 Prevention Measures Template (per Environment)

For each environment, prevention measures are documented across 6 areas:

| # | Area di Prevenzione |
|---|-------------------|
| 1 | Ridurre la probabilita di insorgenza di un incendio |
| 2 | Garantire l'esodo delle persone in sicurezza in caso di incendio |
| 3 | Realizzare le misure per una rapida segnalazione dell'incendio (sistemi di allarme e procedure di intervento) |
| 4 | Assicurare l'estinzione di un incendio |
| 5 | Garantire l'efficienza dei sistemi di protezione antincendio |
| 6 | Fornire ai lavoratori adeguata informazione e formazione sui rischi di incendio |

---

## 5. VDT Assessment Criteria (Videoterminali)

### 5.1 Exposure Threshold

**Rule**: A worker is classified as **Esposto** (Exposed) if they use VDT for **>= 20 ore/settimana** (20 hours/week).

| Condition | Classification |
|-----------|---------------|
| >= 20 ore/settimana | **Esposto** — sorveglianza sanitaria obbligatoria |
| < 20 ore/settimana | **Non Esposto** |

### 5.2 Principal Risk Factors

The VDT assessment identifies three categories of risk:

| # | Categoria di Rischio | Fattori |
|---|---------------------|---------|
| 1 | **Disturbi alla vista e agli occhi** | Errate condizioni di illuminazione; ubicazione sbagliata del VDT rispetto a finestre; condizioni ambientali sfavorevoli (aria secca, correnti, temperatura); caratteristiche inadeguate del software/hardware (sfarfallamento); insufficiente contrasto; posizione statica prolungata; difetti visivi non corretti |
| 2 | **Problemi legati alla postura** | Disturbi colonna vertebrale da errata posizione e seduta prolungata; disturbi muscolari da posizione contratta statica; disturbi mano/avambraccio (infiammazione nervi/tendini da movimenti ripetitivi) |
| 3 | **Affaticamento fisico e mentale** | Operazioni monotone e ripetitive per lunghi periodi; cattive condizioni ambientali (temperatura, umidita, velocita aria); rumore disturbante; software non adeguato |

### 5.3 Workstation Requirements Checklist

The VDT assessment evaluates each workstation against these requirements:

**Monitor:**
- Liberamente e facilmente orientabile e inclinabile
- Luminosita e contrasto regolabili
- Involucro privo di riflessi
- Posizionato in modo che il bordo superiore sia all'altezza degli occhi o leggermente sotto

**Tastiera e Mouse:**
- Tastiera indipendente, spostabile, basso spessore, inclinabile, stabile
- Tasti con superficie infossata e caratteri leggibili
- Colore opaco, chiaro ma non bianco

**Illuminazione:**
- Direzione principale dello sguardo parallela alle finestre
- No finestre davanti o dietro il monitor
- Possibilita di oscuramento (veneziane, pellicole, tende)
- Illuminazione artificiale adeguata (la sola luce diurna e inadeguata)

**Condizioni ambientali:**
- Temperatura invernale >= 18 C
- Differenza estate interno/esterno < 7 C
- Umidita non troppo bassa (evitare secchezza mucose)
- No correnti d'aria fastidiose
- Rumore ambientale non disturbante

**Ergonomia:**
- Distanza visiva minima dal monitor variabile per dimensione schermo
- Piano di lavoro regolabile in altezza
- Sedia regolabile in altezza e inclinazione
- Poggiapiedi disponibile se necessario

### 5.4 Per-Worker Assessment Template

Each worker is assessed with these fields:

| Campo | field_key |
|-------|-----------|
| Nominativo | `worker_name` |
| Mansione | `job_role` |
| Tempo di utilizzo [ore/settimana] | `weekly_vdt_hours` |
| Rischio VDT (Esposto / Non Esposto) | `vdt_exposed` |
| Postazione VDT | `workstation_name` |
| Attivita | `workstation_activity` |

### 5.5 Standard Prevention Measures

| Misura | Descrizione |
|--------|-------------|
| Muoversi di piu | Evitare posizioni statiche prolungate |
| Le pause | Pausa di almeno 15 minuti ogni 2 ore di utilizzo consecutivo |
| Training per gli occhi | Esercizi di rilassamento visivo |
| Lavoratrici gestanti | Disposizioni speciali per lavoratrici in gravidanza |
| Esercizi di stretching e rilassamento | Esercizi specifici per prevenzione disturbi muscolo-scheletrici |

---

## Appendix: Safety Signage Color Codes (from DVR Master)

| Colore | Significato | Indicazioni |
|--------|-----------|-------------|
| **Rosso** | Segnali di divieto / Pericolo-Allarme / Materiali antincendio | Atteggiamenti pericolosi; Alt, arresto; Identificazione ubicazione antincendio |
| **Giallo/Giallo-Arancio** | Segnali di avvertimento | Attenzione, cautela, verifica |
| **Azzurro** | Segnali di prescrizione | Comportamento/azione specifica, obbligo DPI |
| **Verde** | Segnali di salvataggio/soccorso / Situazione di sicurezza | Porte, uscite, percorsi; Ritorno alla normalita |

| Tipo Cartello | Forma | Colori |
|--------------|-------|--------|
| Divieto | Rotonda | Pittogramma nero su fondo bianco, bordo e banda rossa |
| Avvertimento | Triangolare | Pittogramma nero su fondo giallo, bordo nero |
| Prescrizione | Rotonda | Pittogramma bianco su fondo azzurro |
| Salvataggio | Quadrata/Rettangolare | Pittogramma bianco su fondo verde |
| Antincendio | Quadrata/Rettangolare | Pittogramma bianco su fondo rosso |
