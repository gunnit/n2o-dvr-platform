"use client";

import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface DeleteAziendaDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  ragioneSociale: string;
  onConfirm: () => Promise<void>;
}

/**
 * Confirmation dialog for deleting an azienda. Mirrors a shadcn-style
 * AlertDialog using the project's Dialog primitive — base-ui exposes a
 * single Dialog component, so we just style it to look destructive
 * (icon + warning copy + red Confirm button).
 *
 * The actual DELETE request lives in the parent so it can manage the
 * post-delete redirect and toast.
 */
export function DeleteAziendaDialog({
  open,
  onOpenChange,
  ragioneSociale,
  onConfirm,
}: DeleteAziendaDialogProps) {
  const [submitting, setSubmitting] = useState(false);

  async function handleConfirm() {
    if (submitting) return;
    setSubmitting(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <div className="flex items-start gap-3">
            <span className="inline-flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md bg-[rgba(234,34,97,0.08)]">
              <AlertTriangle
                className="h-4 w-4 text-[#b51648]"
                strokeWidth={2}
              />
            </span>
            <div className="space-y-1.5">
              <DialogTitle>Eliminare azienda?</DialogTitle>
              <DialogDescription>
                Stai per eliminare{" "}
                <span className="font-medium text-[#061b31]">
                  {ragioneSociale}
                </span>{" "}
                e tutti i dati collegati (persone, ambienti, attrezzature,
                rischi, documenti). L&apos;operazione non puo&apos; essere
                annullata.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            Annulla
          </Button>
          <Button
            type="button"
            onClick={handleConfirm}
            disabled={submitting}
            className="bg-[#b51648] text-white hover:bg-[#9b1340] focus-visible:ring-[#b51648]/30"
          >
            {submitting ? "Eliminazione..." : "Elimina definitivamente"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
