> **NIUEXA** | AI-Powered Business Automation
> *N2O DVR — Banca ESG-Social Add-on*
> Brainstorm Worksheet | 13 May 2026
> Confidential — Niuexa & N2O SRL

---

# Brainstorm Worksheet — sessione live con Luca

Strumento di lavoro per la sessione brainstorm. Ogni sezione ha **prompt di discussione**, **opzioni da scegliere**, e **decisioni da chiudere**.

---

## Doc da tenere aperte durante la sessione

| Doc | Quando aprirla |
|---|---|
| `BANCA_PROJECT_BRIEF.md` | All'inizio per ricapitolare vision e scope |
| `BANCA_USER_STORIES.md` | Quando si discute il flusso utente (Epic B2-B6) |
| `BANCA_DATA_MODEL.md` | Quando emerge "che dati raccogliamo?" |
| `BANCHE_DVR_NORMATIVA_2026.md` | Per validare gli indicatori MEF con Luca |
| `BANCA_IMPLEMENTATION_PLAN.md` | Verso la fine, per tempistiche e priorità |
| Drive `1pi8cj0jUWAYAS57Tl9rydxuMt6pHsOVf` | Materiali commerciali già pronti |

---

## 0 — Allineamento di apertura (5 min)

Domande da chiudere subito con Luca:

- [ ] **Confermi che l'opportunità banca è la priorità #1 per N2O nei prossimi 6 mesi?**
- [ ] **Quale banca specifica è il pilot?** Nome, taglia, quanti clienti corporate.
- [ ] **Chi è il referente lato banca?** Compliance officer / IT / commerciale.
- [ ] **Quando hai l'appuntamento?** Data target per il pilot firmato.

---

## 1 — Personas & utenti (10 min)

Le 4 personas ipotizzate (vedi `BANCA_PROJECT_BRIEF.md`):

| Persona | Cosa fa | Domanda per Luca |
|---|---|---|
| Banca Admin | Compliance officer banca, vede dashboard | "Chi sarà l'utente reale lato banca? Quanti utenti per banca?" |
| Corporate DdL | Datore di Lavoro PMI, compila autodichiarazione | "I DdL hanno PC o solo cellulare? Età media?" |
| Consulente N2O | Tu, vedi tutto da `dvr-sicurezza.it` | "Vuoi un'unica vista su tutti i clienti, banche incluse?" |
| Niuexa admin | Backend interno per onboarding banche | OK, gestito da Gregor |

**Quinto utente possibile da discutere**:
- [ ] **Gestore di filiale**? Vede solo i clienti del suo portafoglio?
- [ ] **Internal audit della banca**? Permessi read-only?

**Decisioni**:
- ☐ Aggiungiamo `gestore_filiale` come ruolo nell'MVP?
- ☐ Banca admin può creare sotto-ruoli arbitrari o lista chiusa?

---

## 2 — Customer journey: la PMI (15 min)

Lavagna ASCII da discutere:

```
1. INVITO
   ┌──────────────────────────────┐
   │  Email branded dalla banca   │
   │  "Banca X ti chiede di       │
   │  compilare l'autodichiara-   │
   │  zione di sicurezza"         │
   │  [link magico] [codice 6cif] │
   └──────────────────────────────┘
              ↓ click
2. BENVENUTO
   ┌──────────────────────────────┐
   │  Logo Banca + N2O footer     │
   │  "Ciao [Ragione Sociale],    │
   │  ti serviranno ~10 min"      │
   │  [ Inizia ]                  │
   │  ☐ Voglio anche consulenza   │
   │    completa DVR di N2O       │
   └──────────────────────────────┘
              ↓
3. WIZARD (4 step)
   Step 1 — Anagrafica (prefill da visura)
   Step 2 — Lavoratori (CCNL, contratti)
   Step 3 — Salute & Sicurezza (infortuni, decessi)
   Step 4 — Politiche & formazione
              ↓
4. REVISIONE & FIRMA
   ┌──────────────────────────────┐
   │  [Riepilogo 12 indicatori]   │
   │  Semaforo: 🟢 🟡 🔴          │
   │  [Canvas firma]              │
   │  ☐ Dichiaro veritiero        │
   │  [ Firma e invia ]           │
   └──────────────────────────────┘
              ↓
5. CONFERMA + UPSELL
   ┌──────────────────────────────┐
   │  ✓ Inviato. PDF in mail.     │
   │  ━━━━━━━━━━━━━━━━━━━━━━━━━  │
   │  Sapevi che...?              │
   │  [ Aggiorna DVR ]            │
   │  [ Allegato MMC ]            │
   │  [ Pacchetto 16 documenti ]  │
   └──────────────────────────────┘
```

**Domande per Luca**:
- [ ] Il wizard a 4 step è il giusto livello di granularità, o lo splittiamo in più step più corti?
- [ ] Il DdL firma sempre con canvas o gli proponiamo SPID/CIE quando disponibile?
- [ ] Cosa fa la PMI se NON ha il dato infortuni a portata di mano? Esce e torna? Salva draft? Chiama il consulente?
- [ ] L'upsell post-submission: cards immediate o mail a 7 giorni di distanza?

**Decisioni**:
- ☐ N° step wizard: 4 / 5 / 6
- ☐ Firma: canvas only / SPID / entrambi
- ☐ Draft salvabile: sì / no
- ☐ Upsell timing: immediato / mail differita / entrambi

---

## 3 — Customer journey: la Banca Admin (10 min)

```
DASHBOARD
┌─────────────────────────────────────────────┐
│  Banca X — Compliance ESG-Social            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  Tot Clienti  Invitati  Compilati  Scaduti  │
│   3.000       2.700      1.900      450     │
│                                             │
│  Coverage: ████████████░░░░  63%            │
│                                             │
│  Distribuzione semaforo                     │
│  🟢 1.420  🟡 380  🔴 100                   │
│                                             │
│  [Vedi clienti] [Esporta CSV] [Pacchetto    │
│   ispezione]                                │
└─────────────────────────────────────────────┘

CLIENTI LIST (con filtri)
┌─────────────────────────────────────────────┐
│ Filtri: [ATECO ▾] [Stato ▾] [Semaforo ▾]    │
│                                             │
│ Ragione Soc.    │ ATECO │ Stato │ Sem │ ... │
│ ──────────────────────────────────────────  │
│ Officina X SRL  │ 45.2  │ ✓ OK  │ 🟢  │ ... │
│ Ristorante Y    │ 56.1  │ Draft │ —   │ ... │
│ Edile Z         │ 41.2  │ Scad. │ 🔴  │ ... │
└─────────────────────────────────────────────┘
```

**Domande per Luca**:
- [ ] La banca vuole vedere il PDF firmato, o solo i 12 numeri estratti?
- [ ] Ha bisogno di un alert quando un cliente fa una dichiarazione "rossa" (decesso/alto tasso infortuni)?
- [ ] Vuole risk scoring dentro la nostra dashboard o esporta in CSV e usa il loro sistema?
- [ ] Quanti utenti banca per banca? 1 / 5 / decine?

**Decisioni**:
- ☐ Risk scoring nativo o solo data export?
- ☐ Alert email su semaforo rosso: sì / no
- ☐ Limite utenti banca per MVP: illimitato / max 10 / a pagamento

---

## 4 — Scope MVP: cosa entra, cosa esce (15 min)

Use la tabella per fare priorità a 3 livelli: **MUST** (no go senza), **SHOULD** (importante ma negoziabile), **CUT** (taglia per MVP).

| Feature | Default | Decision |
|---|---|---|
| Wizard autodichiarazione | MUST | ☐ |
| Magic-link auth | MUST | ☐ |
| PDF firmato (canvas) | MUST | ☐ |
| Auto-prefill da visura | MUST | ☐ |
| Dashboard banca con coverage | MUST | ☐ |
| Export CSV per SREP | MUST | ☐ |
| White-label theming | MUST | ☐ |
| Reminder automatici (+7,+14,+30) | SHOULD | ☐ |
| Audit log queryable | SHOULD | ☐ |
| Pacchetto ispezione BI | SHOULD | ☐ |
| Heatmap ATECO × semaforo | SHOULD | ☐ |
| Upsell DVR Pro con Stripe | SHOULD | ☐ |
| Revenue share ledger | SHOULD | ☐ |
| SPID/CIE firma | CUT | ☐ |
| Mobile app | CUT | ☐ |
| Multi-banca per PMI | CUT | ☐ |
| SSO bank IdP | CUT | ☐ |
| AI assistant in wizard | CUT | ☐ |
| Integrazione core banking | CUT | ☐ |
| E e G pillar ESG | CUT | ☐ |

**Discussione**: cosa promuovere/declassare? Ogni decisione cambia tempi.

---

## 5 — Modello commerciale verso la banca (15 min)

Lo schema di default (vedi `02 — PROPOSTA B2B2B` su Drive):

```
TIER 1 — Autodichiarazione (PMI gratis, banca paga)
   €3-5/cliente attivato/anno
   Setup €5-10k una tantum

TIER 2 — DVR Pro (PMI paga, banca prende rev share)
   PMI paga €500-2000
   Banca prende 20% rev share
```

**Domande per Luca**:
- [ ] **Il pilot lo facciamo gratis o a €X?** Suggerimento: gratis per la prima banca in cambio di case study + reference + commitment 3 anni.
- [ ] Il prezzo a cliente attivato (€3-5) è in linea o lo alziamo? La banca cosa si aspetta?
- [ ] Il 20% rev share è negoziabile? Limiti? Es. capped a €50k/anno?
- [ ] Fatturazione: mensile o trimestrale?
- [ ] Chi firma il contratto con la banca: N2O o Niuexa o entrambi?

**Decisioni**:
- ☐ Pilot price: €0 / €2k / €5k / €10k
- ☐ Tier 1 price: €3 / €4 / €5 / variabile per scaglione
- ☐ Rev share %: 15% / 20% / 25%
- ☐ Entità che firma il contratto: __________

---

## 6 — Privacy, GDPR, contratti (10 min)

**Domande per Luca**:
- [ ] La banca ha già un DPO (Data Protection Officer)? Possiamo parlarci direttamente?
- [ ] La banca avrà un'opinione sull'hosting? (Frankfurt EU o richiede on-prem italiano?)
- [ ] Il DPA template che genera Niuexa va bene, o la banca avrà il suo template?
- [ ] Chi è il titolare del trattamento sui dati PMI: banca o N2O o entrambi?

**Decisioni**:
- ☐ Hosting: Render EU / on-prem / on-prem possibile a Y€/anno aggiuntivi
- ☐ Titolarità trattamento: banca / N2O / contitolarità con DPA reciproco
- ☐ Cancellazione dati post-contratto: 30gg / 90gg / 12 mesi

---

## 7 — Pilot bank — info necessarie per partire (10 min)

Da estrarre da Luca prima di chiudere il brainstorm:

| Info | Risposta |
|---|---|
| Nome banca pilot | |
| Tipo (BCC / popolare / piccola SpA) | |
| N° totale clienti corporate | |
| Area geografica | |
| Referente compliance: nome + email | |
| Referente IT: nome + email | |
| AD/DG che firmerà mail di lancio | |
| Quando vuole partire | |
| Budget compliance ESG 2026 stimato | |
| Hanno già un questionario ESG? | |
| Loro tempi tipici di contrattualizzazione | |
| Banking provider (Cedacri / CSE / SIA / altro) | |

---

## 8 — Roadmap & tempistiche (10 min)

Dal `BANCA_IMPLEMENTATION_PLAN.md`: 8 fasi, 9.5 settimane di sviluppo solo.

```
B1 Foundation        ━━━━ 1.5 wk
B2 White-label       ━━ 1 wk
B3 Onboarding PMI    ━━ 1 wk
B4 Wizard + PDF      ━━━━ 2 wk
B5 Dashboard banca   ━━━ 1.5 wk
B6 Audit/compliance  ━ 0.5 wk
B7 Upsell + Stripe   ━━ 1 wk
B8 Pilot rollout     ━━ 1 wk
                     ━━━━━━━━━━━━━ 9.5 wk
```

**Domande per Luca**:
- [ ] Si parte oggi, demo a Luca pronta entro 4 settimane (fine B2 + parziale B3)?
- [ ] La banca quando vuole essere live? Realistic 2.5 mesi dal "go".
- [ ] Cosa fa Luca in parallelo nei prossimi 60 giorni? Quanti clienti porta a bordo entro il go-live?

**Decisioni**:
- ☐ Data inizio sviluppo
- ☐ Data demo interna
- ☐ Data target pilot live
- ☐ Data target prima fattura banca

---

## 9 — Cose che IO ho bisogno di sapere prima di scrivere codice (5 min)

Faccio io a Luca:

- [ ] Posso accedere ai questionari ESG che la banca pilot oggi manda? (anche solo 1 esempio)
- [ ] Posso vedere come oggi N2O fattura un DVR (per il modello prezzo DVR Pro)?
- [ ] Posso parlare con un cliente PMI "tipo" per validare il wizard? (User research, 30 min)
- [ ] Hai mail/template della banca per le comunicazioni che già usa? Vorremmo allineare il tono.
- [ ] Vuoi che mostriamo l'AI agent come differenziatore commerciale (lato banca) o lo teniamo backend?

---

## 10 — Action items in uscita (5 min)

| Cosa | Chi | Quando |
|---|---|---|
| Riempire questa worksheet con le decisioni | Luca + Gregor | Fine sessione |
| Mandare contatti banca pilot | Luca | +2 giorni |
| Strutturare termsheet pilot bancaria | Gregor | +3 giorni |
| Discutere struttura interna Niuexa (vedi plan strategico) | Gregor + socio | +5 giorni |
| Iniziare Phase B1 (data model) | Gregor | dopo termsheet |
| Demo interna a Luca | Gregor | +4 settimane |
| Demo a banca pilot | Luca + Gregor | +6 settimane |
| Pilot live | tutti | +10 settimane |

---

## Cose da NON dimenticare durante il brainstorm

- Far parlare Luca, non rispondere subito. Lui ha intuizione di dominio.
- Ogni "no" del cliente è uno sconto sui tempi. Non difendere feature.
- Se Luca propone qualcosa di tecnico, dire "interessante, vediamo" e segnare. Non discutere fattibilità in tempo reale.
- Tenere la worksheet aperta sul portatile e completare in tempo reale — chiusura sessione = decisioni catturate.
- Foto della whiteboard se si usa.

---

## Cheat sheet — frasi chiave da usare con Luca

- **Per spingere il pilot**: *"Per partire bene serve una banca specifica. Chi proviamo a contattare per primo?"*
- **Per chiudere lo scope**: *"Tutto interessante. Per essere live in 2.5 mesi, cosa togliamo da qui?"*
- **Per validare l'UX**: *"Se un DdL aprisse questo a casa la sera, dopo 8 ore di lavoro, lo capirebbe?"*
- **Per chiudere la sessione**: *"OK, riassumo. Le 5 decisioni che abbiamo preso oggi sono: 1..., 2..., 3..., 4..., 5... Domani ti mando il follow-up con le 3 cose che devi fare tu."*
