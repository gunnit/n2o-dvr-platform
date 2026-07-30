// Shared catalog of the 17 generatable document types. Lifted out of
// documents/page.tsx so the inline editor route (documents/[documentId])
// can resolve tipo_documento -> Italian display name without duplicating
// the mapping. Card-only concerns (icons, category chrome) live here too
// because they are intrinsically part of the same catalog rows.
//
// This module is the single source of truth for *what* a document type is;
// components/documents/document-card.tsx is the single source of truth for
// *how* one is drawn. The azienda Documenti tab used to carry its own
// private copies of the labels, the category map and the status styles —
// three maps that had already drifted out of step with these (3 categories
// vs 5, and no "ready"/"generating"/"error" status labels at all).
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Construction,
  Handshake,
  Loader2,
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
  /**
   * Long form, used where there is room to spell the acronym out (the
   * azienda Documenti tab). Falls back to `name` when omitted.
   */
  fullName?: string;
  pages: string;
  complexity: "Bassa" | "Media" | "Alta";
  category: DocCategory;
  icon: LucideIcon;
};

export const CATEGORY_META: Record<
  DocCategory,
  {
    label: string;
    accent: AccentKey;
    rail: string;
    /**
     * Abstract per-category texture, washed in behind the card header at
     * ~7% opacity. Deliberately not an illustration per document type:
     * DESIGN.md §0 rules decorative accents off-brand for a safety domain,
     * so this stays a near-invisible watermark that only differentiates
     * the five families at a glance.
     */
    texture: string;
  }
> = {
  dvr: {
    label: "Documento principale",
    accent: "navy",
    rail: "bg-[#003d74]",
    texture: "/documents/texture-dvr.webp",
  },
  allegati: {
    label: "Allegati DVR",
    accent: "sky",
    rail: "bg-[#0ea5e9]",
    texture: "/documents/texture-allegati.webp",
  },
  emergenza: {
    label: "Piani di emergenza",
    accent: "amber",
    rail: "bg-[#d97706]",
    texture: "/documents/texture-emergenza.webp",
  },
  haccp: {
    label: "HACCP — alimentare",
    accent: "emerald",
    rail: "bg-[#059669]",
    texture: "/documents/texture-haccp.webp",
  },
  // Slate rather than violet: the five category rails are a categorical
  // palette, and violet is spoken for (`Tone.ai` in lib/ui/tones).
  contratti: {
    label: "Appalti e cantieri",
    accent: "slate",
    rail: "bg-[#64748d]",
    texture: "/documents/texture-contratti.webp",
  },
};

export const documentTypes: DocType[] = [
  { key: "dvr_master", name: "DVR Master", fullName: "DVR Master — Valutazione dei Rischi", pages: "~187", complexity: "Alta", category: "dvr", icon: ShieldAlert },
  { key: "allegato_mmc", name: "Allegato MMC", fullName: "Allegato MMC (Movimentazione Carichi)", pages: "~30", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_vdt", name: "Allegato VDT", fullName: "Allegato VDT (Videoterminali)", pages: "~25", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_stress", name: "Allegato Stress", fullName: "Allegato Stress Lavoro-Correlato", pages: "~20", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_gestanti", name: "Allegato Gestanti", fullName: "Allegato Lavoratrici Gestanti", pages: "~10", complexity: "Bassa", category: "allegati", icon: Paperclip },
  { key: "allegato_incendio", name: "Allegato Incendio", fullName: "Allegato Rischio Incendio", pages: "~15", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_microclima", name: "Microclima Moderato", fullName: "Allegato Microclima Moderato", pages: "~15", complexity: "Alta", category: "allegati", icon: Paperclip },
  { key: "allegato_microclima_severo", name: "Microclima Caldo Severo", fullName: "Allegato Microclima Caldo Severo", pages: "~12", complexity: "Alta", category: "allegati", icon: Paperclip },
  { key: "allegato_biologico_alimentare", name: "Biologico Alimentare", fullName: "Allegato Biologico Alimentare", pages: "~25", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_biologico_asilo", name: "Biologico Asilo", fullName: "Allegato Biologico Asilo", pages: "~20", complexity: "Media", category: "allegati", icon: Paperclip },
  { key: "allegato_biologico_dentisti", name: "Biologico Dentisti", fullName: "Allegato Biologico Dentisti", pages: "~30", complexity: "Alta", category: "allegati", icon: Paperclip },
  { key: "pee_azienda", name: "PEE Aziendale", fullName: "Piano Emergenza Aziendale", pages: "~25", complexity: "Media", category: "emergenza", icon: Siren },
  { key: "pee_comune", name: "PEE Edificio/Comune", fullName: "Piano Emergenza Edificio/Comune", pages: "~40", complexity: "Media", category: "emergenza", icon: Siren },
  { key: "haccp", name: "HACCP Manuale", fullName: "Manuale HACCP", pages: "~90", complexity: "Media", category: "haccp", icon: Utensils },
  { key: "haccp_forms", name: "HACCP Schede (16)", fullName: "Schede Autocontrollo HACCP", pages: "~25", complexity: "Bassa", category: "haccp", icon: Utensils },
  { key: "duvri", name: "DUVRI", fullName: "DUVRI — Rischi da Interferenza", pages: "~45", complexity: "Media", category: "contratti", icon: Handshake },
  { key: "pos", name: "POS", fullName: "POS (Piano Operativo Sicurezza)", pages: "~110", complexity: "Alta", category: "contratti", icon: Construction },
];

export const CATEGORY_ORDER: DocCategory[] = ["dvr", "allegati", "emergenza", "haccp", "contratti"];

/** Catalog row for a tipo_documento key, if it is one we know about. */
export function documentTypeFor(key: string): DocType | undefined {
  return documentTypes.find((d) => d.key === key);
}

/** Italian display name for a tipo_documento key; falls back to the key. */
export function documentTypeLabel(key: string): string {
  return documentTypeFor(key)?.name ?? key;
}

/** Long-form Italian name, for surfaces with room to spell acronyms out. */
export function documentTypeFullLabel(key: string): string {
  const t = documentTypeFor(key);
  return t?.fullName ?? t?.name ?? key;
}

/**
 * Category for a tipo_documento key. Unknown keys land in `contratti`
 * rather than being dropped, so a type added backend-first still renders.
 */
export function docCategoryFor(key: string): DocCategory {
  return documentTypeFor(key)?.category ?? "contratti";
}

// ---------------------------------------------------------------------------
// Status vocabulary
// ---------------------------------------------------------------------------

/**
 * Semantic tone per status. Colour is spent on status and nothing else on a
 * document card — the old layout also colour-coded the static `complexity`
 * chip in the same red/amber/green language, so a high-complexity document
 * that had generated cleanly showed a red badge next to a green one.
 */
export type DocStatusTone = "neutral" | "busy" | "ok" | "warn" | "danger";

export const DOC_STATUS_TONE_CLASS: Record<DocStatusTone, string> = {
  neutral: "bg-[#f6f9fc] text-[#273951] border-[#e5edf5]",
  busy: "bg-[rgba(245,158,11,0.12)] text-[#9b6829] border-[rgba(245,158,11,0.3)]",
  ok: "bg-[rgba(21,190,83,0.14)] text-[#108c3d] border-[rgba(21,190,83,0.4)]",
  warn: "bg-[rgba(155,104,41,0.12)] text-[#9b6829] border-[rgba(155,104,41,0.3)]",
  danger: "bg-[rgba(186,26,26,0.1)] text-[#ba1a1a] border-[rgba(186,26,26,0.3)]",
};

export const DOC_STATUS: Record<
  string,
  { label: string; tone: DocStatusTone; icon: LucideIcon; spin?: boolean }
> = {
  pending: { label: "In attesa", tone: "neutral", icon: Clock },
  in_progress: { label: "In generazione", tone: "busy", icon: Loader2, spin: true },
  generating: { label: "In generazione", tone: "busy", icon: Loader2, spin: true },
  completed: { label: "Pronto", tone: "ok", icon: CheckCircle2 },
  ready: { label: "Pronto", tone: "ok", icon: CheckCircle2 },
  // US-2.8 AC3: a failed attempt is rolled back to "bozza" — partial file
  // discarded, record retained so the operator can retry without starting
  // from scratch. Amber rather than red because the record is still usable;
  // red is reserved for non-recoverable legacy "failed" rows that predate
  // the rollback logic.
  bozza: { label: "Bozza", tone: "warn", icon: AlertCircle },
  failed: { label: "Errore", tone: "danger", icon: AlertCircle },
  error: { label: "Errore", tone: "danger", icon: AlertCircle },
};

export const READY_STATUSES = new Set(["completed", "ready", "pronto"]);
export const BUSY_STATUSES = new Set(["pending", "in_progress", "generating"]);

export function isReadyStatus(status: string): boolean {
  return READY_STATUSES.has(status);
}

export function isBusyStatus(status: string): boolean {
  return BUSY_STATUSES.has(status);
}

/**
 * Newest version per tipo_documento, keyed by type. Both card surfaces show
 * one card per *type* headed by its latest version, so both need this.
 */
export function latestByType(
  documenti: DocumentoGenerato[],
): Map<string, DocumentoGenerato> {
  const out = new Map<string, DocumentoGenerato>();
  for (const doc of documenti) {
    const prev = out.get(doc.tipo_documento);
    if (!prev || doc.versione > prev.versione) out.set(doc.tipo_documento, doc);
  }
  return out;
}

// True when the row was minted by "Salva come nuova versione" in the
// in-app inline editor (options.edited_inline). Checks both the derived
// boolean (mirroring how edited_in_gdocs is surfaced) and the raw options
// JSON so the badge works regardless of which one the API emits.
export function isEditedInline(doc: DocumentoGenerato): boolean {
  return Boolean(doc.edited_inline ?? doc.options?.edited_inline);
}
