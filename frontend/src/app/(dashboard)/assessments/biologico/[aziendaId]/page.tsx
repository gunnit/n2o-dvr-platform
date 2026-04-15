"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

/**
 * Valutazione Rischio Biologico - settore alimentare / asilo / dentisti
 * (US-3.15). D.Lgs. 81/2008 Titolo X.
 */
export default function BiologicoAssessmentPage({
  params,
}: {
  params: { aziendaId: string };
}) {
  const [settore, setSettore] = useState("alimentare");
  const [protocollo, setProtocollo] = useState("");

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Valutazione Rischio Biologico
        </h1>
        <p className="text-muted-foreground">
          D.Lgs. 81/2008 Titolo X - Esposizione ad agenti biologici
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Settore di riferimento</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="settore">Settore</Label>
            <select
              id="settore"
              value={settore}
              onChange={(e) => setSettore(e.target.value)}
              className="h-9 rounded-lg border border-input bg-transparent px-3 py-1 text-sm"
            >
              <option value="alimentare">Alimentare (Reg. CE 852/2004)</option>
              <option value="asilo">Asilo nido / scuola infanzia</option>
              <option value="dentisti">Studio odontoiatrico</option>
            </select>
            <p className="text-xs text-muted-foreground">
              Gli agenti biologici di riferimento per il settore selezionato e le
              misure tipiche saranno pre-compilate nel documento generato.
            </p>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="protocollo">Protocollo sanitario aziendale</Label>
            <Textarea
              id="protocollo"
              value={protocollo}
              onChange={(e) => setProtocollo(e.target.value)}
              rows={5}
              placeholder="Descrivi il protocollo di sorveglianza sanitaria: visite mediche, esami periodici, vaccinazioni, etc."
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline">Annulla</Button>
            <Button>Salva valutazione</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
