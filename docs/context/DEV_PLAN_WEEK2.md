# Dev Plan — Week 1 Review Follow-up

> **Meta**: Piano d'azione post-demo Week 1 con Luca Marchetti. Ordinato dal più semplice al più difficile.
> **Status**: Phase 1 + Phase 2 + Phase 5 + **Phase 8** DONE (2026-04-27). Next: e2e test live, push staging, demo martedì.
> **Created**: 2026-04-24
> **Last update**: 2026-04-27 (Phase 8 completata in anticipo — A/B/C/D/E + bonus B22 fix)
> **Next checkpoint**: Martedì 2026-04-29, 10:30 (follow-up call con Luca)

---

## Come usare questo documento

- **Gregor**: leggi "Pre-martedì (MUST)" per lavoro urgente. Il resto è roadmap 4-7 settimane.
- **Claude in chat futura**: questo file è il riassunto completo della call Week 1 e delle decisioni prese. Se parte una nuova conversazione, **leggi prima questo file** per capire lo stato e cosa fare. Le fasi sono numerate in ordine di complessità crescente.

---

## Context snapshot

### Cosa è successo
Il 24 aprile 2026 ci siamo riuniti con Luca Marchetti (N2O) per il review Week 1 dell'applicativo DVR. Luca la sera prima ha creato un'azienda di prova, inserito dati, e generato un primo DVR (`prova.docx.pdf`, 39 pagine). La call è durata 1h37, trascrizione completa nel file Gemini Notes `N2O - DVR App Settimana 1 - 2026_04_24 16_05 CEST - Appunti di Gemini.pdf`. Durante la call abbiamo anche testato il modulo SDS con una scheda reale (`MSDS-00001-M-006 Vanilla-v13_260424_165613.pdf` di MAYAQUA SRL) — estrazione funzionante al 100%.

### Cosa funziona oggi (stato Week 1)
- Dashboard con aziende, azioni rapide, gerarchia aziende → sopralluoghi → documenti
- Inserimento azienda, persone, ambienti, attrezzature
- AI suggerisce rischi in base a tipo attività / ambiente
- AI suggerisce misure di miglioramento
- Calcolo `I = 2D + P` con livelli (Accettabile / Modesto / Grave / Gravissimo)
- Tabella DPI + rischi specifici per persona
- Workflow sopralluogo → firma → generazione documento
- Download DVR in Word + link Google Drive
- Estrazione SDS da PDF con nome prodotto, produttore, pittogrammi GHS, frasi H (100% accuracy su SDS Mayaqua)
- Struttura generale Word template (formattazione tabelle, colonna indice `I = P + 2*D`, livelli colorati)

### Cosa NON funziona (bug critico visibile in `prova.docx.pdf`)
**Il DVR generato è il master template N2O, non un DVR sull'azienda reale.**
- Pag 1 (cover) vuota
- Nessun dato azienda, ambienti, persone, attrezzature specifiche
- Tutte le 11 categorie rischio flaggate "SI" di default senza filtro
- Contenuto statico include entries che non possono applicarsi a un'azienda test (amianto, CVM, 2-naftilammina, lavori in vasche, ascensori montacarichi)
- Sezioni "Come da documenti allegati" rimandano ad allegati che non esistono (MMC, VDT, Stress, Biologico, Fire)
- Header statici: `PROVA`, `Revisione 00`, `24.04.26` non parametrizzati

Vedi **Fase 8** per la fix di questo bug (è il lavoro più corposo e critico).

### Decisioni di scope dalla call
- **"Prima consolidiamo il DVR"** — Luca ha detto di fermarsi sulla parte di layout/branding avanzato e finalizzare il core DVR
- **Scadenze DVR automatiche**: NON servono. N2O gestisce rinnovi annuali con foglio quote esterno
- **Questionario Stress Lavoro Correlato**: NON fare intervista completa. Intuire da osservazioni sopralluogo + misure correttive AI
- **Parametri tecnici MMC** (altezza, peso, angolo, dislocazione): NON chiedibili al cliente. Usare standard NIOSH, fine-tune se necessario
- **Mansioni**: free text (le categorie merceologiche sono infinite)
- **Revisioni DVR**: spesso fatte al telefono, non richiede sopralluogo fisico → serve pulsante "Aggiorna DVR"
- **Principio generale**: "Il nostro deve essere solo una questione di revisione, non di inserimento del dato" — AI pre-flagga/pre-popola, utente conferma/override

### Cosa manda Luca lunedì 2026-04-28
- ✅ Lista rischi completa con sottocategorie (già girata a metà call, è l'Excel dalla chiavetta)
- ✅ Lista tipologie contrattuali (già arrivata via email — vedi sezione "Reference data" più sotto, 12 voci)
- ⏳ Lista parametri stress lavoro correlato

---

## Action plan — dal più semplice al più difficile

### 🟢 Fase 1 — Quick wins (~4h)

| # | Cosa | Dove | Effort | Stato |
|---|------|------|--------|-------|
| 1.1 | Rename "Lavori in quota ai veicoli" → **"Utilizzo attrezzature speciali"** | Qualifiche persona | 10 min | ⚠️ **BLOCCATO** — stringa non trovata nel codice. Qualifiche è textarea libera (step-persone.tsx:535). Forse Luca si riferisce a una vecchia UI o all'autocomplete AI. Da chiarire. |
| 1.2 | Rimuovi colonna **"Verifiche periodiche"** dalle attrezzature (mantenere "Training aggiornamento") | Tabella attrezzature | 10 min | ✅ **DONE** — UI nascosta in `step-attrezzature.tsx`, campo DB intatto |
| 1.3 | Mansione persona: dropdown → **free text input** | Form persona | 20 min | ✅ **DONE** — già free-text Input (step-persone.tsx:431) |
| 1.4 | MMC: area iniziale da **rossa → verde** di default | Valutazione MMC schermata | 15 min | ✅ **DONE** — `DEFAULT_LIFT.distanza` 40→25, `peso_reale` 15→10 (mmc-form.tsx:251). IR iniziale ora ~0.4 verde invece di ~1.01 rosso |
| 1.5 | Rimuovi scadenza automatica DVR (flag interno + campo + reminder/notifica) | Backend + UI | 30 min | ✅ **DONE** — KPI tile "Scadenze" nascosto, todo "DVR in scadenza" rimosso, colonna table → "Creata il" (`created_at`). Sostituito anche su `aziende/page.tsx` e `survey/page.tsx`. Campo DB `data_scadenza_dvr` mantenuto |
| 1.6 | Dropdown **Tipologia contrattuale** con le 12 voci (vedi Reference data) | Form persona | 45 min | ✅ **DONE** — `TIPOLOGIE_CONTRATTUALI` aggiornato in step-persone.tsx |
| 1.7 | Fix formula display Word: `= 2; D = 3; I = 8` → `P = 2; D = 3; I = 8` (manca la "P" da pag 15 in poi) | Template Word | 20 min | ⚠️ **BLOCCATO** — vedi nota 1.7-1.10 in fondo |
| 1.8 | Rimuovi pagine vuote orfane nel Word (pag 1 cover, pag 3 header-only, pag 33, pag 36) | Template Word | 30 min | ⚠️ **BLOCCATO** — vedi nota 1.7-1.10 |
| 1.9 | Header Word parametrico: `PROVA` → nome azienda DB; `24.04.26` → data revisione | Template Word header | 30 min | ⚠️ **BLOCCATO** — vedi nota 1.7-1.10 |
| 1.10 | Date nel Word generato: usa data revisione scelta, non `today()` default | Generator logic | 30 min | ⚠️ **BLOCCATO** — vedi nota 1.7-1.10 |

**Nota 1.7-1.10 (Word template fixes)** — Investigation agent ha trovato un indizio critico prima di stallarsi: le stringhe buggate (`I = P+`, header `PROVA`, ecc.) appaiono **nel template `templates/DVR RISCHIO MASTER.docx` stesso**, mentre `dvr_master.py:260` costruisce il documento con `Document()` da zero (senza riferirsi al template). Sospetto: `prova.docx.pdf` è il template master con find-and-replace manuale, NON output del generatore corrente. Se confermato:
- I fix 1.7-1.10 vanno fatti nel binario `.docx` del template (non in Python)
- Oppure devono aspettare Fase 8 (DVR vero engine)

Da decidere con Gregor prima di procedere.

---

### 🟢 Fase 2 — Bug fix puntuali (~1 giornata) — ✅ DONE 2026-04-27

| # | Cosa | Effort | Stato |
|---|------|--------|-------|
| 2.1 | Autocomplete attrezzature: primo carattere non deve salvare l'attrezzatura col nome vuoto | 2h | ✅ **DONE** — split tra `updateLocal` (state) e `commitAttrezzatura` (POST/PUT). Text input persiste su blur/Enter, checkbox subito. Aggiunto `inFlightRef` per serializzare POST per row id (evitava duplicati). Bonus fix in `toggleSuggested` che non aggiornava `persistedIds` dopo POST → causava POST duplicati su edit successivi |
| 2.2 | Disable rischio: click su "disabilita" deve rimuovere il rischio dal DVR generato | 3h | ✅ **DONE** — il generator filtrava già su `applicabile`. Il bug vero era nel cleanup `useEffect` di step-rischi.tsx: `clearTimeout` invece di flush. Toggle + step-forward entro 800ms perdeva il save. Refactored a `pendingPayloadsRef` + flush fire-and-forget on unmount (i ref `apiFetchRef`/`aziendaIdRef` evitano re-fire premature) |
| 2.3 | Attrezzature: associazione obbligatoria a ambiente | 2h | ✅ **DONE** (~4h reale — più grosso del previsto). Migration `f7b8c9d0e1f2_add_attrezzatura_ambiente_id.py` (+ merge dei 2 alembic head pre-esistenti). Aggiunto `ambiente_id` FK al model + relationship sull'`Ambiente`. Schema Pydantic require `ambiente_id` su create. API valida che l'ambiente appartenga all'azienda. UI step-attrezzature.tsx ora SCOPED per-ambiente: switching ambiente cambia la lista. Survey snapshot include `ambiente_id` |
| 2.4 | "Cancerogeno" default in sala consumazione: va disattivato (dipende da 2.2 + filtro categoria) | 1h | ✅ **DONE** — aggiunto `DEFAULT_APPLICABLE_PER_AMBIENTE` map in step-rischi.tsx + `DEFAULT_APPLICABLE_FALLBACK` conservativo per tipi sconosciuti ("Sala consumazione", "Bar", "Reception"). Cancerogeni/Biologici auto-on solo in laboratorio; per gli altri: opt-in esplicito. `synthesizeValutazione` usa il map invece di `applicabile: true` hard-coded |

---

### 🟡 Fase 3 — Feature semplici confermate (~2 giornate)

#### SDS

| # | Cosa | Effort |
|---|------|--------|
| 3.1 | SDS: pulsante **"+"** aggiungi scheda | 2h |
| 3.2 | SDS: upload multiplo in una sessione | 3h |
| 3.3 | SDS: UI click esplicito per aggiungere frase H (sostituisce "premi virgola per aggiungere" che non funziona) | 2h |

#### Revisioni DVR

| # | Cosa | Effort |
|---|------|--------|
| 3.4 | Pulsante **"Aggiorna DVR"** nelle azioni rapide dashboard | 4h |
| 3.5 | Flusso aggiornamento: scegli cliente → apre sopralluogo in modalità revisione | 4h |
| 3.6 | Campo **"Motivazione revisione"** obbligatorio | 1h |
| 3.7 | Data revisione **modificabile manualmente** | 1h |

#### Layout / branding

| # | Cosa | Effort |
|---|------|--------|
| 3.8 | Pulsante **"Allega logo cliente"** post-sopralluogo | 3h |
| 3.9 | Copertina standard N2O nel Word con riempimento reale dati azienda (oggi la cover è vuota a pag 1) | 4h |

#### Valutazioni — soglie e toggle

| # | Cosa | Effort |
|---|------|--------|
| 3.10 | VDT: soglia **>20h/settimana = Esposto** (flag automatico) | 2h |
| 3.11 | MMC: toggle **Uomini (25kg) / Donne (20kg)** con valori standard NIOSH | 3h |
| 3.12 | Verifica calcolo `I = 2D + P` con bande 3-4/5-6/7-8/9-12 → Accettabile / Modesto / Grave / Gravissimo | 1h |

---

### 🟡 Fase 4 — Miglioramenti medi (~3 giornate)

| # | Cosa | Effort |
|---|------|--------|
| 4.1 | MMC per persona (non per mansione) + lista completa dipendenti flaggabili | 1 giorno |
| 4.2 | MMC: parametri standard default (altezza/peso/dislocazione verticale/angolo asimmetria), fine-tune opzionale | 4h |
| 4.3 | DPI override individuale per persona (oltre al set base da mansione, es. "usa muletto") | 4h |
| 4.4 | Storico revisioni DVR: inserimento automatico riga con progressivo `01, 02, ...` alla rigenerazione | 4h |
| 4.5 | Aggregazione categoria rischio per ambiente = **media** delle sottocategorie. Iterare se fulviante (provare prima, adattare poi) | 1 giorno |
| 4.6 | Filtro categoria Cancerogeni/Amianto: NON includere in DVR se azienda non è cantiere/laboratorio | 4h |

---

### 🟠 Fase 5 — AI "Flegga per me" buttons (~4 giornate) — ✅ DONE 2026-04-27

Principio: "non far scrivere all'utente, fargli solo confermare/correggere".

Anticipata di 2 settimane rispetto alla roadmap originale (era pianificata per 5-9 maggio) perché Gregor ha scelto opzione 3 — bundle Phase 2 + Phase 5.

| # | Cosa | Effort | Stato |
|---|------|--------|-------|
| 5.1 | Button "Flegga per me" in sezione **DPI persona** → AI genera set DPI per mansione + ambiente | 1 giorno | ✅ **DONE** (combinato con 5.2 in un solo endpoint). Backend: `services/ai/mansione_protocol_suggester.py` con `suggest_mansione_protocol(mansione, ambienti, attrezzature) → MansioneProtocolSuggerito`. Carica persone con quella mansione → ambienti dove operano → attrezzature in quegli ambienti, passa il contesto al modello. Catalogo DPI completo serializzato nel prompt; codici invalidi filtrati server-side. UI: button "Flegga con AI" nel header card di step-dpi-rischi.tsx, **merge non replace** (i flag esistenti non vengono persi) |
| 5.2 | Button "Flegga per me" in sezione **Rischi specifici persona** | 1 giorno | ✅ **DONE** (combinato con 5.1). Stesso endpoint restituisce sia `dpi_codes` che `rischi_specifici_codes` — un solo round-trip per protocollo completo. Catalogo `RISCHI_SPECIFICI_CATALOG` serializzato, validazione server-side dei codici. Toast mostra `+N DPI, +M rischi` + motivazione AI |
| 5.3 | Button "Genera attrezzature" in sezione **Attrezzature ambiente** → AI suggerisce attrezzature tipiche per macrosettore | 1 giorno | ✅ **DONE**. Backend: `services/ai/attrezzature_suggester.py` con `suggest_attrezzature(ambiente, azienda, existing_descriptions)`. Endpoint `POST /aziende/{a}/attrezzature/suggerisci/{ambiente_id}` esclude duplicati lato server. UI: card violetta in step-attrezzature.tsx con button "Genera con AI" + chip cliccabili (motivazione nel tooltip). Stato AI per-ambiente (`aiSuggestionsByAmbiente`) — switching non perde le suggestions degli altri ambienti |
| 5.4 | Prompt engineering strutturati (profilo ruolo + output breve stile Gemini) + validation layer | 4h | ✅ **DONE** (consolidato in 5.1-5.3, no PR separato). Pattern uniforme: Pydantic schemas con field descriptions ricche, `SYSTEM_PROMPT` strutturato (regole vincolanti + formato output), validazione server-side post-response (filter su catalog per i codici DPI/rischi; filter su existing per attrezzature). Gli schemas usano `model_config = ConfigDict(extra="forbid")` per enforcement strict |

---

### 🟠 Fase 6 — Permission system (~4 giornate)

| # | Cosa | Effort |
|---|------|--------|
| 6.1 | Profilo **Admin**: vede e modifica tutto, può aprire revisione post-firma | 1 giorno |
| 6.2 | Profilo **DVR** (non-admin, es. stagista Andrea): vede tutti i DVR in dashboard, modifica solo le **proprie** rilevazioni | 2 giorni |
| 6.3 | Pulsante **"Apri revisione"** richiesto prima di modificare DVR firmato | 4h |
| 6.4 | DVR firmato = 100% chiuso, non modificabile da profilo DVR normale | 4h |

---

### 🔴 Fase 7 — Risk library completa (~1 settimana)

| # | Cosa | Effort |
|---|------|--------|
| 7.1 | Importare Excel Luca: 11 macrocategorie (strutture, macchine, impianti elettrici, incendi/esplosioni, chimici, fisici, biologici, cancerogeni, organizzativi, psicologici, ergonomici) con tutte sottocategorie e P/D default | 2 giorni |
| 7.2 | Schema DB + seed: pericolo → rischio → condizioni impiego → misure prevenzione → DPI consigliati | 2 giorni |
| 7.3 | UI: lista filtrata per ambiente + pulsante `+` per aggiungere dal catalogo completo | 1 giorno |
| 7.4 | Link normativa aggiornata per ogni rischio (dalla chiavetta Luca) | 1 giorno |

---

### 🔴 Fase 8 — DVR vero (non master template) (~2 settimane) — ✅ DONE 2026-04-27

**Surprise scoping finding**: il generator era **già data-driven** (iterazione su `ambienti`, filtro per `applicabile` flag, fallback per dati mancanti). Il bug "DVR = master template" era principalmente upstream (vedi B22 bonus fix sotto). Phase 8 si è quindi concentrata su completare le gap reali in 1 sessione invece di 2 settimane.

| # | Cosa | Effort | Stato |
|---|------|--------|-------|
| 8.1 | Engine genera DVR con dati reali (cover page polish, P.IVA + ATECO + revisione versionata, safe ragione_sociale fallback) | 3 giorni | ✅ **DONE** — `_add_cover_page` accetta version param, mostra "Revisione 01 — 27/04/2026", aggiunti P.IVA/ATECO, fix crash su ragione_sociale=None |
| 8.2 | **DVR esploso per ambiente**: lista attrezzature per ogni ambiente in Parte III | 3 giorni | ✅ **DONE** — `_add_environment_section` ora emette anche `Macchine, Attrezzature ed Impianti — <NOME AMBIENTE>` con tabella filtrata via `attrezzatura.ambiente_id` (FK già esistente da Phase 2.3) |
| 8.3 | AI flagga rischi applicabile per ambiente (LLM su ambiente.tipo + descrizione + attrezzature + ATECO) | 2 giorni | ✅ **DONE** — nuovo `services/ai/rischi_suggester.py` con `suggest_rischi(ambiente, azienda, attrezzature)`. Endpoint `POST /aziende/{a}/ambienti/{e}/rischi/suggerisci`. UI button "Flegga rischi con AI" su step-rischi.tsx con merge non-replace + sintesi banner. |
| 8.4 | Pre-popolazione settoriale: aggregato di attrezzature/rischi/sostanze da DVR completati di altre aziende stesso ATECO | 2 giorni | ✅ **DONE** — nuovo `services/sector_prepopulator.py` con aggregazione per ambiente.tipo. Endpoint `GET /aziende/{a}/sector-summary`. UI banner `<SectorSuggestions>` sopra il wizard, auto-hides quando sector_size=0. Sole org-scoped (no cross-tenant data leakage). |
| 8.5 | SDS estratti → tabella DVR (pittogrammi GHS, frasi H, frasi P) | 2 giorni | ✅ **DONE** — `_add_sostanze_table` ora 4 colonne (nome/produttore/stato/pittogrammi GHS) + blocco dettaglio per-sostanza con frasi H e P. Self-hides quando nessuna SDS data. |

**Bonus 🐛 fix critico (B22)** scoperto durante audit: il frontend salvava nomi corti (`Elettrici`, `Incendio`, `Chimici`...) ma il DVR generator faceva lookup con nomi lunghi (`Impianti Elettrici`, `Incendio-Esplosioni`, `Agenti Chimici`...). Risultato: la SI/NO checklist mostrava sempre **NO** indipendentemente dai flag dell'operatore. Questo da solo spiega perché `prova.docx.pdf` sembrava il master template.

Fix: `services/reference_data.py` espone `CATEGORIA_SHORT_TO_LONG` + `CATEGORIA_LONG_TO_SHORT` + `normalize_categoria_to_long()`. Applicata ai 2 lookup site in `dvr_master.py:1126` e `dvr_master.py:1183`. AI suggester restituisce nomi corti (allineato al DB) con doppio-direzione filter server-side.

---

### 🔴 Fase 9 — Allegati completi (~3 settimane)

| # | Cosa | Effort |
|---|------|--------|
| 9.1 | Allegato **MMC** completo (NIOSH con Factor Tables A-F + output per persona) | 1 settimana |
| 9.2 | Allegato **VDT** completo (checklist + soglia esposizione + misure) | 3 giorni |
| 9.3 | Allegato **Stress Lavoro Correlato**: parametri osservativi da sopralluogo (pausa pasto, orario flessibile, mezzi pubblici, lavoro verticale/orizzontale, evoluzione carriera) → misure correttive AI. **NO questionario completo**. | 1 settimana |

---

### ⚫ Fase 10 — Bonus avanzati (rimandati)

| # | Cosa | Effort |
|---|------|--------|
| 10.1 | Scraping sito cliente → estrai logo, colori, font → applica a DVR con branding cliente | 1 settimana |
| 10.2 | Note/commenti utente per capitolo del DVR generato (feedback loop su documento) | 3 giorni |

---

## Roadmap sintetica

| Settimana | Periodo | Fasi | Deliverable |
|-----------|---------|------|-------------|
| **0 (MUST)** | 24-29 apr | Fasi 1-2 | Demo Week 2 pulita per call martedì |
| **1** | 28 apr - 2 mag | Fase 3 + inizio Fase 4 | Revisioni DVR + MMC/VDT base |
| **2** | 5-9 mag | Completa Fase 4 + Fase 5 | AI "Flegga per me" |
| **3** | 12-16 mag | Fase 6 | Permission system |
| **4** | 19-23 mag | Fase 7 | Risk library |
| **5-6** | 26 mag - 6 giu | Fase 8 | DVR vero |
| **7-9** | 9-27 giu | Fase 9 | Allegati MMC / VDT / Stress |
| **Buffer** | 30 giu+ | Fase 10 | Branding scraping, polish |

---

## Pre-martedì 29 apr (MUST) — stato 2026-04-27

Originale check-list:
- ✅ Tutti i task Fase 1 (1.1 → 1.10) — fatto entro 24/04 (1.7-1.10 bloccati su template Word, vedi nota 1.7-1.10)
- ✅ Tutti i task Fase 2 (2.1 → 2.4) — **fatto 27/04**
- ⏳ Fase 3: 3.4-3.7 (workflow Aggiorna DVR), 3.8 (logo cliente), 3.10-3.12 (VDT soglia, MMC M/F) — **non fatto**, scelta consapevole di anticipare Phase 5 + Phase 8
- ⏳ Fase 4: 4.1 (MMC per persona), 4.3 (DPI override), 4.4 (storico revisioni auto) — **non fatto**, idem

**Bonus rispetto al piano originale**:
- ✅ Fase 5 (5.1-5.4) anticipata di 2 settimane — bottoni "Genera con AI" su attrezzature, DPI, rischi specifici. Era pianificata per 5-9 maggio. Decisione presa con Gregor il 27/04 (opzione 3: bundle Phase 2 + Phase 5).
- ✅ **Fase 8 (8.1-8.5) anticipata di 4-5 settimane** — era roadmap settimane 5-6 (fine maggio). Bundle eseguito 27/04 + bonus B22 fix critico. Vedi sezione "Fase 8" sopra per dettaglio.

Demo martedì può girare attorno a:
1. **Bug fixati**: autocomplete attrezzature, disable rischio (era invisibile bug di flush), Cancerogeni che spariscono dai contesti non applicabili
2. **Modello dati pulito**: attrezzature ora obbligatoriamente legate a un ambiente (UI scoped per-ambiente, switching cambia la lista)
3. **AI buttons** (il "wow" moment): "Genera con AI" su attrezzature di un ambiente, "Flegga con AI" su DPI + rischi specifici di una mansione

**Da fare prima di martedì**:
- E2E test live di tutto (richiede DB+backend+frontend up — Docker postgres si è fermato a metà sessione)
- Push su Render staging
- Verificare che la migration giri pulita anche su prod (ha la merge dei 2 alembic head, situazione un po' inusuale)

---

## Reference data (persistente)

### Tipologie contrattuali (12 voci — email Luca 2026-04-24)
```
1. OPERAIO
2. OPERAIO QUALIFICATO
3. COLLABORATORE ESTERNO
4. VOLONTARIO
5. TIROCINANTE
6. STAGISTA
7. COADIUVANTE FAMILIARE
8. IMPIEGATO                   ← assumi full-time di default
9. IMPIEGATO PART-TIME         ← voce separata
10. OPERAIO EDILE
11. CO CO CO                   ← collaborazione coordinata e continuativa
12. DATORE DI LAVORO
```

Esclusi dalla mia lista iniziale (non in lista definitiva Luca): `Operaio specializzato`, `Operaio agile`, `Socio lavoratore`.

### Formule core (già in `FORMULAS_AND_CALCULATIONS.md`)
- **Indice rischio**: `I = 2·D + P` — bande: 3-4 Accettabile, 5-6 Modesto, 7-8 Grave, 9-12 Gravissimo
- **NIOSH**: `PLR = CP · A · B · C · D · E · F`, `IR = P/PLR` — verde <0.75, giallo 0.75-1.0, rosso >1.0
- **VDT**: ≥20 ore/settimana = Esposto
- **MMC max carichi standard**: Uomini 25 kg, Donne 20 kg (NIOSH CP)
- **Fire risk**: `INF+SI+PI` (ciascuno 1-3). 3-4 Low, 5-7 Medium, 8-9 High

### SDS: campi che l'AI estrae (validato su SDS MAYAQUA Vanilla)
- Nome prodotto, codice, UFI
- Produttore (nome + indirizzo + district/country)
- Revisione + data + revisione sostituita
- Classificazione CLP (es. Eye Irrit. cat. 2)
- Frasi H (H319, H302, H317, ...)
- Frasi EUH (EUH208, ...)
- Frasi P (P280, P337+P313, ...)
- Pittogrammi GHS (GHS07, ...)
- Signal word (Warning / Danger)
- Composizione (% + classificazione per ogni componente)
- DPI raccomandati (con normative EN)
- Proprietà fisiche (pH, densità, stato)
- Trasporto ADR/RID/IMDG/IATA

---

## Bug visibili in `prova.docx.pdf` (cross-check)

Elenco bug identificati incrociando il DVR generato con il transcript della call:

| ID | Bug | Sezione | Fase fix | Stato |
|----|-----|---------|----------|-------|
| B1 | Ambiente fantasma "B" (probabile user error, da monitorare) | UI sopralluogo | 2.4 | ⏳ da osservare in produzione |
| B2 | Disable rischio non funziona | Rischi ambiente | 2.2 | ✅ **fixed 2026-04-27** |
| B3 | "Cancerogeno" default in sala consumazione | Risk mapping | 2.4 | ✅ **fixed 2026-04-27** |
| B4 | Autocomplete attrezzature salva nome vuoto | Form attrezzatura | 2.1 | ✅ **fixed 2026-04-27** |
| B5 | Attrezzature non associate a ambiente | Data model | 2.3 | ✅ **fixed 2026-04-27** |
| B6 | MMC area rossa di default → deve essere verde | UI MMC | 1.4 |
| B7 | MMC per mansione invece di per persona | Backend valutazione | 4.1 |
| B8 | MMC non lista tutti i dipendenti | UI MMC | 4.1 |
| B10 | **DVR generato = master N2O, non azienda reale** | Generation engine | 8.1 | ✅ **fixed 2026-04-27** (root cause era B22 + cover page sparsa) |
| B11 | Allegato MMC mezzo template mezzo riempito | MMC generator | 9.1 |
| B12 | Allegato VDT non generato | VDT generator | 9.2 |
| B13 | Allegato Stress non generato | Stress generator | 9.3 |
| B14 | Storico revisioni non aggiorna su rigenera | Revision logic | 4.4 |
| B15 | Bancone bar manca fisico/biologico | AI filter | 8.3 |
| B17 | Date Word = `today()` hardcoded | Template logic | 1.10 |
| B18 | Formula display "= 2; D = 3; I = 8" (manca "P") | Template Word | 1.7 |
| B19 | Pagine vuote orfane (1, 3, 33, 36) | Template Word | 1.8 |
| B20 | "Come da documenti allegati" ma allegati non esistono | Generator | 9.1-9.3 |
| B21 | Cancerogeni/Amianto presenti per azienda non applicabile | AI filter categoria | 4.6 |
| B22 | Identificazione fattori rischio (pag 2) tutti "SI" statici (in realtà tutti **NO**: short vs long category name lookup mismatch) | DVR generator name normalization | 8.3+bonus | ✅ **fixed 2026-04-27** — `normalize_categoria_to_long` |
| B23 | Header Word non parametrico (PROVA, date statiche) | Template Word | 1.9 |

---

## File reference (materiale di partenza)

| File | Dove | Cosa contiene |
|------|------|---------------|
| Trascrizione call Week 1 | `C:\Users\Mato\Downloads\N2O - DVR App Settimana 1 - 2026_04_24 16_05 CEST - Appunti di Gemini.pdf` | 54 pagine, 1h37 dettagliata con timestamp |
| DVR generato di prova | `C:\Dev\dlg\prova.docx.pdf` | 39 pagine — è il master N2O non adattato (bug B10) |
| SDS test | `C:\Dev\dlg\MSDS-00001-M-006 Vanilla-v13_260424_165613.pdf` | 13 pagine, ground truth per estrazione AI |
| Screenshot production | `C:\Dev\dlg\prod-dashboard-pre-deploy.png`, `prod-dashboard-post-deploy.png`, `prod-guida-post-deploy.png` | Stato UI al deploy pre-review |

---

## Assumptions & risks

### Assumptions
- L'Excel completo dei rischi di Luca è parseable (ci aspettiamo .xlsx)
- Il template Word DVR master attuale è manutenibile via python-docx (già confermato in `DVR_TEMPLATE_MAPPING.md`)
- L'auth system NextAuth.js v5 supporta ruoli custom (serve per Fase 6)
- GPT-4.1 gestisce il context del DVR filtering (Fase 8.3) senza dover fare chunking

### Risks
- **Fase 8.1-8.2** può diventare più lunga del previsto se il template master ha troppi placeholder hard-coded (da verificare quanti dei 111 table/2445 paragraphs sono davvero dinamici — `DVR_TEMPLATE_MAPPING.md` dice 41 dynamic / 36 static / 13 mixed tables)
- **Fase 9.3 (Stress)**: normativa è sulla chiavetta Luca, non ancora estratta. Rischio ritardo se il materiale non arriva in tempo.
- **Fase 7** dipende completamente dall'Excel di Luca. Se arriva incompleto, da integrare manualmente → +2-3 giorni

---

## Changelog di questo file
- **2026-04-24** — Prima versione, post-review Week 1 con Luca. Piano 10 fasi, pre-martedì identificato.
- **2026-04-27** — Phase 2 (2.1-2.4) tutta DONE. Phase 5 (5.1-5.4) tutta DONE in anticipo (era roadmap settimana 2). Bug B2/B3/B4/B5 fixati. Aggiunto sistema AI suggester per attrezzature + protocollo mansione (DPI + rischi specifici). Schema change: `attrezzature.ambiente_id` ora NOT NULL con migration `f7b8c9d0e1f2` (anche merge dei 2 alembic head pre-esistenti). Backend tsc-equivalent + frontend tsc/eslint puliti.
- **2026-04-27 (sera)** — **Phase 8 (8.1-8.5) tutta DONE in anticipo di 4-5 settimane**. Cover page polish (P.IVA, ATECO, revisione versionata). DVR esploso: attrezzature per ambiente in Parte III. AI rischi suggester con merge-not-replace e sintesi banner. SDS rendering completo (pittogrammi GHS + frasi H + frasi P, blocco self-hiding). Sector pre-population: backend service + endpoint + `<SectorSuggestions>` banner sopra il wizard. **Bonus fix B22 critico**: short vs long category name normalization in dvr_master — la SI/NO checklist mostrava sempre NO, root cause di B10. Tutti 215 test backend passano, frontend tsc/eslint puliti. End-to-end smoke test: il DVR generato con dati reali ora rende davvero diverso dal master template (152 paragraphs, 57 tables, 21.9k chars con dati ACME fixture). **Live e2e ancora da fare** — push staging → click prova flow su Tuesday-29 demo.
