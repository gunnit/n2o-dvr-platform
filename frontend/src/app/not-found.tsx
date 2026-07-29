import Link from "next/link";
import { SiteFooter } from "@/components/landing/site-footer";
import { SiteNav } from "@/components/landing/site-nav";

/**
 * Reached from both sides of the login wall, so it keeps two ways out and
 * sits inside the public site chrome: a visitor who mistypes a public URL
 * used to land on a lone card with no header, no footer and no way back into
 * the site except the two buttons below.
 */
export default function NotFound() {
  return (
    <div className="flex min-h-svh flex-col bg-white">
      <SiteNav variant="solid" />

      <main className="flex flex-1 items-center bg-[#f6f9fc]">
        {/* pt/pb stated separately rather than `py-* pt-*`: two utilities for
            one property are resolved by Tailwind's output order, not by the
            order written here. The 68px is the fixed nav this sits under. */}
        <div className="mx-auto w-full max-w-[1160px] px-6 pt-[calc(68px+clamp(3.5rem,9vw,6rem))] pb-[clamp(4.5rem,12vw,8rem)] sm:px-7">
          <p className="tnum text-[12px] font-medium tracking-[0.16em] text-[#003d74] uppercase">
            Errore 404
          </p>
          <h1 className="mt-[18px] max-w-[18ch] font-heading text-[clamp(1.9rem,4vw,2.9rem)] leading-[1.08] font-light tracking-[-0.03em] text-balance text-[#061b31]">
            Questa pagina non esiste.
          </h1>
          <p className="mt-[18px] max-w-[52ch] text-[16px] leading-[1.62] text-[#64748d]">
            L&apos;indirizzo richiesto non esiste o &egrave; stato spostato. Se
            ci sei arrivato da un link della piattaforma, scrivici e lo
            sistemiamo.
          </p>

          <div className="mt-9 flex flex-wrap gap-3.5">
            <Link
              href="/"
              className="inline-flex h-[46px] items-center rounded-[4px] bg-[#003d74] px-[26px] text-[15px] font-medium text-white shadow-stripe-ambient transition-colors hover:bg-[#1b5594]"
            >
              Torna al sito
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex h-[46px] items-center rounded-[4px] border border-[#e5edf5] bg-white px-[26px] text-[15px] font-medium text-[#003d74] transition-colors hover:border-[#003d74] hover:bg-[#f6f9fc]"
            >
              Vai alla piattaforma
            </Link>
          </div>
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
