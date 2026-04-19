---
title: User Guide (Guida Utente) — MD source + in-app page
date: 2026-04-19
status: approved
author: Gregor Maric
---

# User Guide — Design Spec

## 1. Goal

Deliver a single Italian-language user guide for the N2O DVR platform that exists as:

1. A standalone, readable Markdown file in `docs/` (shareable, committable, readable outside the app).
2. An in-app page at `/guida` rendered from the same Markdown source.

One source of truth. Zero drift between the two surfaces.

Audience: N2O SRL's operators (campo and ufficio) plus admins (Luca and team). Language: Italian only. Depth: quick-start at the top, reference-by-feature below, in one long scrollable page.

## 2. Non-goals

- No search (single page; browser find is sufficient).
- No version history or changelog inside the guide (git history is the source of truth).
- No PDF export (browser print-to-PDF is good enough).
- No i18n infrastructure (Italian only).
- No content management UI (guide is edited in Git like any other doc).

## 3. Architecture

### 3.1 Source of truth

- **File**: `docs/guida/GUIDA_UTENTE.md`
- **Format**: GitHub Flavored Markdown with YAML frontmatter.
- **Frontmatter fields**:
  - `title: "Guida Utente — N2O DVR"`
  - `description: <one-line summary>`
  - `updated: YYYY-MM-DD` (manually bumped when the content changes meaningfully)

### 3.2 Images

- **Location**: `docs/guida/images/*.png`
- **Seeding**: copy existing `prod-*.png` screenshots from repo root into `docs/guida/images/` with descriptive names:
  - `prod-login.png` → `docs/guida/images/01-login.png`
  - `prod-dashboard.png` → `docs/guida/images/02-dashboard.png`
  - `prod-documents-list.png` → `docs/guida/images/05-documenti-lista.png`
  - `prod-v2-documents-list.png` → `docs/guida/images/05b-documenti-lista-v2.png`
  - `prod-gdoc-opened.png` → `docs/guida/images/06-gdoc-aperto.png`
  - `prod-v2-dirty-check.png` → `docs/guida/images/07-dirty-check.png`
  - `prod-v2-discard-dialog.png` → `docs/guida/images/08-discard-dialog.png`
  - `prod-v2-history-badge.png` → `docs/guida/images/09-history-badge.png`
  - `prod-after-sync.png` → `docs/guida/images/10-after-sync.png`
- **Referencing in MD**: `![alt](./images/01-login.png)` — relative paths so the MD is viewable on GitHub/local as-is.
- **Webpage rewrite**: renderer rewrites `./images/` → `/guida/images/` at render time. A build/copy step mirrors `docs/guida/images/` to `frontend/public/guida/images/` so the browser can serve them.
- **Original `prod-*.png` files in repo root**: leave untouched for now (they are referenced nowhere and act as an archive); they may be moved/cleaned up later in a separate pass.

### 3.3 In-app page

- **Route**: `frontend/src/app/(dashboard)/guida/page.tsx`
- **Rendering**: React Server Component; reads the MD file via `fs.readFile` from `docs/guida/GUIDA_UTENTE.md` at request time (or at build time — to be decided in the plan based on how Next.js 16 handles file access in server components; a `generateStaticParams`-style static build is preferred for speed).
- **MD → HTML pipeline**: `react-markdown` + `remark-gfm` + `rehype-slug` + `rehype-autolink-headings`.
- **Frontmatter parsing**: `gray-matter` (tiny, standard).
- **Image path rewriting**: a small `remark` transformer (or `react-markdown`'s `urlTransform` prop) rewrites `./images/…` URLs to `/guida/images/…`.
- **Sidebar entry**: add to `frontend/src/components/layout/sidebar.tsx` — inserted between "Impostazioni" and the admin block:

  ```ts
  { name: "Guida", href: "/guida", icon: BookOpen }
  ```

  Icon `BookOpen` from `lucide-react`.

### 3.4 Public asset copy step

The guide's images live in `docs/` (outside Next.js). Next.js can only serve static assets from `public/`. Options:

- **A (recommended)**: a tiny Node script at `frontend/scripts/sync-guide-assets.mjs` that copies `docs/guida/images/*` → `frontend/public/guida/images/`. Wired into `prebuild` (in `frontend/package.json`) and runnable manually for dev.
- **B**: symlink `frontend/public/guida/images` → `../../docs/guida/images`. Simpler but symlinks misbehave on Windows/WSL crossings and in some deploy environments.

Go with **A**.

## 4. Page UX

### 4.1 Layout

Two-column layout inside the dashboard shell (sidebar is already present from `(dashboard)/layout.tsx`):

- **Left column** (sticky, ~240px wide): auto-generated Table of Contents.
  - Extract all H2s and H3s from the rendered markdown (parse the MD AST server-side to get heading nodes + their slugified IDs).
  - Render as a nested `<nav>` with anchor links.
  - Scrollspy on the client: highlight the active section as the user scrolls. Simple `IntersectionObserver` in a small client component.
- **Right column** (max-width ~720px prose): rendered Markdown content.
  - Typography follows `frontend/DESIGN.md` — Plus Jakarta Sans for headings, Inter for body.
  - Use Tailwind's `prose` utility (from `@tailwindcss/typography` if present; otherwise hand-tuned styles) configured to match DESIGN.md.
  - Images: `max-width: 100%`, rounded corners matching DESIGN.md radius, subtle border, optional caption from `alt`.
  - Code blocks: monospaced, subtle background, matching DESIGN.md.

### 4.2 Page header

Above the two-column layout, a small header:
- Title from frontmatter (`title`).
- Short tagline (from `description`).
- "Ultimo aggiornamento: {updated}" small and muted.

### 4.3 Responsive behavior

- Below a breakpoint (e.g. `lg`), TOC collapses into a `<details>` at the top of the page. No fancy drawer.

### 4.4 Access control

Page is inside the `(dashboard)` group, so it's already gated behind the auth check in `(dashboard)/layout.tsx`. Any authenticated user can view the guide. The "Amministrazione" section inside the guide is readable by anyone but obviously only useful for admins (it's documentation about admin features, not a live admin tool).

## 5. Content outline

The MD file follows this structure. Section depths are illustrative; each section is 2-6 short paragraphs plus bullet lists for step-by-step tasks and 0-2 screenshots where relevant.

```
# Guida Utente — N2O DVR

## Introduzione
  - Cos'è la piattaforma (3 righe), a chi serve questa guida

## Quick Start (primo utilizzo in 10 minuti)
  ### 1. Accedi alla piattaforma
  ### 2. Crea la tua prima azienda
  ### 3. Compila il sopralluogo
  ### 4. Genera il DVR Master
  ### 5. Revisiona in Google Docs
  ### 6. Scarica la versione definitiva

## Guida per funzione

  ### Dashboard
  ### Aziende
    - Elenco e ricerca
    - Creazione nuova azienda
    - Scheda azienda
  ### Sopralluoghi
    - Cos'è un sopralluogo
    - Come si compila
    - Salvataggio automatico
  ### Documenti
    - Il DVR Master
    - Generazione del documento
    - Versioni e storico
    - Modifica in Google Docs
      - Dirty-check e warning se hai modifiche non sincronizzate
      - Discard (annulla modifiche)
      - Sync (nuova versione)
    - Download .docx
  ### Valutazioni
    - Stato attuale (cosa è disponibile oggi vs. in arrivo — niente finzione)
    - MMC, VDT, Stress, Incendio, Microclima (solo quelle attive)
  ### Impostazioni
    - Profilo e password

## Amministrazione (solo admin)
  ### Gestione utenti
  ### AI feedback

## FAQ e risoluzione problemi
  - Login fallito
  - Il documento non si genera
  - Google Docs non sincronizza
  - Ho perso le mie modifiche

## Glossario
  - DVR, MMC, VDT, SDS, PEE, DUVRI, POS, HACCP, RSPP, RLS, DdL, D.Lgs. 81/2008

## Contatti e supporto
  - Contatti Niuexa (builder), N2O SRL (owner)
```

### 5.1 Accuracy guardrail (rigid)

Before writing prose for each section, read the actual page/component in the repo so the guide matches reality (button labels, flow steps, field names). No documenting UI that doesn't exist. When a feature is partial or not yet built, say so plainly.

Pages/components to cross-check:
- Login/register: `frontend/src/app/(auth)/**`
- Aziende: `frontend/src/app/(dashboard)/aziende/**`
- Sopralluoghi: `frontend/src/app/(dashboard)/survey/**`
- Documenti: `frontend/src/app/(dashboard)/documents/**`
- Valutazioni: `frontend/src/app/(dashboard)/assessments/**`
- Impostazioni: `frontend/src/app/(dashboard)/settings/**`
- Admin: `frontend/src/app/(dashboard)/admin/**`

## 6. Dependencies to add

Added to `frontend/package.json`:

- `react-markdown`
- `remark-gfm`
- `rehype-slug`
- `rehype-autolink-headings`
- `gray-matter`

Optionally (only if not already present):
- `@tailwindcss/typography` (for `prose` utility). If present, use it; if not, hand-tune styles for headings/paragraphs/lists to match DESIGN.md. Plan step must check first.

All are small, widely used, and standard.

## 7. File/change list

New files:
- `docs/guida/GUIDA_UTENTE.md`
- `docs/guida/images/*.png` (copied from repo-root `prod-*.png`)
- `frontend/src/app/(dashboard)/guida/page.tsx`
- `frontend/src/app/(dashboard)/guida/toc.tsx` (small client component for scrollspy + TOC rendering)
- `frontend/scripts/sync-guide-assets.mjs`

Modified files:
- `frontend/src/components/layout/sidebar.tsx` (add "Guida" entry + `BookOpen` import)
- `frontend/package.json` (add deps + `prebuild` script)

## 8. Risks and open items

- **Next.js 16 file-read in RSC**: confirm the right API to read a file from outside the frontend dir at build/request time on both local dev and the Render deployment. If reading from `docs/` at runtime on Render doesn't work (frontend is deployed with its own rootDir), the guide content must be copied into `public/` or `src/` at build time alongside the images. The plan step will verify this before choosing an approach.
- **Prose styling consistency**: DESIGN.md has a brand override preamble. If `@tailwindcss/typography` isn't already set up, we hand-tune. Plan must check before deciding.
- **Screenshots may show stale UI**: if the screenshots in repo root predate recent UI redesigns, capture new ones during implementation. Don't ship misleading images.
- **"Ultimo aggiornamento" discipline**: humans forget to bump frontmatter. Acceptable; if it becomes a problem, a later pass can derive it from `git log -1 -- docs/guida/GUIDA_UTENTE.md` at build time. Out of scope now.

## 9. Acceptance criteria

- `docs/guida/GUIDA_UTENTE.md` exists, fully Italian, covers all sections in §5, includes screenshots, and is readable standalone on GitHub/VS Code.
- `/guida` route works for any logged-in user, renders the MD with TOC on the left and prose on the right, with working in-page anchors.
- Sidebar has a "Guida" entry; clicking it opens `/guida` and highlights the active nav item.
- Images load correctly on the page (no 404s).
- Every documented feature matches the actual implemented UI (accuracy guardrail).
- No regressions on any other dashboard page.
