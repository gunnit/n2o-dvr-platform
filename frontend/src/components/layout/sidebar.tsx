"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import {
  BookOpen,
  Building2,
  ClipboardList,
  FileText,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  MessageSquarePlus,
  MessagesSquare,
  Palette,
  Settings,
  Shield,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { FeedbackDialog } from "@/components/feedback/feedback-dialog";
import { fetchImageBlobUrl } from "@/lib/api-client";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Aziende", href: "/aziende", icon: Building2 },
  { name: "Sopralluoghi", href: "/survey", icon: ClipboardList },
  { name: "Documenti", href: "/documents", icon: FileText },
  { name: "Valutazioni", href: "/assessments", icon: FlaskConical },
  { name: "Guida", href: "/guida", icon: BookOpen },
  { name: "Impostazioni", href: "/settings", icon: Settings },
];

const adminNavigation = [
  { name: "Utenti", href: "/admin/users", icon: Users },
  { name: "Personalizzazione", href: "/admin/branding", icon: Palette },
  { name: "Feedback", href: "/admin/feedback", icon: MessagesSquare },
];

type SidebarUser = {
  name?: string | null;
  email?: string | null;
  role?: string | null;
};

export function Sidebar({ user }: { user: SidebarUser }) {
  const pathname = usePathname();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);

  // Load the organization's custom logo for the app chrome. Falls back
  // silently to the default Shield mark on 404 / any failure. The product
  // name ("N2O DVR") is fixed — only the logo is per-organization here.
  useEffect(() => {
    let cancelled = false;
    let createdUrl: string | null = null;
    (async () => {
      try {
        const url = await fetchImageBlobUrl("/api/v1/organizations/me/branding/logo");
        if (cancelled) {
          if (url) URL.revokeObjectURL(url);
          return;
        }
        createdUrl = url;
        setLogoUrl(url);
      } catch {
        /* keep the default mark */
      }
    })();
    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, []);

  const initials = (user.name ?? user.email ?? "U")
    .split(/[\s@.]+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");

  return (
    <aside className="fixed left-0 top-0 z-50 flex h-screen w-64 flex-col bg-sidebar py-6 font-body text-[13px]">
      <div className="mb-8 flex items-center gap-3 px-6">
        {logoUrl ? (
          <div className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-md bg-white p-1 ring-1 ring-white/10">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={logoUrl} alt="Logo" className="max-h-full max-w-full object-contain" />
          </div>
        ) : (
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-white/10 ring-1 ring-white/10">
            <Shield className="h-4 w-4 text-white" strokeWidth={1.75} />
          </div>
        )}
        <div>
          <h1 className="font-heading text-[15px] font-medium tracking-tight text-white">
            N2O DVR
          </h1>
          <p className="text-[11px] text-white/50">Sicurezza sul lavoro</p>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 px-3">
        {navigation.map((item) => {
          const isActive = pathname?.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 transition-colors",
                isActive
                  ? "bg-white/10 font-medium text-white"
                  : "text-white/65 hover:bg-white/5 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} />
              <span>{item.name}</span>
            </Link>
          );
        })}

        <button
          type="button"
          onClick={() => setFeedbackOpen(true)}
          className="mt-2 flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-white/65 transition-colors hover:bg-white/5 hover:text-white"
        >
          <MessageSquarePlus className="h-4 w-4 shrink-0" strokeWidth={1.75} />
          <span>Segnala</span>
        </button>

        {user.role === "admin" && (
          <>
            <div className="mt-6 mb-2 px-3 text-[10px] font-medium uppercase tracking-wider text-white/40">
              Amministrazione
            </div>
            {adminNavigation.map((item) => {
              const isActive = pathname?.startsWith(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 transition-colors",
                    isActive
                      ? "bg-white/10 font-medium text-white"
                      : "text-white/65 hover:bg-white/5 hover:text-white"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </>
        )}
      </nav>

      <div className="mt-auto border-t border-white/10 px-4 pt-4">
        <div className="flex items-center gap-3 rounded-md px-2 py-2 hover:bg-white/5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-[11px] font-medium text-white ring-1 ring-white/15">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[12px] font-medium text-white">
              {user.name ?? user.email ?? "Utente"}
            </p>
            <p className="truncate text-[10px] text-white/50">
              {user.role ?? "Operatore"}
            </p>
          </div>
          <button
            onClick={() => signOut()}
            className="rounded-sm p-1 text-white/50 transition-colors hover:bg-white/10 hover:text-white"
            aria-label="Esci"
          >
            <LogOut className="h-3.5 w-3.5" strokeWidth={1.75} />
          </button>
        </div>
      </div>
      <FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} />
    </aside>
  );
}
