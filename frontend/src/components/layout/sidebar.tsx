"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import {
  BookOpen,
  Building2,
  ClipboardList,
  CreditCard,
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
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useNavDrawer } from "@/components/layout/nav-drawer";
import { FeedbackDialog } from "@/components/feedback/feedback-dialog";
import { planDisplayName } from "@/components/billing/billing-ui";
import { useEntitlementsContext } from "@/components/billing/entitlements-provider";
import { fetchImageBlobUrl } from "@/lib/api-client";
import { creditsPercent } from "@/lib/billing";
import { usePermissions } from "@/hooks/use-permissions";
import { useTenantVocabulary } from "@/hooks/use-tenant-vocabulary";
import {
  ADMIN_TOOLS,
  ASSESSMENTS_WRITE,
  AZIENDE_READ,
  BILLING_READ,
  type Capability,
  DOCUMENTS_READ,
  ORG_MANAGE,
  SURVEY_WRITE,
  USERS_MANAGE,
} from "@/lib/permissions";

type NavItem = {
  name: string;
  href: string;
  icon: typeof LayoutDashboard;
  /** Hidden unless the user holds this. Absent = visible to everyone. */
  capability?: Capability;
};

/**
 * The main navigation, as a function of who is looking.
 *
 * Two filters, deliberately kept apart:
 *
 * * **capability** — what this person's role permits. A field operator has no
 *   business on `/admin/users`, so the entry is not rendered at all rather than
 *   rendered into a 403.
 * * **vocabulary** — what the tenant's channel calls things. A consultant
 *   manages "Aziende" (a client portfolio); a direct company manages "La mia
 *   azienda" (itself). Same route, same data, different noun.
 *
 * Neither filter gates anything: every route is re-checked server-side.
 */
function mainNavigation(companiesTitle: string): NavItem[] {
  return [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    {
      name: companiesTitle,
      href: "/aziende",
      icon: Building2,
      capability: AZIENDE_READ,
    },
    { name: "Sopralluoghi", href: "/survey", icon: ClipboardList, capability: SURVEY_WRITE },
    { name: "Documenti", href: "/documents", icon: FileText, capability: DOCUMENTS_READ },
    {
      name: "Valutazioni",
      href: "/assessments",
      icon: FlaskConical,
      capability: ASSESSMENTS_WRITE,
    },
    { name: "Guida", href: "/guida", icon: BookOpen },
    { name: "Abbonamento", href: "/billing", icon: CreditCard, capability: BILLING_READ },
    { name: "Impostazioni", href: "/settings", icon: Settings },
  ];
}

const adminNavigation: NavItem[] = [
  { name: "Utenti", href: "/admin/users", icon: Users, capability: USERS_MANAGE },
  {
    name: "Personalizzazione",
    href: "/admin/branding",
    icon: Palette,
    capability: ORG_MANAGE,
  },
  { name: "Feedback", href: "/admin/feedback", icon: MessagesSquare, capability: ADMIN_TOOLS },
];

type SidebarUser = {
  name?: string | null;
  email?: string | null;
  role?: string | null;
};

export function Sidebar({ user }: { user: SidebarUser }) {
  const pathname = usePathname();
  const { open, isDesktop, close } = useNavDrawer();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const { can, roleLabel } = usePermissions();
  const vocabulary = useTenantVocabulary();

  const navigation = mainNavigation(vocabulary.companiesTitle).filter(
    (item) => !item.capability || can(item.capability)
  );
  const adminItems = adminNavigation.filter(
    (item) => !item.capability || can(item.capability)
  );

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
    <>
      {/* Backdrop. Rendered always and faded, rather than mounted on open, so
          the drawer's slide and the dim happen in one frame. */}
      <div
        aria-hidden
        onClick={close}
        className={cn(
          "fixed inset-0 z-40 bg-[#061b31]/45 transition-opacity duration-200 lg:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />

      <aside
        // Off-screen is not merely invisible: without `inert` a keyboard user
        // tabs from the hamburger straight into a menu that is not on screen.
        // Desktop never gets it — there the sidebar is the layout.
        inert={!isDesktop && !open}
        aria-label="Navigazione principale"
        className={cn(
          "fixed left-0 top-0 z-50 flex h-screen w-64 flex-col bg-sidebar py-6 font-body text-[13px]",
          "transition-transform duration-200 ease-out lg:translate-x-0 lg:transition-none",
          open ? "translate-x-0 shadow-2xl" : "-translate-x-full",
        )}
      >
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
          <div className="min-w-0 flex-1">
            <h1 className="font-heading text-[15px] font-medium tracking-tight text-white">
              N2O DVR
            </h1>
            <p className="text-[11px] text-white/50">Sicurezza sul lavoro</p>
          </div>
          <button
            type="button"
            onClick={close}
            aria-label="Chiudi il menu"
            className="-mr-1 rounded-md p-1.5 text-white/60 transition-colors hover:bg-white/10 hover:text-white lg:hidden"
          >
            <X className="h-4 w-4" strokeWidth={2} />
          </button>
        </div>

        {/* min-h-0 + overflow-y-auto, not just flex-1: a flex item's implicit
            min-height is its content, so without these the nav refuses to shrink
            and shoves the plan badge and the user footer (with the only logout
            control) off the bottom of the viewport on short screens. */}
        <nav className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-3">
          {navigation.map((item) => {
            const isActive = pathname?.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={close}
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
            onClick={() => {
              close();
              setFeedbackOpen(true);
            }}
            className="mt-2 flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-white/65 transition-colors hover:bg-white/5 hover:text-white"
          >
            <MessageSquarePlus className="h-4 w-4 shrink-0" strokeWidth={1.75} />
            <span>Segnala</span>
          </button>

          {adminItems.length > 0 && (
            <>
              <div className="mt-6 mb-2 px-3 text-[10px] font-medium uppercase tracking-wider text-white/40">
                Amministrazione
              </div>
              {adminItems.map((item) => {
                const isActive = pathname?.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={close}
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

        {/* The plan badge is itself a permissioned surface: a role that cannot
            read billing has no use for a meter it can neither act on nor change. */}
        {can(BILLING_READ) && <PlanTracker />}

        <div className="mt-auto shrink-0 border-t border-white/10 px-4 pt-4">
          <div className="flex items-center gap-3 rounded-md px-2 py-2 hover:bg-white/5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-[11px] font-medium text-white ring-1 ring-white/15">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[12px] font-medium text-white">
                {user.name ?? user.email ?? "Utente"}
              </p>
              {/* The human label, not the identifier: this line used to read
                  "operatore_ufficio" to the operator it described. */}
              <p className="truncate text-[10px] text-white/50">{roleLabel}</p>
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
    </>
  );
}

/**
 * Plan name + AI credit consumption, on every authenticated page.
 *
 * The product owner's requirement: an operator should never have to open
 * `/billing` to find out how many crediti AI are left. Renders nothing while
 * the entitlements request is in flight — a skeleton that resolves into a
 * two-line block would shove the user footer around on every navigation — and
 * nothing at all if the request failed, because a missing badge is honest and a
 * "0 crediti" badge is not.
 */
function PlanTracker() {
  const { entitlements, loading } = useEntitlementsContext();
  if (loading || !entitlements) return null;

  const ent = entitlements;

  if (!ent.subscribed) {
    return (
      <div className="mt-4 shrink-0 px-4">
        <Link
          href="/billing"
          className="block rounded-md border border-white/10 bg-white/5 p-3 transition-colors hover:bg-white/10"
        >
          <p className="text-[10px] font-medium uppercase tracking-wider text-white/40">
            Piano
          </p>
          <p className="mt-0.5 text-[12.5px] font-medium text-white">Nessun piano</p>
          <span className="mt-2.5 flex h-7 items-center justify-center rounded-md bg-primary px-3 text-[11.5px] font-semibold text-white ring-1 ring-white/15 transition-colors hover:bg-[#1b5594]">
            Attiva un piano
          </span>
        </Link>
      </div>
    );
  }

  const allowance = ent.usage.ai_credits_allowance;
  const percent = creditsPercent(ent.usage);
  // Same thresholds as the meters on /billing and the dashboard: amber at 75%,
  // red at 90%. Warn before the wall, not at it.
  const fill =
    percent !== null && percent >= 90
      ? "bg-[#ef4444]"
      : percent !== null && percent >= 75
        ? "bg-[#f59e0b]"
        : "bg-[#15be53]";

  return (
    <div className="mt-4 shrink-0 px-4">
      <Link
        href="/billing"
        className="block rounded-md border border-white/10 bg-white/5 p-3 transition-colors hover:bg-white/10"
      >
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-[10px] font-medium uppercase tracking-wider text-white/40">
            Piano
          </span>
          <span className="truncate text-[12px] font-medium text-white">
            {planDisplayName(ent)}
          </span>
        </div>
        {/* "Crediti AI 0 / 9000" beside an empty bar read as "no credits left",
            the opposite of the truth. The label carries the direction now. */}
        <div className="mt-2 flex items-baseline justify-between gap-2 text-[11px]">
          <span className="text-white/55">Crediti AI usati</span>
          <span className="tnum text-white/80">
            {ent.usage.ai_credits_used.toLocaleString("it-IT")} /{" "}
            {allowance === null
              ? "illimitati"
              : allowance.toLocaleString("it-IT")}
          </span>
        </div>
        {allowance !== null && (
          <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
            <div
              className={cn("h-full rounded-full transition-all", fill)}
              style={{ width: `${percent ?? 0}%` }}
            />
          </div>
        )}
      </Link>
    </div>
  );
}
