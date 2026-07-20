# UI/UX Technical Audit — N2O DVR Platform

**Date:** 2026-06-13 · **Scope:** `frontend/` (Next.js 16, Tailwind 4, base-ui/react) · **Surface:** authenticated product UI (dashboard, aziende, survey, assessments, documents, admin) · **Method:** code-level audit + live verification on production (`dvr-sicurezza.it`) at 1440 / 390 px.

## Audit Health Score

| # | Dimension | Score | Key Finding |
|---|-----------|-------|-------------|
| 1 | Accessibility | 2/4 | Real WCAG AA contrast fails: `#94a3b8` (~2.6:1) on white used for placeholders + sublabels in 10 files; no `prefers-reduced-motion` anywhere |
| 2 | Performance | 3/4 | Lean: motion in 1 file only, icon-driven (no images), good memoization. Minor: heavy 2-layer shadow on every Card by default |
| 3 | Responsive Design | 1/4 | **App shell is desktop-only** — `fixed w-64` sidebar + `ml-64` with zero breakpoints, no hamburger; content clipped + horizontal overflow below ~900px |
| 4 | Theming | 2/4 | 793 hardcoded hex across 53 files bypass a well-built token system; off-palette colors incl. ruby `#b51648` that DESIGN.md explicitly bans |
| 5 | Anti-Patterns | 3/4 | Distinctive Stripe-grade product UI, not slop. Subtle slips: decorative random accent colors, `font-extrabold` numerals vs. weight-300 brand |
| **Total** | | **11/20** | **Acceptable — significant but concentrated work needed** |

## Anti-Patterns Verdict — PASS

**This does not look AI-generated.** It reads as a deliberate, Stripe-inspired product system: navy + slate restraint, semantic status/risk color language, thoughtful empty states, `aria-hidden` on decorative bars, tabular numerals, restrained motion. None of the cardinal tells are present — no gradient text (`bg-clip-text`: 0), no glassmorphism-as-default, no eyebrow-on-every-section, no identical-card-grid monotony. The score is dragged down by **two concentrated, fixable systemic issues** (the responsive shell and color/contrast hygiene), not by pervasive low quality. Subtle brand-consistency slips remain (below).

## Executive Summary

- **Audit Health Score: 11/20 (Acceptable)** — high desktop craft, two systemic gaps.
- **Issues by severity:** P0: 0 · P1: 3 · P2: 6 · P3: 4
- **Top issues:**
  1. **[P1] App shell does not respond below desktop** — sidebar fixed at 256px, content margin hardcoded `ml-64`, no collapse/hamburger. Verified: at 390px the nav occupies ⅔ of the screen and content is clipped with horizontal scroll. User stories include on-site tablet use.
  2. **[P1] Contrast failures on muted text** — `#94a3b8` (~2.6:1) and `#8a96ab` (~2.9:1) used for placeholders, sub-labels, and timestamps fail WCAG AA 4.5:1 for normal text.
  3. **[P1] 793 hardcoded hex bypass the token system** — theming is not centralized; introduces off-palette and DESIGN-banned colors and makes the installed `next-themes` unusable.
- **Recommended next steps:** `adapt` the shell for mobile/tablet → `colorize`/`polish` to migrate hardcoded hex to tokens and fix contrast → `harden` for reduced-motion + touch targets.

## Detailed Findings by Severity

### [P1] App shell is desktop-only — no responsive navigation
- **Location:** `src/app/(dashboard)/layout.tsx:23` (`ml-64`), `src/components/layout/sidebar.tsx:55` (`fixed … w-64`)
- **Category:** Responsive
- **Impact:** Below ~900px the 256px fixed sidebar consumes most of the viewport; content is clipped and the page scrolls horizontally. There is no hamburger/drawer to dismiss the nav. A `sheet.tsx` exists but is only used in a DUVRI page and version-history, never as a mobile nav. Field operators (per USER_STORIES persona "operatore di campo", tablet on-site) cannot use the app on a tablet/phone.
- **Standard:** WCAG 1.4.10 Reflow (content must reflow to 320px without 2-D scrolling).
- **Recommendation:** Make the sidebar a slide-over `<Sheet>` below `lg`, toggled by a hamburger in `Header`; change `ml-64` to `lg:ml-64` (0 on mobile). Reuse the existing `sheet.tsx`.
- **Suggested command:** `/impeccable adapt`

### [P1] Muted text fails WCAG AA contrast
- **Location:** `#94a3b8` in 10 files (e.g. `dashboard/page.tsx:597,776,816,933`, `_shared.tsx:43`); login placeholder `#8a96ab` in `(auth)/login/page.tsx:76`.
- **Category:** Accessibility
- **Impact:** `#94a3b8` on white ≈ **2.6:1**; `#8a96ab` ≈ **2.9:1** — both below the 4.5:1 minimum. Used for search placeholders, quick-action sublabels ("registra cliente"), activity timestamps ("ieri", "3g fa") — exactly the text users squint at. Visible in the desktop screenshot.
- **Standard:** WCAG 1.4.3 Contrast (Minimum), AA. Placeholders are held to the same 4.5:1.
- **Recommendation:** Replace muted grays with `#64748d` (≈4.75:1, already the body token) or darker. Define a single `--color-muted-foreground` and stop inventing `#94a3b8`/`#8a96ab`.
- **Suggested command:** `/impeccable colorize` (then `polish`)

### [P1] 793 hardcoded hex values bypass the design tokens
- **Location:** 53 files. Most common: `#64748d` ×133, `#e5edf5` ×131, `#061b31` ×104, `#273951` ×69, `#f6f9fc` ×65. Off-palette: `#94a3b8` ×35, `#b51648` ×26, `#0ea5e9` ×13, `#7c3aed` ×9.
- **Category:** Theming
- **Impact:** The `@theme` block in `globals.css` defines a complete token set (`--color-border`, `--color-foreground`, `--color-body`, …), but components hardcode the literal hex via arbitrary Tailwind values (`text-[#64748d]`) instead of token utilities (`text-body`). Consequences: (a) `next-themes` is installed but dark mode is impossible without rewriting every component; (b) palette drift — colors that exist in no token (`#94a3b8`, `#7c3aed`, `#0ea5e9`, `#8a96ab`); (c) a single color change requires a 53-file find/replace.
- **Recommendation:** Migrate hardcoded hex to the existing tokens; add tokens for any legitimately-missing roles. Centralized maps (`_shared.tsx`, `status-map.ts`) are the right pattern — extend it.
- **Suggested command:** `/impeccable polish` (token migration pass)

### [P2] No `prefers-reduced-motion` alternative anywhere
- **Location:** Global — 0 occurrences in `src/**`. Animations exist (`globals.css` keyboard ring, `data-open:animate-in` on dialogs/sheets, framer-motion in `survey-wizard.tsx`, `transition-*` throughout).
- **Category:** Accessibility
- **Impact:** Users with vestibular sensitivity get no relief; the skill treats reduced motion as non-optional.
- **Recommendation:** Add a global `@media (prefers-reduced-motion: reduce)` block in `globals.css` that neutralizes transitions/animations to a crossfade or instant; guard the survey-wizard transitions with `useReducedMotion()`.
- **Suggested command:** `/impeccable harden`

### [P2] Off-brand colors used decoratively (DESIGN.md §0 violation)
- **Location:** `dashboard/page.tsx` `pickAccent()`:115 (random violet/rose per company), `PipelineBar` drafts segment `#7c3aed`:187; `_shared.tsx` `ruby`/`violet`/`sky` accents:27-51; `#b51648` (ruby) in 9 files.
- **Category:** Anti-Pattern / Theming
- **Impact:** DESIGN.md §0 explicitly bans decorative pink/ruby/magenta for the safety domain and PRODUCT.md principle #3 says "color carries meaning, never decoration." `pickAccent` hashes the company id to assign a *random* accent to each monogram — decorative variety, not semantics. Violet `#7c3aed` marks "Bozze/drafts," sky `#0ea5e9` is a generic accent.
- **Recommendation:** Drop `pickAccent` randomization (use one neutral/navy monogram, or accent only by a meaningful attribute). Restrict the accent palette to navy + the semantic status set. Replace `#b51648` with the danger token `#ba1a1a` where it's standing in for "errore/gravissimo."
- **Suggested command:** `/impeccable colorize`

### [P2] KPI numerals use `font-extrabold`, contradicting the weight-300 system
- **Location:** `dashboard/page.tsx:245` (`text-[30px] font-extrabold`); `_shared.tsx` `StatTile`:255 (`font-semibold`).
- **Category:** Anti-Pattern (brand consistency)
- **Impact:** The whole type system is built on weight-300 display/numerals (`.type-numeral` is weight 300, DESIGN.md "Don't use 600-700 for headlines"). The headline dashboard KPIs render at weight 800 — visibly the heaviest thing on the page and off-brand. Visible in the 1440 screenshot.
- **Recommendation:** Use `.type-numeral` (or weight 300–400 + tabular) for KPI figures; reserve weight for genuine emphasis.
- **Suggested command:** `/impeccable typeset`

### [P2] Touch targets below minimum size
- **Location:** Todo checkbox `dashboard/page.tsx:835` (`h-[18px] w-[18px]`), logout button `sidebar.tsx:138` (`p-1` around a 14px icon ≈ 22px), filter chips `dashboard/page.tsx:578` (~26px tall), button sizes `xs`/`badge` (24/22px).
- **Category:** Accessibility / Responsive
- **Impact:** WCAG 2.5.8 (Target Size Minimum, AA) requires ≥24×24px; the 18px checkbox and ~22px logout fail. Worse on the touch/tablet use case.
- **Recommendation:** Pad interactive targets to ≥24px (ideally 44px for primary on-site actions) without enlarging the visual glyph.
- **Suggested command:** `/impeccable adapt`

### [P2] No `aria-current` on active navigation
- **Location:** `sidebar.tsx:74-84,108-118` — active link is styled (`bg-white/10 font-medium`) but carries no programmatic state.
- **Category:** Accessibility
- **Impact:** Screen-reader users don't get the "current page" cue conveyed visually.
- **Recommendation:** Add `aria-current={isActive ? "page" : undefined}` to nav links.
- **Suggested command:** `/impeccable harden`

### [P2] Dense list rows don't reflow
- **Location:** `dashboard/page.tsx:628` azienda row `grid-cols-[auto_minmax(0,1.6fr)_0.9fr_0.8fr_0.9fr_auto]` (6 fixed-ratio columns, no `sm:` collapse).
- **Category:** Responsive
- **Impact:** Once the shell is fixed, these rows still cram 6 columns into a narrow panel; progress/status/date columns become unreadable.
- **Recommendation:** Collapse to a stacked 2-line layout below `md`.
- **Suggested command:** `/impeccable adapt`

### [P3] Sidebar low-contrast section label
- **Location:** `sidebar.tsx:98` — "Amministrazione" at `text-white/40` on `#18244e` ≈ **3.5:1** (10px uppercase = small text, needs 4.5:1).
- **Category:** Accessibility
- **Recommendation:** Bump to `text-white/55`+ for the section label (`text-white/65` inactive nav ≈7:1 is fine).
- **Suggested command:** `/impeccable colorize`

### [P3] English string in an Italian-only UI
- **Location:** `dialog.tsx:75` `<span className="sr-only">Close</span>`; `dialog.tsx:114` "Close".
- **Category:** Anti-Pattern (i18n consistency)
- **Recommendation:** "Chiudi" (it's read aloud by screen readers).
- **Suggested command:** `/impeccable clarify`

### [P3] `<aside>` / nav lack accessible names
- **Location:** `sidebar.tsx:55` `<aside>` and `:66` `<nav>` have no `aria-label`.
- **Category:** Accessibility
- **Recommendation:** `aria-label="Navigazione principale"` on the nav; label the admin nav group too.
- **Suggested command:** `/impeccable harden`

### [P3] Every Card defaults to the heaviest shadow
- **Location:** `card.tsx:15` (`shadow-stripe-elevated` = two-layer 30/45px + 18/36px blur) on all cards, animated on hover.
- **Category:** Performance / Visual hierarchy
- **Impact:** Large-blur shadows are the most expensive to paint; applying the "elevated" (level 3) shadow to *every* card flattens the elevation hierarchy and adds paint cost in card-dense views.
- **Recommendation:** Default cards to ambient/standard (level 1–2); reserve elevated for genuinely-floating surfaces (popovers, the login card).
- **Suggested command:** `/impeccable polish`

## Patterns & Systemic Issues

1. **Color is not tokenized.** 793 raw hex literals across 53 files is the single biggest maintainability and theming liability. The token system is good but unused; this also blocks the dark mode the dependencies imply.
2. **Responsiveness was done per-page, not at the shell.** Pages carry 188 responsive prefixes (`sm/md/lg/xl`), but the frame (`sidebar` + layout margin) has none — so the per-page work is wasted below desktop.
3. **A small accessibility cluster recurs:** invented muted grays under 4.5:1, no reduced-motion, sub-24px targets, missing `aria-current` — all cheap to fix, all systemic.

## Positive Findings (keep & replicate)

- **Forms are properly associated** — 161 `htmlFor` / 172 `id`, `autoComplete`, `required`, inline error messaging (`login/page.tsx`). Strong baseline.
- **Global focus-visible ring** (2px primary, 2px offset) in `globals.css:238` — consistent keyboard affordance.
- **Semantic markup** — 0 `<div onClick>` faux-buttons; icon-only controls carry `aria-label`; decorative bars carry `aria-hidden`.
- **Thoughtful empty states** everywhere (`_shared.tsx` `EmptyState`, dashboard panels) that teach the interface instead of saying "nothing here."
- **Centralized semantic color maps** (`_shared.tsx` risk/doc-status, `status-map.ts`) — the correct pattern; extend it to kill the hardcoded hex.
- **Restrained, purposeful motion** — framer-motion in exactly one place; no orchestrated page-load theatre. Right for product register.
- **Tabular numerals** on KPIs, dates, counts — domain-appropriate precision.

## Recommended Actions (priority order)

1. **[P1] `/impeccable adapt`** — make the shell responsive: sidebar → `Sheet` drawer + hamburger below `lg`, `ml-64` → `lg:ml-64`, fix dense row reflow and sub-24px touch targets.
2. **[P1] `/impeccable colorize`** — fix contrast (`#94a3b8`/`#8a96ab` → `#64748d`+), remove decorative/off-brand accents (`pickAccent` randomization, ruby `#b51648`, violet `#7c3aed`).
3. **[P1] `/impeccable polish`** — migrate the 793 hardcoded hex to the existing tokens; default cards to lighter shadow.
4. **[P2] `/impeccable harden`** — global `prefers-reduced-motion`, `aria-current`, nav `aria-label`.
5. **[P2] `/impeccable typeset`** — bring KPI numerals back to the weight-300 system.
6. **[P3] `/impeccable clarify`** — localize the "Close" dialog string.

> You can ask me to run these one at a time, all at once, or in any order you prefer.
>
> Re-run `/impeccable audit` after fixes to see your score improve.
