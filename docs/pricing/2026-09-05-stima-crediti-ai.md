# Stima dei crediti AI per i tasti AI della piattaforma

**Per:** Luca Marchetti, Simone (N2O) · **Da:** Niuexa · **Data:** 5 settembre 2026
**Richiesta:** call del 4 settembre — "stimare i crediti necessari per i nuovi tasti IA".
**Dati:** codice in produzione al 4 settembre 2026 e consumo reale del tenant N2O letto dall'endpoint dei crediti lo stesso giorno.

## In breve

- Un credito vale un suggerimento testuale. Le foto costano 4 crediti, una scheda di sicurezza (SDS) 8, una visura camerale 15. Generare i documenti non consuma crediti.
- Un'azienda **tipica** (6 ambienti, 15 persone, 8 SDS) costa **162 crediti** usando ogni tasto AI oggi in produzione una volta per unità; i tre tasti nuovi (scheda ambiente da foto, gestanti, protocollo sanitario) aggiungono **36 crediti** (+22 %). Piccola: 71 + 18. Grande: 382 + 84.
- N2O ha usato **2.779 crediti su 9.000** in cinque mesi (31 %). Il 77 % è andato in SDS. Al ritmo attuale (~540 crediti/mese) la soglia dei 9.000 si raggiunge intorno ad **agosto 2027**; con i tasti nuovi, intorno a **giugno 2027**.
- Attenzione: nel codice i 9.000 crediti coprono **l'intero periodo del piano Founding (1 apr 2026 → 1 apr 2029)**, non un anno. Va deciso se azzerare il contatore ogni anno (vedi §3).

## 1. I tasti AI e il loro costo

| Tasto (dove si trova) | Cosa fa | Unità | Crediti | Un nuovo click **non** costa quando… | Stato |
|---|---|---|---|---|---|
| **Compila con AI** (Nuova azienda, da P.IVA) | Visura camerale + ricerca web → dati anagrafici | per P.IVA | **15** | stessa P.IVA nello stesso periodo di abbonamento | in produzione |
| **Genera con AI / Rigenera con AI** (Panoramica, descrizione attività) | Testo della Parte I del DVR | per generazione | 1 | ripetizione dopo un errore; una rigenerazione voluta dopo una versione salvata costa 1 | in produzione |
| **Genera con AI / Rigenera** (Sopralluogo → Attrezzature) | Propone le attrezzature tipiche dell'ambiente | per ambiente | 1 | stesso ambiente con le stesse attrezzature già inserite; dopo aver aggiunto attrezzature costa di nuovo | in produzione |
| **Estrai dalle foto** (Sopralluogo → Attrezzature) | Riconosce le attrezzature nelle foto dell'ambiente (tutte le foto in una chiamata) | per ambiente | **4** | stesso insieme di foto; una foto in più costa di nuovo | in produzione |
| **Compila da foto** (Scheda ambiente: descrizione, materiali, sorgenti di innesco — usata da Incendio e PEE) | Propone la scheda dalle foto già caricate | per ambiente | **4** | stesso insieme di foto | in produzione dal 4 set |
| **Suggerisci con AI** (Rischi per ambiente) | Le 11 categorie di rischio con applicabilità e P/D iniziali | per ambiente | 1 | sempre, dopo la prima volta sullo stesso ambiente | in produzione |
| **Flagga con AI** (Sopralluogo → DPI e rischi per persona) | DPI e rischi specifici della persona | per persona | 1 | sempre, dopo la prima volta sulla stessa persona | in produzione |
| **Genera con AI** (Tab Miglioramento) | Misure di miglioramento per ogni pericolo con indice I ≥ 5 (modesto o peggio) non ancora coperto | per pericolo | 1 × pericoli | i pericoli già coperti da una misura sono saltati (0); un pericolo fallito viene rimborsato | in produzione (dedupe dal 4 set) |
| **Suggerisci con AI** (Stress lavoro-correlato) | Misure correttive dalle risposte INAIL | per questionario | 1 | stesse risposte; cambiando una risposta costa 1 | in produzione |
| **Genera con AI** (POS → fase) | Descrizione, rischi e DPI di una fase di cantiere | per fase | 1 | stesso nome di fase | in produzione |
| **Compila con AI** (POS → matrice DPI) | Riempie le celle vuote ruolo × fase | per matrice | 1 | stessi ruoli e fasi | in produzione |
| **Genera con AI** (HACCP → CCP) | Dettagli del punto critico dal nome | per CCP | 1 | stesso CCP, settore e attività | in produzione |
| **Genera con AI** (DUVRI → interferenze) | Rischi interferenziali dalle attrezzature dell'appaltatore | per richiesta | 1 | stesse attrezzature, oggetto e interferenze già inserite | in produzione |
| **Carica schede di sicurezza (SDS)** (Sopralluogo → Sostanze) | Estrae la scheda dal PDF | per file PDF | **8** | mai: ogni file caricato è addebitato al caricamento, anche se l'estrazione poi fallisce; ricaricare lo stesso PDF costa di nuovo | in produzione |
| **Suggerisci con AI** (Gestanti, per mansione) | Rischi e misure per la mansione | per mansione | 1 | stessa mansione (ipotesi) | **in sviluppo** |
| **Compila con AI** (Protocollo sanitario, per mansione) | Accertamenti e periodicità per la mansione | per mansione | 1 | stessa mansione (ipotesi) | **in sviluppo** |

Costano **0 crediti**: il caricamento del PDF della visura camerale (estrazione locale, senza AI), i pericoli suggeriti dalla libreria (filtro a regole), la generazione e il download dei documenti. Esiste anche un suggeritore di misure per singolo rischio (1 credito), raggiungibile solo via API: non ha un tasto nell'interfaccia.

## 2. Consumo tipico per azienda

Tre scenari, ogni tasto usato **una volta per unità** (ambiente, persona, mansione, file). Mansioni distinte: 3 / 6 / 12. Pericoli con I ≥ 5 per ambiente: 5 (ipotesi, vedi §5). POS, HACCP e DUVRI sono settoriali e restano fuori dal totale base.

| Tasto | Crediti/unità | Piccola (1 sede, 3 amb., 5 pers., 2 SDS) | Tipica (6 amb., 15 pers., 8 SDS) | Grande (15 amb., 40 pers., 20 SDS) |
|---|---|---|---|---|
| Compila con AI (visura) | 15 × 1 | 15 | 15 | 15 |
| Descrizione attività | 1 × 1 | 1 | 1 | 1 |
| Attrezzature: Genera con AI | 1 × ambienti | 3 | 6 | 15 |
| Attrezzature: Estrai dalle foto | 4 × ambienti | 12 | 24 | 60 |
| Rischi: Suggerisci con AI | 1 × ambienti | 3 | 6 | 15 |
| DPI: Flagga con AI | 1 × persone | 5 | 15 | 40 |
| Misure di miglioramento | 1 × (5 × ambienti) | 15 | 30 | 75 |
| Stress: Suggerisci con AI | 1 × 1 | 1 | 1 | 1 |
| SDS | 8 × file | 16 | 64 | 160 |
| **Totale tasti in produzione** | | **71** | **162** | **382** |
| Scheda ambiente: Compila da foto *(nuovo)* | 4 × ambienti | 12 | 24 | 60 |
| Gestanti: Suggerisci con AI *(nuovo)* | 1 × mansioni | 3 | 6 | 12 |
| Protocollo sanitario: Compila con AI *(nuovo)* | 1 × mansioni | 3 | 6 | 12 |
| **Costo aggiuntivo dei tasti nuovi** | | **18 (+25 %)** | **36 (+22 %)** | **84 (+22 %)** |
| **Totale con i tasti nuovi** | | **89** | **198** | **466** |

Moduli settoriali, da aggiungere quando servono: POS ≈ 1 credito per fase + 1 per la matrice DPI (8 fasi → 9 crediti); HACCP ≈ 1 per CCP (6 CCP → 6); DUVRI 1 per appalto.

Due letture utili:
- Lo scenario tipico (162) è in linea con i **≈ 136 crediti per pratica completa** su cui erano stati dimensionati i piani (`docs/pricing/00-FONDAMENTA.md` §6); la differenza è quasi tutta nelle foto delle attrezzature (24), aggiunte dopo quel dimensionamento.
- Dei tasti nuovi, quasi tutto il costo è la scheda ambiente da foto (4 per ambiente). Gestanti e protocollo sanitario pesano 1 credito per mansione: da 6 a 24 crediti per azienda, meno del 5 % del totale.

## 3. Cosa dicono i dati reali di N2O

Periodo 1 aprile → 4 settembre 2026 (5,1 mesi). **2.779 crediti usati su 9.000** (31 %), 6.221 residui. 12 aziende attive su 60.

| Tipo | Azioni | Crediti | Quota |
|---|---|---|---|
| SDS (8) | 268 | 2.144 | 77 % |
| Suggerimenti testuali (1) | 314 | 314 | 11 % |
| Visura (15) | 15 | 225 | 8 % |
| Foto (4) | 24 | 96 | 3 % |

- **Per azienda attiva:** 232 crediti, di cui 22 SDS (179 crediti), 26 suggerimenti, 2 foto, 1,25 visure. Il costo per azienda è più alto dello scenario tipico (162) per una sola ragione: N2O carica quasi tre volte più SDS per azienda di quanto assunto (22 contro 8). Tutto il resto è sotto lo scenario.
- **Ritmo:** 2.779 / 5,1 mesi ≈ **540 crediti/mese**, con 2,3 aziende nuove al mese.
- **Proiezione al ritmo attuale:** ~6.500 crediti al 1 aprile 2027 (12 mesi dall'inizio del periodo, 72 % dei 9.000). La soglia dei 9.000 si raggiunge dopo 16,6 mesi, cioè intorno ad **agosto 2027**.
- **Con i tasti nuovi** su ogni azienda nuova (+36 crediti × 2,3 aziende/mese ≈ +85/mese → ~625/mese): la soglia si raggiunge dopo 14,4 mesi, intorno a **giugno 2027**.

**Il periodo è di tre anni, non di un anno.** Il campo del piano si chiama `ai_credits_year` (9.000), ma il contatore dei crediti è uno per periodo di abbonamento e la sottoscrizione Founding ha un unico periodo 1 apr 2026 → 1 apr 2029, che nessun pagamento PayPal fa avanzare (`backend/app/billing/metering.py`, `entitlements.py`, migrazione `e7f8a9b0c1d2`). Quindi, così com'è, **i 9.000 crediti devono bastare fino ad aprile 2029** e il tracker non si azzera il 1 aprile 2027. Al ritmo attuale non basterebbero: servirebbero ~19.500 crediti in 36 mesi. Va deciso tra: (a) azzerare il contatore a ogni anniversario, con un intervento tecnico di Niuexa; (b) accreditare i 9.000 di ogni anno come ricarica manuale; (c) tenere il tetto triennale e coprire l'eccedenza con i pacchetti. La decisione non è urgente — al ritmo attuale il tracker resta sotto il 75 % fino a primavera 2027 — ma va presa prima.

## 4. Raccomandazioni

1. **Le SDS sono il 77 % della spesa** e sono l'unica azione senza rimborso: ogni PDF è addebitato al caricamento, anche se l'estrazione fallisce, e ricaricare lo stesso file costa altri 8 crediti. Conviene caricare solo le schede delle sostanze effettivamente in uso e, se un'estrazione fallisce, segnalarlo invece di ricaricare. Se N2O lo ritiene giusto, il rimborso automatico dell'estrazione fallita è una modifica piccola.
2. **La visura (15) è il click singolo più caro**, ma pesa l'8 % perché si usa una volta per azienda. Nessuna azione necessaria; ricordare che oggi la ricerca web a corredo è degradata (credito Serper esaurito) e che il caricamento del PDF della visura è gratuito.
3. **I tasti nuovi non cambiano l'ordine di grandezza:** +22 % per azienda, quasi tutto dalla scheda ambiente da foto. Gestanti e protocollo sanitario sono trascurabili.
4. **Pacchetti e ricarica automatica.** La piattaforma **non ha una ricarica automatica**: i pacchetti si comprano a mano dalla pagina Abbonamento (500 crediti = €79, 2.000 = €249, 10.000 = €990, IVA esclusa; €0,158 / €0,125 / €0,099 per credito — `backend/app/billing/credit_packs.py`) e si sommano al periodo in corso, che per N2O scade nel 2029: nessun rischio di perderli. La pagina avvisa al 75 % (6.750 crediti). **Oggi non serve comprare nulla**; se e quando serve, il taglio sensato è il 2.000 (≈ 4 mesi di consumo attuale). Meglio ancora, chiudere prima la decisione del §3.
5. **Ripetere un click non costa.** Ogni tasto è legato ai suoi dati di ingresso: un secondo click con gli stessi dati non viene addebitato, e una chiamata fallita (errore del fornitore AI) viene rimborsata — l'unica eccezione è il caricamento SDS. Gli operatori possono cliccare senza timore; costa solo il lavoro nuovo.

## 5. Ipotesi

- Pesi dei crediti da `backend/app/billing/constants.py` (reasoning 1, vision 4, sds 8, visura 15); piani e pacchetti da `plan_catalogue.py` e `credit_packs.py`; regole di addebito lette da ogni endpoint in `backend/app/api/v1/` al 4 settembre 2026.
- Consumo reale N2O dall'endpoint dei crediti del tenant, 4 settembre 2026; la proiezione assume un ritmo costante e la stessa composizione di consumo. Le aziende reali variano; i mesi estivi possono aver abbassato il ritmo.
- Scenari: ogni tasto usato una volta per unità, senza rigenerazioni. Mansioni distinte 3 / 6 / 12; pericoli con I ≥ 5 per ambiente: 5 (la libreria conta oltre 60 pericoli; il valore reale è nel campo `pericoli_considered` della risposta del tasto Misure ed è facile da verificare sulle aziende esistenti). POS, HACCP e DUVRI esclusi dal totale base.
- Tasti gestanti e protocollo sanitario: non ancora nel codice; assunto 1 credito per mansione e ripetizione gratuita sulla stessa mansione, da confermare a fine sviluppo.
- Nessun prezzo in euro oltre a quelli scritti nel catalogo pacchetti; il piano Founding è a €0.
