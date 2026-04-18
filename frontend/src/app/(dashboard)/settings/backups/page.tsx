"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Database,
  Loader2,
  Mail,
  RefreshCw,
  Shield,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useApi } from "@/hooks/use-api";

/**
 * Admin backup status panel (US-5.4).
 *
 * Surfaces the Render Postgres backup configuration (provider, region,
 * schedule, retention) plus a recent-events history sourced from the
 * AuditLog. AC1 — last successful timestamp, region, retention. AC2 —
 * failures show inline with their message and timestamp; the underlying
 * audit row is what an operator (or pager) consumes for alerting.
 *
 * AC3 (restore wizard against an isolated test environment) is *not*
 * implemented here — Render's web UI is the canonical restore surface
 * for managed Postgres, and proxying it would require a Render API
 * token + workspace permissions we don't currently grant to the app.
 * That ships as a follow-up; the panel links out to Render so the admin
 * always knows where to go. We keep the surface honest by labelling the
 * status as a *visibility* panel, not a control plane.
 */

interface BackupEvent {
  id: string;
  action: string;
  occurred_at: string;
  user_id: string | null;
  backup_id: string | null;
  message: string | null;
}

interface BackupStatus {
  provider: string;
  region: string;
  schedule: string;
  retention_days: number;
  alert_email: string;
  last_successful_at: string | null;
  last_failure_at: string | null;
  last_failure_message: string | null;
  history: BackupEvent[];
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("it-IT", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function ActionBadge({ action }: { action: string }) {
  if (action === "backup_completed") {
    return (
      <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
        <CheckCircle2 className="mr-1 h-3 w-3" />
        Completato
      </Badge>
    );
  }
  if (action === "backup_failed") {
    return (
      <Badge className="bg-red-100 text-red-700 hover:bg-red-100">
        <AlertCircle className="mr-1 h-3 w-3" />
        Fallito
      </Badge>
    );
  }
  return <Badge variant="secondary">{action}</Badge>;
}

export default function BackupsSettingsPage() {
  const { apiFetch } = useApi();
  const { data: session, status: sessionStatus } = useSession();
  const router = useRouter();

  const [status, setStatus] = useState<BackupStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Bounce non-admins back to the dashboard. The backend already rejects
  // them with 403 — this is purely a UX shortcut.
  useEffect(() => {
    if (sessionStatus !== "authenticated") return;
    const role = (session?.user as { role?: string } | undefined)?.role;
    if (role !== "admin") {
      router.replace("/dashboard");
    }
  }, [session, sessionStatus, router]);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await apiFetch<BackupStatus>("/api/v1/admin/backups/status");
      setStatus(data);
    } catch (err) {
      setLoadError(
        err instanceof Error ? err.message : "Caricamento stato backup non riuscito.",
      );
    } finally {
      setLoading(false);
    }
  }, [apiFetch]);

  useEffect(() => {
    load();
  }, [load]);

  const failureWithinDay =
    status?.last_failure_at &&
    Date.now() - new Date(status.last_failure_at).getTime() < 24 * 60 * 60 * 1000;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="type-h1">
            Backup &amp; ripristino
          </h1>
          <p className="text-muted-foreground">
            Stato dei backup automatici del database e cronologia degli eventi
            recenti. I backup sono gestiti da Render — questa pagina è una
            vista di sola lettura.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          {loading ? (
            <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="mr-1 h-3.5 w-3.5" />
          )}
          Aggiorna
        </Button>
      </div>

      {loadError && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {loadError}
        </div>
      )}

      {/* Status overview — AC1 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Stato corrente
          </CardTitle>
          <CardDescription>
            Configurazione del backup managed Postgres + ultimo esito noto.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {failureWithinDay && (
            <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
              <strong>Attenzione:</strong> ultimo backup fallito il{" "}
              {formatDate(status?.last_failure_at ?? null)}.{" "}
              {status?.last_failure_message ?? ""}
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              icon={<Database className="h-3.5 w-3.5" />}
              label="Provider"
              value={status?.provider ?? "—"}
            />
            <Field label="Regione" value={status?.region ?? "—"} />
            <Field
              icon={<Clock className="h-3.5 w-3.5" />}
              label="Pianificazione"
              value={status?.schedule ?? "—"}
            />
            <Field
              label="Retention"
              value={
                status ? `${status.retention_days} giorni` : "—"
              }
            />
            <Field
              icon={<CheckCircle2 className="h-3.5 w-3.5 text-green-600" />}
              label="Ultimo backup riuscito"
              value={formatDate(status?.last_successful_at ?? null)}
            />
            <Field
              icon={<Mail className="h-3.5 w-3.5" />}
              label="Email per notifiche"
              value={status?.alert_email ?? "—"}
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Per eseguire un ripristino, accedi al pannello{" "}
            <a
              className="underline"
              href="https://dashboard.render.com/"
              target="_blank"
              rel="noreferrer"
            >
              Render
            </a>{" "}
            e seleziona il punto di ripristino entro la finestra di retention.
            Lo strumento di Render esegue il restore in un ambiente isolato
            (point-in-time recovery) come richiesto dal Documento di
            Conservazione GDPR.
          </p>
        </CardContent>
      </Card>

      {/* History — AC2 (audit trail of recent events) */}
      <Card>
        <CardHeader>
          <CardTitle>Cronologia eventi</CardTitle>
          <CardDescription>
            Ultimi 30 eventi di backup registrati nell&apos;audit log. Le voci
            vengono inserite via webhook al termine di ogni esecuzione.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!status || status.history.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              Nessun evento di backup ancora registrato. Verrà popolato dopo la
              prima esecuzione del job notturno.
            </p>
          ) : (
            <div className="space-y-2">
              {status.history.map((evt) => (
                <div
                  key={evt.id}
                  className="flex items-start justify-between gap-3 rounded-md border border-border bg-background px-3 py-2"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <ActionBadge action={evt.action} />
                      <span className="text-xs font-mono text-muted-foreground">
                        {evt.backup_id ?? "—"}
                      </span>
                    </div>
                    {evt.message && (
                      <p className="text-xs text-muted-foreground">
                        {evt.message}
                      </p>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {formatDate(evt.occurred_at)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Field({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <p className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted-foreground">
        {icon}
        {label}
      </p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  );
}
