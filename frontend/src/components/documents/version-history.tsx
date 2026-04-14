"use client";

import { Download, FileText, History } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import type { DocumentoGenerato } from "@/types";

interface VersionHistoryProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tipoDocumento: string;
  tipoDocumentoLabel: string;
  aziendaLabel: string;
  // Expected to be pre-sorted with highest versione first.
  versions: DocumentoGenerato[];
}

const statusLabels: Record<string, { color: string; label: string }> = {
  pending: { color: "bg-gray-100 text-gray-700", label: "In attesa" },
  generating: { color: "bg-yellow-100 text-yellow-700", label: "In generazione" },
  ready: { color: "bg-green-100 text-green-700", label: "Pronto" },
  error: { color: "bg-red-100 text-red-700", label: "Errore" },
};

function formatItalianDateTime(iso: string): string {
  return new Date(iso).toLocaleString("it-IT", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

// Returns a short Italian summary of the delta between two versions.
// Covers elapsed time and any status transition.
function buildDiffSummary(
  current: DocumentoGenerato,
  previous: DocumentoGenerato
): string {
  const currMs = new Date(current.created_at).getTime();
  const prevMs = new Date(previous.created_at).getTime();
  const diffMs = Math.max(0, currMs - prevMs);

  const minutes = Math.round(diffMs / (1000 * 60));
  const hours = Math.round(diffMs / (1000 * 60 * 60));
  const days = Math.round(diffMs / (1000 * 60 * 60 * 24));

  let gap: string;
  if (minutes < 60) {
    gap = `${minutes} ${minutes === 1 ? "minuto" : "minuti"}`;
  } else if (hours < 48) {
    gap = `${hours} ${hours === 1 ? "ora" : "ore"}`;
  } else {
    gap = `${days} ${days === 1 ? "giorno" : "giorni"}`;
  }

  const parts = [`+${gap} da v${previous.versione}`];

  if (current.status !== previous.status) {
    const prevStatus = statusLabels[previous.status]?.label ?? previous.status;
    const currStatus = statusLabels[current.status]?.label ?? current.status;
    parts.push(`stato: ${prevStatus} -> ${currStatus}`);
  }

  return parts.join(" \u00b7 ");
}

function downloadUrl(id: string): string {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return `${base}/api/v1/documenti/${id}/download`;
}

export function VersionHistory({
  open,
  onOpenChange,
  tipoDocumentoLabel,
  aziendaLabel,
  versions,
}: VersionHistoryProps) {
  const latestVersione = versions[0]?.versione;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-xl">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <History className="h-4 w-4 text-muted-foreground" />
            Cronologia versioni &mdash; {tipoDocumentoLabel}
          </SheetTitle>
          <SheetDescription>{aziendaLabel}</SheetDescription>
        </SheetHeader>

        <Separator />

        <div className="flex-1 overflow-y-auto px-4 pb-6">
          {versions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileText className="mb-3 h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                Nessuna versione disponibile per questo documento.
              </p>
            </div>
          ) : (
            <ol className="relative space-y-5 border-l border-border pl-5">
              {versions.map((version, idx) => {
                const isCurrent = version.versione === latestVersione;
                const statusInfo =
                  statusLabels[version.status] ?? {
                    color: "bg-gray-100 text-gray-700",
                    label: version.status,
                  };
                const previous = versions[idx + 1];
                const diffSummary = previous
                  ? buildDiffSummary(version, previous)
                  : null;

                return (
                  <li key={version.id} className="relative">
                    <span
                      className={
                        "absolute -left-[29px] top-1.5 flex h-4 w-4 items-center justify-center rounded-full border-2 border-background " +
                        (isCurrent ? "bg-primary" : "bg-muted")
                      }
                      aria-hidden
                    />
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge
                          className={
                            isCurrent
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted text-muted-foreground"
                          }
                        >
                          v{version.versione}
                        </Badge>
                        <Badge className={statusInfo.color}>
                          {statusInfo.label}
                        </Badge>
                        {isCurrent && (
                          <span className="text-xs font-medium text-primary">
                            Versione corrente
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-muted-foreground">
                        Creato il {formatItalianDateTime(version.created_at)}
                      </p>

                      {diffSummary && (
                        <p className="text-xs text-muted-foreground">
                          {diffSummary}
                        </p>
                      )}

                      {version.status === "ready" && version.file_path && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            window.open(downloadUrl(version.id), "_blank");
                          }}
                        >
                          <Download className="mr-1.5 h-3 w-3" />
                          Scarica
                        </Button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
