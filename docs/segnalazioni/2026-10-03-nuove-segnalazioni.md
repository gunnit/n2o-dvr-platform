# Segnalazioni — batch of 2026-10-02

Source: the *Nuovo* filter of `/admin/feedback` on production, copied by Gregor
on 2026-10-03. 20 rows are `nuovo`: 17 filed on 2026-10-02 (all on azienda
`2d1eb57d-e7da-4787-a106-9a0c0b6c2942`) and 3 older ones already on the
2026-09-04 to-do, still blocked on N2O.

## New — 2026-10-02

| # | Tipo | Pagina | Segnalazione |
|---|---|---|---|
| 1 | Osservazione | /documents | RIVEDERE LA GENERAZIONE OUTPUT DEL DOCUMENTO DUVRI |
| 2 | Osservazione | /assessments/haccp | DA RIVEDERE PASSAGGI HACCP |
| 3 | Osservazione | /assessments/protocollo-sanitario | oscurare tutta la valutazione, per ora non necessario |
| 4 | Osservazione | /assessments/gestanti | non data presunta parto ma data inizio periodo di maternità e data fine maternità |
| 5 | Bug | /assessments/gestanti | non mi fa scegliere la lavoratrice da valutare |
| 6 | Osservazione | /assessments/gestanti | se una mansione inserita è ricoperta da un maschio, la valutazione non deve essere presa in considerazione. prendere in considerazione solo le mansioni dove è stata assegnata una femmina. |
| 7 | Osservazione | /assessments/biologico | integrare il rischio con: dpi utilizzati; malattie contraibili con sintomi e cura |
| 8 | Osservazione | /assessments/stress | INSERIRE IL POPUP DOVE C'E' SCRITTO: ESEGUIRE LA VALUTAZIONE PER OGNI MANSIONE PRESENTE |
| 9 | Osservazione | /assessments/stress | SOSTITUIRE LE MANSIONI DI DEFAULT CON LE MANSIONI PRESENTI NEL SOPRALLUOGO |
| 10 | Idea | /assessments/vdt | DOVE C'È LA VOCE POSTAZIONE, MENU A TENDINA CON GLI AMBIENTI |
| 11 | Bug | /assessments/mmc | NON MI SALVA LE VALUTAZIONI PRECEDENTI |
| 12 | Osservazione | /aziende/{id}?tab=miglioramento | CREARE UN POPUP CON LA DICITURA CHE: TI AIUTO IO! NON SPAVENTARTI SE VEDI TUTTI QUESTI PIANI DI MIGLIORAMENTO. DEVI SEMPLICEMENTE SCEGLIERE QUELLI CHE CREDI SIANO INERENTI ALLA TUA ATTIVITA'. |
| 13 | Osservazione | /guida | AGGIORNARE LA GUIDA IN BASE AI RECENTI AGGIORNAMENTI E INSERIRE DELLE LINEE GUIDA PER OGNI MACROSETTORE: RISTORAZIONE, EDILIZIA, E ALTRI |
| 14 | Idea | /assessments/risk | CREARE UNA VALUTAZIONE DEL RISCHIO PRENDENDO SPUNTO DALL'IMMAGINE CARICATA DELL'AMBIENTE |
| 15 | Osservazione | /assessments/risk | SEGNARE COME POPUP ALL'INIZIO DELLA VALUTAZIONE DI OGNI AMBIENTE: *Tutti i rischi individuati all'interno della piattaforma devono essere preventivamente ed espressamente oggetto di valutazione manuale da parte dell'operatore umano preposto. La valutazione generata dai sistemi di intelligenza artificiale ha carattere meramente indicativo e di supporto e non sostituisce in alcun caso l'analisi, il giudizio e la decisione finale dell'operatore.* |
| 16 | Osservazione | /aziende/new | TOGLIERE IL TASTO AGGIUNGI SEDE E LASCIARE I CAMPI PER SEDE LEGALE E SEDE OPERATIVA |
| 17 | Osservazione | /aziende | SBLOCCARE LA P.IVA PER AGGIUNGERE PIU' SEDI OPERATIVE |

## Still `nuovo` from earlier (blocked on N2O, see `2026-09-04-todo.md`)

- 2026-08-25 — Rischio biologico: five new categories (needs the Word sources).
- 2026-08-19 — Compilazione automatica indirizzo/CAP imprecisa (Serper credits).
- 2026-08-04 — POS: new fields and default diciture (needs N2O's original).

## Outcome (branch `claude/ecstatic-davinci-3ftmqi`)

| # | Done | Commit | Notes |
|---|---|---|---|
| 1 DUVRI | ✅ | `fix(duvri)` | Template forms filled from data (anagrafica, attività, lavoratori, emergenze, dates, 112, fire level, dotted blanks). The donor body text itself is unchanged: ask N2O which sections they still find wrong. |
| 2 HACCP | ✅ partial | `fix(haccp)` | Flow diagram, CCPs in process order with all fields, prerequisites apart, SOP index aligned, donor specifics gone. "Passaggi" is ambiguous: confirm with N2O whether they meant the manual or the UI steps. |
| 3 Protocollo sanitario | ✅ | `feat(protocollo-sanitario)` | Hidden behind one flag per side; data and API kept. |
| 4 Maternità dates | ✅ | `fix(gestanti)` | Migration `e1f2a3b4c5d7` prefills from the old date. |
| 5 Lavoratrice selector | ✅ | `fix(gestanti)` | Root cause: strict `sesso === "F"`; now CF fallback + unknown group. |
| 6 Mansioni femminili | ✅ | `fix(gestanti)` | Male-only mansioni hidden; unknown-sex and unheld mansioni kept (see commit). |
| 7 Biologico DPI / malattie | ✅ | `feat(biologico)` | Sintomi/cura text to be reviewed by the MC. |
| 8 Stress popup | ✅ | `feat(stress)` | Once per browser session per azienda. |
| 9 Stress mansioni | ✅ | `feat(stress)` | Also fixed: the allegato printed one arbitrary row. |
| 10 VDT postazione | ✅ | `feat(vdt)` | Plus ambiente_id ownership check. |
| 11 MMC save | ✅ | `fix(mmc)` | Root cause: stored CP read as override → silent validation block. |
| 12 Misure popup | ✅ | `feat(ui)` | Once per azienda, "?" reopens it. |
| 13 Guida | ✅ text | `docs(guida)` | Screenshots not refreshed. |
| 14 Rischi da foto | ✅ | `feat(rischi)` | Vision credits (4 per call). |
| 15 Disclaimer AI | ✅ | `feat(ui)` | Once per ambiente per browser session. |
| 16 Aggiungi sede | ✅ | `feat(aziende)` | |
| 17 P.IVA duplicata | ✅ | `feat(aziende)` | Each sede counts against the direct-plan site limit. |

Once deployed, flip rows 1–17 to `risolto` in /admin/feedback (2 to `in_revisione` pending the clarification).
