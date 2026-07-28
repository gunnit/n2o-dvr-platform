import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import { Sidebar } from "@/components/layout/sidebar";
import { AutoBreadcrumbs } from "@/components/layout/auto-breadcrumbs";
import { Providers } from "@/components/providers";
import { EntitlementsProvider } from "@/components/billing/entitlements-provider";
import { PlanRequiredBanner } from "@/components/billing/plan-required-banner";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session) {
    redirect("/login");
  }

  const user = {
    name: session.user?.name,
    email: session.user?.email,
    role: (session.user as { role?: string | null })?.role ?? "Operatore",
  };

  return (
    <Providers>
      {/* One entitlements fetch for the whole shell — the sidebar plan badge,
          the banner and every page below read the same result. */}
      <EntitlementsProvider>
        <div className="min-h-screen bg-background">
          <Sidebar user={user} />
          <div className="ml-64 flex min-h-screen flex-col">
            <AutoBreadcrumbs />
            <main className="mx-auto w-full max-w-screen-xl flex-1 px-8 py-8">
              <PlanRequiredBanner />
              {children}
            </main>
          </div>
        </div>
      </EntitlementsProvider>
    </Providers>
  );
}
