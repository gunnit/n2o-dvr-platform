/**
 * Shared types for the Gestanti (D.Lgs. 151/2001) assessment UI.
 *
 * Kept in a tiny module so the page component, the worker list, the match
 * panel and the relocation dialog can all import without circular deps.
 */

export type Allegato = "A" | "B" | "C";

export interface RiskMatch {
  risk_key: string;
  allegato: Allegato;
  descrizione: string;
  suggested_alternative_mansione: string | null;
  is_new: boolean;
  decision: "accept" | "reject" | null;
  justification: string | null;
  misura_alternativa: string | null;
}

export interface CrossReferenceResponse {
  worker_id: string;
  worker_nominativo: string;
  worker_mansione: string | null;
  cleared: boolean;
  matches: RiskMatch[];
  valutazione_id: string | null;
}

export interface FemaleWorker {
  id: string;
  nominativo: string;
  mansione: string | null;
}

// ---------------------------------------------------------------------------
// Preventive per-mansione assessment (art. 11 D.Lgs. 151/2001) — objective
// valutazione with no worker attached.
// ---------------------------------------------------------------------------

export type EsitoMansione =
  | "compatibile"
  | "compatibile_con_limitazioni"
  | "non_compatibile";

export interface CatalogRisk {
  risk_key: string;
  allegato: Allegato;
  descrizione: string;
}

export interface MansioneValutazione {
  id: string;
  azienda_id: string;
  mansione: string;
  esito: EsitoMansione;
  rischi: CatalogRisk[];
  misure: string | null;
  note: string | null;
  created_at: string;
}

export interface MansioneOverviewItem {
  mansione: string;
  num_persone: number;
  num_lavoratrici: number;
  suggested_risks: CatalogRisk[];
  valutazione: MansioneValutazione | null;
}

export interface MansioniOverview {
  items: MansioneOverviewItem[];
}

/**
 * POST .../gestanti/mansioni/suggerisci — the AI proposal for one mansione.
 *
 * Never persisted by the server: "Applica" copies it into the form, the
 * operator reviews and saves through PUT .../gestanti/mansioni. A
 * `non_compatibile` esito is a suggestion for the RSPP / medico competente
 * until that save.
 */
export interface GestantiMansioneSuggestion {
  mansione: string;
  /** INCOMPATIBLE_RISKS keys, already validated server-side. */
  rischi: string[];
  /** The catalog rows for `rischi`, so the UI needs no catalog copy. */
  rischi_dettaglio: CatalogRisk[];
  /** Free-text exposures the catalog has no key for. */
  rischi_aggiuntivi: string[];
  limitazioni: string[];
  esito_proposto: EsitoMansione;
  motivazione: string;
  riferimenti_normativi: string[];
  /** How many assessed DVR hazards the model reasoned over. */
  pericoli_considerati: number;
}
