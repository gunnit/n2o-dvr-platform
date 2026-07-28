/**
 * Sanity-check the fascicolo stack geometry without a browser.
 *
 * The landing's scroll animation is driven by requestAnimationFrame, which does
 * not run in a headless/hidden tab, so the maths cannot be verified by driving
 * the real page. It is pure, though, so it can be checked directly.
 *
 *   node scripts/check-stack-geometry.mjs
 */

import { readFileSync } from "node:fs";

const SOURCE = "src/components/landing/fascicolo-stack.tsx";
const COUNT = 17;

// Pull the function out of the TSX rather than duplicating it here: a copy
// would drift and quietly stop testing the real thing.
const src = readFileSync(SOURCE, "utf8");
const start = src.indexOf("export function computeStackFrame");
const end = src.indexOf("\n}\n", start) + 3;
if (start < 0 || end < 3) {
  console.error(`FAIL: computeStackFrame not found in ${SOURCE}`);
  process.exit(1);
}
const body = src
  .slice(start, end)
  .replace("export function", "function")
  .replace(/: \{ frames: SheetFrame\[\]; active: number \}/, "")
  .replace(/progress: number,\s*count: number,/, "progress, count,")
  .replace(/const frames: SheetFrame\[\] = \[\];/, "const frames = [];");

const SPACING = 300;
const computeStackFrame = new Function(
  "SPACING",
  `${body}; return computeStackFrame;`,
)(SPACING);

const failures = [];
function check(label, ok, detail = "") {
  if (!ok) failures.push(`${label}${detail ? " — " + detail : ""}`);
}

// 1. The index sweeps the whole fascicolo, first to last, and never goes out
//    of range. A transcription slip in the travel window shows up here.
const seen = new Set();
let previous = -1;
for (let step = 0; step <= 400; step++) {
  const progress = step / 400;
  const { frames, active } = computeStackFrame(progress, COUNT);

  check(`active in range at p=${progress.toFixed(3)}`, active >= 0 && active < COUNT, `got ${active}`);
  check(`active never goes backwards at p=${progress.toFixed(3)}`, active >= previous, `${previous} -> ${active}`);
  previous = active;
  seen.add(active);

  check(`frame count at p=${progress.toFixed(3)}`, frames.length === COUNT, `got ${frames.length}`);
  for (const [i, f] of frames.entries()) {
    if (f.hidden) continue;
    check(`opacity 0..1 (sheet ${i}, p=${progress.toFixed(3)})`, f.opacity >= 0 && f.opacity <= 1, String(f.opacity));
    check(`blur 0..5 (sheet ${i}, p=${progress.toFixed(3)})`, f.blur >= 0 && f.blur <= 5, String(f.blur));
    check(`transform finite (sheet ${i}, p=${progress.toFixed(3)})`, !/NaN|Infinity/.test(f.transform), f.transform);
  }
}

check(`every one of the ${COUNT} documents becomes active`, seen.size === COUNT, `only ${seen.size} did`);
check("starts on the DVR", computeStackFrame(0, COUNT).active === 0);
check("ends on the last sheet", computeStackFrame(1, COUNT).active === COUNT - 1);

// 2. The section opens on a deck receding into depth — that image is the whole
//    point of the sticky stack — and closes empty, so the next section is not
//    scrolled into behind a leftover card.
const atStart = computeStackFrame(0, COUNT).frames.filter((f) => !f.hidden && f.opacity > 0.05);
const atEnd = computeStackFrame(1, COUNT).frames.filter((f) => !f.hidden && f.opacity > 0.05);
check("a deck is visible at the start", atStart.length >= 5 && atStart.length <= 12, `${atStart.length} visible`);
check("the deck is spent at the end", atEnd.length === 0, `${atEnd.length} still visible`);

// The far sheets must recede rather than pile up flat: opacity falls away and
// blur grows with depth.
const openingFrames = computeStackFrame(0, COUNT).frames.filter((f) => !f.hidden);
const front = openingFrames[0];
const back = openingFrames[openingFrames.length - 1];
check("front sheet is fully opaque", front.opacity === 1, String(front.opacity));
check("back sheet has faded", back.opacity < 0.3, String(back.opacity));
check("back sheet is blurred", back.blur > 1, String(back.blur));
check("front sheet is sharp", front.blur === 0, String(front.blur));
check("front sheet stacks above the back one", front.zIndex > back.zIndex);

if (failures.length) {
  console.error(`FAIL (${failures.length}):`);
  for (const f of failures.slice(0, 15)) console.error("  " + f);
  process.exit(1);
}
console.log(`OK — stack geometry sound across 401 scroll positions, all ${COUNT} documents surface.`);
