import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Providers } from "@/components/providers";

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
      <div className="min-h-screen bg-background">
        <Sidebar user={user} />
        <div className="ml-64 flex min-h-screen flex-col">
          <Header />
          <main className="mx-auto w-full max-w-screen-xl flex-1 px-8 py-8">{children}</main>
        </div>
      </div>
    </Providers>
  );
}
