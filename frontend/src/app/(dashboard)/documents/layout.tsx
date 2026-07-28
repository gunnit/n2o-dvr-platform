import type { Metadata } from "next";

// Metadata-only layout: the page itself is a client component and cannot
// export `metadata`. The root layout's title template turns this into
// "Documenti | N2O DVR" (P3-6).
export const metadata: Metadata = {
  title: "Documenti",
  description: "Genera e scarica i documenti di sicurezza.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
