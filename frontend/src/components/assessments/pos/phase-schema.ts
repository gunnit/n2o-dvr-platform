/**
 * POS phase-builder zod schema (US-4.7).
 *
 * Shape mirrors the backend `app/schemas/pos_phase.py::PosPhase`:
 *   - id is a stable string assigned client-side (UUID or local-*)
 *   - ordine is the 0-based authoritative order; the backend renumbers
 *     to 0..n-1 on save
 *   - rischi/dpi/mezzi are flat string lists (the backend dedupes on save)
 *   - dipende_da carries the predecessor IDs (per-phase array, no
 *     separate edge table — keeps the JSONB compact)
 *   - niosh/rumore/vibrazioni mirror the per-phase snapshots from the
 *     backend's PhaseNiosh/PhaseRumore/PhaseVibrazioni sub-schemas
 *
 * The backend rejects extra keys (`extra="forbid"`), so we keep this
 * schema lean — anything not declared here will 400 on save.
 */

import { z } from "zod";

export const FASCIA_RUMORE_VALUES = ["<80", "80-85", "85-87", ">87"] as const;
export type FasciaRumore = (typeof FASCIA_RUMORE_VALUES)[number];

export const ZONA_NIOSH_VALUES = ["VERDE", "GIALLA", "ROSSA"] as const;
export type ZonaNiosh = (typeof ZONA_NIOSH_VALUES)[number];

export const phaseNioshSchema = z.object({
  peso_sollevato: z.number().gt(0).max(200),
  cp: z.number().gt(0).max(40),
  fattore_a: z.number().min(0).max(1),
  fattore_b: z.number().min(0).max(1),
  fattore_c: z.number().min(0).max(1),
  fattore_d: z.number().min(0).max(1),
  fattore_e: z.number().min(0).max(1),
  fattore_f: z.number().min(0).max(1),
  plr: z.number().nullable().optional(),
  ir: z.number().nullable().optional(),
  livello: z.enum(ZONA_NIOSH_VALUES).nullable().optional(),
});

export const phaseRumoreSchema = z.object({
  lex_8h_dba: z.number().min(0).max(140),
  fascia: z.enum(FASCIA_RUMORE_VALUES).nullable().optional(),
  dpi_obbligatori: z.boolean().default(false),
  note: z.string().max(500).nullable().optional(),
});

export const phaseVibrazioniSchema = z.object({
  a8_mano_braccio: z.number().min(0).max(30).nullable().optional(),
  a8_corpo_intero: z.number().min(0).max(30).nullable().optional(),
  entro_limiti: z.boolean().default(true),
  note: z.string().max(500).nullable().optional(),
});

export const phaseSchema = z.object({
  id: z.string().min(1).max(64),
  ordine: z.number().int().min(0).max(10_000),
  nome: z.string().min(1, "Nome fase richiesto").max(200),
  descrizione: z.string().max(4000).nullable().optional(),
  rischi: z.array(z.string()).default([]),
  dpi: z.array(z.string()).default([]),
  mezzi: z.array(z.string()).default([]),
  niosh: phaseNioshSchema.nullable().optional(),
  rumore: phaseRumoreSchema.nullable().optional(),
  vibrazioni: phaseVibrazioniSchema.nullable().optional(),
  dipende_da: z.array(z.string()).default([]),
});

export const phasesUpdateSchema = z.object({
  fasi: z.array(phaseSchema),
});

export type PhaseNioshValues = z.infer<typeof phaseNioshSchema>;
export type PhaseRumoreValues = z.infer<typeof phaseRumoreSchema>;
export type PhaseVibrazioniValues = z.infer<typeof phaseVibrazioniSchema>;
export type PhaseValues = z.infer<typeof phaseSchema>;
export type PhasesUpdateValues = z.infer<typeof phasesUpdateSchema>;

/** Build a fresh phase with sensible defaults and a local-* id. */
export function makeBlankPhase(ordine: number): PhaseValues {
  return {
    id: `local-${Math.random().toString(36).slice(2, 10)}`,
    ordine,
    nome: "",
    descrizione: null,
    rischi: [],
    dpi: [],
    mezzi: [],
    niosh: null,
    rumore: null,
    vibrazioni: null,
    dipende_da: [],
  };
}

/** Default sub-schema seed values used when the operator opts in via the UI. */
export const DEFAULT_NIOSH: PhaseNioshValues = {
  peso_sollevato: 15,
  cp: 25,
  fattore_a: 1,
  fattore_b: 1,
  fattore_c: 1,
  fattore_d: 1,
  fattore_e: 1,
  fattore_f: 1,
  plr: null,
  ir: null,
  livello: null,
};

export const DEFAULT_RUMORE: PhaseRumoreValues = {
  lex_8h_dba: 80,
  fascia: "<80",
  dpi_obbligatori: false,
  note: null,
};

export const DEFAULT_VIBRAZIONI: PhaseVibrazioniValues = {
  a8_mano_braccio: 0,
  a8_corpo_intero: 0,
  entro_limiti: true,
  note: null,
};
