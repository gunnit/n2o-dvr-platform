# Product

## Register

product

## Users

Three operator personas at N2O SRL, an Italian workplace-safety consultancy, plus the N2O admin:

- **Operatore di campo (field)** — visits client sites, runs the digital survey (sopralluogo) on a laptop/tablet, captures companies (aziende), people, environments, equipment, and risks. Often on-site, sometimes on patchy connectivity, time-pressured.
- **Operatore di ufficio (office)** — reviews surveyed data, runs assessments (MMC, VDT, Stress, Incendio, Gestanti, etc.), triggers AI extraction/suggestions, generates the 16 safety documents, and reviews output before delivery.
- **Admin (N2O)** — manages users, triages the in-app feedback board, reviews AI feedback.

The job to be done: replace manual Word data-entry with a structured digital survey + AI-assisted document generation, targeting 60-70% time reduction. Core principle: **"Il nostro deve essere solo una questione di revisione, non di inserimento del dato"** — the tool exists so consultants review, not re-key, data.

## Product Purpose

Automated generation of Italian workplace-safety documentation (16 documents across 13 types, anchored by the ~187-page DVR Master) compliant with D.Lgs. 81/2008. A digital survey form feeds a shared data layer (Azienda, Persona, Ambiente, Attrezzatura, SostanzaChimica) that drives template-based `.docx` generation and risk calculations (Risk Index I=2D+P, NIOSH, VDT, INAIL Stress, fire risk, thermal comfort). Success = consultants spend their time reviewing AI-assisted output instead of typing the same data into 16 documents.

## Brand Personality

Stripe-grade precision applied to an industrial/regulatory domain. Three words: **precise, trustworthy, unshowy.** This is expert software for licensed safety professionals producing legally-binding documents — it should feel like a financial-grade instrument: confident, dense where data lives, generous in its chrome, never decorative for its own sake. Italian-language UI throughout.

## Anti-references

- **Consumer SaaS cheer** — no playful illustrations, mascots, gradient-drenched hero cards, or celebratory confetti. This is regulated professional work.
- **Generic Bootstrap/admin-template look** — no card-grid monotony, no flat gray dashboards, no pill buttons.
- **Decorative pink/ruby accents** — explicitly off-brand for a safety/industrial domain (the DESIGN.md Stripe base allows them; the N2O override bans them).
- **AI slop tells** — gradient text, glassmorphism-as-default, hero-metric template, tiny tracked eyebrows on every section.

## Design Principles

1. **Review, not entry.** Every screen should reduce keystrokes and surface AI-suggested values for confirmation, never demand re-typing of data the system already holds.
2. **Dense data, generous chrome.** Tables, risk matrices, and assessment grids pack tightly; the frame around them breathes. Controlled density, Stripe-style.
3. **Trust through restraint.** Navy + slate + a single accent. Color carries meaning (risk levels, status), never decoration. The output is legally binding — the UI must read as authoritative.
4. **Domain-honest semantics.** Risk chips, status maps, and scadenza (deadline) indicators use a consistent, learnable color language that mirrors the legislation, not arbitrary brand color.
5. **Earned familiarity.** Standard affordances (side nav, tabs, data tables, command patterns) done well. The tool disappears into the consultant's task.

## Accessibility & Inclusion

- Target **WCAG 2.1 AA**. Professional users on desktop/laptop primarily; tablet on-site.
- Italian-first UI; keep label clarity high (regulatory terms must be exact).
- Keyboard navigation and visible focus required (long form-heavy workflows).
- Respect `prefers-reduced-motion` for any transitions.
- Note: app currently ships **light-mode only** (`color-scheme: light`) despite `next-themes` being installed — dark mode is not a current requirement.
