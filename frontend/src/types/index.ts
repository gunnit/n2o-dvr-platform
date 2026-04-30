export interface Azienda {
  id: string;
  ragione_sociale: string;
  partita_iva: string | null;
  codice_fiscale: string | null;
  forma_giuridica: string | null;
  sede_legale_via: string | null;
  sede_legale_citta: string | null;
  cap_legale: string | null;
  provincia_legale: string | null;
  sede_operativa_via: string | null;
  sede_operativa_citta: string | null;
  cap_operativa: string | null;
  provincia_operativa: string | null;
  attivita: string | null;
  codice_ateco: string | null;
  pec: string | null;
  email: string | null;
  telefono: string | null;
  sito_web: string | null;
  numero_dipendenti_dichiarati: number | null;
  data_costituzione: string | null;
  capitale_sociale: number | null;
  rea: string | null;
  orario_lavoro: string | null;
  metratura_totale: number | null;
  zona_sismica: number | null;
  descrizione_attivita: string | null;
  contesto_territoriale: string | null;
  data_scadenza_dvr: string | null;
  // US-1.6: "firmato" is the post-signature state; "in_revisione" opens the
  // audited edit window; the earlier lifecycle values stay valid for legacy
  // rows. Keep this open-ended (string) to tolerate migration drift — the
  // wizard only checks for "firmato" explicitly.
  survey_status:
    | "draft"
    | "in_progress"
    | "completed"
    | "firmato"
    | "in_revisione"
    | string;
  // US-1.6 signature metadata — populated server-side by
  // POST /aziende/{id}/survey/sign. The PNG bytes themselves live on
  // `aziende.firma_png` (deferred column) and are streamed via the
  // signature download endpoint.
  firma_signed_at?: string | null;
  firma_signed_by_name?: string | null;
  // US-2.1 AC1: ISO timestamp set when a visura camerale PDF is uploaded.
  // The PDF + redacted snippet stay server-side; the frontend only uses
  // this field to render the "visura caricata" hint above the description
  // editor. Optional so older clients still type-check.
  visura_uploaded_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Persona {
  id: string;
  azienda_id: string;
  nominativo: string;
  codice_fiscale: string | null;
  mansione: string | null;
  tipologia_contrattuale: string | null;
  sesso: "M" | "F" | null;
  fascia_eta: ">18" | "15-18" | null;
  ruolo_rspp: boolean;
  ruolo_rls: boolean;
  ruolo_primo_soccorso: boolean;
  ruolo_antincendio: boolean;
  ruolo_preposto: boolean;
  ruolo_datore_lavoro: boolean;
  ruolo_medico_competente: boolean;
  // External consultant flag (feedback #10, 2026-04-29). Only meaningful
  // when ruolo_rspp or ruolo_medico_competente is true; the DVR
  // organigramma renders an "(esterno)" suffix when set.
  is_esterno?: boolean;
  // Free-text note alongside the structured `attrezzature_speciali` flags.
  // Originally "qualifiche" (US-1.4), kept as a note field after 2026-04-28.
  qualifiche: string | null;
  attrezzature_speciali: AttrezzaturaSpecialeCode[];
  ambiente_ids: string[];
}

export type AttrezzaturaSpecialeCode =
  | "lavori_in_quota"
  | "trabattelli"
  | "ponteggi"
  | "carrello_elevatore"
  | "ple"
  | "gru"
  | "ruspa_escavatore"
  | "patente_cde"
  | "adr";

export interface Ambiente {
  id: string;
  azienda_id: string;
  nome: string;
  tipo: string;
  superficie_mq: number | null;
  preposto_id: string | null;
  descrizione_attivita: string | null;
}

export type LivelloRischio =
  | "ACCETTABILE"
  | "MODESTO"
  | "GRAVE"
  | "GRAVISSIMO";

export interface ValutazioneRischio {
  id: string;
  ambiente_id: string;
  categoria_rischio: string;
  applicabile: boolean;
  pericolo: string | null;
  condizioni_esposizione: string | null;
  rischio: string | null;
  misure_prevenzione: string | null;
  probabilita_p: number | null;
  danno_d: number | null;
  indice_i: number | null;
  livello_rischio: LivelloRischio | null;
}

// Phase 3 (1:N) — child of ValutazioneRischio. The DVR Schede Specifiche
// expect N pericolo rows per (ambiente, categoria); each maps to a row in
// pericoli_valutazione. Catalog rows live in PericoloLibreria; custom rows
// have pericolo_libreria_id null and source "custom".
export interface PericoloLibreria {
  id: string;
  code: string;
  categoria: string;
  macro_categoria: string;
  pericolo: string;
  condizioni_esposizione: string | null;
  rischio: string | null;
  misure_prevenzione: string | null;
  p_default: number | null;
  d_default: number | null;
  valutazione_riferimento: string | null;
  ambiente_tipi: string[];
  attrezzatura_keywords: string[];
}

export interface PericoloSuggestionItem {
  pericolo: PericoloLibreria;
  matches_ambiente: boolean;
  triggered_by_attrezzature: string[];
}

export interface PericoloSuggestionResponse {
  ambiente_tipo: string | null;
  attrezzature_count: number;
  items: PericoloSuggestionItem[];
}

export interface PericoloValutazione {
  id: string;
  valutazione_rischio_id: string;
  pericolo_libreria_id: string | null;
  source: "catalog" | "custom";
  pericolo: string;
  condizioni_esposizione: string | null;
  rischio: string | null;
  misure_prevenzione: string | null;
  probabilita_p: number | null;
  danno_d: number | null;
  valutazione_riferimento: string | null;
  applicabile: boolean;
  ordine: number;
  indice_i: number | null;
  livello_rischio: LivelloRischio | null;
}

export interface DocumentoGenerato {
  id: string;
  azienda_id: string;
  tipo_documento: string;
  versione: number;
  // Backend emits these five; legacy "generating"/"ready"/"error"/"failed"
  // values are kept only for older records that may still be in the DB.
  // "bozza" is the US-2.8 AC3 rollback state: a generation attempt failed
  // and the record was reset — partial file discarded, error_message set.
  status:
    | "pending"
    | "in_progress"
    | "completed"
    | "bozza"
    | "failed"
    | "generating"
    | "ready"
    | "error";
  file_path: string | null;
  gdrive_file_id: string | null;
  // Editable Google Doc ID + derived edit URL, populated after the user
  // has opened this document for in-browser editing. Both null on a fresh
  // generation; the documents page toggles the "Modifica in Google Docs"
  // button state on gdoc_file_id presence.
  gdoc_file_id?: string | null;
  gdoc_edit_url?: string | null;
  // True when this row was produced by syncing edits back from Google Docs
  // (i.e. options.edited_in_gdocs was set during generation). Surfaced in
  // the version-history drawer as a "Modificato in Google Docs" badge so
  // reviewers can distinguish AI-generated versions from human-edited ones.
  edited_in_gdocs?: boolean;
  // User-facing explanation when status === "bozza" (US-2.8 AC3).
  error_message?: string | null;
  created_at: string;
  // US-2.9: human-readable name of the user who triggered generation.
  // Resolved server-side via join on users.full_name. Optional so older
  // clients / records still type-check.
  generated_by_name?: string | null;
  // US-5.2 AC2: true when the survey changed between this document's
  // generation start and completion (or after completion via PUT
  // propagation). Documents page renders an amber "rigenera" banner.
  // Optional so legacy clients still type-check; backend defaults to
  // false on every emission.
  stale_snapshot?: boolean;
}

export interface Attrezzatura {
  id: string;
  azienda_id: string;
  // Phase 2.3 / bug B5 — every attrezzatura belongs to exactly one ambiente
  // of its azienda. Required on create; settable on update to move between
  // environments.
  ambiente_id: string;
  descrizione: string;
  marcatura_ce: boolean;
  verifiche_periodiche: boolean;
}

export type ExtractionStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed";

export interface SostanzaChimica {
  id: string;
  azienda_id: string;
  nome_prodotto: string;
  produttore: string | null;
  pittogrammi: string[];
  stato_miscela: string | null;
  frasi_h: string[];
  frasi_p: string[];
  // AI extraction metadata (US-1.9, US-1.10) — optional for manual entries
  ai_extracted?: boolean;
  ai_confidence?: number | null;
  extraction_status?: ExtractionStatus | null;
  extraction_error?: string | null;
  human_reviewed?: boolean;
  sds_file_path?: string | null;
  // Present on server-persisted rows; absent on locally-minted (pre-save)
  // manual entries. Used as the AI-provenance timestamp in the Revisione UI.
  created_at?: string;
}

export interface BatchUploadFileResult {
  filename: string;
  sostanza_id: string | null;
  status: "queued" | "failed";
  reason: string | null;
}

export interface BatchUploadResponse {
  results: BatchUploadFileResult[];
}

export interface BatchStatusItem {
  sostanza_id: string;
  nome_prodotto: string;
  extraction_status: ExtractionStatus | null;
  extraction_error: string | null;
  ai_confidence: number | null;
}

export interface BatchStatusResponse {
  items: BatchStatusItem[];
}

export type UserRole = "admin" | "operatore_ufficio" | "operatore_campo";

// US-1.3 photo uploads
export interface AmbienteFoto {
  id: string;
  ambiente_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

// US-4.8 POS DPI matrix
export interface DpiCatalog {
  roles: string[];
  phases: string[];
  dpi_catalog: Record<string, string>;
}

export interface DpiMatrix {
  [phase: string]: { [role: string]: string[] };
}

export interface Pos {
  id: string;
  azienda_id: string;
  cantiere_indirizzo: string;
  dpi_matrix: DpiMatrix;
  dpi_matrix_roles: string[];
  dpi_matrix_phases: string[];
  // US-4.7: structured phase entries persisted as JSONB on the row.
  // Frontend imports the canonical zod-derived type from
  // `@/components/assessments/pos/phase-schema`; this `unknown[]` here keeps
  // the shared interface dependency-free and forces consumers to narrow.
  fasi_lavorative?: unknown[];
}

// US-4.7: re-export the zod-derived phase-builder types so consumers can
// `import type { PhaseValues } from "@/types"` without reaching into the
// component folder.
export type {
  PhaseValues,
  PhaseNioshValues,
  PhaseRumoreValues,
  PhaseVibrazioniValues,
  PhasesUpdateValues,
  FasciaRumore,
  ZonaNiosh,
} from "@/components/assessments/pos/phase-schema";

// Per-mansione DPI + rischi specifici (sorveglianza sanitaria).
// Backend model: MansioneSorveglianza. Keyed by (azienda_id, mansione_nome).
export interface MansioneSorveglianza {
  id: string;
  azienda_id: string;
  mansione_nome: string;
  dpi_codes: string[];
  rischi_specifici_codes: string[];
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface CatalogItem {
  code: string;
  etichetta: string;
}

export interface DpiCatalogGroup {
  area: string;
  items: CatalogItem[];
}

export interface DpiCatalogResponse {
  groups: DpiCatalogGroup[];
}

export interface RischiSpecificiCatalogGroup {
  macro: string;
  items: CatalogItem[];
}

export interface RischiSpecificiCatalogResponse {
  groups: RischiSpecificiCatalogGroup[];
}

// US-3.8 stress per-client measures library
export interface StressMisuraLibreria {
  id: string;
  azienda_id: string;
  livello_rischio: "Basso" | "Medio" | "Alto";
  testo: string;
  personalizzato: boolean;
  created_at: string;
}


// Azienda autofill — response from POST /aziende/autofill. The values map
// is a partial AziendaCreate; meta carries provenance per field so the UI
// can render "✨ AI" badges with source/confidence tooltips. Fields not
// derivable from the P.IVA are simply absent.
export type AziendaAutofillConfidence = "high" | "medium" | "low";

export interface AziendaAutofillFieldMeta {
  confidence: AziendaAutofillConfidence;
  source: string;
  source_url?: string | null;
}

export interface AziendaAutofillResponse {
  partita_iva: string;
  values: Partial<Record<keyof Azienda, string | number | null>>;
  meta: Partial<Record<keyof Azienda, AziendaAutofillFieldMeta>>;
  warnings: string[];
}
