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
  feedback: "Feedback",
  "ai-feedback": "AI Feedback",
  backups: "Backup",
  new: "Nuovo",
  edit: "Modifica",
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

// Fully-qualified paths that have their own index page. Intermediate paths
// not in this set are rendered as plain labels (no href) — without this
// guard, breadcrumbs link to namespace-only paths like /admin or
// /assessments/stress that 404 when clicked (feedback 2026-04-28 #4).
// Dynamic id segments (UUIDs, numerics) are always linkable separately.
const LINKABLE_PATHS = new Set<string>([
  "/dashboard",
  "/aziende",
  "/aziende/new",
  "/survey",
  "/documents",
  "/assessments",
  "/guida",
  "/settings",
  "/settings/backups",
  "/admin/users",
  "/admin/feedback",
  "/admin/ai-feedback",
]);

function isDynamicId(segment: string): boolean {
  return /^[0-9a-f]{8}-/.test(segment) || /^\d+$/.test(segment);
}

function labelFor(segment: string): string {
  if (SEGMENT_LABELS[segment]) return SEGMENT_LABELS[segment];
  // Looks like a UUID or id — render as "Dettaglio"
  if (isDynamicId(segment)) {
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
    // Linkable when the accumulated path has a real index page, OR the
    // segment is a dynamic id (whose [id] page is assumed to exist —
    // every dynamic route in this app has its own page).
    const linkable =
      !isLast && (LINKABLE_PATHS.has(acc) || isDynamicId(segments[i]));
    crumbs.push({
      label: labelFor(segments[i]),
      href: linkable ? acc : undefined,
    });
  }

  return <Header breadcrumbs={crumbs} actions={actions} />;
}
