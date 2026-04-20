"use client";

import { usePathname } from "next/navigation";
import { Header, type Breadcrumb } from "./header";

// Static path-segment labels. Routes with dynamic ids (e.g. /aziende/[id])
// just append the segment under the next-to-last label's href.
const SEGMENT_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  aziende: "Aziende",
  survey: "Sopralluoghi",
  documents: "Documenti",
  documenti: "Documenti",
  assessments: "Valutazioni",
  valutazioni: "Valutazioni",
  guida: "Guida",
  settings: "Impostazioni",
  admin: "Amministrazione",
  users: "Utenti",
  utenti: "Utenti",
  new: "Nuovo",
  pee: "PEE",
  pos: "POS",
  duvri: "DUVRI",
  haccp: "HACCP",
  stress: "Stress",
  gestanti: "Gestanti",
  biologico: "Biologico",
  mmc: "MMC",
  vdt: "VDT",
  incendio: "Incendio",
  microclima: "Microclima",
};

function labelFor(segment: string): string {
  if (SEGMENT_LABELS[segment]) return SEGMENT_LABELS[segment];
  // Looks like a UUID or id — render as "Dettaglio"
  if (/^[0-9a-f]{8}-/.test(segment) || /^\d+$/.test(segment)) {
    return "Dettaglio";
  }
  // Fallback: title-case single words
  return segment
    .split("-")
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(" ");
}

export function AutoBreadcrumbs({ actions }: { actions?: React.ReactNode }) {
  const pathname = usePathname() ?? "/";
  const segments = pathname.split("/").filter(Boolean);

  const crumbs: Breadcrumb[] = [];
  let acc = "";
  for (let i = 0; i < segments.length; i++) {
    acc += `/${segments[i]}`;
    const isLast = i === segments.length - 1;
    crumbs.push({
      label: labelFor(segments[i]),
      href: isLast ? undefined : acc,
    });
  }

  return <Header breadcrumbs={crumbs} actions={actions} />;
}
