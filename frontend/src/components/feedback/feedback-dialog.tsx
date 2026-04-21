"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { Bug, Lightbulb, Loader2, MessageCircle } from "lucide-react";
import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useApi } from "@/hooks/use-api";
import { cn } from "@/lib/utils";

type FeedbackType = "bug" | "idea" | "observation";

const TYPE_OPTIONS: {
  value: FeedbackType;
  label: string;
  icon: typeof Bug;
  description: string;
}[] = [
  {
    value: "bug",
    label: "Bug",
    icon: Bug,
    description: "Qualcosa non funziona come dovrebbe",
  },
  {
    value: "idea",
    label: "Idea",
    icon: Lightbulb,
    description: "Una proposta per migliorare",
  },
  {
    value: "observation",
    label: "Osservazione",
    icon: MessageCircle,
    description: "Un commento o suggerimento",
  },
];

export function FeedbackDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { apiFetch } = useApi();
  const pathname = usePathname();

  const [type, setType] = useState<FeedbackType>("bug");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setType("bug");
      setDescription("");
    }
  }, [open]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!description.trim()) return;
    setSubmitting(true);
    try {
      await apiFetch("/api/v1/feedback", {
        method: "POST",
        body: JSON.stringify({
          type,
          description: description.trim(),
          page_url:
            typeof window !== "undefined" ? window.location.href : null,
          route: pathname ?? null,
          user_agent:
            typeof navigator !== "undefined" ? navigator.userAgent : null,
        }),
      });
      toast.success("Grazie, abbiamo ricevuto la tua segnalazione.");
      onOpenChange(false);
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Invio non riuscito. Riprova tra poco.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Segnala</DialogTitle>
          <DialogDescription>
            Aiutaci a migliorare N2O DVR. Segnala bug, idee o osservazioni —
            rispondiamo alle più urgenti per prime.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-5">
          <div className="space-y-2">
            <Label>Tipo</Label>
            <div className="grid grid-cols-3 gap-2">
              {TYPE_OPTIONS.map((opt) => {
                const Icon = opt.icon;
                const active = type === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setType(opt.value)}
                    className={cn(
                      "flex flex-col items-center gap-1.5 rounded-md border px-2 py-3 text-xs transition-colors",
                      active
                        ? "border-primary bg-primary/5 text-primary"
                        : "border-[#e5edf5] bg-white text-[#334155] hover:bg-slate-50",
                    )}
                  >
                    <Icon className="h-4 w-4" strokeWidth={1.75} />
                    <span className="font-medium">{opt.label}</span>
                  </button>
                );
              })}
            </div>
            <p className="text-xs text-muted-foreground">
              {TYPE_OPTIONS.find((o) => o.value === type)?.description}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="feedback_description">Descrizione</Label>
            <Textarea
              id="feedback_description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Cosa è successo? Dove? Cosa ti aspettavi?"
              rows={5}
              required
              maxLength={5000}
            />
            <p className="text-xs text-muted-foreground">
              La pagina attuale e il tuo browser vengono allegati
              automaticamente.
            </p>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Annulla
            </Button>
            <Button type="submit" disabled={submitting || !description.trim()}>
              {submitting && (
                <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
              )}
              Invia
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
