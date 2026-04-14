"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardAction,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  FlaskConical,
  MapPin,
  Pencil,
  PenTool,
  ShieldAlert,
  Users,
  Wrench,
} from "lucide-react";
import type { SurveyData } from "../survey-wizard";

interface StepRiepilogoProps {
  data: SurveyData;
  onGoToStep: (step: number) => void;
  onSignatureChange?: (
    signature: { dataUrl: string; timestamp: string } | null,
  ) => void;
}

function getLivelloStyle(livello: string) {
  switch (livello) {
    case "ACCETTABILE":
      return "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800";
    case "MODESTO":
      return "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800";
    case "GRAVE":
      return "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800";
    case "GRAVISSIMO":
      return "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800";
    default:
      return "";
  }
}

function SectionHeader({
  title,
  icon: Icon,
  step,
  count,
  onEdit,
  disabled,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  step: number;
  count?: number;
  onEdit: (step: number) => void;
  disabled?: boolean;
}) {
  return (
    <CardHeader>
      <CardTitle className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
        {title}
        {count !== undefined && (
          <Badge variant="secondary" className="ml-1">
            {count}
          </Badge>
        )}
      </CardTitle>
      <CardAction>
        <Button
          variant="ghost"
          size="sm"
          disabled={disabled}
          onClick={() => onEdit(step)}
        >
          <Pencil className="mr-1 h-3.5 w-3.5" />
          Modifica
        </Button>
      </CardAction>
    </CardHeader>
  );
}

export function StepRiepilogo({
  data,
  onGoToStep,
  onSignatureChange,
}: StepRiepilogoProps) {
  const { azienda, persone, ambienti, attrezzature, valutazioni, sostanze } =
    data;

  const applicableValutazioni = valutazioni.filter((v) => v.applicabile);

  // ---------------------------------------------------------------------------
  // Completion validation
  // ---------------------------------------------------------------------------
  const missingItems: { label: string; step: number }[] = [];

  if (!azienda.ragione_sociale?.trim()) {
    missingItems.push({ label: "Ragione sociale mancante", step: 0 });
  }
  if (persone.length === 0) {
    missingItems.push({ label: "Nessuna persona inserita", step: 1 });
  }
  if (ambienti.length === 0) {
    missingItems.push({ label: "Nessun ambiente inserito", step: 2 });
  }
  if (!persone.some((p) => p.ruolo_rspp)) {
    missingItems.push({
      label: "Nessun RSPP designato tra le persone",
      step: 1,
    });
  }

  const isComplete = missingItems.length === 0;

  // ---------------------------------------------------------------------------
  // Signature state
  // ---------------------------------------------------------------------------
  const [signatureDataUrl, setSignatureDataUrl] = useState<string | null>(null);
  const [isSigned, setIsSigned] = useState(false);
  const [signedTimestamp, setSignedTimestamp] = useState<string | null>(null);

  // Canvas refs and drawing state
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawingRef = useRef(false);

  // Resize canvas to match its CSS width while keeping a fixed height
  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    if (canvas.width !== rect.width || canvas.height !== 200) {
      canvas.width = rect.width;
      canvas.height = 200;
    }
  }, []);

  useEffect(() => {
    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);
    return () => window.removeEventListener("resize", resizeCanvas);
  }, [resizeCanvas]);

  // --- Drawing helpers ---
  const getPos = (
    e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
  ) => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    if ("touches" in e) {
      const touch = e.touches[0] ?? e.changedTouches[0];
      return { x: touch.clientX - rect.left, y: touch.clientY - rect.top };
    }
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const startDraw = (
    e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
  ) => {
    if (isSigned) return;
    e.preventDefault();
    isDrawingRef.current = true;
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    const pos = getPos(e);
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
  };

  const draw = (
    e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
  ) => {
    if (!isDrawingRef.current || isSigned) return;
    e.preventDefault();
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    const pos = getPos(e);
    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
  };

  const endDraw = () => {
    isDrawingRef.current = false;
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  };

  const confirmSignature = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dataUrl = canvas.toDataURL("image/png");
    const timestamp = new Date().toISOString();
    setSignatureDataUrl(dataUrl);
    setSignedTimestamp(timestamp);
    setIsSigned(true);
    onSignatureChange?.({ dataUrl, timestamp });
  };

  return (
    <div className="space-y-4">
      <div className="mb-2">
        <h2 className="text-lg font-semibold">Riepilogo Sopralluogo</h2>
        <p className="text-sm text-muted-foreground">
          Verifica i dati inseriti prima di completare il sopralluogo
        </p>
      </div>

      {/* Azienda */}
      <Card>
        <SectionHeader
          title="Dati Azienda"
          icon={Building2}
          step={0}
          onEdit={onGoToStep}
          disabled={isSigned}
        />
        <CardContent>
          <div className="grid gap-x-8 gap-y-2 sm:grid-cols-2">
            <DetailRow label="Ragione Sociale" value={azienda.ragione_sociale} />
            <DetailRow label="Attivita" value={azienda.attivita} />
            <DetailRow label="Codice ATECO" value={azienda.codice_ateco} />
            <DetailRow
              label="Sede Legale"
              value={
                [azienda.sede_legale_via, azienda.sede_legale_citta]
                  .filter(Boolean)
                  .join(", ") || undefined
              }
            />
            <DetailRow
              label="Sede Operativa"
              value={
                [azienda.sede_operativa_via, azienda.sede_operativa_citta]
                  .filter(Boolean)
                  .join(", ") || undefined
              }
            />
            <DetailRow label="Orario Lavoro" value={azienda.orario_lavoro} />
            <DetailRow
              label="Metratura Totale"
              value={
                azienda.metratura_totale
                  ? `${azienda.metratura_totale} mq`
                  : undefined
              }
            />
            <DetailRow
              label="Zona Sismica"
              value={
                azienda.zona_sismica
                  ? `Zona ${azienda.zona_sismica}`
                  : undefined
              }
            />
          </div>
        </CardContent>
      </Card>

      {/* Persone */}
      <Card>
        <SectionHeader
          title="Persone"
          icon={Users}
          step={1}
          count={persone.length}
          onEdit={onGoToStep}
          disabled={isSigned}
        />
        <CardContent>
          {persone.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nessun dipendente inserito
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nominativo</TableHead>
                  <TableHead>Mansione</TableHead>
                  <TableHead>Contratto</TableHead>
                  <TableHead>Ruoli</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {persone.map((p) => {
                  const ruoli: string[] = [];
                  if (p.ruolo_datore_lavoro) ruoli.push("DdL");
                  if (p.ruolo_rspp) ruoli.push("RSPP");
                  if (p.ruolo_rls) ruoli.push("RLS");
                  if (p.ruolo_primo_soccorso) ruoli.push("PS");
                  if (p.ruolo_antincendio) ruoli.push("AI");
                  if (p.ruolo_preposto) ruoli.push("Prep.");

                  return (
                    <TableRow key={p.id}>
                      <TableCell className="font-medium">
                        {p.nominativo || "-"}
                      </TableCell>
                      <TableCell>{p.mansione || "-"}</TableCell>
                      <TableCell>
                        {p.tipologia_contrattuale || "-"}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {ruoli.length > 0
                            ? ruoli.map((r) => (
                                <Badge
                                  key={r}
                                  variant="secondary"
                                  className="text-xs"
                                >
                                  {r}
                                </Badge>
                              ))
                            : "-"}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Ambienti */}
      <Card>
        <SectionHeader
          title="Ambienti di Lavoro"
          icon={MapPin}
          step={2}
          count={ambienti.length}
          onEdit={onGoToStep}
          disabled={isSigned}
        />
        <CardContent>
          {ambienti.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nessun ambiente inserito
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {ambienti.map((a) => (
                <div
                  key={a.id}
                  className="rounded-lg border border-input p-3 text-sm"
                >
                  <div className="font-medium">{a.nome || "-"}</div>
                  <div className="text-muted-foreground">
                    {a.tipo}
                    {a.superficie_mq
                      ? ` - ${a.superficie_mq} mq`
                      : ""}
                  </div>
                  {a.descrizione_attivita && (
                    <div className="mt-1 text-xs text-muted-foreground">
                      {a.descrizione_attivita}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Attrezzature */}
      <Card>
        <SectionHeader
          title="Attrezzature"
          icon={Wrench}
          step={3}
          count={attrezzature.length}
          onEdit={onGoToStep}
          disabled={isSigned}
        />
        <CardContent>
          {attrezzature.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nessuna attrezzatura inserita
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Descrizione</TableHead>
                  <TableHead className="text-center">
                    Marcatura CE
                  </TableHead>
                  <TableHead className="text-center">
                    Verifiche Periodiche
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {attrezzature.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell className="font-medium">
                      {a.descrizione || "-"}
                    </TableCell>
                    <TableCell className="text-center">
                      {a.marcatura_ce ? "Si" : "No"}
                    </TableCell>
                    <TableCell className="text-center">
                      {a.verifiche_periodiche ? "Si" : "No"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Valutazione Rischi */}
      <Card>
        <SectionHeader
          title="Valutazione Rischi"
          icon={ShieldAlert}
          step={4}
          count={applicableValutazioni.length}
          onEdit={onGoToStep}
          disabled={isSigned}
        />
        <CardContent>
          {applicableValutazioni.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nessuna valutazione inserita
            </p>
          ) : (
            <div className="space-y-4">
              {ambienti.map((amb) => {
                const ambValutazioni = applicableValutazioni.filter(
                  (v) => v.ambiente_id === amb.id
                );
                if (ambValutazioni.length === 0) return null;

                return (
                  <div key={amb.id}>
                    <h4 className="mb-2 text-sm font-medium">
                      {amb.nome || "Ambiente"}
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {ambValutazioni.map((v) => (
                        <div
                          key={v.id}
                          className="flex items-center gap-2 rounded-lg border border-input px-3 py-1.5 text-xs"
                        >
                          <span className="font-medium">
                            {v.categoria_rischio}
                          </span>
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-xs",
                              getLivelloStyle(
                                v.livello_rischio ?? ""
                              )
                            )}
                          >
                            {v.livello_rischio} ({v.indice_i})
                          </Badge>
                        </div>
                      ))}
                    </div>
                    <Separator className="mt-3" />
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Sostanze Chimiche */}
      <Card>
        <SectionHeader
          title="Sostanze Chimiche"
          icon={FlaskConical}
          step={5}
          count={sostanze.length}
          onEdit={onGoToStep}
          disabled={isSigned}
        />
        <CardContent>
          {sostanze.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nessuna sostanza chimica inserita
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Prodotto</TableHead>
                  <TableHead>Produttore</TableHead>
                  <TableHead>Stato</TableHead>
                  <TableHead>Pittogrammi</TableHead>
                  <TableHead>Frasi H</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sostanze.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium">
                      {s.nome_prodotto || "-"}
                    </TableCell>
                    <TableCell>{s.produttore || "-"}</TableCell>
                    <TableCell>{s.stato_miscela || "-"}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {s.pittogrammi.length > 0
                          ? s.pittogrammi.map((p) => (
                              <Badge
                                key={p}
                                variant="outline"
                                className="text-xs"
                              >
                                {p}
                              </Badge>
                            ))
                          : "-"}
                      </div>
                    </TableCell>
                    <TableCell>
                      {s.frasi_h.length > 0
                        ? s.frasi_h.join(", ")
                        : "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Firma del Cliente */}
      <Card
        className={cn(
          isSigned && "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20",
        )}
      >
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PenTool className="h-4 w-4 text-muted-foreground" />
            Firma del Cliente
            {isSigned && (
              <Badge className="ml-2 bg-green-600 text-white hover:bg-green-700">
                <CheckCircle2 className="mr-1 h-3 w-3" />
                Firmato
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!isComplete ? (
            /* Warning banner — survey incomplete */
            <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-800 dark:bg-yellow-900/20">
              <div className="mb-2 flex items-center gap-2 text-sm font-medium text-yellow-800 dark:text-yellow-400">
                <AlertTriangle className="h-4 w-4" />
                Completa il sopralluogo prima di firmare
              </div>
              <ul className="space-y-1">
                {missingItems.map((item) => (
                  <li key={item.label}>
                    <button
                      type="button"
                      className="text-sm text-yellow-800 underline underline-offset-2 hover:text-yellow-900 dark:text-yellow-400 dark:hover:text-yellow-300"
                      onClick={() => onGoToStep(item.step)}
                    >
                      {item.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : isSigned ? (
            /* Signed state */
            <div className="space-y-3">
              <DetailRow label="Data e ora firma" value={formatTimestamp(signedTimestamp!)} />
              {signatureDataUrl && (
                <div className="rounded-lg border border-input bg-white p-2 dark:bg-muted/30">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={signatureDataUrl}
                    alt="Firma del cliente"
                    className="h-[200px] w-full object-contain"
                  />
                </div>
              )}
            </div>
          ) : (
            /* Ready to sign */
            <div className="space-y-4">
              <DetailRow label="Data e ora" value={formatTimestamp(new Date().toISOString())} />

              {/* Signature canvas */}
              <div>
                <p className="mb-2 text-xs text-muted-foreground">
                  Disegna la tua firma nel riquadro sottostante
                </p>
                <canvas
                  ref={canvasRef}
                  className="w-full cursor-crosshair touch-none rounded-lg border border-input bg-white dark:bg-muted/30"
                  style={{ height: 200 }}
                  onMouseDown={startDraw}
                  onMouseMove={draw}
                  onMouseUp={endDraw}
                  onMouseLeave={endDraw}
                  onTouchStart={startDraw}
                  onTouchMove={draw}
                  onTouchEnd={endDraw}
                />
              </div>

              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={clearCanvas}
                >
                  Cancella firma
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={confirmSignature}
                >
                  Conferma firma
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value?: string | null;
}) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value || "-"}</span>
    </div>
  );
}
