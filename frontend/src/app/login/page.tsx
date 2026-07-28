"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { signIn } from "next-auth/react";
import Link from "next/link";
import { LoginBackdrop } from "@/components/auth/login-backdrop";

/** Reassurance labels cycled while the credentials request is in flight. */
const PENDING_LABELS = ["Verifica credenziali…", "Quasi pronto…"];

const FIELD =
  "h-[46px] rounded-sm border border-[#e5edf5] bg-white px-3.5 text-[15px] text-[#061b31] outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-[#8a96ab] focus:border-primary focus:shadow-[0_0_0_3px_rgba(0,61,116,0.13)]";

const FIELD_LABEL =
  "text-[11.5px] font-medium tracking-[0.09em] text-[#273951] uppercase";

// The lifted hover shadow is spelled out rather than reusing .shadow-stripe-deep:
// that is a plain class in globals.css, not a Tailwind utility, so hover:/
// not-disabled: variants cannot be stacked onto it. The `shadow:` type hint is
// required — without it Tailwind reads a value starting with rgba() as a shadow
// *colour* and emits --tw-shadow-color instead of box-shadow.
const SUBMIT =
  "shadow-stripe-ambient mt-1.5 flex h-[46px] items-center justify-center gap-2.5 rounded-sm bg-primary text-[15px] font-medium tracking-[0.01em] text-white transition-[background-color,transform,box-shadow] duration-150 hover:not-disabled:-translate-y-px hover:not-disabled:bg-[#1b5594] hover:not-disabled:shadow-[shadow:rgba(50,50,93,0.25)_0px_10px_20px_-12px,rgba(0,0,0,0.1)_0px_6px_12px_-8px] disabled:opacity-90";

function InfoIcon({ className }: { className?: string }) {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden className={className}>
      <circle cx="7" cy="7" r="6" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <path
        d="M7 6.4v3.4M7 4.1v.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const justRegistered = searchParams.get("registered") === "1";
  // Set when the visitor reached login from the public price list. Sends them to
  // checkout with the plan preselected instead of the dashboard.
  const piano = searchParams.get("piano");

  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reveal, setReveal] = useState(false);
  const [caps, setCaps] = useState(false);
  // "idle" -> "loading" -> "success" (held while the router navigates away).
  const [phase, setPhase] = useState<"idle" | "loading" | "success">("idle");
  const [step, setStep] = useState(0);

  const stepTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => clearTimeout(stepTimer.current ?? undefined), []);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setPhase("loading");
    setStep(0);
    // Second label only appears if the request is genuinely still pending.
    stepTimer.current = setTimeout(() => setStep(1), 1200);

    const formData = new FormData(e.currentTarget);

    const result = await signIn("credentials", {
      email: formData.get("email") as string,
      password: formData.get("password") as string,
      redirect: false,
    });

    clearTimeout(stepTimer.current ?? undefined);

    if (result?.error) {
      setPhase("idle");
      setError("Credenziali non valide. Controlla email e password, oppure reimposta la password.");
      return;
    }

    // Hold the success frame while Next resolves the destination route.
    setPhase("success");
    router.push(piano ? `/billing?piano=${encodeURIComponent(piano)}` : "/dashboard");
  }

  if (phase === "success") {
    return (
      <div className="auth-pop">
        <span className="flex h-13 w-13 items-center justify-center rounded-full border border-[rgba(21,190,83,0.4)] bg-[rgba(21,190,83,0.12)] text-[#108c3d]">
          <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden>
            <path
              className="auth-draw"
              d="M5 12.6 10 17.5 19.2 7"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="30"
            />
          </svg>
        </span>
        <h1 className="font-heading mt-6 text-[34px] leading-[1.08] font-light tracking-[-0.03em] text-[#061b31]">
          Accesso completato
        </h1>
        <p className="mt-3 text-[15px] leading-[1.55] font-light text-[#64748d]">
          Sto aprendo la piattaforma.
        </p>
        <div className="mt-[26px] h-[2px] overflow-hidden rounded-[2px] bg-[#e5edf5]">
          <span className="auth-sweep-slow block h-full w-[34%] rounded-[2px] bg-primary" />
        </div>
      </div>
    );
  }

  const busy = phase === "loading";

  return (
    <div data-testid="login-card">
      <h1 className="font-heading text-[38px] leading-[1.05] font-light tracking-[-0.035em] text-[#061b31]">
        Bentornato
      </h1>
      <p className="mt-3 text-[15px] leading-[1.55] font-light text-[#64748d]">
        Accedi per riprendere la gestione documentale.
      </p>

      <form onSubmit={handleSubmit} className="mt-[34px] flex flex-col gap-[18px]">
        <div className="flex flex-col gap-[7px]">
          <label htmlFor="email" className={FIELD_LABEL}>
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            placeholder="nome@studio.it"
            className={FIELD}
          />
        </div>

        <div className="flex flex-col gap-[7px]">
          <div className="flex items-baseline justify-between gap-3">
            <label htmlFor="password" className={FIELD_LABEL}>
              Password
            </label>
            <button
              type="button"
              onClick={() =>
                setNotice(
                  "Il reset automatico non è ancora attivo. Scrivi a support@dvr-sicurezza.it e reimpostiamo la password.",
                )
              }
              className="text-[12px] font-medium text-primary transition-colors hover:text-[#1b5594]"
            >
              Password dimenticata?
            </button>
          </div>
          <div className="relative flex">
            <input
              id="password"
              name="password"
              type={reveal ? "text" : "password"}
              required
              autoComplete="current-password"
              onKeyUp={(e) => {
                const on = e.getModifierState?.("CapsLock") ?? false;
                if (on !== caps) setCaps(on);
              }}
              className={`${FIELD} flex-1 pr-[78px]`}
            />
            <button
              type="button"
              onClick={() => setReveal((r) => !r)}
              className="absolute top-1/2 right-2 -translate-y-1/2 p-1.5 text-[11.5px] font-medium tracking-[0.06em] text-[#64748d] uppercase transition-colors hover:text-primary"
            >
              {reveal ? "Nascondi" : "Mostra"}
            </button>
          </div>
          {caps && (
            <p className="mt-0.5 text-[12px] text-[#9b6829]">Blocco maiuscole attivo.</p>
          )}
        </div>

        {justRegistered && (
          <div className="flex items-start gap-2.5 rounded-sm border border-[rgba(21,190,83,0.4)] bg-[rgba(21,190,83,0.12)] px-3.5 py-3">
            <span className="mt-px flex text-[#108c3d]">
              <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
                <circle cx="7" cy="7" r="6" fill="none" stroke="currentColor" strokeWidth="1.4" />
                <path
                  d="M4.4 7.2 6.2 9 9.7 5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            <p className="text-[13px] leading-[1.45] text-[#108c3d]">
              Registrazione completata. Accedi con le tue credenziali per iniziare.
            </p>
          </div>
        )}

        {notice && (
          <div className="flex items-start gap-2.5 rounded-sm border border-[#cfe0f2] bg-primary/4 px-3.5 py-3">
            <span className="mt-px flex text-primary">
              <InfoIcon />
            </span>
            <p className="text-[13px] leading-[1.45] text-[#273951]">{notice}</p>
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="auth-shake flex items-start gap-2.5 rounded-sm border border-[rgba(199,42,58,0.28)] bg-[rgba(199,42,58,0.05)] px-3.5 py-3"
          >
            <span className="mt-px flex text-[#c72a3a]">
              <InfoIcon />
            </span>
            <p className="text-[13px] leading-[1.45] text-[#c72a3a]">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={busy}
          className={SUBMIT}
        >
          {busy && (
            <span className="h-[15px] w-[15px] animate-spin rounded-full border-[1.6px] border-white/32 border-t-white" />
          )}
          <span>{busy ? PENDING_LABELS[step] : "Accedi"}</span>
        </button>
      </form>

      <div className="mt-[26px] flex items-center gap-3.5">
        <span className="h-px flex-1 bg-[#e5edf5]" />
        <span className="text-[11px] font-medium tracking-[0.13em] text-[#8a96ab] uppercase">
          oppure
        </span>
        <span className="h-px flex-1 bg-[#e5edf5]" />
      </div>

      <Link
        href={piano ? `/register?piano=${encodeURIComponent(piano)}` : "/prezzi"}
        className="mt-[18px] flex h-[46px] items-center justify-center gap-2 rounded-sm border border-[#cfe0f2] text-[14.5px] font-medium text-primary transition-[background-color,border-color] duration-150 hover:border-[#a5c8ff] hover:bg-primary/4"
      >
        {piano ? "Crea un account" : "Crea un account · scegli un piano"}
      </Link>

      <p className="mt-7 text-[12.5px] leading-[1.6] text-[#8a96ab]">
        Problemi di accesso? Scrivi a{" "}
        <a
          href="mailto:support@dvr-sicurezza.it"
          className="font-medium text-primary hover:underline"
        >
          support@dvr-sicurezza.it
        </a>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="grid min-h-svh grid-cols-[minmax(0,1.12fr)_minmax(0,0.88fr)] bg-[#061b31] max-[900px]:min-h-0 max-[900px]:grid-cols-[minmax(0,1fr)] max-[900px]:grid-rows-[auto_auto]">
      <LoginBackdrop />

      <div className="relative flex flex-col items-center justify-center bg-white px-13 py-14 shadow-[-30px_0_70px_-40px_rgba(6,27,49,0.55)] max-[1080px]:px-[34px] max-[1080px]:py-12 max-[900px]:border-t max-[900px]:border-[rgba(6,27,49,0.1)] max-[900px]:px-[26px] max-[900px]:pt-13 max-[900px]:pb-11 max-[900px]:shadow-none">
        <div className="w-full max-w-[392px]">
          <Suspense fallback={null}>
            <LoginForm />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
