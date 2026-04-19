#!/usr/bin/env node
// Copies the user guide Markdown + screenshots from ../docs/guida/ into
// ./public/guida/ so Next.js can serve them and the server component can
// read the MD from process.cwd()/public/guida/GUIDA_UTENTE.md. Runs as
// `prebuild` and `predev` via package.json. Run manually after editing
// the guide to refresh the in-app copy.

import { cp, mkdir, access } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const source = resolve(here, "../../docs/guida");
const dest = resolve(here, "../public/guida");

try {
  await access(source);
} catch {
  console.warn(`[sync-guide-assets] source not found at ${source} — skipping`);
  process.exit(0);
}

await mkdir(dest, { recursive: true });
await cp(source, dest, { recursive: true });
console.log(`[sync-guide-assets] synced ${source} → ${dest}`);
