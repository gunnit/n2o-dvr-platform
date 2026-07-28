# QA report — "Sono un'azienda": dal landing all'acquisto al sopralluogo

> **Stato al 28/07/2026, sera — tutti i difetti di codice qui elencati sono stati corretti.**
> Restano aperti solo i due passi di *provisioning* che non sono codice:
> le credenziali PayPal in dashboard Render e l'esecuzione di
> `paypal_setup.py --live` / `paypal_webhook_setup.py --live` (P0-1, vedi `DEPLOY.md` §4b).
> Correzione a P2-7: il deep link `/prezzi#aziende` **esisteva già** e il landing
> lo usa — l'osservazione era mia, avevo aperto `/prezzi` senza hash.
> Le modifiche non sono ancora state committate né deployate.

**Data**: 28 luglio 2026
**Ambiente**: produzione — `https://dvr-sicurezza.it` / `https://n2o-dvr-api.onrender.com`
**Commit in produzione**: `a73220a` *feat(billing): open the direct channel — aziende can buy a plan*
**Percorso testato**: landing → `/prezzi` (tab Aziende) → `/register?piano=B_BASE` → checkout → sopralluogo → generazione DVR

---

## Esito in una riga

**Il percorso di acquisto non esiste in produzione**: nessun piano è acquistabile, `/billing/subscribe` risponde 503, e l'azienda che si registra riceve comunque un account **illimitato e marcato "Attivo"**. Il prodotto a valle (sopralluogo, calcoli, generazione DVR) invece **funziona bene** — con un difetto grave di qualità redazionale sul documento finale (accenti italiani assenti) e una numerazione di revisione sbagliata.

| Area | Esito |
|---|---|
| Landing + listino | OK, con incoerenze di copy |
| Registrazione azienda diretta | OK |
| **Pagamento / attivazione piano** | **BLOCCATO — non funziona** |
| **Entitlement dell'azienda non pagante** | **ROTTO — accesso illimitato** |
| Sopralluogo (dati, AI, calcoli) | OK, buono |
| **Generazione DVR** | Funziona, ma **documento non consegnabile** così com'è |

---

## Come è stato eseguito il test

Account creato realmente in produzione (dati di test, vedi §Pulizia):

| | |
|---|---|
| Utente | `ai+dvrtest0728@niuexa.ai` — *Marco Bianchi*, ruolo `admin` |
| Organizzazione | `d0dd2031-b058-4659-8b51-a8a816370a24`, `account_type = direct` |
| Azienda | *Officina Meccanica Bianchi SRL* — `eedfb9ac-ec22-418b-b713-b19be721c258` |
| Sopralluogo | 4 ambienti, 7 attrezzature, 5 lavoratori, 3 sostanze chimiche, 33 rischi valutati |
| Documenti generati | DVR Master, Allegato MMC, HACCP Manuale, HACCP Schede, POS |

> Nota metodologica: il wizard di sopralluogo è stato compilato via API perché il pannello animato (framer-motion) non completa la transizione di step quando il browser di automazione è in background. **Non è un bug del prodotto** — con una finestra visibile funziona.

---

# BLOCCANTI (P0)

## P0-1 — Nessun piano è acquistabile: il checkout è morto

**Cosa succede.** Dopo la registrazione con `?piano=B_BASE`, l'utente viene portato su `/billing?piano=B_BASE`, dove legge:

> *"Nessun piano acquistabile online al momento. Scrivi a support@dvr-sicurezza.it e attiviamo il piano per te."*

Il piano scelto viene **silenziosamente ignorato**: la pagina non lo nomina, non lo mette in evidenza, non offre alcun modo di riprendere l'acquisto.

**Evidenza.**
```
GET  /api/v1/billing/plans      → 200  []
POST /api/v1/billing/subscribe  → 503  {"detail":"Pagamenti non configurati su questo ambiente."}
```
(503 identico sia per `B_BASE` sia per `A_SOLO` — quindi anche il canale consulenti è fermo.)

**Causa — tre provisioning mai eseguiti**, tutti su `backend/render.yaml:50-59`:

1. `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` sono `sync: false`, cioè **non gestiti dal blueprint**: vanno inseriti a mano nella dashboard Render. Non lo sono → 503.
2. `scripts/paypal_setup.py` non è **mai** stato eseguito sul DB di produzione, quindi ogni `plans.paypal_plan_id` è `NULL`. `catalogue.list_purchasable()` filtra su `is_checkoutable` (`backend/app/billing/catalogue.py:35,69`) che richiede `paypal_plan_id` valorizzato → lista vuota.
3. `PAYPAL_WEBHOOK_ID` è vuoto: la verifica firma **fallisce chiusa**, quindi anche riuscendo a pagare nessun abbonamento passerebbe mai ad `active`.

**Attenzione**: `PAYPAL_ENV` è fissato a `live` nel blueprint. Al momento del provisioning servono credenziali **live** reali — un client id sandbox qui produce un 401 in fase di autenticazione, non un pagamento finto.

**Fix.** Seguire `DEPLOY.md` §4b nell'ordine: credenziali in dashboard → `paypal_setup.py --live` → `paypal_webhook_setup.py --live` → un acquisto reale di collaudo.

**Fix aggiuntivo (UX), indipendente dal provisioning:** `/billing` deve riconoscere `?piano=`. Se quel piano non è acquistabile, dirlo esplicitamente — *"Il piano Base non è al momento attivabile online"* — invece di un messaggio generico che scarta l'intenzione d'acquisto appena espressa.

---

## P0-2 — Un'azienda che non ha pagato ottiene un account illimitato marcato "Attivo"

**Cosa succede.** Appena registrata, senza alcun pagamento, la pagina `/billing` mostra:

> Piano attuale · **Attivo** · **A_FOUNDING**
> Utenti inclusi **2147483647** · Sedi incluse **illimitato** · Crediti AI **illimitati** · Tipi di documento **tutti**

`A_FOUNDING` è il piano €0 riservato a N2O come founding partner. **Ogni nuovo iscritto atterra lì.**

**Evidenza** — `GET /api/v1/billing/entitlements`:
```json
{ "account_type": "direct", "plan_code": "A_FOUNDING", "status": "active", "is_active": true,
  "allowed_doc_types": null, "seats": 2147483647, "max_companies": null, "max_sites": null,
  "ai_credits_year": null, "enforced": false }
```

**Causa.** `backend/app/billing/entitlements.py:105-127` — `_fallback_entitlements()`. È la rete di sicurezza INV-1, scritta per il caso *"tenant pagante la cui riga subscription è andata persa"*: in quel caso è giusto lasciar lavorare il cliente. Ma dopo `a73220a` la registrazione self-service crea **per progetto** un tenant senza riga `subscriptions` — quindi la rete di sicurezza è diventata **lo stato normale del canale diretto**.

Tre conseguenze distinte:

- **Commerciale**: nessuno ha motivo di pagare — tutto è già sbloccato.
- **Fiducia**: la UI *afferma* al cliente di avere un abbonamento attivo che non ha. Se domani si attiva l'enforcement, quel cliente si vede togliere accesso che l'interfaccia gli aveva confermato per iscritto.
- **Leggibilità**: viene mostrato `A_FOUNDING` — un codice interno — e `2147483647`, cioè `2^31-1` grezzo, invece di "illimitato".

**Fix consigliato.** Separare i due casi, che oggi collassano su uno:
1. *Tenant senza subscription perché non ha ancora comprato* (nuovo, atteso) → stato dedicato `none` / `trialing`, UI che invita all'acquisto, **mai** `status: active` né `A_FOUNDING`.
2. *Tenant con subscription mancante per data gap* (anomalia) → mantenere il fallback permissivo attuale **e allertare**.

Distinguibili guardando se l'organizzazione ha mai avuto una subscription (`ddl_consent_at` / data di creazione sono già disponibili). In ogni caso: non riusare `FOUNDING_PLAN_CODE` come etichetta di un buco dati, e formattare `2^31-1` come "illimitato".

---

## P0-3 — Il guardrail POS / HACCP non tiene: un tenant diretto li genera

Il commit `a73220a` dichiara POS, HACCP e HACCP_FORMS *"excluded from every Model B plan permanently"* — è la barriera che manda cantieri e filiera alimentare a uno studio partner invece che al canale diretto.

**In produzione non blocca nulla.** Con il tenant diretto non pagante:

```
POST /documents/generate {"tipo_documento":"pos"}          → 202 Accepted
POST /documents/generate {"tipo_documento":"haccp"}        → 202 Accepted
POST /documents/generate {"tipo_documento":"haccp_forms"}  → 202 Accepted
```

Tutti e tre risultano poi **"Pronto"** nella pagina Documenti. Inoltre la pagina propone **tutti e 17** i tipi di documento senza alcun badge "non incluso nel tuo piano", più un pulsante **"Genera Tutti"**.

**Causa — doppia permissività sovrapposta:**
- `ENTITLEMENTS_ENFORCE = "false"` (`render.yaml`, volutamente, finestra shadow MB-2.6);
- e comunque `_fallback_entitlements()` restituisce `allowed_doc_types: null` = tutti ammessi (P0-2).

**P0-3b — la finestra shadow non sta raccogliendo niente.** I log dell'API non contengono **nessun** `WOULD_BLOCK` negli ultimi 7 giorni, incluse le tre chiamate qui sopra. È coerente: con `allowed_doc_types: null` il gate valuta "permesso" e non ha nulla da loggare. Il problema è che **GATE 2 si basa su quelle evidenze**: chi le rileggerà vedrà zero blocchi previsti e concluderà che si può attivare l'enforcement senza impatti. È un falso segnale di via libera. Va sistemato P0-2 *prima* che la finestra shadow abbia senso.

---

# GRAVI (P1)

## P1-1 — Il DVR generato è privo di accenti italiani

Il documento consegnato al cliente — che il datore di lavoro firma e un ispettore legge — contiene errori ortografici sistematici.

**Evidenza** (verificata sui byte del `document.xml`, non su un artefatto di console — `rischi 65 20` = `e` ASCII, non `c3a8` = `è`):

| Nel documento | Corretto |
|---|---|
| «La valutazione dei rischi **e** stata effettuata…» | è stata |
| «Il documento **e** conservato presso l'**unita** produttiva…» | è … unità |
| «La sua rielaborazione **e** prevista…» | è prevista |
| PARTE II — DESCRIZIONE DELL'**ATTIVITA** | ATTIVITÀ |
| 2.4 Scala di **Probabilita** (P) | Probabilità |
| «**nonche** le caratteristiche… **piu** sensibili» | nonché … più |

L'errore `e` → `è` non è cosmetico: cambia il senso della frase da *"e"* a *"è"* in un testo normativo.

**Portata misurata.** Sull'intero DVR generato ci sono **17 caratteri accentati in totale**, e sono **tutti in testo prodotto dall'AI** (le motivazioni dei rischi, dove infatti si legge correttamente «è presente», «può», «attività»). **Tutto il boilerplate hardcoded ne è privo**: 75 occorrenze di forme senza accento.

**Causa.** `backend/app/services/document_generator/dvr_master.py` contiene **1** carattere accentato in tutto il file contro **71** parole italiane scritte senza accento (es. `:1408`, `:1421`, `:2145`, `:2273`). Non è un problema di encoding — UTF-8 funziona correttamente lungo tutta la catena — sono **le stringhe sorgente ad essere state scritte senza accenti**.

**Altri generatori interessati:**

| File | accentati | senza accento |
|---|---|---|
| `dvr_master.py` | 1 | 71 |
| `allegato_vdt.py` | 0 | 12 |
| `haccp_manuale.py` | 1 | 4 |
| `allegato_mmc.py` | 0 | 4 |
| `allegato_incendio.py` | 0 | 4 |
| `duvri.py` | 0 | 3 |

(`pos.py` e `allegato_stress.py` sono invece corretti — quindi è una svista di redazione, non una scelta ASCII deliberata.)

**Fix.** Correggere le stringhe sorgente e aggiungere un test che fallisca se una stringa italiana destinata al documento contiene una forma tronca nota (`attivita`, `probabilita`, `unita`, `puo`, `piu`, `nonche`, ` e stat`, …). Senza il test la regressione rientra alla prima modifica.

---

## P1-2 — Lo stesso identico documento ha quattro numeri di versione diversi

Primo DVR mai generato per una nuova azienda:

| Dove | Valore |
|---|---|
| Riga DB / API `versione` | **1** |
| Badge in pagina Documenti | **v1** |
| Nome file | `…_20260728_**v2**.docx` |
| **Copertina del documento** | **«Revisione 02 — 28/07/2026»** |
| Tabella *Storico Revisioni* nel documento | **«00 — Emissione — 28/07/2026»** |

La copertina contraddice la tabella delle revisioni **dello stesso documento**, e dichiara una seconda revisione di un documento appena emesso. Su un DVR lo storico revisioni ha rilevanza normativa (art. 29 c.3).

**Causa (off-by-one).** `POST /documents/generate` crea la riga `DocumentoGenerato` con `versione=1` **prima** di accodare il task (`backend/app/api/v1/documents.py:345-348`). Il generatore poi ricalcola per conto suo:

```python
# backend/app/services/document_generator/dvr_master.py:1025-1037
stmt = select(func.coalesce(func.max(DocumentoGenerato.versione), 0)).where(...)
current_max = result.scalar()
return current_max + 1        # ← conta anche la propria riga: 1 + 1 = 2
```

**Fix.** Il generatore deve usare il `versione` della riga che sta popolando, non ricalcolarlo. Stesso schema `_next_version()` da verificare negli altri generatori (`allegato_gestanti.py:150`, `allegato_incendio.py:194`, `allegato_microclima.py:117`, `_biologico_common.py:87`).

---

## P1-3 — L'autofill AI produce un ATECO che il form stesso rifiuta

Sequenza reale osservata:

1. Inserisco la P.IVA e premo **Compila con AI** → i campi si popolano correttamente (testato con `00905811006` → *ENI SPA*, indirizzo, PEC, sito: tutto giusto).
2. Fra i campi compilati, `codice_ateco = "19.20.1"`.
3. Premo **Salva Azienda** → **«Formato non valido (es. 56.10.11)»**.

La funzione di punta pubblicizzata sul landing («Autofill dell'anagrafica dalla sola P.IVA») produce un valore che la validazione della stessa pagina respinge, senza spiegare all'utente cosa correggere.

**Causa — due regex diverse per lo stesso campo:**

```
frontend/src/lib/validators/azienda.ts:12      /^\d{2}\.\d{2}\.\d{2}$/        ← form azienda: obbliga XX.YY.ZZ
frontend/src/components/survey/survey-wizard.tsx:342,378
                                               /^\d{2}\.\d{2}(\.\d{2})?$/     ← wizard: accetta anche XX.YY
```

Il wizard accetta `45.20`, il form azienda no. E i codici ATECO reali esistono legittimamente anche a 4 e 5 cifre (`45.20`, `45.20.1`), quindi la regex stretta rifiuta input validi presi dai registri.

**Fix.** Un'unica regex condivisa che accetti `XX.YY`, `XX.YY.Z` e `XX.YY.ZZ`; normalizzare l'output dell'estrattore AI sullo stesso formato; messaggio d'errore che mostri il valore ricevuto e i formati ammessi.

---

## P1-4 — `POST /survey/complete` non verifica nulla

`backend/app/api/v1/survey.py:161-176` imposta `survey_status = "completed"` **senza alcun controllo**: non verifica che esistano ambienti, lavoratori o rischi valutati.

La UI il vincolo lo ha («Aggiungi almeno un ambiente per continuare»), ma è solo lato client. Un sopralluogo completamente vuoto può essere marcato "completato" e mandato in generazione documenti, producendo un DVR privo di contenuto valutativo.

**Fix.** Spostare la precondizione nell'endpoint: almeno un ambiente e almeno un lavoratore, altrimenti 422 con l'elenco di cosa manca.

---

# MEDI (P2)

## P2-1 — L'azienda diretta usa tutta l'interfaccia del consulente

Un datore di lavoro che registra **la propria** impresa si trova ovunque il lessico di chi gestisce un portafoglio clienti:

| Pagina | Testo mostrato |
|---|---|
| Dashboard | «**CLIENTI ATTIVI**», «**Aziende Clienti**», «Aggiungi cliente», «Nuova azienda — *registra cliente*» |
| `/aziende/new` | «Registra una nuova **azienda cliente**» |
| `/documents` | «Genera i documenti di sicurezza per le **aziende clienti**» |

Solo `/billing` è stato adattato (mostra "sedi" invece di "aziende attive"). Per il cliente diretto il messaggio implicito è "questo software non è per te", proprio nella schermata che vede per prima dopo l'iscrizione.

**Fix.** Le stesse stringhe già condizionate in `/billing` su `account_type === "direct"` vanno estese a dashboard, `/aziende`, `/documents`. Per un tenant diretto: "Le mie sedi", "Nuova sede", "I miei documenti".

## P2-2 — Timestamp sfasati di due ore

Un'azienda appena creata mostra **«ULTIMO AGGIORNAMENTO: 2 ore fa»**; documenti generati un minuto prima mostrano **«v1 · 2 ore fa»**.

Verificato: ora locale browser `12:17 CEST (UTC+2)`, `created_at` restituito `10:12` senza indicatore di fuso. Il valore è UTC ma viene confrontato con l'ora locale come se fosse locale. In inverno lo scarto diventerà di 1 ora.

**Fix.** Serializzare i timestamp con offset esplicito (`…Z` o `+00:00`) e interpretarli come UTC lato client.

## P2-3 — Il listino promette un prezzo primo anno che il checkout non applica

`/prezzi` tab Aziende:

| Piano | Prezzo esposto | Nota | Catalogo backend |
|---|---|---|---|
| Base | €490/anno | «**Primo anno €690**, setup guidato incluso» | `49_000` cent = **€490** |
| Plus | €990/anno | «Primo anno €1.290» | `99_000` = **€990** |
| Multi-sede | €2.400/anno | «Primo anno €2.900» | `240_000` = **€2.400** |

(`backend/app/billing/plan_catalogue.py:183-235`)

Il prezzo maggiorato del primo anno non esiste da nessuna parte nel codice: non c'è né un piano di primo anno, né un add-on di setup. Al momento in cui il checkout verrà attivato, il cliente a cui è stato scritto "primo anno €690" verrà addebitato €490 — o, peggio, la discrepanza verrà notata a contratto firmato.

**Fix.** Decidere quale delle due è la verità e allineare l'altra: o un piano/add-on di setup realmente fatturato, o rimuovere la riga dal listino.

## P2-4 — Il listino dichiara un requisito di idoneità che non viene applicato

Landing: *«I piani diretti sono riservati alle imprese sotto le soglie dimensionali e di rischio previste. Cantieri, classi ATECO ad alto rischio e organici superiori vengono indirizzati a uno studio partner.»*
`/prezzi`: *«Base — Micro impresa fino a 15 addetti»*.

Nessun controllo esiste (scelta di scope dichiarata, D-8: il gate MB-5.2/5.3 non è stato spedito). Nel test ho caricato **ENI SPA** — raffineria, decine di migliaia di addetti — su un tenant Base, senza alcun attrito.

Il commit dice di aver rimosso la copy che prometteva una *"verifica di idoneità"* proprio per non fare affermazioni false; **queste due frasi sono rimaste** e affermano ancora una restrizione inesistente.

**Fix.** O si implementa il gate, o si riformula in termini di responsabilità del cliente («i piani diretti sono pensati per…» / «se la tua impresa rientra in questi casi, contattaci»).

## P2-5 — Fasce di addetti sovrapposte fra i piani

| Piano | Fascia dichiarata |
|---|---|
| Base | fino a **15** addetti |
| Plus | da **15** a 50 addetti |
| Multi-sede | da **10** a **249** addetti |

Un'impresa con 15 addetti rientra in Base *e* Plus; una con 12 addetti in tutti e tre. E i 249 addetti di Multi-sede contraddicono apertamente la promessa, sulla stessa pagina, che gli «organici superiori» vadano a uno studio partner.

**Fix.** Fasce disgiunte (`1-14`, `15-49`, `50-249`) e allineare la frase del landing alla soglia reale.

## P2-6 — «Compila con AI»: 25-30 secondi senza alcun riscontro

L'autofill P.IVA ha impiegato **~28 secondi** (misurato). L'unico feedback è l'etichetta del pulsante che passa a «Cerco...»: nessuna barra, nessuna stima, nessun testo che dica che l'operazione è lunga. Un utente in azienda, su rete mobile, conclude che si è bloccato e ricarica.

**Fix.** Indicatore di avanzamento con aspettativa esplicita («Interrogazione dei registri pubblici, fino a ~30 secondi»), e disabilitare il resto del form durante l'operazione.

## P2-7 — La selezione del listino non finisce nell'URL

`/prezzi` apre **sempre** sul tab «Consulenti e studi». Chi arriva dalla sezione "Per aziende" del landing (`Vedi i piani` → `/prezzi`) atterra sui prezzi dei consulenti — €1.490 invece di €490 — e deve accorgersi da solo del tab. Non esiste inoltre un link condivisibile al listino aziende.

**Fix.** `/prezzi?tipo=aziende` (o `#aziende`) che preseleziona il tab, e farlo puntare dalle CTA della sezione aziende.

---

# MINORI (P3)

- **P3-1 — Il nome dell'utente non viene mai mostrato.** `full_name = "Marco Bianchi"` è salvato correttamente (`GET /auth/me`), ma la sidebar mostra l'email e un avatar con iniziali **«AN»**, che non corrispondono né al nome né all'organizzazione. Atteso: «MB» e "Marco Bianchi".
- **P3-2 — `/api/auth/session` chiamata 7+ volte di fila** dopo il redirect post-registrazione. Sospetto loop di render; da verificare perché moltiplica il carico su ogni navigazione.
- **P3-3 — «Ragione sociale dell'impresa» è opzionale in registrazione** (`required: false`) proprio nel flusso in cui l'impresa *è* l'oggetto della registrazione. Lasciandolo vuoto l'organizzazione nasce senza nome.
- **P3-4 — Accenti mancanti anche nel wizard di sopralluogo**, stesso problema di P1-1 ma lato UI: `step-azienda.tsx:48-51` («pericolosita» ×4), `:189` («Attivita»), `:234`, `:266` («Citta»); `step-riepilogo.tsx:325`; `step-ambienti.tsx:917,920`. Il form `/aziende/new` scrive invece correttamente «Attività» e «Città» — quindi l'utente vede due grafie diverse per lo stesso campo a due schermate di distanza.
- **P3-5 — Percentuale di avanzamento incoerente**: al primo step il wizard indica «25%» ma anche «Passo 1 di 7». Se il 25% si riferisce ai soli step obbligatori, va detto.
- **P3-6 — `<title>` generico** su tutte le pagine applicative: «N2O DVR - Sicurezza sul Lavoro» su registrazione, dashboard, documenti, sopralluogo. Le pagine marketing invece hanno title corretti.
- **P3-7 — Da verificare: la casella `support@dvr-sicurezza.it` riceve davvero?** È l'unico canale per i piani Network ed Enterprise, per tutti gli add-on, e — finché vale P0-1 — **per qualsiasi acquisto**. Se non è configurata, ogni richiesta commerciale del sito cade nel vuoto.

---

# Cosa funziona bene

Vale la pena isolarlo, perché è la parte difficile ed è solida:

- **Registrazione canale diretto**: `account_type: "direct"` correttamente impostato dall'endpoint (non dal payload), consenso datore di lavoro versionato e registrato.
- **Autofill P.IVA**: dati ENI recuperati corretti e completi (ragione sociale, CF, forma giuridica, ATECO, indirizzo, CAP, PEC, sito).
- **Nessun dato reinserito**: lo step 1 del sopralluogo arriva già popolato dall'anagrafica azienda — la promessa centrale del prodotto è mantenuta.
- **Suggeritore rischi AI**: ~12 secondi per ambiente, 10 categorie pertinenti per l'officina (ponte sollevatore, saldatura MIG, oli esausti…), con P/D motivati e coerenti.
- **Formula indice di rischio corretta**: `I = 2·D + P` verificata sui valori restituiti — `P2/D2 → I=6 MODESTO` (fascia 5-6), `P2/D3 → I=8 GRAVE` (fascia 7-8).
- **DVR Master generato completo**: 1.394 paragrafi, **83 tabelle**, 4 parti, tutti e 4 gli ambienti. Dati reali ovunque, nessun placeholder rimasto: tutti e 5 i lavoratori nei Dati Occupazionali, ruoli sicurezza risolti correttamente (RSPP, RLS, primo soccorso, antincendio), attrezzature per ambiente, sostanze chimiche.
- **Anteprima inline**: `/documenti/{id}/preview` restituisce 544 KB di blocchi strutturati, funzionante.
- **Fail-safe dei pagamenti**: con le credenziali assenti il sistema risponde 503 e **non** chiama PayPal — nessun rischio di addebito accidentale.

---

# Ordine di intervento consigliato

| # | Intervento | Perché prima |
|---|---|---|
| 1 | **P0-2** — separare "non ha ancora comprato" da "buco dati" | Blocca P0-3 e rende sensata la finestra shadow. È un bug di correttezza, non di configurazione |
| 2 | **P1-1** — accenti nei generatori + test di regressione | Il documento oggi non è consegnabile a un cliente |
| 3 | **P1-2** — off-by-one della revisione | Una riga di codice; errore visibile in copertina |
| 4 | **P0-1** — provisioning PayPal (`DEPLOY.md` §4b) | Sblocca il ricavo, ma è configurazione: nessun codice da scrivere |
| 5 | **P0-3** — attivare l'enforcement dopo una finestra shadow *vera* | Ha senso solo dopo il #1 |
| 6 | **P1-3, P1-4** | Difetti sul percorso principale |
| 7 | P2-* | Coerenza commerciale e di prodotto |

---

# Pulizia

Il test ha lasciato dati **nel database di produzione**:

- utente `ai+dvrtest0728@niuexa.ai` e organizzazione `d0dd2031-b058-4659-8b51-a8a816370a24`
- azienda `eedfb9ac-ec22-418b-b713-b19be721c258` (*Officina Meccanica Bianchi SRL*) con 4 ambienti, 7 attrezzature, 5 lavoratori, 3 sostanze, 33 rischi
- 5 documenti generati su disco Render (DVR, MMC, HACCP Manuale, HACCP Schede, POS)

Sono utili da tenere per riprodurre i difetti qui elencati. **Da rimuovere prima del go-live** — o subito, se preferisci: dimmelo e li elimino.
