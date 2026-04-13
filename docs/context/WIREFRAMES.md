> **NIUEXA** | AI-Powered Business Automation  
> *N2O DVR Automation Platform — Project Documentation*  
> Version 1.1 | April 2026 | Gregor Maric  
> Confidential — Niuexa & N2O SRL

---

# Wireframes

This document is the definitive visual blueprint for every screen in the N2O DVR Automation Platform. It captures layout, component placement, interaction behavior, states, and responsive breakpoints using ASCII wireframes with detailed annotations. Every developer, designer, and stakeholder should treat this as the source of truth for what the application looks like and how it behaves.

**Design System**: "Digital Guardian" light theme (clean white #F8F9FC surfaces, deep navy #003D74 primary, blue accent #A5C8FF), shadcn/ui components, Plus Jakarta Sans headings + Inter body, 8px spacing grid, 12px rounded corners, tonal layering (no hard borders), gradient CTAs (#003D74 → #1B5594), ambient whisper shadows.

**Responsive Breakpoints**:
- Desktop: ≥1024px (full sidebar 256px + 2-column forms)
- Tablet: 768–1023px (icon-only sidebar 64px + single-column forms)
- Mobile: <768px (hamburger drawer + stacked layout)

---

## Table of Contents

1. [Global Navigation Shell](#1-global-navigation-shell)
2. [Login](#2-login)
3. [Dashboard](#3-dashboard)
4. [Survey Wizard — Shell](#4-survey-wizard--shell)
5. [Step 1: Azienda (Company)](#5-step-1-azienda)
6. [Step 2: Persone (Employees)](#6-step-2-persone)
7. [Step 3: Ambienti (Environments)](#7-step-3-ambienti)
8. [Step 4: Attrezzature (Equipment)](#8-step-4-attrezzature)
9. [Step 5: Rischi (Risk Checklist)](#9-step-5-rischi)
10. [Step 6: Sostanze Chimiche (SDS Extraction)](#10-step-6-sostanze-chimiche)
11. [Step 7: Riepilogo (Summary + Signature)](#11-step-7-riepilogo)
12. [Risk Scoring Interface](#12-risk-scoring-interface)
13. [Document Generation](#13-document-generation)
14. [Phase 3: MMC Assessment](#14-mmc-assessment)
15. [Phase 3: VDT Assessment](#15-vdt-assessment)
16. [Phase 3: Stress Lavoro-Correlato](#16-stress-lavoro-correlato)
17. [Phase 3: Gestanti (Pregnant Workers)](#17-gestanti)
18. [Phase 3: Rischio Incendio (Fire Risk)](#18-rischio-incendio)
19. [Phase 3: Microclima (Thermal Comfort)](#19-microclima)
20. [Phase 3: Rischio Biologico](#20-rischio-biologico)
21. [Phase 4: PEE (Emergency Plan)](#21-pee)
22. [Phase 4: HACCP](#22-haccp)
23. [Phase 4: DUVRI](#23-duvri)
24. [Phase 4: POS](#24-pos)
25. [Settings](#25-settings)
26. [Role-Based Access Matrix](#26-role-based-access-matrix)
27. [Reusable Component Patterns](#27-reusable-component-patterns)

---

## 1. Global Navigation Shell

Every authenticated page shares this shell. The sidebar, header, and content area are persistent.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ HEADER BAR (h: 64px, sticky top, surface-container bg)                  │
│ ┌────────────────────────────────────┐  ┌─────────────────────────────┐ │
│ │ 📍 Dashboard > N2O SRL > Ambienti  │  │ 🔔 3  ⬛ Queue(2) 👤 GM ▾  │ │
│ │ Breadcrumb (text-secondary)        │  │ Notifications / Queue / User│ │
│ └────────────────────────────────────┘  └─────────────────────────────┘ │
├────────────┬─────────────────────────────────────────────────────────────┤
│ SIDEBAR    │ MAIN CONTENT AREA                                          │
│ (w: 256px) │ (scrollable, max-w: 1280px, centered)                     │
│            │                                                             │
│ ┌────────┐ │  ┌─────────────────────────────────────────────────────┐   │
│ │ N2O    │ │  │                                                     │   │
│ │ Safety │ │  │  Page content rendered here                         │   │
│ │ [logo] │ │  │                                                     │   │
│ └────────┘ │  │  - Dashboard cards                                  │   │
│            │  │  - Survey wizard steps                               │   │
│ ┌────────┐ │  │  - Risk scoring tables                              │   │
│ │▶ Dash  │ │  │  - Document generation grid                        │   │
│ │  board │ │  │  - Assessment forms                                 │   │
│ ├────────┤ │  │                                                     │   │
│ │  Sopral│ │  │                                                     │   │
│ │  luogo │ │  │                                                     │   │
│ ├────────┤ │  │                                                     │   │
│ │  Valut.│ │  │                                                     │   │
│ │  Rischi│ │  │                                                     │   │
│ ├────────┤ │  │                                                     │   │
│ │  Docum.│ │  │                                                     │   │
│ ├────────┤ │  │                                                     │   │
│ │  Valut.│ │  │                                                     │   │
│ │  azioni│ │  │  (Phase 3 assessments: MMC, VDT, Stress, etc.)     │   │
│ ├────────┤ │  │                                                     │   │
│ │  Impost│ │  │                                                     │   │
│ │  azioni│ │  │                                                     │   │
│ └────────┘ │  └─────────────────────────────────────────────────────┘   │
│            │                                                             │
│ ┌────────┐ │                                                             │
│ │ 👤 User│ │                                                             │
│ │ Name   │ │                                                             │
│ │ Role   │ │                                                             │
│ └────────┘ │                                                             │
└────────────┴─────────────────────────────────────────────────────────────┘
```

### Sidebar Navigation Items

| Icon | Label (IT) | Route | Badge |
|------|-----------|-------|-------|
| LayoutDashboard | Dashboard | `/[lang]/dashboard` | — |
| ClipboardList | Sopralluogo | `/[lang]/survey/[aziendaId]` | Count of active surveys |
| ShieldAlert | Valutazione Rischi | `/[lang]/risk-scoring/[aziendaId]` | — |
| FileStack | Documenti | `/[lang]/documents/[aziendaId]` | Count of ready docs |
| FlaskConical | Valutazioni | `/[lang]/assessments/[aziendaId]` | — |
| Settings | Impostazioni | `/[lang]/settings` | — |

### Header Queue Indicator

```
┌──────────────────────────────┐
│ ⬛ 2 documenti in coda  ▾    │
├──────────────────────────────┤
│ DVR Master      ████░░ 65%   │
│ Allegato MMC    ░░░░░░ In coda│
└──────────────────────────────┘
```

Dropdown shows each queued document with name + progress bar or queue position. Updates via WebSocket.

### Responsive Behavior

```
TABLET (<1024px):                    MOBILE (<768px):
┌──┬─────────────────┐              ┌─────────────────────┐
│☰ │ Header          │              │ ☰  N2O Safety  👤   │
│  │                 │              ├─────────────────────┤
│🏠│ Content         │              │                     │
│📋│                 │              │ Full-width content  │
│⚠│                 │              │                     │
│📄│                 │              └─────────────────────┘
│⚙│                 │
└──┴─────────────────┘              Hamburger opens slide-over
Icons only (64px sidebar)           drawer with full labels
```

---

## 2. Login

**Route**: `/[lang]/login` (public, no sidebar)

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│                    ┌──────────────────────┐                   │
│                    │                      │                   │
│                    │      N2O Safety      │                   │
│                    │      [App Logo]      │                   │
│                    │                      │                   │
│                    │  ┌────────────────┐  │                   │
│                    │  │ Email          │  │                   │
│                    │  └────────────────┘  │                   │
│                    │  ┌────────────────┐  │                   │
│                    │  │ Password    👁  │  │                   │
│                    │  └────────────────┘  │                   │
│                    │                      │                   │
│                    │  ☐ Ricordami         │                   │
│                    │                      │                   │
│                    │  ┌────────────────┐  │                   │
│                    │  │   Accedi       │  │                   │
│                    │  └────────────────┘  │                   │
│                    │                      │                   │
│                    │  ────── oppure ───── │                   │
│                    │                      │                   │
│                    │  ┌────────────────┐  │                   │
│                    │  │ G  Google      │  │                   │
│                    │  └────────────────┘  │                   │
│                    │                      │                   │
│                    │  Password dimenticata│                   │
│                    │                      │                   │
│                    └──────────────────────┘                   │
│                                                              │
│              © 2026 Niuexa — N2O DVR Platform                │
└──────────────────────────────────────────────────────────────┘
```

### States

- **Error**: Red text below password field: "Email o password non validi"
- **Loading**: "Accedi" button shows spinner, inputs disabled
- **Google OAuth**: Redirects to Google consent screen, returns to dashboard
- **Already authenticated**: Auto-redirect to `/[lang]/dashboard`

---

## 3. Dashboard

**Route**: `/[lang]/dashboard`

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Benvenuto nel Caveau Digitale                                   │
│  L'automazione della sicurezza sul lavoro per le tue aziende     │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │    12    │  │     3    │  │    48    │  │     2    │        │
│  │ AZIENDE  │  │SOPRALLU. │  │DOCUMENTI │  │   IN    │        │
│  │ TOTALI   │  │ ATTIVI   │  │ PRONTI   │  │GENERAZ. │        │
│  │          │  │  (amber) │  │  (green) │  │  (blue) │        │
│  │          │  │          │  │          │  │         │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                                                  │
│  Aziende Recenti                     ┌─────────────────────┐    │
│  Le tue aziende in gestione          │ 🔍 Cerca azienda... │    │
│                                      └─────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ RAGIONE SOCIALE    │ SEDE      │ATECO │SOPRAL.│DOC│AZIONI│   │
│  ├────────────────────┼───────────┼──────┼───────┼───┼──────┤   │
│  │ Rossi Costruz. SRL │ Milano(MI)│41.20 │██ Bozza│3/16│ Apri │   │
│  │ Smart Logistics SpA│ Torino(TO)│52.10 │██ Corso│8/16│ Apri │   │
│  │ Green Factory Co.  │ Roma (RM) │35.11 │██ Inv. │16/16│Apri │   │
│  │ Alimentari Bianchi │ Napoli(NA)│10.71 │██ Compl│16/16│Apri │   │
│  │ Dental Studio Verdi│ Firenze   │86.23 │██ Bozza│0/16│ Apri │   │
│  └────────────────────┴───────────┴──────┴───────┴───┴──────┘   │
│  ← Precedente    1  2  3    Successivo →                        │
│                                                                  │
│  ┌──────────────────────────┐  ┌─────────────────────────────┐  │
│  │ Documenti per Tipo       │  │ Scadenze Imminenti          │  │
│  │        ┌───┐             │  │                             │  │
│  │       /  48 \            │  │ ⚠ Rossi Costruz. - DVR     │  │
│  │      │ TOTALI│           │  │   Scade: 15/05/2026        │  │
│  │       \ ████/            │  │ ⚠ Smart Logistics - VDT    │  │
│  │        └───┘             │  │   Scade: 22/05/2026        │  │
│  │  ■ DVR Pronti   ■ MMC   │  │ ● Green Factory - Stress   │  │
│  │  ■ In Coda      ■ Altro │  │   Scade: 01/06/2026        │  │
│  └──────────────────────────┘  └─────────────────────────────┘  │
│                                                                  │
│  ┌────────────────┐                                              │
│  │ + Nuova Azienda │  (Primary button, top-right of table)      │
│  └────────────────┘                                              │
└──────────────────────────────────────────────────────────────────┘
```

### "Nuova Azienda" Modal

```
┌────────────────────────────────────────────┐
│  Nuova Azienda                         ✕   │
│                                            │
│  Ragione Sociale *                         │
│  ┌──────────────────────────────────────┐  │
│  │                                      │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  Sede Legale - Via *          Città *      │
│  ┌──────────────────┐  ┌────────────────┐  │
│  │                  │  │                │  │
│  └──────────────────┘  └────────────────┘  │
│                                            │
│  Codice ATECO *                            │
│  ┌──────────────────────────────────────┐  │
│  │ es. 46.69.94                         │  │
│  └──────────────────────────────────────┘  │
│                                            │
│           ┌──────────┐  ┌──────────┐       │
│           │ Annulla  │  │  Crea    │       │
│           └──────────┘  └──────────┘       │
└────────────────────────────────────────────┘
```

### Dashboard States

| State | Appearance |
|-------|-----------|
| **Empty** | No KPIs, centered: "Nessuna azienda ancora." + "Nuova Azienda" CTA |
| **Loading** | 4 skeleton KPI cards + 5 skeleton table rows |
| **Error** | Toast: "Errore nel caricamento" + retry |
| **Populated** | Full layout as shown above |

---

## 4. Survey Wizard — Shell

**Route**: `/[lang]/survey/[aziendaId]`

The survey is a 7-step wizard wrapped in a persistent shell with step bar and bottom navigation.

```
┌──────────────────────────────────────────────────────────────────┐
│  HEADER: Dashboard > Rossi Costruzioni SRL > Sopralluogo        │
│                                              ┌───────┐ ┌──────┐ │
│                                              │Salva  │ │██Bozza│ │
│                                              │Bozza  │ └──────┘ │
│                                              └───────┘          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  STEP BAR (inside white/surface card, sticky below header)       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │  ●───●───●───◉───○───○───○                               │   │
│  │  1   2   3   4   5   6   7                               │   │
│  │  Az. Per.Amb.Attr.Ris.Chim.Riep.                        │   │
│  │  ✓   ✓   ✓   ▶   ○   ○   ○                              │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │                                                          │   │
│  │              STEP CONTENT AREA                           │   │
│  │              (Framer Motion animated)                    │   │
│  │                                                          │   │
│  │              Each step renders its form here.            │   │
│  │              Slides left/right on navigation.            │   │
│  │                                                          │   │
│  │                                                          │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ BOTTOM NAV                                               │   │
│  │ ┌───────────────┐                    ┌────────────────┐  │   │
│  │ │ ← Indietro    │     Salvato ✓      │   Avanti →     │  │   │
│  │ │ (Ambienti)    │                    │  (Rischi)      │  │   │
│  │ └───────────────┘                    └────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Step Bar States

```
LEGEND:
  ●  = Completed (green circle + checkmark, clickable)
  ◉  = Active (primary color circle + step number)
  ○  = Locked/Future (gray circle, not clickable in linear mode)
  ─  = Connector line (green if both sides complete, gray otherwise)

LINEAR MODE (first pass):
  ●───●───◉───○───○───○───○
  1   2   3   4   5   6   7
  ✓   ✓   ▶

FREE MODE (after reaching step 7):
  ●───●───●───●───●───●───●
  1   2   3   4   5   6   7
  ✓   ✓   ✓   ✓   ✓   ✓   ✓     (all clickable, jump to any)
```

### Post-Submission Banner

```
┌──────────────────────────────────────────────────────────────┐
│ ⚠ Modificato dopo l'invio — le modifiche non sono ancora     │
│   firmate dal cliente.                    [Richiedi firma →] │
└──────────────────────────────────────────────────────────────┘
```

Shown as an amber banner at the top of content area when survey status is "Inviato" and any field has been edited since submission.

### Survey Lifecycle Badges

| Status | Badge Color | Nav Mode | Edit Behavior |
|--------|-------------|----------|---------------|
| Bozza | Gray | Linear | Full edit |
| In Corso | Amber | Linear | Full edit |
| Inviato | Blue | Free | Edit + warning banner |
| Completato | Green | Free | Edit + warning banner |

---

## 5. Step 1: Azienda

**Purpose**: Company master data — foundation for all 16 documents.

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  DATI AZIENDALI                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                                                             │ │
│  │  Ragione Sociale *                                          │ │
│  │  ┌───────────────────────────────────────────────────────┐  │ │
│  │  │ N2O SRL                                               │  │ │
│  │  └───────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  Partita IVA *                  Codice ATECO *              │ │
│  │  ┌────────────────────┐  ┌────────────────────────────────┐ │ │
│  │  │ 12345678901        │  │ 46.69.94                       │ │ │
│  │  └────────────────────┘  └────────────────────────────────┘ │ │
│  │  11 cifre                        Format: XX.XX.XX           │ │
│  │                                                             │ │
│  │  Attività *                                                 │ │
│  │  ┌───────────────────────────────────────────────────────┐  │ │
│  │  │ Commercio all'ingrosso articoli antincendio           │  │ │
│  │  └───────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  Orario Lavoro                  Metratura Totale (mq) *     │ │
│  │  ┌────────────────────┐  ┌────────────────────────────────┐ │ │
│  │  │ 46.69.94           │  │ Comm. ingrosso art. antincendio│ │ │
│  │  └────────────────────┘  └────────────────────────────────┘ │ │
│  │  Format: XX.XX.XX                                           │ │
│  │                                                             │ │
│  │  Orario Lavoro                  Metratura Totale (mq) *     │ │
│  │  ┌────────────────────┐  ┌────────────────────────────────┐ │ │
│  │  │ Lun-Ven 08:30-19:00│  │ 1000                           │ │ │
│  │  └────────────────────┘  └────────────────────────────────┘ │ │
│  │                                                             │ │
│  │  Zona Sismica *                                             │ │
│  │  ┌────────────────────┐                                     │ │
│  │  │ 3                ▾ │                                     │ │
│  │  └────────────────────┘                                     │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  SEDE LEGALE                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Via *                                                      │ │
│  │  ┌───────────────────────────────────────────────────────┐  │ │
│  │  │ VIA DEI CHIOSI 4                                      │  │ │
│  │  └───────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  Città (Provincia) *            CAP                         │ │
│  │  ┌────────────────────────┐  ┌──────────────────┐          │ │
│  │  │ GORGONZOLA (MI)        │  │ 20064            │          │ │
│  │  └────────────────────────┘  └──────────────────┘          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  SEDE OPERATIVA                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  ☐ Stessa della sede legale                                 │ │
│  │                                                             │ │
│  │  Via *                                                      │ │
│  │  ┌───────────────────────────────────────────────────────┐  │ │
│  │  │ VIA MONZA 107/30                                      │  │ │
│  │  └───────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  Città (Provincia) *            CAP                         │ │
│  │  ┌────────────────────────┐  ┌──────────────────┐          │ │
│  │  │ GESSATE (MI)           │  │ 20060            │          │ │
│  │  └────────────────────────┘  └──────────────────┘          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  DATORE DI LAVORO                                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Seleziona DdL *                                            │ │
│  │  ┌───────────────────────────────────────────────────────┐  │ │
│  │  │ CIARAMITARO AMALIA                                  ▾ │  │ │
│  │  └───────────────────────────────────────────────────────┘  │ │
│  │  ℹ Populated from Persone (Step 2). First visit shows:     │ │
│  │    "Aggiungi prima le persone al passo 2"                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  VISURA CAMERALE                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Visura Camerale (PDF)                                      │ │
│  │  ┌───────────────────────────────────────────────────────┐  │ │
│  │  │          📄                                            │  │ │
│  │  │  Trascina la visura PDF qui o clicca per caricare     │  │ │
│  │  │  (Usata per la generazione AI della descrizione)      │  │ │
│  │  └───────────────────────────────────────────────────────┘  │ │
│  │  [visura_n2o_srl.pdf 1.2MB ✕]                              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  AI-GENERATED FIELDS                                             │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Descrizione Attività                                       │ │
│  │  ┌─────────────────────────┐                                │ │
│  │  │ 🤖 Genera con AI       │  (button, primary-outline)     │ │
│  │  └─────────────────────────┘                                │ │
│  │  ┌───────────────────────────────────────────────────────┐  │ │
│  │  │ ┃ 🤖 AI                                               │  │ │
│  │  │ ┃ N2O SRL è un'azienda specializzata nel commercio   │  │ │
│  │  │ ┃ all'ingrosso di articoli antincendio e dispositivi  │  │ │
│  │  │ ┃ di protezione individuale...                        │  │ │
│  │  │ ┃                                                      │  │ │
│  │  └───────────────────────────────────────────────────────┘  │ │
│  │  Left blue border + "🤖 AI" badge = AI-generated content    │ │
│  │  Fully editable. Badge disappears if fully rewritten.       │ │
│  │                                                             │ │
│  │  Contesto Territoriale                                      │ │
│  │  (Same pattern as above)                                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Validation Errors (inline, on blur)

```
  Codice ATECO *
  ┌────────────────────┐
  │ 46.69              │  ← red border
  └────────────────────┘
  ⚠ Formato non valido (es. 46.69.94)   ← red text, 12px
```

---

## 6. Step 2: Persone

**Purpose**: Register all employees with roles, contracts, and safety assignments.

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Personale                                    ┌────────────────┐ │
│  Gestisci i dipendenti dell'azienda           │+ Aggiungi      │ │
│                                               │  Persona       │ │
│                                               └────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │NOMINATIVO  │MANSIONE    │CONTRATTO│S│ETÀ│RUOLI SICUR. │AZIONI││
│  ├────────────┼────────────┼─────────┼─┼───┼─────────────┼──────┤│
│  │MARCHETTI   │IMPIEGATO   │██IMPIEG.│M│>18│[RSPP][RLS]  │ ✏ 🗑 ││
│  │LUCA        │DOCENTE FORM│         │ │   │             │      ││
│  ├────────────┼────────────┼─────────┼─┼───┼─────────────┼──────┤│
│  │CIARAMITARO │AMMINISTR.  │██DdL    │F│>18│[P.S.][A.I.] │ ✏ 🗑 ││
│  │AMALIA      │            │         │ │   │[DdL]        │      ││
│  ├────────────┼────────────┼─────────┼─┼───┼─────────────┼──────┤│
│  │BIANCHI     │MAGAZZINIERE│██OPERAIO│M│>18│[Prep.][A.I.]│ ✏ 🗑 ││
│  │MARCO       │            │         │ │   │             │      ││
│  └────────────┴────────────┴─────────┴─┴───┴─────────────┴──────┘│
│                                                                  │
│  3 dipendenti registrati                                         │
│                                                                  │
│  EMPTY STATE:                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              👤                                           │   │
│  │    Nessun dipendente registrato.                         │   │
│  │         [+ Aggiungi Persona]                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Add/Edit Person Modal

```
┌────────────────────────────────────────────────┐
│  Aggiungi Persona                          ✕   │
│                                                │
│  Nominativo *                                  │
│  ┌──────────────────────────────────────────┐  │
│  │ MARCHETTI LUCA                           │  │  ← auto-uppercase
│  └──────────────────────────────────────────┘  │
│                                                │
│  Codice Fiscale *                              │
│  ┌──────────────────────────────────────────┐  │
│  │ MRCLCU93S03M052M                         │  │  ← masked after save
│  └──────────────────────────────────────────┘  │
│  16 caratteri alfanumerici                     │
│                                                │
│  Mansione *                                    │
│  ┌──────────────────────────────────────────┐  │
│  │ IMPIEGATO-DOCENTE FORMATORE              │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  Tipologia Contrattuale *    Sesso *           │
│  ┌──────────────────┐        ○ M  ● F         │
│  │ IMPIEGATO      ▾ │                          │
│  └──────────────────┘        Fascia Età *      │
│                              ● >18  ○ 15-18   │
│                                                │
│  Qualifiche                                    │
│  ┌──────────────────────────────────────────┐  │
│  │ es. Patentino muletto, Corso antincendio│  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  Ambienti Assegnati * (multi-select)           │
│  ┌──────────────────────────────────────────┐  │
│  │ ☑ Ufficio Amministrativo                │  │
│  │ ☑ Magazzino Principale                  │  │
│  │ ☐ Sala Corsi                            │  │
│  │ ☐ Spogliatoio                           │  │
│  └──────────────────────────────────────────┘  │
│  ℹ Populated from Ambienti (Step 3). If none  │
│    exist: "Aggiungi prima gli ambienti (Passo 3)"│
│                                                │
│  ── Ruoli di Sicurezza ──────────────────────  │
│                                                │
│  RSPP               ┌──●─┐  (toggle switch)   │
│  RLS                └●───┘                     │
│  Primo Soccorso     ┌──●─┐                     │
│  Antincendio        ┌──●─┐                     │
│  Preposto           └●───┘                     │
│  Datore di Lavoro   ┌──●─┐                     │
│                                                │
│  ⚠ RSPP già assegnato a BIANCHI MARCO.         │
│    Sostituire?  [Conferma] [Annulla]           │
│                                                │
│            ┌──────────┐  ┌──────────┐          │
│            │ Annulla  │  │  Salva   │          │
│            └──────────┘  └──────────┘          │
└────────────────────────────────────────────────┘
```

### Delete Confirmation

```
┌──────────────────────────────────────────┐
│  Conferma eliminazione                ✕  │
│                                          │
│  Eliminare MARCHETTI LUCA?               │
│  Questa azione non può essere annullata. │
│                                          │
│        ┌──────────┐  ┌──────────┐        │
│        │ Annulla  │  │ Elimina  │        │  ← red danger button
│        └──────────┘  └──────────┘        │
└──────────────────────────────────────────┘
```

---

## 7. Step 3: Ambienti

**Purpose**: Define work environments — drives equipment checklists, risk lists, and fire/microclima calculations.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Ambienti di Lavoro                           ┌────────────────────┐ │
│  Definisci gli ambienti dell'azienda          │ + Aggiungi Ambiente│ │
│                                               └────────────────────┘ │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │ UFFICIO AMMINIST.│  │ MAGAZZINO PRINC. │  │ SALA CORSI       │   │
│  │ ┌──────────────┐ │  │ ┌──────────────┐ │  │ ┌──────────────┐ │   │
│  │ │ ██ Ufficio   │ │  │ │ ██ Magazzino │ │  │ │ ██ Sala Corsi│ │   │
│  │ └──────────────┘ │  │ └──────────────┘ │  │ └──────────────┘ │   │
│  │ 📐 50 mq         │  │ 📐 150 mq        │  │ 📐 80 mq         │   │
│  │ 👤 Marchetti L.  │  │ 👤 Bianchi M.    │  │ 👤 —              │   │
│  │ Amministrazione  │  │ Stoccaggio merci │  │ Formazione        │   │
│  │         ✏ 🗑      │  │         ✏ 🗑      │  │         ✏ 🗑      │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘   │
│                                                                      │
│  ┌──────────────────┐                                                │
│  │ SPOGLIATOIO      │      Riepilogo Sopralluogo                    │
│  │ ┌──────────────┐ │      ┌─────────────────────┐                  │
│  │ │ ██ Esterno   │ │      │       42%            │                  │
│  │ └──────────────┘ │      │     ┌────┐           │                  │
│  │ 📐 15 mq         │      │     │ ●  │  Progresso│                  │
│  │ 👤 —              │      │     └────┘           │                  │
│  │ —                 │      │ ● Azienda    ✓      │                  │
│  │         ✏ 🗑      │      │ ● Persone    ✓      │                  │
│  └──────────────────┘      │ ● Ambienti   ▶      │                  │
│                            │ ○ Attrezzature       │                  │
│                            │ ○ Rischi             │                  │
│                            │ ○ Sost. Chimiche     │                  │
│                            │ ○ Riepilogo          │                  │
│                            └─────────────────────┘                  │
│                                                                      │
│  EMPTY STATE:                                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    🏢                                          │  │
│  │      Nessun ambiente aggiunto.                                │  │
│  │           [+ Aggiungi Ambiente]                               │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Add/Edit Environment Modal

```
┌────────────────────────────────────────────────┐
│  Aggiungi Nuovo Ambiente                   ✕   │
│                                                │
│  ☐ Usa informazioni da altro ambiente          │
│                                                │
│  Nome *                                        │
│  ┌──────────────────────────────────────────┐  │
│  │ LABORATORIO CHIMICO                      │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  Scegli Tipologia *                            │
│  ┌──────────────────────────────────────────┐  │
│  │ Ufficio                               ▾  │  │
│  └──────────────────────────────────────────┘  │
│  Options: Ufficio, Magazzino, Sala Corsi,      │
│  Cucina, Esterno, Laboratorio, Officina        │
│                                                │
│  Superficie (mq)            Preposto           │
│  ┌──────────────────┐  ┌──────────────────┐   │
│  │ 120              │  │ Bianchi M.    ▾  │   │
│  └──────────────────┘  └──────────────────┘   │
│                                                │
│  Descrizione Attività                          │
│  ┌──────────────────────────────────────────┐  │
│  │ Descrivi brevemente le attività svolte   │  │
│  │ in questo ambiente...                    │  │
│  │                                          │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  Documentazione Fotografica                    │
│  ┌──────────────────────────────────────────┐  │
│  │          📷                               │  │
│  │  Trascina le foto qui o clicca per        │  │
│  │  caricare (max 10 foto, JPG/PNG/HEIC)    │  │
│  └──────────────────────────────────────────┘  │
│  [thumb1.jpg 2.1MB ✕] [thumb2.jpg 1.8MB ✕]   │
│                                                │
│            ┌──────────┐  ┌──────────────────┐  │
│            │ Annulla  │  │+ Aggiungi Ambiente│  │
│            └──────────┘  └───────────────────┘  │
└────────────────────────────────────────────────┘
```

### Environment Type Change Warning

```
┌──────────────────────────────────────────────┐
│  ⚠ Cambiamento tipo ambiente              ✕  │
│                                              │
│  Cambiando il tipo di ambiente verranno      │
│  aggiornate le attrezzature e i rischi       │
│  associati. Continuare?                      │
│                                              │
│        ┌──────────┐  ┌──────────┐            │
│        │ Annulla  │  │ Conferma │            │
│        └──────────┘  └──────────┘            │
└──────────────────────────────────────────────┘
```

---

## 8. Step 4: Attrezzature

**Purpose**: Equipment checklists per environment. Checklist items change dynamically based on environment type.

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Attrezzature                                                    │
│  Seleziona le attrezzature presenti in ogni ambiente             │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Ufficio Amm. (5) │ Magazzino (8) │ Sala Corsi (3) │ ...  │  │
│  │ ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔                                        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                        Active tab underlined     │
│  UFFICIO AMMINISTRATIVO — Tipo: Ufficio                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ■ ARREDI E POSTAZIONI                                    │   │
│  │                                                          │   │
│  │ ☑ Scrivania                  CE: ●SI  ○NO   Verif: ●SI  │   │
│  │ ☑ Sedia ergonomica          CE: ●SI  ○NO   Verif: ●SI  │   │
│  │ ☐ Armadio/scaffalatura                                   │   │
│  │ ☐ Cassettiera                                            │   │
│  │                                                          │   │
│  │ ■ APPARECCHIATURE ELETTRONICHE                           │   │
│  │                                                          │   │
│  │ ☑ Monitor                   CE: ●SI  ○NO   Verif: ○NO  │   │
│  │ ☑ Tastiera + mouse          CE: ●SI  ○NO   Verif: ○NO  │   │
│  │ ☑ Stampante                 CE: ●SI  ○NO   Verif: ●SI  │   │
│  │ ☐ Scanner                                                │   │
│  │ ☐ Telefono / centralino                                  │   │
│  │                                                          │   │
│  │ ■ CLIMATIZZAZIONE                                        │   │
│  │                                                          │   │
│  │ ☐ Condizionatore / split                                 │   │
│  │ ☐ Ventilatore                                            │   │
│  │ ☐ Stufa elettrica                                        │   │
│  │                                                          │   │
│  │ ─────────────────────────────────────────────────────── │   │
│  │ + Aggiungi attrezzatura personalizzata                   │   │
│  │ ┌─────────────────────────────────┐  ┌─────────┐        │   │
│  │ │ Nome attrezzatura...            │  │ Aggiungi│        │   │
│  │ └─────────────────────────────────┘  └─────────┘        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  5 attrezzature selezionate per Ufficio Amministrativo           │
│                                                                  │
│  NO ENVIRONMENTS STATE:                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Aggiungi prima gli ambienti nel Passo 3.               │   │
│  │  [← Vai al Passo 3]                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Equipment Items by Environment Type

| Environment Type | Equipment Categories |
|-----------------|---------------------|
| Ufficio | Arredi, Elettroniche, Climatizzazione |
| Magazzino | Scaffalature, Sollevamento, Trasporto, DPI |
| Cucina | Cottura, Refrigerazione, Lavaggio, Taglio |
| Sala Corsi | Arredi, Proiezione, Elettroniche |
| Esterno | Veicoli, Attrezzi, DPI |
| Laboratorio | Strumentazione, Aspirazione/Ventilazione, DPI Specifici, Stoccaggio |
| Officina | Macchine Utensili, Saldatura, Sollevamento, DPI, Compressori |

**Data model note**: Equipment is scoped per-environment (via `ambiente_id` FK or junction table `attrezzature_ambienti`). The tab-per-environment UI requires this relationship.

---

## 9. Step 5: Rischi

**Purpose**: Mark which risks from the standard library apply to each environment. Sets up the Risk Scoring interface.

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Rischi                                                          │
│  Seleziona i rischi applicabili per ambiente                     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Ufficio Amm. (12)│ Magazzino (18) │ Sala Corsi (8) │ ... │  │
│  │ ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔                                       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  UFFICIO AMMINISTRATIVO                                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ▼ STRUTTURE (3 selezionati)                              │   │
│  │                                                          │   │
│  │ ☑ Presenza di ingombri ad altezza d'uomo — Infortuni    │   │
│  │   al capo durante la normale circolazione                │   │
│  │ ☑ Pavimentazione sconnessa o scivolosa — Infortuni per  │   │
│  │   scivolamento, cadute a livello                         │   │
│  │ ☑ Porte/finestre con vetri non di sicurezza             │   │
│  │ ☐ Scale fisse con gradini usurati                        │   │
│  │ ☐ Parapetti o protezioni mancanti                        │   │
│  │                                                          │   │
│  │ ▼ ELETTRICI (2 selezionati)                              │   │
│  │                                                          │   │
│  │ ☑ Impianto elettrico non conforme — Elettrocuzione      │   │
│  │ ☑ Prese multiple sovraccariche — Cortocircuito, incendio│   │
│  │ ☐ Lavori elettrici sotto tensione                        │   │
│  │                                                          │   │
│  │ ▶ MACCHINE (0 selezionati)  ← collapsed, no selections │   │
│  │                                                          │   │
│  │ ▼ INCENDIO (2 selezionati)                               │   │
│  │ ...                                                      │   │
│  │                                                          │   │
│  │ ▶ CHIMICI (0)                                            │   │
│  │ ▶ FISICI (1)                                             │   │
│  │ ▶ BIOLOGICI (0)                                          │   │
│  │ ▶ CANCEROGENI (0)                                        │   │
│  │ ▼ ORGANIZZAZIONE (2)                                     │   │
│  │ ...                                                      │   │
│  │ ▶ PSICOLOGICI (1)                                        │   │
│  │ ▼ ERGONOMICI (1)                                         │   │
│  │ ...                                                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 12 rischi selezionati su 45 disponibili per              │   │
│  │ Ufficio Amministrativo                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│  Summary bar — updates in real time as checkboxes toggle        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Environment Modified Banner

When environments are added/removed after risks were already selected:

```
┌──────────────────────────────────────────────────────────────┐
│ ⚠ Ambienti modificati — rivedi le selezioni dei rischi.      │
│                                          [Chiudi]            │
└──────────────────────────────────────────────────────────────┘
```

---

## 10. Step 6: Sostanze Chimiche

**Purpose**: Upload SDS PDFs for AI extraction, review and correct extracted data.

### Phase 1: Upload

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Sostanze Chimiche                                               │
│  Carica le Schede di Sicurezza (SDS) per l'estrazione AI        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │                      📄                                   │   │
│  │                                                          │   │
│  │   Trascina i file SDS (PDF) qui, oppure clicca per       │   │
│  │   selezionare                                            │   │
│  │                                                          │   │
│  │   Max 20 file per caricamento · Solo PDF · Max 50MB      │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│  (dashed border, drag-and-drop zone, react-dropzone)            │
│                                                                  │
│  File selezionati: 3/20                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 📄 SDS_Detergente_Industriale.pdf      2.1 MB        ✕  │   │
│  │ 📄 SDS_Solvente_Acetone.pdf            1.8 MB        ✕  │   │
│  │ 📄 SDS_Vernice_Spray.pdf               3.4 MB        ✕  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────┐                                          │
│  │ Avvia Estrazione   │  (Primary button)                       │
│  └────────────────────┘                                          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Phase 2: Extraction Progress

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Estrazione in Corso — 2 di 3 file completati                    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 📄 SDS_Detergente_Ind...   ████████████████████ Completato ✓│ │
│  │ 📄 SDS_Solvente_Acet...   █████████████░░░░░░░ Estrazione...│ │
│  │ 📄 SDS_Vernice_Spray...   ░░░░░░░░░░░░░░░░░░░ In coda      │ │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ ████████████████████████░░░░░░░░░░░░ 65%               │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Phase 3: Review Table

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Revisione Estrazioni                        ┌────────────────────┐ │
│  Verifica i dati estratti dall'AI            │ Conferma Tutti     │ │
│                                              └────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │PRODOTTO    │PRODUTTORE│PITTOGR.│STATO │FRASI H  │FRASI P│AZIONI│  │
│  │ 🤖 AI      │ 🤖 AI     │        │      │ 🤖 AI    │ 🤖 AI  │      │  │
│  ├────────────┼──────────┼────────┼──────┼─────────┼───────┼──────┤  │
│  │Detergente  │ChemCo    │⬡ ⬡    │Liquid│H315,H319│P264,  │ ✓ 🗑 │  │
│  │Industriale │SRL       │GHS05   │      │         │P280   │      │  │
│  │            │          │GHS07   │      │         │       │      │  │
│  ├────────────┼──────────┼────────┼──────┼─────────┼───────┼──────┤  │
│  │Acetone     │SolventPro│⬡      │Liquid│H225,    │P210,  │ ✓ 🗑 │  │
│  │ Revisionato│SpA       │GHS02   │      │H319,H336│P233   │      │  │
│  ├────────────┼──────────┼────────┼──────┼─────────┼───────┼──────┤  │
│  │Vernice     │PaintMax  │⬡ ⬡ ⬡  │Gas   │H222,    │P210,  │ ✓ 🗑 │  │
│  │Spray       │          │GHS02   │      │H229,H336│P251   │      │  │
│  │  ⚠ bassa   │          │GHS04   │      │         │       │      │  │
│  │  confidenza│          │GHS07   │      │         │       │      │  │
│  └────────────┴──────────┴────────┴──────┴─────────┴───────┴──────┘  │
│                                                                      │
│  🤖 AI = AI-extracted, editable. Click any cell to edit inline.       │
│  ⚠  = Low confidence — review carefully.                             │
│  Revisionato = Human-reviewed cell.                                  │
│                                                                      │
│  ┌──────────────────────────────────┐                                │
│  │ + Aggiungi Sostanza Manualmente  │  (secondary button)           │
│  └──────────────────────────────────┘                                │
│                                                                      │
│  ┌────────────────────┐                                              │
│  │ Conferma e Salva   │  (Primary button)                           │
│  └────────────────────┘                                              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 11. Step 7: Riepilogo

**Purpose**: Read-only summary of all entered data + digital countersignature for the client.

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Riepilogo Sopralluogo                                           │
│  Rivedi i dati inseriti prima dell'invio                        │
│                                                                  │
│  COMPLETENESS CHECK                                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ✅ Azienda         — Completo                    [Modifica]│   │
│  │ ✅ Persone          — 3 dipendenti               [Modifica]│   │
│  │ ✅ Ambienti         — 4 ambienti                 [Modifica]│   │
│  │ ✅ Attrezzature     — 16 totali                  [Modifica]│   │
│  │ ✅ Rischi           — 38 rischi selezionati      [Modifica]│   │
│  │ ⚠  Sost. Chimiche  — Dati mancanti              [Completa]│   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ── DATI AZIENDALI ──────────────────────────── [Modifica →] ── │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Ragione Sociale:    N2O SRL                              │   │
│  │ Codice ATECO:       46.69.94                             │   │
│  │ Sede Legale:        Via dei Chiosi 4, Gorgonzola (MI)    │   │
│  │ Sede Operativa:     Via Monza 107/30, Gessate (MI)       │   │
│  │ Datore di Lavoro:   CIARAMITARO AMALIA                   │   │
│  │ Zona Sismica:       3                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ── PERSONALE (3) ───────────────────────────── [Modifica →] ── │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ MARCHETTI LUCA      │ IMPIEGATO-DOC.  │ RSPP, RLS       │   │
│  │ CIARAMITARO AMALIA  │ AMMINISTR.      │ DdL, P.S., A.I. │   │
│  │ BIANCHI MARCO       │ MAGAZZINIERE    │ Prep., A.I.     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ── AMBIENTI (4) ────────────────────────────── [Modifica →] ── │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ UFFICIO AMMINISTRATIVO  │ Ufficio     │ 50 mq           │   │
│  │ MAGAZZINO PRINCIPALE    │ Magazzino   │ 150 mq          │   │
│  │ SALA CORSI              │ Sala Corsi  │ 80 mq           │   │
│  │ SPOGLIATOIO             │ Esterno     │ 15 mq           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ── ATTREZZATURE ────────────────────────────── [Modifica →] ── │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Ufficio Amm.: 5 attrezzature   │ Magazzino: 8           │   │
│  │ Sala Corsi: 3                  │ Spogliatoio: 0         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ── RISCHI ──────────────────────────────────── [Modifica →] ── │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Ufficio Amm.: 12 rischi  │ Magazzino: 18 rischi         │   │
│  │ Sala Corsi: 8 rischi     │ Spogliatoio: 0               │   │
│  │ Per categoria: Strutture(8), Elettrici(6), Incendio(5)..│   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ── SOSTANZE CHIMICHE ───────────────────────── [Modifica →] ── │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 3 sostanze registrate                                    │   │
│  │ Detergente Industriale │ ChemCo SRL     │ ⬡GHS05 ⬡GHS07│   │
│  │ Acetone                │ SolventPro SpA │ ⬡GHS02        │   │
│  │ Vernice Spray          │ PaintMax       │ ⬡GHS02 ⬡GHS04│   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ═══════════════════════════════════════════════════════════════ │
│                                                                  │
│  FIRMA DEL CLIENTE                                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │  Nome del firmatario *                                   │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │ CIARAMITARO AMALIA                               │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  │  Firma *                             Data                │   │
│  │  ┌──────────────────────────┐  ┌──────────────────┐     │   │
│  │  │                          │  │ 12/04/2026       │     │   │
│  │  │   ~~signature canvas~~   │  │ (auto, read-only)│     │   │
│  │  │                          │  └──────────────────┘     │   │
│  │  │                          │                            │   │
│  │  └──────────────────────────┘                            │   │
│  │  [Cancella firma]                                        │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │            Invia Sopralluogo                      │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  INCOMPLETE STATE (signature disabled):                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ⚠ Completa tutti i passi prima di firmare:               │   │
│  │   • Passo 6: Sostanze Chimiche [→ Completa]              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 12. Risk Scoring Interface

**Route**: `/[lang]/risk-scoring/[aziendaId]`

**Purpose**: The core "review, not data entry" screen. Office operators adjust P/D scores for all risks marked in Step 5.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Valutazione Rischi — Rossi Costruzioni SRL                          │
│                                                     ┌─────────────┐ │
│                                                     │Salva Modif. │ │
│                                                     └─────────────┘ │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │ Tutti (38) │ Ufficio (12) │ Magazzino (18) │ Sala Corsi (8) │   │
│  │▔▔▔▔▔▔▔▔▔▔▔                                                  │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ■ UFFICIO AMMINISTRATIVO — 12 rischi                                │
│  3 accettabili, 5 modesti, 3 gravi, 1 gravissimo                    │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │CAT.    │PERICOLO           │ESPOSIZIONE    │RISCHIO │P│D│ I │LIV│ │
│  ├────────┼───────────────────┼───────────────┼────────┼─┼─┼───┼───┤ │
│  │Strutt. │Ingombri altezza   │Circolazione   │Infort. │2│2│ 6 │██ │ │
│  │        │d'uomo             │normale        │al capo │ │ │MOD│YEL│ │
│  │        │                                           │ │ │   │   │ │
│  │        │  ▶ Misure di prevenzione                          │   │ │
│  ├────────┼───────────────────┼───────────────┼────────┼─┼─┼───┼───┤ │
│  │Strutt. │Paviment. sconnessa│Circolazione   │Scivolam│1│1│ 3 │██ │ │
│  │        │o scivolosa        │               │cadute  │ │ │ACC│GRN│ │
│  ├────────┼───────────────────┼───────────────┼────────┼─┼─┼───┼───┤ │
│  │Elettr. │Impianto non       │Uso quotidiano │Elettro-│3│3│ 9 │██ │ │
│  │        │conforme           │               │cuzione │ │ │GRV│RED│ │
│  │        │                                           │ │ │   │   │ │
│  │        │  ▼ Misure di prevenzione (expanded)               │   │ │
│  │        │  ┌────────────────────────────────────────────┐   │   │ │
│  │        │  │ Misure attuali:                            │   │   │ │
│  │        │  │ ┌──────────────────────────────────────┐   │   │   │ │
│  │        │  │ │ Verifica periodica impianto da       │   │   │   │ │
│  │        │  │ │ elettricista qualificato. Installare │   │   │   │ │
│  │        │  │ │ interruttori differenziali...        │   │   │   │ │
│  │        │  │ └──────────────────────────────────────┘   │   │   │ │
│  │        │  │                                            │   │   │ │
│  │        │  │ ┌──────────────────────┐                   │   │   │ │
│  │        │  │ │ 🤖 Suggerisci con AI │                   │   │   │ │
│  │        │  │ └──────────────────────┘                   │   │   │ │
│  │        │  │                                            │   │   │ │
│  │        │  │ 🤖 AI Suggestion:                          │   │   │ │
│  │        │  │ ┌──────────────────────────────────────┐   │   │   │ │
│  │        │  │ │ Installare quadro elettrico con      │   │   │   │ │
│  │        │  │ │ protezione IP44 e verifica annuale   │   │   │   │ │
│  │        │  │ │ [Accetta] [Modifica] [Rifiuta]       │   │   │   │ │
│  │        │  │ └──────────────────────────────────────┘   │   │   │ │
│  │        │  └────────────────────────────────────────────┘   │   │ │
│  ├────────┼───────────────────────────────────────────────┼───┤   │ │
│  │ ...    │ (more risk rows)                              │   │   │ │
│  └────────┴───────────────────────────────────────────────┴───┘   │ │
│                                                                      │
│  Risk Level Color Legend:                                            │
│  ██ ACCETTABILE (I=3-4)  Green   — rischio sotto controllo          │
│  ██ MODESTO     (I=5-6)  Yellow  — monitoraggio consigliato         │
│  ██ GRAVE       (I=7-8)  Orange  — intervento necessario            │
│  ██ GRAVISSIMO  (I=9-12) Red     — intervento urgente               │
│                                                                      │
│  Formula: I = 2×D + P    (P and D each range 1–4, I range 3–12)     │
│  P: 1=Improbabile, 2=Poco prob., 3=Probabile, 4=Molto prob.        │
│  D: 1=Trascurabile, 2=Modesto, 3=Notevole, 4=Gravissimo           │
│  Note: Architecture and DB use 1-4 range. US-2.7 cites 1-3 —       │
│  resolved to 1-4 per SQL schema CHECK constraint and UI spec.       │
│                                                                      │
│  ┌──────────────┐  ┌──────────────────┐                             │
│  │ Salva Modif. │  │ Esporta Riepilogo│                             │
│  └──────────────┘  └──────────────────┘                             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### P/D Input Detail

```
  P column input:
  ┌───┐
  │ 2 │  ← number input, constrained 1-4
  └───┘     ↑↓ arrow keys increment/decrement
            Tab moves to D column
            On change: I recalculates instantly
            Row color band animates transition (200ms)
```

### Tooltip on P/D Hover

```
  ┌────────────────────┐
  │ Probabilità (P)    │
  │ 1 — Improbabile    │
  │ 2 — Poco probabile │
  │ 3 — Probabile      │
  │ 4 — Molto probabile│
  └────────────────────┘
```

---

## 13. Document Generation

**Route**: `/[lang]/documents/[aziendaId]`

**Purpose**: View, generate, download, and deliver all 16 documents for a company.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Documenti — Rossi Costruzioni SRL                                   │
│                                            ┌──────────────────────┐ │
│                                            │ Genera Tutti (12)    │ │
│                                            └──────────────────────┘ │
│                                                                      │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌──────────┐ │
│  │ 📄 DVR Master │ │ 📋 Allegato   │ │ 🖥 Allegato   │ │ 😰 Alleg.│ │
│  │               │ │    MMC        │ │    VDT        │ │   Stress │ │
│  │ ████████████  │ │               │ │               │ │          │ │
│  │ preview image │ │ ██ Non Gen.   │ │ ██ Non Gen.   │ │██ Non Gen│ │
│  │               │ │               │ │               │ │          │ │
│  │ ██ Pronto ✓   │ │ 15/04/2026   │ │ —             │ │ —        │ │
│  │ 12/04/2026    │ │               │ │               │ │          │ │
│  │               │ │ ┌───────────┐ │ │ ┌───────────┐ │ │┌───────┐│ │
│  │ ┌──────────┐  │ │ │  Genera   │ │ │ │  Genera   │ │ ││ Genera││ │
│  │ │ Scarica  │  │ │ └───────────┘ │ │ └───────────┘ │ │└───────┘│ │
│  │ └──────────┘  │ │               │ │               │ │         │ │
│  │ [Rigenera]    │ │               │ │               │ │         │ │
│  └───────────────┘ └───────────────┘ └───────────────┘ └─────────┘ │
│                                                                      │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌──────────┐ │
│  │ 🤰 Allegato   │ │ 🔥 Allegato   │ │ 🌡 Allegato   │ │ 🦠 Alleg.│ │
│  │   Gestanti    │ │   Incendio    │ │   Microclima  │ │  Biolog. │ │
│  │               │ │               │ │               │ │          │ │
│  │ ██ Non Gen.   │ │ ██ In Coda    │ │ ██ Non Gen.   │ │██ Non Gen│ │
│  │               │ │   Pos: #2     │ │               │ │          │ │
│  │ ┌───────────┐ │ │               │ │ ┌───────────┐ │ │┌───────┐│ │
│  │ │  Genera   │ │ │ ░░░░░░░░░░░  │ │ │  Genera   │ │ ││ Genera││ │
│  │ └───────────┘ │ │ In attesa... │ │ └───────────┘ │ │└───────┘│ │
│  └───────────────┘ └───────────────┘ └───────────────┘ └─────────┘ │
│                                                                      │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌──────────┐ │
│  │ 🚨 PEE        │ │ 🍽 HACCP      │ │ 🏗 DUVRI      │ │ 🏗 POS   │ │
│  │  Azienda      │ │  Manuale      │ │               │ │          │ │
│  │               │ │               │ │               │ │          │ │
│  │ ██ Generaz... │ │ ██ Errore ✗   │ │ ██ Non Gen.   │ │██ Non Gen│ │
│  │ ████████░░ 75%│ │               │ │               │ │          │ │
│  │               │ │ ┌───────────┐ │ │ ┌───────────┐ │ │┌───────┐│ │
│  │ [Annulla]     │ │ │  Riprova  │ │ │ │  Genera   │ │ ││ Genera││ │
│  │               │ │ └───────────┘ │ │ └───────────┘ │ │└───────┘│ │
│  │               │ │ [Dettagli]    │ │               │ │         │ │
│  └───────────────┘ └───────────────┘ └───────────────┘ └─────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Document Status States

| Status | Badge | Button | Card Behavior |
|--------|-------|--------|---------------|
| Non Generato | Gray | "Genera" (primary) | Static |
| In Coda | Blue | Queue position text | Static |
| Generazione... | Blue + spinner | "Annulla" (secondary) | Progress bar |
| Pronto | Green "Pronto ✓" | "Scarica" + "Rigenera" | Preview thumbnail |
| Errore | Red "Errore ✗" | "Riprova" + "Dettagli" | Error icon |
| Consegnato | Green "Consegnato ✓" | "Scarica" + "Rigenera" | Check + Drive link |

### Document Preview Panel (Slide-in)

```
┌──────────────────────────────────────────┐
│  DVR Master — Rossi Costruzioni SRL   ✕  │
│                                          │
│  ┌──────────────────┐                    │
│  │ 📥 Scarica .docx │                    │
│  └──────────────────┘                    │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │                                  │    │
│  │   ┌──────────────────────┐       │    │
│  │   │  ROSSI COSTRUZIONI   │       │    │
│  │   │  SRL                 │       │    │
│  │   │                      │       │    │
│  │   │  DOCUMENTO DI        │       │    │
│  │   │  VALUTAZIONE DEI     │       │    │
│  │   │  RISCHI              │       │    │
│  │   │                      │       │    │
│  │   │  Edizione 2026       │       │    │
│  │   └──────────────────────┘       │    │
│  │                                  │    │
│  │  Page 1 of 187                   │    │
│  │  ◀  ▶                            │    │
│  └──────────────────────────────────┘    │
│                                          │
│  Versione: v3                            │
│  Generato: 12/04/2026 14:35             │
│  Generato da: Marchetti Luca            │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ Cronologia Versioni              │    │
│  │ v3  12/04/2026  Marchetti L.    │    │
│  │ v2  08/04/2026  Marchetti L.    │    │
│  │ v1  01/04/2026  Ciaramitaro A.  │    │
│  │        [Differenze v2↔v3]       │    │
│  └──────────────────────────────────┘    │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ 📤 Consegna su Google Drive      │    │
│  └──────────────────────────────────┘    │
└──────────────────────────────────────────┘
```

### Prerequisite Tooltip

When "Genera" is hovered but prerequisites aren't met:

```
  ┌─────────────────────────────────────┐
  │ Completa prima:                     │
  │ • Passo 5: Rischi                   │
  │ • Valutazione Rischi (P/D scores)   │
  └─────────────────────────────────────┘
```

---

## 14. MMC Assessment

**Route**: `/[lang]/assessments/[aziendaId]/mmc`

**Purpose**: NIOSH manual handling assessment per worker. Calculates PLR and IR with Green/Yellow/Red classification.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Valutazione MMC — Rossi Costruzioni SRL                             │
│  Movimentazione Manuale dei Carichi (Metodo NIOSH)                  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Seleziona lavoratore *                                       │   │
│  │ ┌─────────────────────────────────────────────────────────┐  │   │
│  │ │ BIANCHI MARCO — Magazziniere                         ▾  │  │   │
│  │ └─────────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  │ Sesso: M  │  Fascia Età: >18  │  CP (peso costante): 25 kg │   │
│  │                                   [Modifica CP]              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  SOLLEVAMENTO #1                              [+ Aggiungi Sollev.]  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  Altezza Origine (cm) *    Altezza Destinaz. (cm) *         │   │
│  │  ┌───────────────────┐     ┌───────────────────┐            │   │
│  │  │ 75                │     │ 125               │            │   │
│  │  └───────────────────┘     └───────────────────┘            │   │
│  │  A: Fattore altezza         B: Fattore dislocaz.            │   │
│  │  = 1.00                     = 0.93                          │   │
│  │                                                              │   │
│  │  Distanza Orizzontale (cm) *    Angolo Torsione (°) *      │   │
│  │  ┌───────────────────┐          ┌───────────────────┐       │   │
│  │  │ 30                │          │ 45                │       │   │
│  │  └───────────────────┘          └───────────────────┘       │   │
│  │  C: Fattore distanza            D: Fattore asimmetria      │   │
│  │  = 0.83                         = 0.86                     │   │
│  │                                                              │   │
│  │  Tipo di Presa *             Frequenza (sollevamenti/min) * │   │
│  │  ┌───────────────────┐      ┌───────────────────┐          │   │
│  │  │ Buona           ▾ │      │ 5                 │          │   │
│  │  └───────────────────┘      └───────────────────┘          │   │
│  │  E: Fattore presa              F: Fattore frequenza        │   │
│  │  = 1.00                        = 0.80                      │   │
│  │                                                              │   │
│  │  Durata Sollevamento *      Peso Effettivo (kg) *          │   │
│  │  ┌───────────────────┐      ┌───────────────────┐          │   │
│  │  │ ≤1 ora          ▾ │      │ 18                │          │   │
│  │  └───────────────────┘      └───────────────────┘          │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  RISULTATI                                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  PLR = CP × A × B × C × D × E × F                          │   │
│  │  PLR = 25 × 1.00 × 0.93 × 0.83 × 0.86 × 1.00 × 0.80      │   │
│  │  PLR = 13.28 kg                                              │   │
│  │                                                              │   │
│  │  IR = Peso Effettivo / PLR                                   │   │
│  │  IR = 18 / 13.28                                             │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │                                                      │   │   │
│  │  │          IR = 1.36  ██ NON ACCETTABILE               │   │   │
│  │  │                     (IR > 1.0 — Red)                 │   │   │
│  │  │                                                      │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  │  Classification:                                             │   │
│  │  ██ IR ≤ 0.75    Accettabile (Green)                        │   │
│  │  ██ 0.75 < IR ≤ 1.0  Da ridurre (Yellow)                   │   │
│  │  ██ IR > 1.0     Non accettabile (Red) ← ACTIVE            │   │
│  │                                                              │   │
│  │  ⚠ Misure obbligatorie richieste per IR > 1.0               │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │ Misure di prevenzione:                               │   │   │
│  │  │ ┌──────────────────────────────────────────────────┐ │   │   │
│  │  │ │ Ridurre il peso del carico, introdurre ausili    │ │   │   │
│  │  │ │ meccanici per il sollevamento...                 │ │   │   │
│  │  │ └──────────────────────────────────────────────────┘ │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### States

- **Empty**: No workers eligible for MMC → "Nessun lavoratore con mansioni di movimentazione carichi." + link to Step 2
- **Loading**: Skeleton for worker dropdown + form fields
- **Error**: Toast on calculation failure + "Riprova"
- **Populated**: Full form as shown above with real-time factor calculation

### Responsive

- Desktop: 2-column parameter layout as shown
- Tablet/Mobile: Single-column stacked parameters, results section full-width below

---

## 15. VDT Assessment

**Route**: `/[lang]/assessments/[aziendaId]/vdt`

**Purpose**: Display screen equipment hours per worker. Threshold: ≥20h/week = Exposed.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Valutazione VDT — Rossi Costruzioni SRL                             │
│  Videoterminali (D.Lgs. 81/2008, Titolo VII)                       │
│                                                    ┌──────────────┐ │
│                                                    │Importa da CSV│ │
│                                                    └──────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │NOMINATIVO     │MANSIONE       │ORE VDT/SETT.│CLASSIF.│SORV.│   │
│  ├───────────────┼───────────────┼─────────────┼────────┼─────┤   │
│  │MARCHETTI LUCA │IMP.-DOC. FORM │ [22]        │██ Esp. │ ✓   │   │
│  │               │               │             │        │5 ann│   │
│  ├───────────────┼───────────────┼─────────────┼────────┼─────┤   │
│  │CIARAMITARO A. │AMMINISTR.     │ [35]        │██ Esp. │ ✓   │   │
│  │               │               │             │        │2 ann│   │
│  ├───────────────┼───────────────┼─────────────┼────────┼─────┤   │
│  │BIANCHI MARCO  │MAGAZZINIERE   │ [4]         │Non esp.│ —   │   │
│  └───────────────┴───────────────┴─────────────┴────────┴─────┘   │
│                                                                      │
│  VDT Threshold: ≥20 ore/settimana = Esposto                        │
│  Sorveglianza sanitaria: ogni 5 anni (<50 anni), ogni 2 anni (≥50) │
│                                                                      │
│  VISITE IN SCADENZA                                                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ⚠ CIARAMITARO AMALIA — Prossima visita: 15/05/2026 (33 gg) │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### States

- **Empty**: No workers in survey → "Aggiungi prima i dipendenti nel Passo 2."
- **Loading**: Skeleton table rows
- **Error**: Toast on save failure
- **Populated**: Table with editable hours and auto-classification

### Responsive

- Desktop: Full table as shown
- Tablet/Mobile: Card view per worker (name, hours input, classification badge, surveillance status)

---

## 16. Stress Lavoro-Correlato

**Route**: `/[lang]/assessments/[aziendaId]/stress`

**Purpose**: INAIL checklist with ~76 SI/NO indicators across 3 areas. Real-time scoring.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Stress Lavoro-Correlato — Rossi Costruzioni SRL                    │
│  Metodo INAIL (Lista di Controllo)                                  │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ RISULTATO COMPLESSIVO                                       │    │
│  │                                                             │    │
│  │  Punteggio: 24 / 67            ██ RISCHIO MEDIO            │    │
│  │  ████████████████░░░░░░░░░░░░░░                             │    │
│  │                                                             │    │
│  │  Area A (Eventi sentinella): 3    0-17=Basso               │    │
│  │  Area B (Contesto del lavoro): 12  18-34=Medio  ← ATTIVO   │    │
│  │  Area C (Contenuto del lavoro): 9  ≥35=Alto                 │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ▼ AREA A — EVENTI SENTINELLA (3/5)                                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │ 1. Indici infortunistici                     SI ●──○ NO    │   │
│  │ 2. Assenze per malattia                      SI ○──● NO    │   │
│  │ 3. Ferie/permessi non goduti                 SI ●──○ NO    │   │
│  │ 4. Rotazione del personale                   SI ●──○ NO    │   │
│  │ 5. Turnover                                  SI ○──● NO    │   │
│  │ 6. Procedimenti/sanzioni disciplinari        SI ●──○ NO    │   │
│  │ 7. Richieste visite straordinarie            SI ○──● NO    │   │
│  │ 8. Segnalazioni stress lavoro                SI ●──○ NO    │   │
│  │ 9. Istanze giudiziarie                       SI ○──● NO    │   │
│  │ 10. Lamentele frequenti                      SI ●──○ NO    │   │
│  │ ...                                                         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ▶ AREA B — CONTESTO DEL LAVORO (12/26)                             │
│  (collapsed — click to expand)                                       │
│                                                                      │
│  ▶ AREA C — CONTENUTO DEL LAVORO (9/36)                             │
│  (collapsed — click to expand)                                       │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ MISURE CORRETTIVE                                            │   │
│  │                                                              │   │
│  │ Per livello "Medio" si suggeriscono:                         │   │
│  │ ☑ Indagine approfondita con questionari soggettivi           │   │
│  │ ☑ Interventi organizzativi mirati                            │   │
│  │ ☑ Formazione specifica per dirigenti e preposti              │   │
│  │ + Aggiungi misura                                            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌────────────────────────┐                                          │
│  │ Conferma Valutazione   │                                          │
│  └────────────────────────┘                                          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### States

- **Empty**: No indicators answered → all toggles default to NO, score shows 0
- **Loading**: Skeleton toggle rows
- **Error**: Toast on save failure; draft restored from auto-save
- **Populated**: Toggles with real-time scoring; "Conferma Valutazione" blocked until all indicators answered
- **Incomplete**: If user clicks "Conferma" with unanswered items: unanswered indicators highlighted amber, action blocked

### Responsive

- Desktop: Full-width accordion as shown
- Tablet/Mobile: Same accordion layout (single-column by nature), toggle labels may wrap

---

## 17. Gestanti

**Route**: `/[lang]/assessments/[aziendaId]/gestanti`

**Purpose**: Cross-reference female worker roles against D.Lgs. 151/2001 incompatible risk factors.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Valutazione Gestanti — Rossi Costruzioni SRL                        │
│  Tutela lavoratrici madri (D.Lgs. 151/2001)                        │
│                                                                      │
│  LAVORATRICI                                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │NOMINATIVO       │MANSIONE      │RISCHI INCOMPAT.│ESITO      │   │
│  ├─────────────────┼──────────────┼────────────────┼───────────┤   │
│  │CIARAMITARO A.   │AMMINISTR.    │ 0 rischi       │✅ Nessun   │   │
│  │                 │              │                │rischio    │   │
│  ├─────────────────┼──────────────┼────────────────┼───────────┤   │
│  │ROSSI GIULIA     │OPERAIA       │ 3 rischi       │⚠ Incomp.  │   │
│  │                 │MAGAZZINO     │                │           │   │
│  │                 │              │ • Sollevamento  │           │   │
│  │                 │              │   carichi >3kg  │           │   │
│  │                 │              │ • Esposizione   │           │   │
│  │                 │              │   solventi      │           │   │
│  │                 │              │ • Stazione      │           │   │
│  │                 │              │   eretta >50%   │           │   │
│  │                 │              │                │           │   │
│  │                 │ PROPOSTA RICOLLOCAZIONE:       │           │   │
│  │                 │ → Ufficio Amministrativo       │           │   │
│  │                 │ [Accetta] [Rifiuta]            │           │   │
│  └─────────────────┴──────────────┴────────────────┴───────────┘   │
│                                                                      │
│  Only female workers from Step 2 are shown here.                    │
│  Risk cross-reference runs automatically from survey data.          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### States

- **Empty**: No female workers in survey → "Nessuna lavoratrice registrata. L'allegato gestanti non è necessario."
- **Loading**: Skeleton table rows
- **No risks**: All workers show green "Nessun rischio identificato"
- **With risks**: Incompatible workers show amber with relocation proposals

### Responsive

- Desktop: Table as shown
- Tablet/Mobile: Card per worker with risk details and actions stacked

---

## 18. Rischio Incendio

**Route**: `/[lang]/assessments/[aziendaId]/incendio`

**Purpose**: Fire risk per homogeneous area. INF + SI + PI scoring (1-3 each).

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Valutazione Rischio Incendio — Rossi Costruzioni SRL               │
│  Metodo D.M. 03/09/2021                       [+ Aggiungi Area]    │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ UFFICIO AMMINISTRATIVO — 50 mq                    [Duplica] │   │
│  │                                                              │   │
│  │  INF (Infiammabilità) *   SI (Sorgenti Igniz.) *            │   │
│  │  ┌─────┐                  ┌─────┐                           │   │
│  │  │  1  │  Bassa           │  2  │  Media                   │   │
│  │  └─────┘                  └─────┘                           │   │
│  │                                                              │   │
│  │  PI (Persone in Pericolo) *                                  │   │
│  │  ┌─────┐                                                    │   │
│  │  │  1  │  Bassa                                             │   │
│  │  └─────┘                                                    │   │
│  │                                                              │   │
│  │  RISULTATO:  INF + SI + PI = 1 + 2 + 1 = 4                 │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │          LIVELLO: ██ BASSO (3-4)                     │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  │  Misure richieste per livello BASSO:                         │   │
│  │  ☑ Estintori portatili conformi                              │   │
│  │  ☑ Cartellonistica di emergenza                              │   │
│  │  ☑ Piano di evacuazione semplificato                         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ MAGAZZINO PRINCIPALE — 150 mq                     [Duplica] │   │
│  │                                                              │   │
│  │  INF: [2]    SI: [2]    PI: [2]                             │   │
│  │                                                              │   │
│  │  RISULTATO: 2 + 2 + 2 = 6                                   │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │          LIVELLO: ██ MEDIO (5-7)                     │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Classification:                                                     │
│  ██ BASSO  (3-4)   — Misure standard                                │
│  ██ MEDIO  (5-7)   — Misure aggiuntive richieste                    │
│  ██ ALTO   (8-9)   — Valutazione approfondita VVF richiesta        │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### States

- **Empty**: No environments defined → "Aggiungi prima gli ambienti nel Passo 3."
- **Loading**: Skeleton for area cards
- **Populated**: Area cards with INF/SI/PI inputs and live classification
- **Validation**: Value outside 1-3 rejected with tooltip "Valore consentito: 1-3"

### Responsive

- Desktop: Area cards stacked vertically as shown
- Tablet/Mobile: Same layout (single-column by nature), inputs stacked within each card

---

## 19. Microclima

**Route**: `/[lang]/assessments/[aziendaId]/microclima`

**Purpose**: Thermal comfort (PMV/PPD for moderate environments, PHS for severe heat).

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Valutazione Microclima — Rossi Costruzioni SRL                      │
│  Comfort Termico (UNI EN ISO 7730 / 7933)                           │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │ Ufficio Amm. │ Magazzino │ Sala Corsi │ Spogliatoio │     │     │
│  │ ▔▔▔▔▔▔▔▔▔▔▔▔                                        │     │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                      │
│  UFFICIO AMMINISTRATIVO        Modalità: ● Moderato  ○ Caldo Severo│
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ PARAMETRI AMBIENTALI (6 parametri UNI EN ISO 7730)          │   │
│  │                                                              │   │
│  │  Temp. Aria (°C) *           Temp. Radiante Media (°C) *    │   │
│  │  ┌───────────────┐           ┌───────────────┐              │   │
│  │  │ 22.5          │           │ 23.0          │              │   │
│  │  └───────────────┘           └───────────────┘              │   │
│  │                                                              │   │
│  │  Velocità Aria (m/s) *       Umidità Relativa (%) *         │   │
│  │  ┌───────────────┐           ┌───────────────┐              │   │
│  │  │ 0.1           │           │ 50            │              │   │
│  │  └───────────────┘           └───────────────┘              │   │
│  │                                                              │   │
│  │  Tasso Metabolico (met) *    Isolamento Vestiario (clo) *   │   │
│  │  ┌───────────────┐           ┌───────────────┐              │   │
│  │  │ 1.2           │           │ 0.8           │              │   │
│  │  └───────────────┘           └───────────────┘              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  RISULTATI PMV/PPD                                                   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  PMV = -0.2       PPD = 5.8%                                │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │        COMFORT: ██ Leggermente fresco               │   │   │
│  │  │                    (Accettabile)                     │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  │  PMV Scale:                                                  │   │
│  │  -3      -2      -1      0      +1      +2      +3          │   │
│  │  Freddo  Fresco  Legg.  Neutro  Legg.  Caldo   Molto       │   │
│  │                  fresco         caldo          caldo         │   │
│  │                          ▲                                   │   │
│  │                        -0.2                                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  PHS MODE (when "Caldo Severo" is selected):                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Additional parameters (ISO 7933):                           │   │
│  │  Durata esposizione (min) *     Postura *                    │   │
│  │  ┌───────────────┐              ┌───────────────┐            │   │
│  │  │ 120           │              │ In piedi    ▾ │            │   │
│  │  └───────────────┘              └───────────────┘            │   │
│  │                                                              │   │
│  │  RISULTATI PHS:                                              │   │
│  │  Dlim (max esposizione): 45 min                              │   │
│  │  Temperatura corporea: 38.2°C                                │   │
│  │  Perdita idrica: 1.8 L                                       │   │
│  │                                                              │   │
│  │  ⚠ Dlim < 30 min → red banner:                              │   │
│  │  "Esposizione critica — misure obbligatorie"                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### States

- **Empty**: No environments → "Aggiungi prima gli ambienti nel Passo 3."
- **Loading**: Skeleton for parameter inputs
- **Populated**: Full parameter form with real-time PMV/PPD
- **Validation**: Out-of-range values rejected with physical range tooltip

### Responsive

- Desktop: 2-column parameter layout + results panel side-by-side
- Tablet/Mobile: Single-column parameters, results below

---

## 20. Rischio Biologico

**Route**: `/[lang]/assessments/[aziendaId]/biologico`

**Purpose**: Sector-specific biological risk assessment with pre-loaded agents and prevention measures.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Valutazione Rischio Biologico — Rossi Costruzioni SRL              │
│                                                                      │
│  Settore *                                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Asilo nido                                               ▾ │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  Options: Asilo nido, Alimentare, Dentisti, Altro                   │
│                                                                      │
│  AGENTI BIOLOGICI (pre-populated for sector)                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │AGENTE BIOLOGICO  │GRUPPO│VIA TRASMISSIONE│PATOLOGIA  │AZIONI│   │
│  ├──────────────────┼──────┼────────────────┼───────────┼──────┤   │
│  │Virus respiratori │  2   │Aerea, contatto │Influenza, │  ✏   │   │
│  │(influenza, RSV)  │      │diretto         │bronchite  │      │   │
│  ├──────────────────┼──────┼────────────────┼───────────┼──────┤   │
│  │Batteri intestinali│  2   │Oro-fecale     │Gastroent. │  ✏   │   │
│  │(Salmonella, etc.) │      │               │           │      │   │
│  ├──────────────────┼──────┼────────────────┼───────────┼──────┤   │
│  │Parassiti (pidocchi│  1   │Contatto diretto│Pediculosi│  ✏   │   │
│  │ scabbia)          │      │               │           │      │   │
│  └──────────────────┴──────┴────────────────┴───────────┴──────┘   │
│  [+ Aggiungi agente]                                                 │
│                                                                      │
│  When sector = "Altro":                                              │
│  "Nessun agente pre-caricato per questo settore.                    │
│   Inserisci manualmente gli agenti e le misure."                    │
│  (empty editable table + "Aggiungi agente" button)                  │
│                                                                      │
│  MISURE DI PREVENZIONE (pre-populated)                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ☑ Lavaggio mani frequente con sapone antibatterico           │   │
│  │ ☑ Utilizzo guanti monouso per cambio pannolini               │   │
│  │ ☑ Disinfezione superfici e giocattoli quotidiana             │   │
│  │ ☑ Vaccinazione raccomandata per operatori                    │   │
│  │ ☑ Protocollo gestione malattie infettive                     │   │
│  │ [+ Aggiungi misura]                                          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### States

- **Empty**: No sector selected → "Seleziona un settore per caricare gli agenti biologici."
- **Loading**: Skeleton for agents table + measures list
- **Populated**: Pre-loaded agents/measures for selected sector
- **"Altro" sector**: Empty editable lists as described above

### Responsive

- Desktop: Table + measures as shown
- Tablet/Mobile: Agents as cards with stacked fields; measures as checklist

---

## 21. PEE

**Route**: `/[lang]/documents/[aziendaId]/pee`

**Purpose**: Emergency plan generation with auto-populated data from DVR.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Piano di Emergenza ed Evacuazione — Rossi Costruzioni SRL          │
│  Prerequisito: DVR Master ✅                                         │
│                                                                      │
│  DATI AUTO-COMPILATI DAL DVR                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Azienda:      Rossi Costruzioni SRL (read-only from DVR)    │   │
│  │ Ambienti:     4 (auto-loaded)                               │   │
│  │ Squadra emergenza:                                           │   │
│  │   Primo Soccorso: Ciaramitaro A.                            │   │
│  │   Antincendio: Ciaramitaro A., Bianchi M.                   │   │
│  │ Punto di raccolta: ______________________ (manual entry)    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  PLANIMETRIA                                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  📷 Trascina la planimetria qui o clicca per caricare        │   │
│  │  (oppure) ☐ Inserire planimetria — placeholder nel documento│   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  PROCEDURE DI EMERGENZA                                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ▼ Incendio (Procedura A-E)                     [Reset std.] │   │
│  │   A. Rilevamento: ...editable...                             │   │
│  │   B. Allarme: ...editable...                                 │   │
│  │   C. Evacuazione: ...editable...                             │   │
│  │   D. Chiamata VVF: ...editable...                            │   │
│  │   E. Verifica presenze: ...editable...                       │   │
│  │                                                              │   │
│  │ ▶ Terremoto (standard template)                              │   │
│  │ ▶ Allagamento (standard template)                            │   │
│  │ ▶ Fuga di Gas (standard template)                            │   │
│  │ ▶ Evacuazione Generale (standard template)                   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  VARIANTE PEE                                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  ● Azienda (dipendenti, primo soccorso dettagliato)         │   │
│  │  ○ Comune/Evento (volontari, procedura RCP, pubblico)       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  Switching to "Comune/Evento" replaces employee-based fields       │
│  with volunteer roster, public capacity, and RCP procedures.       │
│                                                                      │
│  ┌────────────────┐                                                  │
│  │ Genera PEE     │                                                  │
│  └────────────────┘                                                  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### States

- **Prerequisite not met**: DVR not generated → "Genera prima il DVR Master" with link to Documents page
- **Empty**: DVR exists but no emergency team assigned → "Assegna i ruoli di primo soccorso e antincendio nel Passo 2."
- **Loading**: Skeleton for auto-populated fields
- **Populated**: Full form as shown with editable procedures

### Responsive

- Desktop: Form as shown
- Tablet/Mobile: Single-column layout, procedure accordions full-width

---

## 22. HACCP

**Route**: `/[lang]/documents/[aziendaId]/haccp`

**Purpose**: HACCP manual with CCP analysis + 16 self-check forms (SA-01 to SA-16).

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  HACCP Manuale Autocontrollo — Rossi Costruzioni SRL                │
│                                                                      │
│  Tipo Attività Alimentare *                                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Ristorante con cucina                                    ▾ │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  Options: Ristorante, Bar, Pasticceria, Macelleria, Mensa, Altro   │
│                                                                      │
│  CCP (Punti Critici di Controllo) — pre-loaded for activity type    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ CCP │ FASE         │ LIMITE CRITICO      │ MONITORAGGIO     │   │
│  ├─────┼──────────────┼─────────────────────┼──────────────────┤   │
│  │ 1   │ Cottura      │ T ≥ 75°C al cuore   │ Termometro sonda │   │
│  │ 2   │ Conservazione│ T ≤ 4°C (frigo)     │ Reg. giornaliero │   │
│  │ 3   │ Scongelamento│ T ≤ 4°C, 24h max    │ Ispezione visiva │   │
│  │ 4   │ Servizio     │ T ≥ 65°C (caldo)    │ Termometro       │   │
│  └─────┴──────────────┴─────────────────────┴──────────────────┘   │
│  [+ Aggiungi CCP]                                                    │
│                                                                      │
│  SCHEDE DI AUTOCONTROLLO (SA-01 to SA-16)                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ☑ SA-01 Ricezione merci            ☑ SA-09 Pest control     │   │
│  │ ☑ SA-02 Stoccaggio                 ☑ SA-10 Formazione       │   │
│  │ ☑ SA-03 Preparazione               ☑ SA-11 Manutenzione     │   │
│  │ ☑ SA-04 Cottura                    ☑ SA-12 Approvvig.       │   │
│  │ ☑ SA-05 Raffreddamento             ☑ SA-13 Rintracciab.     │   │
│  │ ☑ SA-06 Conservazione              ☑ SA-14 Non conformità   │   │
│  │ ☑ SA-07 Distribuzione              ☑ SA-15 Reclami          │   │
│  │ ☑ SA-08 Pulizia e sanificazione    ☑ SA-16 Revisione        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  Deselect forms you don't need.                                     │
│                                                                      │
│  ┌────────────────┐  ┌──────────────────────────┐                   │
│  │ Genera Manuale │  │ Genera Schede (ZIP) 📦    │                   │
│  └────────────────┘  └──────────────────────────┘                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### States

- **Empty**: No food activity selected → "Seleziona il tipo di attività alimentare."
- **Loading**: Skeleton for CCP table
- **Populated**: Pre-loaded CCPs + selectable forms
- **Regeneration warning**: If activity type changed after generation → "Le personalizzazioni CCP potrebbero essere sovrascritte. Unire le modifiche?"

### Responsive

- Desktop: CCP table + form checkboxes as shown
- Tablet/Mobile: CCP entries as cards; forms as 2-column checkbox grid

---

## 23. DUVRI

**Route**: `/[lang]/documents/[aziendaId]/duvri`

**Purpose**: Contractor interference risk document. Principal data auto-filled from DVR, contractor data entered manually.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DUVRI — Rossi Costruzioni SRL                                      │
│                                                                      │
│  COMMITTENTE (auto-compilato dal DVR — read-only)                   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Ragione Sociale:  Rossi Costruzioni SRL                  🔒  │   │
│  │ Sede:             Via Roma 15, Milano (MI)               🔒  │   │
│  │ RSPP:             Marchetti Luca                         🔒  │   │
│  │ DdL:              Ciaramitaro Amalia                     🔒  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  APPALTATORI                                    [+ Aggiungi Appalt.] │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ▼ IMPRESA PULIZIE SRL                                        │   │
│  │   Sede: Via Verdi 8, Milano                                  │   │
│  │   Oggetto appalto: Pulizie uffici e magazzino                │   │
│  │   Durata: 01/01/2026 — 31/12/2026                           │   │
│  │   Attrezzature: Lavasciuga, aspirapolvere, prodotti chimici  │   │
│  │                                                              │   │
│  │ ▶ MANUTENZIONE IMPIANTI SpA                                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ANALISI INTERFERENZE                                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │COMBINAZIONE       │RISCHIO INTERF.│MISURA PREVENZ. │AZIONE  │   │
│  ├───────────────────┼───────────────┼────────────────┼────────┤   │
│  │Lavasciuga +       │Scivolamento su│Segnaletica "pav│Accetta │   │
│  │transito persone   │pav. bagnato   │bagnato", orari │Rifiuta │   │
│  ├───────────────────┼───────────────┼────────────────┼────────┤   │
│  │Prod. chimici +    │Inalazione     │Ventilazione    │Accetta │   │
│  │presenza lavoratori│               │meccanica, DPI  │Rifiuta │   │
│  └───────────────────┴───────────────┴────────────────┴────────┘   │
│                                                                      │
│  NESSUNA INTERFERENZA STATE:                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Nessuna interferenza rilevata tra le attrezzature.          │   │
│  │  [+ Aggiungi interferenza manualmente]                       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌────────────────┐                                                  │
│  │ Genera DUVRI   │                                                  │
│  └────────────────┘                                                  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### States

- **Prerequisite not met**: No DVR → "Genera prima il DVR Master"
- **Empty**: No contractors added → "Aggiungi almeno un appaltatore."
- **Loading**: Skeleton for principal data + contractor sections
- **Populated**: Principal (read-only) + contractors + interference analysis
- **DVR updated**: Banner: "Dati committente aggiornati dal DVR" when principal data changed

### Responsive

- Desktop: Form as shown
- Tablet/Mobile: Principal card stacked, contractor accordions, interference table as cards

---

## 24. POS

**Route**: `/[lang]/documents/[aziendaId]/pos`

**Purpose**: Construction site safety plan. The most complex document — phases, risks, NIOSH, noise/vibration, DPI matrix.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  POS — Rossi Costruzioni SRL                                        │
│  Piano Operativo di Sicurezza                                       │
│                                                                      │
│  FASI DI LAVORO                          [+ Aggiungi Fase]          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  ≡ 1. Scavo                                          ✏ 🗑   │   │
│  │     Rischi: 5 │ NIOSH: 2 valutazioni │ Rumore: 82 dB(A)    │   │
│  │  ≡ 2. Getto calcestruzzo                             ✏ 🗑   │   │
│  │     Rischi: 3 │ NIOSH: 1 valutazione │ Rumore: 88 dB(A)    │   │
│  │  ≡ 3. Montaggio impalcature                          ✏ 🗑   │   │
│  │     Rischi: 8 │ NIOSH: 0 │ Rumore: 75 dB(A)                │   │
│  │     Dipende da: Fase 1 (Scavo) ⚡                            │   │
│  │  ≡ 4. Demolizione parziale                           ✏ 🗑   │   │
│  │     Rischi: 6 │ NIOSH: 1 │ Vibr: HAV 4.2 m/s²              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  (≡ = drag handle for reordering)                                    │
│                                                                      │
│  MATRICE MANSIONE / DPI                                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │           │Casco│Scarpe│Guanti│Imbrag.│Occhiali│Cuffie│     │   │
│  ├───────────┼─────┼──────┼──────┼───────┼────────┼──────┤     │   │
│  │Carpentiere│  ✓  │  ✓   │  ✓   │  ✓    │   ✓    │  ✓   │     │   │
│  │Manovale   │  ✓  │  ✓   │  ✓   │  —    │   —    │  ✓   │     │   │
│  │Gruista    │  ✓  │  ✓   │  ✓   │  —    │   —    │  ✓   │     │   │
│  │Elettricis.│  ✓  │  ✓   │  ✓*  │  —    │   ✓    │  —   │     │   │
│  └───────────┴─────┴──────┴──────┴───────┴────────┴──────┘     │   │
│  * = specialized (guanti isolanti)                                   │
│  DPI auto-suggested per role, inline-editable per cell.             │
│                                                                      │
│  ┌────────────────┐                                                  │
│  │ Genera POS     │                                                  │
│  └────────────────┘                                                  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### States

- **Empty**: No phases defined → "Aggiungi almeno una fase di lavoro."
- **Loading**: Skeleton for phase list + DPI matrix
- **Populated**: Drag-and-drop phases + filled DPI matrix

### Responsive

- Desktop: Phase list + DPI matrix as shown
- Tablet/Mobile: Phase cards stacked; DPI matrix scrolls horizontally

---

## 25. Settings

**Route**: `/[lang]/settings`

**Purpose**: Application configuration — user profile, organization, theme, reference data management.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Impostazioni                                                        │
│                                                                      │
│  ┌────────────────┬──────────────────────────────────────────────┐  │
│  │ SIDEBAR TABS   │ CONTENT                                      │  │
│  │                │                                              │  │
│  │ ▶ Profilo      │  PROFILO UTENTE                              │  │
│  │   Organiz.     │                                              │  │
│  │   Utenti       │  Nome:  Marchetti Luca                      │  │
│  │   Aspetto      │  Email: luca@n2o.it                         │  │
│  │   Lingua       │  Ruolo: Amministratore                      │  │
│  │   Libreria     │                                              │  │
│  │   Rischi       │  ┌────────────────────────────────────────┐  │  │
│  │   Template     │  │ Cambia Password                       │  │  │
│  │   AI           │  └────────────────────────────────────────┘  │  │
│  │   Backup       │                                              │  │
│  │                │  ASPETTO                                     │  │
│  │                │  ┌──────────┐ ┌──────────┐                  │  │
│  │                │  │ 🌙 Scuro  │ │ ☀ Chiaro │                  │  │
│  │                │  │ (active) │ │          │                  │  │
│  │                │  └──────────┘ └──────────┘                  │  │
│  │                │                                              │  │
│  │                │  LINGUA INTERFACCIA                          │  │
│  │                │  ● Italiano  ○ English                      │  │
│  │                │                                              │  │
│  │                │  GESTIONE UTENTI (Admin only)                │  │
│  │                │  ┌────────────────────────────────────────┐  │  │
│  │                │  │User           │Role         │Actions  │  │  │
│  │                │  │Marchetti L.   │Admin        │ ✏       │  │  │
│  │                │  │Ciaramitaro A. │Op. Ufficio  │ ✏ 🗑    │  │  │
│  │                │  │Bianchi M.     │Op. Campo    │ ✏ 🗑    │  │  │
│  │                │  └────────────────────────────────────────┘  │  │
│  │                │  [+ Invita Utente]                           │  │
│  │                │                                              │  │
│  └────────────────┴──────────────────────────────────────────────┘  │
│                                                                      │
│  Additional Settings Tabs:                                           │
│  - Libreria Rischi: Add/edit/remove standard risks per env type     │
│  - Template: Upload custom .docx templates, set per-client branding │
│  - AI Prompts: Edit system prompts for company description,         │
│    improvement measures, SDS extraction                              │
│  - Backup: View backup status, restore point, retention window      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### States

- **Loading**: Skeleton for user table + settings fields
- **Non-admin**: "Gestione Utenti" and "Invita Utente" hidden. Only Profilo, Aspetto, Lingua visible.
- **Populated**: Full settings as shown (admin view)

---

## 26. Role-Based Access Matrix

Every screen adapts based on the authenticated user's role. Actions not listed for a role are **hidden** (not disabled).

| Screen | Admin | Operatore Ufficio | Operatore Campo |
|--------|-------|-------------------|-----------------|
| Dashboard | Full access. "Nuova Azienda", "Elimina" visible | Full access. "Nuova Azienda" visible, "Elimina" hidden | Read-only. No "Nuova Azienda" or "Elimina" |
| Survey (Steps 1-7) | Full edit | Full edit | Full edit + photo/SDS upload |
| Risk Scoring | Full edit P/D + AI suggestions | Full edit P/D + AI suggestions | **Read-only** (view scores, no editing) |
| Document Generation | Generate, download, deliver all docs | Generate, download, deliver all docs | **Download only** (no generate/deliver) |
| Assessments (Phase 3) | Full edit all assessments | Full edit all assessments | **Read-only** view |
| Documents (Phase 4) | Full edit + generate | Full edit + generate | **Read-only** view |
| Settings: Profilo | Own profile only | Own profile only | Own profile only |
| Settings: Utenti | Full CRUD + invite | Hidden | Hidden |
| Settings: Libreria/Template/AI | Full CRUD | Read-only | Hidden |
| Settings: Backup | View + restore | Hidden | Hidden |

### Role Badge in Sidebar

```
  ┌────────┐
  │ 👤 User│
  │ Name   │
  │ ██ Role│  ← Badge: Admin (blue), Op. Ufficio (green), Op. Campo (amber)
  └────────┘
```

### Permission Denied

When a restricted action is accessed directly via URL:
- Toast: "Non hai i permessi per questa azione."
- Redirect to Dashboard

---

## 27. Reusable Component Patterns

These patterns appear across multiple screens and should be built as shared components.

### Status Badge

```
  ┌────────────┐
  │ ██ Bozza   │  Gray bg/text
  └────────────┘
  ┌────────────┐
  │ ██ In Corso│  Amber bg/text
  └────────────┘
  ┌────────────┐
  │ ██ Inviato │  Blue bg/text
  └────────────┘
  ┌──────────────┐
  │ ██ Completato│  Green bg/text
  └──────────────┘
  ┌────────────┐
  │ ██ Errore  │  Red bg/text
  └────────────┘
```

### Empty State

```
  ┌──────────────────────────────────────┐
  │                                      │
  │          [Lucide Icon 48px]          │
  │                                      │
  │     Italian message text             │
  │                                      │
  │     ┌──────────────────┐             │
  │     │  Primary CTA     │             │
  │     └──────────────────┘             │
  │                                      │
  └──────────────────────────────────────┘
```

### Loading Skeleton

```
  KPI Card Skeleton:          Table Row Skeleton:
  ┌──────────┐                ┌────────┬──────┬─────┬────┐
  │ ░░░░░░░  │                │ ░░░░░░ │ ░░░░ │ ░░░ │ ░░ │
  │ ░░░░░    │                │ ░░░░░░ │ ░░░░ │ ░░░ │ ░░ │
  │ ░░░░░░░░ │                │ ░░░░░░ │ ░░░░ │ ░░░ │ ░░ │
  └──────────┘                └────────┴──────┴─────┴────┘
```

### Toast Notifications

```
  Position: Bottom-right
  Auto-dismiss: 5 seconds

  ┌──────────────────────────────────┐
  │ ✅ Salvato con successo          │  Success (green accent)
  └──────────────────────────────────┘

  ┌──────────────────────────────────┐
  │ ❌ Errore di connessione.        │  Error (red accent)
  │    [Riprova]                     │
  └──────────────────────────────────┘

  ┌──────────────────────────────────┐
  │ ℹ DVR Master generato.          │  Info (blue accent)
  └──────────────────────────────────┘

  ┌──────────────────────────────────┐
  │ ⚠ Modifiche non salvate.        │  Warning (amber accent)
  └──────────────────────────────────┘
```

### Confirmation Dialog

```
  ┌──────────────────────────────────┐
  │  Title                        ✕  │
  │                                  │
  │  Descriptive message text        │
  │                                  │
  │       ┌─────────┐ ┌─────────┐   │
  │       │ Annulla │ │ Action  │   │
  │       └─────────┘ └─────────┘   │
  └──────────────────────────────────┘
```

### AI Content Indicator

```
  AI-generated content has:
  - Left border in primary/info color (4px)
  - Small "🤖 AI" badge above the content
  - Fully editable
  - On edit: badge changes to "Revisionato" with editor's name
  - On full rewrite: badge disappears entirely

  ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐
  ┃ 🤖 AI                            │
  ┃ Content generated by AI appears   │
  ┃ here with a blue left border...   │
  └─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘
```

### Risk Level Color System

Used across Risk Scoring, MMC, Fire Risk, and VDT:

```
  ┌──────────────────────────────────────────────────┐
  │  Context    │  Green     │  Yellow  │ Orange │ Red  │
  ├─────────────┼────────────┼─────────┼────────┼──────┤
  │  DVR Risk   │ I=3-4      │ I=5-6   │ I=7-8  │I=9-12│
  │  Index      │ Accettab.  │ Modesto │ Grave  │Gravis│
  ├─────────────┼────────────┼─────────┼────────┼──────┤
  │  NIOSH IR   │ IR ≤ 0.75  │0.75-1.0 │  —     │IR>1.0│
  │             │ Accettab.  │Da ridurre│       │Non acc│
  ├─────────────┼────────────┼─────────┼────────┼──────┤
  │  Fire Risk  │ Sum 3-4    │Sum 5-7  │  —     │Sum 8-9│
  │             │ Basso      │ Medio   │        │ Alto  │
  ├─────────────┼────────────┼─────────┼────────┼──────┤
  │  Stress     │ 0-17       │ 18-34   │  —     │ ≥35   │
  │             │ Basso      │ Medio   │        │ Alto  │
  └─────────────┴────────────┴─────────┴────────┴──────┘
```

### Auto-Save Indicator

```
  Header area, near page title:

  Saving:   ● Salvataggio...    (spinner + text, primary color)
  Saved:    ✓ Salvato           (appears, fades out after 3s)
  Error:    ✗ Errore di salvataggio [Riprova]  (persists, red)
  Offline:  ⚡ Non in linea — salvataggio locale  (persists, amber)
```

### Responsive Form Grid

```
  Desktop (≥1024px):            Mobile/Tablet (<1024px):
  ┌──────────┐ ┌──────────┐    ┌──────────────────────┐
  │ Field A  │ │ Field B  │    │ Field A              │
  └──────────┘ └──────────┘    └──────────────────────┘
  ┌──────────┐ ┌──────────┐    ┌──────────────────────┐
  │ Field C  │ │ Field D  │    │ Field B              │
  └──────────┘ └──────────┘    └──────────────────────┘
                               ┌──────────────────────┐
                               │ Field C              │
                               └──────────────────────┘
                               ┌──────────────────────┐
                               │ Field D              │
                               └──────────────────────┘
```

---

## Screen Inventory Summary

| # | Screen | Route | Phase | Wireframe Section |
|---|--------|-------|-------|-------------------|
| 1 | Login | `/[lang]/login` | 2 | [Section 2](#2-login) |
| 2 | Dashboard | `/[lang]/dashboard` | 2 | [Section 3](#3-dashboard) |
| 3 | Survey: Azienda | `/[lang]/survey/[aziendaId]` step 1 | 2 | [Section 5](#5-step-1-azienda) |
| 4 | Survey: Persone | `/[lang]/survey/[aziendaId]` step 2 | 2 | [Section 6](#6-step-2-persone) |
| 5 | Survey: Ambienti | `/[lang]/survey/[aziendaId]` step 3 | 2 | [Section 7](#7-step-3-ambienti) |
| 6 | Survey: Attrezzature | `/[lang]/survey/[aziendaId]` step 4 | 2 | [Section 8](#8-step-4-attrezzature) |
| 7 | Survey: Rischi | `/[lang]/survey/[aziendaId]` step 5 | 2 | [Section 9](#9-step-5-rischi) |
| 8 | Survey: Sost. Chimiche | `/[lang]/survey/[aziendaId]` step 6 | 2 | [Section 10](#10-step-6-sostanze-chimiche) |
| 9 | Survey: Riepilogo | `/[lang]/survey/[aziendaId]` step 7 | 2 | [Section 11](#11-step-7-riepilogo) |
| 10 | Risk Scoring | `/[lang]/risk-scoring/[aziendaId]` | 2 | [Section 12](#12-risk-scoring-interface) |
| 11 | Document Generation | `/[lang]/documents/[aziendaId]` | 2 | [Section 13](#13-document-generation) |
| 12 | MMC Assessment | `/[lang]/assessments/[aziendaId]/mmc` | 3 | [Section 14](#14-mmc-assessment) |
| 13 | VDT Assessment | `/[lang]/assessments/[aziendaId]/vdt` | 3 | [Section 15](#15-vdt-assessment) |
| 14 | Stress Assessment | `/[lang]/assessments/[aziendaId]/stress` | 3 | [Section 16](#16-stress-lavoro-correlato) |
| 15 | Gestanti | `/[lang]/assessments/[aziendaId]/gestanti` | 3 | [Section 17](#17-gestanti) |
| 16 | Rischio Incendio | `/[lang]/assessments/[aziendaId]/incendio` | 3 | [Section 18](#18-rischio-incendio) |
| 17 | Microclima | `/[lang]/assessments/[aziendaId]/microclima` | 3 | [Section 19](#19-microclima) |
| 18 | Rischio Biologico | `/[lang]/assessments/[aziendaId]/biologico` | 3 | [Section 20](#20-rischio-biologico) |
| 19 | PEE (Azienda) | `/[lang]/documents/[aziendaId]/pee` | 4 | [Section 21](#21-pee) |
| 20 | PEE (Comune/Evento) | `/[lang]/documents/[aziendaId]/pee?variant=comune` | 4 | [Section 21](#21-pee) |
| 21 | HACCP | `/[lang]/documents/[aziendaId]/haccp` | 4 | [Section 22](#22-haccp) |
| 22 | DUVRI | `/[lang]/documents/[aziendaId]/duvri` | 4 | [Section 23](#23-duvri) |
| 23 | POS | `/[lang]/documents/[aziendaId]/pos` | 4 | [Section 24](#24-pos) |
| 24 | Settings | `/[lang]/settings` | 5 | [Section 25](#25-settings) |

**Total: 24 screens** (including PEE variant) covering all 16 document types, the complete 7-step survey wizard, risk scoring, role-based access, and admin functions.

---

*© 2026 Niuexa. Confidential — prepared for N2O SRL.*
