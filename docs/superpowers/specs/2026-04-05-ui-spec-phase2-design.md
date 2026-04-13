# UI Specification — Phase 2 (Core Development)

**Version**: 1.0
**Date**: 2026-04-05
**Scope**: Dashboard, Survey Wizard (7 steps), Risk Scoring, Document Generation
**Design Direction**: Design-agnostic (colors/fonts deferred). Layout, interactions, and rules only.
**AntiGravity Framework**: Integrated where applicable (spacing grid, animation timing, anti-patterns, accessibility).

---

## Table of Contents

1. [Global Patterns](#1-global-patterns)
2. [Dashboard](#2-dashboard)
3. [Survey Wizard Shell](#3-survey-wizard-shell)
4. [Step 1: Azienda (Company)](#4-step-1-azienda)
5. [Step 2: Persone (Employees)](#5-step-2-persone)
6. [Step 3: Ambienti (Environments)](#6-step-3-ambienti)
7. [Step 4: Attrezzature (Equipment)](#7-step-4-attrezzature)
8. [Step 5: Rischi (Risk Checklist)](#8-step-5-rischi)
9. [Step 6: Sostanze Chimiche (SDS Extraction)](#9-step-6-sostanze-chimiche)
10. [Step 7: Riepilogo (Summary + Signature)](#10-step-7-riepilogo)
11. [Risk Scoring Interface](#11-risk-scoring-interface)
12. [Document Generation](#12-document-generation)
13. [Form Validation Rules](#13-form-validation-rules)

---

## 1. Global Patterns

### 1.1 Navigation Shell

**Layout**: Fixed sidebar (256px) + scrollable main content + sticky top header (64px).

**Sidebar**:
- App logo at top
- Nav items with Lucide thin-stroke icons + Italian labels:
  - Dashboard (LayoutDashboard) → `/[lang]/dashboard`
  - Sopralluogo (ClipboardList) → `/[lang]/survey/[aziendaId]` — badge: active survey count
  - Valutazione Rischi (ShieldAlert) → `/[lang]/risk-scoring/[aziendaId]`
  - Documenti (FileStack) → `/[lang]/documents/[aziendaId]` — badge: ready doc count
  - Valutazioni (FlaskConical) → `/[lang]/assessments/[aziendaId]` — Phase 3 assessments
  - Impostazioni (Settings) → `/[lang]/settings`
- **Sidebar state**: Company-specific routes (Sopralluogo through Valutazioni) are disabled/hidden until a company is selected from Dashboard. On company selection, sidebar activates with the current `aziendaId` context.
- Active state: highlighted background + semibold (600) text
- Responsive:
  - <1024px: collapses to icon-only (64px)
  - <768px: hamburger drawer (no hamburger on desktop)

**Top Header Bar**:
- Left: Page title + breadcrumb (e.g., "Sopralluogo > N2O SRL > Ambienti")
- Right: Background queue indicator, user avatar dropdown

### 1.2 Spacing & Grid

- **Base unit**: 8px grid (all spacing as multiples of 8)
- **Content max-width**: 1280px, centered with auto margins
- **Page padding**: 32px desktop, 16px mobile
- **Section gap**: 24px
- **Card gap**: 16px
- **Form field gap**: 16px vertical between fields, 24px between field groups

### 1.3 Color System (Semantic Tokens)

Resolved via "Digital Guardian" Stitch design system (April 2026). Hex values and semantic mapping:

| Token | Hex Value | Usage |
|-------|-----------|-------|
| `--color-primary` | `#003D74` | Brand accent, active nav, links, primary buttons (gradient to `#1B5594`) |
| `--color-primary-light` | `#A5C8FF` | Highlights, focus rings, subtle accents |
| `--color-surface` | `#FFFFFF` | Card/panel backgrounds (surface-container-lowest) |
| `--color-surface-low` | `#F2F3F6` | Input backgrounds, secondary sections |
| `--color-background` | `#F8F9FC` | Page background |
| `--color-border` | `#C2C6D2` at 15% | Ghost borders only — "No-Line" rule: use tonal shifts instead of borders |
| `--color-text` | `#191C1E` | Primary text (never pure #000) |
| `--color-text-secondary` | `#424750` | Labels, help text, placeholders |
| `--color-success` | `#22C55E` | Completato badge, Accettabile risk, save confirmation |
| `--color-warning` | `#F59E0B` | In Corso badge, Modesto risk, modification banner |
| `--color-danger` | `#BA1A1A` | Errors, required asterisk, Gravissimo risk |
| `--color-info` | `#1B5594` | Generating badge, active processing |
| `--color-risk-green` | `#22C55E` | Risk I=3-4 (Accettabile), NIOSH IR ≤0.75 |
| `--color-risk-yellow` | `#F59E0B` | Risk I=5-6 (Modesto), NIOSH IR 0.75-1.0 |
| `--color-risk-orange` | `#F97316` | Risk I=7-8 (Grave) |
| `--color-risk-red` | `#EF4444` | Risk I=9-12 (Gravissimo), NIOSH IR >1.0 |

**Rules**: 60-30-10 color distribution. Max 3 primary hues. Never pure #000 on #FFF. **"No-Line" Rule**: No 1px solid borders for sectioning. Define boundaries via tonal surface shifts (#FFFFFF cards on #F2F3F6 backgrounds). Ghost borders (outline-variant at 15% opacity) only as accessibility fallback. Depth via tonal layering, not drop shadows. Ambient whisper shadows only for floating elements (blur 24-48px, on-surface at 4-6% opacity).

### 1.4 Typography — "Digital Guardian" Design System

- **Headings**: Plus Jakarta Sans, weights 600-700, tracking -0.02em
- **Body/Labels**: Inter, weight 400-500, line-height 1.5
- **Data/Codes**: JetBrains Mono (fallback), weight 400 — used only for code snippets, not general data
- **Size scale** (max 5 sizes per view):
  - Display/Hero: 3.5rem (56px) — Plus Jakarta Sans 700 (KPI numbers, hero headlines)
  - Page title: 1.75rem (28px) — Plus Jakarta Sans 600
  - Section heading: 1.125rem (18px) — Inter 500
  - Body: 0.875rem (14px) — Inter 400
  - Label/Caption: 0.6875rem (11px) — Inter 600, uppercase with 0.05em tracking

### 1.5 Form Patterns

- **Labels**: Always above inputs, never inside (accessibility). Italian, semibold 600, 0.875rem.
- **Required indicator**: Red asterisk (*) after label text
- **Input height**: 40px minimum, 44px tap target on mobile
- **Focus state**: 2-4px ring with `--color-primary` at 50% opacity, transition 150ms
- **Validation**: Inline error below field on blur. Red text + red input border. Never validation-only-on-submit.
- **Submit buttons**: Never disabled. Always clickable. Shows field-level errors on click if form invalid.
- **Help text**: `--color-text-secondary`, 0.75rem, below input
- **Auto-save indicator**: "Salvato" text near header, fade in on save, fade out after 3s
- **Field layout**: 2-column grid on desktop (>768px), single column on mobile. Related fields grouped visually.

### 1.6 Animation & Interaction

| Interaction | Animation | Duration | Easing |
|-------------|-----------|----------|--------|
| Button hover | scale(1.02) + translateY(-2px) + shadow | 200ms | cubic-bezier(0.4, 0, 0.2, 1) |
| Card hover | translateY(-4px) + shadow increase | 200ms | cubic-bezier(0.4, 0, 0.2, 1) |
| Input focus | Ring glow + border color shift | 150ms | ease-out |
| Survey step transition | Slide + fade (Framer Motion) | 300ms | ease-in-out |
| Scroll reveal | Fade up, translateY(20px→0), stagger 100ms | 600ms | ease-out |
| Modal enter | Backdrop opacity 200ms, content scale(0.95→1) | 300ms | ease-out |
| Modal exit | Reverse of enter | 200ms | ease-in |
| Toast enter | Slide in from right | 300ms | ease-out |
| Skeleton shimmer | Linear gradient sweep | 1.5s | infinite ease-in-out |

**Performance**: Only animate `transform` + `opacity`. Use `will-change` on animated elements. Support `prefers-reduced-motion` media query (set all durations to 0.01ms).

### 1.7 Notifications

- **Toast** (sonner): Bottom-right. Auto-dismiss 5s. Types: success/error/info/warning.
- **Background queue**: Header badge with count + spinner. Click expands dropdown showing per-document name + status.
- **Modified warning**: Amber banner, top of survey page when editing after submission. Text: "Modificato dopo l'invio — le modifiche non sono ancora firmate dal cliente". "Richiedi firma" action link.

### 1.8 Empty States

- Centered: Lucide icon (48px, `--color-text-secondary`) + Italian message + primary action CTA
- Examples:
  - Dashboard: "Nessuna azienda ancora." → "Nuova Azienda"
  - Persone: "Nessun dipendente registrato." → "Aggiungi Persona"
  - Ambienti: "Nessun ambiente aggiunto." → "Aggiungi Ambiente"
  - Documenti: "Nessun documento generato." → "Genera Documenti"

### 1.9 Loading States

- **Page**: Skeleton placeholders matching layout shape
- **Table**: Skeleton rows (5 rows, matching column widths)
- **Cards**: Skeleton with rounded rect matching card dimensions
- **Actions** (save, calculate): Inline spinner replacing button text

### 1.10 Error States

- **API failure**: Toast with "Errore di connessione. Riprova." + retry action
- **Form validation**: Per-field inline errors (see 1.5)
- **404 / Not found**: Centered page with "Pagina non trovata" + link to dashboard
- **Permission denied**: "Non hai i permessi per questa azione." toast

---

## 2. Dashboard

**Route**: `/[lang]/dashboard`

### 2.1 Layout

Bento Grid: KPI row (4 columns) + client table below.

### 2.2 KPI Cards

Top row, `grid-template-columns: repeat(4, 1fr)` on desktop, `repeat(2, 1fr)` on tablet, stack on mobile.

| Card | Value | Semantic Color |
|------|-------|----------------|
| Aziende Totali | Count of all companies | Default text |
| Sopralluoghi Attivi | Surveys with status In Corso | `--color-warning` |
| Documenti Pronti | Documents with status Ready | `--color-success` |
| In Generazione | Documents currently generating | `--color-info` |

Card hover: translateY(-4px) + shadow increase.

### 2.3 Client Table

Built with TanStack Table v8.

**Columns**:

| Column | Content | Width | Sortable |
|--------|---------|-------|----------|
| Ragione Sociale | Company name, bold 600 | 2fr | Yes (alpha) |
| Sede | City (Province) | 1.5fr | Yes (alpha) |
| Sopralluogo | Status badge | 1fr | Yes (by status order) |
| Documenti | "X/16" count | 1fr | Yes (numeric) |
| Azioni | "Apri" link | 0.5fr | No |

**Status badges**:

| Status | Label | Color |
|--------|-------|-------|
| Bozza | Bozza | Gray bg, gray text |
| In Corso | In Corso | Amber bg, dark amber text |
| Inviato | Inviato | Blue bg, dark blue text |
| Completato | Completato | Green bg, dark green text |

**Interactions**:
- Search bar: top-right of table, debounced 300ms, filters by ragione_sociale
- Sort: Click column header, toggles asc/desc/none. Arrow indicator.
- Pagination: 10 rows per page. "Precedente" / "Successivo" + page numbers.
- Row hover: subtle background highlight
- "Apri" link: navigates to `/[lang]/survey/[aziendaId]`

**"+ Nuova Azienda" button**: Primary color, top-right next to search. Opens modal with:
- ragione_sociale (required)
- sede_legale_via + sede_legale_citta (required)
- codice_ateco (required)
- "Crea" primary button, "Annulla" secondary

### 2.4 States

- **Empty**: No companies → centered empty state with "Nuova Azienda" CTA
- **Loading**: Skeleton for 4 KPI cards + 5 skeleton table rows
- **Error**: Toast for API failure, table shows "Errore nel caricamento" with retry

---

## 3. Survey Wizard Shell

**Route**: `/[lang]/survey/[aziendaId]`

### 3.1 Step Bar

Horizontal bar at top of content area, inside a white card with border.

**7 Steps**: Azienda → Persone → Ambienti → Attrezzature → Rischi → Sost. Chimiche → Riepilogo

**Step states**:
- **Completed**: Green circle with checkmark + green label. Clickable.
- **Active**: Primary color circle with step number + primary label.
- **Available** (free mode only): Default circle with number. Clickable.
- **Locked** (linear mode): Gray circle + gray label. Not clickable, `cursor: not-allowed`.

**Connector lines**: Between each step circle. Green if both adjacent steps completed, gray otherwise.

### 3.2 Navigation Modes

**Linear mode** (first pass, hasn't reached step 7 yet):
- Only completed steps and current step are clickable in step bar
- "Avanti →" validates current step via Zod before advancing
- "← Indietro" always available (no validation on back)
- Future steps show as locked gray

**Free mode** (after reaching Riepilogo once):
- All steps clickable in step bar, jump to any step
- Bottom nav shows destination names: "← Ambienti" / "Rischi →"
- No validation required to navigate (auto-save handles persistence)
- Steps that have been modified since submission show a small edit icon

### 3.3 Auto-Save

- **Trigger**: 2 seconds after last field change (debounced)
- **Endpoint**: `PUT /api/v1/aziende/{id}/survey/step/{n}`
- **Success**: "Salvato" indicator near header, fades out after 3s
- **Failure**: Red "Errore di salvataggio" + "Riprova" link, persists until resolved
- **Offline**: Queues changes in IndexedDB, syncs on reconnect. Shows "Non in linea — salvataggio locale" indicator.

### 3.4 Survey Lifecycle

| State | Badge | Behavior | Trigger |
|-------|-------|----------|---------|
| Bozza | Gray | Full edit, linear nav | Initial creation |
| In Corso | Amber | Full edit, linear nav | First field saved |
| Inviato | Blue | Edit with warning, free nav | Client signs on Riepilogo |
| Completato | Green | Edit with warning, free nav | All documents generated |

**Soft-lock behavior**: After submission (Inviato), any edit triggers the amber "Modificato dopo l'invio" banner. Banner includes "Richiedi firma" link. Editing is never blocked.

### 3.5 Step Transitions

Framer Motion `AnimatePresence`:
- Forward: content slides left out, new slides left in (300ms ease-in-out)
- Backward: content slides right out, new slides right in
- Fade + translate combined

---

## 4. Step 1: Azienda

**Purpose**: Company master data. Foundation for all documents.

### 4.1 Form Layout

Two-column grid on desktop, single column on mobile.

**Section: Dati Aziendali**

| Field | Type | Required | Width | Validation |
|-------|------|----------|-------|------------|
| Ragione Sociale | Text input | Yes | Full | min 2 chars |
| Codice ATECO | Text input + autocomplete | Yes | Half | Pattern: XX.XX.XX |
| Attività | Text input | Yes | Full | min 5 chars |
| Orario Lavoro | Text input | No | Half | Free text |
| Metratura Totale (mq) | Number input | Yes | Half | min 1 |
| Zona Sismica | Select dropdown | Yes | Half | Options: 1, 2, 3, 4 |

**Section: Sede Legale**

| Field | Type | Required | Width |
|-------|------|----------|-------|
| Via | Text input | Yes | Full |
| Città (Provincia) | Text input | Yes | Half |
| CAP | Text input | No | Half |

**Section: Sede Operativa**

Same fields as Sede Legale. Checkbox at top: "Stessa della sede legale" — if checked, fields auto-fill and disable.

**Section: Datore di Lavoro**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Seleziona DdL | Select dropdown | Yes | Populated from Persone (step 2). On first pass, shows "Aggiungi prima le persone al passo 2". On subsequent visits, dropdown of existing people. |

### 4.2 AI-Generated Fields

- **Descrizione Attività**: Textarea with "Genera con AI" button. Clicking triggers AI generation from company data + ATECO. Shows loading spinner in button. Result appears in textarea, marked with `--color-info` left border + small "Generato con AI" badge above. Fully editable.
- **Contesto Territoriale**: Same pattern. Generated from sede + zona sismica.

AI badge: Small pill "🤖 AI" in `--color-info` above the field when content is AI-generated. Disappears if user edits the entire content.

---

## 5. Step 2: Persone

**Purpose**: Register employees with roles, assignments, and safety positions.

### 5.1 Layout

Table view of all registered people + "Aggiungi Persona" button.

**Table columns** (TanStack Table):

| Column | Type | Width |
|--------|------|-------|
| Nominativo | Text (bold) | 2fr |
| Mansione | Text | 1.5fr |
| Tipo Contratto | Badge | 1fr |
| Sesso | Text (M/F) | 0.5fr |
| Fascia Età | Text | 0.5fr |
| Ruoli Sicurezza | Badge list | 1.5fr |
| Azioni | Edit/Delete icons | 0.5fr |

**Safety role badges**: Displayed as small pills within the row: RSPP, RLS, P.S. (Primo Soccorso), A.I. (Antincendio), Prep. (Preposto). Colored with `--color-primary` background.

### 5.2 Add/Edit Person Modal

Opens when clicking "Aggiungi Persona" or edit icon. Modal (max-width 640px).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Nominativo | Text input | Yes | UPPERCASE auto-transform |
| Codice Fiscale | Text input | Yes | Pattern: 16 alphanumeric chars. Privacy: shown as masked (last 4 visible) after save. |
| Mansione | Text input | Yes | Free text, e.g., "IMPIEGATO" |
| Tipologia Contrattuale | Select | Yes | Options: IMPIEGATO, OPERAIO, DdL, COLLABORATORE |
| Sesso | Radio buttons | Yes | M / F |
| Fascia Età | Radio buttons | Yes | >18 / 15-18 |
| **Ruoli di Sicurezza** | | | |
| RSPP | Toggle switch | No | Only one person can hold this. Warning if already assigned. |
| RLS | Toggle switch | No | Only one person. |
| Primo Soccorso | Toggle switch | No | Multiple allowed. |
| Antincendio | Toggle switch | No | Multiple allowed. |
| Preposto | Toggle switch | No | Multiple allowed. Assigned per environment in Step 3. |

**Modal footer**: "Salva" primary button + "Annulla" secondary.

### 5.3 Delete Confirmation

Clicking delete icon shows confirmation dialog: "Eliminare [Nome]? Questa azione non può essere annullata." with "Elimina" danger button + "Annulla".

---

## 6. Step 3: Ambienti

**Purpose**: Define work environments. Critical dependency for Steps 4, 5, and risk scoring.

### 6.1 Layout

Card grid of environments + "Aggiungi Ambiente" button.

Each environment is a card showing:
- **Name** (bold, e.g., "UFFICIO AMMINISTRATIVO")
- **Type** badge (Ufficio / Magazzino / Sala Corsi / Esterno)
- **Superficie**: X mq
- **Preposto**: Person name (if assigned)
- **Descrizione attività**: truncated to 1 line
- Edit (pencil) and Delete (trash) icon buttons in card header

Cards in `grid-template-columns: repeat(auto-fill, minmax(320px, 1fr))` with 16px gap.

### 6.2 Add/Edit Environment Modal

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Nome | Text input | Yes | e.g., "MAGAZZINO PRINCIPALE" |
| Tipo | Select dropdown | Yes | Options: Ufficio, Magazzino, Sala Corsi, Esterno. **This selection determines which equipment checklists appear in Step 4 and which risks appear in Step 5.** |
| Superficie (mq) | Number input | No | Used in fire risk and microclima calculations |
| Preposto | Select dropdown | No | Populated from Persone with ruolo_preposto=true. Shows "Nessun preposto disponibile — assegna il ruolo nel Passo 2" if none. |
| Descrizione Attività | Textarea | No | Free text |

### 6.3 Environment-Dependent Data

When an environment's `tipo` changes, the system must:
1. Refresh the equipment checklist for that environment in Step 4
2. Refresh the applicable risk list in Step 5
3. Show a confirmation if data already exists: "Cambiando il tipo di ambiente verranno aggiornate le attrezzature e i rischi associati. Continuare?"

---

## 7. Step 4: Attrezzature

**Purpose**: Equipment per environment with dynamic checklists based on environment type.

### 7.1 Layout

Tab bar at top: one tab per environment (from Step 3). Active tab underlined with `--color-primary`.

Below tabs: equipment checklist for selected environment.

### 7.2 Equipment Checklist

Loaded from `GET /api/v1/reference/equipment/{env_type}` based on the environment's tipo.

**Display**: Checkbox list grouped by category.

| Element | Details |
|---------|---------|
| Checkbox | Pre-populated checklist items per environment type |
| Equipment name | Italian label from reference data |
| Marcatura CE | Toggle (SI/NO) per checked item |
| Verifiche Periodiche | Toggle (SI/NO) per checked item |

**Behavior**:
- Checking a checkbox reveals the CE + Verifiche toggles inline
- Unchecking hides them
- Custom equipment: "Aggiungi attrezzatura personalizzata" text input + add button at bottom of list

### 7.3 Environment Tabs

- If no environments exist: "Aggiungi prima gli ambienti nel Passo 3" message with link/button to Step 3
- Tab badges: show count of selected equipment per environment (e.g., "Ufficio (5)")

---

## 8. Step 5: Rischi

**Purpose**: Contextualized risk checklist per environment. Marks which risks apply.

### 8.1 Layout

Same tab-per-environment pattern as Step 4.

Below tabs: Risk checklist for selected environment, loaded from `GET /api/v1/reference/risks/{env_type}`.

### 8.2 Risk Checklist

Grouped by the 11 risk categories:

1. Strutture
2. Macchine
3. Elettrici
4. Incendio
5. Chimici
6. Fisici
7. Biologici
8. Cancerogeni
9. Organizzazione
10. Psicologici
11. Ergonomici

Each category is a collapsible section (accordion). Default: expanded for categories with pre-selected risks, collapsed for empty categories.

**Per risk item**:
- Checkbox: "Applicabile" — marks this risk as relevant to this environment
- Risk description text (from reference library)
- When checked: risk is included in the Risk Scoring interface (Section 11)

### 8.3 Summary Bar

Fixed bar at bottom of the risk checklist (above bottom nav):
- "X rischi selezionati su Y disponibili per [Ambiente Name]"
- Updates in real-time as checkboxes toggle

---

## 9. Step 6: Sostanze Chimiche

**Purpose**: Chemical substance management with AI-powered SDS extraction.

### 9.1 Layout

Two-phase interface:
1. **Upload zone** (when no SDS uploaded yet)
2. **Extraction review table** (after upload + extraction)

### 9.2 Upload Zone

- react-dropzone area: dashed border, centered icon + text
- Text: "Trascina i file SDS (PDF) qui, oppure clicca per selezionare"
- Constraint: Max 20 files per batch. Show count: "X/20 file selezionati"
- File list below dropzone: filename + size + remove (X) button per file
- "Avvia Estrazione" primary button. Always clickable per global pattern. If clicked with no files: shows inline error "Seleziona almeno un file". Active styling when ≥1 file selected.
- Supported format: PDF only. Reject non-PDF with inline error: "Solo file PDF accettati"

### 9.3 Extraction Progress

After clicking "Avvia Estrazione":
- Upload + extraction happens via `POST /api/v1/aziende/{id}/sds/upload`
- Progress per file: filename + progress bar + status text
- Statuses: "Caricamento...", "Estrazione in corso...", "Completato ✓", "Errore ✗"
- Overall progress: "X di Y file completati"
- On completion: auto-transition to review table

### 9.4 Extraction Review Table

TanStack Table with inline editing.

| Column | Type | Editable | Width |
|--------|------|----------|-------|
| Prodotto | Text cell | Yes | 2fr |
| Produttore | Text cell | Yes | 1.5fr |
| Pittogrammi | Icon/tag display | Yes (multi-select) | 1fr |
| Stato Miscela | Dropdown cell | Yes | 1fr |
| Frasi H | Text cell | Yes | 1.5fr |
| Frasi P | Text cell | Yes | 1.5fr |
| Azioni | Confirm/Delete | — | 0.5fr |

**AI badge**: Small "🤖 AI" indicator on cells that were AI-extracted. Disappears when user manually edits.

**Pittogrammi**: GHS pictogram codes (GHS01-GHS09) displayed as small icons. Editable via multi-select dropdown.

**Stato Miscela options**: Liquido, Solido, Gas

**Row actions**:
- Checkmark: Confirm this row's data is correct
- Trash: Delete this substance
- All rows start unconfirmed. "Conferma Tutti" button above table to bulk-confirm.

**Bottom action**: "Conferma e Salva" primary button. Calls `POST /api/v1/aziende/{id}/sds/confirm`. If clicked with unconfirmed rows: shows inline error "Conferma tutte le righe prima di salvare" and highlights unconfirmed rows.

### 9.5 Manual Add

"Aggiungi Sostanza Manualmente" button below table for chemicals without SDS PDFs. Opens modal with all SostanzaChimica fields.

---

## 10. Step 7: Riepilogo

**Purpose**: Summary review of all entered data + digital countersignature.

### 10.1 Layout

Read-only summary sections, one per previous step:

1. **Dati Aziendali**: Key company fields in 2-column key-value layout
2. **Personale**: Count + mini table (name, role, safety roles)
3. **Ambienti**: Count + card list (name, type, sqm)
4. **Attrezzature**: Count per environment
5. **Rischi**: Count per environment + count per category
6. **Sostanze Chimiche**: Count + table (product, manufacturer, pictograms)

Each section has an "Modifica" link in the header → navigates to that step (enables free mode if first pass).

### 10.2 Completeness Check

Before enabling submission:
- Visual checklist showing each step's completion status
- Incomplete steps: amber warning icon + "Dati mancanti" + link to step
- All steps complete: green checkmarks

### 10.3 Countersignature

Below the summary, after completeness check passes:

- **Client name** text input (pre-filled from DdL if available)
- **Signature pad**: Canvas-based signature input (touch + mouse). "Cancella" to reset.
- **Date**: Auto-filled with current date, read-only
- **"Invia Sopralluogo"** primary button. Triggers:
  1. Save signature image
  2. Set survey status to "Inviato"
  3. Enable free navigation mode
  4. Toast: "Sopralluogo inviato con successo"
  5. Navigate to Dashboard

---

## 11. Risk Scoring Interface

**Route**: `/[lang]/risk-scoring/[aziendaId]`

**Purpose**: Office operator reviews and adjusts P/D scores for all risks marked in Step 5. This is the core "review, not data entry" screen.

### 11.1 Layout

Full-width table with environment grouping. Tab bar at top for switching environments, or "Tutti gli Ambienti" view showing all grouped.

### 11.2 Risk Table

TanStack Table with inline editing, grouped by environment.

**Columns**:

| Column | Type | Width | Editable |
|--------|------|-------|----------|
| Categoria | Badge (11 risk categories) | 1fr | No |
| Pericolo | Text (risk description) | 2.5fr | No |
| Condizioni Esposizione | Text | 2fr | No |
| Rischio | Text | 1.5fr | No |
| P | Number input (1-4) | 0.5fr | **Yes** |
| D | Number input (1-4) | 0.5fr | **Yes** |
| I | Calculated display | 0.5fr | No (auto) |
| Livello | Color-coded badge | 0.75fr | No (auto) |
| Misure | Expand button | 0.5fr | — |

### 11.3 P and D Inputs

- Number inputs constrained to 1-4
- Keyboard: arrow keys increment/decrement. Tab moves to next cell.
- On change: I recalculates instantly (I = 2*D + P)
- Pre-populated from reference data. Office operator adjusts as needed.

**P Scale** (shown in tooltip on hover):
1. Improbabile
2. Poco probabile
3. Probabile
4. Molto probabile

**D Scale** (shown in tooltip on hover):
1. Trascurabile
2. Modesto
3. Notevole
4. Gravissimo

### 11.4 I Calculation & Color Coding

Formula: **I = 2*D + P** (calculated client-side, instant)

| I Range | Level | Badge Text | Color Token |
|---------|-------|------------|-------------|
| 3-4 | Accettabile | ACCETTABILE | `--color-risk-green` |
| 5-6 | Modesto | MODESTO | `--color-risk-yellow` |
| 7-8 | Grave | GRAVE | `--color-risk-orange` |
| 9-12 | Gravissimo | GRAVISSIMO | `--color-risk-red` |

The I cell and Livello badge both use the corresponding color. Row background gets a very subtle tint of the risk color (5% opacity) for visual scanning.

### 11.5 Misure di Prevenzione (Expandable Row)

Clicking the expand button on a row reveals a panel below:

- **Current measures**: Textarea with existing prevention measures. Editable.
- **"Suggerisci con AI"** button: Calls AI to suggest improvement measures based on the risk.
  - Response shows as a card with AI badge
  - Three action buttons per suggestion: **Accetta** (replaces text), **Modifica** (appends to textarea for editing), **Rifiuta** (dismisses)
  - Multiple suggestions possible per risk

### 11.6 Environment Grouping

- **Tab mode**: Tab bar at top with environment names. Click to filter table.
- **"Tutti" tab**: Shows all environments. Group header rows with environment name + risk count. Collapsible groups.
- **Summary stats per environment**: "X rischi: Y accettabili, Z modesti, W gravi, V gravissimi" below each group header.

### 11.7 Bulk Actions

- **"Salva Modifiche"**: Saves all changed P/D values. Calls `PUT /api/v1/aziende/{id}/ambienti/{aid}/rischi` per environment.
- Auto-save: Also debounced 5 seconds after last P/D change (longer than survey because table edits are rapid).
- **"Esporta Riepilogo"**: Downloads a summary CSV of all risks + scores.

---

## 12. Document Generation

**Route**: `/[lang]/documents/[aziendaId]`

**Purpose**: View, generate, and download all documents for a company.

### 12.1 Layout

Card grid showing all 16 document types.

`grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))` with 16px gap.

### 12.2 Document Card

Each card represents one document type:

| Element | Details |
|---------|---------|
| **Icon** | Lucide icon representing doc type (FileText, Shield, Flame, etc.) |
| **Title** | Italian document name (e.g., "DVR Master", "Allegato MMC") |
| **Status badge** | Current status (see below) |
| **Last generated** | Date/time or "Mai generato" |
| **Action button** | Context-dependent (see below) |

**Status badges & actions**:

| Status | Badge | Action Button |
|--------|-------|---------------|
| Non Generato | Gray "Non Generato" | "Genera" (primary) |
| In Coda | Blue "In Coda" | Shows queue position text, no action button (already queued) |
| Generazione... | Blue "Generazione..." + spinner | "Annulla" (secondary) |
| Pronto | Green "Pronto" | "Scarica" (primary) + "Rigenera" (secondary) |
| Errore | Red "Errore" | "Riprova" (primary) + "Dettagli" (link) |
| Consegnato | Green "Consegnato ✓" | "Scarica" + "Rigenera" |

### 12.3 Batch Generation

Top-right: **"Genera Tutti"** button. Queues all non-generated documents.

Confirmation dialog: "Generare tutti i X documenti non ancora pronti? Questa operazione richiede alcuni minuti."

### 12.4 Background Queue

Generation is fully asynchronous:
1. Click "Genera" → `POST /api/v1/aziende/{id}/documents/generate` → card immediately shows "In Coda"
2. Backend processes via Celery → WebSocket pushes status updates
3. Card updates in real-time: In Coda → Generazione... → Pronto (or Errore)
4. Header queue indicator updates count
5. Toast on completion: "DVR Master generato con successo" (per document)
6. User can navigate away freely; notifications follow them

### 12.5 Document Preview

Clicking card title (when Pronto) opens a preview panel:
- Right-side slide-in panel (480px width) or modal on mobile
- PDF.js preview of generated .docx (converted server-side) or download prompt
- "Scarica .docx" button at top of panel

### 12.6 Document Dependencies

Some documents require data from specific survey steps or calculations:

| Document | Requires |
|----------|----------|
| DVR Master | Steps 1-5 complete + risk scoring done |
| Allegato MMC | MMC calculations (Phase 3) |
| Allegato VDT | VDT calculations (Phase 3) |
| All others | At minimum Steps 1-3 complete |

If prerequisites not met: "Genera" button shows tooltip: "Completa prima: [missing step/data]"

---

## 13. Form Validation Rules

### 13.1 Azienda Fields

| Field | Rule | Error Message (IT) |
|-------|------|--------------------|
| ragione_sociale | Required, min 2 chars | "Ragione sociale obbligatoria" / "Minimo 2 caratteri" |
| codice_ateco | Required, pattern `\d{2}\.\d{2}\.\d{2}` | "Codice ATECO obbligatorio" / "Formato non valido (es. 46.69.94)" |
| attivita | Required, min 5 chars | "Attività obbligatoria" |
| metratura_totale | Required, min 1, integer | "Metratura obbligatoria" / "Inserire un numero valido" |
| zona_sismica | Required, one of [1,2,3,4] | "Selezionare la zona sismica" |
| sede_legale_via | Required | "Indirizzo sede legale obbligatorio" |
| sede_legale_citta | Required | "Città sede legale obbligatoria" |
| sede_operativa_via | Required (unless same as legale) | "Indirizzo sede operativa obbligatorio" |
| sede_operativa_citta | Required (unless same as legale) | "Città sede operativa obbligatoria" |

### 13.2 Persona Fields

| Field | Rule | Error Message (IT) |
|-------|------|--------------------|
| nominativo | Required, min 2 chars | "Nominativo obbligatorio" |
| codice_fiscale | Required, exactly 16 alphanumeric | "Codice fiscale obbligatorio" / "Deve essere di 16 caratteri alfanumerici" |
| mansione | Required | "Mansione obbligatoria" |
| tipologia_contrattuale | Required, one of enum | "Selezionare il tipo di contratto" |
| sesso | Required, M or F | "Selezionare il sesso" |
| fascia_eta | Required | "Selezionare la fascia d'età" |

**Cross-field rules**:
- RSPP: Only one person can have ruolo_rspp=true. If user toggles on for person B while person A already has it: "RSPP già assegnato a [Person A]. Sostituire?" with confirm/cancel.
- RLS: Same single-assignment rule.

### 13.3 Ambiente Fields

| Field | Rule | Error Message (IT) |
|-------|------|--------------------|
| nome | Required, min 2 chars | "Nome ambiente obbligatorio" |
| tipo | Required, one of enum | "Selezionare il tipo di ambiente" |
| superficie_mq | Optional, if provided must be > 0 | "La superficie deve essere maggiore di zero" |

### 13.4 Risk Scoring Fields

| Field | Rule | Error Message (IT) |
|-------|------|--------------------|
| P | Required, integer 1-4 | "P deve essere tra 1 e 4" |
| D | Required, integer 1-4 | "D deve essere tra 1 e 4" |

### 13.5 SDS Upload

| Rule | Error Message (IT) |
|------|--------------------|
| Max 20 files | "Massimo 20 file per caricamento" |
| PDF only | "Solo file PDF accettati" |
| Max 50MB per file | "File troppo grande (max 50MB)" |

### 13.6 Countersignature

| Field | Rule | Error Message (IT) |
|-------|------|--------------------|
| Client name | Required | "Nome del firmatario obbligatorio" |
| Signature | Required (non-empty canvas) | "Firma obbligatoria" |

### 13.7 Validation Timing

- **On blur**: Validate individual field when user leaves it
- **On submit/advance**: Validate entire step. Scroll to first error. Focus first error field.
- **On type** (real-time): Only for format-constrained fields (codice_ateco, codice_fiscale) — show format hint as user types
- **Never**: Validation only on final submit without per-field feedback

---

## Appendix: Screen Inventory

| # | Screen | Route | Status |
|---|--------|-------|--------|
| 1 | Dashboard | `/[lang]/dashboard` | Specified |
| 2 | Survey Wizard Shell | `/[lang]/survey/[aziendaId]` | Specified |
| 3 | Step 1: Azienda | (wizard step) | Specified |
| 4 | Step 2: Persone | (wizard step) | Specified |
| 5 | Step 3: Ambienti | (wizard step) | Specified |
| 6 | Step 4: Attrezzature | (wizard step) | Specified |
| 7 | Step 5: Rischi | (wizard step) | Specified |
| 8 | Step 6: Sostanze Chimiche | (wizard step) | Specified |
| 9 | Step 7: Riepilogo | (wizard step) | Specified |
| 10 | Risk Scoring | `/[lang]/risk-scoring/[aziendaId]` | Specified |
| 11 | Document Generation | `/[lang]/documents/[aziendaId]` | Specified |
| 12 | Settings | `/[lang]/settings` | Phase 5 (deferred) |
| 13 | Login | `/[lang]/login` | NextAuth.js v5 login (email/password + Google OAuth) |

---

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scope | Phase 2 only | Spec what you build next; other phases get specced when reached |
| Design direction | Deferred | Design-agnostic spec; skin applied later via Stitch |
| User model | Unified interface, no role separation | Small team wears multiple hats |
| Survey navigation | Linear first pass, free after Riepilogo | Respects data dependencies while allowing easy editing |
| Survey lifecycle | Soft-lock on submit | Edit with warning, no bureaucratic overhead |
| Document generation | Background queue + notifications | Users can keep working during generation |
| Risk scoring | Table-based inline editing | Data density for power users, "review not data entry" |
| Animation framework | AntiGravity timing (200ms hover, 300ms transitions) | Professional feel without blocking interactions |
| Anti-patterns | No labels in inputs, no disabled submit, min 44px targets | AntiGravity + WCAG compliance |
