"use client";

import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
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
  ChevronLeft,
  ChevronRight,
  Check,
  Lock,
} from "lucide-react";
import type {
  Azienda,
  Persona,
  Ambiente,
  Attrezzatura,
  ValutazioneRischio,
  SostanzaChimica,
} from "@/types";

import { StepAzienda } from "./steps/step-azienda";
import { StepPersone } from "./steps/step-persone";
import { StepAmbienti } from "./steps/step-ambienti";
import { StepAttrezzature } from "./steps/step-attrezzature";
import { StepRischi, ambientiSignature } from "./steps/step-rischi";
import { StepSostanze } from "./steps/step-sostanze";
import { StepRiepilogo } from "./steps/step-riepilogo";

const STEPS = [
  { key: "azienda", label: "Dati Azienda", icon: Building2 },
  { key: "persone", label: "Persone", icon: Users },
  { key: "ambienti", label: "Ambienti", icon: MapPin },
  { key: "attrezzature", label: "Attrezzature", icon: Wrench },
  { key: "rischi", label: "Valutazione Rischi", icon: ShieldAlert },
  { key: "sostanze", label: "Sostanze Chimiche", icon: FlaskConical },
  { key: "riepilogo", label: "Riepilogo", icon: ClipboardCheck },
] as const;

export interface SurveyData {
  azienda: Partial<Azienda>;
  persone: Persona[];
  ambienti: Ambiente[];
  attrezzature: Attrezzatura[];
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
  // to Step 7 until the operator opens an audited revision. Anything else
  // (draft, step_1..7, in_revisione, completed) allows free navigation.
  const [surveyStatus, setSurveyStatus] =
    useState<string>(initialSurveyStatus);
  const [signedAt, setSignedAt] = useState<string | null>(initialSignedAt);

  const isSigned = surveyStatus === "firmato";

  const [currentStep, setCurrentStep] = useState(isSigned ? 6 : 0);
  const [direction, setDirection] = useState(0);
  const [saving, setSaving] = useState(false);

  const [data, setData] = useState<SurveyData>({
    azienda: initialData?.azienda ?? {},
    persone: initialData?.persone ?? [],
    ambienti: initialData?.ambienti ?? [],
    attrezzature: initialData?.attrezzature ?? [],
    valutazioni: initialData?.valutazioni ?? [],
    sostanze: initialData?.sostanze ?? [],
  });

  // US-1.5 AC3: ambienti signature the operator has last acknowledged
  // on Step 5. Lives at wizard scope so it survives Step 5 unmount/
  // remount under <AnimatePresence mode="wait">. Lazy initializer seeds
  // it from the initial ambienti list, so a fresh page load does NOT
  // surface the banner — only an in-session edit on Step 3 does.
  const [acknowledgedAmbientiSig, setAcknowledgedAmbientiSig] =
    useState<string>(() => ambientiSignature(initialData?.ambienti ?? []));

  const acknowledgeAmbienti = useCallback((sig: string) => {
    setAcknowledgedAmbientiSig(sig);
  }, []);

  // Keep the wizard pinned on the Riepilogo step whenever the survey is
  // signed — step-navigation handlers short-circuit below, but if the
  // user arrives deep-linked to an earlier step we still want to bounce
  // them to Step 7.
  useEffect(() => {
    if (isSigned && currentStep !== 6) {
      setCurrentStep(6);
    }
  }, [isSigned, currentStep]);

  const updateAzienda = useCallback(
    (fields: Partial<Azienda>) => {
      setData((prev) => ({ ...prev, azienda: { ...prev.azienda, ...fields } }));
    },
    []
  );

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

  const updateSostanze = useCallback((sostanze: SostanzaChimica[]) => {
    setData((prev) => ({ ...prev, sostanze }));
  }, []);

  const goToStep = useCallback(
    (step: number) => {
      // US-1.6 AC4: when the survey is firmato, the only reachable step
      // is Step 7 (Riepilogo). Any navigation attempt bounces there.
      if (isSigned && step !== 6) return;
      setDirection(step > currentStep ? 1 : -1);
      setCurrentStep(step);
    },
    [currentStep, isSigned]
  );

  const goNext = useCallback(() => {
    if (isSigned) return;
    if (currentStep < STEPS.length - 1) {
      setDirection(1);
      setCurrentStep((prev) => prev + 1);
    }
  }, [currentStep, isSigned]);

  const goPrev = useCallback(() => {
    if (isSigned) return;
    if (currentStep > 0) {
      setDirection(-1);
      setCurrentStep((prev) => prev - 1);
    }
  }, [currentStep, isSigned]);

  const handleComplete = useCallback(async () => {
    setSaving(true);
    try {
      const sessionRes = await fetch("/api/auth/session");
      const session = await sessionRes.json();
      const token = session?.accessToken;

      await fetch(`http://localhost:8000/api/v1/aziende/${aziendaId}/survey/complete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(data),
      });
    } catch (err) {
      console.error("Error completing survey:", err);
    } finally {
      setSaving(false);
    }
  }, [aziendaId, data]);

  // US-1.6: POST signed PNG → backend stamps server-side timestamp and
  // flips survey_status to "firmato". Returns the new lifecycle state so
  // the wizard can gate nav without a round-trip refetch.
  const handleSign = useCallback(
    async (signature: { dataUrl: string; signedByName?: string | null }) => {
      const sessionRes = await fetch("/api/auth/session");
      const session = await sessionRes.json();
      const token = session?.accessToken;

      const res = await fetch(
        `http://localhost:8000/api/v1/aziende/${aziendaId}/survey/sign`,
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
      `http://localhost:8000/api/v1/aziende/${aziendaId}/survey/revision`,
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
          />
        );
      case 1:
        return (
          <StepPersone
            aziendaId={aziendaId}
            persone={data.persone}
            ambienti={data.ambienti}
            onChange={updatePersone}
          />
        );
      case 2:
        return (
          <StepAmbienti
            aziendaId={aziendaId}
            ambienti={data.ambienti}
            onChange={updateAmbienti}
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
      case 5:
        return (
          <StepSostanze
            aziendaId={aziendaId}
            sostanze={data.sostanze}
            onChange={updateSostanze}
          />
        );
      case 6:
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

  return (
    <div className="space-y-6">
      {/* US-1.6: lock banner when survey is firmato — nav is frozen until
         the operator opens an audited revision via Step 7. */}
      {isSigned && (
        <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800 dark:border-green-800 dark:bg-green-900/20 dark:text-green-400">
          <Lock className="h-4 w-4" />
          <span>
            Sopralluogo firmato — navigazione bloccata. Clicca
            &ldquo;Apri revisione&rdquo; nel riepilogo per modificare.
          </span>
        </div>
      )}

      {/* Progress bar */}
      <nav className="relative">
        <div className="flex items-center justify-between">
          {STEPS.map((step, index) => {
            const Icon = step.icon;
            const isActive = index === currentStep;
            const isCompleted = index < currentStep;
            const navDisabled = isSigned && index !== 6;

            return (
              <button
                key={step.key}
                type="button"
                onClick={() => goToStep(index)}
                disabled={navDisabled}
                className={cn(
                  "group relative flex flex-col items-center gap-1.5",
                  "transition-colors duration-200",
                  isActive && "text-primary",
                  isCompleted && "text-primary",
                  !isActive && !isCompleted && "text-muted-foreground",
                  navDisabled && "cursor-not-allowed opacity-50"
                )}
              >
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all duration-200",
                    isActive &&
                      "border-primary bg-primary text-primary-foreground shadow-md",
                    isCompleted &&
                      "border-primary bg-primary/10 text-primary",
                    !isActive &&
                      !isCompleted &&
                      "border-muted-foreground/30 bg-background text-muted-foreground group-hover:border-muted-foreground/50"
                  )}
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </div>
                <span className="hidden text-xs font-medium lg:block">
                  {step.label}
                </span>
              </button>
            );
          })}
        </div>

        {/* Connecting line */}
        <div className="absolute left-0 right-0 top-5 -z-10 mx-auto h-0.5 bg-muted-foreground/20">
          <div
            className="h-full bg-primary transition-all duration-500 ease-out"
            style={{
              width: `${(currentStep / (STEPS.length - 1)) * 100}%`,
            }}
          />
        </div>
      </nav>

      {/* Step content */}
      <div className="relative min-h-[500px] overflow-hidden">
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
      </div>

      {/* Navigation buttons */}
      <div className="flex items-center justify-between border-t pt-4">
        <Button
          variant="outline"
          onClick={goPrev}
          disabled={currentStep === 0 || isSigned}
        >
          <ChevronLeft className="mr-1 h-4 w-4" />
          Indietro
        </Button>

        <span className="text-sm text-muted-foreground">
          Passo {currentStep + 1} di {STEPS.length}
        </span>

        {currentStep < STEPS.length - 1 ? (
          <Button onClick={goNext} disabled={isSigned}>
            Avanti
            <ChevronRight className="ml-1 h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleComplete} disabled={saving || isSigned}>
            {saving ? "Salvataggio..." : "Completa Sopralluogo"}
            {!saving && <Check className="ml-1 h-4 w-4" />}
          </Button>
        )}
      </div>
    </div>
  );
}
