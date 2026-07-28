import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t border-[#e5edf5] bg-white">
      <div className="mx-auto flex w-full max-w-[1160px] flex-wrap items-center justify-between gap-7 px-6 py-11 sm:px-7">
        <div>
          <p className="font-heading text-[14px] font-light tracking-[0.2em] text-[#061b31] uppercase">
            N2O <span className="text-[#64748d]">·</span> DVR
          </p>
          <p className="mt-2 text-[13px] text-[#64748d]">
            © {new Date().getFullYear()} N2O SRL · Conforme D.Lgs. 81/2008 ·
            Powered by Niuexa
          </p>
        </div>
        <nav
          aria-label="Collegamenti"
          className="flex flex-wrap items-center gap-6"
        >
          <Link
            href="/prezzi"
            className="text-[14px] font-medium text-[#003d74] hover:underline"
          >
            Prezzi
          </Link>
          <Link
            href="/login"
            className="text-[14px] font-medium text-[#003d74] hover:underline"
          >
            Accedi
          </Link>
          <Link
            href="/register"
            className="text-[14px] font-medium text-[#003d74] hover:underline"
          >
            Registrati
          </Link>
          <a
            href="mailto:support@dvr-sicurezza.it"
            className="text-[14px] text-[#64748d] hover:text-[#061b31]"
          >
            support@dvr-sicurezza.it
          </a>
        </nav>
      </div>
    </footer>
  );
}
