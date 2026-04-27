import Link from "next/link";
import { Shield } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f6f9fc] p-4">
      <div className="w-full max-w-[420px] rounded-lg border border-[#e5edf5] bg-white p-8 text-center shadow-stripe-elevated">
        <div className="mb-7 flex flex-col items-center">
          <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-md bg-primary/10 ring-1 ring-primary/20">
            <Shield className="h-5 w-5 text-primary" strokeWidth={1.75} />
          </div>
          <p className="type-eyebrow mb-2 text-[#64748d]">404</p>
          <h1 className="font-heading text-[26px] font-light leading-[1.12] tracking-[-0.015em] text-[#061b31]">
            Pagina non trovata
          </h1>
          <p className="type-body mt-2">
            L&apos;indirizzo richiesto non esiste o &egrave; stato spostato.
          </p>
        </div>
        <Link href="/dashboard">
          <Button className="h-10 w-full rounded-md bg-primary text-sm font-medium text-white hover:bg-[#1b5594] shadow-stripe-ambient">
            Torna alla dashboard
          </Button>
        </Link>
      </div>
    </div>
  );
}
