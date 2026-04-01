> **NIUEXA** | AI-Powered Business Automation  
> *N2O DVR Automation Platform — Project Documentation*  
> Version 1.0 | April 2026 | Gregor Maric  
> Confidential — Niuexa & N2O SRL

---

# DVR Template Mapping

Programmatic structural analysis of `DVR RISCHIO MASTER.docx` (the ~187-page master risk assessment document). This mapping drives the document generation engine by identifying every structural element, classifying it as static or dynamic, and mapping its data dependencies.

**Source file**: `templates/DVR RISCHIO MASTER.docx` (4.8 MB)

## 1. Summary Statistics

| Metric | Value |
|--------|-------|
| Total paragraphs | 2445 |
| Total tables | 111 |
| Total image relationships | 19 |
| Total body elements (ordered) | 2556 |
| Heading paragraphs | 109 |
| Document parts (Parte I-IV) | 4 |
| Work environments in Part III | 7 |
| Unique paragraph styles | 24 |
| Unique table styles | 1 |
| Paragraphs with dynamic content | 18 |
| Table cells with dynamic content | 269 |

### Table Classification Summary

| Classification | Count | Description |
|---------------|-------|-------------|
| DYNAMIC | 41 | Company-specific data — must be generated from data model |
| MIXED | 13 | Static structure with dynamic data fields |
| STATIC | 36 | Generic legal/methodological text — copy verbatim |
| UNKNOWN | 21 | Could not auto-classify — examine manually |

### Paragraph Style Inventory

| Style Name | Count | Role | Heading Level |
|------------|-------|------|---------------|
| `a` | 1253 | Body text (main content) | - |
| `Normal` | 668 | Default/body text | - |
| `a puntato` | 217 | Bullet point list item | - |
| `a titolo 2` | 68 | Subsection heading | H2 |
| `a titolo 1` | 54 | Main section heading | H1 |
| `toc 3` | 48 | Table of contents level 3 | - |
| `toc 2` | 31 | Table of contents level 2 | - |
| `a puntato 2` | 19 | Nested bullet (level 2) | - |
| `a elenchi alfabetici` | 19 | Alphabetical list item | - |
| `toc 1` | 8 | Table of contents level 1 | - |
| `a elenco num` | 8 | Numbered list item | - |
| `Body Text 3` | 7 | Cover page text | - |
| `spec` | 7 | Risk factor spec header (repeats per env) | - |
| `a tabella` | 7 | Table-associated text | - |
| `a elenchi nuovo` | 6 | New-format list item | - |
| `a Titolo parte` | 4 | Part divider (PARTE I/II/III/IV) | H0 |
| `a titolo parte 2` | 4 | Part subtitle | H0 |
| `a titolo 3` | 4 | Sub-subsection heading | H3 |
| `a titolo` | 4 | Section heading variant | H1 |
| `Subtitle` | 4 | Subtitle (declaration) | - |
| `a tabella centrato` | 2 | Centered table text (formulas) | - |
| `No Spacing` | 1 | No spacing text | - |
| `a indice` | 1 | Index text | - |
| `a tabella centrato 2` | 1 | Centered table text variant | - |

## 2. Document Parts and Boundaries

The DVR is divided into 4 major parts, each with a distinct role in the generation engine:

### PARTE I: Presentazione Azienda

- **Starts at**: paragraph #127 (element #130)
- **Contains**: 232 paragraphs, 15 tables (247 elements total)
- **Content**: Company data, employees, environments, equipment, chemicals
- **Engine role**: Almost entirely DYNAMIC — populated from Azienda, Persona, Ambiente entities

### PARTE II: Metodologia di Valutazione dei Rischi

- **Starts at**: paragraph #359 (element #377)
- **Contains**: 227 paragraphs, 5 tables (232 elements total)
- **Content**: Legal definitions, risk assessment methodology, D.Lgs. 81/2008 references, I=2D+P formula
- **Engine role**: Almost entirely STATIC — copy verbatim with minimal substitution

### PARTE III: Valutazione dei Rischi per Ambiente

- **Starts at**: paragraph #586 (element #609)
- **Contains**: 1201 paragraphs, 85 tables (1286 elements total)
- **Content**: Per-environment risk assessment with individual risk factor tables
- **Engine role**: THE DYNAMIC CORE — repeating template block generated once per Ambiente

### PARTE IV: Procedure di Attuazione e Miglioramento

- **Starts at**: paragraph #1787 (element #1895)
- **Contains**: 658 paragraphs, 3 tables (661 elements total)
- **Content**: Improvement procedures, safety management, training, inspections, DPI, signage
- **Engine role**: Mostly STATIC procedures with some dynamic fields (DPI lists, training schedules, DdL signature)

## 3. Document Structure — Heading Tree

Complete heading outline showing the document hierarchy. Style names in backticks, paragraph numbers in parentheses.

  - [a titolo 1] **Indice** *(#15)*
  - [a titolo 1] **Premessa** *(#104)*

---
**PARTE I** *(para #127, `a Titolo parte`)*

  *Presentazione dell’azienda*
  - [a titolo 1] **Anagrafica Aziendale** *(#135)*
  - [a titolo 1] **Dati occupazionali** *(#138)*
  - [a titolo 1] **Descrizione dell’azienda e dell’attività** *(#139)*
  - [a titolo 1] **Organizzazione Aziendale della Sicurezza** *(#203)*
  - [a titolo 1] **Ambienti di Lavoro** *(#233)*
  - [a titolo 1] **Servizi Igienico – Assistenziali** *(#292)*
  - [a titolo 1] **Elenco Macchine, Attrezzature ed Impianti** *(#308)*
  - [a titolo 1] **Elenco sostanze, prodotti e preparati chimici** *(#339)*
  - [a titolo 1] **Elenco Fattori di Pericolo** *(#345)*
      - [a titolo 3] **N.B. Gli elenchi seguenti sono da intendersi indicativi e non esaustivi** *(#346)*

---
**PARTE II** *(para #359, `a Titolo parte`)*

  *Relazione sulla valutazione dei rischi per la sicurezza e la salute durante il lavoro e relativi criteri adottati*
  - [a titolo 1] **Definizioni** *(#366)*
  - [a titolo 1] **Metodologia** *(#367)*
    - [a titolo 2] **Generalità** *(#368)*
    - [a titolo 2] **Individuazione dei Soggetti Esposti** *(#389)*
    - [a titolo 2] **Identificazione dei Pericoli** *(#428)*
    - [a titolo 2] **Individuazione dei Rischi di Esposizione** *(#452)*
    - [a titolo 2] **Definizione delle misure di prevenzione e di protezione attuate e dei dispositivi di protezione individuali adottati** *(#499)*
    - [a titolo 2] **Classificazione dei rischi** *(#503)*
    - [a titolo 2] **Individuazione delle procedure per l’attuazione delle misure** *(#567)*
    - [a titolo 2] **Redazione del Documento di Valutazione dei Rischi** *(#571)*
    - [a titolo 2] **Aggiornamento del documento** *(#576)*

---
**PARTE III** *(para #586, `a Titolo parte`)*

  *Individuazione dei rischi, delle misure di prevenzione e di protezione e dei dispositivi di protezione individuale*
  - [a titolo 1] **Identificazione dell’Ambiente di Lavoro e degli Addetti - UFFICIO AMMINISTRATIVO** *(#598)*
  - [a titolo 1] **Identificazione dei Fattori di Rischio - UFFICIO AMMINISTRATIVO** *(#610)*
  - [a titolo 1] **Identificazione dell’Ambiente di Lavoro e degli Addetti - UFFICIO TECNICO** *(#759)*
  - [a titolo 1] **Identificazione dei Fattori di Rischio - UFFICIO TECNICO** *(#769)*
  - [a titolo 1] **Identificazione dell’Ambiente di Lavoro e degli Addetti - UFFICIO COMMERCIALE E MEDICINA DEL LAVORO** *(#925)*
  - [a titolo 1] **Identificazione dei Fattori di Rischio - UFFICIO COMMERCIALE E MEDICINA DEL LAVORO** *(#935)*
  - [a titolo 1] **Identificazione dell’Ambiente di Lavoro e degli Addetti - SALA CORSI** *(#1103)*
  - [a titolo 1] **Identificazione dei Fattori di Rischio - SALA CORSI** *(#1114)*
  - [a titolo 1] **Identificazione dell’Ambiente di Lavoro e degli Addetti - MAGAZZINO** *(#1281)*
  - [a titolo 1] **Identificazione dei Fattori di Rischio - MAGAZZINO** *(#1291)*
  - [a titolo 1] **Identificazione dell’Ambiente di Lavoro e degli Addetti - AREA BREAK** *(#1442)*
  - [a titolo 1] **Identificazione dei Fattori di Rischio - AREA BREAK** *(#1452)*
  - [a titolo 1] **Identificazione dell’Ambiente di Lavoro e degli Addetti - STRUTTURE PRESSO CLIENTI** *(#1560)*
  - [a titolo 1] **Identificazione dei Fattori di Rischio - STRUTTURE PRESSO CLIENTI** *(#1570)*
  - [a titolo 1] **Elenco Mansioni che espongono i lavoratori a rischi specifici (art. 28 co. 2/f D.Lgs. 81/08 e s.m.i.)** *(#1669)*
  - [a titolo 1] **Dispositivi di Protezione Individuale (DPI)** *(#1672)*
  - [a titolo 1] **Segnaletica di sicurezza** *(#1709)*
      - [a titolo 3] **Definizione** *(#1710)*
      - [a titolo 3] **Obblighi del datore di lavoro** *(#1713)*
      - [a titolo 3] **Scopo della segnaletica di sicurezza** *(#1722)*
  - [a titolo 1] **Principale segnaletica da apporre negli ambienti di lavoro** *(#1729)*
  - [a titolo 1] **Programma di Formazione, Informazione ed Addestramento** *(#1773)*

---
**PARTE IV** *(para #1787, `a Titolo parte`)*

  *Programma e Procedure delle misure per garantire il miglioramento nel tempo dei livelli di sicurezza*
  - [a titolo 1] **Programma e Procedure di attuazione delle Misure di Miglioramento** *(#1794)*
  - [a titolo 1] **Gestione Leggi e Regolamenti** *(#1800)*
    - [a titolo 2] **Responsabilità** *(#1801)*
    - [a titolo 2] **Ricerca delle leggi** *(#1809)*
    - [a titolo 2] **Diffusione ed utilizzo di leggi e regolamenti** *(#1813)*
    - [a titolo 2] **Archiviazione** *(#1819)*
  - [a titolo] **Documentazione Collegata** *(#1828)*
  - [a titolo 1] **Gestione Sorveglianza sanitaria** *(#1831)*
    - [a titolo 2] **Verifica delle necessità della sorveglianza sanitaria** *(#1832)*
    - [a titolo 2] **Nomina del MC** *(#1841)*
    - [a titolo 2] **Revoca della Nomina** *(#1867)*
    - [a titolo 2] **Attività Del MC** *(#1876)*
    - [a titolo 2] **Documentazione Collegata** *(#1879)*
  - [a titolo 1] **Gestione Informazione, Formazione ed Addestramento** *(#1884)*
    - [a titolo 2] **Programmazione della Formazione, Informazione ed Addestramento** *(#1885)*
    - [a titolo 2] **Segnalazione delle necessità Formative od Informative** *(#1897)*
    - [a titolo 2] **Criteri di Erogazione delle Attività di Informazione, Formazione ed Addestramento** *(#1905)*
    - [a titolo 2] **Esecuzione e Registrazione delle Attività** *(#1933)*
    - [a titolo 2] **Documentazione Collegata** *(#1943)*
  - [a titolo 1] **Riunione Periodica** *(#1962)*
    - [a titolo 2] **Convocazione** *(#1963)*
    - [a titolo 2] **Verbalizzazione e Divulgazione** *(#1999)*
  - [a titolo] **Documentazione Collegata** *(#2009)*
  - [a titolo 1] **Gestione degli Infortuni** *(#2013)*
    - [a titolo 2] **Segnalazione** *(#2014)*
    - [a titolo 2] **Indagine** *(#2021)*
    - [a titolo 2] **Commissione di indagine** *(#2043)*
    - [a titolo 2] **Relazione Tecnica di Valutazione Finale** *(#2069)*
    - [a titolo 2] **Registro degli Infortuni e Denuncia Infortunio** *(#2094)*
  - [a titolo] **Documentazione Collegata** *(#2108)*
  - [a titolo 1] **Gestione comportamenti scorretti dei lavoratori** *(#2115)*
    - [a titolo 2] **Cause di Richiamo Lavoratori** *(#2116)*
    - [a titolo 2] **Richiamo verbale** *(#2130)*
    - [a titolo 2] **Lettera di Richiamo** *(#2138)*
    - [a titolo 2] **Sanzione Disciplinare** *(#2141)*
    - [a titolo 2] **Possibilità di risposta da parte del lavoratore alla sanzione disciplinare** *(#2149)*
  - [a titolo] **Documentazione Collegata** *(#2155)*
  - [a titolo 1] **Gestione DPI** *(#2159)*
    - [a titolo 2] **Acquisizione di DPI** *(#2160)*
    - [a titolo 2] **Destinazione dei DPI** *(#2174)*
    - [a titolo 2] **Gestione di casi di inadeguatezza ed intolleranza ai DPI** *(#2184)*
    - [a titolo 2] **Modalità di utilizzazione e mantenimento dei DPI** *(#2190)*
    - [a titolo 2] **informazione, formazione e addestramento** *(#2213)*
    - [a titolo 2] **Documentazione Collegata** *(#2232)*
  - [a titolo 1] **Gestione Infrastrutture** *(#2235)*
    - [a titolo 2] **Documentazione Collegata** *(#2249)*
  - [a titolo 1] **Gestione Lavoratori appartenenti a gruppi particolarmente sensibili al rischio** *(#2253)*
    - [a titolo 2] **Lavoratrici gestanti, puerpere o in periodo di allattamento (D.Lgs. 151/2001)** *(#2254)*
    - [a titolo 2] **Lavoratori minori (D.Lgs. 345/99)** *(#2305)*
    - [a titolo 2] **Lavoratori diversamente abili** *(#2374)*
    - [a titolo 2] **Lavoratori stranieri** *(#2378)*
  - [a titolo 1] **Gestione Acquisti** *(#2380)*
  - [a titolo 1] **Gestione delle lavorazioni affidate in appalto** *(#2390)*
    - [a titolo 2] **D.U.V.R.I.** *(#2402)*
    - [a titolo 2] **Informazioni sui requisiti tecnico professionali delle ditte appaltatrici** *(#2410)*
  - [a titolo 1] **Dichiarazione del Datore di Lavoro** *(#2429)*

## 4. Table Catalog

All **111 tables** in the document, grouped by Part.

### Tables in Before PARTE I

#### Table 0

- **Size**: 5 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=4, static=0)
- **Nearest heading**: ex art. 17, comma 1, lettera a) ed art. 28 del D.Lgs. 81/2008 e s.m.i. (D.Lgs. 1

**Header row:**

| `Azienda` | `N2O SRL` |
| --- | --- |
| Sede Legale | VIA DEI CHIOSI 4 |
| Sede Legale | GORGONZOLA (MI) |

#### Table 1

- **Size**: 7 rows x 3 columns
- **Classification**: **DYNAMIC** (dynamic=3, static=0)
- **Nearest heading**: ex art. 17, comma 1, lettera a) ed art. 28 del D.Lgs. 81/2008 e s.m.i. (D.Lgs. 1

**Header row:**

| `Rev.` | `Motivazione` | `Data` |
| --- | --- | --- |
| 00 | Emissione | 27/03/2024 |
| 01 | Revisione – Aggiornamento anagrafica dipenden | 02/09/2024 |

#### Table 2

- **Size**: 2 rows x 1 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: ex art. 17, comma 1, lettera a) ed art. 28 del D.Lgs. 81/2008 e s.m.i. (D.Lgs. 1

**Header row:**

| `Timbro e Firma` |
| --- |
|  |

### Tables in PARTE I

#### Table 3

- **Size**: 5 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=4, static=0)
- **Nearest heading**: Presentazione dell’azienda

**Header row:**

| `Azienda` | `N2O SRL` |
| --- | --- |
| Sede Legale | VIA DEI CHIOSI 4 |
| Sede Legale | GORGONZOLA (MI) |

#### Table 4

- **Size**: 12 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=4, static=0)
- **Nearest heading**: Anagrafica Aziendale

**Header row:**

| `Azienda` | `N2O SRL` |
| --- | --- |
| Attività | 46.69.94 - Commercio all'ingrosso di articoli |
| Sede legale | VIA DEI CHIOSI 4 |

#### Table 5

- **Size**: 15 rows x 5 columns
- **Classification**: **DYNAMIC** (dynamic=8, static=0)
- **Nearest heading**: Dati occupazionali

**Header row:**

| `Nominativo` | `Mansione` | `Ambiente di Lavoro` | `Note` | `Tipologia contrattuale` |
| --- | --- | --- | --- | --- |
| CIARAMITARO AMALIA | TITOLARE | UFFICI MAGAZZINO AREA BREAK SALA CORSI | CRMMLA90M70G273Y | DATORE  DI LAVORO |
| SORMANI ANNALISA | IMPIEGATA | UFFICIO AMMINISTRATIVO AREA BREAK | SRMNLS75B57F119X | IMPIEGATA |

#### Table 6

- **Size**: 2 rows x 1 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Organizzazione Aziendale della Sicurezza

**Header row:**

| `Datore di Lavoro` |
| --- |
| CIARAMITARO AMALIA |

#### Table 7

- **Size**: 2 rows x 1 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Organizzazione Aziendale della Sicurezza

**Header row:**

| `Responsabile del  Servizio di Prev. e Prot.` |
| --- |
| CIARAMITARO AMALIA |

#### Table 8

- **Size**: 2 rows x 1 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: Organizzazione Aziendale della Sicurezza

**Header row:**

| `Rappresentante dei Lavoratori` |
| --- |
| CIARCELLUTI MARIANNA |

#### Table 9

- **Size**: 2 rows x 1 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: (none)

**Header row:**

| `Medico Competente` |
| --- |
| DOTT.SSA MARINA MORARI |

#### Table 10

- **Size**: 5 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=0)
- **Nearest heading**: Il Datore di Lavoro ai sensi dell’art. 18 co. 1 lettera b) del D.Lgs. 81/08 e s.

**Header row:**

| `Addetti al Primo Soccorso` | `Addetti al Primo Soccorso` |
| --- | --- |
| Nominativo | Mansione |
| MARCHETTI LUCA | IMPIEGATO -DOCENTE FORMATORE |

#### Table 11

- **Size**: 5 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: Il Datore di Lavoro ai sensi dell’art. 18 co. 1 lettera b) del D.Lgs. 81/08 e s.

**Header row:**

| `Addetti alla prevenzione incendi e lotta anti` | `Addetti alla prevenzione incendi e lotta anti` |
| --- | --- |
| Nominativo | Mansione |
| MARCHETTI LUCA | IMPIEGATO-DOCENTE FORMATORE |

#### Table 12

- **Size**: 8 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=8, static=0)
- **Nearest heading**: Ambienti di Lavoro

**Header row:**

| `Ambiente` | `N. Lavoratori` |
| --- | --- |
| UFFICIO AMMINISTRATIVO | 1 |
| UFFICIO TECNICO | 5 |

#### Table 13

- **Size**: 16 rows x 3 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Si riporta l’elenco delle macchine, attrezzature ed impianti utilizzate nell’att

**Header row:**

| `Macchine, attrezzature ed impianti` | `Marcata CE` | `Verifiche periodiche` |
| --- | --- | --- |
| FURGONE MOD.JUMPY TARGA FZ909GN | Si | Si |
| FURGONE MOD.DOBLO' TG.FP120WZ | Si | Si |

#### Table 14

- **Size**: 5 rows x 3 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Elenco sostanze, prodotti e preparati chimici

**Header row:**

| `Sostanza / Prodotto` | `Produttore / Distributore` | `Attività` |
| --- | --- | --- |
| WD-40 LUBRIFICANTE AL SILICONE SPECIALIST | LUBRIFICANTI 4WD ITALIA | PRODOTTO MULTIFUNZIONE LUBRIFICA METALLI, ELI |
| ACE CANDEGGINA SPRAY MOUSSE | ACE | DISINFETTANTE SANITARI WC |

#### Table 15

- **Size**: 33 rows x 2 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: N.B. Gli elenchi seguenti sono da intendersi indicativi e non esaustivi

**Header row:**

| `` | `Rischi per la Sicurezza` |
| --- | --- |
| Strutture Rischi da carenze strutturali dell’ | Altezza dell’Ambiente |
| Strutture Rischi da carenze strutturali dell’ | Superficie dell’Ambiente |

#### Table 16

- **Size**: 18 rows x 2 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: N.B. Gli elenchi seguenti sono da intendersi indicativi e non esaustivi

**Header row:**

| `` | `Rischi per la Salute` |
| --- | --- |
| Agenti Chimici | Rischi di esposizione connessi con l’impiego  |
| Agenti Fisici Rischi dsa esposizione a grande | Rumore: presenza di apparecchiature rumorose  |

#### Table 17

- **Size**: 16 rows x 2 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: N.B. Gli elenchi seguenti sono da intendersi indicativi e non esaustivi

**Header row:**

| `` | `Rischi Trasversali` |
| --- | --- |
| Organizzazione del Lavoro | Processi di Lavoro usuranti: lavori in contin |
| Organizzazione del Lavoro | Pianificazione degli aspetti attinenti alla s |

### Tables in PARTE II

#### Table 18

- **Size**: 5 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=4, static=0)
- **Nearest heading**: Relazione sulla valutazione dei rischi per la sicurezza e la salute durante il lavoro e relativi criteri adottati

**Header row:**

| `Azienda` | `N2O SRL` |
| --- | --- |
| Sede Legale | VIA DEI CHIOSI 4 |
| Sede Legale | GORGONZOLA (MI) |

#### Table 19

- **Size**: 27 rows x 2 columns
- **Classification**: **MIXED** (dynamic=2, static=5)
- **Nearest heading**: Definizioni

**Header row:**

| `LAVORATORE (LAV)` | `persona che, indipendentemente dalla tipologi` |
| --- | --- |
| DATORE DI LAVORO (DL) | il soggetto titolare del rapporto di lavoro c |
| AZIENDA | il complesso della struttura organizzata dal  |

#### Table 20

- **Size**: 5 rows x 3 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)

**Header row:**

| `I` | `LIVELLO DI RISCHIO` | `AZIONE DA INTRAPRENDERE` |
| --- | --- | --- |
| I = 3-4 | ACCETTABILE | Instaurare un sistema di verifica che consent |
| I = 5-6 | MODESTO | Predisporre gli strumenti necessari a minimiz |

#### Table 21

- **Size**: 5 rows x 3 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=0)
- **Nearest heading**: Dove D è il massimo entità del danno ragionevolmente prevedibile, ovvero la magn

**Header row:**

| `P` | `LIVELLO` | `CRITERI` |
| --- | --- | --- |
| 4 | ELEVATA | Esiste una correlazione diretta tra mancanza  |
| 3 | MEDIO ALTA | La mancanza rilevata può provocare un danno,  |

#### Table 22

- **Size**: 5 rows x 3 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: (none)

**Header row:**

| `D` | `LIVELLO` | `CRITERI` |
| --- | --- | --- |
| 4 | INGENTE | Infortunio o episodio di esposizione con effe |
| 3 | NOTEVOLE | Infortunio o episodio di esposizione acuta co |

### Tables in PARTE III

#### Table 23

- **Size**: 5 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=4, static=0)
- **Nearest heading**: Individuazione dei rischi, delle misure di prevenzione e di protezione e dei dispositivi di protezione individuale

**Header row:**

| `Azienda` | `N2O SRL` |
| --- | --- |
| Sede Legale | VIA DEI CHIOSI 4 |
| Sede Legale | GORGONZOLA (MI) |

#### Table 24 `[ENV: UFFICIO AMMINISTRATIVO]`

- **Size**: 3 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=0)
- **Nearest heading**: Identificazione dell’Ambiente di Lavoro e degli Addetti - UFFICIO AMMINISTRATIVO
- **Environment**: UFFICIO AMMINISTRATIVO

**Header row:**

| `Ambiente di lavoro` | `UFFICIO AMMINISTRATIVO` |
| --- | --- |
| Preposto per la sicurezza | MARCHETTI LUCA |
| Descrizione Attività | AMMINISTRAZIONE |

#### Table 25 `[ENV: UFFICIO AMMINISTRATIVO]`

- **Size**: 3 rows x 2 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Identificazione dell’Ambiente di Lavoro e degli Addetti - UFFICIO AMMINISTRATIVO
- **Environment**: UFFICIO AMMINISTRATIVO

**Header row:**

| `Nominativo Addetti` | `Mansione` |
| --- | --- |
| CIARAMITARO AMALIA | TITOLARE |
| SORMANI ANNALISA | IMPIEGATA |

#### Table 26 `[ENV: UFFICIO AMMINISTRATIVO]`

- **Size**: 14 rows x 2 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Identificazione dei Fattori di Rischio - UFFICIO AMMINISTRATIVO
- **Environment**: UFFICIO AMMINISTRATIVO
- **Type**: Risk factor checklist (SI/NO)

**Header row:**

| `Rischi per la sicurezza` | `Rischi per la sicurezza` |
| --- | --- |
| Strutture | SI |
| Macchine | SI |

#### Table 27 `[ENV: UFFICIO AMMINISTRATIVO]`

- **Size**: 10 rows x 5 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=1)
- **Nearest heading**: (none)
- **Environment**: UFFICIO AMMINISTRATIVO
- **Risk table**: RISCHI PER LA SICUREZZA / STRUTTURE
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 8

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Presenza di ingombri ad altezza d’uomo | Durante la normale circolazione ed in condizi | Infortuni al capo | Segnalazione degli ingombri con nastro adesiv | P = 2; D = 2; I = 6; MODESTO |

#### Table 28 `[ENV: UFFICIO AMMINISTRATIVO]`

- **Size**: 10 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: UFFICIO AMMINISTRATIVO
- **Risk table**: RISCHI PER LA SICUREZZA / MACCHINE
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 8

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Utilizzo di attrezzature manuali. | Durante le ordinarie attività lavorative. | Lesioni alle mani e agli arti superiori.  Fer | Utilizzo delle attrezzature secondo le dispos | P = 2; D = 2; I = 6; MODESTO |

#### Table 29 `[ENV: UFFICIO AMMINISTRATIVO]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=2)
- **Nearest heading**: (none)
- **Environment**: UFFICIO AMMINISTRATIVO
- **Risk table**: RISCHI PER LA SICUREZZA / INCENDIO - ESPLOSIONI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Presenza di materiali infiammabili. | Durante le ordinarie attività lavorative | Ustioni. Incendi. Esplosioni. | Valutazione del rischio incendio ex art. 46 d | P = 2; D = 1; I = 4; ACCETTABILE |

#### Table 30 `[ENV: UFFICIO AMMINISTRATIVO]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: UFFICIO AMMINISTRATIVO
- **Risk table**: RISCHI PER LA SALUTE / AGENTI FISICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Condizioni microclimatiche non idonee. | Durante le ordinarie attività lavorative. | Disturbi a carico dell’apparato respiratorio. | Manutenzione periodica dei sistemi di condizi | P = 2; D = 2; I = 6; MODESTO |

#### Table 31 `[ENV: UFFICIO AMMINISTRATIVO]`

- **Size**: 7 rows x 5 columns
- **Classification**: **MIXED** (dynamic=2, static=3)
- **Nearest heading**: (none)
- **Environment**: UFFICIO AMMINISTRATIVO
- **Risk table**: RISCHI TRASVERSALI / ORGANIZZAZIONE DEL LAVORO
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 5

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Nuove attrezzature di lavoro | Introduzione nel ciclo produttivo di nuove at | Infortuni vari. Tensione nervosa, irritabilit | Prima dell’inserimento nel ciclo produttivo d | P = 2; D = 2; I = 6; MODESTO |

#### Table 32 `[ENV: UFFICIO AMMINISTRATIVO]`

- **Size**: 3 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=2)
- **Nearest heading**: (none)
- **Environment**: UFFICIO AMMINISTRATIVO
- **Risk table**: RISCHI TRASVERSALI / FATTORI PSICOLOGICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 1

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Stress da lavoro correlato | Durante le ordinarie attività lavorative. | Stress | Valutazione dello stress da lavoro correlato  | Come da documenti allegati |

#### Table 33 `[ENV: UFFICIO AMMINISTRATIVO]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: UFFICIO AMMINISTRATIVO
- **Risk table**: RISCHI TRASVERSALI / FATTORI ERGONOMICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Posti di lavoro. | Durante le ordinarie attività lavorative. | Infortuni vari. | I posti di lavoro sono stati progettati in ri | P = 2; D = 2; I = 6; MODESTO |

#### Table 34 `[ENV: UFFICIO TECNICO]`

- **Size**: 3 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=0)
- **Nearest heading**: Identificazione dell’Ambiente di Lavoro e degli Addetti - UFFICIO TECNICO
- **Environment**: UFFICIO TECNICO

**Header row:**

| `Ambiente di lavoro` | `UFFICIO TECNICO` |
| --- | --- |
| Preposto per la sicurezza | MARCHETTI LUCA |
| Descrizione Attività | DOCUMENTAZIONI VARIE SECONDO DLGS 81/08 |

#### Table 35 `[ENV: UFFICIO TECNICO]`

- **Size**: 8 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: Identificazione dell’Ambiente di Lavoro e degli Addetti - UFFICIO TECNICO
- **Environment**: UFFICIO TECNICO

**Header row:**

| `Nominativo Addetti` | `Mansione` |
| --- | --- |
| CIARAMITARO AMALIA | TITOLARE |
| MARCHETTI LUCA | IMPIEGATO-DOCENTE FORMATORE |

#### Table 36 `[ENV: UFFICIO TECNICO]`

- **Size**: 14 rows x 2 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Identificazione dei Fattori di Rischio - UFFICIO TECNICO
- **Environment**: UFFICIO TECNICO
- **Type**: Risk factor checklist (SI/NO)

**Header row:**

| `Rischi per la sicurezza` | `Rischi per la sicurezza` |
| --- | --- |
| Strutture | SI |
| Macchine | SI |

#### Table 37 `[ENV: UFFICIO TECNICO]`

- **Size**: 9 rows x 5 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=1)
- **Nearest heading**: (none)
- **Environment**: UFFICIO TECNICO
- **Risk table**: RISCHI PER LA SICUREZZA / STRUTTURE
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 7

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Presenza di ingombri ad altezza d’uomo | Durante la normale circolazione ed in condizi | Infortuni al capo | Segnalazione degli ingombri con nastro adesiv | P = 2; D = 2; I = 6; MODESTO |

#### Table 38 `[ENV: UFFICIO TECNICO]`

- **Size**: 10 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: UFFICIO TECNICO
- **Risk table**: RISCHI PER / MACCHINE
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 8

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Utilizzo di attrezzature manuali. | Durante le ordinarie attività lavorative. | Lesioni alle mani e agli arti superiori.  Fer | Utilizzo delle attrezzature secondo le dispos | P = 2; D = 2; I = 6; MODESTO |

#### Table 39 `[ENV: UFFICIO TECNICO]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=2)
- **Nearest heading**: (none)
- **Environment**: UFFICIO TECNICO
- **Risk table**: RISCHI PER / INCENDIO - ESPLOSIONI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Presenza di materiali infiammabili. | Durante le ordinarie attività lavorative | Ustioni. Incendi. Esplosioni. | Valutazione del rischio incendio ex art. 46 d | P = 2; D = 1; I = 4; ACCETTABILE |

#### Table 40 `[ENV: UFFICIO TECNICO]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: UFFICIO TECNICO
- **Risk table**: RISCHI PER / AGENTI FISICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Condizioni microclimatiche non idonee. | Durante le ordinarie attività lavorative. | Disturbi a carico dell’apparato respiratorio. | Manutenzione periodica dei sistemi di condizi | P = 2; D = 2; I = 6; MODESTO |

#### Table 41 `[ENV: UFFICIO TECNICO]`

- **Size**: 7 rows x 5 columns
- **Classification**: **MIXED** (dynamic=2, static=3)
- **Nearest heading**: (none)
- **Environment**: UFFICIO TECNICO
- **Risk table**: RISCHI TRASVERSALI / ORGANIZZAZIONE DEL LAVORO
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 5

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Nuove attrezzature di lavoro | Introduzione nel ciclo produttivo di nuove at | Infortuni vari. Tensione nervosa, irritabilit | Prima dell’inserimento nel ciclo produttivo d | P = 2; D = 2; I = 6; MODESTO |

#### Table 42 `[ENV: UFFICIO TECNICO]`

- **Size**: 3 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=2)
- **Nearest heading**: (none)
- **Environment**: UFFICIO TECNICO
- **Risk table**: RISCHI TRASVERSALI / FATTORI PSICOLOGICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 1

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Stress da lavoro correlato | Durante le ordinarie attività lavorative. | Stress | Valutazione dello stress da lavoro correlato  | Come da documenti allegati |

#### Table 43 `[ENV: UFFICIO TECNICO]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: UFFICIO TECNICO
- **Risk table**: RISCHI TRASVERSALI / FATTORI ERGONOMICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Posti di lavoro. | Durante le ordinarie attività lavorative. | Infortuni vari. | I posti di lavoro sono stati progettati in ri | P = 2; D = 2; I = 6; MODESTO |

#### Table 44 `[ENV: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]`

- **Size**: 3 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=0)
- **Nearest heading**: Identificazione dell’Ambiente di Lavoro e degli Addetti - UFFICIO COMMERCIALE E MEDICINA DEL LAVORO
- **Environment**: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO

**Header row:**

| `Ambiente di lavoro` | `UFFICIO COMMERCIALE E MEDICINA DEL LAVORO` |
| --- | --- |
| Preposto per la sicurezza | MARCHETTI LUCA |
| Descrizione Attività | ACQUISIZIONE CLIENTI E ORGANIZZAZIONE VISITE  |

#### Table 45 `[ENV: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]`

- **Size**: 4 rows x 2 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Identificazione dell’Ambiente di Lavoro e degli Addetti - UFFICIO COMMERCIALE E MEDICINA DEL LAVORO
- **Environment**: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO

**Header row:**

| `Nominativo Addetti` | `Mansione` |
| --- | --- |
| CIARAMITARO AMALIA | TITOLARE |
| ESPOSITO ELIANA | IMPIEGATA |

#### Table 46 `[ENV: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]`

- **Size**: 14 rows x 2 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Identificazione dei Fattori di Rischio - UFFICIO COMMERCIALE E MEDICINA DEL LAVORO
- **Environment**: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO
- **Type**: Risk factor checklist (SI/NO)

**Header row:**

| `Rischi per la sicurezza` | `Rischi per la sicurezza` |
| --- | --- |
| Strutture | SI |
| Macchine | SI |

#### Table 47 `[ENV: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]`

- **Size**: 9 rows x 5 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=1)
- **Nearest heading**: (none)
- **Environment**: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO
- **Risk table**: RISCHI PER LA SICUREZZA / STRUTTURE
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 7

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Presenza di ingombri ad altezza d’uomo | Durante la normale circolazione ed in condizi | Infortuni al capo | Segnalazione degli ingombri con nastro adesiv | P = 2; D = 2; I = 6; MODESTO |

#### Table 48 `[ENV: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO
- **Risk table**: RISCHI PER / MACCHINE
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Utilizzo di attrezzature manuali. | Durante le ordinarie attività lavorative. | Lesioni alle mani e agli arti superiori.  Fer | Utilizzo delle attrezzature secondo le dispos | P = 2; D = 2; I = 6; MODESTO |

#### Table 49 `[ENV: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO
- **Risk table**: RISCHI PER LA SICUREZZA / IMPIANTI ELETTRICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Contatti elettrici indiretti | Durante le ordinarie attività lavorative. | Folgorazione | Protezione meccanica delle parti di impianto  | = 2; D = 3; I = 8; GRAVE |

#### Table 50 `[ENV: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=2)
- **Nearest heading**: (none)
- **Environment**: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO
- **Risk table**: RISCHI PER / INCENDIO - ESPLOSIONI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Presenza di materiali infiammabili. | Durante le ordinarie attività lavorative | Ustioni. Incendi. Esplosioni. | Valutazione del rischio incendio ex art. 46 d | P = 2; D = 1; I = 4; ACCETTABILE |

#### Table 51 `[ENV: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO
- **Risk table**: RISCHI PER / AGENTI FISICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Condizioni microclimatiche non idonee. | Durante le ordinarie attività lavorative. | Disturbi a carico dell’apparato respiratorio. | Manutenzione periodica dei sistemi di condizi | P = 2; D = 2; I = 6; MODESTO |

#### Table 52 `[ENV: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]`

- **Size**: 7 rows x 5 columns
- **Classification**: **MIXED** (dynamic=2, static=3)
- **Nearest heading**: (none)
- **Environment**: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO
- **Risk table**: RISCHI TRASVERSALI / ORGANIZZAZIONE DEL LAVORO
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 5

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Nuove attrezzature di lavoro | Introduzione nel ciclo produttivo di nuove at | Infortuni vari. Tensione nervosa, irritabilit | Prima dell’inserimento nel ciclo produttivo d | P = 2; D = 2; I = 6; MODESTO |

#### Table 53 `[ENV: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]`

- **Size**: 3 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=2)
- **Nearest heading**: (none)
- **Environment**: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO
- **Risk table**: RISCHI TRASVERSALI / FATTORI PSICOLOGICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 1

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Stress da lavoro correlato | Durante le ordinarie attività lavorative. | Stress | Valutazione dello stress da lavoro correlato  | Come da documenti allegati |

#### Table 54 `[ENV: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: UFFICIO COMMERCIALE E MEDICINA DEL LAVORO
- **Risk table**: RISCHI TRASVERSALI / FATTORI ERGONOMICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Posti di lavoro. | Durante le ordinarie attività lavorative. | Infortuni vari. | I posti di lavoro sono stati progettati in ri | P = 2; D = 2; I = 6; MODESTO |

#### Table 55 `[ENV: SALA CORSI]`

- **Size**: 3 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=0)
- **Nearest heading**: Identificazione dell’Ambiente di Lavoro e degli Addetti - SALA CORSI
- **Environment**: SALA CORSI

**Header row:**

| `Ambiente di lavoro` | `SALA CORSI` |
| --- | --- |
| Preposto per la sicurezza | MARCHETTI LUCA |
| Descrizione Attività | CORSI DI FORMAZIONE DLGS 81/08 |

#### Table 56 `[ENV: SALA CORSI]`

- **Size**: 6 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: Identificazione dell’Ambiente di Lavoro e degli Addetti - SALA CORSI
- **Environment**: SALA CORSI

**Header row:**

| `Nominativo Addetti` | `Mansione` |
| --- | --- |
| CIARAMITARO AMALIA | TITOLARE |
| GEOM. LOVINO SIMONE | DOCENTE FORMATORE |

#### Table 57 `[ENV: SALA CORSI]`

- **Size**: 14 rows x 2 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Identificazione dei Fattori di Rischio - SALA CORSI
- **Environment**: SALA CORSI
- **Type**: Risk factor checklist (SI/NO)

**Header row:**

| `Rischi per la sicurezza` | `Rischi per la sicurezza` |
| --- | --- |
| Strutture | SI |
| Macchine | SI |

#### Table 58 `[ENV: SALA CORSI]`

- **Size**: 9 rows x 5 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=1)
- **Nearest heading**: (none)
- **Environment**: SALA CORSI
- **Risk table**: RISCHI PER LA SICUREZZA / STRUTTURE
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 7

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Presenza di ingombri ad altezza d’uomo | Durante la normale circolazione ed in condizi | Infortuni al capo | Segnalazione degli ingombri con nastro adesiv | P = 2; D = 2; I = 6; MODESTO |

#### Table 59 `[ENV: SALA CORSI]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: SALA CORSI
- **Risk table**: RISCHI PER / MACCHINE
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Utilizzo di attrezzature manuali. | Durante le ordinarie attività lavorative. | Lesioni alle mani e agli arti superiori.  Fer | Utilizzo delle attrezzature secondo le dispos | P = 2; D = 2; I = 6; MODESTO |

#### Table 60 `[ENV: SALA CORSI]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: SALA CORSI
- **Risk table**: RISCHI PER LA SICUREZZA / IMPIANTI ELETTRICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Contatti elettrici indiretti | Durante le ordinarie attività lavorative. | Folgorazione | Protezione meccanica delle parti di impianto  | = 2; D = 3; I = 8; GRAVE |

#### Table 61 `[ENV: SALA CORSI]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=2)
- **Nearest heading**: (none)
- **Environment**: SALA CORSI
- **Risk table**: RISCHI PER LA SICUREZZA / INCENDIO - ESPLOSIONI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Presenza di materiali infiammabili. | Durante le ordinarie attività lavorative | Ustioni. Incendi. Esplosioni. | Valutazione del rischio incendio ex art. 46 d | P = 2; D = 1; I = 4; ACCETTABILE |

#### Table 62 `[ENV: SALA CORSI]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: SALA CORSI
- **Risk table**: RISCHI PER / AGENTI FISICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Condizioni microclimatiche non idonee. | Durante le ordinarie attività lavorative. | Disturbi a carico dell’apparato respiratorio. | Manutenzione periodica dei sistemi di condizi | P = 2; D = 2; I = 6; MODESTO |

#### Table 63 `[ENV: SALA CORSI]`

- **Size**: 7 rows x 5 columns
- **Classification**: **MIXED** (dynamic=2, static=3)
- **Nearest heading**: (none)
- **Environment**: SALA CORSI
- **Risk table**: RISCHI TRASVERSALI / ORGANIZZAZIONE DEL LAVORO
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 5

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Nuove attrezzature di lavoro | Introduzione nel ciclo produttivo di nuove at | Infortuni vari. Tensione nervosa, irritabilit | Prima dell’inserimento nel ciclo produttivo d | P = 2; D = 2; I = 6; MODESTO |

#### Table 64 `[ENV: SALA CORSI]`

- **Size**: 3 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=2)
- **Nearest heading**: (none)
- **Environment**: SALA CORSI
- **Risk table**: RISCHI TRASVERSALI / FATTORI PSICOLOGICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 1

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Stress da lavoro correlato | Durante le ordinarie attività lavorative. | Stress | Valutazione dello stress da lavoro correlato  | Come da documenti allegati |

#### Table 65 `[ENV: SALA CORSI]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: SALA CORSI
- **Risk table**: RISCHI TRASVERSALI / FATTORI ERGONOMICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Posti di lavoro. | Durante le ordinarie attività lavorative. | Infortuni vari. | I posti di lavoro sono stati progettati in ri | P = 2; D = 2; I = 6; MODESTO |

#### Table 66 `[ENV: MAGAZZINO]`

- **Size**: 3 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=0)
- **Nearest heading**: Identificazione dell’Ambiente di Lavoro e degli Addetti - MAGAZZINO
- **Environment**: MAGAZZINO

**Header row:**

| `Ambiente di lavoro` | `MAGAZZINO` |
| --- | --- |
| Preposto per la sicurezza | MARCHETTI LUCA |
| Descrizione Attività | STOCCAGGIO ATTREZZATURE ANTINCENDIO E MEZZI A |

#### Table 67 `[ENV: MAGAZZINO]`

- **Size**: 10 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: Identificazione dell’Ambiente di Lavoro e degli Addetti - MAGAZZINO
- **Environment**: MAGAZZINO

**Header row:**

| `Nominativo Addetti` | `Mansione` |
| --- | --- |
| CIARAMITARO AMALIA | TITOLARE |
| GEOM. LOVINO SIMONE | DOCENTE FORMATORE |

#### Table 68 `[ENV: MAGAZZINO]`

- **Size**: 14 rows x 2 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Identificazione dei Fattori di Rischio - MAGAZZINO
- **Environment**: MAGAZZINO
- **Type**: Risk factor checklist (SI/NO)

**Header row:**

| `Rischi per la sicurezza` | `Rischi per la sicurezza` |
| --- | --- |
| Strutture | SI |
| Macchine | SI |

#### Table 69 `[ENV: MAGAZZINO]`

- **Size**: 15 rows x 5 columns
- **Classification**: **MIXED** (dynamic=1, static=1)
- **Nearest heading**: (none)
- **Environment**: MAGAZZINO
- **Risk table**: RISCHI PER LA SICUREZZA / STRUTTURE
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 13

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Presenza di ingombri ad altezza d’uomo | Durante la normale circolazione ed in condizi | Infortuni al capo | Segnalazione degli ingombri con nastro adesiv | P = 2; D = 2; I = 6; MODESTO |

#### Table 70 `[ENV: MAGAZZINO]`

- **Size**: 12 rows x 5 columns
- **Classification**: **MIXED** (dynamic=1, static=2)
- **Nearest heading**: (none)
- **Environment**: MAGAZZINO
- **Risk table**: RISCHI PER LA SICUREZZA / MACCHINE
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 10

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Attrezzature di lavoro - Organi di avviamento | Durante l’utilizzo delle attrezzature di lavo | Lesioni. Traumi, contusioni. | Protezione degli organi di avviamento e di co | P = 2; D = 3; I = 8; GRAVE |

#### Table 71 `[ENV: MAGAZZINO]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: MAGAZZINO
- **Risk table**: RISCHI PER LA SICUREZZA / IMPIANTI ELETTRICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Contatti elettrici indiretti | Durante le ordinarie attività lavorative. | Folgorazione | Protezione meccanica delle parti di impianto  | = 2; D = 3; I = 8; GRAVE |

#### Table 72 `[ENV: MAGAZZINO]`

- **Size**: 6 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=2)
- **Nearest heading**: (none)
- **Environment**: MAGAZZINO
- **Risk table**: RISCHI PER / INCENDIO - ESPLOSIONI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 4

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Presenza di materiali infiammabili. | Durante le ordinarie attività lavorative | Ustioni. Incendi. Esplosioni. | Valutazione del rischio incendio ex art. 46 d | P = 2; D = 1; I = 4; ACCETTABILE |

#### Table 73 `[ENV: MAGAZZINO]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: MAGAZZINO
- **Risk table**: RISCHI PER LA SALUTE / AGENTI FISICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Condizioni microclimatiche non idonee. | Durante le ordinarie attività lavorative. | Disturbi a carico dell’apparato respiratorio. | Manutenzione periodica dei sistemi di condizi | P = 2; D = 2; I = 6; MODESTO |

#### Table 74 `[ENV: MAGAZZINO]`

- **Size**: 6 rows x 5 columns
- **Classification**: **MIXED** (dynamic=1, static=3)
- **Nearest heading**: (none)
- **Environment**: MAGAZZINO
- **Risk table**: RISCHI TRASVERSALI / ORGANIZZAZIONE DEL LAVORO
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 4

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Nuove attrezzature di lavoro | Introduzione nel ciclo produttivo di nuove at | Infortuni vari. Tensione nervosa, irritabilit | Prima dell’inserimento nel ciclo produttivo d | P = 2; D = 2; I = 6; MODESTO |

#### Table 75 `[ENV: MAGAZZINO]`

- **Size**: 3 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=2)
- **Nearest heading**: (none)
- **Environment**: MAGAZZINO
- **Risk table**: RISCHI TRASVERSALI / FATTORI PSICOLOGICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 1

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Stress da lavoro correlato | Durante le ordinarie attività lavorative. | Stress | Valutazione dello stress da lavoro correlato  | Come da documenti allegati |

#### Table 76 `[ENV: MAGAZZINO]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: MAGAZZINO
- **Risk table**: RISCHI TRASVERSALI / FATTORI ERGONOMICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Posti di lavoro. | Durante le ordinarie attività lavorative. | Infortuni vari. | I posti di lavoro sono stati progettati in ri | P = 2; D = 2; I = 6; MODESTO |

#### Table 77 `[ENV: AREA BREAK]`

- **Size**: 3 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=3, static=0)
- **Nearest heading**: Identificazione dell’Ambiente di Lavoro e degli Addetti - AREA BREAK
- **Environment**: AREA BREAK

**Header row:**

| `Ambiente di lavoro` | `AREA BREAK` |
| --- | --- |
| Preposto per la sicurezza | MARCHETTI LUCA |
| Descrizione Attività | RISTORO DIPENDENTI |

#### Table 78 `[ENV: AREA BREAK]`

- **Size**: 15 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: Identificazione dell’Ambiente di Lavoro e degli Addetti - AREA BREAK
- **Environment**: AREA BREAK

**Header row:**

| `Nominativo Addetti` | `Mansione` |
| --- | --- |
| CIARAMITARO AMALIA | TITOLARE |
| SORMANI ANNALISA | IMPIEGATA |

#### Table 79 `[ENV: AREA BREAK]`

- **Size**: 14 rows x 2 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Identificazione dei Fattori di Rischio - AREA BREAK
- **Environment**: AREA BREAK
- **Type**: Risk factor checklist (SI/NO)

**Header row:**

| `Rischi per la sicurezza` | `Rischi per la sicurezza` |
| --- | --- |
| Strutture | SI |
| Macchine | NO |

#### Table 80 `[ENV: AREA BREAK]`

- **Size**: 7 rows x 5 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=1)
- **Nearest heading**: (none)
- **Environment**: AREA BREAK
- **Risk table**: RISCHI PER LA SICUREZZA / STRUTTURE
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 5

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Presenza di ingombri ad altezza d’uomo | Durante la normale circolazione ed in condizi | Infortuni al capo | Segnalazione degli ingombri con nastro adesiv | P = 2; D = 2; I = 6; MODESTO |

#### Table 81 `[ENV: AREA BREAK]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: AREA BREAK
- **Risk table**: RISCHI PER LA SICUREZZA / IMPIANTI ELETTRICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Contatti elettrici indiretti | Durante le ordinarie attività lavorative. | Folgorazione | Protezione meccanica delle parti di impianto  | = 2; D = 3; I = 8; GRAVE |

#### Table 82 `[ENV: AREA BREAK]`

- **Size**: 6 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=2)
- **Nearest heading**: (none)
- **Environment**: AREA BREAK
- **Risk table**: RISCHI PER LA SICUREZZA / INCENDIO - ESPLOSIONI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 4

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Presenza di materiali infiammabili. | Durante le ordinarie attività lavorative | Ustioni. Incendi. Esplosioni. | Valutazione del rischio incendio ex art. 46 d | P = 2; D = 1; I = 4; ACCETTABILE |

#### Table 83 `[ENV: AREA BREAK]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: AREA BREAK
- **Risk table**: RISCHI PER LA SALUTE / AGENTI FISICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Condizioni microclimatiche non idonee. | Durante le ordinarie attività lavorative. | Disturbi a carico dell’apparato respiratorio. | Manutenzione periodica dei sistemi di condizi | P = 2; D = 2; I = 6; MODESTO |

#### Table 84 `[ENV: AREA BREAK]`

- **Size**: 6 rows x 5 columns
- **Classification**: **MIXED** (dynamic=1, static=3)
- **Nearest heading**: (none)
- **Environment**: AREA BREAK
- **Risk table**: RISCHI TRASVERSALI / ORGANIZZAZIONE DEL LAVORO
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 4

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Nuove attrezzature di lavoro | Introduzione nel ciclo produttivo di nuove at | Infortuni vari. Tensione nervosa, irritabilit | Prima dell’inserimento nel ciclo produttivo d | P = 2; D = 2; I = 6; MODESTO |

#### Table 85 `[ENV: AREA BREAK]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: AREA BREAK
- **Risk table**: RISCHI TRASVERSALI / FATTORI ERGONOMICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Posti di lavoro. | Durante le ordinarie attività lavorative. | Infortuni vari. | I posti di lavoro sono stati progettati in ri | P = 2; D = 2; I = 6; MODESTO |

#### Table 86 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 3 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=0)
- **Nearest heading**: Identificazione dell’Ambiente di Lavoro e degli Addetti - STRUTTURE PRESSO CLIENTI
- **Environment**: STRUTTURE PRESSO CLIENTI

**Header row:**

| `Ambiente di lavoro` | `STRUTTURE PRESSO CLIENTI` |
| --- | --- |
| Preposto per la sicurezza | MARCHETTI LUCA |
| Descrizione Attività | MANUTENZIONE E FORNITURA ATTREZZATURE ANTINCE |

#### Table 87 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 10 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: Identificazione dell’Ambiente di Lavoro e degli Addetti - STRUTTURE PRESSO CLIENTI
- **Environment**: STRUTTURE PRESSO CLIENTI

**Header row:**

| `Nominativo Addetti` | `Mansione` |
| --- | --- |
| GEOM. LOVINO SIMONE | DOCENTE FORMATORE |
| MARCHETTI LUCA | IMPIEGATO-DOCENTE FORMATORE |

#### Table 88 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 14 rows x 2 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Identificazione dei Fattori di Rischio - STRUTTURE PRESSO CLIENTI
- **Environment**: STRUTTURE PRESSO CLIENTI
- **Type**: Risk factor checklist (SI/NO)

**Header row:**

| `Rischi per la sicurezza` | `Rischi per la sicurezza` |
| --- | --- |
| Strutture | SI |
| Macchine | SI |

#### Table 89 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 20 rows x 5 columns
- **Classification**: **MIXED** (dynamic=1, static=1)
- **Nearest heading**: (none)
- **Environment**: STRUTTURE PRESSO CLIENTI
- **Risk table**: RISCHI PER LA SICUREZZA / STRUTTURE
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 18

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Presenza di ingombri ad altezza d’uomo | Durante la normale circolazione ed in condizi | Infortuni al capo | Segnalazione degli ingombri con nastro adesiv | P = 2; D = 2; I = 6; MODESTO |

#### Table 90 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 14 rows x 5 columns
- **Classification**: **MIXED** (dynamic=1, static=1)
- **Nearest heading**: (none)
- **Environment**: STRUTTURE PRESSO CLIENTI
- **Risk table**: RISCHI PER LA SICUREZZA / MACCHINE
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 12

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Ascensori e montacarichi. | Durante le ordinarie attività lavorative. | Caduta di carichi e/o persone dall’alto. Trau | Utilizzo dei mezzi in conformità alle prescri | = 2; D = 3; I = 8; GRAVE |

#### Table 91 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 8 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=2)
- **Nearest heading**: (none)
- **Environment**: STRUTTURE PRESSO CLIENTI
- **Risk table**: RISCHI PER LA SICUREZZA / INCENDIO - ESPLOSIONI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 6

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Presenza di materiali infiammabili. | Durante le ordinarie attività lavorative | Ustioni. Incendi. Esplosioni. | Valutazione del rischio incendio ex art. 46 d | P = 2; D = 1; I = 4; ACCETTABILE |

#### Table 92 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 8 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: STRUTTURE PRESSO CLIENTI
- **Risk table**: RISCHI PER LA SALUTE / AGENTI FISICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 6

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Condizioni microclimatiche non idonee. | Durante le ordinarie attività lavorative. | Disturbi a carico dell’apparato respiratorio. | Manutenzione periodica dei sistemi di condizi | P = 2; D = 2; I = 6; MODESTO |

#### Table 93 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 6 rows x 5 columns
- **Classification**: **MIXED** (dynamic=2, static=3)
- **Nearest heading**: (none)
- **Environment**: STRUTTURE PRESSO CLIENTI
- **Risk table**: RISCHI TRASVERSALI / ORGANIZZAZIONE DEL LAVORO
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 4

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Nuove attrezzature di lavoro | Introduzione nel ciclo produttivo di nuove at | Infortuni vari. Tensione nervosa, irritabilit | Prima dell’inserimento nel ciclo produttivo d | P = 2; D = 2; I = 6; MODESTO |

#### Table 94 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 4 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=2)
- **Nearest heading**: (none)
- **Environment**: STRUTTURE PRESSO CLIENTI
- **Risk table**: RISCHI TRASVERSALI / FATTORI PSICOLOGICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 2

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Stress da lavoro correlato | Durante le ordinarie attività lavorative. | Stress | Valutazione dello stress da lavoro correlato  | Come da documenti allegati |

#### Table 95 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 5 rows x 5 columns
- **Classification**: **STATIC** (dynamic=0, static=1)
- **Nearest heading**: (none)
- **Environment**: STRUTTURE PRESSO CLIENTI
- **Risk table**: RISCHI TRASVERSALI / FATTORI ERGONOMICI
- **Columns**: PERICOLO | CONDIZIONI | RISCHIO | MISURE+DPI | I=P+2*D
- **Data rows**: 3

**Column headers (row 1):**

| `PERICOLO` | `CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE` | `RISCHIO` | `MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E ` | `I = P+ 2*D` |
| --- | --- | --- | --- | --- |
| Posti di lavoro. | Durante le ordinarie attività lavorative. | Infortuni vari. | I posti di lavoro sono stati progettati in ri | P = 2; D = 2; I = 6; MODESTO |

#### Table 96 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 14 rows x 3 columns
- **Classification**: **MIXED** (dynamic=1, static=1)
- **Nearest heading**: Elenco Mansioni che espongono i lavoratori a rischi specifici (art. 28 co. 2/f D.Lgs. 81/08 e s.m.i.)
- **Environment**: STRUTTURE PRESSO CLIENTI

**Header row:**

| `Nominativo` | `Mansione` | `Rischio specifico` |
| --- | --- | --- |
| SORMANI ANNALISA | IMPIEGATA | Lavoro ai VDT (es. DATA ENTRY).  (Titolo VII  |
| MARCHETTI LUCA | IMPIEGATO-DOCENTE FORMATORE | Utilizzo di Dispositivi  di Protezione indivi |

#### Table 97 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 6 rows x 3 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=0)
- **Nearest heading**: Dispositivi di Protezione Individuale (DPI)
- **Environment**: STRUTTURE PRESSO CLIENTI

**Header row:**

| `NOMINATIVO LAVORATORE` | `MARCHETTI LUCA` | `MARCHETTI LUCA` |
| --- | --- | --- |
| DESCRIZIONE | MARCA MODELLO | NOTE |
| Caschi di protezione per l'industria (caschi  |  | Dispositivi di protezione della testa |

#### Table 98 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 7 rows x 3 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: Dispositivi di Protezione Individuale (DPI)
- **Environment**: STRUTTURE PRESSO CLIENTI

**Header row:**

| `NOMINATIVO LAVORATORE` | `CIARCELLUTI MARIANNA` | `CIARCELLUTI MARIANNA` |
| --- | --- | --- |
| DESCRIZIONE | MARCA MODELLO | NOTE |
| Caschi di protezione per l'industria (caschi  |  | Dispositivi di protezione della testa |

#### Table 99 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 6 rows x 3 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: (none)
- **Environment**: STRUTTURE PRESSO CLIENTI

**Header row:**

| `NOMINATIVO LAVORATORE` | `GEOM. LOVINO SIMONE` | `GEOM. LOVINO SIMONE` |
| --- | --- | --- |
| DESCRIZIONE | MARCA MODELLO | NOTE |
| Caschi di protezione per l'industria (caschi  |  | Dispositivi di protezione della testa |

#### Table 100 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 11 rows x 3 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: (none)
- **Environment**: STRUTTURE PRESSO CLIENTI

**Header row:**

| `NOMINATIVO LAVORATORE` | `VENTURA VITTORIO` | `VENTURA VITTORIO` |
| --- | --- | --- |
| DESCRIZIONE | MARCA MODELLO | NOTE |
| Caschi di protezione per l'industria (caschi  |  | Dispositivi di protezione della testa |

#### Table 101 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 6 rows x 3 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: (none)
- **Environment**: STRUTTURE PRESSO CLIENTI

**Header row:**

| `NOMINATIVO LAVORATORE` | `SIVIERO MATTEO` | `SIVIERO MATTEO` |
| --- | --- | --- |
| DESCRIZIONE | MARCA MODELLO | NOTE |
| Guanti contro le aggressioni meccaniche (perf |  | Dispositivi di protezione delle mani e delle  |

#### Table 102 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 9 rows x 3 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: (none)
- **Environment**: STRUTTURE PRESSO CLIENTI

**Header row:**

| `NOMINATIVO LAVORATORE` | `FUMAGALLI ALESSIO` | `FUMAGALLI ALESSIO` |
| --- | --- | --- |
| DESCRIZIONE | MARCA MODELLO | NOTE |
| Caschi di protezione per l'industria (caschi  |  | Dispositivi di protezione della testa |

#### Table 103 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 8 rows x 3 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: (none)
- **Environment**: STRUTTURE PRESSO CLIENTI

**Header row:**

| `NOMINATIVO LAVORATORE` | `FRROKU PETRIT` | `FRROKU PETRIT` |
| --- | --- | --- |
| DESCRIZIONE | MARCA MODELLO | NOTE |
| Caschi di protezione per l'industria (caschi  |  | Dispositivi di protezione della testa |

#### Table 104 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 7 rows x 3 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: (none)
- **Environment**: STRUTTURE PRESSO CLIENTI

**Header row:**

| `NOMINATIVO LAVORATORE` | `INVERNIZZI MARCO` | `INVERNIZZI MARCO` |
| --- | --- | --- |
| DESCRIZIONE | MARCA MODELLO | NOTE |
| Guanti contro le aggressioni meccaniche (perf |  | Dispositivi di protezione delle mani e delle  |

#### Table 105 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 8 rows x 4 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: Scopo della segnaletica di sicurezza
- **Environment**: STRUTTURE PRESSO CLIENTI

**Header row:**

| `Colore` | `Forma` | `Significato o Scopo` | `Indicazioni e precisazioni` |
| --- | --- | --- | --- |
| Rosso |  | Segnali di divieto | Atteggiamenti Pericolosi |
| Rosso |  | Pericolo-Allarme | Alt, arresto dispositivi di interruzione di e |

#### Table 106 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 6 rows x 4 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Scopo della segnaletica di sicurezza
- **Environment**: STRUTTURE PRESSO CLIENTI

**Header row:**

| `` | `Cartelli di divieto` | `` | `Cartelli antincendio` |
| --- | --- | --- | --- |
|  | Forma rotonda Pittogramma nero su fondo bianc |  | Forma quadrata o rettangolare Pittogramma bia |
|  | Cartelli di avvertimento |  | Cartelli di prescrizione |

#### Table 107 `[ENV: STRUTTURE PRESSO CLIENTI]`

- **Size**: 18 rows x 4 columns
- **Classification**: **DYNAMIC** (dynamic=2, static=1)
- **Nearest heading**: Programma di Formazione, Informazione ed Addestramento
- **Environment**: STRUTTURE PRESSO CLIENTI

**Header row:**

| `Destinatari` | `Attività di informazione/formazione/addestram` | `Svolta` | `Periodicità (*)` |
| --- | --- | --- | --- |
| RSPP | Corso RSPP (art. 31-32-33-34 D.Lgs. n. 81/200 | I verbali di formazione ed informazione dei l | Come stabilito dal D.Lgs. 81/2008 e s.m.i. |
| Addetti | Corso Addetti Prevenzione Incendi (D.M. 10/03 | I verbali di formazione ed informazione dei l | Ogni cinque anni |

### Tables in PARTE IV

#### Table 108

- **Size**: 5 rows x 2 columns
- **Classification**: **DYNAMIC** (dynamic=4, static=0)
- **Nearest heading**: Programma e Procedure delle misure per garantire il miglioramento nel tempo dei livelli di sicurezza

**Header row:**

| `Azienda` | `N2O SRL` |
| --- | --- |
| Sede Legale | VIA DEI CHIOSI 4 |
| Sede Legale | GORGONZOLA (MI) |

#### Table 109

- **Size**: 3 rows x 5 columns
- **Classification**: **UNKNOWN** (dynamic=0, static=0)
- **Nearest heading**: Programma e Procedure di attuazione delle Misure di Miglioramento

**Header row:**

| `Misure di miglioramento` | `Procedure per l’attuazione delle misure di mi` | `Risorse necessarie per l’attuazione` | `Responsabile` | `Tempi di attuazione` |
| --- | --- | --- | --- | --- |
| PROVVEDERE A FARE CERTIFICATO MESSA A TERRA | FISSARE APPUNTAMENTO CON TECNICO | TECNICO | DATORE DI LAVORO | A BREVE |
| INTEGRARE ALLARME SONORO PER PIANO EMERGENZA | ACQUISTARE ALLARMI SONORI | PC | PREPOSTO | A BREVE |

#### Table 110

- **Size**: 2 rows x 3 columns
- **Classification**: **DYNAMIC** (dynamic=1, static=0)
- **Nearest heading**: GORGONZOLA (MI), lì 18 11 2025

**Header row:**

| `Il Datore di Lavoro (CIARAMITARO AMALIA)` | `` | `Il Responsabile del S.P.P. (CIARAMITARO AMALI` |
| --- | --- | --- |
| Il Medico Competente (DOTT.SSA MARINA MORARI) |  | Per consultazione Il Rappresentante dei Lavor |

## 5. Environment Risk Assessment Block (Template Pattern)

Part III contains **7 work environments**, each following an identical repeating template structure. This is the heart of the generation engine — the block must be instantiated once per `Ambiente` entity.

### 5.1 Environments in Template

1. **UFFICIO AMMINISTRATIVO** — para #598, 171 elements, 10 tables
2. **UFFICIO TECNICO** — para #759, 176 elements, 10 tables
3. **UFFICIO COMMERCIALE E MEDICINA DEL LAVORO** — para #925, 189 elements, 11 tables
4. **SALA CORSI** — para #1103, 189 elements, 11 tables
5. **MAGAZZINO** — para #1281, 172 elements, 11 tables
6. **AREA BREAK** — para #1442, 127 elements, 9 tables
7. **STRUTTURE PRESSO CLIENTI** — para #1560, 249 elements, 22 tables

### 5.2 Environment Block Template Structure

Analyzed from the first environment (UFFICIO AMMINISTRATIVO, 171 elements). Each environment block contains:

1. **Identification section** (`Identificazione dell'Ambiente di Lavoro e degli Addetti - {AMBIENTE}`)
   - Environment details table (name, floor, area, characteristics)
   - Workers assigned table (names, roles, presence)

2. **Risk assessment section** (`Identificazione dei Fattori di Rischio - {AMBIENTE}`)
   - Risk factor checklist table (which risks apply)
   - `spec` header paragraph (risk specification sheets intro)
   - Multiple risk factor assessment tables (one per risk category, with D/P/I scores, measures, DPI)

**Detailed section breakdown (first environment):**

  **[a titolo 1] Identificazione dell’Ambiente di Lavoro e degli Addetti - UFFICIO AMMINISTRATIVO**

    - TABLE 24 (3x2, DYNAMIC): `Ambiente di lavoro | UFFICIO AMMINISTRATIVO`
    - TABLE 25 (3x2, UNKNOWN): `Nominativo Addetti | Mansione`

  **[a titolo 1] Identificazione dei Fattori di Rischio - UFFICIO AMMINISTRATIVO**

    - **CHECKLIST TABLE 26** (14x2): Risk factors with SI/NO indicators
    - **SPEC HEADER**: Schede Specifiche con l’Individuazione dei pericoli, delle condizioni di impiego
    - **RISK TABLE 27** (10x5): RISCHI PER LA SICUREZZA / STRUTTURE (8 risk entries)
    - **RISK TABLE 28** (10x5): RISCHI PER LA SICUREZZA / MACCHINE (8 risk entries)
    - **RISK TABLE 29** (5x5): RISCHI PER LA SICUREZZA / INCENDIO - ESPLOSIONI (3 risk entries)
    - **RISK TABLE 30** (5x5): RISCHI PER LA SALUTE / AGENTI FISICI (3 risk entries)
    - **RISK TABLE 31** (7x5): RISCHI TRASVERSALI / ORGANIZZAZIONE DEL LAVORO (5 risk entries)
    - **RISK TABLE 32** (3x5): RISCHI TRASVERSALI / FATTORI PSICOLOGICI (1 risk entries)
    - **RISK TABLE 33** (5x5): RISCHI TRASVERSALI / FATTORI ERGONOMICI (3 risk entries)

### 5.3 Tables per Environment (Comparison)

| Environment | Total Tables | Table Indices |
|-------------|-------------|---------------|
| UFFICIO AMMINISTRATIVO | 10 | 24, 25, 26, 27, 28, 29, 30, 31, 32, 33 |
| UFFICIO TECNICO | 10 | 34, 35, 36, 37, 38, 39, 40, 41, 42, 43 |
| UFFICIO COMMERCIALE E MEDICINA DEL LAVORO | 11 | 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| SALA CORSI | 11 | 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65 |
| MAGAZZINO | 11 | 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76 |
| AREA BREAK | 9 | 77, 78, 79, 80, 81, 82, 83, 84, 85 |
| STRUTTURE PRESSO CLIENTI | 22 | 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107 |

### 5.4 Risk Factor Table Patterns

Each environment block contains a standard set of risk assessment tables. The structure (from the first environment):

**Standard environment block tables:**

| Position | Table Type | Columns | Description |
|----------|-----------|---------|-------------|
| 1 | Environment ID | 2 | `Ambiente di lavoro`, `Preposto`, `Descrizione Attivita` |
| 2 | Workers List | 2 | `Nominativo Addetti`, `Mansione` |
| 3 | Risk Checklist | 2 | Risk factor names with SI/NO presence indicators |
| 4+ | Risk Assessment | 5 | `PERICOLO`, `CONDIZIONI`, `RISCHIO`, `MISURE`, `I=P+2*D` |

**Risk assessment tables per environment (first env as reference):**

| # | Category | Subcategory | Data Rows | Table Size |
|---|----------|-------------|-----------|------------|
| 1 | RISCHI PER LA SICUREZZA | STRUTTURE | 8 | 10x5 |
| 2 | RISCHI PER LA SICUREZZA | MACCHINE | 8 | 10x5 |
| 3 | RISCHI PER LA SICUREZZA | INCENDIO - ESPLOSIONI | 3 | 5x5 |
| 4 | RISCHI PER LA SALUTE | AGENTI FISICI | 3 | 5x5 |
| 5 | RISCHI TRASVERSALI | ORGANIZZAZIONE DEL LAVORO | 5 | 7x5 |
| 6 | RISCHI TRASVERSALI | FATTORI PSICOLOGICI | 1 | 3x5 |
| 7 | RISCHI TRASVERSALI | FATTORI ERGONOMICI | 3 | 5x5 |

**Risk assessment table column structure (all tables identical):**

| Column | Header | Content | Data Type |
|--------|--------|---------|-----------|
| 0 | PERICOLO | Hazard description | Free text, from risk catalog |
| 1 | CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE | Exposure conditions | Free text |
| 2 | RISCHIO | Risk/harm description | Free text |
| 3 | MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E DPI ADOTTATI | Prevention measures and DPI | Free text |
| 4 | I = P + 2*D | Risk index calculation | Formula: `P = N; D = N; I = N; LEVEL` |

**Cross-environment table count comparison:**

| Position | UFFICIO AMMI | UFFICIO TECN | UFFICIO COMM | SALA CORSI | MAGAZZINO | AREA BREAK | STRUTTURE PR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 3x2 | 3x2 | 3x2 | 3x2 | 3x2 | 3x2 | 3x2 |
| 2 | 3x2 | 8x2 | 4x2 | 6x2 | 10x2 | 15x2 | 10x2 |
| 3 | 14x2 (checklist) | 14x2 (checklist) | 14x2 (checklist) | 14x2 (checklist) | 14x2 (checklist) | 14x2 (checklist) | 14x2 (checklist) |
| 4 | 10x5 (STRUTTURE) | 9x5 (STRUTTURE) | 9x5 (STRUTTURE) | 9x5 (STRUTTURE) | 15x5 (STRUTTURE) | 7x5 (STRUTTURE) | 20x5 (STRUTTURE) |
| 5 | 10x5 (MACCHINE) | 10x5 (MACCHINE) | 5x5 (MACCHINE) | 5x5 (MACCHINE) | 12x5 (MACCHINE) | 5x5 (IMPIANTI E) | 14x5 (MACCHINE) |
| 6 | 5x5 (INCENDIO -) | 5x5 (INCENDIO -) | 5x5 (IMPIANTI E) | 5x5 (IMPIANTI E) | 5x5 (IMPIANTI E) | 6x5 (INCENDIO -) | 8x5 (INCENDIO -) |
| 7 | 5x5 (AGENTI FIS) | 5x5 (AGENTI FIS) | 5x5 (INCENDIO -) | 5x5 (INCENDIO -) | 6x5 (INCENDIO -) | 5x5 (AGENTI FIS) | 8x5 (AGENTI FIS) |
| 8 | 7x5 (ORGANIZZAZ) | 7x5 (ORGANIZZAZ) | 5x5 (AGENTI FIS) | 5x5 (AGENTI FIS) | 5x5 (AGENTI FIS) | 6x5 (ORGANIZZAZ) | 6x5 (ORGANIZZAZ) |
| 9 | 3x5 (FATTORI PS) | 3x5 (FATTORI PS) | 7x5 (ORGANIZZAZ) | 7x5 (ORGANIZZAZ) | 6x5 (ORGANIZZAZ) | 5x5 (FATTORI ER) | 4x5 (FATTORI PS) |
| 10 | 5x5 (FATTORI ER) | 5x5 (FATTORI ER) | 3x5 (FATTORI PS) | 3x5 (FATTORI PS) | 3x5 (FATTORI PS) | - | 5x5 (FATTORI ER) |
| 11 | - | - | 5x5 (FATTORI ER) | 5x5 (FATTORI ER) | 5x5 (FATTORI ER) | - | 14x3 |
| 12 | - | - | - | - | - | - | 6x3 |
| 13 | - | - | - | - | - | - | 7x3 |
| 14 | - | - | - | - | - | - | 6x3 |
| 15 | - | - | - | - | - | - | 11x3 |
| 16 | - | - | - | - | - | - | 6x3 |
| 17 | - | - | - | - | - | - | 9x3 |
| 18 | - | - | - | - | - | - | 8x3 |
| 19 | - | - | - | - | - | - | 7x3 |
| 20 | - | - | - | - | - | - | 8x4 |
| 21 | - | - | - | - | - | - | 6x4 |
| 22 | - | - | - | - | - | - | 18x4 |

## 6. Dynamic Content Map

All locations containing company-specific data that the generation engine must populate from the data model.

### 6.1 Detection Codes

| Code | Meaning | Example Patterns |
|------|---------|-----------------|
| COMPANY_NAME | Company/business name | N2O, Bar Caffetteria, Residenza Pace |
| ADDRESS | Street address | Via Manzoni, Piazza Roma |
| DATE | Date value | 15/03/2024, 01.01.2025 |
| PERSON_NAME | Person with title prefix | Sig. Marchetti, Dott. Rossi |
| CODICE_FISCALE | Italian tax code (16 chars) | MRCGGG80A01F205X |
| RISK_SCORE | Computed risk index | I = 7 |
| NUMERIC_DATA | Measurable quantities | 15 dipendenti, 200 mq, 40 ore |

### 6.2 Dynamic Paragraphs

**18 paragraphs** with company-specific content:

| Para # | Style | Data Types | Preview |
|--------|-------|------------|---------|
| 140 | `a` | COMPANY_NAME, ADDRESS | La sede operativa di N2O SRL si trova nel comune di Gessate (MI) in Via Monza 10 |
| 192 | `a` | ADDRESS | La società svolge la sua attività in Via Monza 107/30 a Gessate (MI). |
| 196 | `a` | DATE | In base all'Ordinanza del Presidente del Consigli dei Ministri n. 3274/2003, agg |
| 200 | `a` | COMPANY_NAME | La N2O srl offre un servizio di consulenza, a tutti i tipi di attività, sulla no |
| 227 | `a` | ADDRESS | Il Datore di Lavoro ai sensi dell’art. 18 co. 1 lettera b) del D.Lgs. 81/08 e s. |
| 253 | `a` | ADDRESS | Le porte situate sul percorso delle vie di emergenza sono opportunamente contras |
| 484 | `a puntato` | DATE | il rischio incendio, ai sensi del D.M. 10.03.1998. La valutazione è stata condot |
| 536 | `a tabella centrato` | RISK_SCORE | I = 2*D + P |
| 1714 | `a` | ADDRESS | Quando, anche a seguito della valutazione effettuata in conformità dell'articolo |
| 1719 | `a puntato` | ADDRESS | fornire indicazioni relative alle uscite di sicurezza o ai mezzi di soccorso o d |
| 1748 | `a` | ADDRESS | Cartelli per indicazione del percorso per uscita di emergenza |
| 1817 | `a` | ADDRESS | Il RSPP conserva le copie delle leggi e regolamenti applicate dalla Organizzazio |
| 1842 | `a` | ADDRESS | Il DL con la collaborazione di RSPP e DRG interessati, contatta i candidati medi |
| 1889 | `a puntato` | DATE | di quanto definito dagli artt. 31-32-33-34-36-37-73-77-164-169-177-184-195-227-2 |
| 1992 | `a` | ADDRESS | Nel corso della riunione verranno individuati anche: |
| 2417 | `a puntato` | ADDRESS | nomina del responsabile del servizio di prevenzione e protezione, degli incarica |
| 2431 | `a` | COMPANY_NAME, ADDRESS | Il/la sottoscritto/a, CIARAMITARO AMALIA in qualità di Datore di Lavoro della N2 |
| 2435 | `a` | ADDRESS | che il procedimento sulla valutazione dei rischi ex art. 17 del D.Lgs. n. 81/200 |

### 6.3 Dynamic Table Cells

**269 table cells** with company-specific content, grouped by table:

**Table 0** (5x2, DYNAMIC) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 0 | 1 | COMPANY_NAME | N2O SRL |
| 1 | 1 | ADDRESS | VIA DEI CHIOSI 4 |
| 3 | 1 | ADDRESS | VIA MONZA 107/30 |

**Table 1** (7x3, DYNAMIC) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 1 | 2 | DATE | 27/03/2024 |
| 2 | 2 | DATE | 02/09/2024 |
| 3 | 2 | DATE | 02/12/2024 |
| 4 | 2 | DATE | 13/05/2025 |
| 5 | 2 | DATE | 04/11/2025 |
| 6 | 2 | DATE | 18/11/2025 |

**Table 3** (5x2, DYNAMIC) — Presentazione dell’azienda:

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 0 | 1 | COMPANY_NAME | N2O SRL |
| 1 | 1 | ADDRESS | VIA DEI CHIOSI 4 |
| 3 | 1 | ADDRESS | VIA MONZA 107/30 |

**Table 4** (12x2, DYNAMIC) — Anagrafica Aziendale:

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 0 | 1 | COMPANY_NAME | N2O SRL |
| 1 | 1 | DATE | 46.69.94 - Commercio all'ingrosso di articoli antincendio e  |
| 2 | 1 | ADDRESS | VIA DEI CHIOSI 4 |
| 4 | 1 | ADDRESS | VIA MONZA 107/30 |

**Table 5** (15x5, DYNAMIC) — Dati occupazionali:

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 1 | 3 | CODICE_FISCALE | CRMMLA90M70G273Y |
| 2 | 3 | CODICE_FISCALE | SRMNLS75B57F119X |
| 3 | 3 | CODICE_FISCALE | MRCLCU93S03M052M |
| 4 | 3 | CODICE_FISCALE | CRCMNN97L67F119Y |
| 5 | 0 | PERSON_NAME | GEOM. LOVINO SIMONE |
| 5 | 3 | CODICE_FISCALE | LVNSMN90R16I577C |
| 6 | 3 | CODICE_FISCALE | SPSLNE74L50F704G |
| 7 | 3 | CODICE_FISCALE | NCRDNS84A49F119R |
| 8 | 3 | CODICE_FISCALE | BSCSFN88E59F119A |
| 9 | 3 | CODICE_FISCALE | VNTVTR81D14F205T |
| 10 | 3 | CODICE_FISCALE | SVRMTT88E10F205R |
| 11 | 3 | CODICE_FISCALE | FMGLSS78R13F704X |
| 12 | 3 | CODICE_FISCALE | FRRPRT87R01Z100K |
| 13 | 3 | CODICE_FISCALE | NVRMRC86M27A794M |
| 14 | 3 | CODICE_FISCALE | MNANDR01C11I577S |

**Table 18** (5x2, DYNAMIC) — Relazione sulla valutazione dei rischi per la sicu:

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 0 | 1 | COMPANY_NAME | N2O SRL |
| 1 | 1 | ADDRESS | VIA DEI CHIOSI 4 |
| 3 | 1 | ADDRESS | VIA MONZA 107/30 |

**Table 19** (27x2, MIXED) — Definizioni:

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 19 | 1 | ADDRESS | soluzioni organizzative o procedurali coerenti con la normat |

**Table 20** (5x3, STATIC) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 1 | 0 | RISK_SCORE | I = 3-4 |
| 2 | 0 | RISK_SCORE | I = 5-6 |
| 3 | 0 | RISK_SCORE | I = 7-8 |
| 4 | 0 | RISK_SCORE | I = 9-12 |

**Table 23** (5x2, DYNAMIC) — Individuazione dei rischi, delle misure di prevenz:

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 0 | 1 | COMPANY_NAME | N2O SRL |
| 1 | 1 | ADDRESS | VIA DEI CHIOSI 4 |
| 3 | 1 | ADDRESS | VIA MONZA 107/30 |

**Table 27** (10x5, DYNAMIC [UFFICIO AMMINISTRATIVO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 5 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 6 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 7 | 3 | ADDRESS | Divieto di depositare nemmeno in via provvisoria alcun mater |
| 7 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 8 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 9 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 28** (10x5, STATIC [UFFICIO AMMINISTRATIVO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 7 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |
| 8 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 9 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 29** (5x5, STATIC [UFFICIO AMMINISTRATIVO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 3 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 4 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |

**Table 30** (5x5, STATIC [UFFICIO AMMINISTRATIVO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 31** (7x5, MIXED [UFFICIO AMMINISTRATIVO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 33** (5x5, STATIC [UFFICIO AMMINISTRATIVO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 35** (8x2, DYNAMIC [UFFICIO TECNICO]) — Identificazione dell’Ambiente di Lavoro e degli Ad:

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 4 | 0 | PERSON_NAME | GEOM. LOVINO SIMONE |

**Table 37** (9x5, DYNAMIC [UFFICIO TECNICO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 5 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 6 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 7 | 3 | ADDRESS | Divieto di depositare nemmeno in via provvisoria alcun mater |
| 7 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 8 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 38** (10x5, STATIC [UFFICIO TECNICO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 7 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |
| 8 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 9 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 39** (5x5, STATIC [UFFICIO TECNICO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 3 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 4 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |

**Table 40** (5x5, STATIC [UFFICIO TECNICO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 41** (7x5, MIXED [UFFICIO TECNICO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 43** (5x5, STATIC [UFFICIO TECNICO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 47** (9x5, DYNAMIC [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 5 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 6 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 7 | 3 | ADDRESS | Divieto di depositare nemmeno in via provvisoria alcun mater |
| 7 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 8 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 48** (5x5, STATIC [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 49** (5x5, STATIC [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 50** (5x5, STATIC [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 3 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 4 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |

**Table 51** (5x5, STATIC [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 52** (7x5, MIXED [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 54** (5x5, STATIC [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 56** (6x2, DYNAMIC [SALA CORSI]) — Identificazione dell’Ambiente di Lavoro e degli Ad:

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 0 | PERSON_NAME | GEOM. LOVINO SIMONE |

**Table 58** (9x5, DYNAMIC [SALA CORSI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 5 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 6 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 7 | 3 | ADDRESS | Divieto di depositare nemmeno in via provvisoria alcun mater |
| 7 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 8 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 59** (5x5, STATIC [SALA CORSI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 60** (5x5, STATIC [SALA CORSI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 61** (5x5, STATIC [SALA CORSI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 3 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 4 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |

**Table 62** (5x5, STATIC [SALA CORSI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 63** (7x5, MIXED [SALA CORSI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 65** (5x5, STATIC [SALA CORSI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 67** (10x2, DYNAMIC [MAGAZZINO]) — Identificazione dell’Ambiente di Lavoro e degli Ad:

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 0 | PERSON_NAME | GEOM. LOVINO SIMONE |

**Table 69** (15x5, MIXED [MAGAZZINO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 5 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 6 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 7 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 8 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 9 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 10 | 3 | ADDRESS | Divieto di depositare nemmeno in via provvisoria alcun mater |
| 10 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 11 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 12 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 13 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 14 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 70** (12x5, MIXED [MAGAZZINO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 3; I = 8; GRAVE |
| 3 | 4 | RISK_SCORE | P = 2; D = 3; I = 8; GRAVE |
| 4 | 4 | RISK_SCORE | P = 2; D = 3; I = 8; GRAVE |
| 5 | 4 | RISK_SCORE | P = 2; D = 3; I = 8; GRAVE |
| 6 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |
| 7 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |
| 8 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |
| 9 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 10 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 11 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 71** (5x5, STATIC [MAGAZZINO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 72** (6x5, STATIC [MAGAZZINO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 3 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 4 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 5 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |

**Table 73** (5x5, STATIC [MAGAZZINO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 74** (6x5, MIXED [MAGAZZINO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 5 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 76** (5x5, STATIC [MAGAZZINO]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 78** (15x2, DYNAMIC [AREA BREAK]) — Identificazione dell’Ambiente di Lavoro e degli Ad:

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 5 | 0 | PERSON_NAME | GEOM. LOVINO SIMONE |

**Table 80** (7x5, DYNAMIC [AREA BREAK]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 5 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 6 | 3 | ADDRESS | Divieto di depositare nemmeno in via provvisoria alcun mater |
| 6 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 81** (5x5, STATIC [AREA BREAK]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 82** (6x5, STATIC [AREA BREAK]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 3 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 4 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 5 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |

**Table 83** (5x5, STATIC [AREA BREAK]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 84** (6x5, MIXED [AREA BREAK]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 85** (5x5, STATIC [AREA BREAK]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 87** (10x2, DYNAMIC [STRUTTURE PRESSO CLIENTI]) — Identificazione dell’Ambiente di Lavoro e degli Ad:

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 1 | 0 | PERSON_NAME | GEOM. LOVINO SIMONE |

**Table 89** (20x5, MIXED [STRUTTURE PRESSO CLIENTI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 5 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 6 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 7 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 8 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 9 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 10 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 11 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 12 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 13 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 14 | 3 | ADDRESS | Divieto di depositare nemmeno in via provvisoria alcun mater |
| 14 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 15 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 16 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 17 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 18 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 19 | 4 | RISK_SCORE | P = 2; D = 3; I = 8; GRAVE |

**Table 90** (14x5, MIXED [STRUTTURE PRESSO CLIENTI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |
| 3 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |
| 4 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |
| 5 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |
| 6 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 7 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 8 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 11 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |
| 12 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 13 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 91** (8x5, STATIC [STRUTTURE PRESSO CLIENTI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 3 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 4 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |
| 5 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |

**Table 92** (8x5, STATIC [STRUTTURE PRESSO CLIENTI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 5 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 6 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 7 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 93** (6x5, MIXED [STRUTTURE PRESSO CLIENTI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 5 | 4 | RISK_SCORE | = 2; D = 3; I = 8; GRAVE |

**Table 94** (4x5, STATIC [STRUTTURE PRESSO CLIENTI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 3 | 4 | RISK_SCORE | P = 2; D = 1; I = 4; ACCETTABILE |

**Table 95** (5x5, STATIC [STRUTTURE PRESSO CLIENTI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 2 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 3 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |
| 4 | 4 | RISK_SCORE | P = 2; D = 2; I = 6; MODESTO |

**Table 96** (14x3, MIXED [STRUTTURE PRESSO CLIENTI]) — Elenco Mansioni che espongono i lavoratori a risch:

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 4 | 0 | PERSON_NAME | GEOM. LOVINO SIMONE |

**Table 99** (6x3, DYNAMIC [STRUTTURE PRESSO CLIENTI]) — (no heading):

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 0 | 1 | PERSON_NAME | GEOM. LOVINO SIMONE |
| 0 | 2 | PERSON_NAME | GEOM. LOVINO SIMONE |

**Table 107** (18x4, DYNAMIC [STRUTTURE PRESSO CLIENTI]) — Programma di Formazione, Informazione ed Addestram:

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 1 | 1 | ADDRESS, DATE | Corso RSPP (art. 31-32-33-34 D.Lgs. n. 81/2008 e s.m.i.) |
| 2 | 1 | ADDRESS, DATE | Corso Addetti Prevenzione Incendi (D.M. 10/03/1998) |
| 3 | 1 | ADDRESS | Corso primo soccorso (D.M. 388/03) |
| 4 | 1 | ADDRESS | Corso RLS (art. 37 co. 10 D.Lgs. n. 81/2008 e s.m.i.) |

**Table 108** (5x2, DYNAMIC) — Programma e Procedure delle misure per garantire i:

| Row | Col | Data Types | Preview |
|-----|-----|------------|---------|
| 0 | 1 | COMPANY_NAME | N2O SRL |
| 1 | 1 | ADDRESS | VIA DEI CHIOSI 4 |
| 3 | 1 | ADDRESS | VIA MONZA 107/30 |

## 7. Repeated Template Patterns

Headings that repeat across environments (after normalizing environment names to `{AMBIENTE}`):

| Heading Template | Occurrences |
|-----------------|-------------|
| Documentazione Collegata | 8 |
| Identificazione dell’Ambiente di Lavoro e degli Addetti - {AMBIENTE} | 7 |
| Identificazione dei Fattori di Rischio - {AMBIENTE} | 7 |

**Environment-specific heading patterns:**

- `Identificazione dell'Ambiente di Lavoro e degli Addetti - {AMBIENTE}` (x7)
- `Identificazione dei Fattori di Rischio - {AMBIENTE}` (x7)

**`spec` style paragraphs** repeat 7 times (one per environment for risk specification sheets).

## 8. Static Sections (Copy Verbatim)

These sections contain standard legal/methodological text that does not change between companies.

### 8.1 PARTE II (Methodology) — Entirely Static

- **227 paragraphs, 5 tables** (232 elements)
- Paragraph range: #359 to #585
- Content: Legal definitions, risk methodology, D.Lgs. 81/2008 references, I=2D+P formula
- **Engine action**: Copy verbatim, no data substitution needed

### 8.2 PARTE IV Static Procedures

Each procedure section in Part IV is self-contained. Most are fully static with minor dynamic fields:

- **Programma e Procedure di attuazione delle Misure di Miglioramento** *(#1794)*  — `STATIC (copy verbatim)`
- **Gestione Leggi e Regolamenti** *(#1800)*  — `STATIC (copy verbatim)`
- **Gestione Sorveglianza sanitaria** *(#1831)*  — `STATIC (copy verbatim)`
- **Gestione Informazione, Formazione ed Addestramento** *(#1884)*  — `MIXED (has dynamic fields)`
- **Riunione Periodica** *(#1962)*  — `STATIC (copy verbatim)`
- **Gestione degli Infortuni** *(#2013)*  — `STATIC (copy verbatim)`
- **Gestione comportamenti scorretti dei lavoratori** *(#2115)*  — `STATIC (copy verbatim)`
- **Gestione DPI** *(#2159)*  — `STATIC (copy verbatim)`
- **Gestione Infrastrutture** *(#2235)*  — `STATIC (copy verbatim)`
- **Gestione Lavoratori appartenenti a gruppi particolarmente sensibili al rischio** *(#2253)*  — `STATIC (copy verbatim)`
- **Gestione Acquisti** *(#2380)*  — `STATIC (copy verbatim)`
- **Gestione delle lavorazioni affidate in appalto** *(#2390)*  — `STATIC (copy verbatim)`
- **Dichiarazione del Datore di Lavoro** *(#2429)*  — `MIXED (has dynamic fields)`

### 8.3 Static Tables List

All tables classified as fully static:

| Table # | Size | Part | Context |
|---------|------|------|---------|
| 20 | 5x3 | PARTE II | (none) |
| 28 | 10x5 | PARTE III | (none) |
| 29 | 5x5 | PARTE III | (none) |
| 30 | 5x5 | PARTE III | (none) |
| 32 | 3x5 | PARTE III | (none) |
| 33 | 5x5 | PARTE III | (none) |
| 38 | 10x5 | PARTE III | (none) |
| 39 | 5x5 | PARTE III | (none) |
| 40 | 5x5 | PARTE III | (none) |
| 42 | 3x5 | PARTE III | (none) |
| 43 | 5x5 | PARTE III | (none) |
| 48 | 5x5 | PARTE III | (none) |
| 49 | 5x5 | PARTE III | (none) |
| 50 | 5x5 | PARTE III | (none) |
| 51 | 5x5 | PARTE III | (none) |
| 53 | 3x5 | PARTE III | (none) |
| 54 | 5x5 | PARTE III | (none) |
| 59 | 5x5 | PARTE III | (none) |
| 60 | 5x5 | PARTE III | (none) |
| 61 | 5x5 | PARTE III | (none) |
| 62 | 5x5 | PARTE III | (none) |
| 64 | 3x5 | PARTE III | (none) |
| 65 | 5x5 | PARTE III | (none) |
| 71 | 5x5 | PARTE III | (none) |
| 72 | 6x5 | PARTE III | (none) |
| 73 | 5x5 | PARTE III | (none) |
| 75 | 3x5 | PARTE III | (none) |
| 76 | 5x5 | PARTE III | (none) |
| 81 | 5x5 | PARTE III | (none) |
| 82 | 6x5 | PARTE III | (none) |
| 83 | 5x5 | PARTE III | (none) |
| 85 | 5x5 | PARTE III | (none) |
| 91 | 8x5 | PARTE III | (none) |
| 92 | 8x5 | PARTE III | (none) |
| 94 | 4x5 | PARTE III | (none) |
| 95 | 5x5 | PARTE III | (none) |

## 9. Data Field Mapping — Generation Engine Requirements

Summary of data fields required by each document section, mapped to the data model entities.

### Part I: Company Presentation (All Dynamic)

| Section | Para # | Data Required | Source Entity |
|---------|--------|--------------|---------------|
| Anagrafica Aziendale | #135 | Company name, address, CAP, city, province, P.IVA, CF, ATECO code, phone, email, PEC | `Azienda` |
| Dati occupazionali | #138 | Employee count by category (dirigenti, preposti, impiegati, operai), contract types | `Azienda.dati_occupazionali` |
| Descrizione azienda | #139 | Free-text company/activity description (AI-generated) | `Azienda.descrizione` |
| Organizzazione Sicurezza | #203 | DdL, RSPP, RLS, MC names, appointment dates, training dates | `Persona[]` by role |
| Ambienti di Lavoro | #233 | Environment list with dimensions, floor, characteristics | `Ambiente[]` |
| Servizi Igienico-Assistenziali | #292 | Toilets, changing rooms, break areas | `Ambiente[]` (filtered by type) |
| Macchine/Attrezzature | #308 | Equipment with make, model, serial, CE marking, year | `Attrezzatura[]` |
| Sostanze Chimiche | #339 | Chemical list from SDS (AI-extracted) | `SostanzaChimica[]` |
| Fattori di Pericolo | #345 | Hazard checklist with presence indicators per environment | `FattorePericolo[]` |

### Part III: Per-Environment Risk Assessment (Repeating Dynamic Block)

**For each `Ambiente` (work environment), generate the following:**

| Data Field | Source Entity | Notes |
|-----------|--------------|-------|
| Environment name | `Ambiente.nome` | Used in heading: `Identificazione... - {nome}` |
| Floor/piano | `Ambiente.piano` | In identification table |
| Area (mq) | `Ambiente.area_mq` | In identification table |
| Characteristics | `Ambiente.caratteristiche` | Free text in identification table |
| Workers assigned | `Persona[]` per `Ambiente` | Names, roles, hours of presence |
| Risk factors present | `RischioAmbiente[]` | Boolean checklist per risk category |
| D (Danno) score per risk | `ValutazioneRischio.danno` | 1-4 scale |
| P (Probabilita) score per risk | `ValutazioneRischio.probabilita` | 1-4 scale |
| I (Indice) per risk | Computed: `2*D + P` | Range 3-12 |
| Risk level classification | Derived from I | Accettabile/Modesto/Grave/Gravissimo |
| Prevention measures | `MisuraPrevenzione[]` per risk | Text descriptions |
| Protection measures | `MisuraProtezione[]` per risk | Text descriptions |
| DPI assigned | `DPI[]` per risk factor | DPI types and quantities |

### Part IV: Procedures (Mostly Static)

| Section | Dynamic Fields | Source |
|---------|---------------|--------|
| DPI Inventory | DPI list per mansione, assignment table | `DPI[]`, `Mansione[]` |
| Segnaletica | Company-specific signage per environment | `Segnaletica[]`, `Ambiente[]` |
| Training Program | Schedule, employee assignments, dates | `Formazione[]`, `Persona[]` |
| Dichiarazione DdL | Employer name, date, signature block | `Persona` (DdL role), current date |

## 10. Full Element Sequence

Complete ordered sequence of all **2556** body elements. This is the master build order for the generation engine.

Legend: `P` = paragraph, `T` = table, `H0`-`H3` = heading level. Empty paragraphs omitted.

  1. [P] #1 `Body Text 3` — DOCUMENTO ELABORATO
  2. [P] #2 `Body Text 3` — SUGLI ESITI DELLA
  3. [P] #3 `Body Text 3` — VALUTAZIONE DEI RISCHI
  4. [P] #4 `Body Text 3` — ex art. 17, comma 1, lettera a) ed art. 28 del D.Lgs. 81/2008 e s.m.i. (D.Lgs. 1
  7. [**T0**] 5x2 DYNAMIC — ...
  10. [**T1**] 7x3 DYNAMIC — ...
  13. [**T2**] 2x1 UNKNOWN — ...
  18. [**H1**] #15 `a titolo 1` — Indice
  19. [P] #16 `toc 2` — Indice	3
  20. [P] #17 `toc 2` — Premessa	6
  21. [P] #18 `toc 1` — PARTE I	7
  22. [P] #19 `toc 1` — Presentazione dell’azienda	7
  23. [P] #20 `toc 2` — Anagrafica Aziendale	8
  24. [P] #21 `toc 2` — Dati occupazionali	9
  25. [P] #22 `toc 2` — Descrizione dell’azienda e dell’attività	11
  26. [P] #23 `toc 2` — Organizzazione Aziendale della Sicurezza	13
  27. [P] #24 `toc 2` — Ambienti di Lavoro	15
  28. [P] #25 `toc 2` — Servizi Igienico – Assistenziali	18
  29. [P] #26 `toc 2` — Elenco Macchine, Attrezzature ed Impianti	19
  30. [P] #27 `toc 2` — Elenco sostanze, prodotti e preparati chimici	21
  31. [P] #28 `toc 2` — Elenco Fattori di Pericolo	22
  32. [P] #29 `toc 1` — PARTE II	25
  33. [P] #30 `toc 1` — Relazione sulla valutazione dei rischi per la sicurezza e la salute durante il l
  34. [P] #31 `toc 2` — Definizioni	26
  35. [P] #32 `toc 2` — Metodologia	29
  36. [P] #33 `toc 3` — Generalità	29
  37. [P] #34 `toc 3` — Individuazione dei Soggetti Esposti	30
  38. [P] #35 `toc 3` — Identificazione dei Pericoli	31
  39. [P] #36 `toc 3` — Individuazione dei Rischi di Esposizione	32
  40. [P] #37 `toc 3` — Definizione delle misure di prevenzione e di protezione attuate e dei dispositiv
  41. [P] #38 `toc 3` — Classificazione dei rischi	34
  42. [P] #39 `toc 3` — Individuazione delle procedure per l’attuazione delle misure	37
  43. [P] #40 `toc 3` — Redazione del Documento di Valutazione dei Rischi	37
  44. [P] #41 `toc 3` — Aggiornamento del documento	37
  45. [P] #42 `toc 1` — PARTE III	38
  46. [P] #43 `toc 1` — Individuazione dei rischi, delle misure di prevenzione e di protezione e dei dis
  47. [P] #44 `toc 2` — Elenco Mansioni che espongono i lavoratori a rischi specifici (art. 28 co. 2/f D
  48. [P] #45 `toc 2` — Dispositivi di Protezione Individuale (DPI)	149
  49. [P] #46 `toc 2` — Segnaletica di sicurezza	153
  50. [P] #47 `toc 2` — Principale segnaletica da apporre negli ambienti di lavoro	155
  51. [P] #48 `toc 2` — Programma di Formazione, Informazione ed Addestramento	158
  52. [P] #49 `toc 1` — PARTE IV	159
  53. [P] #50 `toc 1` — Programma e Procedure delle misure per garantire il miglioramento nel tempo dei 
  54. [P] #51 `toc 2` — Programma e Procedure di attuazione delle Misure di Miglioramento	160
  55. [P] #52 `toc 2` — Gestione Leggi e Regolamenti	161
  56. [P] #53 `toc 3` — Responsabilità	161
  57. [P] #54 `toc 3` — Ricerca delle leggi	161
  58. [P] #55 `toc 3` — Diffusione ed utilizzo di leggi e regolamenti	161
  59. [P] #56 `toc 3` — Archiviazione	161
  60. [P] #57 `toc 2` — Gestione Sorveglianza sanitaria	162
  61. [P] #58 `toc 3` — Verifica delle necessità della sorveglianza sanitaria	162
  62. [P] #59 `toc 3` — Nomina del MC	162
  63. [P] #60 `toc 3` — Revoca della Nomina	163
  64. [P] #61 `toc 3` — Attività Del MC	163
  65. [P] #62 `toc 3` — Documentazione Collegata	163
  66. [P] #63 `toc 2` — Gestione Informazione, Formazione ed Addestramento	164
  67. [P] #64 `toc 3` — Programmazione della Formazione, Informazione ed Addestramento	164
  68. [P] #65 `toc 3` — Segnalazione delle necessità Formative od Informative	164
  69. [P] #66 `toc 3` — Criteri di Erogazione delle Attività di Informazione, Formazione ed Addestrament
  70. [P] #67 `toc 3` — Esecuzione e Registrazione delle Attività	166
  71. [P] #68 `toc 3` — Documentazione Collegata	166
  72. [P] #69 `toc 2` — Riunione Periodica	167
  73. [P] #70 `toc 3` — Convocazione	167
  74. [P] #71 `toc 3` — Verbalizzazione e Divulgazione	168
  75. [P] #72 `toc 2` — Gestione degli Infortuni	169
  76. [P] #73 `toc 3` — Segnalazione	169
  77. [P] #74 `toc 3` — Indagine	169
  78. [P] #75 `toc 3` — Commissione di indagine	170
  79. [P] #76 `toc 3` — Relazione Tecnica di Valutazione Finale	171
  80. [P] #77 `toc 3` — Registro degli Infortuni e Denuncia Infortunio	172
  81. [P] #78 `toc 2` — Gestione comportamenti scorretti dei lavoratori	173
  82. [P] #79 `toc 3` — Cause di Richiamo Lavoratori	173
  83. [P] #80 `toc 3` — Richiamo verbale	173
  84. [P] #81 `toc 3` — Lettera di Richiamo	174
  85. [P] #82 `toc 3` — Sanzione Disciplinare	174
  86. [P] #83 `toc 3` — Possibilità di risposta da parte del lavoratore alla sanzione disciplinare	174
  87. [P] #84 `toc 2` — Gestione DPI	175
  88. [P] #85 `toc 3` — Acquisizione di DPI	175
  89. [P] #86 `toc 3` — Destinazione dei DPI	175
  90. [P] #87 `toc 3` — Gestione di casi di inadeguatezza ed intolleranza ai DPI	176
  91. [P] #88 `toc 3` — Modalità di utilizzazione e mantenimento dei DPI	176
  92. [P] #89 `toc 3` — informazione, formazione e addestramento	177
  93. [P] #90 `toc 3` — Documentazione Collegata	177
  94. [P] #91 `toc 2` — Gestione Infrastrutture	178
  95. [P] #92 `toc 3` — Documentazione Collegata	178
  96. [P] #93 `toc 2` — Gestione Lavoratori appartenenti a gruppi particolarmente sensibili al rischio	1
  97. [P] #94 `toc 3` — Lavoratrici gestanti, puerpere o in periodo di allattamento (D.Lgs. 151/2001)	17
  98. [P] #95 `toc 3` — Lavoratori minori (D.Lgs. 345/99)	181
  99. [P] #96 `toc 3` — Lavoratori diversamente abili	183
  100. [P] #97 `toc 3` — Lavoratori stranieri	183
  101. [P] #98 `toc 2` — Gestione Acquisti	184
  102. [P] #99 `toc 2` — Gestione delle lavorazioni affidate in appalto	185
  103. [P] #100 `toc 3` — D.U.V.R.I.	185
  104. [P] #101 `toc 3` — Informazioni sui requisiti tecnico professionali delle ditte appaltatrici	186
  105. [P] #102 `toc 2` — Dichiarazione del Datore di Lavoro	187
  107. [**H1**] #104 `a titolo 1` — Premessa
  108. [P] #105 `a` — Il presente documento rappresenta attuazione dell’obbligo previsto per il datore
  109. [P] #106 `a` — La valutazione di cui all’articolo 17, comma 1, lettera a), anche nella scelta d
  110. [P] #107 `a` — Il presente documento in accordo con quanto previsto dal D.Lgs. 81/2008 e s.m.i.
  112. [P] #109 `a puntato` — una relazione sulla valutazione di tutti i rischi per la sicurezza e la salute d
  113. [P] #110 `a puntato` — l’indicazione delle misure di prevenzione e di protezione attuate e dei disposit
  114. [P] #111 `a puntato` — il programma delle misure ritenute opportune per garantire il miglioramento nel 
  115. [P] #112 `a puntato` — l’individuazione delle procedure per l’attuazione delle misure da realizzare, no
  116. [P] #113 `a puntato` — l’indicazione del nominativo del responsabile del servizio di prevenzione e prot
  117. [P] #114 `a puntato` — l’individuazione delle mansioni che eventualmente espongono i lavoratori a risch
  119. [P] #116 `a` — La valutazione dei rischi verrà immediatamente rielaborata in occasione di modif

--- **PARTE I** (element #130) ---

  130. [**H0**] #127 `a Titolo parte` — PARTE I
  131. [**H0**] #128 `a titolo parte 2` — Presentazione dell’azienda
  136. [**T3**] 5x2 DYNAMIC — Presentazione dell’azienda
  139. [**H1**] #135 `a titolo 1` — Anagrafica Aziendale
  141. [**T4**] 12x2 DYNAMIC — Anagrafica Aziendale
  143. [**H1**] #138 `a titolo 1` — Dati occupazionali
  144. [**T5**] 15x5 DYNAMIC — Dati occupazionali
  145. [**H1**] #139 `a titolo 1` — Descrizione dell’azienda e dell’attività
  146. [P] #140 `a` — La sede operativa di N2O SRL si trova nel comune di Gessate (MI) in Via Monza 10
  147. [P] #141 `a` — L'orario di lavoro dell'attività è:
  148. [P] #142 `a` — - da lunedì a venerdì orari 08:30-13:00 / 14:00-19:00
  167. [P] #161 `a` — LOCALI
  169. [P] #163 `a` — Metratura totale circa mq 1000
  171. [P] #165 `a` — Servizi igienici     Presenti
  172. [P] #166 `a` — Uffici                    Presenti
  173. [P] #167 `a` — Magazzino          Presente
  174. [P] #168 `a` — Area Break          Presente
  175. [P] #169 `a` — Sala corsi            Presente
  179. [P] #173 `a` — CONTESTO TERRITORIALE
  198. [P] #192 `a` — La società svolge la sua attività in Via Monza 107/30 a Gessate (MI).
  199. [P] #193 `a` — L'immobile è inserito in un contesto di zona industriale dedicato alle attività 
  200. [P] #194 `a` — Non sono presenti rischi territoriali naturali che potrebbero interessare l'area
  201. [P] #195 `a` — La classificazione sismica del territorio nazionale ha introdotto normative spec
  202. [P] #196 `a` — In base all'Ordinanza del Presidente del Consigli dei Ministri n. 3274/2003, agg
  203. [P] #197 `a` — Accelerazione con probabilità di superamento del 10% in 50 anni: ag ≥0,07.
  205. [P] #199 `a` — DESCRIZIONE ATTIVITA' LAVORATIVA
  206. [P] #200 `a` — La N2O srl offre un servizio di consulenza, a tutti i tipi di attività, sulla no
  207. [P] #201 `a` — inoltre, si occupa di fornire attrezzature antincendio e loro manutenzione.
  209. [**H1**] #203 `a titolo 1` — Organizzazione Aziendale della Sicurezza
  212. [**T6**] 2x1 UNKNOWN — Organizzazione Aziendale della Sicurezza
  218. [**T7**] 2x1 UNKNOWN — Organizzazione Aziendale della Sicurezza
  219. [**T8**] 2x1 DYNAMIC — Organizzazione Aziendale della Sicurezza
  226. [**T9**] 2x1 UNKNOWN — ...
  237. [P] #227 `a` — Il Datore di Lavoro ai sensi dell’art. 18 co. 1 lettera b) del D.Lgs. 81/08 e s.
  240. [**T10**] 5x2 DYNAMIC — ...
  243. [**T11**] 5x2 DYNAMIC — ...
  245. [**H1**] #233 `a titolo 1` — Ambienti di Lavoro
  246. [P] #234 `a` — Le lavorazioni si svolgono nella seguente aree di lavoro:
  247. [**T12**] 8x2 DYNAMIC — Ambienti di Lavoro
  249. [P] #236 `a` — Ambienti di lavoro
  250. [P] #237 `a` — (All. IV D.Lgs. 81/2008 e s.m.i.)
  251. [P] #238 `a` — I limiti minimi per altezza, cubatura e superficie dei locali destinati al lavor
  252. [P] #239 `a` — Lo spazio destinato al lavoratore nel posto di lavoro è tale da consentire il no
  253. [P] #240 `a` — Gli ambienti di lavoro sono ben difesi contro gli agenti atmosferici, e provvist
  255. [P] #242 `a` — Pareti e soffitti
  256. [P] #243 `a` — Le pareti e i soffitti dei locali di lavoro sono tinteggiate con colori chiari e
  258. [P] #245 `a` — Pavimenti
  259. [P] #246 `a` — Il pavimento dei locali di lavoro è realizzato in materiale resistente e di faci
  260. [P] #247 `a` — Il pavimento risulta essere sgombro da materiale che possa ostacolare la circola
  262. [P] #249 `a` — Porte e finestre
  263. [P] #250 `a` — Le porte dei locali di lavoro rispettano le prescrizioni della normativa vigente
  266. [P] #253 `a` — Le porte situate sul percorso delle vie di emergenza sono opportunamente contras
  267. [P] #254 `a` — Le finestre sono di facile utilizzo e rispettano tutte le misure di sicurezza pe
  268. [P] #255 `a` — Le finestre risultano essere di facile pulizia e non presentano rischi per i lav
  270. [P] #257 `a` — Scale fisse
  271. [P] #258 `a` — Le scale fisse a gradini, destinate al normale accesso agli ambienti di lavoro, 
  273. [P] #260 `a` — Arredi, attrezzature e piani li lavoro
  274. [P] #261 `a` — La scelta degli arredi e delle attrezzature, nonché la loro forma e le loro cara
  276. [P] #263 `a` — Soppalchi
  277. [P] #264 `a` — I soppalchi garantiscono la rispondenza di tutte le caratteristiche previste per
  278. [P] #265 `a` — I soppalchi destinati a deposito presentano, in un punto ben visibile, la chiara
  280. [P] #267 `a` — Scaffalature
  281. [P] #268 `a` — Le scaffalature garantiscono la rispondenza di tutte le caratteristiche previste
  289. [P] #276 `a` — Aerazione naturale e artificiale dei locali di lavoro
  290. [P] #277 `a` — L’aria dei locali di lavoro è convenientemente e frequentemente rinnovata con me
  291. [P] #278 `a` — Le postazioni di lavoro sono tali da non permettere che durante l’utilizzo dell’
  292. [P] #279 `a` — Gli stessi impianti sono periodicamente sottoposti a controlli, manutenzione, pu
  295. [P] #282 `a` — Illuminazione naturale e artificiale dei locali di lavoro
  296. [P] #283 `a` — I luoghi di lavoro dispongono di sufficiente luce naturale. Tutti i locali e i l
  297. [P] #284 `a` — Gli ambienti, i posti di lavoro ed i passaggi sono illuminati con luce naturale 
  298. [P] #285 `a` — Gli impianti di illuminazione dei locali di lavoro e delle vie di circolazione s
  299. [P] #286 `a` — Le superfici vetrate illuminanti ed i mezzi di illuminazione artificiale sono te
  302. [P] #289 `a` — Illuminazione sussidiaria
  303. [P] #290 `a` — Sono presenti nei luoghi di lavoro dispositivi di illuminazione sussidiaria che 
  304. [P] #291 `a` — Detti mezzi sono tenuti in posti noti al personale, conservati in costante effic
  305. [**H1**] #292 `a titolo 1` — Servizi Igienico – Assistenziali
  307. [P] #294 `a` — Gabinetti e lavabi
  308. [P] #295 `a` — Gabinetti e lavabi sono a disposizione dei lavoratori e degli avventori, colloca
  309. [P] #296 `a` — I lavabi erogano acqua calda e sono forniti di mezzi detergenti e per asciugarsi
  310. [P] #297 `a` — Per uomini e donne sono previsti gabinetti separati.
  312. [P] #299 `a` — All’interno dei servizi igienici è presente una Cassetta di Pronto Soccorso, da 
  316. [P] #303 `a` — Pulizia dei locali di servizio
  317. [P] #304 `a` — Le installazioni e gli arredi destinati ai bagni ed in genere ai servizi di igie
  318. [P] #305 `a` — I lavoratori usano con cura e proprietà i locali, le installazioni e gli arredi.
  321. [**H1**] #308 `a titolo 1` — Elenco Macchine, Attrezzature ed Impianti
  322. [P] #309 `a` — Le attrezzature di lavoro messe a disposizione dei lavoratori sono conformi alle
  323. [P] #310 `a` — Le attrezzature di lavoro costruite in assenza di disposizioni legislative e reg
  325. [P] #312 `a` — All'atto della scelta delle attrezzature di lavoro, il datore di lavoro prende i
  327. [P] #314 `a puntato` — le condizioni e le caratteristiche specifiche del lavoro da svolgere;
  328. [P] #315 `a puntato` — i rischi presenti nell’ambiente di lavoro;
  329. [P] #316 `a puntato` — i rischi derivanti dall’impiego delle attrezzature stesse
  330. [P] #317 `a puntato` — i rischi derivanti da interferenze con le altre attrezzature già in uso.
  332. [P] #319 `a` — Il datore di lavoro, al fine di ridurre al minimo i rischi connessi all’uso dell
  334. [P] #321 `a` — Il datore di lavoro ha adottate le misure necessarie affinché:
  336. [P] #323 `a puntato` — le attrezzature di lavoro:
  337. [P] #324 `a puntato` — vengono installate ed utilizzate in conformità alle istruzioni d’uso;
  338. [P] #325 `a puntato` — siano oggetto di idonea manutenzione al fine di garantire nel tempo la permanenz
  339. [P] #326 `a puntato` — siano curati la tenuta e l’aggiornamento del registro di controllo delle attrezz
  341. [P] #328 `a` — Il datore di lavoro ha adottato le misure necessarie affinché il posto di lavoro
  349. [P] #336 `a` — Si riporta l’elenco delle macchine, attrezzature ed impianti utilizzate nell’att
  351. [**T13**] 16x3 UNKNOWN — ...
  353. [**H1**] #339 `a titolo 1` — Elenco sostanze, prodotti e preparati chimici
  355. [P] #341 `a` — Si riporta nel seguito l’elenco sostanze, prodotti e preparati chimici utilizzat
  358. [**T14**] 5x3 UNKNOWN — Elenco sostanze, prodotti e preparati ch
  360. [**H1**] #345 `a titolo 1` — Elenco Fattori di Pericolo
  361. [**H3**] #346 `a titolo 3` — N.B. Gli elenchi seguenti sono da intendersi indicativi e non esaustivi
  362. [**T15**] 33x2 UNKNOWN — N.B. Gli elenchi seguenti sono da intend
  367. [**T16**] 18x2 UNKNOWN — N.B. Gli elenchi seguenti sono da intend
  369. [**T17**] 16x2 UNKNOWN — N.B. Gli elenchi seguenti sono da intend

--- **PARTE II** (element #377) ---

  377. [**H0**] #359 `a Titolo parte` — PARTE II
  378. [**H0**] #360 `a titolo parte 2` — Relazione sulla valutazione dei rischi per la sicurezza e la salute durante il l
  384. [**T18**] 5x2 DYNAMIC — Relazione sulla valutazione dei rischi p
  385. [**H1**] #366 `a titolo 1` — Definizioni
  386. [**T19**] 27x2 MIXED — Definizioni
  387. [**H1**] #367 `a titolo 1` — Metodologia
  388. [**H2**] #368 `a titolo 2` — Generalità
  389. [P] #369 `a` — Il DL, tramite il SPP, in collaborazione con il RSPP, gli ASPP ed il MC, e con l
  391. [P] #371 `a` — La valutazione dei rischi, anche nella scelta delle attrezzature di lavoro e del
  393. [P] #373 `a` — Il documento di valutazione dei rischi (DVR) redatto a conclusione della valutaz
  394. [P] #374 `a elenchi nuovo` — una relazione sulla valutazione di tutti i rischi per la sicurezza e la salute d
  396. [P] #376 `a elenchi nuovo` — l’indicazione delle misure di prevenzione e di protezione attuate e dei disposit
  398. [P] #378 `a elenchi nuovo` — il programma delle misure ritenute opportune per garantire il miglioramento nel 
  399. [P] #379 `a elenchi nuovo` — l’individuazione delle procedure per l’attuazione delle misure da realizzare, no
  401. [P] #381 `a elenchi nuovo` — l’indicazione del nominativo del responsabile del servizio di prevenzione e prot
  403. [P] #383 `a elenchi nuovo` — l’individuazione delle mansioni che eventualmente espongono i lavoratori a risch
  409. [**H2**] #389 `a titolo 2` — Individuazione dei Soggetti Esposti
  410. [P] #390 `a` — Per “Soggetto Esposto” si intende qualsiasi persona presente nell’area di pertin
  412. [P] #392 `a` — L’individuazione dei soggetti esposti è valutata considerando:
  414. [P] #394 `a puntato` — l’interazione tra i lavoratori ed i rischi in modo diretto o indiretto;
  415. [P] #395 `a puntato` — gruppi omogenei di lavoratori esposti agli stessi rischi;
  416. [P] #396 `a puntato` — lavoratori, o gruppi di lavoratori, esposti a rischi maggiori, in quanto:
  417. [P] #397 `a elenco num` — portatori di handicap;
  418. [P] #398 `a elenco num` — molto giovani o anziani;
  419. [P] #399 `a elenco num` — donne in stato di gravidanza o madri in allattamento;
  420. [P] #400 `a elenco num` — neoassunti in fase di formazione;
  421. [P] #401 `a elenco num` — affetti da malattie particolari;
  422. [P] #402 `a elenco num` — addetti ai servizi di manutenzione;
  423. [P] #403 `a elenco num` — addetti a mansioni in spazi confinati o scarsamente ventilati.
  425. [P] #405 `a` — Per l’identificazione di tutti i soggetti esposti, occorrerà fare riferimento al
  427. [P] #407 `a puntato` — lavoratori addetti ad attività di produzione, manifattura, distribuzione, vendit
  428. [P] #408 `a puntato` — lavoratori addetti a servizi ausiliari (lavori di pulizia, manutenzione, lavori 
  429. [P] #409 `a puntato` — lavoratori impiegati d’ufficio e personale di vendita;
  430. [P] #410 `a puntato` — lavoratori di ditte appaltatrici;
  431. [P] #411 `a puntato` — lavoratori autonomi;
  432. [P] #412 `a puntato` — studenti, apprendisti, tirocinanti;
  433. [P] #413 `a puntato` — lavoratori addetti ai laboratori;
  434. [P] #414 `a puntato` — visitatori ed ospiti;
  435. [P] #415 `a puntato` — lavoratori esposti a rischi maggiori.
  448. [**H2**] #428 `a titolo 2` — Identificazione dei Pericoli
  449. [P] #429 `a` — Tale fase è stata eseguita partendo dalla analisi del ciclo lavorativo e dall’an
  451. [P] #431 `a` — A supporto della descrizione dell’attività lavorativa svolta, sono state analizz
  453. [P] #433 `a puntato` — la finalità della lavorazione o dell’operazione, con la descrizione del processo
  454. [P] #434 `a puntato` — la descrizione del ciclo tecnologico delle lavorazioni;
  455. [P] #435 `a puntato` — la destinazione operativa dell’ambiente di lavoro (reparto di lavoro, laboratori
  456. [P] #436 `a puntato` — le caratteristiche strutturali dell’ambiente di lavoro (superficie, volume, port
  457. [P] #437 `a puntato` — il numero degli operatori addetti alle lavorazioni e/o operazioni svolte per amb
  458. [P] #438 `a puntato` — le informazioni provenienti dalla Sorveglianza Sanitaria;
  459. [P] #439 `a puntato` — la presenza di movimentazione manuale dei carichi.
  461. [P] #441 `a` — La descrizione dell’attività operativa permette di avere una visione d’insieme d
  472. [**H2**] #452 `a titolo 2` — Individuazione dei Rischi di Esposizione
  473. [P] #453 `a` — La individuazione dei Rischi di Esposizione permette di definire se la presenza 
  475. [P] #455 `a` — Al riguardo sono stati esaminati:
  477. [P] #457 `a puntato` — le modalità operative seguite per la conduzione della lavorazione (es. manuale, 
  478. [P] #458 `a puntato` — l’entità delle lavorazioni in funzione dei tempi impiegati e delle quantità di m
  479. [P] #459 `a puntato` — l’organizzazione dell’attività: tempi di permanenza nell’ambiente di lavoro; con
  481. [P] #461 `a` — Tra i rischi individuati sono stati individuati alcuni per i quali è stato condo
  499. [P] #479 `a` — Sono stati oggetto di analisi specifica:
  501. [P] #481 `a puntato` — il rischio da esposizione a rumore, ai sensi del Titolo VIII Capo II del D.Lgs. 
  502. [P] #482 `a puntato` — il rischio da esposizione a vibrazioni, ai sensi del Titolo VIII Capo III del D.
  503. [P] #483 `a puntato` — il rischio da esposizione ad agenti chimici, ai sensi del Titolo IX Capo I del D
  504. [P] #484 `a puntato` — il rischio incendio, ai sensi del D.M. 10.03.1998. La valutazione è stata condot
  505. [P] #485 `a puntato` — il rischio da movimentazione manuale dei carichi, ai sensi del Titolo VI del D.L
  506. [P] #486 `a puntato` — il rischio da esposizione a videoterminali, ai sensi del Titolo VII del D.Lgs. 8
  507. [P] #487 `a puntato` — il rischio da stress lavoro correlato.
  509. [P] #489 `a` — A seguito dell’individuazione dei rischi di esposizione vengono individuate, fac
  519. [**H2**] #499 `a titolo 2` — Definizione delle misure di prevenzione e di protezione attuate e dei dispositiv
  520. [P] #500 `a` — Al termine di questa analisi delle sorgenti di rischio si potrà procede alla def
  523. [**H2**] #503 `a titolo 2` — Classificazione dei rischi
  524. [P] #504 `a` — Al fine di definire il programma delle misure ritenute opportune per garantire i
  525. [P] #505 `a` — I rischi sono stati classificati secondo la seguente scala, dove I sta per indic
  551. [**T20**] 5x3 STATIC — ...
  554. [P] #533 `a` — L’indice di rischio, I, viene calcolato secondo la relazione
  557. [P] #536 `a tabella centrato` — I = 2*D + P
  560. [P] #539 `a` — Dove D è il massimo entità del danno ragionevolmente prevedibile, ovvero la magn
  574. [**T21**] 5x3 DYNAMIC — ...
  580. [**T22**] 5x3 UNKNOWN — ...
  590. [**H2**] #567 `a titolo 2` — Individuazione delle procedure per l’attuazione delle misure
  591. [P] #568 `a` — Le misure di prevenzione e protezione e i dispositivi di protezione individuale 
  594. [**H2**] #571 `a titolo 2` — Redazione del Documento di Valutazione dei Rischi
  595. [P] #572 `a` — Il DL, tramite il SPP, redige il documento contenente la valutazione dei rischi,
  596. [P] #573 `a` — Il documento è firmato dal DL, dal RSPP, e, per presa visione, dal MC e dal RLS.
  599. [**H2**] #576 `a titolo 2` — Aggiornamento del documento
  600. [P] #577 `a` — La valutazione dei rischi deve essere immediatamente rielaborata, in collaborazi

--- **PARTE III** (element #609) ---

  609. [**H0**] #586 `a Titolo parte` — PARTE III
  610. [**H0**] #587 `a titolo parte 2` — Individuazione dei rischi, delle misure di prevenzione e di protezione e dei dis
  616. [**T23**] 5x2 DYNAMIC — Individuazione dei rischi, delle misure 
  622. [**H1**] #598 `a titolo 1` — Identificazione dell’Ambiente di Lavoro e degli Addetti - UFFICIO AMMINISTRATIVO
  626. [**T24**] 3x2 DYNAMIC [UFFICIO AMMINISTRATIVO] — Identificazione dell’Ambiente di Lavoro 
  631. [**T25**] 3x2 UNKNOWN [UFFICIO AMMINISTRATIVO] — Identificazione dell’Ambiente di Lavoro 
  636. [**H1**] #610 `a titolo 1` — Identificazione dei Fattori di Rischio - UFFICIO AMMINISTRATIVO
  640. [**T26**] 14x2 UNKNOWN [UFFICIO AMMINISTRATIVO] — Identificazione dei Fattori di Rischio -
  657. [P] #630 `spec` — Schede Specifiche con l’Individuazione dei pericoli, delle condizioni di impiego
  672. [**T27**] 10x5 DYNAMIC [UFFICIO AMMINISTRATIVO] — ...
  696. [**T28**] 10x5 STATIC [UFFICIO AMMINISTRATIVO] — ...
  718. [**T29**] 5x5 STATIC [UFFICIO AMMINISTRATIVO] — ...
  743. [**T30**] 5x5 STATIC [UFFICIO AMMINISTRATIVO] — ...
  751. [**T31**] 7x5 MIXED [UFFICIO AMMINISTRATIVO] — ...
  758. [**T32**] 3x5 STATIC [UFFICIO AMMINISTRATIVO] — ...
  790. [**T33**] 5x5 STATIC [UFFICIO AMMINISTRATIVO] — ...
  793. [**H1**] #759 `a titolo 1` — Identificazione dell’Ambiente di Lavoro e degli Addetti - UFFICIO TECNICO
  796. [**T34**] 3x2 DYNAMIC [UFFICIO TECNICO] — Identificazione dell’Ambiente di Lavoro 
  800. [**T35**] 8x2 DYNAMIC [UFFICIO TECNICO] — Identificazione dell’Ambiente di Lavoro 
  805. [**H1**] #769 `a titolo 1` — Identificazione dei Fattori di Rischio - UFFICIO TECNICO
  809. [**T36**] 14x2 UNKNOWN [UFFICIO TECNICO] — Identificazione dei Fattori di Rischio -
  826. [P] #789 `spec` — Schede Specifiche con l’Individuazione dei pericoli, delle condizioni di impiego
  842. [**T37**] 9x5 DYNAMIC [UFFICIO TECNICO] — ...
  872. [**T38**] 10x5 STATIC [UFFICIO TECNICO] — ...
  893. [**T39**] 5x5 STATIC [UFFICIO TECNICO] — ...
  919. [**T40**] 5x5 STATIC [UFFICIO TECNICO] — ...
  927. [**T41**] 7x5 MIXED [UFFICIO TECNICO] — ...
  934. [**T42**] 3x5 STATIC [UFFICIO TECNICO] — ...
  966. [**T43**] 5x5 STATIC [UFFICIO TECNICO] — ...
  969. [**H1**] #925 `a titolo 1` — Identificazione dell’Ambiente di Lavoro e degli Addetti - UFFICIO COMMERCIALE E 
  972. [**T44**] 3x2 DYNAMIC [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO] — Identificazione dell’Ambiente di Lavoro 
  976. [**T45**] 4x2 UNKNOWN [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO] — Identificazione dell’Ambiente di Lavoro 
  981. [**H1**] #935 `a titolo 1` — Identificazione dei Fattori di Rischio - UFFICIO COMMERCIALE E MEDICINA DEL LAVO
  985. [**T46**] 14x2 UNKNOWN [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO] — Identificazione dei Fattori di Rischio -
  1002. [P] #955 `spec` — Schede Specifiche con l’Individuazione dei pericoli, delle condizioni di impiego
  1019. [**T47**] 9x5 DYNAMIC [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO] — ...
  1049. [**T48**] 5x5 STATIC [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO] — ...
  1062. [**T49**] 5x5 STATIC [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO] — ...
  1083. [**T50**] 5x5 STATIC [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO] — ...
  1109. [**T51**] 5x5 STATIC [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO] — ...
  1117. [**T52**] 7x5 MIXED [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO] — ...
  1124. [**T53**] 3x5 STATIC [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO] — ...
  1155. [**T54**] 5x5 STATIC [UFFICIO COMMERCIALE E MEDICINA DEL LAVORO] — ...
  1158. [**H1**] #1103 `a titolo 1` — Identificazione dell’Ambiente di Lavoro e degli Addetti - SALA CORSI
  1161. [**T55**] 3x2 DYNAMIC [SALA CORSI] — Identificazione dell’Ambiente di Lavoro 
  1166. [**T56**] 6x2 DYNAMIC [SALA CORSI] — Identificazione dell’Ambiente di Lavoro 
  1171. [**H1**] #1114 `a titolo 1` — Identificazione dei Fattori di Rischio - SALA CORSI
  1175. [**T57**] 14x2 UNKNOWN [SALA CORSI] — Identificazione dei Fattori di Rischio -
  1192. [P] #1134 `spec` — Schede Specifiche con l’Individuazione dei pericoli, delle condizioni di impiego
  1207. [**T58**] 9x5 DYNAMIC [SALA CORSI] — ...
  1237. [**T59**] 5x5 STATIC [SALA CORSI] — ...
  1249. [**T60**] 5x5 STATIC [SALA CORSI] — ...
  1272. [**T61**] 5x5 STATIC [SALA CORSI] — ...
  1298. [**T62**] 5x5 STATIC [SALA CORSI] — ...
  1306. [**T63**] 7x5 MIXED [SALA CORSI] — ...
  1313. [**T64**] 3x5 STATIC [SALA CORSI] — ...
  1344. [**T65**] 5x5 STATIC [SALA CORSI] — ...
  1347. [**H1**] #1281 `a titolo 1` — Identificazione dell’Ambiente di Lavoro e degli Addetti - MAGAZZINO
  1350. [**T66**] 3x2 DYNAMIC [MAGAZZINO] — Identificazione dell’Ambiente di Lavoro 
  1354. [**T67**] 10x2 DYNAMIC [MAGAZZINO] — Identificazione dell’Ambiente di Lavoro 
  1359. [**H1**] #1291 `a titolo 1` — Identificazione dei Fattori di Rischio - MAGAZZINO
  1363. [**T68**] 14x2 UNKNOWN [MAGAZZINO] — Identificazione dei Fattori di Rischio -
  1380. [P] #1311 `spec` — Schede Specifiche con l’Individuazione dei pericoli, delle condizioni di impiego
  1397. [**T69**] 15x5 MIXED [MAGAZZINO] — ...
  1402. [**T70**] 12x5 MIXED [MAGAZZINO] — ...
  1408. [**T71**] 5x5 STATIC [MAGAZZINO] — ...
  1429. [**T72**] 6x5 STATIC [MAGAZZINO] — ...
  1451. [**T73**] 5x5 STATIC [MAGAZZINO] — ...
  1459. [**T74**] 6x5 MIXED [MAGAZZINO] — ...
  1483. [**T75**] 3x5 STATIC [MAGAZZINO] — ...
  1515. [**T76**] 5x5 STATIC [MAGAZZINO] — ...
  1519. [**H1**] #1442 `a titolo 1` — Identificazione dell’Ambiente di Lavoro e degli Addetti - AREA BREAK
  1522. [**T77**] 3x2 DYNAMIC [AREA BREAK] — Identificazione dell’Ambiente di Lavoro 
  1526. [**T78**] 15x2 DYNAMIC [AREA BREAK] — Identificazione dell’Ambiente di Lavoro 
  1531. [**H1**] #1452 `a titolo 1` — Identificazione dei Fattori di Rischio - AREA BREAK
  1535. [**T79**] 14x2 UNKNOWN [AREA BREAK] — Identificazione dei Fattori di Rischio -
  1552. [P] #1472 `spec` — Schede Specifiche con l’Individuazione dei pericoli, delle condizioni di impiego
  1568. [**T80**] 7x5 DYNAMIC [AREA BREAK] — ...
  1571. [**T81**] 5x5 STATIC [AREA BREAK] — ...
  1590. [**T82**] 6x5 STATIC [AREA BREAK] — ...
  1612. [**T83**] 5x5 STATIC [AREA BREAK] — ...
  1620. [**T84**] 6x5 MIXED [AREA BREAK] — ...
  1643. [**T85**] 5x5 STATIC [AREA BREAK] — ...
  1646. [**H1**] #1560 `a titolo 1` — Identificazione dell’Ambiente di Lavoro e degli Addetti - STRUTTURE PRESSO CLIEN
  1649. [**T86**] 3x2 DYNAMIC [STRUTTURE PRESSO CLIENTI] — Identificazione dell’Ambiente di Lavoro 
  1653. [**T87**] 10x2 DYNAMIC [STRUTTURE PRESSO CLIENTI] — Identificazione dell’Ambiente di Lavoro 
  1658. [**H1**] #1570 `a titolo 1` — Identificazione dei Fattori di Rischio - STRUTTURE PRESSO CLIENTI
  1662. [**T88**] 14x2 UNKNOWN [STRUTTURE PRESSO CLIENTI] — Identificazione dei Fattori di Rischio -
  1679. [P] #1590 `spec` — Schede Specifiche con l’Individuazione dei pericoli, delle condizioni di impiego
  1696. [**T89**] 20x5 MIXED [STRUTTURE PRESSO CLIENTI] — ...
  1710. [**T90**] 14x5 MIXED [STRUTTURE PRESSO CLIENTI] — ...
  1713. [**T91**] 8x5 STATIC [STRUTTURE PRESSO CLIENTI] — ...
  1722. [**T92**] 8x5 STATIC [STRUTTURE PRESSO CLIENTI] — ...
  1726. [**T93**] 6x5 MIXED [STRUTTURE PRESSO CLIENTI] — ...
  1734. [**T94**] 4x5 STATIC [STRUTTURE PRESSO CLIENTI] — ...
  1762. [**T95**] 5x5 STATIC [STRUTTURE PRESSO CLIENTI] — ...
  1765. [**H1**] #1669 `a titolo 1` — Elenco Mansioni che espongono i lavoratori a rischi specifici (art. 28 co. 2/f D
  1766. [P] #1670 `a` — Agli esiti della valutazione dei rischi nel seguito si individuano come previsto
  1768. [**T96**] 14x3 MIXED [STRUTTURE PRESSO CLIENTI] — Elenco Mansioni che espongono i lavorato
  1769. [**H1**] #1672 `a titolo 1` — Dispositivi di Protezione Individuale (DPI)
  1771. [**T97**] 6x3 DYNAMIC [STRUTTURE PRESSO CLIENTI] — Dispositivi di Protezione Individuale (D
  1775. [**T98**] 7x3 DYNAMIC [STRUTTURE PRESSO CLIENTI] — Dispositivi di Protezione Individuale (D
  1787. [**T99**] 6x3 DYNAMIC [STRUTTURE PRESSO CLIENTI] — ...
  1791. [**T100**] 11x3 DYNAMIC [STRUTTURE PRESSO CLIENTI] — ...
  1794. [**T101**] 6x3 DYNAMIC [STRUTTURE PRESSO CLIENTI] — ...
  1799. [**T102**] 9x3 DYNAMIC [STRUTTURE PRESSO CLIENTI] — ...
  1807. [**T103**] 8x3 DYNAMIC [STRUTTURE PRESSO CLIENTI] — ...
  1812. [**T104**] 7x3 DYNAMIC [STRUTTURE PRESSO CLIENTI] — ...
  1814. [**H1**] #1709 `a titolo 1` — Segnaletica di sicurezza
  1815. [**H3**] #1710 `a titolo 3` — Definizione
  1816. [P] #1711 `a` — Per segnaletica di sicurezza si intende una segnaletica che, riferita ad un ogge
  1818. [**H3**] #1713 `a titolo 3` — Obblighi del datore di lavoro
  1819. [P] #1714 `a` — Quando, anche a seguito della valutazione effettuata in conformità dell'articolo
  1821. [P] #1716 `a puntato` — avvertire di un rischio o di un pericolo le persone esposte;
  1822. [P] #1717 `a puntato` — vietare comportamenti che potrebbero causare pericolo;
  1823. [P] #1718 `a puntato` — prescrivere determinati comportamenti necessari ai fini della sicurezza;
  1824. [P] #1719 `a puntato` — fornire indicazioni relative alle uscite di sicurezza o ai mezzi di soccorso o d
  1825. [P] #1720 `a puntato` — fornire altre indicazioni in materia di prevenzione e sicurezza.
  1827. [**H3**] #1722 `a titolo 3` — Scopo della segnaletica di sicurezza
  1828. [P] #1723 `a` — Attirare velocemente e in modo facilmente comprensibile l'attenzione su oggetti 
  1830. [P] #1725 `a` — Devono essere utilizzati colori di sicurezza e di contrasto, nonché i colori del
  1831. [**T105**] 8x4 DYNAMIC [STRUTTURE PRESSO CLIENTI] — Scopo della segnaletica di sicurezza
  1834. [P] #1728 `a` — Le caratteristiche dei cartelli cambiano a seconda che si tratti di:
  1835. [**T106**] 6x4 UNKNOWN [STRUTTURE PRESSO CLIENTI] — Scopo della segnaletica di sicurezza
  1836. [**H1**] #1729 `a titolo 1` — Principale segnaletica da apporre negli ambienti di lavoro
  1837. [P] #1730 `a` — Cartello per indicazione dei servizi igienici:
  1842. [P] #1735 `a` — Cartello per indicazione cassetta pronto soccorso:
  1846. [P] #1739 `a` — Cartelli di indicazione uscite di emergenza
  1855. [P] #1748 `a` — Cartelli per indicazione del percorso per uscita di emergenza
  1860. [P] #1753 `a` — Norme comportamentali in caso di incendio, pronto soccorso, movimentazione manua
  1864. [P] #1757 `a` — Cartello di segnalazione estintore
  1868. [P] #1761 `a` — Divieto di depositare materiale in prossimità delle uscite di sicurezza
  1872. [P] #1765 `a` — Divieto di fumare
  1876. [P] #1769 `a` — Divieto di accesso
  1880. [**H1**] #1773 `a titolo 1` — Programma di Formazione, Informazione ed Addestramento
  1881. [P] #1774 `a` — Si riporta di seguito i requisiti minimi del programma minimo di formazione da a
  1882. [**T107**] 18x4 DYNAMIC [STRUTTURE PRESSO CLIENTI] — Programma di Formazione, Informazione ed
  1883. [P] #1775 `a` — (*) L’informazione, formazione e, ove previsto, l’addestramento specifico devono
  1884. [P] #1776 `a puntato` — della costituzione del rapporto di lavoro o dell’inizio dell’utilizzazione qualo
  1885. [P] #1777 `a puntato` — del trasferimento o cambiamento di mansioni;
  1886. [P] #1778 `a puntato` — della introduzione di nuove attrezzature di lavoro o di nuove tecnologie, di nuo

--- **PARTE IV** (element #1895) ---

  1895. [**H0**] #1787 `a Titolo parte` — PARTE IV
  1896. [**H0**] #1788 `a titolo parte 2` — Programma e Procedure delle misure per garantire il miglioramento nel tempo dei 
  1902. [**T108**] 5x2 DYNAMIC — Programma e Procedure delle misure per g
  1903. [**H1**] #1794 `a titolo 1` — Programma e Procedure di attuazione delle Misure di Miglioramento
  1904. [P] #1795 `a` — Al fine di perseguire il miglioramento nel tempo dei livelli di sicurezza aziend
  1907. [**T109**] 3x5 UNKNOWN — Programma e Procedure di attuazione dell
  1910. [**H1**] #1800 `a titolo 1` — Gestione Leggi e Regolamenti
  1911. [**H2**] #1801 `a titolo 2` — Responsabilità
  1912. [P] #1802 `a` — IL RSPP ha la responsabilità di:
  1914. [P] #1804 `a puntato` — ricercare leggi e regolamenti applicabili e identificare quelli relativi alle at
  1915. [P] #1805 `a puntato` — valutare i potenziali impatti di queste leggi e regolamenti sulla Organizzazione
  1916. [P] #1806 `a puntato` — assicurarsi che  abbia tutti i nulla osta, autorizzazioni e permessi necessari e
  1917. [P] #1807 `a puntato` — comunicare qualsiasi nuova prescrizione legislativa alle persone interessate
  1919. [**H2**] #1809 `a titolo 2` — Ricerca delle leggi
  1920. [P] #1810 `a` — Il RSPP riceve periodicamente gli aggiornamenti legislativi in materia di SSL e 
  1921. [P] #1811 `a` — Il RSPP, al ricevimento di tali documenti, analizza le prescrizioni contenute e 
  1923. [**H2**] #1813 `a titolo 2` — Diffusione ed utilizzo di leggi e regolamenti
  1924. [P] #1814 `a` — Dopo aver individuato le aree in cui tali disposizioni legislative individuate d
  1925. [P] #1815 `a` — La predisposizione di eventuali atti amministrativi previsti dalla normativa, qu
  1926. [P] #1816 `a` — Il RSPP registra ogni eventuale scadenza di adempimento e/o di controlli da effe
  1927. [P] #1817 `a` — Il RSPP conserva le copie delle leggi e regolamenti applicate dalla Organizzazio
  1929. [**H2**] #1819 `a titolo 2` — Archiviazione
  1930. [P] #1820 `a` — Il RSPP conserva per il periodo di validità:
  1932. [P] #1822 `a puntato` — Bollettini ricevuti dalle associazioni di categoria
  1933. [P] #1823 `a puntato` — leggi, regolamenti, norme, prescrizioni applicate dalla Organizzazione
  1934. [P] #1824 `a puntato` — nulla osta, permessi, autorizzazioni
  1936. [P] #1826 `a` — Successivamente alla loro scadenza tali documenti sono archiviati per 3 anni, a 
  1938. [**H1**] #1828 `a titolo` — Documentazione Collegata
  1939. [P] #1829 `a` — Registro Norme e Leggi
  1941. [**H1**] #1831 `a titolo 1` — Gestione Sorveglianza sanitaria
  1942. [**H2**] #1832 `a titolo 2` — Verifica delle necessità della sorveglianza sanitaria
  1943. [P] #1833 `a` — Il DL, tramite il SPP, verifica la necessità di sottoporre a sorveglianza sanita
  1944. [P] #1834 `a` — Tale necessità ricorre:
  1946. [P] #1836 `a puntato` — in ogni caso per tutti i LAV prima del loro inizio attività, per determinare la 
  1947. [P] #1837 `a puntato` — qualora il lavoratore ne faccia richiesta e la stessa sia ritenuta dal medico co
  1948. [P] #1838 `a puntato` — in ogni caso previsto dalle leggi vigenti;
  1949. [P] #1839 `a puntato` — a seguito disposizioni dell’AUSL locale; nei casi di dubbia interpretazione il D
  1951. [**H2**] #1841 `a titolo 2` — Nomina del MC
  1952. [P] #1842 `a` — Il DL con la collaborazione di RSPP e DRG interessati, contatta i candidati medi
  1953. [P] #1843 `a` — La lettera di nomina comprende la richiesta dell’osservanza da parte del MC dei 
  1954. [P] #1844 `a` — Il medico competente deve avere i titoli e requisiti previsti dall’art. 38 del D
  1956. [P] #1846 `a` — Il medico competente svolge la propria opera in qualità di:
  1957. [P] #1847 `a puntato` — a) dipendente o collaboratore di una struttura esterna pubblica o privata, conve
  1958. [P] #1848 `a puntato` — b) libero professionista;
  1959. [P] #1849 `a puntato` — c) dipendente del datore di lavoro.
  1961. [P] #1851 `a` — Successivamente alla nomina il DL redige un contratto di consulenza, in cui sono
  1962. [P] #1852 `a puntato` — la natura del rapporto di lavoro tra azienda e MC;
  1963. [P] #1853 `a puntato` — il nominativo del dirigente che curerà le relazioni con il MC;
  1964. [P] #1854 `a puntato` — le prestazioni di routine del MC, specificando, se del caso, il tempo richiesto 
  1965. [P] #1855 `a puntato` — eventualmente, l’indicazione dei locali o strutture aziendali a disposizione del
  1966. [P] #1856 `a puntato` — la durata della collaborazione ed eventualmente le condizioni e modalità di rinn
  1967. [P] #1857 `a puntato` — i casi di inadempimento che possono comportare la rescissione del contratto.
  1969. [P] #1859 `a` — Dopo la nomina il DL o il DRG, tramite il SPP, trasmette al MC copia della docum
  1971. [P] #1861 `a puntato` — elenco LAV con mansioni e data di nascita;
  1972. [P] #1862 `a puntato` — i dati del registro degli infortuni e delle malattie professionali;
  1973. [P] #1863 `a puntato` — schede di sicurezza delle sostanze o preparati utilizzati;
  1974. [P] #1864 `a puntato` — documento di valutazione dei rischi;
  1975. [P] #1865 `a puntato` — relazioni di sintesi dei risultati di verifiche fonometriche e/o dell’ambiente d
  1977. [**H2**] #1867 `a titolo 2` — Revoca della Nomina
  1978. [P] #1868 `a` — Il DL, anche su segnalazione del DRG interessato, può revocare la nomina del MC 
  1980. [P] #1870 `a puntato` — fine del termine contrattuale;
  1981. [P] #1871 `a puntato` — dimissioni dall’incarico;
  1982. [P] #1872 `a puntato` — per evidenti carenze nello svolgere gli incarichi previsti.
  1984. [P] #1874 `a` — Il DL effettua la revoca assicurando però che, in attesa della nuova nomina, la 
  1986. [**H2**] #1876 `a titolo 2` — Attività Del MC
  1987. [P] #1877 `a` — Il MC svolge le attività definite dagli artt. 25–39–40–41-42 del D.Lgs. 81/2008 
  1989. [**H2**] #1879 `a titolo 2` — Documentazione Collegata
  1990. [P] #1880 `a` — Nomina medico competente
  1991. [P] #1881 `a` — Contratto di consulenza stipulato con il medico competente
  1992. [P] #1882 `a` — Cartelle sanitarie lavoratori
  1994. [**H1**] #1884 `a titolo 1` — Gestione Informazione, Formazione ed Addestramento
  1995. [**H2**] #1885 `a titolo 2` — Programmazione della Formazione, Informazione ed Addestramento
  1996. [P] #1886 `a` — Il DL in collaborazione con il RSPP, in funzione
  1997. [P] #1887 `a puntato` — della valutazione dei rischi
  1998. [P] #1888 `a puntato` — delle segnalazioni ricevute,
  1999. [P] #1889 `a puntato` — di quanto definito dagli artt. 31-32-33-34-36-37-73-77-164-169-177-184-195-227-2
  2000. [P] #1890 `a puntato` — I contenuti dell’informazione e formazione necessaria
  2001. [P] #1891 `a puntato` — Sito e lavoratore coinvolto
  2002. [P] #1892 `a puntato` — Modalità di erogazione, comprendente inoltre l’indicazione delle funzioni intern
  2003. [P] #1893 `a puntato` — Indicazione delle misure di accertamento, anche periodiche (domande, questionari
  2004. [P] #1894 `a puntato` — Periodo indicativo di prevista effettuazione dell’azione di informazione e forma
  2005. [P] #1895 `a` — Il Piano di Formazione è redatto in forma scritta tramite modello Piano di forma
  2007. [**H2**] #1897 `a titolo 2` — Segnalazione delle necessità Formative od Informative
  2008. [P] #1898 `a` — Tutte le parti interessate possono evidenziare, anche con il contributo del RSPP
  2009. [P] #1899 `a` — La richiesta di interventi informativi o formativi può essere effettuata anche a
  2010. [P] #1900 `a puntato` — Mutate condizioni di rischio per i lavoratori
  2011. [P] #1901 `a puntato` — Variazione del personale ovvero ogni volta si ha una nuova assunzione
  2012. [P] #1902 `a puntato` — Presenza di non conformità
  2013. [P] #1903 `a` — Il modulo viene inoltrato al RSPP che valutata la richiesta, la sottopone al DL.
  2015. [**H2**] #1905 `a titolo 2` — Criteri di Erogazione delle Attività di Informazione, Formazione ed Addestrament
  2016. [P] #1906 `a` — L’erogazione delle attività di informazione, formazione ed addestramento avviene
  2018. [P] #1908 `a puntato` — corsi su argomenti specifici
  2019. [P] #1909 `a puntato` — schede o manuali di apparecchiature e macchine
  2020. [P] #1910 `a puntato` — procedure operative di lavoro
  2021. [P] #1911 `a puntato` — dépliant, posters e cartelli di sensibilizzazione
  2022. [P] #1912 `a puntato` — prove pratiche
  2024. [P] #1914 `a` — Le attività di informazione, formazione ed addestramento avvengono abitualmente 
  2026. [P] #1916 `a` — La attività di informazione, formazione ed addestramento avviene in ogni modo se
  2028. [P] #1918 `a puntato` — dell’assunzione;
  2029. [P] #1919 `a puntato` — del trasferimento o cambiamento di mansioni;
  2030. [P] #1920 `a puntato` — dell’introduzione di nuove attrezzature di lavoro o di nuove tecnologie, di nuov
  2031. [P] #1921 `a puntato` — del trasferimento o cambiamento di mansioni che implichi variazioni sostanziali 
  2032. [P] #1922 `a puntato` — in relazione all'evoluzione dei rischi ovvero all'insorgenza di nuovi rischi.
  2034. [P] #1924 `a` — In tutti i casi precedentemente elencati, il DL, in collaborazione con il PREP o
  2035. [P] #1925 `a` — La durata del periodo di affiancamento del LAV è stabilita dal PREP competente p
  2043. [**H2**] #1933 `a titolo 2` — Esecuzione e Registrazione delle Attività
  2044. [P] #1934 `a` — Le attività di formazione, informazione ed addestramento sono effettuate durante
  2045. [P] #1935 `a` — L’attività formativa ed informativa o qualsiasi riunione a carattere informativo
  2047. [P] #1937 `a` — Per l’attività formativa occorre procedere anche alla compilazione da parte del 
  2049. [P] #1939 `a` — Tutti i registri e questionari sono conservati a cura del RSPP
  2050. [P] #1940 `a` — Il RSPP redige e tiene aggiornato l’elenco dei LAV comprendente l’indicazione de
  2053. [**H2**] #1943 `a titolo 2` — Documentazione Collegata
  2054. [P] #1944 `a` — Registro presenze attività info – formative
  2055. [P] #1945 `a` — Piano di formazione ed informazione
  2072. [**H1**] #1962 `a titolo 1` — Riunione Periodica
  2073. [**H2**] #1963 `a titolo 2` — Convocazione
  2074. [P] #1964 `a` — Il DL direttamente o comunque tramite il RSPP, indice una riunione con oggetto l
  2075. [P] #1965 `a` — La riunione ha altresì luogo in occasione di eventuali significative variazioni 
  2077. [P] #1967 `a` — È facoltà del rappresentante dei lavoratori per la sicurezza chiedere la convoca
  2079. [P] #1969 `a puntato` — il DL;
  2080. [P] #1970 `a puntato` — il RSPP;
  2081. [P] #1971 `a puntato` — il MC;
  2082. [P] #1972 `a puntato` — il RLS;
  2083. [P] #1973 `a puntato` — soggetti esterni che eventualmente hanno inoltrato richiesta di riunione.
  2085. [P] #1975 `a` — Alle riunioni del servizio di prevenzione e protezione partecipano, su invito de
  2087. [P] #1977 `a` — Il RSPP prepara l’ordine di giorno degli argomenti da trattare anche sulla base 
  2089. [P] #1979 `a puntato` — il documento di valutazione dei rischi;
  2090. [P] #1980 `a puntato` — l’andamento degli infortuni e delle malattie professionali e della sorveglianza 
  2091. [P] #1981 `a puntato` — i criteri di scelta, le caratteristiche tecniche e l’efficacia dei dispositivi d
  2092. [P] #1982 `a puntato` — i programmi di informazione e formazione dei dirigenti, dei preposti e dei lavor
  2093. [P] #1983 `a puntato` — varie ed eventuali
  2102. [P] #1992 `a` — Nel corso della riunione verranno individuati anche:
  2104. [P] #1994 `a puntato` — codici di comportamento e buone prassi per prevenire i rischi di infortuni e di 
  2105. [P] #1995 `a puntato` — obiettivi di miglioramento della sicurezza complessiva.
  2107. [P] #1997 `a` — La convocazione della riunione è effettuata da parte del RSPP, trasmesso ai sogg
  2109. [**H2**] #1999 `a titolo 2` — Verbalizzazione e Divulgazione
  2111. [P] #2001 `a` — La riunione periodica è verbalizzata a cura del RSPP su apposito Modello di verb
  2112. [P] #2002 `a` — Il modulo di verbalizzazione deve obbligatoriamente riportare le firme di DL, RS
  2114. [P] #2004 `a` — Il verbale di riunione periodica è trasmesso a cura del RSPP in copia a tutti i 
  2116. [P] #2006 `a` — I verbali di riunione periodica sono conservati in originale, in allegato al doc
  2119. [**H1**] #2009 `a titolo` — Documentazione Collegata
  2120. [P] #2010 `a` — Convocazione Riunione Periodica
  2121. [P] #2011 `a` — Verbale Riunione Periodica
  2123. [**H1**] #2013 `a titolo 1` — Gestione degli Infortuni
  2124. [**H2**] #2014 `a titolo 2` — Segnalazione
  2126. [P] #2016 `a` — I LAV hanno il dovere di informare immediatamente con comunicazione di tipo verb
  2128. [P] #2018 `a` — Il PREP o DRG a sua volta informa, sempre verbalmente, il DL e il RSPP.
  2129. [P] #2019 `a` — Il PREP o il DRG in caso di INFORTUNIO procede secondo quanto riportato nei para
  2131. [**H2**] #2021 `a titolo 2` — Indagine
  2133. [P] #2023 `a` — Tutti gli incidenti devono essere seguiti da indagine, la cui complessità dipend
  2135. [P] #2025 `a puntato` — Raccolta dei dati descrittivi dell’evento verificatosi tramite indagine prelimin
  2136. [P] #2026 `a puntato` — Istituzione della commissione di indagine e redazione del rapporto di indagine
  2137. [P] #2027 `a puntato` — Elaborazione della relazione con relative azioni correttive
  2139. [P] #2029 `a` — Successivamente all’evento, il RSPP, raccoglie i dati descrittivi ed identificat
  2141. [P] #2031 `a` — La compilazione del suddetto modulo ha lo scopo di identificare i dati significa
  2142. [P] #2032 `a` — Una volta compilato il Modello di Indagine Preliminare, il RSPP incaricato conse
  2153. [**H2**] #2043 `a titolo 2` — Commissione di indagine
  2154. [P] #2044 `a` — Il RSPP istituisce la commissione di indagine che sarà composta dal DL, dal DRG 
  2156. [P] #2046 `a` — La commissione di indagine, sulla base dei contenuti del Modello di Indagine Pre
  2158. [P] #2048 `a puntato` — Identificazione dell’attività lavorativa (fase lavorativa) che veniva svolto al 
  2159. [P] #2049 `a puntato` — Descrizione dettagliata dell’incidente, specificando posizione fisica dell’inter
  2160. [P] #2050 `a puntato` — Nel caso in cui l’evento abbia provocato un infortunio, identificazione delle az
  2161. [P] #2051 `a puntato` — Indicazione, descrizione delle condizioni (ambiente, macchine, attrezzature, mat
  2162. [P] #2052 `a puntato` — Descrizione dei provvedimenti presi per evitare il ripetersi di eventi analoghi
  2163. [P] #2053 `a puntato` — Osservazioni ed eventuali conclusioni delle funzioni interessate
  2165. [P] #2055 `a` — Il rapporto di indagine, con allegata tutta la documentazione raccolta (foto, fa
  2179. [**H2**] #2069 `a titolo 2` — Relazione Tecnica di Valutazione Finale
  2181. [P] #2071 `a` — Sulla base di quanto emerso dall’indagine sulle circostanze dell’incidente, il R
  2182. [P] #2072 `a` — L’attività di valutazione finale sull’evento viene coordinata dal RSPP in collab
  2184. [P] #2074 `a` — Tale attività prevede la redazione di una relazione tecnica finale da parte del 
  2186. [P] #2076 `a puntato` — Descrizione dell’incidente o infortunio
  2187. [P] #2077 `a puntato` — Analisi delle cause e delle condizioni che hanno indotto l’evento
  2188. [P] #2078 `a puntato` — Analisi dei provvedimenti già presi per evitare l’evento indesiderato
  2189. [P] #2079 `a puntato` — Analisi dei provvedimenti da adottare per evitare il ripetersi della condizione 
  2190. [P] #2080 `a puntato` — Modalità di scelta delle azioni correttive;
  2191. [P] #2081 `a puntato` — Metodi, modi e tempi con cui si intende procedere nell’applicazione di suddette 
  2192. [P] #2082 `a puntato` — Metodi, modi e tempi con cui si intende verificare l’efficacia delle azioni intr
  2194. [P] #2084 `a` — Nel caso in cui siano state individuate delle azioni correttive queste devono es
  2196. [P] #2086 `a` — Alla relazione dovrà essere allegato il modello di indagine preliminare compilat
  2204. [**H2**] #2094 `a titolo 2` — Registro degli Infortuni e Denuncia Infortunio
  2205. [P] #2095 `a` — In caso di INF che comportano un'assenza dal lavoro di almeno un giorno, il DL, 
  2206. [P] #2096 `a` — Il DL provvede a comunicare all’INAIL, o all’IPSEMA, in relazione alle rispettiv
  2207. [P] #2097 `a` — La denuncia ed il certificato medico debbono indicare, oltre alle generalità del
  2208. [P] #2098 `a` — La denuncia redatta sull’apposito modulo è firmata dal DL.
  2209. [P] #2099 `a` — Infortunio non guaribile in tre giorni
  2210. [P] #2100 `a` — In caso di INF non guaribile entro 3 giorni, il DL o il RSPP, denuncia all'INAIL
  2211. [P] #2101 `a` — Qualora l'inabilità per un INF pronosticato guaribile entro tre giorni si prolun
  2212. [P] #2102 `a` — Infortunio che ha prodotto morte o pericolo di morte
  2213. [P] #2103 `a` — Se si tratta di INF che abbia prodotto la morte o per il quale sia possibile il 
  2214. [P] #2104 `a` — Ulteriore denuncia all’autorità locale
  2215. [P] #2105 `a` — In caso di INF sul lavoro che abbia per conseguenza la morte o l'inabilità al la
  2216. [P] #2106 `a` — La denuncia, redatta sull’apposito modulo, è firmata dal DL.
  2218. [**H1**] #2108 `a titolo` — Documentazione Collegata
  2219. [P] #2109 `a` — Modello di Indagine Preliminare
  2220. [P] #2110 `a` — Modulo di denuncia infortunio INAIL
  2221. [P] #2111 `a` — Registro degli infortuni
  2222. [P] #2112 `a` — Rapporto di indagine
  2223. [P] #2113 `a` — Relazione tecnica sulle non conformità
  2225. [**H1**] #2115 `a titolo 1` — Gestione comportamenti scorretti dei lavoratori
  2226. [**H2**] #2116 `a titolo 2` — Cause di Richiamo Lavoratori
  2227. [P] #2117 `a` — Il DL, tramite i DRG e PREP, verifica costantemente il comportamento dei LAV e l
  2229. [P] #2119 `a` — A tale proposito, un comportamento ai ritiene scorretto o non conforme quando i 
  2231. [P] #2121 `a puntato` — non osservano le disposizioni e le istruzioni di sicurezza impartite, ai fini de
  2232. [P] #2122 `a puntato` — non utilizzano correttamente i macchinari, le apparecchiature, gli utensili, le 
  2233. [P] #2123 `a puntato` — non utilizzano in modo appropriato i DPI messi a loro disposizione
  2234. [P] #2124 `a puntato` — non segnalano immediatamente al datore di lavoro, al dirigente o al preposto le 
  2235. [P] #2125 `a puntato` — rimuovono o modificano senza autorizzazione i dispositivi di sicurezza o di segn
  2236. [P] #2126 `a puntato` — compiono di propria iniziativa operazioni o manovre che non sono di loro compete
  2237. [P] #2127 `a puntato` — non si sottopongono ai controlli sanitari previsti nei loro confronti.
  2240. [**H2**] #2130 `a titolo 2` — Richiamo verbale
  2241. [P] #2131 `a` — Ogni volta che si verifichi un comportamento scorretto di un certo lavoratore ch
  2248. [**H2**] #2138 `a titolo 2` — Lettera di Richiamo
  2249. [P] #2139 `a` — Se il comportamento a carico del singolo LAV si ripete in maniera continuativa, 
  2251. [**H2**] #2141 `a titolo 2` — Sanzione Disciplinare
  2252. [P] #2142 `a` — Qualora il LAV prosegua il comportamento scorretto il DL, anche tramite il RSPP
  2254. [P] #2144 `a puntato` — convoca il LAV in apposita riunione per contestargli l’eventuale addebito e lo s
  2255. [P] #2145 `a puntato` — assegna la sanzione disciplinare conformemente a quanto prescritto da accordi o 
  2257. [P] #2147 `a` — Le norme disciplinari relative alle sanzioni, alle infrazioni in relazione alle 
  2259. [**H2**] #2149 `a titolo 2` — Possibilità di risposta da parte del lavoratore alla sanzione disciplinare
  2260. [P] #2150 `a` — Salvo analoghe procedure previste dai contratti collettivi di lavoro e ferma res
  2261. [P] #2151 `a` — La sanzione disciplinare resta sospesa fino alla pronuncia da parte del collegio
  2262. [P] #2152 `a` — Qualora il DL non provveda, entro dieci giorni dall'invito rivoltogli dall'uffic
  2263. [P] #2153 `a` — Non può tenersi conto ad alcun effetto delle sanzioni disciplinari decorsi due a
  2265. [**H1**] #2155 `a titolo` — Documentazione Collegata
  2266. [P] #2156 `a` — Lettera di richiamo scritto ai lavoratori
  2269. [**H1**] #2159 `a titolo 1` — Gestione DPI
  2270. [**H2**] #2160 `a titolo 2` — Acquisizione di DPI
  2271. [P] #2161 `a` — Il DL o suo incaricato in collaborazione con il RSPP, MC, consultato eventualmen
  2273. [P] #2163 `a puntato` — adeguatezza ai rischi da prevenire, senza comportare di per sé un rischio maggio
  2274. [P] #2164 `a puntato` — adeguatezza alle condizioni esistenti sul luogo di lavoro;
  2275. [P] #2165 `a puntato` — reciproca compatibilità e mantenimento, anche nell'uso simultaneo, della propria
  2277. [P] #2167 `a` — Il DL o suo incaricato all’atto dell’acquisto controlla inoltre che i DPI siano 
  2279. [P] #2169 `a puntato` — dichiarazione di conformità CE da parte del fabbricante
  2280. [P] #2170 `a puntato` — marcatura CE
  2281. [P] #2171 `a puntato` — nota informativa rilasciata da fabbricante (che deve contenere le istruzioni d'u
  2282. [P] #2172 `a puntato` — caratteristiche previste a seguito della valutazione dei rischi
  2284. [**H2**] #2174 `a titolo 2` — Destinazione dei DPI
  2285. [P] #2175 `a` — Il DL o DRG delegato ha l’obbligo di destinare i DPI ad un uso personale. Una vo
  2286. [P] #2176 `a` — L’avvenuta consegna è registrata sul modulo di Dichiarazione di ricevimento dei 
  2288. [P] #2178 `a puntato` — Descrizione dei DPI consegnati (tipologia e codice identificativo)
  2289. [P] #2179 `a puntato` — Dati identificativi del lavoratore a cui è stato consegnato il DPI
  2290. [P] #2180 `a puntato` — Data consegna
  2291. [P] #2181 `a puntato` — Firma del LAV (a convalida dell’avvenuta consegna e dell’impegno al corretto uti
  2293. [P] #2183 `a` — Qualora le circostanze richiedano l'uso di uno stesso DPI da parte di più person
  2294. [**H2**] #2184 `a titolo 2` — Gestione di casi di inadeguatezza ed intolleranza ai DPI
  2296. [P] #2186 `a` — In caso di intolleranza da parte dei LAV, questi ultimi dovranno farne comunicaz
  2298. [P] #2188 `a` — Il DL deve avvalersi del MC per esprimere parere sull’adeguatezza o meno dei DPI
  2300. [**H2**] #2190 `a titolo 2` — Modalità di utilizzazione e mantenimento dei DPI
  2302. [P] #2192 `a` — Per quanto attiene modalità di utilizzazione e mantenimento dei DPI, il DRG inca
  2304. [P] #2194 `a puntato` — Prevedere corrette modalità di utilizzo in funzione delle indicazioni indicate d
  2305. [P] #2195 `a puntato` — Determinare la periodicità di sostituzione in funzione delle indicazioni del fab
  2306. [P] #2196 `a puntato` — nel caso in cui le indicazioni sulla periodicità di sostituzione non siano dispo
  2307. [P] #2197 `a puntato 2` — entità del rischio
  2308. [P] #2198 `a puntato 2` — frequenza dell'esposizione al rischio
  2309. [P] #2199 `a puntato 2` — caratteristiche del posto di lavoro di ciascun lavoratore
  2323. [**H2**] #2213 `a titolo 2` — informazione, formazione e addestramento
  2325. [P] #2215 `a` — IL DL deve:
  2327. [P] #2217 `a puntato` — fornire istruzioni comprensibili per i lavoratori
  2328. [P] #2218 `a puntato` — informare preliminarmente il lavoratore dei rischi dai quali il DPI lo protegge
  2329. [P] #2219 `a puntato` — rendere disponibile nell'azienda ovvero unità produttiva informazioni adeguate s
  2330. [P] #2220 `a puntato` — assicurare una formazione adeguata e organizzare, se necessario, uno specifico a
  2331. [P] #2221 `a puntato` — In ogni caso l'addestramento è obbligatorio:
  2332. [P] #2222 `a puntato 2` — per ogni DPI che, ai sensi del decreto legislativo 4 dicembre 1992, n. 475, appa
  2333. [P] #2223 `a puntato 2` — per i dispositivi di protezione dell'udito
  2335. [P] #2225 `a` — Al fine di espletare gli obblighi di legge; il DL all’atto della consegna dei DP
  2337. [P] #2227 `a puntato` — consegnare al LAV copia della nota informativa sul DPI fornita dal fabbricante;
  2338. [P] #2228 `a puntato` — nel caso in cui sia necessario un addestramento, provvedere ad organizzare tale 
  2339. [P] #2229 `a puntato` — nel caso di DPI particolari, provvedere all’organizzazione di opportuni interven
  2342. [**H2**] #2232 `a titolo 2` — Documentazione Collegata
  2343. [P] #2233 `a` — Dichiarazione di ricevimento dei dispositivi di protezione personale
  2344. [P] #2234 `a` — Comunicazione inadeguatezza DPI
  2345. [**H1**] #2235 `a titolo 1` — Gestione Infrastrutture
  2347. [P] #2237 `a` — Per tutte le macchine presenti in azienda sono state definite le responsabilità,
  2349. [P] #2239 `a` — Per apparecchiature si intendono:
  2351. [P] #2241 `a puntato` — macchine, attrezzature ed impianti necessari per lo svolgimento dell’attività
  2352. [P] #2242 `a puntato` — mezzi di trasporto
  2353. [P] #2243 `a puntato` — attrezzatura per la movimentazione dei materiali
  2354. [P] #2244 `a puntato` — dispositivi di protezione individuale di 3° categoria
  2355. [P] #2245 `a puntato` — dispositivi antincendio
  2356. [P] #2246 `a puntato` — attrezzature sanitarie
  2359. [**H2**] #2249 `a titolo 2` — Documentazione Collegata
  2360. [P] #2250 `a` — Elenco Attrezzature e Piano di manutenzione annuale
  2361. [P] #2251 `a` — Scheda manutenzione
  2363. [**H1**] #2253 `a titolo 1` — Gestione Lavoratori appartenenti a gruppi particolarmente sensibili al rischio
  2364. [**H2**] #2254 `a titolo 2` — Lavoratrici gestanti, puerpere o in periodo di allattamento (D.Lgs. 151/2001)
  2366. [P] #2256 `a` — È vietato adibire le lavoratrici al trasporto e al sollevamento di pesi, nonché 
  2368. [P] #2258 `a elenchi alfabetici` — quelli previsti dal decreto legislativo 4 agosto 1999, n. 345 e dal decreto legi
  2369. [P] #2259 `a elenchi alfabetici` — quelli indicati nella tabella allegata al decreto del Presidente della Repubblic
  2370. [P] #2260 `a elenchi alfabetici` — quelli che espongono alla silicosi e all'asbestosi, nonchè alle altre malattie p
  2372. [P] #2262 `a elenchi alfabetici` — i lavori che comportano l'esposizione alle radiazioni ionizzanti: durante la ges
  2373. [P] #2263 `a elenchi alfabetici` — i lavori su scale ed impalcature mobili e fisse: durante la gestazione e fino al
  2375. [P] #2265 `a elenchi alfabetici` — i lavori di manovalanza pesante: durante la gestazione e fino al termine del per
  2376. [P] #2266 `a elenchi alfabetici` — i lavori che comportano una stazione in piedi per più di metà dell'orario o che 
  2377. [P] #2267 `a elenchi alfabetici` — i lavori con macchina mossa a pedale, o comandata a pedale, quando il ritmo del 
  2378. [P] #2268 `a elenchi alfabetici` — i lavori con macchine scuotenti o con utensili che trasmettono intense vibrazion
  2380. [P] #2270 `a elenchi alfabetici` — i lavori di assistenza e cura degli infermi nei sanatori e nei reparti per malat
  2382. [P] #2272 `a elenchi alfabetici` — i lavori agricoli che implicano la manipolazione e l'uso di sostanze tossiche o 
  2383. [P] #2273 `a elenchi alfabetici` — i lavori di monda e trapianto del riso: durante la gestazione e fino al termine 
  2384. [P] #2274 `a elenchi alfabetici` — i lavori a bordo delle navi, degli aerei, dei treni, dei pullman e di ogni altro
  2390. [P] #2280 `a` — Tra i lavori pericolosi, faticosi ed insalubri sono inclusi quelli che comportan
  2392. [P] #2282 `a` — A. Lavoratrici gestanti.
  2393. [P] #2283 `a` — 1. Agenti:
  2394. [P] #2284 `a` — a) agenti fisici: lavoro in atmosfera di sovrapressione elevata, ad esempio in c
  2395. [P] #2285 `a` — b) agenti biologici:
  2396. [P] #2286 `a` — toxoplasma;
  2397. [P] #2287 `a` — virus della rosolia, a meno che sussista la prova che la lavoratrice e' sufficie
  2398. [P] #2288 `a` — c) agenti chimici: piombo e suoi derivati, nella misura in cui questi agenti pos
  2399. [P] #2289 `a` — 2. Condizioni di lavoro: lavori sotterranei di carattere minerario.
  2401. [P] #2291 `a` — B. Lavoratrici nel periodo successivo al parto.
  2402. [P] #2292 `a` — 1. Agenti:
  2403. [P] #2293 `a` — a) agenti chimici: piombo e suoi derivati, nella misura in cui tali agenti posso
  2404. [P] #2294 `a` — 2. Condizioni di lavoro: lavori sotterranei di carattere minerario.
  2407. [P] #2297 `a` — La lavoratrice è addetta ad altre mansioni per il periodo per il quale è previst
  2408. [P] #2298 `a` — La lavoratrice è, altresì, spostata ad altre mansioni nei casi in cui i servizi 
  2415. [**H2**] #2305 `a titolo 2` — Lavoratori minori (D.Lgs. 345/99)
  2416. [P] #2306 `a` — L'età minima per l'ammissione al lavoro è fissata al momento in cui il minore ha
  2417. [P] #2307 `a` — Non verranno assegnati ad adolescenti, ovvero minori di età compresa tra i 15 e 
  2419. [P] #2309 `a` — A. Lavorazioni che espongono ai seguenti agenti:
  2420. [P] #2310 `a` — 1. Agenti fisici:
  2422. [P] #2312 `a elenchi alfabetici` — atmosfera a pressione superiore a quella naturale, ad esempio in contenitori sot
  2423. [P] #2313 `a elenchi alfabetici` — rumori con esposizione superiore al valore limite previsti dal D.Lgs. 81/2008 e 
  2424. [P] #2314 `a` — 2. Agenti biologici:
  2426. [P] #2316 `a elenchi alfabetici` — agenti biologici dei gruppi 3 e 4, ai sensi del titolo X del D.Lgs. 81/2008 e s.
  2427. [P] #2317 `a` — 3. Agenti chimici:
  2429. [P] #2319 `a elenchi alfabetici` — sostanze e preparati classificati tossici (T), molto tossici (T+), corrosivi (C)
  2430. [P] #2320 `a elenchi alfabetici` — sostanze e preparati classificati nocivi (Xn) ai sensi dei decreti legislativi d
  2431. [P] #2321 `a elenchi alfabetici` — sostanze e preparati classificati irritanti (Xi) e comportanti uno o più rischi 
  2438. [P] #2328 `a` — B. Processi e lavori:
  2439. [P] #2329 `a` — Processi e lavori di cui all'allegato XLII del D.Lgs. 81/2008 e s.m.i..
  2440. [P] #2330 `a` — Lavori di fabbricazione e di manipolazione di dispositivi, ordigni ed oggetti di
  2441. [P] #2331 `a` — Lavori in serragli contenenti animali feroci o velenosi nonché condotta e govern
  2442. [P] #2332 `a` — Lavori di mattatoio.
  2443. [P] #2333 `a` — Lavori comportanti la manipolazione di apparecchiature di produzione, di immagaz
  2444. [P] #2334 `a` — Lavori su tini, bacini, serbatoi, damigiane o bombole contenenti agenti chimici 
  2445. [P] #2335 `a` — Lavori edili di demolizione, allestimento e smontaggio delle armature esterne ed
  2446. [P] #2336 `a` — Lavori comportanti rischi elettrici da alta tensione.
  2447. [P] #2337 `a` — Lavori il cui ritmo è determinato dalla macchina e che sono pagati a cottimo.
  2448. [P] #2338 `a` — Esercizio dei forni a temperatura superiore a  come, ad esempio, quelli per la p
  2449. [P] #2339 `a` — Lavorazioni nelle fonderie.
  2450. [P] #2340 `a` — Processi elettrolitici.
  2451. [P] #2341 `a` — Produzione di gomma sintetica; lavorazione della gomma naturale e sintetica.
  2452. [P] #2342 `a` — Produzione dei metalli ferrosi e non ferrosi e loro leghe.
  2453. [P] #2343 `a` — Produzione e lavorazione dello zolfo.
  2454. [P] #2344 `a` — Lavorazioni di escavazione, comprese le operazioni di estirpazione del materiale
  2455. [P] #2345 `a` — Lavorazioni in gallerie, cave, miniere, torbiere e industria estrattiva in gener
  2456. [P] #2346 `a` — Lavorazione meccanica dei minerali e delle rocce, limitatamente alle fasi di tag
  2457. [P] #2347 `a` — Lavorazione dei tabacchi.
  2458. [P] #2348 `a` — Lavori di costruzione, trasformazione, riparazione, manutenzione e demolizione d
  2459. [P] #2349 `a` — Produzione di calce ventilata.
  2460. [P] #2350 `a` — Lavorazioni che espongono a rischio silicotigeno.
  2461. [P] #2351 `a` — Manovra degli apparecchi di sollevamento a trazione meccanica, ad eccezione di a
  2462. [P] #2352 `a` — Lavori in pozzi, cisterne ed ambienti assimilabili.
  2463. [P] #2353 `a` — Lavori nei magazzini frigoriferi.
  2464. [P] #2354 `a` — Lavorazione, produzione e manipolazione comportanti esposizione a prodotti farma
  2465. [P] #2355 `a` — Condotta dei veicoli di trasporto e di macchine operatrici semoventi con propuls
  2466. [P] #2356 `a` — Operazioni di metallizzazione a spruzzo.
  2467. [P] #2357 `a` — Legaggio ed abbattimento degli alberi.
  2468. [P] #2358 `a` — Pulizia di camini e focolai negli impianti di combustione.
  2469. [P] #2359 `a` — Apertura, battitura, cardatura e pulitura delle fibre tessili, del crine vegetal
  2470. [P] #2360 `a` — Produzione e lavorazione di fibre minerali e artificiali.
  2471. [P] #2361 `a` — Cernita e trituramento degli stracci e della carta usata.
  2472. [P] #2362 `a` — Lavori con impieghi di martelli pneumatici, mole ad albero flessibile e altri st
  2473. [P] #2363 `a` — Produzione di polveri metalliche.
  2474. [P] #2364 `a` — Saldatura e taglio dei metalli con arco elettrico o con fiamma ossidrica o ossia
  2475. [P] #2365 `a` — Lavori nelle macellerie che comportano l'uso di utensili taglienti, seghe e macc
  2484. [**H2**] #2374 `a titolo 2` — Lavoratori diversamente abili
  2485. [P] #2375 `a` — All’assunzione di soggetti diversamente abili il datore di lavoro, in collaboraz
  2488. [**H2**] #2378 `a titolo 2` — Lavoratori stranieri
  2489. [P] #2379 `a` — All’assunzione di lavoratori stranieri, l’Ufficio del Personale verifica il grad
  2490. [**H1**] #2380 `a titolo 1` — Gestione Acquisti
  2492. [P] #2382 `a` — Per quanto concerne l’acquisto di nuove sostanze, attrezzature e macchinari da i
  2494. [P] #2384 `a puntato` — valutare ed eventualmente qualificare i fornitori, con la possibilità di dare pr
  2495. [P] #2385 `a puntato` — monitorare i fornitori e fidelizzarli, abituandoli alle prassi in voga presso l’
  2496. [P] #2386 `a puntato` — richiedere già in fase preventiva la documentazione prevista dalla legislazione 
  2497. [P] #2387 `a puntato` — scegliere l’acquisto che permetta di ridurre al minimo i possibili rischi
  2498. [P] #2388 `a puntato` — controllare e monitorare le forniture
  2500. [**H1**] #2390 `a titolo 1` — Gestione delle lavorazioni affidate in appalto
  2502. [P] #2392 `a` — Il datore di lavoro, in caso di affidamento di lavori all’impresa appaltatrice o
  2504. [P] #2394 `a puntato` — verifica l’idoneità tecnico professionale delle imprese appaltatrici o dei lavor
  2505. [P] #2395 `a puntato` — fornisce agli stessi soggetti dettagliate informazioni sui rischi specifici esis
  2507. [P] #2397 `a` — Il datore di lavoro, con i datori di lavoro dei subappaltatori:
  2509. [P] #2399 `a puntato` — cooperano all’attuazione delle misure di prevenzione e protezione dai rischi sul
  2510. [P] #2400 `a puntato` — coordinano gli interventi di protezione e prevenzione dai rischi cui sono espost
  2512. [**H2**] #2402 `a titolo 2` — D.U.V.R.I.
  2513. [P] #2403 `a` — Il datore di lavoro committente promuove la cooperazione ed il coordinamento, el
  2514. [P] #2404 `a` — Nell’ambito dello svolgimento di attività in regime di appalto o subappalto, il 
  2520. [**H2**] #2410 `a titolo 2` — Informazioni sui requisiti tecnico professionali delle ditte appaltatrici
  2521. [P] #2411 `Subtitle` — In occasione dell’affidamento di lavori all’impresa appaltatrice o a lavoratori 
  2523. [P] #2413 `a puntato` — iscrizione alla camera di commercio, industria e artigianato con oggetto sociale
  2524. [P] #2414 `a puntato` — documento di valutazione dei rischi di cui all’articolo 17, comma 1, lettera a) 
  2525. [P] #2415 `a puntato` — specifica documentazione attestante la conformità alle disposizioni di cui al D.
  2526. [P] #2416 `a puntato` — elenco dei dispositivi di protezione individuali forniti ai lavoratori
  2527. [P] #2417 `a puntato` — nomina del responsabile del servizio di prevenzione e protezione, degli incarica
  2528. [P] #2418 `a puntato` — nominativo del rappresentante dei lavoratori per la sicurezza
  2529. [P] #2419 `a puntato` — attestati inerenti alla formazione delle suddette figure e dei lavoratori previs
  2530. [P] #2420 `a puntato` — elenco dei lavoratori risultanti dal libro matricola e relativa idoneità sanitar
  2531. [P] #2421 `a puntato` — documento unico di regolarità contributiva
  2532. [P] #2422 `a puntato` — dichiarazione di non essere oggetto di provvedimenti di sospensione o interditti
  2535. [P] #2425 `a` — N.B.: Nel caso si rientri nel campo di applicazione del Titolo IV del D.Lgs. 81/
  2539. [**H1**] #2429 `a titolo 1` — Dichiarazione del Datore di Lavoro
  2541. [P] #2431 `a` — Il/la sottoscritto/a, CIARAMITARO AMALIA in qualità di Datore di Lavoro della N2
  2543. [P] #2433 `Subtitle` — DICHIARA
  2545. [P] #2435 `a` — che il procedimento sulla valutazione dei rischi ex art. 17 del D.Lgs. n. 81/200
  2549. [P] #2439 `a` — GORGONZOLA (MI), lì 18 11 2025
  2554. [**T110**] 2x3 DYNAMIC — ...

---

*Generated programmatically by DVR template analysis script. Source: `templates/DVR RISCHIO MASTER.docx`*