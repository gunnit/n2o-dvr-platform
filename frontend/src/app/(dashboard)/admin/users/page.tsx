"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  AlertCircle,
  Check,
  KeyRound,
  Loader2,
  Minus,
  RefreshCw,
  ShieldCheck,
  UserPlus,
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import { TONE_CHIP } from "@/lib/ui/tones";
import { FormError } from "@/components/ui/form-error";
import { Callout } from "@/components/ui/callout";
import { useEntitlementsContext } from "@/components/billing/entitlements-provider";
import { formatSeats } from "@/lib/billing";
import { type RoleDefinition, usePermissions, useRoles } from "@/hooks/use-permissions";
import { USERS_MANAGE, roleLabel } from "@/lib/permissions";
import { CAPABILITY_LABELS } from "@/lib/capability-labels";
import { Select } from "@/components/ui/select";

interface UserRow {
  id: string;
  email: string;
  full_name: string;
  role: string;
  created_at: string;
}

interface StatsRow {
  user_id: string;
  full_name: string;
  email: string;
  role: string;
  aziende_count: number;
  documenti_count: number;
}

// The role dropdown's options. `useRoles()` supplies richer descriptions for
// the matrix above, but the picker must still render before that request lands
// — and must keep working if it fails — so the three codes stay here. Labels
// come from `lib/permissions`, the same strings the server returns.
const ROLE_OPTIONS = ["admin", "operatore_ufficio", "operatore_campo"].map(
  (value) => ({ value, label: roleLabel(value) }),
);

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("it-IT", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function RoleBadge({ role }: { role: string }) {
  // Privilege ramp, not a semantic tone: neutral (campo) → info (ufficio) →
  // brand (admin), matching the nesting the permission matrix enforces.
  const tone =
    role === "admin"
      ? TONE_CHIP.brand
      : role === "operatore_ufficio"
        ? TONE_CHIP.info
        : TONE_CHIP.neutral;
  return <Badge className={tone}>{roleLabel(role)}</Badge>;
}

/**
 * "Chi può fare cosa" — the role matrix, rendered from the server's own answer.
 *
 * An admin assigning "Operatore sul campo" to a colleague is making a decision
 * about what that person will and will not be able to do, and until now the
 * only description of that was a three-word label. Every row here comes from
 * `GET /users/roles`, so it cannot drift from what the API enforces.
 *
 * Renders nothing when the fetch failed: the role picker below still works, and
 * an empty explanatory table is worse than none.
 */
function RoleMatrix({ roles }: { roles: RoleDefinition[] }) {
  if (roles.length === 0) return null;

  // The union of every role's grants, in the order the most privileged role
  // lists them — so the columns read from "everyone can" down to "only admin".
  const allCapabilities = Array.from(
    new Set(roles.flatMap((r) => r.capabilities))
  ).sort(
    (a, b) =>
      roles.filter((r) => r.capabilities.includes(b)).length -
      roles.filter((r) => r.capabilities.includes(a)).length
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4" />
          Ruoli e permessi
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-3">
          {roles.map((r) => (
            <div key={r.role} className="rounded-md border p-3">
              <RoleBadge role={r.role} />
              <p className="mt-2 text-sm text-muted-foreground">{r.description}</p>
            </div>
          ))}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[34rem] text-sm">
            <thead>
              <tr className="text-left text-xs text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Permesso</th>
                {roles.map((r) => (
                  <th key={r.role} className="py-2 px-2 text-center font-medium">
                    {r.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {allCapabilities.map((capability) => (
                <tr key={capability} className="border-t">
                  <td className="py-2 pr-4">{CAPABILITY_LABELS[capability] ?? capability}</td>
                  {roles.map((r) => (
                    <td key={r.role} className="px-2 py-2 text-center">
                      {r.capabilities.includes(capability) ? (
                        <Check
                          className="mx-auto h-4 w-4 text-[#0f7a37]"
                          aria-label="consentito"
                        />
                      ) : (
                        <Minus
                          className="mx-auto h-4 w-4 text-muted-foreground/40"
                          aria-label="non consentito"
                        />
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AdminUsersPage() {
  const { apiFetch } = useApi();
  const { data: session, status: sessionStatus } = useSession();
  const { can } = usePermissions();
  // Served by the API so the table below describes the matrix the server
  // enforces, not a copy of it.
  const roles = useRoles();
  const router = useRouter();

  const [users, setUsers] = useState<UserRow[]>([]);
  const [stats, setStats] = useState<StatsRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [addOpen, setAddOpen] = useState(false);
  const [editing, setEditing] = useState<UserRow | null>(null);
  const [resetting, setResetting] = useState<UserRow | null>(null);

  useEffect(() => {
    if (sessionStatus !== "authenticated") return;
    // Capability, not role: the redirect and the API's 403 now answer to the
    // same rule in `lib/permissions` / `core/permissions.py`.
    if (!can(USERS_MANAGE)) {
      router.replace("/dashboard");
    }
  }, [can, session, sessionStatus, router]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [u, s] = await Promise.all([
        apiFetch<UserRow[]>("/api/v1/users"),
        apiFetch<StatsRow[]>("/api/v1/users/stats"),
      ]);
      setUsers(u);
      setStats(s);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Caricamento utenti non riuscito.",
      );
    } finally {
      setLoading(false);
    }
  }, [apiFetch]);

  useEffect(() => {
    load();
  }, [load]);

  // Seats come from the plan. Fail open: no entitlements (or a backend still in
  // shadow mode) means we show nothing and block nothing — the server's 402 is
  // the only real gate (INV-5).
  const { entitlements } = useEntitlementsContext();
  const seats = entitlements?.seats ?? null;
  const seatLimitReached =
    entitlements !== null &&
    entitlements.enforced &&
    seats !== null &&
    users.length >= seats;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex flex-wrap items-baseline gap-3">
            <h1 className="type-h1">Utenti</h1>
            {seats !== null && !loading && (
              <Link
                href="/billing"
                className="rounded-full border border-[#e5edf5] bg-[#f6f9fc] px-2.5 py-0.5 text-[11.5px] font-semibold text-[#273951] transition-colors hover:border-primary/40 hover:text-primary"
                title="Utenti inclusi nel piano"
              >
                <span className="tnum">
                  {users.length} / {formatSeats(seats)}
                </span>{" "}
                utenti
              </Link>
            )}
          </div>
          <p className="text-muted-foreground">
            Gestisci i membri del team e visualizza chi ha creato clienti e
            documenti.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            {loading ? (
              <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="mr-1 h-3.5 w-3.5" />
            )}
            Aggiorna
          </Button>
          {/* `title` on a disabled button never fires (pointer-events: none), so
              the span carries it and the hint below states it in plain text. */}
          <span
            title={
              seatLimitReached
                ? "Hai raggiunto il numero di utenti inclusi nel piano"
                : undefined
            }
          >
            <Button
              size="sm"
              onClick={() => setAddOpen(true)}
              disabled={seatLimitReached}
            >
              <UserPlus className="mr-1 h-3.5 w-3.5" />
              Aggiungi utente
            </Button>
          </span>
        </div>
      </div>

      {seatLimitReached && (
        <Callout tone="warn" dense>
          Hai usato tutti gli utenti inclusi nel piano.{" "}
          <Link href="/billing" className="font-semibold underline underline-offset-2">
            Aggiorna il piano
          </Link>{" "}
          per aggiungerne altri.
        </Callout>
      )}

      {error && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <RoleMatrix roles={roles} />

      <Card>
        <CardHeader>
          <CardTitle>Team</CardTitle>
          <CardDescription>
            Tutti gli utenti della tua organizzazione.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {users.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              {loading ? "Caricamento..." : "Nessun utente."}
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Ruolo</TableHead>
                  <TableHead>Creato il</TableHead>
                  <TableHead className="w-[180px] text-right">Azioni</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">{u.full_name}</TableCell>
                    <TableCell className="text-sm">{u.email}</TableCell>
                    <TableCell>
                      <RoleBadge role={u.role} />
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(u.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setEditing(u)}
                        >
                          Modifica
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setResetting(u)}
                        >
                          <KeyRound className="mr-1 h-3.5 w-3.5" />
                          Password
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Attività per utente</CardTitle>
          <CardDescription>
            Clienti e documenti creati da ciascun utente (dati raccolti dal
            2026-04-19 in poi).
          </CardDescription>
        </CardHeader>
        <CardContent>
          {stats.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              {loading ? "Caricamento..." : "Nessun dato."}
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Utente</TableHead>
                  <TableHead>Ruolo</TableHead>
                  <TableHead className="text-right">Clienti creati</TableHead>
                  <TableHead className="text-right">
                    Documenti generati
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stats.map((row) => (
                  <TableRow key={row.user_id}>
                    <TableCell>
                      <div className="font-medium">{row.full_name}</div>
                      <div className="text-xs text-muted-foreground">
                        {row.email}
                      </div>
                    </TableCell>
                    <TableCell>
                      <RoleBadge role={row.role} />
                    </TableCell>
                    <TableCell className="type-numeral text-right">
                      {row.aziende_count}
                    </TableCell>
                    <TableCell className="type-numeral text-right">
                      {row.documenti_count}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <AddUserDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        onCreated={load}
      />
      <EditUserDialog
        user={editing}
        onOpenChange={(open) => {
          if (!open) setEditing(null);
        }}
        onSaved={load}
      />
      <ResetPasswordDialog
        user={resetting}
        onOpenChange={(open) => {
          if (!open) setResetting(null);
        }}
      />
    </div>
  );
}

function AddUserDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}) {
  const { apiFetch } = useApi();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("operatore_ufficio");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setFullName("");
      setEmail("");
      setPassword("");
      setRole("operatore_ufficio");
      setErr(null);
    }
  }, [open]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setErr(null);
    try {
      await apiFetch("/api/v1/users", {
        method: "POST",
        body: JSON.stringify({
          full_name: fullName,
          email,
          password,
          role,
        }),
      });
      onCreated();
      onOpenChange(false);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Errore");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Aggiungi utente</DialogTitle>
          <DialogDescription>
            Crea un nuovo utente nella tua organizzazione. La password iniziale
            andrà comunicata manualmente.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
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
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">
              Password iniziale (min. 8 caratteri)
            </Label>
            <Input
              id="password"
              type="text"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="role">Ruolo</Label>
            <Select
              id="role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              {ROLE_OPTIONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </Select>
          </div>
          <FormError>{err}</FormError>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Annulla
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting && (
                <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
              )}
              Crea utente
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function EditUserDialog({
  user,
  onOpenChange,
  onSaved,
}: {
  user: UserRow | null;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}) {
  const { apiFetch } = useApi();
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("operatore_ufficio");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name);
      setRole(user.role);
      setErr(null);
    }
  }, [user]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!user) return;
    setSubmitting(true);
    setErr(null);
    try {
      await apiFetch(`/api/v1/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ full_name: fullName, role }),
      });
      onSaved();
      onOpenChange(false);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Errore");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={!!user} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Modifica utente</DialogTitle>
          <DialogDescription>{user?.email}</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="edit_full_name">Nome completo</Label>
            <Input
              id="edit_full_name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit_role">Ruolo</Label>
            <Select
              id="edit_role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              {ROLE_OPTIONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </Select>
          </div>
          <FormError>{err}</FormError>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Annulla
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting && (
                <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
              )}
              Salva
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ResetPasswordDialog({
  user,
  onOpenChange,
}: {
  user: UserRow | null;
  onOpenChange: (open: boolean) => void;
}) {
  const { apiFetch } = useApi();
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (user) {
      setPassword("");
      setErr(null);
      setDone(false);
    }
  }, [user]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!user) return;
    setSubmitting(true);
    setErr(null);
    try {
      await apiFetch(`/api/v1/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ password }),
      });
      setDone(true);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Errore");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={!!user} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reimposta password</DialogTitle>
          <DialogDescription>
            Imposta una nuova password per {user?.full_name}. Comunicala
            manualmente all&apos;utente.
          </DialogDescription>
        </DialogHeader>
        {done ? (
          <div className="space-y-4">
            <p className="rounded-md border border-[rgba(16,140,61,0.26)] bg-[rgba(16,140,61,0.05)] px-3 py-2 text-sm text-[#0f7a37]">
              Password aggiornata. Consegnala all&apos;utente.
            </p>
            <DialogFooter>
              <Button onClick={() => onOpenChange(false)}>Chiudi</Button>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="new_password">
                Nuova password (min. 8 caratteri)
              </Label>
              <Input
                id="new_password"
                type="text"
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <FormError>{err}</FormError>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Annulla
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting && (
                  <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                )}
                Reimposta
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
