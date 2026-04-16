"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import {
  Building2,
  ClipboardList,
  FileText,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  Settings,
  Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Aziende", href: "/aziende", icon: Building2 },
  { name: "Sopralluoghi", href: "/survey", icon: ClipboardList },
  { name: "Documenti", href: "/documents", icon: FileText },
  { name: "Valutazioni", href: "/assessments", icon: FlaskConical },
  { name: "Impostazioni", href: "/settings", icon: Settings },
];

type SidebarUser = {
  name?: string | null;
  email?: string | null;
  role?: string | null;
};

export function Sidebar({ user }: { user: SidebarUser }) {
  const pathname = usePathname();
  const initials = (user.name ?? user.email ?? "U")
    .split(/[\s@.]+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");

  return (
    <aside className="fixed left-0 top-0 z-50 flex h-screen w-64 flex-col bg-sidebar py-6 sidebar-shadow font-heading text-sm">
      <div className="mb-10 flex items-center gap-3 px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-container">
          <Shield className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight text-white">N2O DVR</h1>
          <p className="text-[11px] text-white/50">Sicurezza sul lavoro</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname?.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "mx-2 flex items-center gap-3 rounded-xl px-4 py-3 transition-colors",
                isActive
                  ? "bg-primary-container font-semibold text-white"
                  : "text-white/70 hover:bg-white/10 hover:text-white"
              )}
            >
              <Icon className="h-5 w-5 shrink-0" strokeWidth={1.75} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto border-t border-white/10 px-6 pt-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-container text-xs font-bold text-white">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-white">
              {user.name ?? user.email ?? "Utente"}
            </p>
            <p className="truncate text-[10px] text-white/50">
              {user.role ?? "Operatore"}
            </p>
          </div>
          <button
            onClick={() => signOut()}
            className="rounded-lg p-1.5 text-white/50 transition-colors hover:bg-white/10 hover:text-white"
            aria-label="Esci"
          >
            <LogOut className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </div>
      </div>
    </aside>
  );
}
