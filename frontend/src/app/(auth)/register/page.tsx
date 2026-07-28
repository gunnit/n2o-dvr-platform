"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { signIn } from "next-auth/react";
import Link from "next/link";
import { Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DDL_CONSENT_TEXT, DDL_CONSENT_VERSION } from "@/lib/consent";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Display names for the `?piano=` codes the public price list can send. */
const PLAN_NAMES: Record<string, string> = {
  A_SOLO: "Solo",
  A_STUDIO: "Studio",
  A_NETWORK: "Network",
  A_ENTERPRISE: "Enterprise",
  B_BASE: "Base",
  B_PLUS: "Plus",
  B_MULTISEDE: "Multi-sede",
};

/**
 * Which signup route a plan belongs to. The account type is a property of the
 * endpoint, not a form field — it decides which price list the tenant may ever
 * buy from, so `/register` cannot be talked into creating a direct tenant and
 * vice versa. `?piano=` is only a hint; a visitor who arrives with no plan gets
 * the consultant form, which is the older and larger channel.
 */
function isDirectPlan(planCode: string | null): boolean {
  return planCode?.startsWith("B_") ?? false;
}

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // The plan the visitor picked on /prezzi. Only a hint: it is re-validated
  // server-side before any charge, and an unknown code just falls through to
  // the full plan list on /billing.
  const piano = searchParams.get("piano");
  const planName = piano ? PLAN_NAMES[piano] : undefined;
  const direct = isDirectPlan(piano);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const formData = new FormData(e.currentTarget);
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;
    const confirmPassword = formData.get("confirm_password") as string;

    if (password !== confirmPassword) {
      setError("Le password non coincidono");
      setLoading(false);
      return;
    }

    if (password.length < 8) {
      setError("La password deve essere di almeno 8 caratteri");
      setLoading(false);
      return;
    }

    // The backend refuses a direct signup without this anyway (INV-5); checking
    // here just avoids a round-trip to be told so.
    if (direct && formData.get("consenso_datore_lavoro") !== "on") {
      setError(
        "Per attivare un piano per aziende devi confermare la dichiarazione del datore di lavoro."
      );
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(
        `${API_URL}/api/v1/auth/${direct ? "register-direct" : "register"}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            full_name: formData.get("full_name"),
            email,
            password,
            organization_name: formData.get("organization_name") || null,
            ...(direct && {
              consenso_datore_lavoro: true,
              consenso_versione: DDL_CONSENT_VERSION,
            }),
          }),
        }
      );

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Errore: ${res.status}`);
      }

      // Sign in with the credentials just registered, so the customer goes
      // straight to checkout instead of retyping them at /login. If that fails
      // the account still exists, so send them to the login form rather than
      // stranding them on an error.
      const signedIn = await signIn("credentials", {
        email,
        password,
        redirect: false,
      });
      if (signedIn?.error) {
        router.push("/login?registered=1");
        return;
      }

      const target = piano
        ? `/billing?piano=${encodeURIComponent(piano)}`
        : "/billing";
      router.push(target);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore nella registrazione");
      setLoading(false);
    }
  }

  const labelClass = "text-[13px] font-medium text-[#273951]";

  return (
    <div className="w-full max-w-[440px] rounded-[10px] border border-white/60 bg-white/97 p-8 shadow-stripe-elevated backdrop-blur-md sm:p-9">
      <div className="mb-7 flex flex-col items-center text-center">
        <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-md bg-primary/10 ring-1 ring-primary/20">
          <Shield className="h-5 w-5 text-primary" strokeWidth={1.75} />
        </div>
        <h1 className="font-heading text-[26px] leading-[1.12] font-light tracking-[-0.015em] text-[#061b31]">
          Crea Account
        </h1>
        <p className="type-body mt-2">
          {planName
            ? `Un ultimo passaggio prima di attivare il piano ${planName}`
            : "Registrati per accedere alla piattaforma"}
        </p>
      </div>

      {planName && (
        <div className="mb-6 rounded-md border border-primary/25 bg-primary/5 px-3 py-2.5 text-[13px] text-[#273951]">
          Piano selezionato: <strong>{planName}</strong>. Dopo la registrazione
          ti portiamo su PayPal per approvare l&apos;abbonamento annuale.
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="full_name" className={labelClass}>
            Nome Completo *
          </Label>
          <Input
            id="full_name"
            name="full_name"
            type="text"
            required
            autoComplete="name"
            placeholder="Mario Rossi"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email" className={labelClass}>
            Email *
          </Label>
          <Input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            placeholder="nome@esempio.it"
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="password" className={labelClass}>
              Password *
            </Label>
            <Input
              id="password"
              name="password"
              type="password"
              required
              autoComplete="new-password"
              placeholder="Minimo 8 caratteri"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm_password" className={labelClass}>
              Conferma *
            </Label>
            <Input
              id="confirm_password"
              name="confirm_password"
              type="password"
              required
              autoComplete="new-password"
            />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="organization_name" className={labelClass}>
            {direct ? "Ragione sociale dell'impresa" : "Studio o organizzazione"}
          </Label>
          <Input
            id="organization_name"
            name="organization_name"
            type="text"
            autoComplete="organization"
            placeholder="Es. N2O SRL"
          />
        </div>
        {direct && (
          <div className="rounded-md border border-[#e5edf5] bg-[#f6f9fc] p-3.5">
            <label
              htmlFor="consenso_datore_lavoro"
              className="flex cursor-pointer gap-2.5 text-[12.5px] leading-[1.55] text-[#273951]"
            >
              <input
                id="consenso_datore_lavoro"
                name="consenso_datore_lavoro"
                type="checkbox"
                required
                className="mt-0.5 h-3.5 w-3.5 shrink-0 cursor-pointer accent-[#003d74]"
              />
              <span>{DDL_CONSENT_TEXT}</span>
            </label>
          </div>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="mt-2 w-full" disabled={loading}>
          {loading ? "Registrazione in corso..." : "Registrati"}
        </Button>
      </form>

      <p className="mt-5 text-center text-[13px] text-[#64748d]">
        Hai gi&agrave; un account?{" "}
        <Link
          href={piano ? `/login?piano=${encodeURIComponent(piano)}` : "/login"}
          className="font-medium text-primary hover:underline"
        >
          Accedi
        </Link>
      </p>

      <p className="mt-4 border-t border-[#e5edf5] pt-4 text-center text-[12.5px] leading-[1.55] text-[#64748d]">
        {direct ? (
          <>
            Sei invece un consulente o uno studio che segue pi&ugrave; aziende
            clienti?{" "}
            <Link href="/prezzi#consulenti" className="font-medium text-primary hover:underline">
              Guarda i piani per consulenti
            </Link>
            .
          </>
        ) : (
          <>
            Sei un&apos;azienda che deve documentare la propria sicurezza?{" "}
            <Link href="/prezzi#aziende" className="font-medium text-primary hover:underline">
              Guarda i piani per aziende
            </Link>
            .
          </>
        )}
      </p>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={null}>
      <RegisterForm />
    </Suspense>
  );
}
