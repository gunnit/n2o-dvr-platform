export interface Azienda {
  id: string;
  ragione_sociale: string;
  partita_iva: string | null;
  sede_legale_via: string | null;
  sede_legale_citta: string | null;
  sede_operativa_via: string | null;
  sede_operativa_citta: string | null;
  attivita: string | null;
  codice_ateco: string | null;
  orario_lavoro: string | null;
  metratura_totale: number | null;
  zona_sismica: number | null;
  descrizione_attivita: string | null;
  contesto_territoriale: string | null;
  survey_status: "draft" | "in_progress" | "completed";
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
}

export interface Ambiente {
  id: string;
  azienda_id: string;
  nome: string;
  tipo: string;
  superficie_mq: number | null;
  preposto_id: string | null;
  descrizione_attivita: string | null;
}

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
  livello_rischio: "ACCETTABILE" | "MODESTO" | "GRAVE" | "GRAVISSIMO" | null;
}

export interface DocumentoGenerato {
  id: string;
  azienda_id: string;
  tipo_documento: string;
  versione: number;
  status: "pending" | "generating" | "ready" | "error";
  file_path: string | null;
  gdrive_file_id: string | null;
  created_at: string;
}

export interface Attrezzatura {
  id: string;
  azienda_id: string;
  descrizione: string;
  marcatura_ce: boolean;
  verifiche_periodiche: boolean;
}

export interface SostanzaChimica {
  id: string;
  azienda_id: string;
  nome_prodotto: string;
  produttore: string | null;
  pittogrammi: string[];
  stato_miscela: string | null;
  frasi_h: string[];
  frasi_p: string[];
}

export type UserRole = "admin" | "operatore_ufficio" | "operatore_campo";
