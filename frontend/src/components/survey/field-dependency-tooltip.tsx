"use client";

import { useEffect, useState } from "react";
import { Info } from "lucide-react";
import { useApi } from "@/hooks/use-api";

/**
 * Inline "Modifying this field will update X, Y, Z" hint (US-5.2 AC3).
 *
 * Wraps a survey form label / field with a small information icon. Hovering
 * the icon surfaces a native `title` tooltip listing the document types
 * that consume the field. Powered by the `/api/v1/lookup/field-dependencies`
 * catalog so any change to the catalog is reflected automatically without
 * touching component code.
 *
 * The catalog is fetched once per page load and cached in module state so
 * many `<FieldDependencyTooltip>` instances on the same form don't each
 * fire a request.
 */

let _catalogPromise: Promise<Record<string, string[]>> | null = null;

const DOC_LABELS: Record<string, string> = {
  dvr_master: "DVR Master",
  pee_azienda: "PEE Azienda",
  pee_comune: "PEE Comune",
  duvri: "DUVRI",
  pos: "POS",
  haccp: "HACCP",
  haccp_forms: "Schede HACCP",
  mmc: "MMC",
  vdt: "VDT",
  stress: "Stress lavoro-correlato",
  incendio: "Rischio Incendio",
  microclima: "Microclima",
  gestanti: "Gestanti",
  biologico: "Rischio Biologico",
};

interface FieldDependencyTooltipProps {
  /** ``entity.field`` path that matches the backend catalog. */
  field: string;
  /** Optional className passed to the wrapper span. */
  className?: string;
}

export function FieldDependencyTooltip({
  field,
  className,
}: FieldDependencyTooltipProps) {
  const { apiFetch } = useApi();
  const [docs, setDocs] = useState<string[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!_catalogPromise) {
      _catalogPromise = apiFetch<{
        dependencies: Record<string, string[]>;
      }>("/api/v1/lookup/field-dependencies").then((r) => r.dependencies);
    }
    _catalogPromise
      .then((catalog) => {
        if (cancelled) return;
        setDocs(catalog[field] ?? []);
      })
      .catch(() => {
        if (!cancelled) setDocs([]);
      });
    return () => {
      cancelled = true;
    };
  }, [field, apiFetch]);

  if (!docs || docs.length === 0) return null;

  const labels = docs.map((d) => DOC_LABELS[d] ?? d);
  // Native title tooltip — same dependency-free pattern AIBadge uses.
  const tooltip =
    "Modificando questo campo verranno aggiornati: " + labels.join(", ");

  return (
    <span
      className={
        "inline-flex items-center text-muted-foreground hover:text-foreground cursor-help " +
        (className ?? "")
      }
      title={tooltip}
      aria-label={tooltip}
    >
      <Info className="h-3 w-3" />
      <span className="sr-only">{tooltip}</span>
    </span>
  );
}
