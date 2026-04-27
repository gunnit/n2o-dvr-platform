"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { signIn } from "next-auth/react";
import Link from "next/link";
import { toast } from "sonner";
import { CheckCircle2, Shield } from "lucide-react";
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
    <div
      data-testid="login-card"
      className="w-full max-w-[420px] rounded-lg border border-[#e5edf5] bg-white p-8 shadow-stripe-elevated"
    >
      <div className="mb-7 flex flex-col items-center text-center">
        <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-md bg-primary/10 ring-1 ring-primary/20">
          <Shield className="h-5 w-5 text-primary" strokeWidth={1.75} />
        </div>
        <h1 className="font-heading text-[26px] font-light leading-[1.12] tracking-[-0.015em] text-[#061b31]">
          N2O DVR Platform
        </h1>
        <p className="type-body mt-2">
          Accedi al sistema di gestione documentale
        </p>
      </div>

      {justRegistered && (
        <div className="mb-5 flex items-start gap-2 rounded-md border border-[rgba(21,190,83,0.4)] bg-[rgba(21,190,83,0.12)] p-3 text-sm text-[#108c3d]">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={2} />
          <p>Registrazione completata. Accedi con le tue credenziali per iniziare.</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <Label
            htmlFor="email"
            className="text-[13px] font-medium text-[#273951]"
          >
            Email
          </Label>
          <Input
            id="email"
            name="email"
            type="email"
            required
            placeholder="nome@esempio.it"
            className="h-10 rounded-md border-[#e5edf5] bg-white text-[#061b31] placeholder:text-[#64748d] focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
          />
        </div>
        <div className="space-y-1.5">
          <Label
            htmlFor="password"
            className="text-[13px] font-medium text-[#273951]"
          >
            Password
          </Label>
          <Input
            id="password"
            name="password"
            type="password"
            required
            className="h-10 rounded-md border-[#e5edf5] bg-white text-[#061b31] focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
          />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button
          type="submit"
          disabled={loading}
          className="mt-2 h-10 w-full rounded-md bg-primary text-sm font-medium text-white hover:bg-[#1b5594] shadow-stripe-ambient"
        >
          {loading ? "Accesso in corso..." : "Accedi"}
        </Button>
        <div className="flex justify-center pt-1">
          <button
            type="button"
            onClick={() =>
              toast(
                "La funzione sarà disponibile a breve. Contatta support@dvr-sicurezza.it",
              )
            }
            className="text-[13px] font-medium text-primary hover:underline"
          >
            Password dimenticata?
          </button>
        </div>
      </form>
      <p className="mt-5 text-center text-[13px] text-[#64748d]">
        Non hai un account?{" "}
        <Link
          href="/register"
          className="font-medium text-primary hover:underline"
        >
          Registrati
        </Link>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f6f9fc] p-4">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
