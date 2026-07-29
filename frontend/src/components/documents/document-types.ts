// Shared catalog of the 17 generatable document types. Lifted out of
// documents/page.tsx so the inline editor route (documents/[documentId])
// can resolve tipo_documento -> Italian display name without duplicating
// the mapping. Card-only concerns (icons, category chrome) live here too
// because they are intrinsically part of the same catalog rows.
import {
  Construction,
  Handshake,
  Paperclip,
  ShieldAlert,
  Siren,
  Utensils,
  type LucideIcon,
} from "lucide-react";

import type { AccentKey } from "@/components/cards/Monogram";
import type { DocumentoGenerato } from "@/types";

export type DocCategory = "dvr" | "allegati" | "emergenza" | "haccp" | "contratti";

export type DocType = {
  key: string;
  name: string;
  pages: string;
  complexity: "Bassa" | "Media" | "Alta";
  category: DocCategory;
  icon: LucideIcon;
};

export const CATEGORY_META: Record<
  DocCategory,
  { label: string; accent: AccentKey; rail: string }
> = {
  dvr: { label: "Documento principale", accent: "navy", rail: "bg-[#003d74]" },
  allegati: { label: "Allegati DVR", accent: "sky", rail: "bg-[#0ea5e9]" },
  emergenza: { label: "Piani di emergenza", accent: "amber", rail: "bg-[#d97706]" },
  haccp: { label: "HACCP — alimentare", accent: "emerald", rail: "bg-[#059669]" },
  // Slate rather than violet: the five category rails are a categorical
  // palette, and violet is spoken for (`Tone.ai` in lib/ui/tones).
  contratti: { label: "Appalti e cantieri", accent: "slate", rail: "bg-[#64748d]" },
};

export const documentTypes: DocType[] = [
  { key: "dvr_master", name: "DVR Master", pages: "~187", complexity: "Alta", category: "dvr", icon: ShieldAlert },
  { key: "allegato_mmc", name: "Allegato MMC", pages: "~30", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_vdt", name: "Allegato VDT", pages: "~25", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_stress", name: "Allegato Stress", pages: "~20", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_gestanti", name: "Allegato Gestanti", pages: "~10", complexity: "Bassa", category: "allegati", icon: Paperclip },
  { key: "allegato_incendio", name: "Allegato Incendio", pages: "~15", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_microclima", name: "Microclima Moderato", pages: "~15", complexity: "Alta", category: "allegati", icon: Paperclip },
  { key: "allegato_microclima_severo", name: "Microclima Caldo Severo", pages: "~12", complexity: "Alta", category: "allegati", icon: Paperclip },
  { key: "allegato_biologico_alimentare", name: "Biologico Alimentare", pages: "~25", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_biologico_asilo", name: "Biologico Asilo", pages: "~20", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_biologico_dentisti", name: "Biologico Dentisti", pages: "~30", complexity: "Alta", category: "allegati", icon: Paperclip },
  { key: "pee_azienda", name: "PEE Aziendale", pages: "~25", complexity: "Media", category: "emergenza", icon: Siren },
  { key: "pee_comune", name: "PEE Edificio/Comune", pages: "~40", complexity: "Media", category: "emergenza", icon: Siren },
  { key: "haccp", name: "HACCP Manuale", pages: "~90", complexity: "Media", category: "haccp", icon: Utensils },
  { key: "haccp_forms", name: "HACCP Schede (16)", pages: "~25", complexity: "Bassa", category: "haccp", icon: Utensils },
  { key: "duvri", name: "DUVRI", pages: "~45", complexity: "Media", category: "contratti", icon: Handshake },
  { key: "pos", name: "POS", pages: "~110", complexity: "Alta", category: "contratti", icon: Construction },
];

export const CATEGORY_ORDER: DocCategory[] = ["dvr", "allegati", "emergenza", "haccp", "contratti"];

/** Italian display name for a tipo_documento key; falls back to the key. */
export function documentTypeLabel(key: string): string {
  return documentTypes.find((d) => d.key === key)?.name ?? key;
}

// True when the row was minted by "Salva come nuova versione" in the
// in-app inline editor (options.edited_inline). Checks both the derived
// boolean (mirroring how edited_in_gdocs is surfaced) and the raw options
// JSON so the badge works regardless of which one the API emits.
export function isEditedInline(doc: DocumentoGenerato): boolean {
  return Boolean(doc.edited_inline ?? doc.options?.edited_inline);
}
