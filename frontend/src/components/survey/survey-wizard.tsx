"use client";

import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Building2,
  Users,
  MapPin,
  Wrench,
  ShieldAlert,
  FlaskConical,
  ClipboardCheck,
  Stethoscope,
  ChevronLeft,
  ChevronRight,
  Check,
  Circle,
  CloudUpload,
  Lock,
} from "lucide-react";
import type {
  Azienda,
  Persona,
  Ambiente,
  Attrezzatura,
  MansioneSorveglianza,
  ValutazioneRischio,
  SostanzaChimica,
} from "@/types";

import { StepAzienda } from "./steps/step-azienda";
import { StepPersone } from "./steps/step-persone";
import { StepAmbienti } from "./steps/step-ambienti";
import { StepAttrezzature } from "./steps/step-attrezzature";
import { StepDpiRischi } from "./steps/step-dpi-rischi";
import { StepRischi, ambientiSignature } from "./steps/step-rischi";
import { StepSostanze } from "./steps/step-sostanze";
import { StepRiepilogo } from "./steps/step-riepilogo";
import { SectorSuggestions } from "./sector-suggestions";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// `required` drives both progress % and the Avanti gate. Optional steps
// (attrezzature, dpi_rischi, sostanze) don't block the wizard but still
// surface a green check once the operator has visited them.
const STEPS = [
  { key: "azienda", label: "Dati Azienda", icon: Building2, required: true },
  { key: "ambienti", label: "Ambienti", icon: MapPin, required: true },
  { key: "persone", label: "Persone", icon: Users, required: true },
  { key: "attrezzature", label: "Attrezzature", icon: Wrench, required: false },
  {
    key: "dpi_rischi",
    label: "DPI & Rischi Specifici",
    icon: Stethoscope,
    required: false,
  },
  {
    key: "rischi",
    label: "Valutazione Rischi",
    icon: ShieldAlert,
    required: true,
  },
  {
    key: "sostanze",
    label: "Sostanze Chimiche",
    icon: FlaskConical,
    required: false,
  },
  {
    key: "riepilogo",
    label: "Riepilogo",
    icon: ClipboardCheck,
    required: true,
  },
] as const;

export interface SurveyData {
  azienda: Partial<Azienda>;
  persone: Persona[];
  ambienti: Ambiente[];
  attrezzature: Attrezzatura[];
  mansioniSorveglianza: MansioneSorveglianza[];
  valutazioni: ValutazioneRischio[];
  sostanze: SostanzaChimica[];
}

interface SurveyWizardProps {
  aziendaId: string;
  initialData?: Partial<SurveyData>;
}

const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 300 : -300,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction: number) => ({
    x: direction > 0 ? -300 : 300,
    opacity: 0,
  }),
};

export function SurveyWizard({ aziendaId, initialData }: SurveyWizardProps) {
  const initialSurveyStatus = initialData?.azienda?.survey_status ?? "draft";
  const initialSignedAt = initialData?.azienda?.firma_signed_at ?? null;

  // US-1.6: if the survey arrives already "firmato" the wizard locks nav
  // to the last (riepilogo) step until the operator opens an audited
  // revision. Anything else (draft, step_1..n, in_revisione, completed)
  // allows free navigation. Index stays in sync with STEPS.length-1 so
  // inserting a new step doesn't break the lock.
  const [surveyStatus, setSurveyStatus] =
    useState<string>(initialSurveyStatus);
  const [signedAt, setSignedAt] = useState<string | null>(initialSignedAt);

  const isSigned = surveyStatus === "firmato";
  const riepilogoIndex = STEPS.length - 1;

  const [currentStep, setCurrentStep] = useState(
    isSigned ? riepilogoIndex : 0
  );
  const [direction, setDirection] = useState(0);
  const [saving, setSaving] = useState(false);
  // B-01 (US-1.1): when the operator clicks "Avanti" on a step with
  // validation errors we flip this flag so the failing step forces its
  // inline errors to render (the fields' own onBlur paths don't fire on a
  // never-touched empty field). Cleared whenever the operator moves off
  // the step so they don't stay highlighted between visits.
  const [showValidationErrors, setShowValidationErrors] = useState(false);

  // H1: track which steps the operator has actually opened. Combined with
  // content-based completion this lets us:
  //  - mark optional steps "complete" only after a deliberate visit
  //  - allow stepper-circle navigation only to already-seen steps
  // Step 0 is always considered visited (it's the wizard's landing step).
  const [visited, setVisited] = useState<Set<number>>(() => new Set([0]));

  const [data, setData] = useState<SurveyData>({
    azienda: initialData?.azienda ?? {},
    persone: initialData?.persone ?? [],
    ambienti: initialData?.ambienti ?? [],
    attrezzature: initialData?.attrezzature ?? [],
    mansioniSorveglianza: initialData?.mansioniSorveglianza ?? [],
    valutazioni: initialData?.valutazioni ?? [],
    sostanze: initialData?.sostanze ?? [],
  });

  // US-1.5 AC3: ambienti signature the operator has last acknowledged
  // on Step 5. Lives at wizard scope so it survives Step 5 unmount/
  // remount under <AnimatePresence mode="wait">. Lazy initializer seeds
  // it from the initial ambienti list, so a fresh page load does NOT
  // surface the banner — only an in-session edit on Step 2 does.
  const [acknowledgedAmbientiSig, setAcknowledgedAmbientiSig] =
    useState<string>(() => ambientiSignature(initialData?.ambienti ?? []));

  const acknowledgeAmbienti = useCallback((sig: string) => {
    setAcknowledgedAmbientiSig(sig);
  }, []);

  // Keep the wizard pinned on the Riepilogo step whenever the survey is
  // signed — step-navigation handlers short-circuit below, but if the
  // user arrives deep-linked to an earlier step we still want to bounce
  // them to the last step.
  useEffect(() => {
    if (isSigned && currentStep !== riepilogoIndex) {
      setCurrentStep(riepilogoIndex);
    }
  }, [isSigned, currentStep, riepilogoIndex]);

  const updateAzienda = useCallback(
    (fields: Partial<Azienda>) => {
      setData((prev) => ({ ...prev, azienda: { ...prev.azienda, ...fields } }));
    },
    []
  );

  // H6: autosave step-1 azienda edits to /api/v1/aziende/{id} so the
  // canonical record (and dashboard / company detail screens) stays in
  // sync with the wizard. Debounced 800ms; only fires when at least one
  // editable field has changed from the initial snapshot. Backend uses
  // `exclude_unset` so sending the partial payload is safe.
  const initialAziendaRef = useRef<Partial<Azienda>>(initialData?.azienda ?? {});
  // Only the fields the operator can edit on Step 1 — we deliberately
  // skip server-managed columns (id, organization_id, survey_status,
  // firma_*, timestamps, AI-generated descrizione_attivita) so autosave
  // never accidentally clobbers them.
  const AUTOSAVE_FIELDS: (keyof Azienda)[] = [
    "ragione_sociale",
    "partita_iva",
    "codice_ateco",
    "attivita",
    "sede_legale_via",
    "sede_legale_citta",
    "sede_operativa_via",
    "sede_operativa_citta",
    "orario_lavoro",
    "metratura_totale",
    "zona_sismica",
  ];
  useEffect(() => {
    if (isSigned) return;
    const a = data.azienda;
    const base = initialAziendaRef.current;
    const diff: Partial<Azienda> = {};
    let dirty = false;
    for (const key of AUTOSAVE_FIELDS) {
      const next = a[key];
      const prev = base[key];
      if (next !== prev) {
        // @ts-expect-error indexed assignment across the union types is
        // safe because we restrict `key` to AUTOSAVE_FIELDS above.
        diff[key] = next;
        dirty = true;
      }
    }
    if (!dirty) return;
    // Skip pushes when ragione_sociale is still empty — the record
    // requires it server-side and we'd just get a 422.
    if (!a.ragione_sociale?.trim()) return;
    const handle = setTimeout(async () => {
      setSaving(true);
      try {
        const sessionRes = await fetch("/api/auth/session");
        const session = await sessionRes.json();
        const token = session?.accessToken;
        const res = await fetch(`${API_URL}/api/v1/aziende/${aziendaId}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(diff),
        });
        if (res.ok) {
          // Reset the baseline so subsequent edits compute a fresh diff
          // instead of re-sending the same fields on every keystroke.
          initialAziendaRef.current = { ...initialAziendaRef.current, ...diff };
        }
      } catch {
        // Silent — autosave is best-effort. The "Completa Sopralluogo"
        // POST will surface any persistence errors loudly.
      } finally {
        setSaving(false);
      }
    }, 800);
    return () => clearTimeout(handle);
    // AUTOSAVE_FIELDS is a stable literal; only the live azienda payload
    // and aziendaId can actually change here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.azienda, aziendaId, isSigned]);

  const updatePersone = useCallback((persone: Persona[]) => {
    setData((prev) => ({ ...prev, persone }));
  }, []);

  const updateAmbienti = useCallback((ambienti: Ambiente[]) => {
    setData((prev) => ({ ...prev, ambienti }));
  }, []);

  const updateAttrezzature = useCallback((attrezzature: Attrezzatura[]) => {
    setData((prev) => ({ ...prev, attrezzature }));
  }, []);

  const updateValutazioni = useCallback((valutazioni: ValutazioneRischio[]) => {
    setData((prev) => ({ ...prev, valutazioni }));
  }, []);

  const updateMansioniSorveglianza = useCallback(
    (mansioniSorveglianza: MansioneSorveglianza[]) => {
      setData((prev) => ({ ...prev, mansioniSorveglianza }));
    },
    []
  );

  const updateSostanze = useCallback((sostanze: SostanzaChimica[]) => {
    setData((prev) => ({ ...prev, sostanze }));
  }, []);

  // Per-step validation (H1/H2/H7). Returns the list of operator-facing
  // error messages for the step; empty list means the step is ready to
  // advance. Required-step content rules:
  //  - 0 azienda: ragione sociale + valid P.IVA (11 digits) + valid ATECO
  //    (NN.NN or NN.NN.NN)
  //  - 1 ambienti: at least one record
  //  - 2 persone: at least one record AND at least one with ruolo_rspp
  //  - 5 valutazioni rischio: at least one applicable risk assessment
  //  - 7 riepilogo: all upstream required steps complete + signature
  // Optional steps (3, 4, 6) always pass.
  const validationForStep = useCallback(
    (step: number): { field?: string; message: string }[] => {
      const errors: { field?: string; message: string }[] = [];
      if (step === 0) {
        const a = data.azienda;
        if (!a.ragione_sociale || !a.ragione_sociale.trim()) {
          errors.push({
            field: "ragione_sociale",
            message: "Ragione sociale: campo obbligatorio",
          });
        }
        // P.IVA is required for the step to be "complete" (H1 spec). Match
        // the 11-digit regex when present; treat empty as missing.
        if (!a.partita_iva || !a.partita_iva.trim()) {
          errors.push({
            field: "partita_iva",
            message: "Partita IVA: campo obbligatorio (11 cifre)",
          });
        } else if (!/^\d{11}$/.test(a.partita_iva.trim())) {
          errors.push({
            field: "partita_iva",
            message: "Partita IVA: deve essere di 11 cifre",
          });
        }
        if (!a.codice_ateco || !a.codice_ateco.trim()) {
          errors.push({
            field: "codice_ateco",
            message: "Codice ATECO: campo obbligatorio (formato NN.NN o NN.NN.NN)",
          });
        } else if (!/^\d{2}\.\d{2}(\.\d{2})?$/.test(a.codice_ateco.trim())) {
          errors.push({
            field: "codice_ateco",
            message: "Codice ATECO: formato richiesto NN.NN o NN.NN.NN",
          });
        }
      } else if (step === 1) {
        if (data.ambienti.length === 0) {
          errors.push({
            message: "Aggiungi almeno un ambiente per continuare",
          });
        }
      } else if (step === 2) {
        if (data.persone.length === 0) {
          errors.push({
            message: "Aggiungi almeno una persona per continuare",
          });
        } else if (!data.persone.some((p) => p.ruolo_rspp)) {
          errors.push({
            message: "Designa almeno un RSPP tra le persone inserite",
          });
        }
      } else if (step === 5) {
        const applicable = data.valutazioni.filter((v) => v.applicabile);
        if (applicable.length === 0) {
          errors.push({
            message:
              "Compila almeno una valutazione del rischio applicabile per continuare",
          });
        }
      } else if (step === 7) {
        // Riepilogo is "complete" only when every upstream required step
        // is content-complete and the survey is signed. We don't recurse
        // through validationForStep here because that would cause a
        // dependency cycle; instead we re-check the invariants directly.
        const a = data.azienda;
        if (
          !a.ragione_sociale?.trim() ||
          !a.partita_iva ||
          !/^\d{11}$/.test(a.partita_iva.trim()) ||
          !a.codice_ateco ||
          !/^\d{2}\.\d{2}(\.\d{2})?$/.test(a.codice_ateco.trim())
        ) {
          errors.push({
            message: "Completa i dati azienda prima di firmare",
          });
        }
        if (data.ambienti.length === 0) {
          errors.push({
            message: "Aggiungi almeno un ambiente prima di firmare",
          });
        }
        if (data.persone.length === 0 || !data.persone.some((p) => p.ruolo_rspp)) {
          errors.push({
            message:
              "Designa almeno un RSPP tra le persone prima di firmare",
          });
        }
        if (data.valutazioni.filter((v) => v.applicabile).length === 0) {
          errors.push({
            message:
              "Compila almeno una valutazione del rischio prima di firmare",
          });
        }
        if (!isSigned) {
          errors.push({ message: "Firma del cliente mancante" });
        }
      }
      return errors;
    },
    [data, isSigned],
  );

  // H1: a step is "complete" when (required ⇒ content-validated) or
  // (optional ⇒ visited). Used by both stepper circles and sidebar list.
  const isStepComplete = useCallback(
    (step: number): boolean => {
      const meta = STEPS[step];
      if (!meta) return false;
      if (meta.required) {
        return validationForStep(step).length === 0;
      }
      return visited.has(step);
    },
    [validationForStep, visited],
  );

  // Progress % counts only required steps so optional ones (which a fast
  // operator may legitimately skip) don't dilute the indicator.
  const progressPct = useMemo(() => {
    const required = STEPS.map((s, i) => ({ s, i })).filter(
      ({ s }) => s.required,
    );
    if (required.length === 0) return 0;
    const done = required.filter(({ i }) => isStepComplete(i)).length;
    return Math.round((done / required.length) * 100);
  }, [isStepComplete]);

  const currentStepErrors = useMemo(
    () => validationForStep(currentStep),
    [validationForStep, currentStep],
  );

  const goToStep = useCallback(
    (step: number) => {
      // US-1.6 AC4: when the survey is firmato, the only reachable step
      // is Riepilogo. Any navigation attempt bounces there.
      if (isSigned && step !== riepilogoIndex) return;
      setDirection(step > currentStep ? 1 : -1);
      setCurrentStep(step);
      setShowValidationErrors(false);
      setVisited((prev) => {
        if (prev.has(step)) return prev;
        const next = new Set(prev);
        next.add(step);
        return next;
      });
    },
    [currentStep, isSigned, riepilogoIndex]
  );

  // H7: when validation fails on Avanti, find the first invalid field DOM
  // node (matching the validator's `field` key against an element id) and
  // smooth-scroll it into view. We defer to a microtask so React has time
  // to flip showValidationErrors and re-render the inline error markup
  // before we read getBoundingClientRect.
  const scrollFirstInvalidIntoView = useCallback(
    (errors: { field?: string; message: string }[]) => {
      if (typeof window === "undefined") return;
      const firstWithField = errors.find((e) => e.field);
      const targetId = firstWithField?.field;
      requestAnimationFrame(() => {
        const node = targetId ? document.getElementById(targetId) : null;
        const firstInvalid: HTMLElement | null =
          node ?? document.querySelector<HTMLElement>(".border-destructive");
        firstInvalid?.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    },
    [],
  );

  const goNext = useCallback(() => {
    if (isSigned) return;
    const meta = STEPS[currentStep];
    const errors = validationForStep(currentStep);
    // H2/H7: required steps must pass content validation before we let
    // the operator advance. Optional steps fall through to the navigation
    // path even when validationForStep returns issues (today none of the
    // optional steps emit any, but we keep the gate explicit).
    if (meta?.required && errors.length > 0) {
      setShowValidationErrors(true);
      toast.error(errors[0].message, {
        description:
          errors.length > 1
            ? `Altri ${errors.length - 1} campo/i da correggere prima di avanzare`
            : "Compila i campi obbligatori prima di proseguire",
      });
      scrollFirstInvalidIntoView(errors);
      return;
    }
    if (currentStep < STEPS.length - 1) {
      setDirection(1);
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      setShowValidationErrors(false);
      setVisited((prev) => {
        if (prev.has(nextStep)) return prev;
        const next = new Set(prev);
        next.add(nextStep);
        return next;
      });
    }
  }, [currentStep, isSigned, validationForStep, scrollFirstInvalidIntoView]);

  const goPrev = useCallback(() => {
    if (isSigned) return;
    if (currentStep > 0) {
      setDirection(-1);
      setCurrentStep((prev) => prev - 1);
    }
  }, [currentStep, isSigned]);

  // B-03 (US-1.6): "Completa Sopralluogo" must surface *why* it's blocked
  // instead of being a silent no-op. We check structural completeness
  // (ragione sociale + at-least-one ambiente/persona + at-least-one RSPP)
  // and the signed flag before hitting /survey/complete.
  const completionIssues = useMemo<string[]>(() => {
    const out: string[] = [];
    if (!data.azienda.ragione_sociale?.trim()) {
      out.push("Ragione sociale mancante");
    }
    if (data.persone.length === 0) {
      out.push("Nessuna persona inserita");
    }
    if (data.ambienti.length === 0) {
      out.push("Nessun ambiente inserito");
    }
    if (!data.persone.some((p) => p.ruolo_rspp)) {
      out.push("Manca un RSPP tra le persone");
    }
    if (!isSigned) {
      out.push("Firma del cliente mancante");
    }
    return out;
  }, [data, isSigned]);

  const handleComplete = useCallback(async () => {
    if (completionIssues.length > 0) {
      toast.error(completionIssues[0], {
        description:
          completionIssues.length > 1
            ? `Altri ${completionIssues.length - 1} prerequisito/i aperto/i`
            : undefined,
      });
      return;
    }
    setSaving(true);
    try {
      const sessionRes = await fetch("/api/auth/session");
      const session = await sessionRes.json();
      const token = session?.accessToken;

      const res = await fetch(
        `${API_URL}/api/v1/aziende/${aziendaId}/survey/complete`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(data),
        },
      );
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(
          detail?.detail ?? `Errore completamento (${res.status})`,
        );
      }
      toast.success("Sopralluogo completato");
    } catch (err) {
      console.error("Error completing survey:", err);
      toast.error(
        err instanceof Error
          ? `Errore: ${err.message}`
          : "Errore durante il completamento",
      );
    } finally {
      setSaving(false);
    }
  }, [aziendaId, data, completionIssues]);

  // US-1.6: POST signed PNG → backend stamps server-side timestamp and
  // flips survey_status to "firmato". Returns the new lifecycle state so
  // the wizard can gate nav without a round-trip refetch.
  const handleSign = useCallback(
    async (signature: { dataUrl: string; signedByName?: string | null }) => {
      const sessionRes = await fetch("/api/auth/session");
      const session = await sessionRes.json();
      const token = session?.accessToken;

      const res = await fetch(
        `${API_URL}/api/v1/aziende/${aziendaId}/survey/sign`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            signature_data_url: signature.dataUrl,
            signed_by_name: signature.signedByName ?? null,
          }),
        }
      );

      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? `Errore firma (${res.status})`);
      }

      const payload = (await res.json()) as {
        survey_status: string;
        firma_signed_at: string;
        firma_signed_by_name: string | null;
      };

      setSurveyStatus(payload.survey_status);
      setSignedAt(payload.firma_signed_at);
      return payload;
    },
    [aziendaId]
  );

  // US-1.6 AC4: "Apri revisione" — flips status to in_revisione so the
  // wizard re-enables nav. The signature PNG stays on disk so we can show
  // a "previously signed at …" badge while in revision mode.
  const handleOpenRevision = useCallback(async () => {
    const sessionRes = await fetch("/api/auth/session");
    const session = await sessionRes.json();
    const token = session?.accessToken;

    const res = await fetch(
      `${API_URL}/api/v1/aziende/${aziendaId}/survey/revision`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      }
    );

    if (!res.ok) {
      const detail = await res.json().catch(() => null);
      throw new Error(detail?.detail ?? `Errore apertura revisione (${res.status})`);
    }

    const payload = (await res.json()) as { survey_status: string };
    setSurveyStatus(payload.survey_status);
  }, [aziendaId]);

  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return (
          <StepAzienda
            aziendaId={aziendaId}
            data={data.azienda}
            onChange={updateAzienda}
            showAllErrors={showValidationErrors}
          />
        );
      case 1:
        return (
          <StepAmbienti
            aziendaId={aziendaId}
            ambienti={data.ambienti}
            onChange={updateAmbienti}
          />
        );
      case 2:
        return (
          <StepPersone
            aziendaId={aziendaId}
            persone={data.persone}
            ambienti={data.ambienti}
            onChange={updatePersone}
          />
        );
      case 3:
        return (
          <StepAttrezzature
            aziendaId={aziendaId}
            ambienti={data.ambienti}
            attrezzature={data.attrezzature}
            onChange={updateAttrezzature}
          />
        );
      case 4:
        return (
          <StepDpiRischi
            aziendaId={aziendaId}
            persone={data.persone}
            mansioniSorveglianza={data.mansioniSorveglianza}
            onChange={updateMansioniSorveglianza}
          />
        );
      case 5:
        return (
          <StepRischi
            aziendaId={aziendaId}
            ambienti={data.ambienti}
            attrezzature={data.attrezzature}
            valutazioni={data.valutazioni}
            onChange={updateValutazioni}
            acknowledgedAmbientiSig={acknowledgedAmbientiSig}
            onAcknowledgeAmbienti={acknowledgeAmbienti}
          />
        );
      case 6:
        return (
          <StepSostanze
            aziendaId={aziendaId}
            sostanze={data.sostanze}
            onChange={updateSostanze}
          />
        );
      case 7:
        return (
          <StepRiepilogo
            aziendaId={aziendaId}
            data={data}
            onGoToStep={goToStep}
            isSigned={isSigned}
            signedAt={signedAt}
            signedByName={data.azienda.firma_signed_by_name ?? null}
            onSign={handleSign}
            onOpenRevision={handleOpenRevision}
          />
        );
      default:
        return null;
    }
  };

  // Wave 2: Digital Guardian stepper + glass-cards. progressPct is now
  // computed above (content-based across required steps only).
  const circumference = 2 * Math.PI * 58;
  const progressDashOffset = circumference - (progressPct / 100) * circumference;

  // H2/H7 — Avanti disabled when the current step is required and not
  // yet content-complete. The tooltip surfaces the precise reason so the
  // operator never sees a silently dead button.
  const currentStepMeta = STEPS[currentStep];
  const nextDisabled =
    isSigned ||
    (currentStepMeta?.required ?? false) && currentStepErrors.length > 0;
  const nextDisabledReason =
    !isSigned && currentStepErrors.length > 0
      ? currentStepErrors[0].message
      : "Compila i campi obbligatori prima di proseguire";

  return (
    <div className="space-y-10 pb-24">
      {/* US-1.6: lock banner when survey is firmato — nav is frozen until
         the operator opens an audited revision via Step 7. */}
      {isSigned && (
        <div className="flex items-center gap-2 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-800">
          <Lock className="h-4 w-4" />
          <span>
            Sopralluogo firmato — navigazione bloccata. Clicca
            &ldquo;Apri revisione&rdquo; nel riepilogo per modificare.
          </span>
        </div>
      )}

      {/* Stepper */}
      <div className="mx-auto max-w-6xl">
        <div className="relative flex items-start justify-between">
          <div className="absolute left-5 right-5 top-5 -z-10 h-0.5 bg-slate-200" />
          <div
            className="absolute left-5 top-5 -z-10 h-0.5 bg-primary-container transition-all duration-500 ease-out"
            style={{
              width: `calc((100% - 2.5rem) * ${currentStep / (STEPS.length - 1)})`,
            }}
          />
          {STEPS.map((step, index) => {
            const isActive = index === currentStep;
            const isCompleted = isStepComplete(index);
            const isVisited = visited.has(index);
            // M4: top-circle nav is allowed only for already-visited steps
            // (so the operator can jump back), never to future steps. We
            // also keep the existing "firmato" lock that pins everything
            // outside Riepilogo.
            const navDisabled =
              (isSigned && index !== riepilogoIndex) ||
              (!isVisited && !isActive);

            return (
              <button
                key={step.key}
                type="button"
                onClick={() => goToStep(index)}
                disabled={navDisabled}
                title={
                  navDisabled && !isSigned
                    ? "Step non ancora visitato"
                    : step.label
                }
                className={cn(
                  "group flex flex-col items-center gap-2",
                  !navDisabled &&
                    "cursor-pointer hover:opacity-90",
                  navDisabled && "cursor-not-allowed opacity-60"
                )}
              >
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-full shadow-lg transition-all duration-200",
                    isActive &&
                      "bg-primary-container text-white ring-4 ring-primary-container/20",
                    !isActive && isCompleted && "bg-green-500 text-white",
                    !isActive && !isCompleted && "bg-slate-200 text-slate-500",
                    !navDisabled &&
                      !isActive &&
                      "group-hover:ring-2 group-hover:ring-primary-container/30"
                  )}
                >
                  {!isActive && isCompleted ? (
                    <Check className="h-5 w-5" strokeWidth={2.5} />
                  ) : (
                    <span className="font-bold">{index + 1}</span>
                  )}
                </div>
                <span
                  className={cn(
                    "hidden text-[11px] font-bold tracking-tight md:block",
                    isActive && "text-primary-container",
                    !isActive && isCompleted && "text-slate-600",
                    !isActive && !isCompleted && "text-slate-400"
                  )}
                >
                  {step.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Two-column: main content + right sidebar panel */}
      <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-12">
        <div className="space-y-4 lg:col-span-8">
          {/* Phase 8.4 — sector pre-population banner. Self-hides when
              there are no peer DVRs in this org. */}
          <SectorSuggestions aziendaId={aziendaId} />
          <section className="glass-card relative min-h-[500px] rounded-xl p-8">
            <AnimatePresence mode="wait" custom={direction}>
              <motion.div
                key={currentStep}
                custom={direction}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.3, ease: "easeInOut" }}
              >
                {renderStep()}
              </motion.div>
            </AnimatePresence>
          </section>
        </div>

        <aside className="space-y-6 lg:sticky lg:top-24 lg:col-span-4">
          <div className="glass-card rounded-xl p-6">
            <h4 className="mb-6 font-heading text-lg font-bold text-primary-container">
              Riepilogo Sopralluogo
            </h4>
            <div className="mb-6 flex flex-col items-center">
              <div className="relative flex h-32 w-32 items-center justify-center">
                <svg className="h-full w-full -rotate-90 transform">
                  <circle
                    className="text-slate-100"
                    cx="64"
                    cy="64"
                    fill="transparent"
                    r="58"
                    stroke="currentColor"
                    strokeWidth="8"
                  />
                  <circle
                    className="text-primary-container transition-all duration-500"
                    cx="64"
                    cy="64"
                    fill="transparent"
                    r="58"
                    stroke="currentColor"
                    strokeDasharray={circumference}
                    strokeDashoffset={progressDashOffset}
                    strokeWidth="8"
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="font-heading text-2xl font-black text-primary-container">
                    {progressPct}%
                  </span>
                  <span className="text-[9px] font-bold uppercase text-slate-400">
                    Progresso
                  </span>
                </div>
              </div>
            </div>
            <ul className="space-y-2">
              {STEPS.map((step, index) => {
                const isActive = index === currentStep;
                // H1: green check is content-driven, not "did the operator
                // click past it". Active step never collapses to the
                // completed badge so the "In corso" pill always wins.
                const isCompleted = !isActive && isStepComplete(index);
                return (
                  <li
                    key={step.key}
                    className={cn(
                      "flex items-center justify-between rounded-lg p-3",
                      isCompleted && "bg-surface-low",
                      isActive &&
                        "border border-primary-container/20 bg-primary-container/10",
                      !isActive && !isCompleted && "bg-surface-low/50 opacity-60"
                    )}
                  >
                    <div className="flex items-center gap-3">
                      {isCompleted ? (
                        <Check
                          className="h-5 w-5 text-green-600"
                          strokeWidth={2.5}
                        />
                      ) : isActive ? (
                        <Circle
                          className="h-5 w-5 text-primary-container"
                          strokeWidth={2}
                        />
                      ) : (
                        <Circle
                          className="h-5 w-5 text-slate-300"
                          strokeWidth={1.5}
                        />
                      )}
                      <span
                        className={cn(
                          "text-sm",
                          isActive && "font-bold text-primary-container",
                          isCompleted && "font-medium text-slate-700",
                          !isActive && !isCompleted && "text-slate-400"
                        )}
                      >
                        {step.label}
                        {!step.required && (
                          <span className="ml-1 text-[10px] font-medium uppercase text-slate-400">
                            (opz.)
                          </span>
                        )}
                      </span>
                    </div>
                    {isActive && (
                      <span className="text-xs font-bold text-primary-container">
                        In corso
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        </aside>
      </div>

      {/* Sticky footer action bar */}
      <footer className="fixed bottom-0 left-64 right-0 z-40 flex h-16 items-center justify-between border-t border-slate-200/50 bg-white/90 px-8 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <CloudUpload className="h-4 w-4 text-green-600" strokeWidth={2} />
          <span className="text-[11px] font-medium tracking-tight text-slate-400">
            Passo {currentStep + 1} di {STEPS.length}
            {saving ? " — salvataggio..." : " — bozza salvata"}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={goPrev}
            disabled={currentStep === 0 || isSigned}
            className="flex items-center gap-2 rounded-lg border-2 border-slate-200 px-6 py-2 text-sm font-bold text-slate-500 transition-all hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <ChevronLeft className="h-[18px] w-[18px]" strokeWidth={2.5} />
            Indietro
          </button>
          {currentStep < STEPS.length - 1 ? (
            <button
              type="button"
              onClick={goNext}
              disabled={nextDisabled}
              title={nextDisabled ? nextDisabledReason : undefined}
              className="flex items-center gap-2 rounded-lg bg-primary-container px-8 py-2 text-sm font-bold text-white shadow-lg transition-all hover:-translate-y-0.5 hover:shadow-primary-container/30 active:translate-y-0 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Avanti
              <ChevronRight className="h-[18px] w-[18px]" strokeWidth={2.5} />
            </button>
          ) : isSigned ? (
            // B-03 (Bug B): once the survey is firmato the firma itself
            // *is* the completion. The dashboard, activity log, and DVR
            // progress all roll firmato up to "DVR completato 100%". So
            // the bottom-right action no longer claims to "complete" —
            // it confirms the completed state and routes back to the
            // azienda page where documents and the firma badge live.
            <Link
              href={`/aziende/${aziendaId}`}
              className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-8 py-2 text-sm font-bold text-white shadow-lg transition-all hover:-translate-y-0.5 hover:bg-green-700"
            >
              <Check className="h-4 w-4" strokeWidth={2.5} />
              Sopralluogo Completato
            </Link>
          ) : (
            <Button
              onClick={handleComplete}
              disabled={saving || completionIssues.length > 0}
              title={
                completionIssues.length > 0
                  ? `Prerequisiti mancanti: ${completionIssues.join(" • ")}`
                  : undefined
              }
              className="rounded-lg bg-primary-container px-8 py-2 text-sm font-bold text-white shadow-lg hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? "Salvataggio..." : "Completa Sopralluogo"}
              {!saving && <Check className="ml-1 h-4 w-4" />}
            </Button>
          )}
        </div>
      </footer>
    </div>
  );
}
