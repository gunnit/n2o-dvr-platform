import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
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
  STAGE,
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
      assert.equal(riskIndex({ danno: d, probabilita: p }), 2 * d + p, `D ${d} · P ${p}`);
    }
  }
  assert.equal(riskIndex({ danno: 1, probabilita: 1 }), 3);
  assert.equal(riskIndex({ danno: 4, probabilita: 4 }), 12);
  // Not the textbook P × D, and not symmetric: damage weighs double.
  assert.equal(riskIndex({ danno: 4, probabilita: 1 }), 9);
  assert.equal(riskIndex({ danno: 1, probabilita: 4 }), 6);
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
    assert.throws(() => riskIndex({ danno: d, probabilita: p }), RangeError, `D ${d} · P ${p}`);
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

  // Word for word the DVR Master's level table
  // (backend/app/services/document_generator/dvr_master.py, _RISK_LEVEL_TABLE_ROWS):
  // the matrix promises the visitor these are what the DVR prints.
  assert.deepEqual(
    RISK_BANDS.map((b) => [`${b.min}-${b.max}`, b.label.toUpperCase(), b.action, b.timeframe]),
    [
      ["3-4", "ACCETTABILE", "Monitoraggio", "Continuo"],
      ["5-6", "MODESTO", "Strumenti di minimizzazione", "1 anno"],
      ["7-8", "GRAVE", "Sensibilizzazione + controllo", "6 mesi"],
      ["9-12", "GRAVISSIMO", "Ricerca urgente misure", "Immediatamente"],
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
  const bands = HERO_PINS.map((pin) => riskBand(riskIndex(pin)).key);
  assert.deepEqual([...bands].sort(), ["accettabile", "grave", "gravissimo", "modesto"]);

  const cards = HERO_PINS.filter((pin) => pin.placement.kind === "card");
  assert.equal(cards.length, 1, "exactly one pin carries the worked-example card");
  const [card] = cards;
  // The card prints "I = 2·4 + 2 = 10": keep the arithmetic and the band honest.
  assert.equal(card.id, "saldatura");
  assert.equal(riskIndex(card), 10);
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
      // Right-aligned on x, so the leader lands inside it at any width as
      // long as the chip is at least (x - head.x) wide: ~5% of the stage.
      assert.ok(x > pin.head.x && x - pin.head.x < 0.1, `${pin.id}: the leader must land inside the chip`);
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

test("STAGE is the shipped image's real size (the stage's aspect comes from it)", () => {
  const size = webpSize(new URL("../src/components/landing/assets/officina-modello.webp", import.meta.url));
  assert.deepEqual(size, { width: STAGE.width, height: STAGE.height });
  const depth = webpSize(new URL("../src/components/landing/assets/officina-profondita.webp", import.meta.url));
  // Powers of two: WebGL1 can only mipmap those, and the scan needs the mips.
  for (const side of [depth.width, depth.height]) assert.equal(side & (side - 1), 0, `${side} is not a power of two`);
});

/** Width and height from a WebP's RIFF header (lossy, lossless or extended). */
function webpSize(url) {
  const b = readFileSync(url);
  assert.equal(b.toString("ascii", 0, 4), "RIFF");
  assert.equal(b.toString("ascii", 8, 12), "WEBP");
  const chunk = b.toString("ascii", 12, 16);
  if (chunk === "VP8 ") return { width: b.readUInt16LE(26) & 0x3fff, height: b.readUInt16LE(28) & 0x3fff };
  if (chunk === "VP8L") {
    const bits = b.readUInt32LE(21);
    return { width: (bits & 0x3fff) + 1, height: ((bits >> 14) & 0x3fff) + 1 };
  }
  if (chunk === "VP8X") return { width: b.readUIntLE(24, 3) + 1, height: b.readUIntLE(27, 3) + 1 };
  throw new Error(`unknown WebP chunk ${chunk}`);
}

test("depth constants describe a usable scan plane and ground", () => {
  const [lo, hi] = DEPTH.scanRange;
  assert.ok(hi > lo);
  assert.equal(DEPTH.scanAxis.length, 3);
  assert.equal(DEPTH.ground.length, 5);
  assert.ok(DEPTH.focus > 0 && DEPTH.focus < 1);
});
