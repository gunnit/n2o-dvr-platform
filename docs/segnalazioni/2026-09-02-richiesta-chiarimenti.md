# Richiesta di chiarimenti — segnalazioni aperte al 2026-09-02

Bozza di email per Luca (N2O). Testo in italiano, pronto da copiare.
Contesto tecnico e verifiche: `docs/segnalazioni/2026-09-02-triage.md`.

---

**Oggetto:** Segnalazioni di agosto — 21 già risolte, 13 da chiarire

Ciao Luca,

ho controllato tutte le segnalazioni inserite nella piattaforma e i log di
produzione. Ti scrivo prima la buona notizia, poi le domande.

## 1. Le segnalazioni di agosto non erano ferme: 21 su 34 sono già in produzione

Le 20 segnalazioni del 3–5 agosto (MMC, VDT, valutazione rischi, PEE, POS,
DUVRI, gestanti, microclima) sono state sviluppate il 14 agosto e sono online
da allora. Ho verificato una per una direttamente sull'ambiente di produzione:
i campi cantiere del POS, la tipologia di allarme nel PEE, il numero unico 112,
lo stress da freddo nel microclima, il tasto AI delle interferenze DUVRI e la
valutazione gestanti per mansione **ci sono e funzionano**.

Si è aggiunta poi la segnalazione del 20 agosto sui numeri di emergenza del PEE
("mi fa uscire dal riquadro ogni lettera che scrivi"): risolta il 25 agosto.

**Perché allora risultano ancora "nuove"?** Per due motivi, e nessuno dei due
ha a che fare con il lavoro svolto:

- Lo stato di una segnalazione si cambia solo a mano dal pannello di
  amministrazione. Pubblicare la correzione non la sposta automaticamente su
  "risolto". Le abbiamo sviluppate e non le abbiamo marcate.
- Il collegamento automatico che copia ogni segnalazione sulla nostra bacheca
  interna di lavorazione **si è rotto il 10 giugno** (una credenziale scaduta).
  Da quel giorno le segnalazioni continuavano ad arrivare e a salvarsi
  correttamente, ma non comparivano più sulla bacheca da cui il team lavora.
  Tutte e 38 quelle di agosto sono in questa condizione.

Ho già sistemato il secondo punto: da ora un guasto di questo tipo genera un
allarme visibile invece di restare silenzioso, e ho preparato lo strumento per
recuperare le 89 segnalazioni rimaste indietro. **Nessuna segnalazione è andata
persa** — erano tutte nel database, era solo la bacheca a non vederle.

Ti chiedo una conferma su due punti prima di marcarle come risolte:

1. **"Aree valutazione dei rischi completamente da rivedere" (3 agosto).**
   L'abbiamo interpretata come l'ombrello delle tre segnalazioni successive
   (gestanti, lavoratori stranieri, lavoratori minori). Se intendevi altro,
   dimmi cosa e la riapriamo.
2. **Diciture di default del POS.** Nella segnalazione scrivevi "se vuoi te le
   fornisco". Le abbiamo ricavate dal vostro documento originale: puoi dare
   un'occhiata a un POS generato e confermarci che sono quelle giuste?

## 2. Due cose che dipendono da rinnovi, non da sviluppo

- **Compilazione automatica dell'indirizzo imprecisa (19 agosto).** La causa non
  è il codice: il servizio esterno che recupera i dati aziendali **ha esaurito i
  crediti**, e una seconda fonte non è mai stata attivata. La piattaforma sta
  quindi lavorando con una sola fonte e "tira a indovinare" più di quanto
  dovrebbe. Serve rinnovare l'abbonamento a quel servizio: fatto quello, la
  precisione torna quella prevista. Confermi che procediamo?
- **"Mi dice che ho finito i crediti ma in realtà li ho" (31 luglio).** Oggi non
  si riproduce: il tuo account ha **6.239 crediti disponibili su 9.000**. La
  segnalazione è di quattro giorni dopo l'attivazione dei pagamenti, quindi molto
  probabilmente era un effetto di quel passaggio, già corretto. Ho comunque reso
  il messaggio più preciso, così se ricapita si capisce subito la causa.
  **Ti è più successo dopo il 31 luglio?** Se sì, dimmi giorno, ora e su quale
  azienda: con quello lo ritrovo nei log.

## 3. Le 11 segnalazioni su cui ho bisogno di una tua decisione

Sono tutte fattibili. Il punto non è "se", è "come": in ognuna c'è una scelta
che tocca a voi, perché riguarda il documento firmato e la vostra prassi.

**Contenuti che servono da voi**

1. **Lavorazioni di default nel POS (29 maggio).** Chiedevi l'elenco delle
   lavorazioni di un operaio edile in cantiere. Preferisco partire dal *vostro*
   elenco piuttosto che generarne uno: quello che mettiamo qui finisce in un
   documento che firmate. Ce lo mandi?
2. **Rischio Biologico — 5 nuove categorie (25 agosto):** veterinari, operatori
   sanitari, centri estetici, agricoltori, gestione ambientale (rifiuti e
   depurazione). Oggi il modulo copre solo alimentare, asilo e dentisti. Ogni
   nuova categoria richiede il suo elenco di agenti biologici, misure e
   protocollo sanitario. **Qui c'è un problema pratico:** i vostri modelli
   originali del Rischio Biologico sono gli unici che non riusciamo a leggere
   automaticamente (due sono `.doc` vecchio formato, uno è un PDF). Ci mandi i
   modelli in Word per queste categorie, o preferisci che li ricostruiamo noi
   dalla normativa e ve li facciamo validare?
3. **Protocollo sanitario aziendale compilato con AI + elenco malattie
   (25 agosto).** Su cosa deve basarsi l'AI: mansioni, rischi valutati, o
   entrambi? E l'elenco delle malattie professionali lo prendiamo dalle tabelle
   INAIL o avete un vostro riferimento?
4. **Guida aggiornata con nuovi screenshot (28 aprile).** Gli screenshot li
   rifacciamo noi, ma dimmi se la struttura attuale della guida va bene o vuoi
   riorganizzarla.

**Scelte di prodotto**

5. **Misure di miglioramento che si ripetono (21 agosto).** Ho trovato la causa:
   il sistema genera le misure *per ogni pericolo*, quindi una misura generica
   (es. "formazione specifica dei lavoratori") ricompare su tutti i pericoli che
   la richiedono. Due strade: **(a)** una riga per misura, con l'elenco dei
   pericoli che copre — elenco più corto e leggibile, ma si perde il dettaglio
   pericolo-per-pericolo nel DVR; **(b)** si tengono separate ma si raggruppano
   visivamente. Quale preferisci per il documento firmato?
6. **Rischio incendio e PEE — schede per ambiente (25 agosto).** I tre campi che
   hai indicato (descrizione/metratura/materiali, numero massimo di persone,
   possibili sorgenti di innesco) sono chiari. La domanda è sul riconoscimento
   automatico dalle foto: **quanto vi fidate?** Proposta: l'AI propone e
   l'operatore conferma sempre, mai compilazione silenziosa — coerente con il
   principio "revisione, non inserimento". Ti va?
7. **Catalogo rischi: mostrare tutti i rischi della categoria anche con il
   suggerimento AI (19 agosto).** Vuoi che i rischi non suggeriti restino
   visibili in fondo alla lista, oppure dietro un "mostra tutti"? La prima
   allunga parecchio la pagina.
8. **Documenti allegati voce per voce invece che per categoria (19 agosto).**
   Confermi che serve per tutte le categorie o solo per alcune? E gli allegati
   già collegati a livello di categoria li manteniamo o li ridistribuiamo?
9. **Tasto AI per i rischi delle lavoratrici gestanti (25 agosto).** Deve
   arrivare a dire "mansione non compatibile"? È una conclusione che pesa: la
   proponiamo come suggerimento da confermare, giusto?

**Domanda legale, non tecnica**

10. **Foto della carta d'identità per estrarre i dati del lavoratore
    (28 aprile).** Tecnicamente si fa, e funzionerebbe anche con il permesso di
    soggiorno. Il problema è GDPR, e l'avevi già visto tu nella segnalazione: un
    documento d'identità è un dato personale, e per i lavoratori stranieri il
    permesso di soggiorno rientra tra i dati particolari. Le domande a cui serve
    risposta prima di scrivere una riga di codice:
    - Il consenso lo raccoglie N2O o il datore di lavoro verso il dipendente?
    - Conserviamo l'immagine del documento o solo i dati estratti, scartando
      subito la foto? (La seconda è nettamente più difendibile.)
    - Chi è il titolare del trattamento: voi o l'azienda cliente?

    **Ti conviene farla verificare dal vostro consulente privacy prima che
    stimiamo lo sviluppo.** È l'unica segnalazione su cui non mi muovo senza una
    risposta scritta.

## In sintesi

Sono 34 segnalazioni aperte in tutto:

- **21** sono già risolte e online — le marco come tali appena mi confermi i due
  punti della sezione 1.
- **2** dipendono da un rinnovo, non da sviluppo (compilazione automatica e
  messaggio sui crediti).
- **11** aspettano una tua decisione: 4 di contenuto, 6 di prodotto, 1 legale.

Se preferisci, sentiamoci mezz'ora: le domande della sezione 3 si chiudono più
in fretta a voce che via email.

Un saluto,
Gregor
