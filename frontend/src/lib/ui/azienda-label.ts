import type { Azienda } from "@/types";

/**
 * The label an azienda gets inside a `<Select>` option.
 *
 * One format, because the two hub pages disagreed: /documents rendered
 * "RAGIONE — via, città" while /assessments rendered "RAGIONE · città", so the
 * same company read differently depending on which screen you picked it from.
 *
 * The street is part of it deliberately (#73): consultancies routinely hold two
 * clients with the same ragione sociale, and the sede is the only thing that
 * tells them apart. Sede operativa wins over sede legale — that is the address
 * the sopralluogo actually happened at.
 */
export function aziendaOptionLabel(a: Azienda): string {
  const sede =
    [a.sede_operativa_via, a.sede_operativa_citta].filter(Boolean).join(", ") ||
    [a.sede_legale_via, a.sede_legale_citta].filter(Boolean).join(", ");
  return sede ? `${a.ragione_sociale} — ${sede}` : a.ragione_sociale;
}
