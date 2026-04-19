"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { Database, KeyRound, Loader2, Sparkles, UserCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useApi } from "@/hooks/use-api";

interface MeResponse {
  id: string;
  email: string;
  full_name: string;
  role: string;
  organization_id: string;
}

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  operatore_ufficio: "Operatore ufficio",
  operatore_campo: "Operatore campo",
};

export default function SettingsPage() {
  const { data: session } = useSession();
  const role = (session?.user as { role?: string } | undefined)?.role;
  const isAdmin = role === "admin";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="type-h1">Impostazioni</h1>
        <p className="type-body mt-2">Gestione account e preferenze</p>
      </div>

      <ProfileCard />
      <PasswordCard />

      {/* US-5.4: only admins should see the backup status entry. The
          backup page itself also gates by role + bounces on render. */}
      {isAdmin && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-4 w-4" />
              Backup &amp; ripristino
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="type-body">
              Stato dei backup automatici del database, cronologia eventi e
              istruzioni per il ripristino dal pannello Render.
            </p>
            <Link
              href="/settings/backups"
              className="inline-flex h-9 items-center justify-center rounded-md border border-[#e5edf5] bg-white px-4 text-[13px] font-medium text-[#273951] transition-colors hover:bg-[#f6f9fc]"
            >
              Apri pannello backup
            </Link>
          </CardContent>
        </Card>
      )}

      {/* US-5.3: admin-only AI feedback panel — the page itself bounces
          non-admins, but we hide the entry too to keep the UI honest. */}
      {isAdmin && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              Feedback AI
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="type-body">
              Conteggi di accettazioni / rifiuti dei suggerimenti AI per
              superficie e cronologia degli ultimi 50 segnali — utile per
              capire dove migliorare i prompt.
            </p>
            <Link
              href="/admin/ai-feedback"
              className="inline-flex h-9 items-center justify-center rounded-md border border-[#e5edf5] bg-white px-4 text-[13px] font-medium text-[#273951] transition-colors hover:bg-[#f6f9fc]"
            >
              Apri pannello feedback AI
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ProfileCard() {
  const { apiFetch } = useApi();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<MeResponse>("/api/v1/auth/me");
      setMe(data);
      setFullName(data.full_name);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Caricamento profilo non riuscito.",
      );
    } finally {
      setLoading(false);
    }
  }, [apiFetch]);

  useEffect(() => {
    load();
  }, [load]);

  const dirty = me != null && fullName.trim() !== me.full_name;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!dirty) return;
    setSaving(true);
    try {
      const updated = await apiFetch<MeResponse>("/api/v1/auth/me", {
        method: "PATCH",
        body: JSON.stringify({ full_name: fullName.trim() }),
      });
      setMe(updated);
      setFullName(updated.full_name);
      toast.success("Profilo aggiornato");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Errore salvataggio");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserCircle className="h-4 w-4" />
          Profilo
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="type-body">Caricamento…</p>
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : me ? (
          <form onSubmit={submit} className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="full_name">Nome completo</Label>
                <Input
                  id="full_name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" value={me.email} disabled readOnly />
                <p className="text-xs text-[#64748d]">
                  L&apos;email di accesso non può essere modificata.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="role">Ruolo</Label>
                <Input
                  id="role"
                  value={ROLE_LABEL[me.role] ?? me.role}
                  disabled
                  readOnly
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="org">ID organizzazione</Label>
                <Input
                  id="org"
                  value={me.organization_id}
                  disabled
                  readOnly
                  className="font-mono text-xs"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <Button type="submit" disabled={!dirty || saving}>
                {saving && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}
                Salva modifiche
              </Button>
            </div>
          </form>
        ) : null}
      </CardContent>
    </Card>
  );
}

function PasswordCard() {
  const { apiFetch } = useApi();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const mismatch = confirm.length > 0 && next !== confirm;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    if (next !== confirm) {
      setErr("Le due nuove password non coincidono.");
      return;
    }
    setSubmitting(true);
    try {
      await apiFetch("/api/v1/auth/me/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: current,
          new_password: next,
        }),
      });
      setCurrent("");
      setNext("");
      setConfirm("");
      toast.success("Password aggiornata");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Errore");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRound className="h-4 w-4" />
          Password
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="current_password">Password attuale</Label>
              <Input
                id="current_password"
                type="password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new_password">Nuova password</Label>
              <Input
                id="new_password"
                type="password"
                minLength={8}
                value={next}
                onChange={(e) => setNext(e.target.value)}
                autoComplete="new-password"
                required
              />
              <p className="text-xs text-[#64748d]">Almeno 8 caratteri.</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm_password">Conferma nuova password</Label>
              <Input
                id="confirm_password"
                type="password"
                minLength={8}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
                required
                aria-invalid={mismatch || undefined}
              />
              {mismatch && (
                <p className="text-xs text-destructive">
                  Le password non coincidono.
                </p>
              )}
            </div>
          </div>
          {err && <p className="text-sm text-destructive">{err}</p>}
          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={
                submitting ||
                !current ||
                !next ||
                !confirm ||
                next !== confirm ||
                next.length < 8
              }
            >
              {submitting && (
                <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
              )}
              Aggiorna password
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
