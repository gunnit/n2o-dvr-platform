// Mirror of backend/app/services/pericolo_suggester.py:
// _TIPO_BUCKETS + CANONICAL_TIPI + normalize_ambiente_tipo. The ambiente
// picker (step-ambienti.tsx TIPI_AMBIENTE) accepts free text but the
// downstream lookup tables in step-rischi.tsx (default P/D matrix,
// applicable categories, per-ambiente category subset) only key off these
// 9 canonical buckets — so every free-text tipo must be mapped here
// before any lookup. Backend already does this for AI suggestions and
// pericoli filtering; the frontend was the missing piece.
//
// IMPORTANT: keep the bucket order identical to the backend. Order
// matters because we do substring matching and the *first* hit wins —
// e.g. "cucina industriale" must come before "cucina".

export const CANONICAL_TIPI = [
  "ufficio",
  "magazzino",
  "cucina",
  "produzione",
  "laboratorio",
  "esterno",
  "negozio",
  "officina",
  "altro",
] as const;

export type CanonicalTipo = (typeof CANONICAL_TIPI)[number];

const CANONICAL_SET: ReadonlySet<string> = new Set(CANONICAL_TIPI);

const TIPO_BUCKETS: ReadonlyArray<readonly [string, CanonicalTipo]> = [
  ["ufficio direzionale", "ufficio"],
  ["ufficio", "ufficio"],
  ["open space", "ufficio"],
  ["sala riunioni", "ufficio"],
  ["sala corsi", "ufficio"],
  ["aula formazione", "ufficio"],
  ["reception", "ufficio"],
  ["accoglienza", "ufficio"],
  ["sala server", "ufficio"],
  ["ced", "ufficio"],
  ["aula scolastica", "ufficio"],
  ["sala d'attesa", "ufficio"],
  // Order matters: "cucina industriale" before "cucina"
  ["cucina industriale", "cucina"],
  ["cucina", "cucina"],
  ["sala mensa", "cucina"],
  ["refettorio", "cucina"],
  ["bar", "cucina"],
  ["caffetteria", "cucina"],
  ["magazzino", "magazzino"],
  ["deposito", "magazzino"],
  ["archivio", "magazzino"],
  ["area carico", "magazzino"],
  ["laboratorio chimico", "laboratorio"],
  ["laboratorio analisi", "laboratorio"],
  ["laboratorio", "laboratorio"],
  ["studio medico", "laboratorio"],
  ["ambulatorio", "laboratorio"],
  ["officina meccanica", "officina"],
  ["officina elettrica", "officina"],
  ["officina", "officina"],
  ["capannone produttivo", "produzione"],
  ["reparto produzione", "produzione"],
  ["linea di assemblaggio", "produzione"],
  ["produzione", "produzione"],
  ["showroom", "negozio"],
  ["sala esposizione", "negozio"],
  ["punto vendita", "negozio"],
  ["negozio", "negozio"],
  ["area esterna", "esterno"],
  ["cortile", "esterno"],
  ["parcheggio", "esterno"],
  ["cantiere", "esterno"],
  ["esterno", "esterno"],
  ["bagno", "altro"],
  ["servizi igienici", "altro"],
  ["spogliatoio", "altro"],
  ["locale tecnico", "altro"],
  ["centrale termica", "altro"],
  ["cabina elettrica", "altro"],
  ["palestra", "altro"],
];

export function normalizeAmbienteTipo(
  tipo: string | null | undefined,
): CanonicalTipo {
  if (!tipo) return "altro";
  const t = tipo.trim().toLowerCase();
  if (CANONICAL_SET.has(t)) return t as CanonicalTipo;
  for (const [needle, bucket] of TIPO_BUCKETS) {
    if (t.includes(needle)) return bucket;
  }
  return "altro";
}

const TIPO_LABEL: Record<CanonicalTipo, string> = {
  ufficio: "Ufficio",
  magazzino: "Magazzino",
  cucina: "Cucina",
  produzione: "Produzione",
  laboratorio: "Laboratorio",
  esterno: "Esterno",
  negozio: "Negozio",
  officina: "Officina",
  altro: "Altro",
};

export function canonicalTipoLabel(tipo: CanonicalTipo): string {
  return TIPO_LABEL[tipo];
}
