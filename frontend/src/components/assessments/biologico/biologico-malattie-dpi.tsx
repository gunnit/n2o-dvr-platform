"use client";

import { useState } from "react";
import { Plus, RotateCcw, X } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

/**
 * Agente biologico as stored in BiologicoValutazione.agenti_identificati.
 * `sintomi` and `cura` were added for segnalazione 2026-10-02 ("malattie
 * contraibili con sintomi e cura").
 */
export interface AgenteBiologico {
  nome: string;
  gruppo: string;
  via: string;
  patologia: string;
  sintomi: string;
  cura: string;
}

const EMPTY_AGENTE: AgenteBiologico = {
  nome: "",
  gruppo: "",
  via: "",
  patologia: "",
  sintomi: "",
  cura: "",
};

// ---------------------------------------------------------------------------
// DPI utilizzati
// ---------------------------------------------------------------------------

export function DpiUtilizzatiCard({
  dpi,
  onChange,
  onRestore,
}: {
  dpi: string[];
  onChange: (next: string[]) => void;
  onRestore: () => void;
}) {
  const [nuovo, setNuovo] = useState("");

  const add = () => {
    const v = nuovo.trim();
    if (!v || dpi.some((d) => d.toLowerCase() === v.toLowerCase())) return;
    onChange([...dpi, v]);
    setNuovo("");
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <CardTitle className="text-sm">DPI utilizzati</CardTitle>
            <CardDescription className="text-xs">
              Proposti dal settore: togli quelli che non si usano e aggiungi
              quelli mancanti. Compaiono nel documento generato.
            </CardDescription>
          </div>
          <Button type="button" size="sm" variant="ghost" onClick={onRestore}>
            <RotateCcw className="h-3.5 w-3.5" aria-hidden />
            Ripristina proposti
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {dpi.length === 0 ? (
          <p className="text-xs text-muted-foreground">Nessun DPI indicato.</p>
        ) : (
          <ul className="space-y-1.5">
            {dpi.map((d, i) => (
              <li
                key={`${d}-${i}`}
                className="flex items-center justify-between gap-2 rounded-md border border-border bg-background px-3 py-1.5 text-sm"
              >
                <span>{d}</span>
                <button
                  type="button"
                  className="rounded-sm p-0.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                  onClick={() => onChange(dpi.filter((_, j) => j !== i))}
                  aria-label={`Rimuovi ${d}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="flex gap-2">
          <Input
            value={nuovo}
            onChange={(e) => setNuovo(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                add();
              }
            }}
            placeholder="Aggiungi un DPI…"
            aria-label="Nuovo DPI"
          />
          <Button type="button" variant="outline" onClick={add}>
            <Plus className="h-3.5 w-3.5" aria-hidden />
            Aggiungi
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Malattie contraibili: sintomi e cura
// ---------------------------------------------------------------------------

export function MalattieContraibiliCard({
  agenti,
  onChange,
  onRestore,
}: {
  agenti: AgenteBiologico[];
  onChange: (next: AgenteBiologico[]) => void;
  onRestore: () => void;
}) {
  const update = (i: number, fields: Partial<AgenteBiologico>) =>
    onChange(agenti.map((a, j) => (j === i ? { ...a, ...fields } : a)));

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <CardTitle className="text-sm">
              Malattie contraibili: sintomi e cura
            </CardTitle>
            <CardDescription className="text-xs">
              Agenti biologici del settore con le malattie che possono
              trasmettere. Sintomi e cura sono una proposta da rivedere con il
              Medico Competente; compaiono nel documento generato.
            </CardDescription>
          </div>
          <Button type="button" size="sm" variant="ghost" onClick={onRestore}>
            <RotateCcw className="h-3.5 w-3.5" aria-hidden />
            Ripristina proposti
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {agenti.length === 0 && (
          <p className="text-xs text-muted-foreground">
            Nessun agente indicato.
          </p>
        )}
        {agenti.map((a, i) => (
          <div
            key={i}
            className="space-y-2 rounded-md border border-border bg-background p-3"
          >
            <div className="flex flex-wrap items-end gap-2">
              <div className="min-w-[180px] flex-1 space-y-1">
                <Label htmlFor={`agente-${i}-patologia`} className="text-[11px] text-muted-foreground">
                  Malattia
                </Label>
                <Input
                  id={`agente-${i}-patologia`}
                  value={a.patologia}
                  onChange={(e) => update(i, { patologia: e.target.value })}
                />
              </div>
              <div className="min-w-[180px] flex-1 space-y-1">
                <Label htmlFor={`agente-${i}-nome`} className="text-[11px] text-muted-foreground">
                  Agente
                </Label>
                <Input
                  id={`agente-${i}-nome`}
                  value={a.nome}
                  onChange={(e) => update(i, { nome: e.target.value })}
                />
              </div>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => onChange(agenti.filter((_, j) => j !== i))}
                aria-label={`Rimuovi ${a.patologia || a.nome || "agente"}`}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor={`agente-${i}-sintomi`} className="text-[11px] text-muted-foreground">
                  Sintomi principali
                </Label>
                <Textarea
                  id={`agente-${i}-sintomi`}
                  rows={2}
                  value={a.sintomi}
                  onChange={(e) => update(i, { sintomi: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor={`agente-${i}-cura`} className="text-[11px] text-muted-foreground">
                  Cura e profilassi
                </Label>
                <Textarea
                  id={`agente-${i}-cura`}
                  rows={2}
                  value={a.cura}
                  onChange={(e) => update(i, { cura: e.target.value })}
                />
              </div>
            </div>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onChange([...agenti, { ...EMPTY_AGENTE }])}
        >
          <Plus className="h-3.5 w-3.5" aria-hidden />
          Aggiungi malattia
        </Button>
      </CardContent>
    </Card>
  );
}
