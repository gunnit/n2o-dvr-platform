# UI/UX Test — Valutazione Rischio Incendio

**Date:** 2026-09-07 · **Surface:** `/assessments/incendio/[aziendaId]` (`frontend/src/app/(dashboard)/assessments/incendio/[aziendaId]/page.tsx` + `frontend/src/components/assessments/incendio/*`) · **Method:** scripted browser walkthrough (Playwright 1.59, Chromium 141) against the full stack run locally from this branch — Postgres 16 with all Alembic migrations, FastAPI on :8000, `next dev` on :3000 — at 1440×900, 820×1180 and 390×844, plus an axe-core 4.10 scan and a code read of the page, its components and the backend endpoints it calls. Script: `frontend/tests/e2e/incendio-uiux-walkthrough.mjs` (see §6). Evidence: `docs/audits/incendio-2026-09-07/`.

Test data: a throwaway consultant tenant, one azienda ("Falegnameria Rossi SRL") with three ambienti (Magazzino vernici, Reparto verniciatura, Uffici amministrativi). The walkthrough logs in through the UI, reaches the page through the Valutazioni hub, links each area to an ambiente, scores them Alto / Medio / Basso, edits the measures checklist, adds, duplicates, validates and removes areas, saves twice, reloads, navigates away with unsaved edits, simulates a 503 on load and a 500 on the measures endpoint, tabs through the form, and repeats the load on mobile and tablet.

> **Update, same day:** the five P1 findings are fixed in the same PR and re-verified with the walkthrough — see §7. The sections below describe the page as tested before the fixes.

## Health score

| # | Dimension | Score | Key finding |
|---|-----------|-------|-------------|
| 1 | Accessibility | 2/4 | 16 unnamed 16 px checklist buttons (axe critical); score "radiogroup" contains plain buttons, no radio state or arrow keys; focus rings, labels and inline errors are good |
| 2 | Performance | 3/4 | Every API call is preceded by a `/api/auth/session` round trip (208 for 184 API calls); measures list re-fetched 6× after one save |
| 3 | Responsive | 2/4 | No horizontal overflow at 390/820 (shell fixed since June), but header + red banner + summary card all pin at once: 55% of the phone viewport |
| 4 | Theming / consistency | 3/4 | Band colours consistent everywhere; native `window.confirm`; read-only input indistinguishable from editable |
| 5 | Task flow & data safety | 1/4 | Areas reorder on every reload; a failed load shows an empty form with no error; unsaved edits are lost silently; checklist decisions do not reach the allegato |
| **Total** | | **11/20** | **Acceptable — the page computes correctly and persists faithfully, but five P1 flow/layout defects need fixing before it is trustworthy on site** |

## Executive summary

- **What works:** scoring, bands, VV.F. banner, validation, save-then-delete ordering (June F4 fix verified: 3 POST, then 3 DELETE), and hydration are all correct. Every field survives save → reload, including custom measures and de-selected measures. Keyboard focus is visible on every control. The page reflows to 390 px without overflow.
- **Issues by severity:** P0: 0 · P1: 5 · P2: 6 · P3: 6.
- **Top three:**
  1. **[P1] Three sticky layers collide.** The app header (`sticky top-0 z-30`), the VV.F. banner (`sticky top-0 z-20`) and the summary card (`sticky top-4 z-10`) all pin at the top with no coordinated offsets. Scrolled, the banner slides under the header and the card slides under the banner; on a phone the pinned stack takes 55% of the screen.
  2. **[P1] Area order flips on every reload.** Rows are saved in form order and read back `created_at DESC`, so the operator's Magazzino / Reparto / Uffici comes back as Uffici / Reparto / Magazzino, the "Valutazioni archiviate" card disagrees with the form, and the allegato reads rows in unspecified order.
  3. **[P1] The measures checklist is not what the allegato prints.** Untouched checklists persist `NULL`; the generator prints its own hardcoded list (`LIVELLO_SPECIFIC_MEASURES`, different wording) and appends the operator's selection only when non-null. De-selecting a measure in the UI never removes anything from the document.
- **Recommended next steps:** fix the sticky stack and the ordering first (small, contained); then make load failures loud and guard unsaved edits; then unify the measures source so what the operator reviews is what gets printed ("solo una questione di revisione").

## 1. Findings by severity

### [P1] F1 · Sticky header, banner and summary card overlap each other
- **Location:** `src/components/layout/header.tsx:22` (`sticky top-0 z-30 h-14`), `src/components/assessments/incendio/incendio-vvf-banner.tsx:24` (`sticky top-0 z-20`), `src/components/assessments/incendio/incendio-form.tsx` `IncendioOverview` (`sticky top-4 z-10`).
- **Observed:** desktop, scrolled 900 px: banner box 0–70 px, summary card 16–189 px — the card title "Livello di rischio incendio" and the "livello massimo" chip sit under the translucent red banner, and the banner's first line sits under the breadcrumb bar (`02-desktop-sticky-collision.png`). Mobile 390×844: banner 154 px + card 311 px = **55% of the viewport pinned**, banner text drawn over the card header (`03-mobile-sticky-collision.png`). Tablet 820: 26%.
- **Impact:** the two elements that exist to stay visible are the ones that get hidden. On a phone the operator scrolls the form through a 380 px slot. WCAG 2.2 SC 2.4.11 (Focus Not Obscured): a focused control can scroll under 330 px of pinned chrome.
- **Fix:** keep one pinned element besides the app header. Offset it by the header height (`top-14`), make the VV.F. banner an in-flow alert at the top of the page (it is already mirrored by the red "livello massimo: Alto" chip), and on `<lg` collapse the summary to a one-line strip (count + max band) or un-pin it.

### [P1] F2 · Areas come back in reverse order after every save and reload
- **Location:** `backend/app/api/v1/incendio_valutazioni.py:70` (`order_by(created_at.desc())`), page `load()` hydrates `rows.map(...)` in that order; `backend/app/services/document_generator/data_loader.py:43` `load_incendio` has no `order_by` at all.
- **Observed:** entered Magazzino → Reparto → Uffici; after save the "Valutazioni archiviate (3)" card lists Uffici, Reparto, Magazzino (`05-after-save-archived-order.png`); after reload the form itself is Uffici, Reparto, Magazzino (`06-after-reload-order-flipped.png`). Each save re-creates every row (3 POST + 3 DELETE), so the next reload flips again.
- **Impact:** the operator loses their mental map of the areas between sessions; "Area 1" is a different room every time; the archived card and the form disagree on screen; the printed allegato orders areas by whatever Postgres returns.
- **Fix:** order ascending (`created_at`) in the list endpoint and in `load_incendio`, or add an `ordine` column as `ambienti` already has (feedback #22) and persist the form position. Render the archived card in the same order as the form.

### [P1] F3 · A failed load renders an empty form with no error — and the next save duplicates rows
- **Location:** `page.tsx` `load()`: `if (rowsRes.ok) {...}` with no `else`; `ambRes.ok ? … : []`.
- **Observed:** with the saved-rows GET answering 503, the page shows one empty "Area 1 · Basso · 3/9", no error, no retry, no archived card (`04-load-503-silent.png`). `existing` stays `[]`, so a save would POST new rows and delete nothing: the three saved rows would survive next to the new ones. A failed ambienti GET silently removes the "Locale / Ambiente" select, so linked names hydrate as free text.
- **Impact:** Render cold starts return exactly these 5xx responses (June audit F10). The operator sees "nessuna valutazione", re-enters, and the fascicolo ends up with duplicates that the generator prints twice.
- **Fix:** treat any non-2xx on the three initial GETs as a load error with a "Riprova" action (reuse `PericoliPanel.fetchWithRetry`), and do not enable "Salva valutazione" until the existing rows are known.

### [P1] F4 · Unsaved edits are lost without a prompt
- **Location:** page-level; the `dirty` state only drives the badge.
- **Observed:** with "Modifiche non salvate" showing, clicking the "Valutazioni" breadcrumb navigates immediately; coming back, the edit is gone (`unsaved.guard` FAIL, `unsaved.lost`).
- **Impact:** a full sopralluogo of several areas is one accidental tap away from loss on a tablet. WCAG 3.3.4 (Error Prevention for legal data) applies: this is a legally required document.
- **Fix:** `beforeunload` while dirty plus a client-side route guard (Next `useRouter` + the app `Dialog`), or a per-area draft autosave.

### [P1] F5 · What the operator reviews in "Misure consigliate" is not what the allegato prints
- **Location:** `incendio-measures.tsx` (default selection is local until the operator interacts; `misure_prevenzione` stays `null`), `incendio-roundtrip.ts` (null preserved on save, by design), `backend/app/services/document_generator/allegato_incendio.py:47-61` and `:175-181`.
- **Observed:** after saving, the API holds `misure_prevenzione = NULL` for the two untouched areas while the UI showed "4 / 4 SELEZIONATE" and "5 / 5 SELEZIONATE" (`api.rows`). The generator prints `LIVELLO_SPECIFIC_MEASURES` — a different, shorter list ("formazione 16 ore (livello 3-FOR)…") than the six items served by `/calculate/fire-measures` — and adds the operator's list under "Misure aggiuntive registrate" only when non-null.
- **Impact:** de-selecting "Presentare SCIA ai Vigili del Fuoco" in the UI has no effect on the document; leaving the checklist untouched prints none of the six reviewed items; touching it prints both lists, with overlapping content. The page also shows the same guidance a third time in "Azione consigliata". This breaks the product principle that the operator reviews rather than re-enters.
- **Fix:** one source of truth (`app/data/fire_measures.py`) for UI and generator; persist the default selection on first save (or have the generator treat `NULL` as "all canonical measures for the band"); print the operator's selection *instead of* the hardcoded list. Drop or fold the "Azione consigliata" paragraph into the checklist header.

### [P2] F6 · A new area is born "Basso · 3/9" before anyone looked at it
- **Location:** `incendio-form.tsx` `DEFAULT_AREA` (`inf: 1, si: 1, pi: 1`), `computeArea` incomplete branch, footer copy "Completa INF, SI e PI…".
- **Observed:** on first load the empty area already shows "Basso · 3/9", the summary says "livello massimo: Basso" and the footer "1 area/e compilate" (`01-desktop-initial-prefilled.png`). Because scores can never be undefined, the "incompleta" state and the "Completa INF, SI e PI" messages are unreachable; the only thing blocking a save is the missing name.
- **Impact:** an operator can archive a fire assessment at the minimum score without touching a parameter. Prefill is the right instinct for facts (name, dotazioni), not for a judgement the law requires the assessor to make.
- **Fix:** start scores undefined (schema `optional()` until save) so the existing "incompleta" path lights up and "Salva" genuinely gates on assessment, or keep 1/1/1 but label the row "valori predefiniti — da confermare" until touched.

### [P2] F7 · "Correggi i campi non validi" with no visible invalid field
- **Location:** `page.tsx` save-card helper text; RHF `mode: "onChange"` shows errors only after a field is touched.
- **Observed:** on first load and right after "Duplica area": helper says "Correggi i campi non validi prima di salvare la valutazione." while zero error messages are on screen (`initial.save.help.actionable` FAIL). The button is disabled, so clicking cannot reveal them either.
- **Fix:** name the blocker ("Inserisci il nome dell'area 2"), or keep "Salva" enabled and on click run `form.trigger()`, show the errors and scroll to the first.

### [P2] F8 · Linked area name is read-only but looks editable
- **Location:** `incendio-area-card.tsx` name `<Input readOnly>`; `input.tsx` styles `disabled` but not `read-only`.
- **Observed:** white background, text cursor, identical to an editable input; the only hint is a hover `title`. Typing does nothing.
- **Fix:** `read-only:bg-[#f6f9fc] read-only:text-[#64748d]`, or render the linked name as text with a "Rinomina" action that switches the select to "Altro".

### [P2] F9 · Measures checklist toggles have no name and a 16 px hit area
- **Location:** `incendio-measures.tsx` `<button aria-pressed …>` (`h-4 w-4`).
- **Observed:** axe `button-name` **critical ×16**; hit area 16×16 px; the label text is a sibling `<span>`, not clickable. Mobile: the only sub-24 px targets on the page are these and the plan banner's close (18×18).
- **Standard:** WCAG 4.1.2 Name, Role, Value; 2.5.8 Target Size (min 24 px).
- **Fix:** native `<input type="checkbox" id>` + `<label htmlFor>` wrapping the text (whole row clickable), or `role="checkbox" aria-checked aria-label={m}` with `min-h-6 min-w-6`.

### [P2] F10 · Score selector is a `radiogroup` of plain buttons
- **Location:** `incendio-area-card.tsx` `ScoreButton` inside `role="radiogroup"`.
- **Observed:** children are `<button>` with no `role="radio"`/`aria-checked`; ArrowRight does nothing; every option is a tab stop (27 stops for three areas; `keyboard.tab.sequence`). A screen reader announces a group with no selected value.
- **Fix:** `role="radio" aria-checked` + roving `tabIndex` + arrow keys, or native radios styled as segments (the app already has a radio primitive pattern in the survey).

### [P2] F11 · The page is a dead end in navigation
- **Location:** `auto-breadcrumbs.tsx` (`/assessments/incendio` not linkable), `assessments/page.tsx` (selected azienda kept in state only), `aziende/[id]/page.tsx` (0 links to `/assessments/incendio`).
- **Observed:** the only route in is Valutazioni → pick azienda → card. The breadcrumb "Valutazioni" drops the azienda selection; the azienda page never links here; the page has no link back to the azienda or forward to "Genera Allegato Incendio".
- **Fix:** carry the azienda in the hub URL (`/assessments?azienda=…`), add a "Valutazioni" entry on the azienda page (the Rischi tab already links to `/assessments/risk`), and give this page a header row with "← Falegnameria Rossi SRL" and "Genera allegato".

### [P3] F12 · Copy: hedged plurals, raw status codes, three overlapping guidance blocks
- "1 area/e compilate", "3 area/e archiviata/e", "riga/he precedente/i" — pick the plural in code. Measures endpoint failure shows the literal "Errore 500". Recommended actions appear three times (checklist, "Azione consigliata — livello massimo", VV.F. banner) with three different wordings. "livello massimo:" chip vs "LIVELLO MAX" label in the same view.

### [P3] F13 · "Duplica area" produces an invalid, nameless copy; removal uses `window.confirm`
- Duplicate copies INF/SI/PI only (documented in the tooltip) but not dotazioni or note; the copy has an empty name and immediately triggers "Correggi i campi non validi". Removal prompts with a native dialog ("Rimuovere l'area \"#3\"?…") that ignores the design system. Name copies "Copia di …", copy dotazioni, use the app `Dialog`.

### [P3] F14 · At 390 px the three-option segmented control breaks 2 + 1
- INF buttons measure 141 / 141 / 290 px: the third option becomes a full-width row of its own, so "Altamente infiammabili" reads as a different kind of control than "A basso tasso". Stack all three vertically below `sm`, or shorten labels.

### [P3] F15 · Type density and contrast
- With three areas: 122 of 242 text elements are ≤ 11 px (10 px ×18, 11 px ×104); all field labels are 11 px uppercase. On a tablet in a warehouse this is the size that gets misread. axe `color-contrast` ×4: sidebar section labels 3.4–3.6:1 (known from June), archived-card description 4.44:1 on the green tint. axe `heading-order`: `<h4>` directly under `<h1>`.

### [P3] F16 · Chatty network: a session fetch before every API call, measures re-fetched per area
- `authHeaders()` in the page and `getToken()` in `useApi` each call `/api/auth/session` before every request: 208 session round trips for 184 API calls in the run; a 3-area save = 5 session fetches + 3 POST + 1 GET + 6 `fire-measures` GETs (static reference data re-fetched after `form.reset` remounts the cards). Memoise the token per page and fetch measures once per band.

### [P3] F17 · Out of scope, seen in passing
- `/login`: React hydration mismatch on the email/password inputs (`style={{caret-color: "transparent"}}` differs server/client).
- `GET /organizations/me/branding/logo` returns 404 on every page for tenants without a logo — console noise on each navigation.

## 2. What works (verified)

- Bands and totals match `calculate_fire_risk` (3–4 Basso, 5–7 Medio, 8–9 Alto); the VV.F. banner appears exactly when an area is Alto and is restored on reload.
- Inline Italian validation with `role="alert"`: negative and decimal dotazioni rejected, empty name flagged after touch; "Rimuovi" disabled on the last area.
- Save order is safe: 3 POST (201) then 3 DELETE (204), then one GET; message reports the count; dirty badge clears.
- Faithful hydration: note, dotazioni, custom measure, de-selected measure, ambiente link and band all come back after reload.
- "Aggiungi area" moves focus into the new area's name field; every control in the tab order shows a `:focus-visible` ring.
- No horizontal overflow at 390 or 820 px; the sidebar is a drawer with a hamburger (June P1 shell finding is fixed on this page). No uncaught page errors on the page during the whole run.

## 3. Check log (run of 2026-09-07)

| Check | Result | Detail |
|---|---|---|
| discover.hub.select / hub.card | PASS | azienda selectable on /assessments; "Rischio Incendio" card links to the page |
| discover.azienda.page | INFO | 0 links to the page from /aziende/{id} |
| initial.subtitle | PASS | ragione sociale shown |
| initial.area1.prefilled.band | **FAIL** | new area already "Basso · 3/9" |
| initial.save.disabled | PASS | disabled while name empty |
| initial.save.help.actionable | **FAIL** | "Correggi i campi non validi…" with 0 visible errors |
| initial.remove.disabled | PASS | |
| area1.name.autofill | PASS | name filled from ambiente |
| area1.name.readonly.cue | **FAIL** | readOnly input styled like editable |
| area1.band.alto / vvf.banner.visible | PASS | Alto · 9/9, banner shown |
| measures.loaded | INFO | 6 toggles, "6 / 6 SELEZIONATE" |
| sticky.desktop.no.overlap | **FAIL** | banner 0–70, card 16–189 |
| measures.toggle.off / custom.added | PASS | 5/6 → 6/7 |
| measures.toggle.a11y.name | **FAIL** | accessible name "" |
| measures.toggle.size | **FAIL** | 16×16 px |
| dirty.badge | PASS | |
| add.focus | INFO | focus moves to areas.1.nome |
| area2.band.medio / duplicate.count | PASS | Medio · 5/9; 3 areas |
| validation.negative / decimal / name.required | PASS | |
| remove.confirm.native / remove.count | PASS | `window.confirm`; 2 areas |
| save.enabled / archived.card / dirty.cleared | PASS | 3 POST 201, GET 200; "Valutazioni archiviate (3)" |
| archived.order | **FAIL** | Uffici, Reparto, Magazzino |
| save2.network | INFO | 3 POST, 3 DELETE, 7 GET |
| api.untouched.measures.null | **FAIL** | two rows with `misure_prevenzione = NULL` |
| reload.order.preserved | **FAIL** | Uffici, Reparto, Magazzino |
| reload.vvf / dirty.clean / measures.custom / measures.toggle / note / estintori / ambiente.link | PASS | everything hydrates |
| unsaved.guard | **FAIL** | no prompt, edit lost |
| loadfail.error.visible | **FAIL** | 503 → empty form, no error |
| measures.error.copy | INFO | "Errore 500" |
| keyboard.tab.sequence | INFO | 9 tab stops per area, ring visible on all |
| radiogroup.semantics | **FAIL** | buttons, no aria-checked |
| axe.button-name | **FAIL** | critical, 16 nodes |
| axe.color-contrast | **FAIL** | serious, 4 nodes |
| axe.heading-order | **FAIL** | moderate, 1 node |
| mobile.no.horizontal.overflow | PASS | 390 = 390 |
| mobile.sticky.budget | **FAIL** | 55% pinned |
| mobile.touch.targets | **FAIL** | 2 of 95 under 24 px |
| tablet.no.horizontal.overflow | PASS | 820 = 820 |

## 4. Evidence

| File | Shows |
|---|---|
| `docs/audits/incendio-2026-09-07/01-desktop-initial-prefilled.png` | F6, F7 — fresh page already "Basso · 3/9", helper text with no visible error |
| `docs/audits/incendio-2026-09-07/02-desktop-sticky-collision.png` | F1 — desktop scrolled: header over banner over summary card |
| `docs/audits/incendio-2026-09-07/03-mobile-sticky-collision.png` | F1 — 390 px: banner text drawn over the summary card, 55% pinned |
| `docs/audits/incendio-2026-09-07/04-load-503-silent.png` | F3 — 503 on load: empty form, no error, no archived card |
| `docs/audits/incendio-2026-09-07/05-after-save-archived-order.png` | F2 — archived card order reversed vs. form |
| `docs/audits/incendio-2026-09-07/06-after-reload-order-flipped.png` | F2 — form order after reload |

## 5. Suggested order of work

1. ~~**F1 + F2** (half a day): `top-14` / un-pin on mobile; ascending order in the two queries; archived card in form order.~~ Done (§7).
2. ~~**F3 + F4** (one day): load-error state with retry; unsaved-changes guard.~~ Done (§7).
3. ~~**F5** (one day, backend + frontend): single measures source; generator prints the operator's selection.~~ Done (§7).
4. **F6–F11** (two days): undefined default scores, actionable save helper, read-only cue, checkbox/radio semantics, navigation links.
5. **F12–F16** as polish.

## 6. Reproducing the walkthrough

```bash
# backend (from backend/, venv with requirements*.txt, Postgres + Redis running)
alembic upgrade head && uvicorn app.main:app --port 8000
# frontend (from frontend/)
AUTH_SECRET=dev AUTH_TRUST_HOST=true NEXT_PUBLIC_API_URL=http://localhost:8000 node node_modules/next/dist/bin/next dev
# walkthrough — seeds a throwaway tenant + azienda + 3 ambienti on the local API, then drives the page
node tests/e2e/incendio-uiux-walkthrough.mjs --seed
```

Optional env: `E2E_AXE_PATH=/path/to/axe.min.js` runs the accessibility scan; `E2E_CHROMIUM_PATH` points at a local Chromium when Playwright's download is unavailable; `E2E_EMAIL` / `E2E_PASSWORD` / `E2E_AZIENDA_ID` run against an existing (throwaway) tenant instead of seeding. Output: PASS/FAIL/INFO lines, `report.json` and 16 screenshots in `tests/e2e/out/incendio/`. The exit code reflects only whether the walkthrough itself completed; FAIL lines are findings to read, not a CI gate.

## 7. Fix status — 2026-09-07, same PR

All five P1 findings are fixed and re-verified with the committed walkthrough on a fresh tenant: **36 PASS · 10 FAIL** (was 30 · 17). Every remaining FAIL is a P2/P3 item (F6–F10, F15, mobile touch targets).

| Finding | Fix | Re-run evidence |
|---|---|---|
| F1 sticky collision | VV.F. banner is in flow (`incendio-vvf-banner.tsx`); the summary card is pinned only from `lg`, offset below the app header (`lg:sticky lg:top-[4.5rem]` in `incendio-form.tsx`) | desktop scrolled: no overlap, card at 72 px below the header; phone: 18% of the viewport occupied while scrolled (was 55%); tablet 16% |
| F2 order flips | list endpoint (`incendio_valutazioni.py`) and generator loader (`data_loader.load_incendio`) order by `created_at` ascending, `id` as tie-break; the page sorts the rows the same way so it holds against an older API | archived card and reload both keep Magazzino → Reparto → Uffici |
| F3 silent load failure | the three initial reads go through `fetchWithRetry` (5xx and network errors retried 3×, 400/800 ms back-off); any failure renders an error card with the reason and a "Riprova" button, and neither the form nor "Salva valutazione" is rendered until all three reads succeed | 503 on the saved rows → error card, Riprova, 0 areas rendered, no save button |
| F4 unsaved edits | `src/hooks/use-unsaved-changes-guard.ts`: `beforeunload` for reload/close plus capture-phase interception of same-origin link clicks while dirty, resolved by an in-app dialog ("Continua a modificare" / "Esci senza salvare") that navigates on confirm | breadcrumb click with a dirty form shows the dialog and stays on the page; confirming leaves |
| F5 checklist vs allegato | `allegato_incendio.py` prints the operator's saved selection under "Prescrizioni aggiuntive", or the canonical list from `app/data/fire_measures.py` (the same list the UI serves) when the checklist was left at its default (`NULL`); an explicitly empty selection prints "Nessuna prescrizione aggiuntiva registrata"; the generator's private `LIVELLO_SPECIFIC_MEASURES` list and the duplicate "Misure aggiuntive registrate" block are gone | 4 new tests in `backend/tests/test_allegato_incendio_measures.py`; generator, calculator and DVR suites green (114 passed); import contracts kept |

**Extra defect found while fixing F4.** The page read `formState.isDirty` only inside a `watch` callback, and react-hook-form computes `isDirty` only after something subscribes to it, so the first edit never counted: a single changed note showed no "Modifiche non salvate" badge and would have left without a prompt. The flag is now read during render.

**Still open, on purpose.** The browser back button is not guarded (no App Router event; documented in the hook). The measures endpoint failure still shows the literal "Errore 500" (F12). The walkthrough's `api.untouched.measures` line is now informational: `NULL` means "checklist left at its default" and the allegato expands it to the canonical list.

