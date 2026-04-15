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
