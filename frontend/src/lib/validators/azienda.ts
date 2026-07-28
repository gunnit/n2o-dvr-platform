// Shared Azienda field validators — single source of truth for the
// regexes used by both the survey wizard (Step Azienda) and the
// "Nuova Azienda" / "Modifica Azienda" pages. If the format ever
// changes, update it here only.

// Italian VAT number: exactly 11 digits.
export const PARTITA_IVA_REGEX = /^\d{11}$/;

// ATECO classification code.
//
// Mirrors `_CODICE_ATECO_RE` in `backend/app/schemas/azienda.py`, which is the
// authority — the API re-validates every write, so a stricter rule here can
// only reject input the server would have accepted.
//
// It used to be `^\d{2}\.\d{2}\.\d{2}$`, i.e. the fully qualified six-digit
// form only. Real ATECO codes are legitimately shorter at the intermediate
// levels (`45.20` divisione, `45.20.1` categoria), so the registry lookup
// behind "Compila con AI" returned values — `19.20.1` for ENI — that this
// form then refused to save. The survey wizard meanwhile carried a third,
// different regex of its own. One rule, defined here.
export const ATECO_REGEX = /^\d{2}\.\d{2}(\.\d{1,2})?$/;

// Personal codice fiscale (titolare ditta individuale): 16 alphanumeric chars.
// Companies that aren't ditta individuale can have an 11-digit CF that equals
// the P.IVA, so the strict 16-char rule only applies when the form context
// flags this as a ditta individuale CF (see validateCodiceFiscaleDitta).
export const CODICE_FISCALE_PERSONA_REGEX = /^[A-Z0-9]{16}$/;

export type AziendaFieldErrors = {
  ragione_sociale?: string;
  partita_iva?: string;
  codice_ateco?: string;
  codice_fiscale?: string;
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
    // Name the accepted shapes rather than a single example: the previous
    // message showed "es. 56.10.11" while silently rejecting 56.10, which
    // reads as though the value were wrong rather than the rule.
    return "Formato non valido: usa XX.XX, XX.XX.X o XX.XX.XX (es. 45.20, 45.20.1, 56.10.11)";
  }
  return undefined;
}

export function validateRagioneSociale(value: string | null | undefined): string | undefined {
  if (!value || value.trim() === "") return "Campo obbligatorio";
  return undefined;
}

/**
 * Validate the codice fiscale field when the azienda is a ditta individuale.
 * Empty values pass (CF is optional), but if present it must be the 16-char
 * alphanumeric personal CF — not the 11-digit company P.IVA.
 */
export function validateCodiceFiscaleDitta(
  value: string | null | undefined,
): string | undefined {
  if (!value) return undefined;
  const trimmed = value.trim().toUpperCase();
  if (trimmed === "") return undefined;
  if (!CODICE_FISCALE_PERSONA_REGEX.test(trimmed)) {
    return "Per ditta individuale: 16 caratteri alfanumerici (CF del titolare)";
  }
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
