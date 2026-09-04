# Segnalazioni — export completo dal database di produzione (2026-09-04)

Query diretta su `user_feedback` (Render Postgres `n2o-dvr-db`), join con `organizations` e `users`. Copre **tutti** i tenant, non solo quello letto via API.

- Righe totali: **158**
- Organizzazioni: Niuexa Test (158)
- Utenti: test.business@niuexa.ai (158)
- Stato: Nuovo **30**, In revisione **3**, Non farà **3**, Risolto **122**
- Con issue GitHub: 69 su 158 (mirror fermo dal 2026-06-10)
- Per mese: 2026-04 (23), 2026-05 (85), 2026-06 (11), 2026-07 (1), 2026-08 (38)

Verdetto: identico alla lettura via API di oggi — nessun altro tenant ha inserito segnalazioni.

## Nuovo (30)

| # | Data | Tipo | GH | Pagina | Segnalazione |
|---|---|---|---|---|---|
| 1 | 2026-07-31 | Bug | — | /survey/162580ba-c307-46a8-a2b0-38bd09590688 | MI DICE CHE HO FINITO I CREDITI MA IN REALTA' LI HO |
| 2 | 2026-08-03 | Osservazione | — | /assessments/mmc/2b1c9da7-a79d-4ca4-87b6-afb005465bef | Nel documento elaborato, deve rimanere sempre la tabella dei dati occupazionali uguale a quella del rischio master, in più deve esserci la tabella dove si evidenzia solo: nome e cognome, sesso età, mansione |
| 3 | 2026-08-03 | Osservazione | — | /assessments/mmc/2b1c9da7-a79d-4ca4-87b6-afb005465bef | nel documento elaborato, nella sezione "programma di attuazione delle misure di prevenzione", modificare la voce della colonna "compito" con AZIONE e indicare tutte le azioni per ogni dipendente in un unica riga |
| 4 | 2026-08-03 | Osservazione | — | /assessments/vdt/2b1c9da7-a79d-4ca4-87b6-afb005465bef | nel documento elaborato, inserire sempre la tabella organigramma dipendenti presente sul rischio master |
| 5 | 2026-08-03 | Osservazione | — | /assessments/vdt/2b1c9da7-a79d-4ca4-87b6-afb005465bef | nel documento elaborato, nella tabella elenco postazioni vdl, modificare la voce ambienti di lavoro con la voce ATTIVITA'. nel programma, va aggiunta la voce ATTIVITA' con un campo da compilare |
| 6 | 2026-08-03 | Osservazione | — | /assessments/vdt/2b1c9da7-a79d-4ca4-87b6-afb005465bef | nel documento elaborato, nella sezione "tavole di valutazione rischio vdt" le tabelle devono essere divise per dipendente e non per postazione. |
| 7 | 2026-08-03 | Osservazione | — | /assessments/vdt/2b1c9da7-a79d-4ca4-87b6-afb005465bef | se nel rischio vdi, una persona utilizza piu Device, il programma deve farmi la somma delle ore e riconoscere se una persone è esposta al rischio o no. |
| 8 | 2026-08-03 | Osservazione | — | /assessments/vdt/2b1c9da7-a79d-4ca4-87b6-afb005465bef | nel documento elaborato, nella sezione "quadro sinottico di esposizione" deve esserci il calcolo delle ore a cui un dipendente è esposto includendo tutte le postazioni che utilizza. deve essere visualizzato il totale su una riga |
| 9 | 2026-08-03 | Osservazione | — | /assessments/vdt/2b1c9da7-a79d-4ca4-87b6-afb005465bef | Nel documento elaborato, nella sezione "sorveglianza sanitaria", eliminare le vici Ultima visita e Prossima Visita e il campo periodicità deve essere calcolato in base all'età del lavoratore |
| 10 | 2026-08-03 | Bug | — | /assessments/risk/5ca01e04-9099-44b7-8e10-63ce7baa6320 | Togliere le misure di miglioramento da qua e lasciarle solo nella sezione dedicata. |
| 11 | 2026-08-03 | Bug | — | /assessments/risk/5ca01e04-9099-44b7-8e10-63ce7baa6320 | Aree valutazione dei rischi completamente da rivedere |
| 12 | 2026-08-03 | Bug | — | /assessments/risk/5ca01e04-9099-44b7-8e10-63ce7baa6320 | nella valutazione dei rischi, nel rischio gestanti non va inserito "vedi normativa ..." ma come da documenti allegati in caso ci sia oppure si puo' scegliere l'indice di rischio. |
| 13 | 2026-08-03 | Bug | — | /assessments/risk/5ca01e04-9099-44b7-8e10-63ce7baa6320 | nella valutazione dei rischi, nella sezione lavoratori stranieri, ci deve essere solo la possibilità di scegliere l'indice di rischio. |
| 14 | 2026-08-03 | Bug | — | /assessments/risk/5ca01e04-9099-44b7-8e10-63ce7baa6320 | nella valutazione dei rischi, nella sezione lavoratori minori, stessa cosa delle gestanti |
| 15 | 2026-08-03 | Osservazione | — | /assessments/pee/5ca01e04-9099-44b7-8e10-63ce7baa6320 | nella tabella configurazione piano d'emergenza inserire la casella tipologia di allarme. |
| 16 | 2026-08-03 | Osservazione | — | /assessments/pee/5ca01e04-9099-44b7-8e10-63ce7baa6320 | nella tabella incendio e in quella evacuazione generale nel punto A il programma deve riconoscere la tipologia di allarme indicata. |
| 17 | 2026-08-03 | Osservazione | — | /assessments/pee/5ca01e04-9099-44b7-8e10-63ce7baa6320 | sostituire tutti i numeri di emergenza con la dicitura. numero unico 112 |
| 18 | 2026-08-04 | Osservazione | — | /assessments/gestanti/5ca01e04-9099-44b7-8e10-63ce7baa6320 | Nell'allegato gestanti devo avere la possibilità di poter fare una valutazione oggettiva dei rischi legati alla mansione/i senza che qualche dipendente sia già in fase di gestazione. |
| 19 | 2026-08-04 | Idea | — | /assessments/microclima/2b1c9da7-a79d-4ca4-87b6-afb005465bef | BISOGNEREBBE IMPLEMENTARE OLTRE CONFORT E STRESS TERMICO ANCHE LO STRESS DA FREDDO. |
| 20 | 2026-08-04 | Osservazione | — | /assessments/pos/2b1c9da7-a79d-4ca4-87b6-afb005465bef | CAMPI DA INSERIRE ALL'INTERNO DEL POS: - Indirizzo cantiere (inserimento manuale) - Data inizio/fine lavori (inserimento manuale) - Subappalti (flag con "si" o "no", e la possibilità sul si di inserirli manualmente) - Dipendenti che lavorano in cantiere (selezionabili dall'elenco organigrama) - Figure di sicurezza sul cantiere (selezionabili con tendina) - Sostanze pericolose (flag con "si" o "no", e la possibilità sul si di inserirli manualmente) - nel documento elaborato, inserire tutte le diciture di default presenti sul nostro originale (se vuoi te le fornisco) |
| 21 | 2026-08-04 | Osservazione | — | /assessments/duvri/2b1c9da7-a79d-4ca4-87b6-afb005465bef | nella sezione "interferenze identificate" bisogna creare un tasto AI dove in base ai pulsanti delle attrezzature/attività, mi crea i rischi interferenziali |
| 22 | 2026-08-19 | Bug | — | /aziende/new | Se scegli la compilazione automatica all'indirizzo ti compila il CAP e la sede operativa in automatico, ma spesso è molto impreciso |
| 23 | 2026-08-19 | Osservazione | — | /assessments/risk/a923821e-c5a9-4e56-8c2c-104dc9c1565d | Nel catalogo non applicati, sarebbe bello avere tutti i rischi possibili per quella categoria anche se si sceglie il suggerimento con AI |
| 24 | 2026-08-19 | Osservazione | — | /assessments/risk/a923821e-c5a9-4e56-8c2c-104dc9c1565d | Quando vado ad inserire la valutazione rischi scegliendo i valori per l'indice di rischio dovrei avere li la possibilità di scegliere come documenti allegati voce per voce e non per tutta la categoria. |
| 25 | 2026-08-21 | Bug | — | /aziende/ac6d1b03-b3f8-4142-8d59-aaba0aa651b3 | Molte misure di miglioramento me le ripete |
| 26 | 2026-08-25 | Osservazione | — | /assessments/incendio/a923821e-c5a9-4e56-8c2c-104dc9c1565d | nell'allegato rischio incendio, dovremmo integrare per ogni ambiente le seguenti caselle: - Descrizione dell'ambiente, metratura e materiali presenti - Numero di persone max presenti * - Possibili sorgenti di innesco Sarebbe bello se riconoscesse mediante le foto caricate tutte questo informazioni tranne quelle segnate da asterisco |
| 27 | 2026-08-25 | Osservazione | — | /assessments/pee/a923821e-c5a9-4e56-8c2c-104dc9c1565d | nell'allegato PEE, dovremmo integrare per ogni ambiente le seguenti caselle: - Descrizione dell'ambiente, metratura e materiali presenti - Numero di persone max presenti * - Possibili sorgenti di innesco Sarebbe bello se riconoscesse mediante le foto caricate tutte questo informazioni tranne quelle segnate da asterisco |
| 28 | 2026-08-25 | Idea | — | /assessments/gestanti/cddbfb34-8541-4541-bfc7-3a7e2e45890f | integrare un tasto AI che riconosce per ogni mansione i rischi a cui è sottoposta una lavoratrice gestante e mi va a introdurre delle limitazioni in caso ce ne fosse bisogno o mi definisce la lavoratrice non compatibile con la mansione |
| 29 | 2026-08-25 | Osservazione | — | /settings | nella sezione:Protocollo sanitario aziendale, deve essere compilabile con l'utilizzo dell'AI. Deve esserci anche una lista delle malattie a cui gli operatori sono esposti. (anche quella estraibile con AI) |
| 30 | 2026-08-25 | Osservazione | — | /settings | Devono essere integrate anche nel Rischio Biologico le seguenti categorie: - Veterinari - Operatori sanitari - Centri estetici - Agricoltori - Gestione ambientale: lavori in impianti di smaltimento e trattamento dei rifiuti e negli impianti per la depurazione delle acque di scarico (fogne) |

## In revisione (3)

| # | Data | Tipo | GH | Pagina | Segnalazione |
|---|---|---|---|---|---|
| 1 | 2026-04-28 | Bug | — | /guida | la guida deve essere aggiornata con nuovi screashot e nuovespiegazioni |
| 2 | 2026-04-28 | Idea | — | /admin/feedback | Servirebbe fare la foto alla carta identita per estrare le info del lavoratore nome cogniome cdice fiscale , sesso , data di nasciata , indirizzo reidenza , numero carta di identita , altezza, nazionalita, emissioe e scadenza della carta , estremi del atto di nascita - non carta di identità sempre ma anche permesso di soggiorno - verificare che si puo fare utilizzare lgalmente , verfcare se deo flaggare un pop up per usare i loro dati personali o devo farlo per dipendente, e un problema di gdpr |
| 3 | 2026-05-29 | Bug | #63 | /assessments/pos/50e371cf-d45a-439a-be58-ccb9e1b15158 | QUALI SONO LE LAVORAZIONI CHE UN OPERAIO EDILE FA ALL'INTERNO DI UN CANTIERE. DEVO INSERIRLE COME LAVORAZIONI DI DEFAULT IN UN POS. FAMMI L'ELENCO |

## Non farà (3)

| # | Data | Tipo | GH | Pagina | Segnalazione |
|---|---|---|---|---|---|
| 1 | 2026-04-28 | Idea | — | /dashboard | Aggiungiamo un grafico a barre per far vedere avanzamento |
| 2 | 2026-05-05 | Bug | — | /survey/7263b070-3d8f-44b1-87e0-d715bc2eecb9 | non mi fa selezionare i campi |
| 3 | 2026-05-18 | Osservazione | #25 | /assessments/risk/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | le misure di miglioramento devono essere inserite una volta completata la valutazione di tutti gli ambienti. |

## Risolto (122)

| # | Data | Tipo | GH | Pagina | Segnalazione |
|---|---|---|---|---|---|
| 1 | 2026-04-21 | Idea | — | /dashboard | Test end-to-end della nuova funzione Segnala dopo il deploy su Render. Verifica che il backend registri il feedback e che l'admin lo veda nella pagina /admin/feedback. |
| 2 | 2026-04-28 | Osservazione | — | /aziende | Il layout dovrebbe essere un po piu accativante |
| 3 | 2026-04-28 | Osservazione | — | /survey/465a45bc-115f-43ed-940c-9dec49ac70cf | Prima azienda , seconda ambienti , terza atrezzature , quarta persone , quinta quella che ce dp richi specifici |
| 4 | 2026-04-28 | Bug | — | /survey/46afcdb0-b368-4c49-9bf7-e24f78c5ca4f | Quando si inserice una nuova persona il campo teso libero per la qualificha va sotituito con questo Lavori in Quota e Veicoli Lavori in quota Utilizzo carrello elevatore Utilizzo piattaforma di lavoro elevabile (PLE) Utilizzo gru Utilizzo ruspa / escavatore Guida automezzi (patente C-D-E) Trasporto ADR (merci pericolose) --> a flag , e questo va tolto da altro tab dpi rischi |
| 5 | 2026-04-28 | Idea | — | /survey/46afcdb0-b368-4c49-9bf7-e24f78c5ca4f | rinominare qualifiche in atrezzature speciali ma mantenere un campo note free text |
| 6 | 2026-04-28 | Bug | — | /survey/46afcdb0-b368-4c49-9bf7-e24f78c5ca4f | Quando seleziono marcatura CE il flag scompare |
| 7 | 2026-04-28 | Osservazione | — | /survey/46afcdb0-b368-4c49-9bf7-e24f78c5ca4f | Al censimeno di un nuovo dipendente quando vado afleggare le attrezzature speciali il programma deve risocnoscere ln automatico i rischi e dpi a qui quel dipendente e esposto indipendentemente dalla mansione che svolgo |
| 8 | 2026-04-28 | Bug | — | /assessments/stress/46afcdb0-b368-4c49-9bf7-e24f78c5ca4f | i breadcrumbs non funzionano su molte pagine |
| 9 | 2026-04-28 | Idea | — | /assessments/stress/3305a3a9-2809-443c-bfa7-502ad91522fb | potremmo suddividere la valutazione dello stress per mansione |
| 10 | 2026-04-29 | Bug | — | /survey/0c9a31be-b797-4c5f-b0e5-59a91d099f5a | non mi fa scrivere la parola completa ma da' l'invio alla prima lettera |
| 11 | 2026-04-29 | Osservazione | — | /survey/0c9a31be-b797-4c5f-b0e5-59a91d099f5a | caricamento delle immagini troppo lento |
| 12 | 2026-04-29 | Bug | — | /survey/0c9a31be-b797-4c5f-b0e5-59a91d099f5a | non mi fa caricare piu' di 3 foto per ambiente |
| 13 | 2026-04-29 | Bug | — | /survey/0c9a31be-b797-4c5f-b0e5-59a91d099f5a | non mi estrapola le attrezzature dalla foto quando ne carico più di una. mi dice load failed |
| 14 | 2026-04-29 | Bug | — | /survey/0c9a31be-b797-4c5f-b0e5-59a91d099f5a | mi deve dare la possibilità di riaprire la persona per poter modificare o aggiungere dettagli |
| 15 | 2026-04-29 | Osservazione | — | /survey/0c9a31be-b797-4c5f-b0e5-59a91d099f5a | il medico competente e l'RSPP devono avere l'opzione che non sono dipendenti dell'azienda. Devono essere inseriti in una scheda a parte. |
| 16 | 2026-04-29 | Osservazione | — | /survey/0c9a31be-b797-4c5f-b0e5-59a91d099f5a | nelle attrezzature speciali aggiungere: trabattelli e ponteggi |
| 17 | 2026-04-29 | Osservazione | — | /survey/0c9a31be-b797-4c5f-b0e5-59a91d099f5a | se possibile, mettere tutta la tabella in un unica pagina cosi da non scorrere lateralmente con il mouse. |
| 18 | 2026-04-29 | Bug | — | /survey/0c9a31be-b797-4c5f-b0e5-59a91d099f5a | da rivedere rischio incendio e suoi sotto rischi |
| 19 | 2026-04-29 | Bug | — | /survey/0c9a31be-b797-4c5f-b0e5-59a91d099f5a | quando nel riepilogo chiedo di modificare le persone, mi apre la pagina degli ambienti |
| 20 | 2026-04-29 | Osservazione | — | /survey/0c9a31be-b797-4c5f-b0e5-59a91d099f5a | nella sezione di dpi e rischi specifici, come già accennato, richiediamo che non vi siano le mansioni ma i nominativi dei dipendenti. per ogni dipendente, andremo a flagrare i vari dpi e rischi a cui è esposto. (anche mediante l'utilizzo dell'IA) |
| 21 | 2026-05-04 | Osservazione | — | /survey/0c9a31be-b797-4c5f-b0e5-59a91d099f5a | Riusciresti a mettere anche la possibilità di avere la figura RLS esterna all'azienda? in quel caso si chiamerebbe RLST. Spiegazione per voi: Mentre l'RLS (Rappresentante dei Lavoratori per la Sicurezza) è una figura interna all'azienda, l'RLST è il Rappresentante dei Lavoratori per la Sicurezza Territoriale. |
| 22 | 2026-05-05 | Osservazione | — | /aziende/new | bisogna inserire l'opzione di compilazione dei campi "dati amministrativi" nella maggioranza dei casi queste informazioni non sono necessarie |
| 23 | 2026-05-05 | Osservazione | — | /aziende/new | la zona sismica, si deve compilare automaticamente in base alla sede operativa. serve aiuto AI |
| 24 | 2026-05-05 | Bug | — | /survey/7263b070-3d8f-44b1-87e0-d715bc2eecb9 | mi esce la scritta not found nell'inserimento dei DPI con AI |
| 25 | 2026-05-05 | Osservazione | — | /survey/7263b070-3d8f-44b1-87e0-d715bc2eecb9 | anche questa pagina deve essere tutta visibile senza scorrere a destra e sinistra |
| 26 | 2026-05-05 | Osservazione | — | /aziende/new | Per tutti i dati che sono nulli sul azienda per la sezione Dati Amministrativi - se dati sono nulli non deveono comparire da nessuna parte ne su dvr ne sull sopraluogo |
| 27 | 2026-05-05 | Osservazione | — | /aziende/new | la zona sismica dovrebbe essere selezionata in automatico con un pulsante a seguito di aere inserito il comune , la tabella e qui https://view.officeapps.live.com/op/view.aspx?src=https%3A%2F%2Frischi.protezionecivile.gov.it%2Fstatic%2F731c04d7fb1e26091a831455d7cfb9cf%2Fclassificazione-sismica-aggiornata-maggio-2025.xlsx&wdOrigin=BROWSELINK |
| 28 | 2026-05-05 | Idea | — | /admin/feedback | spostare la valutazioe dei rischi ome una pagina a parte perch enoviene fatto durante il sopralugo |
| 29 | 2026-05-05 | Bug | — | /assessments/mmc/7263b070-3d8f-44b1-87e0-d715bc2eecb9 | la valutazione deve essere fatta per dipendente , se posibil estrarre eta dall codice fscale , ci sono diversi errori sul salvataggio |
| 30 | 2026-05-07 | Idea | — | /assessments/risk/7263b070-3d8f-44b1-87e0-d715bc2eecb9 | INSERIRE UN "?" A LATO PER SUGGERIRE LA COMPILAZIONE DEI CAMPI |
| 31 | 2026-05-07 | Bug | — | /aziende/7263b070-3d8f-44b1-87e0-d715bc2eecb9 | NON C'è LA SCHERMATA RELATIVA AL PIANO DI MIGLIORAMENTO |
| 32 | 2026-05-07 | Osservazione | — | /aziende/new | ALL'INSERIMENTO DELLA PARTITA IVA, IL PROGRAMMA DEVE RICONOSCERE SE GIA' PRESENTE IL CLIENTE IN PIATTAFORMA |
| 33 | 2026-05-08 | Osservazione | — | /aziende/new | non mettere suggerimenti in grigio nelle caselle di compilazione lasciarle vuote grazie |
| 34 | 2026-05-08 | Bug | — | /survey/711dde59-4d18-4e52-801f-c1520bbb2417 | appena scrivi ti fa mettere la prima lettera e poi da invio al secondo tentativo va |
| 35 | 2026-05-08 | Idea | — | /survey/711dde59-4d18-4e52-801f-c1520bbb2417 | Sarebbe carino avere la possibilità di fleggare tutte le attrezzature ce con la voce seleziona tutto |
| 36 | 2026-05-09 | Osservazione | — | /assessments/risk/711dde59-4d18-4e52-801f-c1520bbb2417 | Nella valutazione del rischio incendio, devono esserci anche qua, per ogni voce, i numerini per il calcolo del rischio. Si può implementare un pulsante "come da valutazione allegata" e schiacciandolo flava tutti i campi con quella scritta |
| 37 | 2026-05-09 | Bug | — | /assessments/risk/711dde59-4d18-4e52-801f-c1520bbb2417 | le macrosezioni si devono aggiornare con la madia dei rischi presenti al suo interno. una volta che cambio ambiente mi si resettano come se fossero di default |
| 38 | 2026-05-11 | Osservazione | — | /survey/5c5d35f8-397e-4de4-ab09-6cbf47affc4c | NELLA TIPOLOGIA CONTRATTUALE, MANCA LA VOCE: SOCIO LAVORATORE |
| 39 | 2026-05-12 | Bug | — | /survey/0f449112-4106-4d57-b741-a59eb315b657 | Segnalando tutto con il pulsante segnala tutto su atrezzature ne selezziona solo uno alla volta |
| 40 | 2026-05-12 | Idea | — | /survey/0f449112-4106-4d57-b741-a59eb315b657 | aggiungere un tasto per selezzionare tutte le marcature ce |
| 41 | 2026-05-12 | Bug | — | /assessments/risk/5c5d35f8-397e-4de4-ab09-6cbf47affc4c | qualche volta sulla valutazione rischi non appare il dettaglio viene scritto in rosso errore nessun richio trovato poi se abiliti e disabiliti compaiono |
| 42 | 2026-05-12 | Osservazione | — | /documents | Sul DVR che viene generato come documento indice deve essere esploso con paginazione e pu dettagliato |
| 43 | 2026-05-12 | Osservazione | — | /documents | Impaginazzioe dovrebbe rispettare piu le tabelle ei capitoli |
| 44 | 2026-05-12 | Bug | — | /documents | Sulla generazione del DVR 7 macchine attrezzature impanti non mette le cose giuste nel dvr generato |
| 45 | 2026-05-12 | Osservazione | — | /admin/feedback | Test mirror — confirming feedback → GitHub Issues integration. Please ignore / close. |
| 46 | 2026-05-13 | Osservazione | #5 | /admin/feedback | Second smoke test after token rotation. Please close. |
| 47 | 2026-05-14 | Idea | #6 | /aziende/new | AGGIUGERE LE API A PAGAMENTO PER COMPLETAMENTO DELLA RAGIONE SOCIALE |
| 48 | 2026-05-14 | Idea | #7 | /survey/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | VISUALIZZARE ANTEPRIMA FOTO CARICATE |
| 49 | 2026-05-14 | Osservazione | #8 | /survey/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | riesci ad inserire un tasto dove mi fa selezionare tutte le marcature CE |
| 50 | 2026-05-14 | Osservazione | #9 | /survey/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | togliere il tasto "copia da altra mansione" |
| 51 | 2026-05-14 | Bug | #10 | /aziende/new | nel caso della ditta individuale il codice fiscale deve essere quello della persona fisica |
| 52 | 2026-05-14 | Osservazione | #11 | /aziende/new | nel caso di più sedi operative, mi deve dare la possibilità di aggiungerla |
| 53 | 2026-05-14 | Idea | #12 | /aziende/new | nel caso della sede legale uguale a quella operativa, inserire un flag con scritto "stessa sede" |
| 54 | 2026-05-14 | Osservazione | #13 | /survey/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | i dipendenti devono essere nell'ordine di inserimento |
| 55 | 2026-05-14 | Osservazione | #14 | /survey/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | inserire nella tipologia contrattuale la voce: SMART WORKING |
| 56 | 2026-05-18 | Bug | #15 | /survey/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | rimetti "copia da altra persona" e togli "copia da stessa mansione" |
| 57 | 2026-05-18 | Osservazione | #16 | /assessments/risk/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | QUANDO GENERO LE MISURE DI MIGLIORAMENTO NELLA PRIMA MACRO SEZIONE, NELLE SEZIONI SUCCESSIVE, LA VALUTAZIONE ME LA FA FARE SCORRENDO A DX E SX. DEVE ESSERE TUTTO NELLA STESSA PAGINA |
| 58 | 2026-05-18 | Bug | #17 | /aziende/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | NON SALVA LE MISURE DI MGLIORAMENTO. ME LO DEVE DARE COMPLETATO ANCHE SE NON VADO AD INSERIRE LE MISURE DI MIGLIORAMENTO. LE MISURE SONO A DISCREZIONE DI CHI REDIGE IL DVR |
| 59 | 2026-05-18 | Bug | #18 | /assessments/mmc/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | NON MI TIENE SALVATA LA VALUTAZIONE EFFETTUATA PRECEDENTEMENTE |
| 60 | 2026-05-18 | Bug | #19 | /assessments/vdt/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | NON SALVA LE VALUTAZIONI VDT. DEVE ESSERCI L'ELENCO DEI LAVORATORI GIA VALUTATI |
| 61 | 2026-05-18 | Osservazione | #20 | /assessments/stress/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | INSERIRE LE MISURE DI CORREZIONE SUGGERITO DALL' AI |
| 62 | 2026-05-18 | Osservazione | #21 | /survey/ba56a58d-70c1-4128-874a-d37fc60c5f87 | INSERIRE PUNTO DI DOMANDA SULL'INSERIMENTO DEI DATI DELL'AZIENDA NEI CAMPI |
| 63 | 2026-05-18 | Bug | #22 | /survey/ba56a58d-70c1-4128-874a-d37fc60c5f87 | i locali inseriti devono rispettare l'ordine di inserimento, devo avere la possibilità di modificare l'ordine degli ambienti |
| 64 | 2026-05-18 | Osservazione | #23 | /survey/ba56a58d-70c1-4128-874a-d37fc60c5f87 | AGGIUNGERE ALLA LISTA TIPOLOGIA CONTRATTUALE: - APPRENDISTA - ARTIGIANO |
| 65 | 2026-05-18 | Osservazione | #24 | /survey/ba56a58d-70c1-4128-874a-d37fc60c5f87 | DI FIANCO ALLA SCRITTA "CARICA SCHEDE DI SICUREZZA", RIUSCIRESTI AD INSERIRE LA SCRITTA "DELLE SOSTANZE CHIMICHE" |
| 66 | 2026-05-18 | Osservazione | #26 | /aziende/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | nei prossimi passi, aggiungere un ulteriore punto dopo la valutazione dei rischi per generare le misure di miglioramento |
| 67 | 2026-05-18 | Osservazione | #27 | /assessments/mmc/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | inserire un piccola "x" sul nominativo del dipendente così da eliminare la valutazione in caso di errore. |
| 68 | 2026-05-18 | Bug | #28 | /assessments/mmc/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | non mi salva le valutazioni, ne primarie ne secondarie |
| 69 | 2026-05-18 | Osservazione | #29 | /assessments/vdt/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | riesci ad inserire una piccola "x" come nel MMC per eliminare il dato in caso di errore |
| 70 | 2026-05-18 | Bug | #30 | /assessments/vdt/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | anche in questo caso non salva i valori inseriti |
| 71 | 2026-05-18 | Bug | #31 | /assessments/stress/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | non salva le misure correttive e quando clicco salva non cambia il colore e non indica all'utente che è stato salvato |
| 72 | 2026-05-18 | Bug | #32 | /assessments/gestanti/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | elaborare i dati dell'allegato gestanti |
| 73 | 2026-05-18 | Osservazione | #33 | /aziende/new | togliere tutti i punti di domanda nella schermata nuova azienda |
| 74 | 2026-05-18 | Osservazione | #34 | /survey/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | aggiungere campo "verifiche periodiche" che era stato rimosso, con il flag seleziona tutto |
| 75 | 2026-05-18 | Osservazione | #35 | /survey/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | inserire il campo "destinazione d'uso" della sostanza chimica, lo estrapola dalla sds |
| 76 | 2026-05-22 | Osservazione | #39 | /aziende/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | il punto 3 si deve chiamare Valutazione Rischi |
| 77 | 2026-05-22 | Osservazione | #40 | /aziende/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | la frase al punto 3: 32 rischi senza misure (su 33). Apri l'editor per definirle o generarle con AI. deve essere modificata con: Valutare i rischi presenti all'interno dell'azienda |
| 78 | 2026-05-22 | Idea | #41 | /aziende/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | viene completato il pt. 3 quanto tutti gli ambienti vengono cliccati durante la valutazione dei rischi. |
| 79 | 2026-05-22 | Bug | #42 | /aziende/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | il piano di miglioramento deve essere su un unica pagina e senza scorrere a dx |
| 80 | 2026-05-22 | Osservazione | #43 | /aziende/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | al posto della voce PROCEDURA, rinominarla con la voce ATTIVITA' |
| 81 | 2026-05-22 | Osservazione | #44 | /aziende/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | rinominare MISURA con la voce RISCHIO |
| 82 | 2026-05-22 | Osservazione | #45 | /aziende/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | aggiungere una colonna con la voce MISURA DI MIGLIORAMENTO (l'ai deve ragionare e creare una misura di miglioramento per eliminare o abbassare al limite il rischio rilevato) |
| 83 | 2026-05-22 | Osservazione | #46 | /aziende/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | aggiornare anche i campi su AGGIUNGI MISURA |
| 84 | 2026-05-22 | Bug | #47 | /assessments/mmc/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | non si elimina la persona in caso di errato inserimento |
| 85 | 2026-05-22 | Bug | #48 | /assessments/mmc/5d23a5a4-13f7-471e-92fc-38c4b11c91e2 | non mi salva ancora la valutazione effettuata precedentemente |
| 86 | 2026-05-22 | Osservazione | #49 | /assessments/incendio/a0e5e547-5ac2-49c1-af78-55764afd6871 | nella sezione DETTAGLI AREA, dovrebbe aprirsi una tendina che mi fa scegliere il locale/ambiente da valutare |
| 87 | 2026-05-22 | Idea | #50 | /assessments/pos/a0e5e547-5ac2-49c1-af78-55764afd6871 | integrar il pulsate AI per la complazione dei campi: descrizione, rischi, dpi |
| 88 | 2026-05-22 | Osservazione | #51 | /assessments/duvri/a0e5e547-5ac2-49c1-af78-55764afd6871 | Togliere i campi: COSTI DELLA SICUREZZA e COSTO APPALTO |
| 89 | 2026-05-25 | Bug | #52 | /survey/50e371cf-d45a-439a-be58-ccb9e1b15158 | SUPPORTARE FORMATO HEIC X FOTO IPHONE |
| 90 | 2026-05-25 | Bug | #53 | /aziende/50e371cf-d45a-439a-be58-ccb9e1b15158 | NON MI CARICA I DATI DELLA VISURA |
| 91 | 2026-05-25 | Bug | #54 | /survey/50e371cf-d45a-439a-be58-ccb9e1b15158 | le persone devono essere disposte in ordine di inserimento |
| 92 | 2026-05-26 | Bug | #55 | /assessments/mmc/50e371cf-d45a-439a-be58-ccb9e1b15158 | non mi salva le valutazioni che effettuo |
| 93 | 2026-05-26 | Bug | #56 | /assessments/vdt/50e371cf-d45a-439a-be58-ccb9e1b15158 | non mi salva le valutazioni effettuate |
| 94 | 2026-05-26 | Osservazione | #57 | /assessments/pos/50e371cf-d45a-439a-be58-ccb9e1b15158 | togliere il campo "riunioni di coordinamento" e rinominarlo come "DESCRIZIONE DEL CANTIERE" |
| 95 | 2026-05-26 | Osservazione | #58 | /assessments/pos/50e371cf-d45a-439a-be58-ccb9e1b15158 | l'elenco dei rischi e dei DPI deve essere visibile in un unica schermata |
| 96 | 2026-05-26 | Osservazione | #59 | /assessments/pos/50e371cf-d45a-439a-be58-ccb9e1b15158 | nelle "Fasi per la matrice DPI" deve esserci la possibilità di aggiungere manualmente delle lavorazioni |
| 97 | 2026-05-26 | Osservazione | #60 | /assessments/pos/50e371cf-d45a-439a-be58-ccb9e1b15158 | anche per quanto riguarda i ruoli in cantiere, devo avere la possibilità di aggiungere delle mansioni alternative |
| 98 | 2026-05-26 | Osservazione | #61 | /assessments/pos/50e371cf-d45a-439a-be58-ccb9e1b15158 | all'interno delle matrici dpi quando si seleziona il ruolo, devo avere la possibilità di selezionare la voce: non effettua questa operazione |
| 99 | 2026-05-29 | Bug | #62 | /assessments/vdt/50e371cf-d45a-439a-be58-ccb9e1b15158 | NON ELIMINA LE VALUTAZIONI INCASO IO LE VOGLIA CANCELLARE |
| 100 | 2026-05-29 | Bug | #64 | /assessments/pos/50e371cf-d45a-439a-be58-ccb9e1b15158 | PULSANTE COPILA CON AI CHE IM INDICA QUALI DPI SONO NECESSARI PER OGNI LAVORAZIONE "MATRICE DPI" |
| 101 | 2026-05-29 | Osservazione | #65 | /assessments/haccp/50e371cf-d45a-439a-be58-ccb9e1b15158 | INSERIRE ELENCO ATTREZZATURE CON LA POSSIBILITA' DI SELEZIONARE SOLO QUELLE SOTTOPOSTE A CONTROLLO HACCP |
| 102 | 2026-05-29 | Idea | #66 | /assessments/haccp/50e371cf-d45a-439a-be58-ccb9e1b15158 | PULSANTE AI PER LA GENERAZIONE DI NUOVI CCP. MAGARI IO INSERISCO IL CCP E AI MI COMPILA I DETTAGLI |
| 103 | 2026-06-08 | Bug | #67 | /survey/50e371cf-d45a-439a-be58-ccb9e1b15158 | sulla modifica delle persone, dovrebbe restare tutto senza dover scrollare a dx e sx |
| 104 | 2026-06-08 | Bug | #68 | /assessments/risk/50e371cf-d45a-439a-be58-ccb9e1b15158 | ogni tanto sul dettaglio dei rischi quando si seleziona il rischio compare un errore, quando si disabilita e riabilita, caricano correttamente |
| 105 | 2026-06-08 | Bug | #69 | /aziende/50e371cf-d45a-439a-be58-ccb9e1b15158 | l'icona della valutazione rischi diventa verde quando uno ha cliccato su ognuno degli ambienti |
| 106 | 2026-06-08 | Osservazione | #70 | /aziende/50e371cf-d45a-439a-be58-ccb9e1b15158 | fare un tasto con scritto salva misure e una volta cliccato l'icona diventa verde |
| 107 | 2026-06-08 | Osservazione | #71 | /aziende/50e371cf-d45a-439a-be58-ccb9e1b15158 | creare una misura di miglioramento di default con scritto: inviare nomina telematica RLS presso portale INAIL. |
| 108 | 2026-06-08 | Osservazione | #72 | /aziende/50e371cf-d45a-439a-be58-ccb9e1b15158 | fare una tendina sulla voce responsabile che si abbassa e le voci sono: Datore di Lavoro, RSPP, Preposto |
| 109 | 2026-06-08 | Bug | #73 | /documents | nella scelta dell'azienda, si deve vedere tutto il nome e la sede |
| 110 | 2026-06-10 | Bug | #74 | /survey/a1cacba3-f97b-4d61-90aa-7b0b79069050 | GLI AMBIENTI NON RIMANGONO NELL'ORDINE DI INSERIMENTO |
| 111 | 2026-06-10 | Bug | #75 | /survey/a1cacba3-f97b-4d61-90aa-7b0b79069050 | LE PERONE NON RIMANGONO NELL'ORDINE DI INSERIMENTO |
| 112 | 2026-06-10 | Bug | #76 | /survey/a1cacba3-f97b-4d61-90aa-7b0b79069050 | mi duplica i nomi delle attrezzature nel riepilogo |
| 113 | 2026-06-22 | Bug | — | /assessments/microclima/50e371cf-d45a-439a-be58-ccb9e1b15158 | mi crasha la pagina quando vado ad inserire il valore umidità nello stress da calore |
| 114 | 2026-08-03 | Osservazione | — | /assessments/mmc/2b1c9da7-a79d-4ca4-87b6-afb005465bef | Nel documento elaborato, nella sezione "tavole di valutazione del rischio mmc", deve essere suddivisa per persona e sotto ogni persona, tutte le sue valutazioni. |
| 115 | 2026-08-03 | Osservazione | — | /assessments/mmc/2b1c9da7-a79d-4ca4-87b6-afb005465bef | Nel documento elaborato, nella sezione "quadro sinottico di esposizione", visualizza solo una delle valutazioni effettuate per una persona. |
| 116 | 2026-08-04 | Bug | — | /assessments/pos/2b1c9da7-a79d-4ca4-87b6-afb005465bef | NELLA SCHERMATA DI INSERIMENTO DEI DPI NON MI FA SPAZIARE E METTERE LE VIRGOLE TRA UNA PAROLA E L'ALTRA |
| 117 | 2026-08-04 | Bug | — | /assessments/pos/2b1c9da7-a79d-4ca4-87b6-afb005465bef | NELLA SCHERMATA DI INSERIMENTO RISCHI MI FA SPAZIARE E METTERE LE VIRGOLE TRA UNA PAROLA E L'ALTRA |
| 118 | 2026-08-04 | Bug | — | /assessments/pos/2b1c9da7-a79d-4ca4-87b6-afb005465bef | IN OGNI CAMPO DA COMPILARE NON VA LO SPAZIO E LA VIRGOLA |
| 119 | 2026-08-04 | Bug | — | /assessments/pos/2b1c9da7-a79d-4ca4-87b6-afb005465bef | Le caselle con le descrizioni devono essere completamente visibili |
| 120 | 2026-08-04 | Osservazione | — | /assessments/duvri/2b1c9da7-a79d-4ca4-87b6-afb005465bef | nella sezione attrezzature, devono comparire tutte le attrezzature presenti all'interno del rischio master |
| 121 | 2026-08-05 | Osservazione | — | /assessments/microclima/2b1c9da7-a79d-4ca4-87b6-afb005465bef | nel primo paragrafo cambiare T rettale con T corporea. Suona meglio |
| 122 | 2026-08-20 | Bug | — | /assessments/pee/a923821e-c5a9-4e56-8c2c-104dc9c1565d | nella sezione numeri telefonici di emergenza ci sono problemi nella compilazione. nella sezioni enti mi fa uscire dal riquadro ogni lettera che scrivi. nella sezione numeri non mi fa scrivere |
