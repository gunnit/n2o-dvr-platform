/**
 * Browser walkthrough of the Valutazione Rischio Incendio page
 * (/assessments/incendio/[aziendaId]) — the script behind
 * UI-UX-AUDIT-INCENDIO-2026-09-07.md.
 *
 * It is an audit probe, not a pass/fail suite: every observation is printed
 * as PASS / FAIL / INFO and written to <out>/report.json together with the
 * screenshots. The process exits non-zero only when the walkthrough itself
 * breaks (selector drift, server down), never because a check failed.
 *
 * Usage (from frontend/, with the API and `next dev` running):
 *
 *   node tests/e2e/incendio-uiux-walkthrough.mjs --seed
 *       registers a throwaway tenant on E2E_API_URL, creates one azienda with
 *       three ambienti, then runs the walkthrough as that tenant. Refused
 *       against a non-local API unless E2E_ALLOW_REMOTE_SEED=1.
 *
 *   E2E_EMAIL=… E2E_PASSWORD=… E2E_AZIENDA_ID=… node tests/e2e/incendio-uiux-walkthrough.mjs
 *       runs against an existing tenant. The azienda needs at least three
 *       ambienti; the "initial state" checks assume no saved valutazione yet
 *       (the script saves, re-saves and reloads, so use a throwaway azienda).
 *
 * Optional: E2E_BASE_URL (http://localhost:3000), E2E_API_URL
 * (http://localhost:8000), E2E_OUT_DIR (tests/e2e/out/incendio),
 * E2E_CHROMIUM_PATH (executable to launch instead of Playwright's download),
 * E2E_AXE_PATH (a local axe.min.js — the axe scan is skipped without it).
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from '@playwright/test';

const BASE = process.env.E2E_BASE_URL || 'http://localhost:3000';
const API = process.env.E2E_API_URL || 'http://localhost:8000';
const OUT = path.resolve(process.env.E2E_OUT_DIR || 'tests/e2e/out/incendio');
const SEED = process.argv.includes('--seed');
fs.mkdirSync(OUT, { recursive: true });

const TITLES = { inf: 'Infiammabilità delle sostanze', si: 'Sorgenti di innesco', pi: "Propagazione dell'incendio" };
const report = { checks: [], console: [], network: [], dialogs: [], http4xx: [], axe: null };
const summary = { pass: 0, fail: 0 };
function check(id, ok, detail) { report.checks.push({ id, ok, detail }); summary[ok ? 'pass' : 'fail'] += 1; console.log(`${ok ? 'PASS' : 'FAIL'} ${id} :: ${detail}`); }
function info(id, detail) { report.checks.push({ id, ok: null, detail }); console.log(`INFO ${id} :: ${detail}`); }
async function shot(pg, name, full = true) { await pg.screenshot({ path: path.join(OUT, name + '.png'), fullPage: full }); }

async function api(pathname, { method = 'GET', token, body } = {}) {
  const res = await fetch(`${API}/api/v1${pathname}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${method} ${pathname} → ${res.status}: ${text.slice(0, 300)}`);
  return text ? JSON.parse(text) : null;
}

// ---------------------------------------------------------------------------
// Tenant: seeded or provided.
// ---------------------------------------------------------------------------
let EMAIL = process.env.E2E_EMAIL;
let PASS = process.env.E2E_PASSWORD;
let AZID = process.env.E2E_AZIENDA_ID;
let token;
if (SEED) {
  const local = /^https?:\/\/(localhost|127\.0\.0\.1)(:|\/|$)/.test(API);
  if (!local && process.env.E2E_ALLOW_REMOTE_SEED !== '1') {
    console.error(`--seed refused: E2E_API_URL=${API} is not local. Set E2E_ALLOW_REMOTE_SEED=1 to seed a throwaway tenant there anyway.`);
    process.exit(2);
  }
  const stamp = Date.now().toString(36);
  EMAIL = `e2e-incendio-${stamp}@n2o-e2e.it`;
  PASS = `E2e-Incendio-${stamp}!`;
  ({ access_token: token } = await api('/auth/register', { method: 'POST', body: { email: EMAIL, password: PASS, full_name: 'Tester Antincendio', organization_name: 'Studio E2E Incendio' } }));
  ({ id: AZID } = await api('/aziende', { method: 'POST', token, body: { ragione_sociale: 'Falegnameria Rossi SRL', sede_legale_via: 'Via Roma 1', sede_legale_citta: 'Milano', cap_legale: '20100', provincia_legale: 'MI', attivita: 'Lavorazione legno e verniciatura' } }));
  for (const amb of [
    { nome: 'Magazzino vernici', tipo: 'magazzino', superficie_mq: 120 },
    { nome: 'Reparto verniciatura', tipo: 'produzione', superficie_mq: 300 },
    { nome: 'Uffici amministrativi', tipo: 'ufficio', superficie_mq: 80 },
  ]) await api(`/aziende/${AZID}/ambienti`, { method: 'POST', token, body: amb });
  info('seed', `tenant ${EMAIL} / azienda ${AZID} created on ${API}`);
} else {
  if (!EMAIL || !PASS || !AZID) { console.error('Set E2E_EMAIL, E2E_PASSWORD and E2E_AZIENDA_ID, or pass --seed.'); process.exit(2); }
  ({ access_token: token } = await api('/auth/login', { method: 'POST', body: { email: EMAIL, password: PASS } }));
}
const ambienti = (await api(`/aziende/${AZID}/ambienti`, { token })).sort((a, b) => a.ordine - b.ordine);
if (ambienti.length < 3) { console.error(`Azienda ${AZID} has ${ambienti.length} ambienti; the walkthrough needs three.`); process.exit(2); }
const [A0, A1, A2] = ambienti;
const PAGE_URL = `${BASE}/assessments/incendio/${AZID}`;

// ---------------------------------------------------------------------------
// Browser plumbing.
// ---------------------------------------------------------------------------
function wire(pg, tag) {
  pg.on('console', (m) => { if (['error', 'warning'].includes(m.type())) report.console.push({ tag, type: m.type(), text: m.text().slice(0, /hydrat/i.test(m.text()) ? 2500 : 400) }); });
  pg.on('pageerror', (e) => report.console.push({ tag, type: 'pageerror', text: String(e).slice(0, 400) }));
  pg.on('dialog', async (d) => { report.dialogs.push({ tag, type: d.type(), message: d.message() }); await d.accept(); });
  pg.on('response', (r) => {
    const u = r.url();
    if (r.status() >= 400) report.http4xx.push({ tag, status: r.status(), url: u.slice(0, 160) });
    if (u.startsWith(API) || u.includes('/api/auth/session')) report.network.push({ tag, method: r.request().method(), url: u.replace(API, '').replace(BASE, ''), status: r.status() });
  });
}
async function openPage(pg) {
  await pg.goto(PAGE_URL, { waitUntil: 'domcontentloaded' });
  await pg.waitForSelector('h1:has-text("Valutazione Rischio Incendio")', { timeout: 120000 });
  await pg.waitForFunction(() => !document.body.innerText.includes('Caricamento…'), null, { timeout: 120000 });
  await pg.waitForTimeout(600);
}
async function waitMeasures(pg) { await pg.waitForFunction(() => !document.body.innerText.includes('Caricamento misure'), null, { timeout: 60000 }).catch(() => {}); await pg.waitForTimeout(200); }
// Measures the VV.F. banner and the summary card against the viewport while
// scrolled: how much of each is on screen (`visible`, px) and whether the two
// overlap. `pinnedPct` is the share of the viewport they occupy together.
const stickyEval = () => {
  const alert = [...document.querySelectorAll('[role="alert"]')].find((e) => e.textContent.includes('VV.F.'));
  const overview = [...document.querySelectorAll('[data-slot="card"]')].find((c) => c.textContent.includes('Livello di rischio incendio'));
  const r = (el) => { if (!el) return null; const b = el.getBoundingClientRect(); const visible = Math.max(0, Math.min(b.bottom, innerHeight) - Math.max(b.top, 0)); return { top: Math.round(b.top), bottom: Math.round(b.bottom), h: Math.round(b.height), visible: Math.round(visible), sticky: getComputedStyle(el).position === 'sticky' }; };
  const a = r(alert), o = r(overview);
  const overlap = Boolean(a && o && a.visible > 0 && o.visible > 0 && o.top < a.bottom && a.top < o.bottom);
  return { alert: a, overview: o, vh: innerHeight, overlap, pinnedPct: Math.round((((a?.visible || 0) + (o?.visible || 0)) / innerHeight) * 100) };
};
const HELP = 'text=/Completa INF, SI e PI per ciascuna area per salvare|Correggi i campi non validi|Tutte le aree \\(/';

const browser = await chromium.launch(process.env.E2E_CHROMIUM_PATH ? { executablePath: process.env.E2E_CHROMIUM_PATH } : {});
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'it-IT' });
const page = await ctx.newPage();
wire(page, 'desktop');
const card = (i) => page.locator('[data-slot="card"]', { has: page.locator(`input[id="areas.${i}.nome"]`) }).first();
async function setScore(i, key, value) { await card(i).getByRole('radiogroup', { name: TITLES[key] }).locator('button').nth(value - 1).click(); await page.waitForTimeout(120); }
const areaCount = () => page.locator('input[id^="areas."][id$=".nome"]').count();
const saveBtn = page.getByRole('button', { name: /Salva valutazione|Salvataggio in corso/ });
const dirtyBadge = page.locator('text=Modifiche non salvate');
const banner = page.getByRole('alert').filter({ hasText: 'VV.F.' }).first();
let failed = false;

try {
  // ---- 1. login
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#email', { timeout: 120000 });
  await shot(page, '01-login', false);
  await page.fill('#email', EMAIL); await page.fill('#password', PASS);
  await Promise.all([page.waitForURL((u) => !u.pathname.startsWith('/login'), { timeout: 120000 }), page.click('button[type=submit]')]);
  info('login.landing', 'after login → ' + page.url());
  await page.waitForTimeout(2500);
  await shot(page, '02-after-login', false);

  // ---- 2. discoverability
  await page.goto(`${BASE}/assessments`, { waitUntil: 'domcontentloaded' });
  const sel = page.locator('select').first();
  await sel.waitFor({ timeout: 120000 });
  await page.waitForFunction((id) => [...document.querySelectorAll('select option')].some((o) => o.value === id), AZID, { timeout: 60000 }).catch(() => {});
  const hasOpt = await sel.evaluate((s, id) => [...s.options].some((o) => o.value === id), AZID);
  check('discover.hub.select', hasOpt, 'azienda selectable on /assessments');
  if (hasOpt) await sel.selectOption(AZID);
  await page.waitForTimeout(500);
  const link = page.locator(`a[href="/assessments/incendio/${AZID}"]`).first();
  check('discover.hub.card', await link.isVisible().catch(() => false), 'Rischio Incendio card links to the page once an azienda is selected');
  await shot(page, '03-assessments-hub', true);
  await page.goto(`${BASE}/aziende/${AZID}`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('h1', { timeout: 120000 }); await page.waitForTimeout(2500);
  info('discover.azienda.page', `links to /assessments/incendio from /aziende/{id}: ${await page.locator('a[href*="/assessments/incendio"]').count()}; elements mentioning 'incendio': ${(await page.locator('text=/incendio/i').allInnerTexts()).map((t) => t.replace(/\s+/g, ' ').slice(0, 60)).join(' | ') || 'none'}`);
  await shot(page, '03b-azienda-detail', false);

  // ---- 3. initial state
  await openPage(page);
  await shot(page, '04-initial', true);
  const body0 = await page.innerText('body');
  check('initial.subtitle', body0.includes('Falegnameria Rossi SRL') || body0.includes((await api(`/aziende/${AZID}`, { token })).ragione_sociale), 'subtitle shows ragione sociale');
  info('initial.breadcrumbs', (await page.locator('nav[aria-label="Breadcrumb"]').innerText().catch(() => '(no breadcrumb nav)')).replace(/\n+/g, ' › '));
  const hdr0 = await card(0).locator('[data-slot="card-header"]').first().innerText();
  info('initial.area1.header', hdr0.replace(/\n+/g, ' / ').slice(0, 160));
  check('initial.area1.prefilled.band', !/Basso · 3\/9/.test(hdr0), 'a brand-new area should not already carry a computed band (defaults INF=SI=PI=1)');
  info('initial.overview', (await page.locator('[data-slot="card"]', { hasText: 'Livello di rischio incendio' }).first().innerText()).replace(/\n+/g, ' / ').slice(0, 220));
  check('initial.save.disabled', await saveBtn.isDisabled(), 'save disabled with empty area name');
  const help0 = await page.locator(HELP).first().innerText();
  info('initial.save.help', help0);
  const errAtLoad = await page.locator('text=Nome area richiesto').count();
  check('initial.save.help.actionable', !(help0.startsWith('Correggi') && errAtLoad === 0), `helper says "${help0.slice(0, 40)}…" while visible field errors = ${errAtLoad}`);
  check('initial.remove.disabled', await page.getByRole('button', { name: 'Rimuovi' }).first().isDisabled(), 'Rimuovi disabled when only one area');
  info('initial.footer', await page.locator('text=/area\\/e compilate|Completa INF, SI e PI per ciascuna area per ottenere/').first().innerText());

  // ---- 4. link ambiente
  const amb0 = page.locator('select[id="areas.0.ambiente_select"]');
  info('area1.ambiente.options', (await amb0.locator('option').allInnerTexts()).join(' | '));
  info('area1.ambiente.initial', 'initial value: ' + (await amb0.inputValue()));
  const editableBg = await page.locator('input[id="areas.0.nome"]').evaluate((e) => getComputedStyle(e).backgroundColor);
  await amb0.selectOption(A0.id);
  await page.waitForTimeout(400);
  const nome0 = page.locator('input[id="areas.0.nome"]');
  check('area1.name.autofill', (await nome0.inputValue()) === A0.nome, 'name auto-filled from ambiente: ' + (await nome0.inputValue()));
  const ro = await nome0.evaluate((e) => ({ readOnly: e.readOnly, bg: getComputedStyle(e).backgroundColor, cursor: getComputedStyle(e).cursor, title: e.title }));
  check('area1.name.readonly.cue', ro.readOnly && ro.bg !== editableBg, `readOnly=${ro.readOnly}, bg editable=${editableBg} vs readOnly=${ro.bg}, cursor=${ro.cursor}, title="${ro.title}"`);
  info('area1.scheda.visible', 'scheda ambiente block visible after linking: ' + (await page.locator('text=/Scheda ambiente/i').first().isVisible().catch(() => false)));
  info('page.save.buttons', 'buttons starting with Salva: ' + (await page.getByRole('button', { name: /^Salva/ }).allInnerTexts()).join(' | '));
  await shot(page, '05-linked-ambiente', true);

  // ---- 5. scores → Alto
  await setScore(0, 'inf', 3); await setScore(0, 'si', 3); await setScore(0, 'pi', 3);
  await page.waitForTimeout(400);
  const hdrAlto = await card(0).locator('[data-slot="card-header"]').first().innerText();
  check('area1.band.alto', /Alto · 9\/9/.test(hdrAlto), 'header band: ' + hdrAlto.replace(/\n+/g, ' / ').slice(0, 80));
  check('vvf.banner.visible', await banner.isVisible(), 'VVF banner appears on Alto');
  await page.waitForSelector('text=/Misure consigliate — livello Alto/', { timeout: 60000 });
  await waitMeasures(page);
  const toggles = card(0).locator('button[aria-pressed]');
  info('measures.loaded', `measure toggles for Alto: ${await toggles.count()}, counter: ${await card(0).locator('text=/\\d+ \\/ \\d+ selezionate/').innerText()}`);
  info('azione.alto', (await page.locator('[data-slot="card"]', { hasText: 'Azione consigliata' }).first().innerText()).replace(/\n+/g, ' / ').slice(0, 160));
  await shot(page, '06-alto', true);
  await page.evaluate(() => window.scrollTo(0, 900)); await page.waitForTimeout(400);
  const sd = await page.evaluate(stickyEval);
  check('sticky.desktop.no.overlap', !sd.overlap, 'banner vs summary card while scrolled 900px: ' + JSON.stringify(sd));
  await shot(page, '07-desktop-scrolled', false);
  await page.evaluate(() => window.scrollTo(0, 0));

  // ---- 6. measures interaction
  const first = toggles.first();
  const firstLabel = await first.locator('xpath=..').innerText();
  await first.click(); await page.waitForTimeout(200);
  check('measures.toggle.off', (await first.getAttribute('aria-pressed')) === 'false', 'first measure toggled off: ' + firstLabel.slice(0, 60));
  info('measures.counter.after.toggle', await card(0).locator('text=/\\d+ \\/ \\d+ selezionate/').innerText());
  const custom = card(0).getByPlaceholder('Aggiungi misura personalizzata…');
  await custom.fill('Verifica semestrale porte REI del magazzino'); await custom.press('Enter'); await page.waitForTimeout(200);
  check('measures.custom.added', await card(0).locator('text=Verifica semestrale porte REI del magazzino').isVisible(), 'custom measure appended; counter: ' + (await card(0).locator('text=/\\d+ \\/ \\d+ selezionate/').innerText()));
  const tName = await first.evaluate((b) => b.getAttribute('aria-label') || b.getAttribute('aria-labelledby') || b.textContent.trim());
  check('measures.toggle.a11y.name', tName.length > 0, `toggle accessible name: "${tName}" (role=${await first.evaluate((b) => b.getAttribute('role') || b.tagName.toLowerCase())})`);
  const tb = await first.boundingBox();
  check('measures.toggle.size', tb.width >= 24 && tb.height >= 24, `toggle hit area ${Math.round(tb.width)}x${Math.round(tb.height)}px (WCAG 2.5.8 min 24)`);
  await card(0).locator('input[id="areas.0.estintori_presenti"]').fill('4');
  await card(0).locator('input[id="areas.0.idranti_presenti"]').fill('1');
  await card(0).locator('input[id="areas.0.uscite_emergenza"]').fill('2');
  await card(0).locator('textarea[id="areas.0.note"]').fill('Porta REI da verificare');
  check('dirty.badge', await dirtyBadge.isVisible(), '"Modifiche non salvate" badge visible after edits');

  // ---- 7. add / duplicate / validate / remove
  const scrollBefore = await page.evaluate(() => scrollY);
  await page.getByRole('button', { name: 'Aggiungi area' }).click(); await page.waitForTimeout(500);
  const addInfo = await page.evaluate(() => ({ scrollY, active: document.activeElement.tagName + (document.activeElement.id ? '#' + document.activeElement.id : '') }));
  info('add.focus', `after "Aggiungi area": scroll ${scrollBefore}→${addInfo.scrollY}, focus on ${addInfo.active}, new card top=${Math.round((await card(1).boundingBox())?.y)} (viewport h 900)`);
  info('add.newcard.header', (await card(1).locator('[data-slot="card-header"]').first().innerText()).replace(/\n+/g, ' / ').slice(0, 100));
  await page.locator('select[id="areas.1.ambiente_select"]').selectOption(A1.id);
  await setScore(1, 'inf', 2); await setScore(1, 'si', 2); await setScore(1, 'pi', 1);
  await page.waitForTimeout(300);
  check('area2.band.medio', /Medio · 5\/9/.test(await card(1).locator('[data-slot="card-header"]').first().innerText()), 'area 2 = Medio 5/9');
  await card(1).getByRole('button', { name: 'Duplica area' }).click(); await page.waitForTimeout(500);
  check('duplicate.count', (await areaCount()) === 3, 'duplicate creates a third area');
  info('duplicate.result', `dup header: ${(await card(2).locator('[data-slot="card-header"]').first().innerText()).replace(/\n+/g, ' / ').slice(0, 60)}; name="${await page.locator('input[id="areas.2.nome"]').inputValue()}"; ambiente=${await page.locator('select[id="areas.2.ambiente_select"]').inputValue()}; note copied=${(await page.locator('textarea[id="areas.2.note"]').inputValue()) !== ''}`);
  const est2 = page.locator('input[id="areas.2.estintori_presenti"]');
  await est2.fill('-1'); await page.waitForTimeout(250);
  check('validation.negative', await card(2).locator('text=Inserisci un numero intero non negativo').isVisible(), 'negative estintori shows inline error');
  await est2.fill('1.5'); await page.waitForTimeout(250);
  check('validation.decimal', await card(2).locator('text=Inserisci un numero intero non negativo').isVisible(), 'decimal estintori shows inline error');
  await est2.fill(''); await page.waitForTimeout(250);
  info('validation.empty', 'empty estintori → error visible: ' + (await card(2).locator('text=Inserisci un numero intero non negativo').isVisible()));
  await est2.fill('0');
  const nome2 = page.locator('input[id="areas.2.nome"]');
  await nome2.fill('x'); await nome2.fill(''); await page.waitForTimeout(250);
  check('validation.name.required', await card(2).locator('text=Nome area richiesto').isVisible(), 'empty name shows "Nome area richiesto" after touch');
  info('validation.help.invalid', await page.locator(HELP).first().innerText());
  await shot(page, '08-validation', true);
  await card(2).getByRole('button', { name: 'Rimuovi' }).click(); await page.waitForTimeout(400);
  check('remove.confirm.native', report.dialogs.some((d) => d.type === 'confirm'), 'remove uses window.confirm: ' + JSON.stringify(report.dialogs[0] || null));
  check('remove.count', (await areaCount()) === 2, 'area removed → 2 areas');
  await page.getByRole('button', { name: 'Aggiungi area' }).click(); await page.waitForTimeout(400);
  await page.locator('select[id="areas.2.ambiente_select"]').selectOption(A2.id);
  await page.waitForTimeout(300);
  info('footer.3areas', await page.locator('text=/area\\/e compilate|Completa INF, SI e PI per ciascuna area per ottenere/').first().innerText());

  // ---- 8. save, re-save
  let net0 = report.network.length;
  check('save.enabled', await saveBtn.isEnabled(), 'save enabled once all areas valid');
  await saveBtn.click();
  await page.waitForSelector('text=/Valutazione salvata|Errore salvataggio/', { timeout: 60000 });
  info('save1.message', await page.locator('text=/Valutazione salvata|Errore salvataggio/').first().innerText());
  const calls1 = report.network.slice(net0);
  info('save1.network', calls1.filter((c) => c.url.includes('/api/v1/')).map((c) => `${c.method} …${c.url.split('/').slice(-1)[0].slice(0, 8)}→${c.status}`).join(', ') + ` | session fetches: ${calls1.filter((c) => c.url.includes('/api/auth/session')).length}`);
  check('archived.card', await page.locator('text=/Valutazioni archiviate \\(3\\)/').isVisible(), 'archived card lists 3 rows');
  check('dirty.cleared', !(await dirtyBadge.isVisible()), 'dirty badge cleared after save');
  const archived1 = (await page.locator('[data-slot="card"]', { hasText: 'Valutazioni archiviate' }).first().locator('li').allInnerTexts()).map((s) => s.split('\n')[0].trim());
  check('archived.order', JSON.stringify(archived1) === JSON.stringify([A0.nome, A1.nome, A2.nome]), 'archived card order: ' + archived1.join(' | ') + ` (entered: ${A0.nome}, ${A1.nome}, ${A2.nome})`);
  await shot(page, '09-saved', true);
  net0 = report.network.length;
  await setScore(2, 'si', 2); await page.waitForTimeout(200);
  await saveBtn.click();
  await page.waitForFunction(() => !document.body.innerText.includes('Salvataggio in corso'), null, { timeout: 60000 });
  await page.waitForTimeout(500);
  const calls2 = report.network.slice(net0).filter((c) => c.url.includes('/api/v1/'));
  info('save2.network', `re-save of 3 areas: ${calls2.filter((c) => c.method === 'POST').length} POST, ${calls2.filter((c) => c.method === 'DELETE').length} DELETE, ${calls2.filter((c) => c.method === 'GET').length} GET (${calls2.map((c) => c.status).join(',')})`);
  const rows = await api(`/aziende/${AZID}/incendio-valutazioni`, { token });
  info('api.rows', rows.map((r) => `${r.nome_area || '(null)'}: ${r.livello_rischio} ${r.punteggio_totale}/9 misure=${r.misure_prevenzione === null ? 'NULL' : JSON.stringify(r.misure_prevenzione).slice(0, 50) + '…'} est=${r.estintori_presenti}`).join(' || '));
  info('api.untouched.measures', `${rows.filter((r) => r.misure_prevenzione === null).length} of ${rows.length} rows persist misure_prevenzione=NULL (checklist left at its default); the allegato expands NULL to the canonical list of the band — see backend/tests/test_allegato_incendio_measures.py`);

  // ---- 9. reload / hydration
  await openPage(page); await waitMeasures(page);
  const names = await page.locator('input[id^="areas."][id$=".nome"]').evaluateAll((els) => els.map((e) => e.value));
  check('reload.order.preserved', JSON.stringify(names) === JSON.stringify([A0.nome, A1.nome, A2.nome]), 'order after reload: ' + names.join(' | ') + ` (entered: ${A0.nome}, ${A1.nome}, ${A2.nome})`);
  check('reload.vvf', await banner.isVisible(), 'VVF banner restored on reload');
  check('reload.dirty.clean', !(await dirtyBadge.isVisible()), 'no dirty badge right after load');
  const magIdx = Math.max(0, names.indexOf(A0.nome));
  const mag = card(magIdx);
  check('reload.measures.custom', await mag.locator('text=Verifica semestrale porte REI del magazzino').isVisible(), 'custom measure persisted');
  check('reload.measures.toggle', (await mag.locator('button[aria-pressed]').first().getAttribute('aria-pressed')) === 'false', 'toggled-off measure stays off; counter: ' + (await mag.locator('text=/\\d+ \\/ \\d+ selezionate/').innerText()));
  check('reload.note', (await mag.locator('textarea[id$=".note"]').inputValue()) === 'Porta REI da verificare', 'note persisted');
  check('reload.estintori', (await mag.locator('input[id$=".estintori_presenti"]').inputValue()) === '4', 'estintori persisted');
  check('reload.ambiente.link', (await mag.locator('select').first().inputValue()) === A0.id, 'ambiente link restored');
  await shot(page, '10-reloaded', true);

  // ---- 10. unsaved changes guard
  await mag.locator('textarea[id$=".note"]').fill('MODIFICA NON SALVATA');
  const dBefore = report.dialogs.length;
  await page.locator('nav[aria-label="Breadcrumb"] a', { hasText: 'Valutazioni' }).first().click();
  const guardDialog = page.getByRole('dialog').filter({ hasText: 'Modifiche non salvate' });
  const inAppPrompt = await guardDialog.waitFor({ state: 'visible', timeout: 3000 }).then(() => true).catch(() => false);
  const nativePrompt = report.dialogs.length > dBefore;
  check('unsaved.guard', inAppPrompt || nativePrompt, `leaving with unsaved edits: in-app prompt=${inAppPrompt}, native prompt=${nativePrompt}, still at ${page.url().replace(BASE, '')}`);
  if (inAppPrompt) {
    await guardDialog.getByRole('button', { name: 'Esci senza salvare' }).click();
    await page.waitForURL('**/assessments', { timeout: 30000 }).catch(() => {});
    info('unsaved.guard.confirm', 'after "Esci senza salvare": ' + page.url().replace(BASE, ''));
  }
  await openPage(page);
  info('unsaved.lost', 'unsaved note text present after returning: ' + ((await page.locator('text=MODIFICA NON SALVATA').count()) > 0));

  // ---- 11. failure states
  await page.route('**/incendio-valutazioni', (route) => route.request().method() === 'GET' ? route.fulfill({ status: 503, contentType: 'text/plain', body: 'Service Unavailable' }) : route.continue());
  await openPage(page);
  const b503 = await page.innerText('body');
  const retryBtn = page.getByRole('button', { name: 'Riprova' });
  check('loadfail.error.visible', /Errore|non disponibil|Riprova/i.test(b503), `503 on saved-rows GET → error shown: ${/Errore|non disponibil|Riprova/i.test(b503)}; Riprova button: ${await retryBtn.isVisible().catch(() => false)}; archived card: ${b503.includes('Valutazioni archiviate')}; form areas rendered: ${await areaCount()}; save button rendered: ${await saveBtn.isVisible().catch(() => false)}`);
  await shot(page, '11-load-503', false);
  await page.unroute('**/incendio-valutazioni');
  await page.route('**/calculate/fire-measures*', (route) => route.fulfill({ status: 500, contentType: 'text/plain', body: 'boom' }));
  await openPage(page); await waitMeasures(page);
  info('measures.error.copy', 'measures endpoint 500 → shown: "' + (await page.locator('[role="alert"]', { hasText: /Errore/ }).first().innerText().catch(() => '(none)')) + '"');
  await page.unroute('**/calculate/fire-measures*');

  // ---- 12. keyboard + semantics
  await openPage(page); await waitMeasures(page);
  await page.locator('input[id="areas.0.nome"]').click();
  const seq = [];
  for (let k = 0; k < 16; k++) {
    await page.keyboard.press('Tab');
    seq.push(await page.evaluate(() => { const e = document.activeElement; const cs = getComputedStyle(e); const ring = cs.boxShadow !== 'none' || cs.outlineStyle !== 'none'; return `${e.tagName.toLowerCase()}:${(e.getAttribute('aria-label') || e.placeholder || e.textContent || e.id || '').trim().replace(/\s+/g, ' ').slice(0, 18)}[${e.matches(':focus-visible') ? 'fv' : '-'}${ring ? '+ring' : ''}]`; }));
  }
  info('keyboard.tab.sequence', seq.join(' → '));
  const g = card(0).getByRole('radiogroup', { name: TITLES.inf });
  await g.locator('button').first().focus(); await page.keyboard.press('ArrowRight');
  info('keyboard.radiogroup.arrows', 'ArrowRight inside role=radiogroup moves focus to: "' + (await page.evaluate(() => document.activeElement.textContent.trim())).slice(0, 30) + '"');
  const roles = await g.locator('button').evaluateAll((bs) => bs.map((b) => `${b.getAttribute('role') || 'button'}/aria-checked=${b.getAttribute('aria-checked')}`));
  check('radiogroup.semantics', roles.every((r) => r.startsWith('radio/')), 'children of role=radiogroup: ' + roles.join(' ; '));
  info('typography.histogram', Object.entries(await page.evaluate(() => { const h = {}; for (const el of document.querySelectorAll('main *')) { if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue; const cs = getComputedStyle(el); if (cs.display === 'none') continue; const fs = Math.round(parseFloat(cs.fontSize)); h[fs] = (h[fs] || 0) + 1; } return h; })).sort((a, b) => a[0] - b[0]).map(([k, v]) => `${k}px×${v}`).join(', '));

  // ---- 13. axe
  if (process.env.E2E_AXE_PATH && fs.existsSync(process.env.E2E_AXE_PATH)) {
    await page.addScriptTag({ path: process.env.E2E_AXE_PATH });
    report.axe = await page.evaluate(async () => { const r = await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'] } }); return r.violations.map((v) => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length, samples: v.nodes.slice(0, 3).map((n) => ({ target: n.target.join(' ').slice(0, 120), summary: (n.failureSummary || '').replace(/\n/g, ' ').slice(0, 220) })) })); });
    for (const v of report.axe) check(`axe.${v.id}`, false, `${v.impact}: ${v.help} (${v.nodes} nodes) — ${v.samples[0]?.summary}`);
    if (report.axe.length === 0) check('axe.clean', true, 'no axe violations');
  } else {
    info('axe.skipped', 'set E2E_AXE_PATH to a local axe.min.js to run the accessibility scan');
  }

  // ---- 14. mobile
  const state = await ctx.storageState();
  const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2, locale: 'it-IT', storageState: state });
  const mp = await mctx.newPage(); wire(mp, 'mobile');
  await mp.goto(PAGE_URL, { waitUntil: 'domcontentloaded' });
  await mp.waitForSelector('h1:has-text("Valutazione Rischio Incendio")', { timeout: 120000 });
  await mp.waitForFunction(() => !document.body.innerText.includes('Caricamento…'), null, { timeout: 120000 });
  await waitMeasures(mp); await mp.waitForTimeout(500);
  const ov = await mp.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
  check('mobile.no.horizontal.overflow', ov.sw <= ov.cw, JSON.stringify(ov));
  await shot(mp, '12-mobile-full', true);
  await mp.evaluate(() => window.scrollTo(0, 1400)); await mp.waitForTimeout(400);
  const ms = await mp.evaluate(stickyEval);
  check('mobile.sticky.budget', ms.pinnedPct <= 25, `banner + summary card occupy ${ms.pinnedPct}% of an 844px viewport while scrolled 1400px: ${JSON.stringify(ms)}`);
  await shot(mp, '13-mobile-scrolled', false);
  const targets = await mp.evaluate(() => { const out = []; let total = 0; for (const b of document.querySelectorAll('main button, main a, main select, main input, main textarea')) { const r = b.getBoundingClientRect(); if (r.width === 0 || r.height === 0) continue; total++; if (r.width < 24 || r.height < 24) out.push(`${b.tagName.toLowerCase()} "${(b.getAttribute('aria-label') || b.textContent || b.id || '').trim().slice(0, 22)}" ${Math.round(r.width)}x${Math.round(r.height)}`); } return { total, small: [...new Set(out)] }; });
  check('mobile.touch.targets', targets.small.length === 0, `${targets.small.length}/${targets.total} interactive elements under 24px: ` + targets.small.slice(0, 6).join(' ; '));
  info('mobile.score.buttons', 'INF button sizes at 390px: ' + (await mp.evaluate(() => [...document.querySelector('[role="radiogroup"]').querySelectorAll('button')].map((b) => { const r = b.getBoundingClientRect(); return `${Math.round(r.width)}x${Math.round(r.height)}`; }).join(', '))));
  await mp.evaluate(() => window.scrollTo(0, 0));
  await shot(mp, '14-mobile-top', false);
  await mctx.close();

  // ---- 15. tablet
  const tctx = await browser.newContext({ viewport: { width: 820, height: 1180 }, locale: 'it-IT', storageState: state });
  const tp = await tctx.newPage(); wire(tp, 'tablet');
  await tp.goto(PAGE_URL, { waitUntil: 'domcontentloaded' });
  await tp.waitForSelector('h1:has-text("Valutazione Rischio Incendio")', { timeout: 120000 });
  await tp.waitForFunction(() => !document.body.innerText.includes('Caricamento…'), null, { timeout: 120000 });
  await waitMeasures(tp); await tp.waitForTimeout(500);
  const tov = await tp.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
  check('tablet.no.horizontal.overflow', tov.sw <= tov.cw, JSON.stringify(tov));
  await tp.evaluate(() => window.scrollTo(0, 1000)); await tp.waitForTimeout(300);
  info('tablet.sticky', JSON.stringify(await tp.evaluate(stickyEval)));
  await shot(tp, '15-tablet', true);
  await tctx.close();
} catch (e) {
  failed = true;
  console.error('WALKTHROUGH BROKE', e);
  await shot(page, '99-error', true).catch(() => {});
} finally {
  const pageErrors = report.console.filter((c) => c.type === 'pageerror');
  info('console.issues', `${report.console.length} console errors/warnings (${pageErrors.length} uncaught page errors)`);
  for (const c of report.console.slice(0, 8)) console.log('  CONSOLE', c.tag, c.type, c.text.slice(0, 200).replace(/\n/g, ' '));
  const uniq = [...new Map(report.http4xx.map((h) => [h.status + h.url, h])).values()];
  info('http.4xx5xx', uniq.length + ' distinct failing responses: ' + uniq.slice(0, 8).map((h) => `${h.status} ${h.url}`).join(' ; '));
  info('network.session.fetches', `${report.network.filter((n) => n.url.includes('/api/auth/session')).length} calls to /api/auth/session during the run (${report.network.filter((n) => n.url.includes('/api/v1/')).length} API calls)`);
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  console.log(`\n${summary.pass} PASS · ${summary.fail} FAIL · screenshots + report.json in ${OUT}`);
  await browser.close();
  process.exit(failed ? 1 : 0);
}
