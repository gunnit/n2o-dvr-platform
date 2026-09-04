/**
 * Types for the protocollo sanitario per mansione — mirror of
 * backend/app/schemas/protocollo_sanitario.py. Kept local to the feature
 * on purpose (not in src/types/index.ts).
 */

export type Fonte = "ai" | "manuale" | "ai_modificato";

export interface CodeItem {
  code: string;
  etichetta: string;
}

export interface Accertamento {
  esame: string;
  periodicita: string;
}

export interface MalattiaCorrelata {
  codice: string | null;
  malattia: string;
  riferimento: string | null;
}

export interface MalattiaRiferimento {
  codice: string;
  malattia: string;
  agente_o_rischio: string;
  tabella: string;
  tabellata: boolean;
  rischi_specifici_codes: string[];
  categorie: string[];
}

export interface ProtocolloSanitario {
  id: string;
  azienda_id: string;
  mansione: string;
  rischi_specifici: CodeItem[];
  accertamenti: Accertamento[];
  periodicita: string | null;
  malattie_correlate: MalattiaCorrelata[];
  note: string | null;
  fonte: Fonte;
  created_at: string;
  updated_at: string;
}

export interface MansioneItem {
  mansione: string;
  num_persone: number;
  rischi_specifici: CodeItem[];
  dpi: CodeItem[];
  malattie_riferimento: MalattiaRiferimento[];
  protocollo: ProtocolloSanitario | null;
}

export interface MansioniOverview {
  items: MansioneItem[];
  periodicita_options: string[];
}

export interface AccertamentoProposto extends Accertamento {
  motivazione: string;
}

export interface ProtocolloProposta {
  mansione: string;
  accertamenti: AccertamentoProposto[];
  periodicita: string;
  malattie_correlate: MalattiaCorrelata[];
  motivazione: string;
}

export interface ProtocolloUpsert {
  mansione: string;
  rischi_specifici: CodeItem[] | null;
  accertamenti: Accertamento[];
  periodicita: string | null;
  malattie_correlate: MalattiaCorrelata[];
  note: string | null;
  fonte: Fonte;
}

export const FONTE_LABELS: Record<Fonte, string> = {
  ai: "Proposta AI",
  ai_modificato: "AI, rivista",
  manuale: "Manuale",
};
