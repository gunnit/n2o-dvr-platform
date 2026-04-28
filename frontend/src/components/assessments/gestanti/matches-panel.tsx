"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { AlertTriangle, CheckCircle2 } from "lucide-react";

import { AllegatoBadge } from "./allegato-badge";
import type { CrossReferenceResponse, RiskMatch } from "./types";

interface Props {
  data: CrossReferenceResponse | null;
  onDecide: (match: RiskMatch, action: "accept" | "reject") => void;
}

/**
 * Renders the list of incompatible risks for the selected lavoratrice.
 *
 * Zero matches: a single green "Nessun rischio identificato" card.
 * Otherwise: one row per match with allegato badge, description, the
 * suggested alternative mansione, accept / reject actions and — if a
 * decision was already persisted — a summary line showing it.
 */
export function MatchesPanel({ data, onDecide }: Props) {
  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Cross-riferimento rischi</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Seleziona una lavoratrice per eseguire il cross-riferimento con il
          D.Lgs. 151/2001.
        </CardContent>
      </Card>
    );
  }

  if (data.cleared) {
    return (
      <Card className="border-emerald-300 bg-emerald-100">
        <CardContent className="flex items-start gap-3 py-4">
          <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-700" />
          <div>
            <p className="text-sm font-semibold text-emerald-950">
              Nessun rischio identificato
            </p>
            <p className="text-xs text-emerald-900">
              La mansione{" "}
              <span className="font-medium text-foreground">
                {data.worker_mansione ?? "—"}
              </span>{" "}
              di {data.worker_nominativo} non presenta incompatibilita' con gli
              Allegati A, B o C del D.Lgs. 151/2001. Nessuna riallocazione
              necessaria.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2 border-b">
        <div>
          <CardTitle className="text-sm">
            Rischi incompatibili rilevati ({data.matches.length})
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Lavoratrice:{" "}
            <span className="font-medium text-foreground">
              {data.worker_nominativo}
            </span>{" "}
            · Mansione:{" "}
            <span className="font-medium text-foreground">
              {data.worker_mansione ?? "—"}
            </span>
          </p>
        </div>
        <AlertTriangle className="size-5 text-amber-500" aria-hidden />
      </CardHeader>
      <CardContent className="divide-y p-0">
        {data.matches.map((match) => (
          <MatchRow key={match.risk_key} match={match} onDecide={onDecide} />
        ))}
      </CardContent>
    </Card>
  );
}

function MatchRow({
  match,
  onDecide,
}: {
  match: RiskMatch;
  onDecide: (match: RiskMatch, action: "accept" | "reject") => void;
}) {
  const hasDecision = match.decision !== null;

  return (
    <div className="flex flex-col gap-3 p-4 md:flex-row md:items-start md:justify-between">
      <div className="flex-1 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <AllegatoBadge allegato={match.allegato} />
          {match.is_new && (
            <Badge
              variant="secondary"
              className="bg-amber-500/20 text-amber-800"
              title="Questo rischio e' stato introdotto dopo l'ultima valutazione salvata per questa lavoratrice."
            >
              Nuovo
            </Badge>
          )}
          {hasDecision && (
            <Badge
              variant="outline"
              className={cn(
                match.decision === "accept"
                  ? "border-emerald-500/40 text-emerald-700"
                  : "border-rose-500/40 text-rose-700",
              )}
            >
              {match.decision === "accept" ? "Accettata" : "Rifiutata"}
            </Badge>
          )}
        </div>
        <p className="text-sm text-foreground">{match.descrizione}</p>
        {match.suggested_alternative_mansione && (
          <p className="text-xs text-muted-foreground">
            Riallocazione suggerita:{" "}
            <span className="font-medium text-foreground">
              {match.suggested_alternative_mansione}
            </span>
          </p>
        )}
        {hasDecision && (
          <p className="text-xs text-muted-foreground">
            <span className="font-medium">
              {match.decision === "accept" ? "Motivazione" : "Misura alternativa"}:
            </span>{" "}
            {match.decision === "accept"
              ? match.justification
              : match.misura_alternativa}
          </p>
        )}
      </div>
      <div className="flex shrink-0 gap-2">
        <Button
          size="sm"
          variant={match.decision === "accept" ? "default" : "outline"}
          onClick={() => onDecide(match, "accept")}
        >
          Accetta riallocazione
        </Button>
        <Button
          size="sm"
          variant={match.decision === "reject" ? "default" : "outline"}
          onClick={() => onDecide(match, "reject")}
        >
          Rifiuta
        </Button>
      </div>
    </div>
  );
}
