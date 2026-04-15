"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

/**
 * Valutazione Gestanti - D.Lgs. 151/2001 (US-3.9, US-3.10).
 * Captures: lavoratrice, stato, data notifica/parto, rischi vietati,
 * misure di adeguamento e firme (placeholder).
 */
export default function GestantiAssessmentPage({
  params,
}: {
  params: { aziendaId: string };
}) {
  const [stato, setStato] = useState("gestante");
  const [mansioneAlternativa, setMansioneAlternativa] = useState("");
  const [misure, setMisure] = useState("");

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Valutazione Gestanti / Puerpere / Allattamento
        </h1>
        <p className="text-muted-foreground">
          Compilazione ai sensi del D.Lgs. 151/2001
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Dati lavoratrice</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="stato">Stato</Label>
            <select
              id="stato"
              value={stato}
              onChange={(e) => setStato(e.target.value)}
              className="h-9 rounded-lg border border-input bg-transparent px-3 py-1 text-sm"
            >
              <option value="gestante">Gestante</option>
              <option value="puerpera">Puerpera (fino a 7 mesi)</option>
              <option value="allattamento">Allattamento</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="notifica">Data notifica</Label>
              <Input id="notifica" type="date" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="parto">Data presunto parto</Label>
              <Input id="parto" type="date" />
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="mansione">Mansione alternativa</Label>
            <Input
              id="mansione"
              value={mansioneAlternativa}
              onChange={(e) => setMansioneAlternativa(e.target.value)}
              placeholder="Es. Impiegata back-office"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="misure">Misure di adeguamento adottate</Label>
            <Textarea
              id="misure"
              value={misure}
              onChange={(e) => setMisure(e.target.value)}
              rows={4}
              placeholder="Descrivi le misure..."
            />
          </div>
          <div className="grid grid-cols-4 gap-4">
            <div className="grid gap-1">
              <Label>Firma lavoratrice</Label>
              <Input placeholder="_____________" />
            </div>
            <div className="grid gap-1">
              <Label>Firma Datore di Lavoro</Label>
              <Input placeholder="_____________" />
            </div>
            <div className="grid gap-1">
              <Label>Firma RSPP</Label>
              <Input placeholder="_____________" />
            </div>
            <div className="grid gap-1">
              <Label>Firma Medico Competente</Label>
              <Input placeholder="_____________" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline">Annulla</Button>
            <Button>Salva valutazione</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Riferimento normativo</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Il D.Lgs. 26 marzo 2001 n. 151 tutela la salute delle lavoratrici in
            stato di gravidanza, puerperio e durante l&apos;allattamento. Gli
            Allegati A, B e C individuano rispettivamente i lavori vietati,
            quelli vietati salvo deroga e gli agenti nocivi cui non possono
            essere esposte.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
