"use client";

import {
  CheckCircle2,
  Circle,
  AlertTriangle,
  Lock,
  ArrowRight,
  ClipboardList,
  FileText,
  Sparkles,
  ShieldAlert,
  Target,
} from "lucide-react";
import type {
  Azienda,
  ValutazioneRischio,
  DocumentoGenerato,
} from "@/types";

type StepStatus = "done" | "todo" | "warning" | "blocked";

type Step = {
  id: string;
  status: StepStatus;
  title: string;
  detail: string;
  cta?: { label: string; onClick: () => void; primary?: boolean };
  icon: typeof ClipboardList;
};

const STATUS_META: Record<
  StepStatus,
  { iconBg: string; iconColor: string; ring: string; pill: string; label: string }
> = {
  done: {
    iconBg: "bg-[rgba(21,190,83,0.16)]",
    iconColor: "text-[#108c3d]",
    ring: "border-[rgba(21,190,83,0.3)]",
    pill: "bg-[rgba(21,190,83,0.18)] text-[#108c3d] border border-[rgba(21,190,83,0.4)]",
    label: "Completato",
  },
  todo: {
    iconBg: "bg-[#f6f9fc]",
    iconColor: "text-[#64748d]",
    ring: "border-[#e5edf5]",
    pill: "bg-[#eef4ff] text-[#1b5594] border border-[#dbe6fe]",
    label: "Da fare",
  },
  warning: {
    iconBg: "bg-[rgba(155,104,41,0.12)]",
    iconColor: "text-[#9b6829]",
    ring: "border-[rgba(155,104,41,0.3)]",
    pill: "bg-[rgba(155,104,41,0.12)] text-[#9b6829] border border-[rgba(155,104,41,0.3)]",
    label: "Attenzione",
  },
  blocked: {
    iconBg: "bg-[#f6f9fc]",
    iconColor: "text-[#94a3b8]",
    ring: "border-[#e5edf5]",
    pill: "bg-[#f6f9fc] text-[#64748d] border border-[#e5edf5]",
    label: "Bloccato",
  },
};

const DOWNLOADABLE = new Set(["completed", "ready", "pronto"]);
const SURVEY_DELIVERED = new Set(["completed", "firmato"]);

export type NextStepsCallbacks = {
  onResumeSurvey: () => void;
  onOpenDescrizione: () => void;
  onOpenRischi: () => void;
  // Always navigates to the standalone /assessments/risk/[id] editor.
  // Distinct from onOpenRischi which may switch the parent tab.
  onEditRischi: () => void;
  onOpenAssessments: () => void;
  onOpenMiglioramento: () => void;
  onOpenDocumenti: () => void;
  onGenerateDocs: () => void;
  generatingDocs: boolean;
};

export function NextStepsPanel({
  azienda,
  rischi,
  documenti,
  miglioramentoCount,
  callbacks,
}: {
  azienda: Azienda;
  rischi: ValutazioneRischio[];
  documenti: DocumentoGenerato[];
  // Count of rows in the misure_miglioramento table for the azienda.
  // Drives the Piano di Miglioramento step status — null means we haven't
  // loaded yet (the step renders as a neutral 'todo' until the parent fills
  // it in, so the panel doesn't lie about progress).
  miglioramentoCount: number | null;
  callbacks: NextStepsCallbacks;
}) {
  const steps = computeSteps(
    azienda,
    rischi,
    documenti,
    miglioramentoCount,
    callbacks,
  );
  const doneCount = steps.filter((s) => s.status === "done").length;
  const total = steps.length;
  const progress = Math.round((doneCount / total) * 100);

  return (
    <div className="relative overflow-hidden rounded-md border border-[#e5edf5] bg-white shadow-stripe-ambient">
      <span aria-hidden className="absolute inset-x-0 top-0 h-[2px] bg-[#003d74]" />
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e5edf5] px-6 py-4">
        <div className="flex items-center gap-2.5">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-[rgba(0,61,116,0.08)]">
            <Sparkles className="h-3.5 w-3.5 text-[#003d74]" strokeWidth={2} />
          </span>
          <h3 className="font-heading text-[15px] font-semibold tracking-[-0.005em] text-[#061b31]">
            Prossimi passi
          </h3>
        </div>
        <div className="flex items-center gap-2.5">
          <span className="tnum text-[12.5px] text-[#64748d]">
            {doneCount}/{total} completati
          </span>
          <div className="h-1.5 w-24 overflow-hidden rounded-full bg-[#f0f4f9]">
            <div
              className="h-full bg-[#003d74] transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>
      <ol className="divide-y divide-[#eef2f7]">
        {steps.map((step, idx) => (
          <StepRow key={step.id} step={step} index={idx + 1} />
        ))}
      </ol>
    </div>
  );
}

function StepRow({ step, index }: { step: Step; index: number }) {
  const meta = STATUS_META[step.status];
  const Icon =
    step.status === "done"
      ? CheckCircle2
      : step.status === "warning"
        ? AlertTriangle
        : step.status === "blocked"
          ? Lock
          : Circle;

  return (
    <li className="flex items-center gap-4 px-6 py-4">
      <span className="tnum w-5 shrink-0 text-[12px] font-medium text-[#94a3b8]">
        {index}
      </span>
      <span
        className={
          "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md " +
          meta.iconBg
        }
      >
        <Icon className={"h-4 w-4 " + meta.iconColor} strokeWidth={2} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={
              "text-[14px] font-medium " +
              (step.status === "done"
                ? "text-[#64748d] line-through decoration-[#cbd5e0]"
                : step.status === "blocked"
                  ? "text-[#94a3b8]"
                  : "text-[#061b31]")
            }
          >
            {step.title}
          </span>
          {step.status !== "todo" && (
            <span
              className={
                "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium " +
                meta.pill
              }
            >
              {meta.label}
            </span>
          )}
        </div>
        <p className="mt-0.5 text-[13px] leading-[1.45] text-[#64748d]">
          {step.detail}
        </p>
      </div>
      {step.cta && (
        <button
          type="button"
          onClick={step.cta.onClick}
          className={
            "inline-flex h-9 shrink-0 items-center gap-1.5 rounded-md px-3.5 text-[13px] font-medium transition-colors " +
            (step.cta.primary
              ? "bg-primary text-white shadow-stripe-ambient hover:bg-[#1b5594]"
              : "border border-[#e5edf5] bg-white text-[#273951] hover:bg-[#f6f9fc]")
          }
        >
          {step.cta.label}
          <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} />
        </button>
      )}
    </li>
  );
}

function computeSteps(
  azienda: Azienda,
  rischi: ValutazioneRischio[],
  documenti: DocumentoGenerato[],
  miglioramentoCount: number | null,
  cb: NextStepsCallbacks,
): Step[] {
  const surveyDelivered = SURVEY_DELIVERED.has(
    (azienda.survey_status ?? "").toLowerCase(),
  );

  const hasDescrizione = (azienda.descrizione_attivita ?? "").trim().length > 0;

  const applicableRisks = rischi.filter((r) => r.applicabile);
  const risksWithMeasures = applicableRisks.filter(
    (r) => (r.misure_prevenzione ?? "").trim().length > 0,
  );
  const missingMeasures = applicableRisks.length - risksWithMeasures.length;

  const docsCompleted = documenti.filter((d) => DOWNLOADABLE.has(d.status));
  const docsStale = documenti.filter((d) => d.stale_snapshot);
  // #17b — Misure di prevenzione / miglioramento are at the operator's
  // discretion ("LE MISURE SONO A DISCREZIONE DI CHI REDIGE IL DVR",
  // feedback 2026-05-18). We only hard-block generation on the sopralluogo
  // gate; missing measures stay surfaced as a warning step above but no
  // longer prevent the operator from generating the DVR.
  const docsBlocked = !surveyDelivered;

  const steps: Step[] = [];

  // 1. Sopralluogo
  steps.push({
    id: "sopralluogo",
    status: surveyDelivered ? "done" : "todo",
    title: "Sopralluogo",
    detail: surveyDelivered
      ? "Dati anagrafici, ambienti, persone e attrezzature consegnati."
      : "Compila ambienti, persone, attrezzature e rischi sul cantiere.",
    icon: ClipboardList,
    cta: surveyDelivered
      ? undefined
      : {
          label: "Riprendi sopralluogo",
          onClick: cb.onResumeSurvey,
          primary: true,
        },
  });

  // 2. Descrizione attivita'
  steps.push({
    id: "descrizione",
    status: hasDescrizione ? "done" : "todo",
    title: "Descrizione attivita'",
    detail: hasDescrizione
      ? "Compilata e pronta per il DVR."
      : "Genera con AI da visura camerale o scrivi manualmente.",
    icon: FileText,
    cta: hasDescrizione
      ? undefined
      : { label: "Apri", onClick: cb.onOpenDescrizione },
  });

  // 3a. Valuta rischi — surfaced once the sopralluogo is delivered but
  // no rischi have been entered yet. Replaces the previous mid-wizard
  // step with a CTA that points at the standalone /assessments/risk/[id]
  // editor (extraction 2026-04-30). When at least one applicable risk
  // exists we drop straight to the Misure di prevenzione step instead.
  if (surveyDelivered && applicableRisks.length === 0) {
    steps.push({
      id: "valuta-rischi",
      status: "todo",
      title: "Valuta rischi",
      detail:
        "Apri la pagina dedicata per assegnare P/D, applicabilità e pericoli specifici per ogni ambiente.",
      icon: ShieldAlert,
      cta: {
        label: "Apri valutazione",
        onClick: cb.onOpenRischi,
        primary: true,
      },
    });
  }

  // 3b. Misure di prevenzione (skip if no risks yet — sopralluogo not done).
  // CTA goes to the standalone editor where the AI suggester actually lives;
  // tab-switching here was a no-op when the user was already on the rischi tab.
  if (applicableRisks.length > 0) {
    const allCovered = missingMeasures === 0;
    steps.push({
      id: "misure",
      status: allCovered ? "done" : "warning",
      title: "Misure di prevenzione",
      detail: allCovered
        ? `${applicableRisks.length} rischi su ${applicableRisks.length} con misure definite.`
        : `${missingMeasures} ${missingMeasures === 1 ? "rischio" : "rischi"} senza misure (su ${applicableRisks.length}). Apri l'editor per definirle o generarle con AI.`,
      icon: ShieldAlert,
      cta: {
        label: allCovered ? "Rivedi rischi" : "Apri editor rischi",
        onClick: cb.onEditRischi,
        primary: !allCovered,
      },
    });
  }

  // 3c. Piano di Miglioramento — surfaces once the operator has at least
  // one applicable risk so they have something to generate measures from.
  // Status reflects whether any misure_miglioramento rows exist; the page
  // itself has the "Genera con AI" CTA, so we just point the operator at
  // it. Skipped until the parent loads miglioramentoCount (null) to avoid
  // misreporting a "todo" before we know.
  if (applicableRisks.length > 0 && miglioramentoCount !== null) {
    const hasMisure = miglioramentoCount > 0;
    steps.push({
      id: "miglioramento",
      status: hasMisure ? "done" : "todo",
      title: "Piano di Miglioramento",
      detail: hasMisure
        ? `${miglioramentoCount} ${miglioramentoCount === 1 ? "misura" : "misure"} nel Programma di Miglioramento (DVR §4.1).`
        : "Genera con AI o aggiungi manualmente le misure di prevenzione per ogni pericolo valutato.",
      icon: Target,
      cta: {
        label: hasMisure ? "Apri piano" : "Apri e genera",
        onClick: cb.onOpenMiglioramento,
        primary: !hasMisure,
      },
    });
  }

  // 4. Valutazioni specialistiche — informational. We can't compute
  // applicability client-side without backend hints, so we just point
  // the user at the dedicated page when the sopralluogo is closed.
  if (surveyDelivered) {
    steps.push({
      id: "valutazioni",
      status: "todo",
      title: "Valutazioni specialistiche",
      detail:
        "Verifica MMC, VDT, Stress, Incendio, Microclima, Biologico, Gestanti — solo se applicabili.",
      icon: ClipboardList,
      cta: { label: "Apri valutazioni", onClick: cb.onOpenAssessments },
    });
  }

  // 5. Genera documenti
  let docStatus: StepStatus;
  let docDetail: string;
  let docCta: Step["cta"];

  if (docsBlocked) {
    docStatus = "blocked";
    docDetail = "Disponibile dopo la firma del sopralluogo.";
    docCta = undefined;
  } else if (docsCompleted.length === 0) {
    docStatus = "todo";
    docDetail = "Pronto per generare DVR Master e fino a 16 allegati.";
    docCta = {
      label: cb.generatingDocs ? "Avvio in corso..." : "Genera documenti",
      onClick: cb.onGenerateDocs,
      primary: true,
    };
  } else if (docsStale.length > 0) {
    docStatus = "warning";
    docDetail = `${docsStale.length} ${docsStale.length === 1 ? "documento" : "documenti"} da rigenerare: il sopralluogo e' stato modificato dopo l'ultima generazione.`;
    docCta = { label: "Apri documenti", onClick: cb.onOpenDocumenti };
  } else {
    docStatus = "done";
    docDetail = `${docsCompleted.length} ${docsCompleted.length === 1 ? "documento pronto" : "documenti pronti"} al download.`;
    docCta = { label: "Apri documenti", onClick: cb.onOpenDocumenti };
  }

  steps.push({
    id: "documenti",
    status: docStatus,
    title: "Documenti",
    detail: docDetail,
    icon: FileText,
    cta: docCta,
  });

  return steps;
}
