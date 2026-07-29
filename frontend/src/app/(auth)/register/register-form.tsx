"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { signIn } from "next-auth/react";
import Link from "next/link";
import { FIELD, FIELD_LABEL, SECONDARY, SUBMIT } from "@/components/auth/auth-ui";
import { FormError } from "@/components/ui/form-error";
import { throwApiError } from "@/lib/api-errors";
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

/**
 * `piano` arrives as a prop, read from the query string on the server, rather
 * than through `useSearchParams()`. That hook forces the whole subtree to be
 * client-only, and the Suspense boundary it needs was rendering `null` — so
 * /register, the page every /prezzi call to action lands on, shipped its HTML
 * with no form in it at all and stayed blank until the JS bundle arrived.
 */
export function RegisterForm({ piano }: { piano: string | null }) {
  const router = useRouter();
  // Only a hint: it is re-validated server-side before any charge, and an
  // unknown code just falls through to the full plan list on /billing.
  const planName = piano ? PLAN_NAMES[piano] : undefined;
  const direct = isDirectPlan(piano);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [reveal, setReveal] = useState(false);
  const [caps, setCaps] = useState(false);
  /** Which field the message is about, so it can be marked and focused. */
  const [badField, setBadField] = useState<
    "password" | "confirm_password" | "organization_name" | null
  >(null);
  const formRef = useRef<HTMLFormElement>(null);

  function fail(message: string, field: typeof badField = null) {
    setError(message);
    setBadField(field);
    setLoading(false);
    // Send the caret where the problem is; an error the customer has to go
    // hunting for is barely better than no error.
    if (field) {
      const el = formRef.current?.elements.namedItem(field);
      if (el instanceof HTMLInputElement) el.focus();
    }
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setBadField(null);
    setLoading(true);

    const formData = new FormData(e.currentTarget);
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;
    const confirmPassword = formData.get("confirm_password") as string;

    if (password !== confirmPassword) {
      fail("Le due password non coincidono.", "confirm_password");
      return;
    }

    if (password.length < 8) {
      fail("La password deve essere di almeno 8 caratteri.", "password");
      return;
    }

    if (direct && !String(formData.get("organization_name") ?? "").trim()) {
      fail(
        "Indica la ragione sociale dell'impresa che stai registrando.",
        "organization_name"
      );
      return;
    }

    // The backend refuses a direct signup without this anyway (INV-5); checking
    // here just avoids a round-trip to be told so.
    if (direct && formData.get("consenso_datore_lavoro") !== "on") {
      fail(
        "Per attivare un piano per aziende devi confermare la dichiarazione del datore di lavoro."
      );
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

      // `throwApiError` already translates FastAPI's shapes — including the
      // 422 list-of-objects that used to reach the customer as the literal
      // string "[object Object]".
      if (!res.ok) await throwApiError(res);

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
      fail(
        err instanceof Error
          ? err.message
          : "Non è stato possibile completare la registrazione. Riprova."
      );
    }
  }

  return (
    <div data-testid="register-card">
      <h1 className="font-heading text-[38px] leading-[1.05] font-light tracking-[-0.035em] text-[#061b31]">
        Crea un account
      </h1>
      <p className="mt-3 text-[15px] leading-[1.55] font-light text-[#64748d]">
        {planName
          ? `Un ultimo passaggio prima di attivare il piano ${planName}`
          : "Registrati per accedere alla piattaforma"}
      </p>

      {planName && (
        <div className="mt-6 flex items-start gap-2.5 rounded-sm border border-[#cfe0f2] bg-primary/4 px-3.5 py-3">
          <p className="text-[13px] leading-[1.45] text-[#273951]">
            Piano selezionato:{" "}
            <strong className="font-semibold text-[#061b31]">{planName}</strong>.
            Dopo la registrazione ti portiamo su PayPal per approvare
            l&apos;abbonamento annuale.
          </p>
        </div>
      )}

      <form
        ref={formRef}
        onSubmit={handleSubmit}
        className="mt-[34px] flex flex-col gap-[18px]"
      >
        <div className="flex flex-col gap-[7px]">
          <label htmlFor="full_name" className={FIELD_LABEL}>
            Nome completo *
          </label>
          <input
            id="full_name"
            name="full_name"
            type="text"
            required
            autoComplete="name"
            placeholder="Mario Rossi"
            className={FIELD}
          />
        </div>

        <div className="flex flex-col gap-[7px]">
          <label htmlFor="email" className={FIELD_LABEL}>
            Email *
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            placeholder="nome@esempio.it"
            className={FIELD}
          />
        </div>

        {/* Two-up from 480px rather than at `sm`: the panel is 440px wide and
            these two fields are the shortest on the form, so pairing them is
            what keeps the whole signup above the fold on a laptop. */}
        <div className="grid gap-[18px] min-[480px]:grid-cols-2">
          <div className="flex flex-col gap-[7px]">
            <div className="flex items-baseline justify-between gap-3">
              <label htmlFor="password" className={FIELD_LABEL}>
                Password *
              </label>
              {/* This form asks for the password twice; being able to read it
                  back is what stops the mismatch error from happening. */}
              <button
                type="button"
                onClick={() => setReveal((r) => !r)}
                className="text-[12px] font-medium text-primary transition-colors hover:text-[#1b5594]"
              >
                {reveal ? "Nascondi" : "Mostra"}
              </button>
            </div>
            <input
              id="password"
              name="password"
              type={reveal ? "text" : "password"}
              required
              autoComplete="new-password"
              placeholder="Minimo 8 caratteri"
              aria-invalid={badField === "password" || undefined}
              onKeyUp={(e) => {
                const on = e.getModifierState?.("CapsLock") ?? false;
                if (on !== caps) setCaps(on);
              }}
              className={FIELD}
            />
          </div>
          <div className="flex flex-col gap-[7px]">
            <label htmlFor="confirm_password" className={FIELD_LABEL}>
              Conferma *
            </label>
            <input
              id="confirm_password"
              name="confirm_password"
              type={reveal ? "text" : "password"}
              required
              autoComplete="new-password"
              aria-invalid={badField === "confirm_password" || undefined}
              onKeyUp={(e) => {
                const on = e.getModifierState?.("CapsLock") ?? false;
                if (on !== caps) setCaps(on);
              }}
              className={FIELD}
            />
          </div>
        </div>
        {caps && (
          <p className="-mt-2 text-[12px] text-[#9b6829]">
            Blocco maiuscole attivo.
          </p>
        )}

        <div className="flex flex-col gap-[7px]">
          <label htmlFor="organization_name" className={FIELD_LABEL}>
            {direct ? "Ragione sociale dell'impresa *" : "Studio o organizzazione"}
          </label>
          <input
            id="organization_name"
            name="organization_name"
            type="text"
            autoComplete="organization"
            // Optional for a consultant — the studio can be named later — but a
            // direct signup *is* the company, and leaving it blank named the
            // organization "Marco Bianchi's Organization" (P3-3).
            required={direct}
            aria-invalid={badField === "organization_name" || undefined}
            placeholder={direct ? "Es. Officina Meccanica Bianchi SRL" : "Es. N2O SRL"}
            className={FIELD}
          />
        </div>

        {direct && (
          <div className="rounded-sm border border-[#e5edf5] bg-[#f6f9fc] p-3.5">
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

        <FormError className="rounded-sm">{error}</FormError>

        <button type="submit" className={SUBMIT} disabled={loading}>
          {loading && (
            <span className="h-[15px] w-[15px] animate-spin rounded-full border-[1.6px] border-white/32 border-t-white" />
          )}
          <span>{loading ? "Registrazione in corso…" : "Registrati"}</span>
        </button>
      </form>

      {/* Same closing structure as /login — divider, the route out for the
          other account state, then the fine print. */}
      <div className="mt-[26px] flex items-center gap-3.5">
        <span className="h-px flex-1 bg-[#e5edf5]" />
        <span className="text-[11px] font-medium tracking-[0.13em] text-[#8a96ab] uppercase">
          oppure
        </span>
        <span className="h-px flex-1 bg-[#e5edf5]" />
      </div>

      <Link
        href={piano ? `/login?piano=${encodeURIComponent(piano)}` : "/login"}
        className={`${SECONDARY} mt-[18px]`}
      >
        Ho gi&agrave; un account · Accedi
      </Link>

      <p className="mt-7 text-[12.5px] leading-[1.6] text-[#8a96ab]">
        {direct ? (
          <>
            Sei invece un consulente o uno studio che segue pi&ugrave; aziende
            clienti?{" "}
            <Link
              href="/prezzi#consulenti"
              className="font-medium text-primary hover:underline"
            >
              Guarda i piani per consulenti
            </Link>
            .
          </>
        ) : (
          <>
            Sei un&apos;azienda che deve documentare la propria sicurezza?{" "}
            <Link
              href="/prezzi#aziende"
              className="font-medium text-primary hover:underline"
            >
              Guarda i piani per aziende
            </Link>
            .
          </>
        )}
      </p>
    </div>
  );
}

