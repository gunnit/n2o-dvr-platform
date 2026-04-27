// Shared Azienda field validators — single source of truth for the
// regexes used by both the survey wizard (Step Azienda) and the
// "Nuova Azienda" / "Modifica Azienda" pages. If the format ever
// changes, update it here only.

// Italian VAT number: exactly 11 digits.
export const PARTITA_IVA_REGEX = /^\d{11}$/;

// ATECO classification code. The wizard historically required the
// fully qualified XX.YY.ZZ form; we keep that format as the canonical
// one (matches every example in the templates and the placeholder
// "Es. 56.10.11").
export const ATECO_REGEX = /^\d{2}\.\d{2}\.\d{2}$/;

export type AziendaFieldErrors = {
  ragione_sociale?: string;
  partita_iva?: string;
  codice_ateco?: string;
};

export function validatePartitaIva(value: string | null | undefined): string | undefined {
  if (!value) return undefined;
  const trimmed = value.trim();
  if (trimmed === "") return undefined;
  if (!PARTITA_IVA_REGEX.test(trimmed)) {
    return "La partita IVA deve essere di 11 cifre";
  }
  return undefined;
}

export function validateCodiceAteco(value: string | null | undefined): string | undefined {
  if (!value) return undefined;
  const trimmed = value.trim();
  if (trimmed === "") return undefined;
  if (!ATECO_REGEX.test(trimmed)) {
    return "Formato non valido (es. 56.10.11)";
  }
  return undefined;
}

export function validateRagioneSociale(value: string | null | undefined): string | undefined {
  if (!value || value.trim() === "") return "Campo obbligatorio";
  return undefined;
}

/**
 * Run all validators and return only the populated errors. Useful at
 * submit-time when we must block the request if anything is invalid.
 */
export function validateAziendaCore(input: {
  ragione_sociale?: string | null;
  partita_iva?: string | null;
  codice_ateco?: string | null;
}): AziendaFieldErrors {
  const errors: AziendaFieldErrors = {};
  const rs = validateRagioneSociale(input.ragione_sociale);
  if (rs) errors.ragione_sociale = rs;
  const piva = validatePartitaIva(input.partita_iva);
  if (piva) errors.partita_iva = piva;
  const ateco = validateCodiceAteco(input.codice_ateco);
  if (ateco) errors.codice_ateco = ateco;
  return errors;
}
