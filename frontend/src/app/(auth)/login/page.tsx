"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { signIn } from "next-auth/react";
import Link from "next/link";
import { toast } from "sonner";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const justRegistered = searchParams.get("registered") === "1";
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const formData = new FormData(e.currentTarget);

    const result = await signIn("credentials", {
      email: formData.get("email") as string,
      password: formData.get("password") as string,
      redirect: false,
    });

    setLoading(false);

    if (result?.error) {
      setError("Credenziali non valide");
    } else {
      router.push("/dashboard");
    }
  }

  return (
    <div className="w-full max-w-[440px]">
      <div className="mb-8 text-center">
        <h1 className="font-heading text-[34px] font-light leading-[1.05] tracking-[-0.02em] text-white sm:text-[40px]">
          Bentornato
        </h1>
        <p className="mt-3 text-[14px] font-light tracking-wide text-white/70">
          Accedi alla piattaforma di gestione documentale
        </p>
      </div>

      <div
        data-testid="login-card"
        className="relative rounded-[10px] border border-white/60 bg-white/97 p-8 shadow-stripe-elevated backdrop-blur-md sm:p-9"
      >
        {justRegistered && (
          <div className="mb-6 flex items-start gap-2 rounded-md border border-[rgba(21,190,83,0.4)] bg-[rgba(21,190,83,0.12)] p-3 text-sm text-[#108c3d]">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={2} />
            <p>Registrazione completata. Accedi con le tue credenziali per iniziare.</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1.5">
            <Label htmlFor="email" className="text-[13px] font-medium text-[#273951]">
              Email
            </Label>
            <Input
              id="email"
              name="email"
              type="email"
              required
              placeholder="nome@esempio.it"
              autoComplete="email"
              className="h-11 rounded-md border-[#e5edf5] bg-white text-[15px] text-[#061b31] placeholder:text-[#8a96ab] focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
            />
          </div>
          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between">
              <Label htmlFor="password" className="text-[13px] font-medium text-[#273951]">
                Password
              </Label>
              <button
                type="button"
                onClick={() =>
                  toast(
                    "La funzione sarà disponibile a breve. Contatta support@dvr-sicurezza.it",
                  )
                }
                className="text-[12px] font-medium text-primary hover:underline"
              >
                Password dimenticata?
              </button>
            </div>
            <Input
              id="password"
              name="password"
              type="password"
              required
              autoComplete="current-password"
              className="h-11 rounded-md border-[#e5edf5] bg-white text-[15px] text-[#061b31] focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
            />
          </div>
          {error && (
            <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-[13px] text-destructive">
              {error}
            </p>
          )}
          <Button
            type="submit"
            disabled={loading}
            className="h-11 w-full rounded-md bg-primary text-[15px] font-medium tracking-wide text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594]"
          >
            {loading ? "Accesso in corso…" : "Accedi"}
          </Button>
        </form>

        <p className="mt-6 text-center text-[13px] text-[#64748d]">
          Non hai un account?{" "}
          <Link href="/register" className="font-medium text-primary hover:underline">
            Registrati
          </Link>
        </p>
      </div>

      <p className="mt-6 text-center text-[11px] tracking-[0.16em] text-white/45 uppercase">
        Powered by Niuexa &middot; AI Document Automation
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
