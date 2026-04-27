import type { AccentKey } from "@/components/cards/Monogram";

export type SurveyStatusKey =
  | "draft"
  | "in_progress"
  | "completed"
  | "firmato"
  | "in_revisione";

export type StatusMeta = {
  label: string;
  badge: string;
  accent: AccentKey;
};

export const SURVEY_STATUS_META: Record<SurveyStatusKey, StatusMeta> = {
  draft: {
    label: "Bozza",
    badge: "bg-[#eef4ff] text-[#1b5594] border border-[#dbe6fe]",
    accent: "sky",
  },
  in_progress: {
    label: "In corso",
    badge:
      "bg-[rgba(0,61,116,0.08)] text-[#003d74] border border-[rgba(0,61,116,0.2)]",
    accent: "amber",
  },
  completed: {
    label: "Completato",
    badge:
      "bg-[rgba(21,190,83,0.18)] text-[#108c3d] border border-[rgba(21,190,83,0.4)]",
    accent: "emerald",
  },
  firmato: {
    label: "Firmato",
    badge:
      "bg-[rgba(21,190,83,0.18)] text-[#108c3d] border border-[rgba(21,190,83,0.4)]",
    accent: "navy",
  },
  in_revisione: {
    label: "In revisione",
    badge: "bg-[#f5f0ff] text-[#5b21b6] border border-[#e4d8ff]",
    accent: "violet",
  },
};

const FALLBACK: SurveyStatusKey = "draft";

export function surveyStatusKey(raw: string | undefined | null): SurveyStatusKey {
  if (raw && raw in SURVEY_STATUS_META) return raw as SurveyStatusKey;
  return FALLBACK;
}

export function surveyStatusMeta(raw: string | undefined | null): StatusMeta {
  return SURVEY_STATUS_META[surveyStatusKey(raw)];
}

// H9 — single source of truth for status filter buckets used by Aziende
// list, Sopralluoghi list, and Dashboard KPIs. "Completed" is the only
// fuzzy bucket: it covers both `completed` and `firmato` because both
// represent a delivered sopralluogo.
export type SurveyStatusBucket = "all" | "draft" | "in_progress" | "in_revisione" | "completed";

export function statusBucketFor(raw: string | undefined | null): Exclude<SurveyStatusBucket, "all"> {
  const key = surveyStatusKey(raw);
  if (key === "firmato") return "completed";
  return key;
}

export function matchesBucket(
  raw: string | undefined | null,
  bucket: SurveyStatusBucket,
): boolean {
  if (bucket === "all") return true;
  return statusBucketFor(raw) === bucket;
}
