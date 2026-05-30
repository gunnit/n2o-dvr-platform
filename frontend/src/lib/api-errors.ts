/**
 * Centralized FastAPI/Pydantic error translator.
 *
 * Problem: when validation fails the API returns
 *   { "detail": [{ "type": "less_than_equal", "loc": ["body","peso_kg"],
 *                  "msg": "Input should be less than or equal to 100",
 *                  "input": 101, "ctx": { "le": 100.0 } }] }
 * The default fetch handler stringifies that whole blob into the user's face.
 *
 * `parseApiError` turns it into a single Italian sentence the operator can act
 * on, plus optional per-field messages for inline display next to the input.
 */

type PydanticErrorItem = {
  type: string;
  loc: (string | number)[];
  msg: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
};

export type ParsedApiError = {
  /** Human-friendly Italian message safe to show as a toast or banner. */
  message: string;
  /** Field-name → message, keyed by the last segment of `loc`. */
  fieldErrors: Record<string, string>;
  /** Raw HTTP status. */
  status: number;
};

const FIELD_LABELS: Record<string, string> = {
  peso_kg: "Peso",
  peso_sollevato: "Peso sollevato",
  compito: "Descrizione compito",
  altezza_cm: "Altezza",
  dislocazione_cm: "Dislocazione verticale",
  distanza_cm: "Distanza orizzontale",
  angolo_gradi: "Angolo di asimmetria",
  frequenza_atti_min: "Frequenza",
  durata_min: "Durata",
  cp: "Costante di peso (CP)",
  fattore_a: "Fattore A",
  fattore_b: "Fattore B",
  fattore_c: "Fattore C",
  fattore_d: "Fattore D",
  fattore_e: "Fattore E",
  fattore_f: "Fattore F",
  postazione: "Postazione",
  ore_settimanali: "Ore settimanali",
  nome_area: "Nome area",
  inf: "INF",
  si: "SI",
  pi: "PI",
  temperatura_aria: "Temperatura aria",
  temperatura_radiante: "Temperatura radiante",
  velocita_aria: "Velocità aria",
  umidita_relativa: "Umidità relativa",
  metabolismo: "Metabolismo",
  isolamento_vestiario: "Isolamento vestiario",
  appaltatore_ragione_sociale: "Ragione sociale appaltatore",
  appaltatore_partita_iva: "Partita IVA",
  appaltatore_referente: "Referente",
  oggetto_appalto: "Oggetto appalto",
  rischio: "Rischio",
  misure: "Misure",
  custom_text: "Testo",
  lex_8h_dba: "Esposizione rumore (LEX,8h)",
  a8_mano_braccio: "Vibrazioni mano-braccio",
  a8_corpo_intero: "Vibrazioni corpo intero",
  justification: "Motivazione",
  misura_alternativa: "Misura alternativa",
  probabilita_p: "Probabilità (P)",
  danno_d: "Danno (D)",
};

function labelFor(fieldName: string): string {
  return FIELD_LABELS[fieldName] ?? fieldName;
}

function translatePydanticItem(item: PydanticErrorItem): string {
  const ctx = item.ctx ?? {};
  switch (item.type) {
    case "missing":
      return "campo obbligatorio";
    case "less_than":
      return `deve essere minore di ${ctx.lt}`;
    case "less_than_equal":
      return `deve essere minore o uguale a ${ctx.le}`;
    case "greater_than":
      return `deve essere maggiore di ${ctx.gt}`;
    case "greater_than_equal":
      return `deve essere maggiore o uguale a ${ctx.ge}`;
    case "string_too_long":
      return `massimo ${ctx.max_length} caratteri`;
    case "string_too_short":
      return `minimo ${ctx.min_length} caratteri`;
    case "int_parsing":
    case "int_type":
      return "deve essere un numero intero";
    case "float_parsing":
    case "float_type":
      return "deve essere un numero";
    case "string_type":
      return "deve essere un testo";
    case "bool_type":
    case "bool_parsing":
      return "deve essere vero o falso";
    case "enum":
    case "literal_error":
      return "valore non valido";
    case "value_error":
    case "assertion_error":
      // Pydantic custom validators leave the message in `msg`.
      return item.msg.replace(/^Value error,\s*/i, "").trim();
    default:
      return item.msg;
  }
}

/**
 * Parse a fetch Response that we expect (or feared) to be an error. Safe to
 * call on any non-ok response — non-JSON bodies degrade to a generic message.
 *
 * Always consumes the body, so don't call this on a Response you also want to
 * read elsewhere.
 */
export async function parseApiError(res: Response): Promise<ParsedApiError> {
  const status = res.status;
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    // Body wasn't JSON (HTML error page, plain text, etc.) — fall through.
  }

  const fieldErrors: Record<string, string> = {};
  let topMessage: string | null = null;

  if (
    body &&
    typeof body === "object" &&
    "detail" in body &&
    Array.isArray((body as { detail: unknown }).detail)
  ) {
    // Pydantic 422 shape — one entry per invalid field.
    const items = (body as { detail: PydanticErrorItem[] }).detail;
    const phrases: string[] = [];
    for (const item of items) {
      // `loc` always starts with "body" (or "query"/"path"); take the last
      // segment as the field name. Nested fields keep the last segment too —
      // that's a tradeoff for keeping the UI message short.
      const segments = item.loc.filter(
        (seg) => seg !== "body" && seg !== "query" && seg !== "path",
      );
      const fieldName =
        segments.length > 0 ? String(segments[segments.length - 1]) : "";
      const phrase = translatePydanticItem(item);
      if (fieldName) {
        fieldErrors[fieldName] = phrase;
        phrases.push(`${labelFor(fieldName)}: ${phrase}`);
      } else {
        phrases.push(phrase);
      }
    }
    if (phrases.length > 0) {
      topMessage = `Dati non validi. ${phrases.join(" · ")}`;
    }
  } else if (
    body &&
    typeof body === "object" &&
    "detail" in body &&
    typeof (body as { detail: unknown }).detail === "string"
  ) {
    // Most 4xx errors raised explicitly via HTTPException(detail="…").
    topMessage = (body as { detail: string }).detail;
  }

  if (!topMessage) {
    topMessage =
      status >= 500
        ? "Errore del server. Riprova tra qualche istante."
        : status === 401
        ? "Sessione scaduta. Effettua nuovamente il login."
        : status === 403
        ? "Non hai i permessi per eseguire questa operazione."
        : status === 404
        ? "Risorsa non trovata."
        : `Errore API ${status}.`;
  }

  return { message: topMessage, fieldErrors, status };
}

/**
 * Throw a friendly `Error` from a non-ok Response. Convenience wrapper for
 * call sites that already have the throw/catch pattern.
 */
export async function throwApiError(res: Response): Promise<never> {
  const err = await parseApiError(res);
  const e = new Error(err.message) as Error & { parsed: ParsedApiError };
  e.parsed = err;
  throw e;
}
