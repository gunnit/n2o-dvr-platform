import Link from "next/link";

// `/#id`, not `#id`: the footer also closes /prezzi and the 404 page, and on
// the landing itself `/#id` is still a same-document jump.
const COLUMNS: { label: string; links: { href: string; label: string }[] }[] = [
  {
    label: "Prodotto",
    links: [
      { href: "/#come-funziona", label: "Come funziona" },
      { href: "/#fascicolo", label: "Documenti" },
      { href: "/#metodo", label: "Metodo" },
      { href: "/prezzi", label: "Prezzi" },
    ],
  },
  {
    label: "Accesso",
    links: [
      { href: "/login", label: "Accedi" },
      { href: "/register", label: "Registrati" },
    ],
  },
  {
    label: "Contatti",
    links: [{ href: "mailto:support@dvr-sicurezza.it", label: "support@dvr-sicurezza.it" }],
  },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-[#e5edf5] bg-white">
      <div className="mx-auto w-full max-w-[1160px] px-6 pt-12 pb-8 sm:px-7 sm:pt-16 sm:pb-10">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[minmax(0,1.4fr)_repeat(3,minmax(0,1fr))] lg:gap-12">
          <div>
            <p className="font-heading text-[15px] font-medium tracking-[0.16em] text-[#061b31]">
              N2O <span className="text-[#64748d]">·</span> DVR
            </p>
            <p className="mt-3 max-w-[300px] text-[14px] leading-[1.6] text-[#64748d]">
              DVR, allegati e piani operativi dai dati del sopralluogo, conformi al
              D.Lgs.&nbsp;81/2008.
            </p>
          </div>
          {COLUMNS.map((column) => (
            <nav key={column.label} aria-label={column.label}>
              <p className="text-[12.5px] font-medium text-[#64748d]">{column.label}</p>
              <ul className="mt-2">
                {column.links.map((link) => (
                  <li key={link.href}>
                    {link.href.startsWith("/") && !link.href.includes("#") ? (
                      <Link
                        href={link.href}
                        className="inline-flex min-h-11 items-center text-[14px] text-[#273951] transition-colors hover:text-[#061b31] sm:min-h-9"
                      >
                        {link.label}
                      </Link>
                    ) : (
                      <a
                        href={link.href}
                        className="inline-flex min-h-11 items-center text-[14px] text-[#273951] transition-colors hover:text-[#061b31] sm:min-h-9"
                      >
                        {link.label}
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>
        <p className="mt-10 border-t border-[#e5edf5] pt-6 text-[13px] text-[#64748d] sm:mt-12">
          © {new Date().getFullYear()} N2O SRL · Conforme D.Lgs. 81/2008 · Powered by Niuexa
        </p>
      </div>
    </footer>
  );
}
