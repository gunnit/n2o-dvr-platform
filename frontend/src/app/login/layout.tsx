import type { Metadata } from "next";

// Metadata-only layout, mirroring register/layout.tsx: the page itself is a
// client component and cannot export `metadata`. Without this /login was the
// one public page still falling back to the generic root title, so a visitor
// with several tabs open saw "N2O DVR - Sicurezza sul Lavoro" on the sign-in
// tab. The root template turns this into "Accedi | N2O DVR".
export const metadata: Metadata = {
  title: "Accedi",
  description: "Accedi alla piattaforma N2O DVR.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
