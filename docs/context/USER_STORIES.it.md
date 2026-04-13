> **NIUEXA** | Automazione Aziendale Basata su AI  
> *Piattaforma di Automazione DVR — N2O SRL*  
> Versione 1.0 | Aprile 2026 | Gregor Maric  
> Riservato — Niuexa & N2O SRL

---

# Storie Utente

Ogni storia segue il formato `Come <profilo>, voglio <funzionalità>, in modo da <beneficio>` ed è accompagnata da **Criteri di Accettazione** espressi in formato Dato che / Quando / Allora. Le etichette dell'interfaccia utente sono virgolettate in italiano per coincidere con la versione finale del prodotto.

## Profili Utente

### Operatore sul Campo
Consulente per la sicurezza che si reca presso le sedi del cliente per condurre i sopralluoghi e raccogliere i dati. Utilizza tablet o smartphone, spesso in condizioni di connessione assente o instabile.

### Operatore in Ufficio
Consulente per la sicurezza che revisiona i documenti generati dall'AI, regola gli indici di rischio e finalizza la documentazione. Utilizza una postazione desktop con monitor multipli.

### Amministratore
Gestisce il portafoglio clienti, supervisiona la generazione dei documenti, si occupa di fatturazione e consegna. Ha accesso a tutti i clienti e ai registri di audit.

---

## Epica 1: Scheda di Rilevazione Digitale

### Raccolta dati sul campo

#### US-1.1
Come operatore sul campo, voglio compilare i campi dei dati aziendali strutturati (ragione sociale, sede, codice ATECO) in modo da non doverli reinserire successivamente.

**Criteri di Accettazione:**

- **Dato che** sono allo Step 1 "Azienda" del wizard di rilevazione, **quando** inserisco ragione sociale, partita IVA, indirizzo sede e codice ATECO, **allora** i dati vengono salvati automaticamente come bozza entro 2 secondi e persistono tra sessioni
- **Dato che** lascio vuoto un campo obbligatorio, **quando** provo ad avanzare allo Step 2, **allora** il campo viene evidenziato in rosso con il messaggio "Campo obbligatorio" e la navigazione viene bloccata
- **Dato che** inserisco una partita IVA non valida (diversa da 11 cifre) o un codice ATECO non conforme al formato `NN.NN.NN`, **quando** il campo perde il focus, **allora** appare un errore inline e il campo viene escluso dal salvataggio automatico fino alla correzione

#### US-1.2
Come operatore sul campo, voglio checklist di attrezzature dinamiche che cambino in base al tipo di ambiente (ufficio, magazzino, cucina) in modo da vedere solo gli elementi pertinenti.

**Criteri di Accettazione:**

- **Dato che** sono allo Step 4 "Attrezzature" con un ambiente di tipo "Ufficio", **quando** il pannello attrezzature si carica, **allora** vedo solo gli elementi pertinenti all'ufficio (scrivania, sedia ergonomica, monitor, tastiera, mouse, stampante)
- **Dato che** cambio il tipo di ambiente da "Ufficio" a "Magazzino", **quando** la modifica è confermata, **allora** la checklist si aggiorna mostrando gli elementi del magazzino (scaffalatura, transpallet, muletto, casco) e gli elementi precedentemente selezionati per l'ufficio vengono preservati sull'ambiente originale
- **Dato che** sto lavorando su un ambiente il cui tipo non è nell'elenco predefinito, **quando** la checklist si carica, **allora** vedo una checklist generica con un pulsante "Aggiungi attrezzatura" per inserire elementi personalizzati

#### US-1.3
Come operatore sul campo, voglio caricare le foto di ogni ambiente di lavoro e delle attrezzature in modo che possano essere utilizzate durante la generazione dei documenti.

**Criteri di Accettazione:**

- **Dato che** sono allo Step 3 "Ambienti" e ho selezionato un ambiente, **quando** tocco "Aggiungi foto", **allora** si apre la fotocamera del dispositivo e posso scattare o selezionare fino a 10 foto per ambiente
- **Dato che** ho caricato una foto, **quando** il caricamento è completato, **allora** la foto appare come miniatura con icona di eliminazione, nome del file originale e dimensione
- **Dato che** provo a caricare un file più grande di 10 MB o in un formato non supportato (diverso da JPG/PNG/HEIC), **quando** il caricamento viene avviato, **allora** vedo un toast inline "Formato non supportato o file troppo grande (max 10 MB)" e il file viene rifiutato
- **Dato che** la mia connessione di rete cade durante il caricamento, **quando** la connettività viene ripristinata, **allora** il caricamento viene riprovato automaticamente e vedo un indicatore persistente "Caricamento in corso"

#### US-1.4
Come operatore sul campo, voglio registrare i dipendenti con i loro ruoli, l'assegnazione agli ambienti e le qualifiche in un modulo strutturato.

**Criteri di Accettazione:**

- **Dato che** sono allo Step 2 "Persone", **quando** tocco "Aggiungi persona", **allora** si apre una modale con i campi nome, cognome, codice fiscale, mansione, ambienti assegnati (selezione multipla) e qualifiche
- **Dato che** inserisco un codice fiscale che non rispetta il pattern alfanumerico di 16 caratteri, **quando** il campo perde il focus, **allora** viene mostrato un errore inline "Codice fiscale non valido" e il pulsante Salva è disabilitato
- **Dato che** salvo una persona valida, **quando** la modale si chiude, **allora** la persona appare come riga nella tabella Persone con un menu di azioni al passaggio del mouse (Modifica, Elimina)
- **Dato che** tocco Elimina su una persona, **quando** appare la modale di conferma, **allora** devo confermare esplicitamente "Elimina" prima che la riga venga rimossa (nessun soft delete in MVP)

#### US-1.5
Come operatore sul campo, voglio una lista di rischi contestualizzata (non l'elenco completo del Decreto) in modo da poter rapidamente segnalare i rischi applicabili per ogni ambiente.

**Criteri di Accettazione:**

- **Dato che** sono allo Step 5 "Rischi" con ambienti e attrezzature già dichiarati, **quando** la lista dei rischi si carica, **allora** vengono mostrati solo i rischi contestualmente rilevanti per gli ambienti e le categorie di attrezzature selezionate (filtrati dal catalogo completo del D.Lgs. 81)
- **Dato che** tocco un rischio per segnalarlo applicabile a un ambiente, **quando** il toggle si attiva, **allora** la barra di riepilogo in fondo aggiorna il conteggio "X rischi selezionati"
- **Dato che** torno allo Step 3 "Ambienti" e aggiungo o rimuovo un ambiente dopo aver segnato i rischi, **quando** torno allo Step 5, **allora** vedo un banner "Ambienti modificati - rivedi le selezioni" che mi invita a riconfermare

#### US-1.6
Come operatore sul campo, voglio che il cliente possa controfirmare digitalmente la rilevazione completata sul mio dispositivo in modo da avere prova legale dell'accettazione.

**Criteri di Accettazione:**

- **Dato che** sono allo Step 7 "Riepilogo" e tutti gli step precedenti sono completi, **quando** scorro fino alla sezione di controfirma, **allora** la canvas per la firma è abilitata e un campo timestamp è auto-popolato
- **Dato che** uno degli step precedenti è incompleto, **quando** apro lo Step 7, **allora** la canvas è disabilitata e un banner elenca gli elementi mancanti come link cliccabili
- **Dato che** il cliente ha disegnato una firma e tocco "Conferma firma", **quando** l'azione si completa, **allora** la firma viene salvata come PNG associato alla rilevazione con timestamp lato server e lo stato della rilevazione passa a "Firmato"
- **Dato che** la rilevazione è già firmata, **quando** un utente prova a modificare uno step, **allora** tutti i campi diventano in sola lettura e viene offerto un pulsante "Apri revisione" per un flusso di modifica tracciato

#### US-1.7
Come operatore sul campo, voglio assegnare ruoli di sicurezza (RSPP, RLS, primo soccorso, antincendio, preposto) al personale durante la rilevazione in modo che l'intestazione del DVR sia auto-popolata.

**Criteri di Accettazione:**

- **Dato che** apro la modale Aggiungi/Modifica Persona, **quando** spunto una o più caselle di ruolo (RSPP, RLS, ASPP, addetto primo soccorso, addetto antincendio, preposto), **allora** i badge dei ruoli appaiono accanto al nome della persona nella tabella Persone
- **Dato che** la rilevazione non ha alcuna persona contrassegnata come RSPP, **quando** provo ad avanzare allo Step 7, **allora** la validazione mi blocca con "È richiesto almeno un RSPP per completare la rilevazione"
- **Dato che** una persona ricopre più ruoli, **quando** il DVR viene generato, **allora** tutti i suoi ruoli appaiono nelle tabelle corrispondenti del DVR Master senza duplicazioni

### Caricamento Schede di Sicurezza Chimiche

#### US-1.8
Come operatore, voglio caricare in batch fino a 20 SDS chimiche in PDF alla volta in modo da non doverle elaborare una per una.

**Criteri di Accettazione:**

- **Dato che** sono allo Step 6 "Sostanze Chimiche", **quando** trascino 20 file PDF nell'area di caricamento, **allora** tutti e 20 i file vengono accodati con barre di avanzamento individuali
- **Dato che** provo a caricare un 21° file nello stesso batch, **quando** il file viene aggiunto, **allora** appare un messaggio inline "Massimo 20 file per caricamento" e il file viene rifiutato
- **Dato che** rilascio un file che non è PDF o supera i 10 MB, **quando** il file entra in coda, **allora** viene immediatamente contrassegnato come fallito con la motivazione e nessuna estrazione viene tentata

#### US-1.9
Come operatore, voglio che l'AI estragga automaticamente nome del prodotto, produttore, pittogrammi, stato della miscela e frasi H/P da ogni SDS in modo da non doverli trascrivere.

**Criteri di Accettazione:**

- **Dato che** una SDS PDF ha terminato il caricamento, **quando** il job di estrazione si avvia, **allora** la riga del file mostra lo stato "Estrazione in corso" con uno spinner, poi "Completata" con i campi estratti popolati
- **Dato che** l'AI non riesce a estrarre un campo con alta confidenza, **quando** l'estrazione si completa, **allora** quel campo viene lasciato vuoto, contrassegnato con un'icona di avviso gialla, e un tooltip dice "Confidenza bassa - inserisci manualmente"
- **Dato che** l'estrazione fallisce completamente (es. immagine scansionata senza OCR), **quando** il job termina, **allora** la riga mostra lo stato "Estrazione fallita" e un pulsante "Inserisci manualmente" apre una riga editabile vuota

#### US-1.10
Come operatore, voglio revisionare e correggere i dati chimici estratti dall'AI in una tabella prima che vengano finalizzati in modo da poter individuare gli errori.

**Criteri di Accettazione:**

- **Dato che** l'estrazione AI è completata per almeno una SDS, **quando** apro la Tabella di Revisione Estrazione, **allora** ogni cella è editabile inline e i valori generati dall'AI sono visivamente contrassegnati con un badge "AI"
- **Dato che** modifico una cella generata dall'AI, **quando** confermo la modifica, **allora** il badge AI viene rimosso e sostituito da un indicatore "Revisionato" con il mio ID utente
- **Dato che** tocco "Conferma estrazione", **quando** l'azione si completa, **allora** le sostanze chimiche vengono persistite nel database e l'indicatore dello Step 6 diventa verde

---

## Epica 2: Generazione del DVR Master

#### US-2.1
Come operatore in ufficio, voglio che il sistema generi automaticamente la descrizione dell'azienda dai dati della rilevazione + visura + sito web utilizzando l'AI in modo da non dover scrivere testi standard.

**Criteri di Accettazione:**

- **Dato che** la rilevazione è firmata e una visura PDF è allegata, **quando** clicco "Genera descrizione azienda", **allora** l'AI produce una descrizione in italiano di 200-400 parole e la mostra in un editor di testo formattato con un badge "AI"
- **Dato che** modifico il testo generato, **quando** salvo, **allora** il badge cambia in "Modificato dall'utente" e la versione AI originale viene conservata nello storico delle versioni
- **Dato che** la chiamata AI fallisce o va in timeout (>30s), **quando** l'errore viene mostrato, **allora** vedo "Generazione fallita - riprova o inserisci manualmente" con un pulsante Riprova e l'editor rimane utilizzabile per l'inserimento manuale

#### US-2.2
Come operatore in ufficio, voglio che il contesto territoriale (zona sismica, normative locali) sia auto-popolato in modo da non doverlo cercare per ogni comune.

**Criteri di Accettazione:**

- **Dato che** ho inserito il comune allo Step 1 "Azienda", **quando** la generazione del DVR si avvia, **allora** il sistema recupera la zona sismica (1-4) e le normative regionali applicabili da una tabella di lookup locale e le inserisce nella sezione contesto della Parte I
- **Dato che** il comune non è nella tabella di lookup, **quando** la ricerca fallisce, **allora** il campo viene lasciato vuoto con un avviso "Comune non trovato - inserisci manualmente"
- **Dato che** i dati territoriali sono auto-popolati, **quando** li visualizzo nell'editor, **allora** sono in sola lettura per default con un pulsante "Sovrascrivi" per abilitare la modifica manuale

#### US-2.3
Come operatore in ufficio, voglio che le tabelle dei rischi siano pre-popolate per ogni ambiente con punteggi di severità contestualizzati che posso revisionare e modificare.

**Criteri di Accettazione:**

- **Dato che** apro l'Interfaccia di Valutazione Rischi per un DVR generato, **quando** la tabella si carica, **allora** ogni ambiente appare come sezione raggruppata con i rischi pre-compilati da una matrice di punteggio predefinita
- **Dato che** modifico il valore di P o D per un rischio, **quando** il valore cambia, **allora** I = 2*D + P viene ricalcolato in tempo reale e la fascia di colore della riga si aggiorna di conseguenza
- **Dato che** voglio annullare le mie modifiche, **quando** clicco l'icona "Reset al default" su una riga, **allora** il punteggio originale suggerito dall'AI viene ripristinato e il flag di override viene rimosso

#### US-2.4
Come operatore in ufficio, voglio che la lista delle attrezzature con marcatura CE sia auto-popolata dalla rilevazione in modo da non duplicare l'inserimento dati.

**Criteri di Accettazione:**

- **Dato che** le attrezzature sono state dichiarate allo Step 4 della rilevazione, **quando** il DVR viene generato, **allora** la tabella delle attrezzature nella Parte II viene popolata con marca, modello, anno e checkbox CE
- **Dato che** un elemento è privo di marcatura CE, **quando** la tabella viene renderizzata, **allora** la riga viene evidenziata in rosso e una nota a piè di pagina viene aggiunta automaticamente al DVR menzionando la non conformità
- **Dato che** modifico una riga inline (es. aggiungo un modello mancante), **quando** salvo, **allora** la modifica si propaga ai dati della rilevazione in modo da essere riutilizzata nelle generazioni successive

#### US-2.5
Come operatore in ufficio, voglio che le tabelle del personale con ruoli e assegnazioni agli ambienti siano auto-generate in modo che la sezione personale non richieda lavoro manuale.

**Criteri di Accettazione:**

- **Dato che** le persone sono state dichiarate allo Step 2 con mansioni, ambienti e qualifiche, **quando** il DVR viene generato, **allora** la sezione personale elenca ogni persona raggruppata per ambiente con la sua mansione, qualifiche e badge dei ruoli (RSPP/RLS/ecc.)
- **Dato che** la rilevazione viene aggiornata dopo che un DVR è stato generato, **quando** rigenerato lo stesso documento, **allora** la tabella del personale riflette il nuovo stato della rilevazione e viene mostrato un diff nello storico delle versioni
- **Dato che** la tabella viene renderizzata nel .docx finale, **quando** la apro in Word, **allora** la tabella usa lo stile ufficiale N2O (riga di intestazione in grigio scuro, righe alternate ombreggiate)

#### US-2.6
Come operatore in ufficio, voglio misure di miglioramento suggerite dall'AI basate sui rischi identificati che posso accettare, modificare o rifiutare.

**Criteri di Accettazione:**

- **Dato che** una riga di rischio è espansa nell'Interfaccia di Valutazione Rischi, **quando** il pannello misure di prevenzione si carica, **allora** l'AI restituisce 2-5 suggerimenti con pulsanti Accetta / Modifica / Rifiuta per elemento
- **Dato che** accetto un suggerimento, **quando** l'azione si completa, **allora** la misura viene aggiunta al testo del DVR con un tag "AI - accettato" e salvata in una libreria di misure per cliente per il riutilizzo
- **Dato che** rifiuto un suggerimento, **quando** l'azione si completa, **allora** la misura viene rimossa dalla vista e un segnale di feedback negativo viene registrato per il futuro fine-tuning del modello
- **Dato che** voglio aggiungere una mia misura, **quando** clicco "Aggiungi misura personalizzata", **allora** appare una riga editabile vuota e la misura salvata viene contrassegnata come "Manuale"

#### US-2.7
Come operatore in ufficio, voglio impostare i punteggi P (probabilità) e D (danno) per ogni rischio e che il sistema calcoli automaticamente I = 2*D + P.

**Criteri di Accettazione:**

- **Dato che** sono su una riga di rischio con P e D vuoti, **quando** inserisco P=2 e D=3, **allora** la colonna I mostra 8 con la fascia arancione "Grave"
- **Dato che** provo a inserire un valore al di fuori dell'intervallo 1-3 in uno dei due campi, **quando** il campo perde il focus, **allora** il valore viene rifiutato e viene mostrato un tooltip "Valore consentito: 1-3"
- **Dato che** ho selezionato più righe tramite checkbox, **quando** uso l'azione bulk "Imposta P/D", **allora** i valori P e D scelti vengono applicati a ogni riga selezionata e I viene ricalcolato per ciascuna
- **Dato che** modifico un valore che provoca un cambio di fascia (es. I passa da 8 "Grave" a 9 "Gravissimo"), **quando** il ricalcolo termina, **allora** la riga anima la transizione di colore in 200 ms

#### US-2.8
Come operatore in ufficio, voglio l'output finale del DVR come .docx professionalmente formattato con copertina, logo e indice.

**Criteri di Accettazione:**

- **Dato che** tutte le sezioni del DVR sono complete e revisionate, **quando** clicco "Genera DVR finale", **allora** un job in background produce un .docx contenente copertina (logo + ragione sociale + data), indice, tutte e quattro le parti (I-IV) e ~111 tabelle secondo la mappatura del template
- **Dato che** la generazione termina con successo, **quando** il file è pronto, **allora** ricevo una notifica desktop e il file è scaricabile dal cassetto documenti con un nome file versionato `DVR_<ragione_sociale>_<AAAAMMGG>_v<N>.docx`
- **Dato che** la generazione fallisce a metà, **quando** l'errore viene catturato, **allora** il file parziale viene scartato, lo stato del documento torna a "Bozza" e l'errore viene loggato con un messaggio comprensibile

#### US-2.9
Come operatore in ufficio, voglio il tracciamento delle versioni per le revisioni dei documenti in modo da poter auditare le modifiche nel tempo.

**Criteri di Accettazione:**

- **Dato che** ho generato un DVR almeno due volte, **quando** apro il pannello Storico Versioni, **allora** vedo un elenco cronologico con numero di versione, utente, timestamp e un pulsante "Differenze"
- **Dato che** clicco "Differenze" tra v2 e v3, **quando** il diff si carica, **allora** vedo un confronto affiancato che evidenzia testo/tabelle aggiunti, rimossi e modificati
- **Dato che** voglio ripristinare una versione precedente, **quando** clicco "Ripristina versione", **allora** viene creata una nuova versione a partire dallo snapshot storico (nessuna sovrascrittura distruttiva)

---

## Epica 3: Allegati al DVR

### MMC (Movimentazione Manuale dei Carichi - NIOSH)

#### US-3.1
Come operatore, voglio inserire i parametri di sollevamento per lavoratore (altezza, dislocazione, distanza, angolo, presa, frequenza, durata, peso effettivo) in modo da poter calcolare l'indice NIOSH.

**Criteri di Accettazione:**

- **Dato che** apro il modulo MMC per un lavoratore, **quando** il modulo si carica, **allora** tutti gli 8 parametri NIOSH sono presentati con le unità (cm per le distanze, ° per l'angolo, kg per il peso, sollevamenti/min per la frequenza)
- **Dato che** inserisco un valore al di fuori dell'intervallo valido per un parametro (es. dislocazione > 175 cm), **quando** il campo perde il focus, **allora** un errore inline spiega l'intervallo valido e il valore viene escluso dal calcolo
- **Dato che** un lavoratore esegue più operazioni di sollevamento distinte, **quando** clicco "Aggiungi sollevamento", **allora** viene aggiunto un ulteriore set di parametri e calcolato in modo indipendente

#### US-3.2
Come operatore, voglio che il sistema deduca automaticamente CP (costante di peso) dal sesso e dall'età del lavoratore in modo da non doverlo cercare.

**Criteri di Accettazione:**

- **Dato che** il sesso del lavoratore è Maschio e l'età è "adulto" (18-45), **quando** il modulo MMC si apre, **allora** CP è auto-compilato con 25 kg secondo la tabella di riferimento NIOSH
- **Dato che** il sesso del lavoratore è Femmina e l'età è "giovane" (15-18), **quando** il modulo si apre, **allora** CP è auto-compilato con 15 kg
- **Dato che** l'utente vuole sovrascrivere il CP di default, **quando** clicca "Modifica CP", **allora** il campo diventa editabile e un campo "Motivazione" a testo libero è obbligatorio per salvare

#### US-3.3
Come operatore, voglio il calcolo automatico di PLR e IR con classificazione Verde/Giallo/Rosso.

**Criteri di Accettazione:**

- **Dato che** tutti gli 8 parametri e CP sono inseriti, **quando** il calcolo viene eseguito, **allora** PLR = CP × A × B × C × D × E × F viene calcolato e IR = peso effettivo / PLR viene mostrato a 2 decimali
- **Dato che** IR è 0,50, **quando** il risultato viene visualizzato, **allora** la riga mostra una fascia verde "Accettabile" (IR ≤ 0,75)
- **Dato che** IR è 0,85, **quando** il risultato viene visualizzato, **allora** la riga mostra una fascia gialla "Da ridurre" (0,75 < IR ≤ 1,00)
- **Dato che** IR è 1,20, **quando** il risultato viene visualizzato, **allora** la riga mostra una fascia rossa "Non accettabile" (IR > 1,00) e una sezione misure obbligatorie appare sotto

### VDT (Videoterminali)

#### US-3.4
Come operatore, voglio inserire le ore VDT settimanali per lavoratore e che il sistema classifichi Esposto/Non Esposto (soglia: 20h/settimana).

**Criteri di Accettazione:**

- **Dato che** inserisco 22 ore/settimana per un lavoratore, **quando** il campo perde il focus, **allora** il lavoratore viene automaticamente classificato come "Esposto" con una spunta verde
- **Dato che** inserisco 18 ore/settimana per un lavoratore, **quando** il campo perde il focus, **allora** il lavoratore viene classificato come "Non esposto"
- **Dato che** ho un CSV con le ore VDT per lavoratore, **quando** uso "Importa da CSV", **allora** il sistema importa e classifica in massa tutte le righe in un'unica operazione

#### US-3.5
Come operatore, voglio la determinazione automatica della sorveglianza sanitaria obbligatoria in modo che i lavoratori che richiedono visite siano segnalati.

**Criteri di Accettazione:**

- **Dato che** un lavoratore è classificato "Esposto", **quando** il modulo VDT termina, **allora** il record del lavoratore viene contrassegnato "Sorveglianza sanitaria obbligatoria" con la prossima data di visita calcolata (5 anni per gli under-50, 2 anni per i 50+)
- **Dato che** un lavoratore ha una visita prevista in meno di 60 giorni, **quando** la dashboard si carica, **allora** il lavoratore appare nel widget "Visite in scadenza"
- **Dato che** la data della visita è passata, **quando** la dashboard si carica, **allora** il lavoratore appare nel widget "Visite scadute" evidenziato in rosso

### Stress Lavoro-Correlato

#### US-3.6
Come operatore, voglio una checklist digitale con ~50 indicatori INAIL (SI/NO) suddivisi in 3 aree (A, B, C) in modo da poter valutare lo stress lavoro-correlato.

**Criteri di Accettazione:**

- **Dato che** apro la valutazione Stress, **quando** la pagina si carica, **allora** tutti gli indicatori sono raggruppati nelle aree A (Eventi sentinella), B (Contenuto del lavoro), C (Contesto del lavoro) con toggle SI/NO
- **Dato che** sono a metà compilazione e chiudo la pagina, **quando** la riapro, **allora** le mie risposte precedenti vengono ripristinate dalla bozza salvata
- **Dato che** provo a finalizzare con indicatori senza risposta, **quando** clicco "Conferma valutazione", **allora** gli elementi senza risposta vengono evidenziati e l'azione viene bloccata

#### US-3.7
Come operatore, voglio il calcolo del punteggio in tempo reale e il livello di rischio automatico (Basso/Medio/Alto) in modo da vedere l'impatto di ogni risposta.

**Criteri di Accettazione:**

- **Dato che** cambio un indicatore da NO a SI, **quando** il toggle viene confermato, **allora** il punteggio dell'area e la fascia di rischio complessiva si aggiornano entro 200 ms
- **Dato che** il punteggio complessivo supera una soglia di fascia (es. da "Basso" a "Medio"), **quando** il ricalcolo si completa, **allora** l'intestazione della fascia anima il cambio di colore e un tooltip mostra la regola di soglia
- **Dato che** passo il mouse sul widget del punteggio, **quando** appare il tooltip, **allora** mostra i sub-totali per area e la formula complessiva

#### US-3.8
Come operatore, voglio misure correttive auto-generate in base al livello di rischio in modo da non doverle scrivere da zero.

**Criteri di Accettazione:**

- **Dato che** la valutazione si finalizza al livello di rischio "Medio", **quando** apro la sezione misure correttive, **allora** viene mostrato un elenco predefinito di misure appropriate per "Medio" con icone modifica e rimuovi
- **Dato che** modifico il testo suggerito, **quando** salvo, **allora** la misura viene contrassegnata come "Personalizzato" e salvata nella libreria per cliente
- **Dato che** voglio aggiungere una misura non presente in libreria, **quando** clicco "Aggiungi misura", **allora** appare una riga editabile vuota

### Gestanti

#### US-3.9
Come operatore, voglio il riferimento incrociato automatico tra i ruoli delle lavoratrici e i fattori di rischio del D.Lgs. 151/2001.

**Criteri di Accettazione:**

- **Dato che** la rilevazione contiene lavoratrici donne con mansioni dichiarate, **quando** il modulo Gestanti viene eseguito, **allora** ogni mansione viene confrontata con la lista dei rischi incompatibili del D.Lgs. 151/2001 e le corrispondenze vengono segnalate
- **Dato che** una lavoratrice ha una mansione senza rischi corrispondenti, **quando** il report viene generato, **allora** la lavoratrice viene mostrata con un indicatore verde "Nessun rischio identificato"
- **Dato che** vengono aggiunti nuovi rischi alla rilevazione dopo la generazione del report Gestanti, **quando** rigenerato, **allora** lavoratrici precedentemente libere possono comparire come nuove corrispondenze e sono chiaramente contrassegnate "Nuovo"

#### US-3.10
Come operatore, voglio l'auto-identificazione delle mansioni incompatibili e proposte di ricollocazione in modo da poter agire rapidamente.

**Criteri di Accettazione:**

- **Dato che** una mansione incompatibile è rilevata per una lavoratrice, **quando** il report viene generato, **allora** la riga mostra la mansione incompatibile e un ruolo alternativo suggerito dal sistema all'interno dello stesso cliente
- **Dato che** accetto un suggerimento di ricollocazione, **quando** l'azione si completa, **allora** viene registrata nell'Allegato Gestanti con un campo di motivazione
- **Dato che** rifiuto un suggerimento, **quando** l'azione si completa, **allora** sono obbligato a inserire una "Misura alternativa" a testo libero prima di salvare

### Rischio Incendio

#### US-3.11
Come operatore, voglio inserire i punteggi INF/SI/PI (1-3 ciascuno) per area omogenea in modo che la classificazione antincendio sia calcolata.

**Criteri di Accettazione:**

- **Dato che** sono sul modulo Rischio Incendio per un'area, **quando** inserisco INF=2, SI=2, PI=1, **allora** la somma 5 viene mostrata in tempo reale sotto gli input
- **Dato che** inserisco un valore al di fuori di 1-3, **quando** il campo perde il focus, **allora** il valore viene rifiutato con il tooltip "Valore consentito: 1-3"
- **Dato che** ho più aree omogenee, **quando** uso "Duplica area", **allora** i parametri dell'area corrente vengono copiati come punto di partenza

#### US-3.12
Come operatore, voglio il calcolo automatico del livello di rischio (Basso/Medio/Alto) e le misure di sicurezza antincendio richieste.

**Criteri di Accettazione:**

- **Dato che** la somma INF+SI+PI è 4, **quando** il calcolo viene eseguito, **allora** la fascia mostra "Basso" con il corrispondente elenco di misure
- **Dato che** la somma è 6, **quando** il calcolo viene eseguito, **allora** la fascia mostra "Medio"
- **Dato che** la somma è 8, **quando** il calcolo viene eseguito, **allora** la fascia mostra "Alto" e viene visualizzato un banner "Richiesta valutazione approfondita VVF"
- **Dato che** la fascia cambia dopo aver modificato i punteggi, **quando** il ricalcolo si completa, **allora** l'elenco delle misure si aggiorna di conseguenza

### Microclima

#### US-3.13
Come operatore, voglio inserire 6 parametri ambientali e ottenere il calcolo automatico di PMV/PPD per ogni ambiente.

**Criteri di Accettazione:**

- **Dato che** inserisco temperatura dell'aria, temperatura media radiante, velocità dell'aria, umidità relativa, tasso metabolico e isolamento dell'abbigliamento, **quando** tutti e 6 i campi sono validi, **allora** PMV e PPD vengono calcolati tramite pythermalcomfort e visualizzati con la fascia di comfort (Confortevole / Leggermente caldo / Caldo / ecc.)
- **Dato che** uno dei 6 parametri è al di fuori del suo intervallo fisico valido, **quando** il campo perde il focus, **allora** un errore di validazione spiega l'intervallo e il calcolo viene messo in pausa
- **Dato che** ho più ambienti, **quando** salvo, **allora** PMV/PPD viene calcolato e memorizzato in modo indipendente per ogni ambiente

#### US-3.14
Per ambienti con calore severo, voglio il calcolo PHS con il tempo massimo di esposizione (Dlim).

**Criteri di Accettazione:**

- **Dato che** un ambiente è contrassegnato come "Calore severo", **quando** apro il suo pannello microclima, **allora** il modulo passa in modalità PHS con i parametri aggiuntivi richiesti dalla ISO 7933
- **Dato che** inserisco tutti i parametri PHS, **quando** il calcolo viene eseguito, **allora** Dlim (minuti massimi di esposizione) viene mostrato insieme alle stime di temperatura corporea e perdita di acqua
- **Dato che** Dlim è inferiore a 30 minuti, **quando** il risultato viene visualizzato, **allora** un banner di avviso rosso "Esposizione critica - misure obbligatorie" viene mostrato sopra il risultato

### Rischio Biologico

#### US-3.15
Come operatore, voglio selezionare il tipo di settore (asilo, alimentare, dentale, ecc.) e ottenere agenti biologici e misure di prevenzione auto-popolati.

**Criteri di Accettazione:**

- **Dato che** apro il modulo Rischio Biologico, **quando** seleziono il settore "Asilo nido", **allora** il modulo si pre-compila con gli agenti biologici standard (virus respiratori, batteri intestinali, ecc.) e le misure di prevenzione per quel settore
- **Dato che** l'attività del mio cliente non è coperta da un settore predefinito, **quando** seleziono "Altro", **allora** il modulo fornisce elenchi vuoti editabili per inserire manualmente agenti e misure
- **Dato che** modifico le liste auto-popolate, **quando** salvo, **allora** le mie modifiche vengono memorizzate per il cliente senza modificare il template di settore globale

---

## Epica 4: Documenti Complementari

### PEE (Piano di Emergenza ed Evacuazione)

#### US-4.1
Come operatore, voglio che il PEE sia auto-generato dai dati del DVR (ambienti, squadre di emergenza, punti di raccolta).

**Criteri di Accettazione:**

- **Dato che** esiste un DVR per il cliente e i membri delle squadre di emergenza sono assegnati, **quando** clicco "Genera PEE", **allora** il sistema produce un .docx con ambienti, organico delle squadre, punti di raccolta e procedure di contatto pre-popolati
- **Dato che** non esiste ancora un DVR, **quando** provo a generare il PEE, **allora** l'azione viene bloccata con il messaggio "Genera prima il DVR Master"
- **Dato che** la planimetria è stata caricata con il DVR, **quando** il PEE viene generato, **allora** viene incorporata nel documento nella sezione designata; altrimenti viene mostrato un placeholder "Inserire planimetria"

#### US-4.2
Come operatore, voglio procedure di emergenza standard (A-E) per ogni tipo di evento pre-compilate.

**Criteri di Accettazione:**

- **Dato che** il PEE è in fase di generazione, **quando** la sezione delle procedure viene costruita, **allora** ogni tipo di evento (incendio, terremoto, allagamento, fuga di gas, evacuazione generale) viene pre-compilato con le procedure A-E dal template standard
- **Dato che** voglio personalizzare una procedura per questo cliente, **quando** la modifico in loco, **allora** la personalizzazione viene salvata per cliente e riutilizzata nella generazione successiva
- **Dato che** voglio annullare le personalizzazioni, **quando** clicco "Reset alle procedure standard", **allora** il testo personalizzato viene sostituito dal template globale dopo una finestra di conferma

### HACCP

#### US-4.3
Come operatore, voglio il manuale HACCP auto-generato in base al tipo di attività alimentare con analisi CCP personalizzata.

**Criteri di Accettazione:**

- **Dato che** seleziono il tipo di attività alimentare (es. "Ristorante con cucina"), **quando** genero il manuale HACCP, **allora** il sistema pre-carica i CCP rilevanti per quell'attività (cottura, conservazione, scongelamento)
- **Dato che** modifico una voce CCP (es. cambio un limite critico di temperatura), **quando** salvo, **allora** la modifica si riflette sia nella revisione a schermo che nel .docx generato
- **Dato che** il tipo di attività viene cambiato dopo che il manuale è stato generato, **quando** rigenerato, **allora** vengo avvisato che le personalizzazioni potrebbero essere perse e mi viene data l'opzione di unire

#### US-4.4
Come operatore, voglio tutte le 16 schede di autocontrollo (SA-01 a SA-16) generate come template compilabili.

**Criteri di Accettazione:**

- **Dato che** il manuale HACCP è generato per un cliente, **quando** clicco "Genera schede di autocontrollo", **allora** tutte le 16 schede (SA-01 a SA-16) vengono prodotte come template .docx compilabili pre-brandizzati con logo cliente e ragione sociale
- **Dato che** voglio solo un sottoinsieme di schede, **quando** apro la finestra di generazione, **allora** posso deselezionare schede specifiche prima della generazione
- **Dato che** le schede sono pronte, **quando** il job termina, **allora** vengono raggruppate in un unico download .zip per comodità

### DUVRI (Interferenze tra Imprese)

#### US-4.5
Come operatore, voglio che i dati dell'azienda committente siano auto-popolati dal DVR e i dati dell'appaltatore inseriti separatamente.

**Criteri di Accettazione:**

- **Dato che** esiste un DVR per l'azienda committente, **quando** creo un nuovo DUVRI, **allora** tutti i dati del committente (ragione sociale, sede, RSPP, datore di lavoro) vengono auto-popolati e in sola lettura
- **Dato che** voglio aggiungere un appaltatore, **quando** clicco "Aggiungi appaltatore", **allora** si apre una nuova sezione appaltatore con campi vuoti per i dati dell'appaltatore e l'oggetto del lavoro
- **Dato che** i dati del committente nel DVR cambiano, **quando** riapro il DUVRI, **allora** la sezione committente si aggiorna automaticamente e un banner segnala "Dati committente aggiornati"

#### US-4.6
Come operatore, voglio l'analisi delle interferenze per tipo di attrezzatura con misure di prevenzione suggerite.

**Criteri di Accettazione:**

- **Dato che** il committente e l'appaltatore hanno dichiarato le loro attrezzature, **quando** l'analisi delle interferenze viene eseguita, **allora** combinazioni di tipi di attrezzature sovrapposte producono misure di prevenzione suggerite da un motore di regole
- **Dato che** revisiono una misura suggerita, **quando** tocco Accetta o Rifiuta per riga, **allora** la mia decisione viene registrata e solo le misure accettate appaiono nel DUVRI finale
- **Dato che** non esistono attrezzature sovrapposte, **quando** l'analisi viene eseguita, **allora** la sezione mostra "Nessuna interferenza rilevata" e viene offerta un'opzione di inserimento manuale

### POS (Piano Operativo di Sicurezza)

#### US-4.7
Come operatore, voglio definire le fasi di costruzione con rischi specifici, calcoli NIOSH e livelli di rumore/vibrazione per fase.

**Criteri di Accettazione:**

- **Dato che** sto costruendo un POS, **quando** aggiungo una fase (es. "Scavo", "Getto calcestruzzo", "Montaggio impalcature"), **allora** posso allegare rischi specifici della fase, parametri NIOSH e misurazioni di rumore/vibrazione
- **Dato che** voglio le fasi in un ordine specifico, **quando** le trascino, **allora** l'ordine viene persistito e riflesso nel .docx generato
- **Dato che** una fase dipende dal completamento di un'altra fase, **quando** le collego, **allora** la dipendenza viene mostrata sia nella UI che nella panoramica simil-Gantt stampata

#### US-4.8
Come operatore, voglio una matrice dettagliata delle mansioni con DPI per ruolo per fase.

**Criteri di Accettazione:**

- **Dato che** una fase ha ruoli assegnati (carpentiere, manovale, gruista), **quando** la matrice viene generata, **allora** ogni cella ruolo × fase viene pre-popolata con suggerimenti di DPI dal motore di regole (casco, scarpe antinfortunistiche, imbragatura, ecc.)
- **Dato che** voglio sovrascrivere i DPI suggeriti per una cella specifica, **quando** la modifico inline, **allora** la sovrascrittura viene salvata solo per questo cliente e i suggerimenti globali rimangono invariati
- **Dato che** la matrice viene esportata in .docx, **quando** apro il file, **allora** la matrice appare come una tabella formattata con celle unite dove appropriato

---

## Epica 5: Trasversali

#### US-5.1
Come amministratore, voglio gestire più aziende clienti e i loro pacchetti di documenti da un'unica dashboard.

**Criteri di Accettazione:**

- **Dato che** sono autenticato come amministratore, **quando** apro la dashboard, **allora** vedo schede KPI (clienti attivi, documenti in lavorazione, scadenze imminenti) e una tabella clienti paginata ordinabile per ragione sociale, ATECO, ultimo aggiornamento, scadenza DVR
- **Dato che** scrivo nella casella di ricerca della dashboard, **quando** inserisco almeno 2 caratteri, **allora** la tabella si filtra in tempo reale confrontando ragione sociale, partita IVA e comune
- **Dato che** sono un utente non amministratore, **quando** provo ad accedere alle azioni "Aggiungi cliente" o "Elimina cliente", **allora** le azioni sono nascoste e l'API restituisce 403 se acceduta direttamente

#### US-5.2
Come qualsiasi utente, voglio che tutti i documenti siano generati dagli stessi dati condivisi (inserisci una volta, usa ovunque).

**Criteri di Accettazione:**

- **Dato che** aggiorno la mansione di una persona nella rilevazione, **quando** rigenerato qualsiasi documento a valle (DVR, PEE, DUVRI), **allora** la nuova mansione appare senza reinserimento manuale
- **Dato che** i dati della rilevazione vengono modificati mentre un job di generazione è in corso, **quando** il job si completa, **allora** ricevo un avviso che lo snapshot potrebbe essere obsoleto e posso scegliere di rigenerare
- **Dato che** voglio sapere quali documenti consumano attualmente uno specifico campo dati, **quando** apro il tooltip del campo, **allora** viene mostrata una lista dei documenti dipendenti

#### US-5.3
Come operatore, voglio che il contenuto generato dall'AI sia chiaramente segnalato in modo da sapere cosa revisionare con attenzione.

**Criteri di Accettazione:**

- **Dato che** una sezione di un documento è stata prodotta dall'AI, **quando** la visualizzo nell'editor, **allora** vengono mostrati uno sfondo leggermente colorato e un badge "AI" accanto alla sezione
- **Dato che** passo il mouse sul badge AI, **quando** appare il tooltip, **allora** recita "Generato da AI - revisiona prima della pubblicazione" e mostra un timestamp
- **Dato che** voglio filtrare l'editor per mostrare solo contenuto AI, **quando** attivo "Mostra solo contenuto AI", **allora** le sezioni non-AI vengono visivamente sfumate e le sezioni AI rimangono interattive

#### US-5.4
Come amministratore, voglio un hosting cloud sicuro con backup giornalieri (sostituendo la chiavetta USB).

**Criteri di Accettazione:**

- **Dato che** la piattaforma è in produzione, **quando** controllo il pannello di stato dei backup, **allora** vedo il timestamp dell'ultimo backup riuscito, la regione di destinazione e il periodo di conservazione
- **Dato che** il job di backup giornaliero fallisce, **quando** il fallimento viene rilevato, **allora** un alert viene inviato all'email dell'amministratore e il fallimento appare nel registro di audit entro 5 minuti
- **Dato che** ho bisogno di ripristinare i dati, **quando** apro la procedura guidata di ripristino, **allora** posso scegliere qualsiasi punto di backup all'interno del periodo di conservazione e il sistema esegue il ripristino prima su un ambiente di test isolato

---

*© 2026 Niuexa. Riservato — preparato per N2O SRL.*
