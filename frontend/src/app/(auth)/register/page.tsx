"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const formData = new FormData(e.currentTarget);
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

    try {
      const res = await fetch(`${API_URL}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: formData.get("full_name"),
          email: formData.get("email"),
          password,
          organization_name: formData.get("organization_name") || null,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Errore: ${res.status}`);
      }

      router.push("/login?registered=1");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore nella registrazione");
    } finally {
      setLoading(false);
    }
  }

  const labelClass = "text-[13px] font-medium text-[#273951]";

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f6f9fc] p-4">
      <div className="w-full max-w-[440px] rounded-lg border border-[#e5edf5] bg-white p-8 shadow-stripe-elevated">
        <div className="mb-7 flex flex-col items-center text-center">
          <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-md bg-primary/10 ring-1 ring-primary/20">
            <Shield className="h-5 w-5 text-primary" strokeWidth={1.75} />
          </div>
          <h1 className="font-heading text-[26px] font-light leading-[1.12] tracking-[-0.015em] text-[#061b31]">
            Crea Account
          </h1>
          <p className="type-body mt-2">
            Registrati per accedere alla piattaforma
          </p>
        </div>

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
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="organization_name" className={labelClass}>
              Organizzazione
            </Label>
            <Input
              id="organization_name"
              name="organization_name"
              type="text"
              placeholder="Es. N2O SRL"
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="mt-2 w-full" disabled={loading}>
            {loading ? "Registrazione in corso..." : "Registrati"}
          </Button>
        </form>

        <p className="mt-5 text-center text-[13px] text-[#64748d]">
          Hai gi&agrave; un account?{" "}
          <Link
            href="/login"
            className="font-medium text-primary hover:underline"
          >
            Accedi
          </Link>
        </p>
      </div>
    </div>
  );
}
