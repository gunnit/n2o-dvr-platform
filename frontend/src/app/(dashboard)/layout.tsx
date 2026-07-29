import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import { Sidebar } from "@/components/layout/sidebar";
import { NavDrawerProvider } from "@/components/layout/nav-drawer";
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
        {/* `lg:ml-64` and not `ml-64`: the sidebar is a fixed 256px column only
            once there is room for it. Below that it is an overlay drawer, and an
            unconditional margin left the operatore di campo — whose whole job is
            filling the sopralluogo on site — with 134px of usable width. */}
        <NavDrawerProvider>
          <div className="min-h-screen bg-background">
            <Sidebar user={user} />
            <div className="flex min-h-screen flex-col lg:ml-64">
              <AutoBreadcrumbs />
              <main className="mx-auto w-full max-w-screen-xl flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
                <PlanRequiredBanner />
                {children}
              </main>
            </div>
          </div>
        </NavDrawerProvider>
      </EntitlementsProvider>
    </Providers>
  );
}
