"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

import { AllegatoBadge } from "./allegato-badge";
import type { RiskMatch } from "./types";

interface Props {
  match: RiskMatch | null;
  action: "accept" | "reject" | null;
  onClose: () => void;
  onConfirm: (payload: {
    justification?: string;
    misura_alternativa?: string;
  }) => Promise<void> | void;
  busy?: boolean;
}

/**
 * Modal that collects the operator's justification when accepting a
 * relocation proposal, or the misura alternativa when rejecting it.
 *
 * Both fields require >= 10 non-whitespace characters (mirrors the backend
 * Pydantic validator in app/schemas/gestanti.py).
 */
export function RelocationDialog({
  match,
  action,
  onClose,
  onConfirm,
  busy = false,
}: Props) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Reset text when a fresh match/action comes in.
  useEffect(() => {
    if (match && action) {
      setText("");
      setError(null);
    }
  }, [match, action]);

  if (!match || !action) return null;

  const isAccept = action === "accept";
  const title = isAccept ? "Accetta riallocazione" : "Rifiuta riallocazione";
  const fieldLabel = isAccept
    ? "Motivazione della riallocazione"
    : "Misura alternativa adottata";
  const fieldHint = isAccept
    ? "Descrivi brevemente la nuova mansione assegnata e il razionale della scelta (min 10 caratteri)."
    : "Descrivi la misura tecnica / organizzativa / procedurale adottata in alternativa alla riallocazione (min 10 caratteri).";

  const handleSubmit = async () => {
    const trimmed = text.trim();
    if (trimmed.length < 10) {
      setError("Il testo deve contenere almeno 10 caratteri.");
      return;
    }
    setError(null);
    try {
      await onConfirm(
        isAccept
          ? { justification: trimmed }
          : { misura_alternativa: trimmed },
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Errore durante il salvataggio.",
      );
    }
  };

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            <span className="mr-2 inline-block align-middle">
              <AllegatoBadge allegato={match.allegato} />
            </span>
            <span className="align-middle text-foreground">
              {match.descrizione}
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <Label htmlFor="relocation-text">{fieldLabel}</Label>
          <textarea
            id="relocation-text"
            rows={5}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={
              isAccept
                ? "Es. Riallocata a mansione di back-office amministrativo, senza esposizione al rischio."
                : "Es. Fornito seggiolino ergonomico e riduzione a 4 ore effettive con pause ogni 40 minuti."
            }
            className="w-full resize-y rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          />
          <p className="text-xs text-muted-foreground">{fieldHint}</p>
          {isAccept && match.suggested_alternative_mansione && (
            <p className="text-xs text-muted-foreground">
              Suggerimento sistema:
              {" "}
              <span className="font-medium text-foreground">
                {match.suggested_alternative_mansione}
              </span>
            </p>
          )}
          {error && (
            <p className="text-xs text-destructive" role="alert">
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={busy}>
            Annulla
          </Button>
          <Button onClick={handleSubmit} disabled={busy}>
            {busy ? "Salvataggio…" : "Conferma"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
