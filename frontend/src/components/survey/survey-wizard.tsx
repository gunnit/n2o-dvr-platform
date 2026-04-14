"use client";

import { useState, useCallback } from "react";
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
import { StepRischi } from "./steps/step-rischi";
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
  const [currentStep, setCurrentStep] = useState(0);
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
      setDirection(step > currentStep ? 1 : -1);
      setCurrentStep(step);
    },
    [currentStep]
  );

  const goNext = useCallback(() => {
    if (currentStep < STEPS.length - 1) {
      setDirection(1);
      setCurrentStep((prev) => prev + 1);
    }
  }, [currentStep]);

  const goPrev = useCallback(() => {
    if (currentStep > 0) {
      setDirection(-1);
      setCurrentStep((prev) => prev - 1);
    }
  }, [currentStep]);

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
            valutazioni={data.valutazioni}
            onChange={updateValutazioni}
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
          <StepRiepilogo data={data} onGoToStep={goToStep} />
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Progress bar */}
      <nav className="relative">
        <div className="flex items-center justify-between">
          {STEPS.map((step, index) => {
            const Icon = step.icon;
            const isActive = index === currentStep;
            const isCompleted = index < currentStep;

            return (
              <button
                key={step.key}
                type="button"
                onClick={() => goToStep(index)}
                className={cn(
                  "group relative flex flex-col items-center gap-1.5",
                  "transition-colors duration-200",
                  isActive && "text-primary",
                  isCompleted && "text-primary",
                  !isActive && !isCompleted && "text-muted-foreground"
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
          disabled={currentStep === 0}
        >
          <ChevronLeft className="mr-1 h-4 w-4" />
          Indietro
        </Button>

        <span className="text-sm text-muted-foreground">
          Passo {currentStep + 1} di {STEPS.length}
        </span>

        {currentStep < STEPS.length - 1 ? (
          <Button onClick={goNext}>
            Avanti
            <ChevronRight className="ml-1 h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleComplete} disabled={saving}>
            {saving ? "Salvataggio..." : "Completa Sopralluogo"}
            {!saving && <Check className="ml-1 h-4 w-4" />}
          </Button>
        )}
      </div>
    </div>
  );
}
