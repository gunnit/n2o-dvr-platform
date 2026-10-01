import assert from "node:assert/strict";
import test from "node:test";

import {
  DANNO_LABELS,
  PROBABILITA_LABELS,
  RISK_BANDS,
  SCALE,
  riskBand,
  riskIndex,
} from "../src/components/landing/risk.ts";
import {
  CARD_DELAY_MS,
  DEPTH,
  HERO_PINS,
  SCAN_FROM,
  SCAN_MS,
  SCAN_TO,
  msToReach,
  scanAt,
  scanEase,
} from "../src/components/landing/hero-scene.ts";

// The public page shows the risk index as numbers an RSPP can check. These
// tests hold it to backend/app/services/risk_calculator.py: I = 2·D + P on
// 1–4 scales, banded 3–4 / 5–6 / 7–8 / 9–12.

test("riskIndex is 2·D + P on every combination of the two 1–4 scales", () => {
  for (const d of SCALE) {
    for (const p of SCALE) {
      assert.equal(riskIndex(d, p), 2 * d + p, `D ${d} · P ${p}`);
    }
  }
  assert.equal(riskIndex(1, 1), 3);
  assert.equal(riskIndex(4, 4), 12);
  // Not the textbook P × D, and not symmetric: damage weighs double.
  assert.notEqual(riskIndex(1, 4), riskIndex(4, 1));
});

test("riskIndex rejects values outside the scales, as the backend does", () => {
  for (const [d, p] of [
    [0, 2],
    [5, 2],
    [2, 0],
    [2, 5],
    [1.5, 2],
    [2, Number.NaN],
  ]) {
    assert.throws(() => riskIndex(d, p), RangeError, `D ${d} · P ${p}`);
  }
});

test("riskBand follows the four DVR levels and their deadlines", () => {
  const expected = {
    3: "accettabile",
    4: "accettabile",
    5: "modesto",
    6: "modesto",
    7: "grave",
    8: "grave",
    9: "gravissimo",
    10: "gravissimo",
    11: "gravissimo",
    12: "gravissimo",
  };
  for (const [index, key] of Object.entries(expected)) {
    assert.equal(riskBand(Number(index)).key, key, `I ${index}`);
  }
  assert.throws(() => riskBand(2), RangeError);
  assert.throws(() => riskBand(13), RangeError);

  // Same order, ranges and timeframes as the DVR Master's level table
  // (dvr_master.py _RISK_LEVEL_TABLE_ROWS: Continuo / 1 anno / 6 mesi / Immediatamente).
  assert.deepEqual(
    RISK_BANDS.map((b) => [b.label, b.min, b.max, b.timeframe]),
    [
      ["Accettabile", 3, 4, "Monitoraggio continuo"],
      ["Modesto", 5, 6, "Entro 1 anno"],
      ["Grave", 7, 8, "Entro 6 mesi"],
      ["Gravissimo", 9, 12, "Immediatamente"],
    ],
  );
  // Bands tile 3..12 with no gap and no overlap.
  for (let i = 1; i < RISK_BANDS.length; i++) {
    assert.equal(RISK_BANDS[i].min, RISK_BANDS[i - 1].max + 1);
  }
});

test("scale labels are complete and in order", () => {
  assert.deepEqual(Object.keys(DANNO_LABELS).map(Number), [...SCALE]);
  assert.deepEqual(Object.keys(PROBABILITA_LABELS).map(Number), [...SCALE]);
  assert.equal(PROBABILITA_LABELS[1], "Bassa");
  assert.equal(PROBABILITA_LABELS[4], "Elevata");
  assert.equal(DANNO_LABELS[1], "Trascurabile");
  assert.equal(DANNO_LABELS[4], "Ingente");
});

test("hero pins are a valid worked example, one per level", () => {
  const bands = HERO_PINS.map((pin) => riskBand(riskIndex(pin.danno, pin.probabilita)).key);
  assert.deepEqual([...bands].sort(), ["accettabile", "grave", "gravissimo", "modesto"]);

  const cards = HERO_PINS.filter((pin) => pin.placement.kind === "card");
  assert.equal(cards.length, 1, "exactly one pin carries the worked-example card");
  const [card] = cards;
  // The card prints "I = 2·4 + 2 = 10": keep the arithmetic and the band honest.
  assert.equal(card.id, "saldatura");
  assert.equal(riskIndex(card.danno, card.probabilita), 10);
  assert.equal(riskBand(10).key, "gravissimo");
  assert.ok(card.hazard, "the card shows a hazard line");
});

test("hero pin geometry is inside the stage and leaders meet their labels", () => {
  const ids = new Set();
  for (const pin of HERO_PINS) {
    assert.ok(!ids.has(pin.id), `duplicate id ${pin.id}`);
    ids.add(pin.id);
    for (const v of [pin.head.x, pin.head.y, pin.base.x, pin.base.y, pin.placement.x, pin.placement.y]) {
      assert.ok(v >= 0 && v <= 1, `${pin.id}: ${v} outside the stage`);
    }
    assert.ok(pin.head.y < pin.base.y, `${pin.id}: head must sit above its base`);
    assert.ok(Math.abs(pin.head.x - pin.base.x) < 0.01, `${pin.id}: stems are vertical`);

    const { kind, x, y } = pin.placement;
    if (kind === "left") assert.ok(x < pin.head.x, `${pin.id}: a left chip ends left of its leader`);
    if (kind === "right") assert.ok(x > pin.head.x, `${pin.id}: a right chip starts right of its leader`);
    if (kind === "above") {
      assert.ok(x < pin.head.x, `${pin.id}: the leader must land inside the chip`);
      assert.ok(y < pin.head.y, `${pin.id}: an "above" chip sits above the head`);
    }
    if (kind === "card") assert.ok(y > pin.base.y, `${pin.id}: the card hangs below the pin`);
  }
});

test("the scan reaches every pin, in order, inside the sweep", () => {
  const scans = HERO_PINS.map((pin) => pin.scan);
  for (const s of scans) assert.ok(s > SCAN_FROM && s < SCAN_TO, `scan ${s} outside the sweep`);

  // Easing is monotonic and pinned at both ends.
  assert.equal(scanEase(0), 0);
  assert.equal(scanEase(1), 1);
  let previous = -Infinity;
  for (let t = 0; t <= 1.0001; t += 0.01) {
    const v = scanAt(t);
    assert.ok(v >= previous, `scanAt not monotonic at t=${t}`);
    previous = v;
  }
  assert.equal(scanAt(0), SCAN_FROM);
  assert.equal(scanAt(1), SCAN_TO);

  // msToReach inverts scanAt to within a frame.
  for (const s of scans) {
    const ms = msToReach(s);
    assert.ok(ms > 0 && ms < SCAN_MS, `pin at ${s} reached at ${ms}ms`);
    assert.ok(Math.abs(scanAt(ms / SCAN_MS) - s) < 0.01, `msToReach(${s}) is off`);
  }

  // The card appears after the last pin, while the page is still on screen.
  const last = Math.max(...scans.map(msToReach));
  assert.ok(last + CARD_DELAY_MS < 4000);
});

test("depth constants describe a usable scan plane and ground", () => {
  const [lo, hi] = DEPTH.scanRange;
  assert.ok(hi > lo);
  assert.equal(DEPTH.scanAxis.length, 3);
  assert.equal(DEPTH.ground.length, 5);
  assert.ok(DEPTH.focus > 0 && DEPTH.focus < 1);
});
