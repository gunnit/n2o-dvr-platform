import type { ReactNode } from "react";
import Link from "next/link";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden">
      <div
        aria-hidden
        className="absolute inset-0 -z-30 bg-[#061b31] bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: "url('/auth/login-bg.jpg')" }}
      />
      <div
        aria-hidden
        className="absolute inset-0 -z-20"
        style={{
          background:
            "linear-gradient(180deg, rgba(6,27,49,0.32) 0%, rgba(6,27,49,0.55) 55%, rgba(6,27,49,0.82) 100%)",
        }}
      />
      <div
        aria-hidden
        className="absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(ellipse 65% 55% at 50% 48%, rgba(165,200,255,0.10) 0%, rgba(6,27,49,0) 70%)",
        }}
      />

      <header className="relative z-10 flex items-center justify-between px-6 pt-7 sm:px-10">
        <Link
          href="/"
          className="font-heading text-[15px] font-light tracking-[0.18em] text-white/85 uppercase transition-colors hover:text-white"
        >
          N2O <span className="text-white/55">·</span> DVR
        </Link>
        <span className="hidden text-[12px] font-medium tracking-[0.14em] text-white/55 uppercase sm:inline">
          Sicurezza sul Lavoro
        </span>
      </header>

      <main className="relative z-10 flex flex-1 items-center justify-center px-4 py-12">
        {children}
      </main>

      <footer className="relative z-10 px-6 pb-6 text-center text-[12px] text-white/55 sm:px-10">
        <span className="tracking-wide">
          {`© ${new Date().getFullYear()} N2O SRL · Conforme D.Lgs. 81/2008`}
        </span>
      </footer>
    </div>
  );
}
