# ⚠️ DEPRECATED — DO NOT EXECUTE

> **STALE PLAN — CONTAINS INCORRECT INFRASTRUCTURE REFERENCES**
> 
> This plan references **Supabase Auth** throughout (Task 4, middleware, env vars). The actual infrastructure is:
> - **Database**: PostgreSQL on Render.com (NOT Supabase)
> - **Auth**: NextAuth.js v5 (Auth.js) with email/password + Google OAuth (NOT Supabase Auth)
> - **Storage**: Render Disk (NOT Supabase Storage)
> - **Design System**: "Digital Guardian" light mode with Plus Jakarta Sans + Inter (NOT Inter + JetBrains Mono dark theme)
> 
> **A new plan must be generated before any frontend development begins.**

# Frontend Foundation Implementation Plan (STALE — DO NOT USE)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold a working Next.js 16 frontend with navigation shell, Supabase auth, i18n, and a Dashboard page with mock data — the foundation all other Phase 2 screens build on.

**Architecture:** Next.js 16 App Router with `[lang]` dynamic segment for i18n. shadcn/ui components styled with Tailwind CSS 4. Supabase Auth for login/session. Mock data layer that will be swapped for real API calls in Plan 2.

**Tech Stack:** Next.js 16, React 19, TypeScript (strict), Tailwind CSS 4, shadcn/ui, next-intl, Framer Motion, Lucide React, TanStack Table v8, sonner, @supabase/ssr

**UI Spec Reference:** `docs/superpowers/specs/2026-04-05-ui-spec-phase2-design.md`

---

## File Structure

```
frontend/
├── package.json
├── tsconfig.json
├── next.config.ts
├── tailwind.config.ts
├── postcss.config.mjs
├── .env.local                          # Supabase keys (gitignored)
├── public/
│   └── locales/                        # (reserved for static assets)
├── src/
│   ├── app/
│   │   ├── layout.tsx                  # Root layout (fonts, providers)
│   │   ├── page.tsx                    # Redirect / → /it/dashboard
│   │   └── [lang]/
│   │       ├── layout.tsx              # Auth-protected layout with sidebar + header
│   │       ├── dashboard/
│   │       │   └── page.tsx            # Dashboard page
│   │       └── login/
│   │           └── page.tsx            # Login page (public)
│   ├── components/
│   │   ├── ui/                         # shadcn/ui primitives (auto-generated)
│   │   ├── layout/
│   │   │   ├── sidebar.tsx             # Navigation sidebar
│   │   │   ├── header.tsx              # Top header bar
│   │   │   ├── nav-item.tsx            # Single sidebar nav item
│   │   │   └── queue-indicator.tsx     # Background queue badge
│   │   ├── dashboard/
│   │   │   ├── kpi-cards.tsx           # 4 KPI metric cards
│   │   │   └── client-table.tsx        # TanStack Table of companies
│   │   └── shared/
│   │       ├── empty-state.tsx         # Reusable empty state component
│   │       └── status-badge.tsx        # Reusable status badge component
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts              # Browser Supabase client
│   │   │   ├── server.ts              # Server Component Supabase client
│   │   │   └── middleware.ts           # Auth session refresh middleware
│   │   ├── mock-data.ts               # Mock data for Dashboard (replaced by API later)
│   │   └── utils.ts                   # cn() helper for Tailwind
│   ├── i18n/
│   │   ├── config.ts                  # Locale config (it, en)
│   │   ├── request.ts                 # next-intl request config
│   │   └── messages/
│   │       ├── it.json                # Italian translations
│   │       └── en.json                # English translations
│   └── middleware.ts                   # Root middleware (auth + i18n redirect)
```

---

## Task 1: Scaffold Next.js Project

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/next.config.ts`, `frontend/tailwind.config.ts`, `frontend/postcss.config.mjs`
- Create: `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx`
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/.env.local`

- [ ] **Step 1: Create Next.js project with TypeScript and Tailwind**

```bash
cd /mnt/c/Dev/dlg
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --turbopack \
  --yes
```

- [ ] **Step 2: Verify the project runs**

```bash
cd /mnt/c/Dev/dlg/frontend
npm run dev -- --port 3000
```

Open http://localhost:3000 — you should see the Next.js default page. Stop the server (Ctrl+C).

- [ ] **Step 3: Install core dependencies**

```bash
cd /mnt/c/Dev/dlg/frontend
npm install next-intl framer-motion lucide-react @tanstack/react-table sonner \
  react-hook-form @hookform/resolvers zod \
  @supabase/supabase-js @supabase/ssr \
  class-variance-authority clsx tailwind-merge
```

- [ ] **Step 4: Create the utils helper**

Create `frontend/src/lib/utils.ts`:

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 5: Create .env.local with placeholder Supabase keys**

Create `frontend/.env.local`:

```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

Add to `frontend/.gitignore` (should already be there, verify):
```
.env.local
```

- [ ] **Step 6: Commit**

```bash
cd /mnt/c/Dev/dlg
git add frontend/
git commit -m "feat: scaffold Next.js 16 project with core dependencies"
```

---

## Task 2: Initialize shadcn/ui

**Files:**
- Modify: `frontend/tailwind.config.ts`
- Create: `frontend/src/components/ui/button.tsx`
- Create: `frontend/src/components/ui/input.tsx`
- Create: `frontend/src/components/ui/badge.tsx`
- Create: `frontend/src/components/ui/card.tsx`
- Create: `frontend/src/components/ui/dropdown-menu.tsx`
- Create: `frontend/src/components/ui/table.tsx`
- Create: `frontend/src/components/ui/tooltip.tsx`
- Create: `frontend/src/components/ui/skeleton.tsx`
- Create: `frontend/src/components/ui/dialog.tsx`
- Create: `frontend/src/components/ui/separator.tsx`
- Create: `frontend/components.json`

- [ ] **Step 1: Initialize shadcn/ui**

```bash
cd /mnt/c/Dev/dlg/frontend
npx shadcn@latest init --defaults
```

When prompted, accept defaults (New York style, Zinc base color, CSS variables: yes).

- [ ] **Step 2: Install required shadcn/ui components**

```bash
cd /mnt/c/Dev/dlg/frontend
npx shadcn@latest add button input badge card dropdown-menu table tooltip skeleton dialog separator
```

- [ ] **Step 3: Verify shadcn/ui is working**

Check that `frontend/src/components/ui/button.tsx` exists and contains a `Button` component.

- [ ] **Step 4: Commit**

```bash
cd /mnt/c/Dev/dlg
git add frontend/
git commit -m "feat: initialize shadcn/ui with core components"
```

---

## Task 3: Set Up Internationalization (next-intl)

**Files:**
- Create: `frontend/src/i18n/config.ts`
- Create: `frontend/src/i18n/request.ts`
- Create: `frontend/src/i18n/messages/it.json`
- Create: `frontend/src/i18n/messages/en.json`
- Modify: `frontend/next.config.ts`

- [ ] **Step 1: Create i18n config**

Create `frontend/src/i18n/config.ts`:

```typescript
export const locales = ["it", "en"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "it";
```

- [ ] **Step 2: Create next-intl request config**

Create `frontend/src/i18n/request.ts`:

```typescript
import { getRequestConfig } from "next-intl/server";
import { locales, type Locale } from "./config";

export default getRequestConfig(async ({ requestLocale }) => {
  let locale = await requestLocale;

  if (!locale || !locales.includes(locale as Locale)) {
    locale = "it";
  }

  return {
    locale,
    messages: (await import(`./messages/${locale}.json`)).default,
  };
});
```

- [ ] **Step 3: Create Italian translation file**

Create `frontend/src/i18n/messages/it.json`:

```json
{
  "nav": {
    "dashboard": "Dashboard",
    "survey": "Sopralluogo",
    "riskScoring": "Valutazione Rischi",
    "documents": "Documenti",
    "settings": "Impostazioni"
  },
  "dashboard": {
    "title": "Dashboard",
    "subtitle": "Panoramica clienti e documenti",
    "totalCompanies": "Aziende Totali",
    "activeSurveys": "Sopralluoghi Attivi",
    "readyDocuments": "Documenti Pronti",
    "generating": "In Generazione",
    "companies": "Aziende",
    "searchPlaceholder": "Cerca azienda...",
    "newCompany": "Nuova Azienda",
    "companyName": "Ragione Sociale",
    "location": "Sede",
    "surveyStatus": "Sopralluogo",
    "documentsCount": "Documenti",
    "actions": "Azioni",
    "open": "Apri",
    "noCompanies": "Nessuna azienda ancora.",
    "createFirst": "Crea la prima azienda per iniziare.",
    "previous": "Precedente",
    "next": "Successivo"
  },
  "status": {
    "draft": "Bozza",
    "inProgress": "In Corso",
    "submitted": "Inviato",
    "completed": "Completato"
  },
  "queue": {
    "generating": "in generazione"
  },
  "auth": {
    "login": "Accedi",
    "email": "Email",
    "password": "Password",
    "loginButton": "Accedi",
    "loginError": "Email o password non validi"
  },
  "common": {
    "loading": "Caricamento...",
    "error": "Errore",
    "retry": "Riprova",
    "save": "Salva",
    "cancel": "Annulla",
    "delete": "Elimina",
    "create": "Crea",
    "saved": "Salvato"
  }
}
```

- [ ] **Step 4: Create English translation file**

Create `frontend/src/i18n/messages/en.json`:

```json
{
  "nav": {
    "dashboard": "Dashboard",
    "survey": "Survey",
    "riskScoring": "Risk Scoring",
    "documents": "Documents",
    "settings": "Settings"
  },
  "dashboard": {
    "title": "Dashboard",
    "subtitle": "Client and document overview",
    "totalCompanies": "Total Companies",
    "activeSurveys": "Active Surveys",
    "readyDocuments": "Ready Documents",
    "generating": "Generating",
    "companies": "Companies",
    "searchPlaceholder": "Search company...",
    "newCompany": "New Company",
    "companyName": "Company Name",
    "location": "Location",
    "surveyStatus": "Survey",
    "documentsCount": "Documents",
    "actions": "Actions",
    "open": "Open",
    "noCompanies": "No companies yet.",
    "createFirst": "Create your first company to get started.",
    "previous": "Previous",
    "next": "Next"
  },
  "status": {
    "draft": "Draft",
    "inProgress": "In Progress",
    "submitted": "Submitted",
    "completed": "Completed"
  },
  "queue": {
    "generating": "generating"
  },
  "auth": {
    "login": "Login",
    "email": "Email",
    "password": "Password",
    "loginButton": "Sign In",
    "loginError": "Invalid email or password"
  },
  "common": {
    "loading": "Loading...",
    "error": "Error",
    "retry": "Retry",
    "save": "Save",
    "cancel": "Cancel",
    "delete": "Delete",
    "create": "Create",
    "saved": "Saved"
  }
}
```

- [ ] **Step 5: Update next.config.ts for next-intl**

Replace `frontend/next.config.ts`:

```typescript
import createNextIntlPlugin from "next-intl/plugin";
import type { NextConfig } from "next";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {};

export default withNextIntl(nextConfig);
```

- [ ] **Step 6: Verify build succeeds**

```bash
cd /mnt/c/Dev/dlg/frontend
npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 7: Commit**

```bash
cd /mnt/c/Dev/dlg
git add frontend/
git commit -m "feat: configure next-intl with Italian and English translations"
```

---

## Task 4: Supabase Auth Setup

**Files:**
- Create: `frontend/src/lib/supabase/client.ts`
- Create: `frontend/src/lib/supabase/server.ts`
- Create: `frontend/src/lib/supabase/middleware.ts`
- Create: `frontend/src/middleware.ts`

- [ ] **Step 1: Create browser Supabase client**

Create `frontend/src/lib/supabase/client.ts`:

```typescript
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

- [ ] **Step 2: Create server Supabase client**

Create `frontend/src/lib/supabase/server.ts`:

```typescript
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // The `setAll` method was called from a Server Component.
            // This can be ignored if you have middleware refreshing sessions.
          }
        },
      },
    }
  );
}
```

- [ ] **Step 3: Create Supabase middleware helper**

Create `frontend/src/lib/supabase/middleware.ts`:

```typescript
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { pathname } = request.nextUrl;

  // Extract locale from path
  const pathnameLocale = pathname.split("/")[1];
  const isValidLocale = ["it", "en"].includes(pathnameLocale);

  // Redirect root to /it/dashboard
  if (pathname === "/") {
    const url = request.nextUrl.clone();
    url.pathname = "/it/dashboard";
    return NextResponse.redirect(url);
  }

  // If no valid locale prefix, redirect to /it version
  if (!isValidLocale) {
    const url = request.nextUrl.clone();
    url.pathname = `/it${pathname}`;
    return NextResponse.redirect(url);
  }

  // Auth check: if not logged in and not on login page, redirect to login
  const isLoginPage = pathname.endsWith("/login");
  if (!user && !isLoginPage) {
    const url = request.nextUrl.clone();
    url.pathname = `/${pathnameLocale}/login`;
    return NextResponse.redirect(url);
  }

  // If logged in and on login page, redirect to dashboard
  if (user && isLoginPage) {
    const url = request.nextUrl.clone();
    url.pathname = `/${pathnameLocale}/dashboard`;
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}
```

- [ ] **Step 4: Create root middleware**

Create `frontend/src/middleware.ts`:

```typescript
import { type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  return await updateSession(request);
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files (images, etc.)
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
```

- [ ] **Step 5: Commit**

```bash
cd /mnt/c/Dev/dlg
git add frontend/
git commit -m "feat: add Supabase auth with middleware session refresh and route protection"
```

---

## Task 5: Root Layout and Login Page

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/[lang]/login/page.tsx`

- [ ] **Step 1: Update root layout with fonts and providers**

Replace `frontend/src/app/layout.tsx`:

```typescript
import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Toaster } from "sonner";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "N2O Sicurezza — DVR Automation",
  description: "Piattaforma di automazione documenti sicurezza sul lavoro",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="it" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        {children}
        <Toaster position="bottom-right" richColors />
      </body>
    </html>
  );
}
```

- [ ] **Step 2: Update root page to redirect**

Replace `frontend/src/app/page.tsx`:

```typescript
import { redirect } from "next/navigation";

export default function RootPage() {
  redirect("/it/dashboard");
}
```

- [ ] **Step 3: Create login page**

Create `frontend/src/app/[lang]/login/page.tsx`:

```typescript
"use client";

import { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { lang } = useParams<{ lang: string }>();

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      setError(
        lang === "it" ? "Email o password non validi" : "Invalid email or password"
      );
      setLoading(false);
      return;
    }

    router.push(`/${lang}/dashboard`);
    router.refresh();
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full max-w-sm space-y-6 p-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight">N2O Sicurezza</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {lang === "it"
              ? "Accedi alla piattaforma"
              : "Sign in to the platform"}
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-2">
            <label
              htmlFor="email"
              className="text-sm font-semibold"
            >
              Email *
            </label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="password"
              className="text-sm font-semibold"
            >
              Password *
            </label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading
              ? lang === "it"
                ? "Accesso in corso..."
                : "Signing in..."
              : lang === "it"
                ? "Accedi"
                : "Sign In"}
          </Button>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
cd /mnt/c/Dev/dlg
git add frontend/
git commit -m "feat: add root layout with fonts, toaster, and login page"
```

---

## Task 6: Navigation Shell (Sidebar + Header)

**Files:**
- Create: `frontend/src/components/layout/sidebar.tsx`
- Create: `frontend/src/components/layout/header.tsx`
- Create: `frontend/src/components/layout/nav-item.tsx`
- Create: `frontend/src/components/layout/queue-indicator.tsx`
- Create: `frontend/src/app/[lang]/layout.tsx`

- [ ] **Step 1: Create NavItem component**

Create `frontend/src/components/layout/nav-item.tsx`:

```typescript
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItemProps {
  href: string;
  icon: LucideIcon;
  label: string;
  collapsed?: boolean;
}

export function NavItem({ href, icon: Icon, label, collapsed }: NavItemProps) {
  const pathname = usePathname();
  const isActive = pathname.startsWith(href);

  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
        isActive
          ? "bg-white/15 font-semibold text-white"
          : "text-white/60 hover:bg-white/10 hover:text-white/80"
      )}
    >
      <Icon className="h-5 w-5 shrink-0" />
      {!collapsed && <span>{label}</span>}
    </Link>
  );
}
```

- [ ] **Step 2: Create QueueIndicator component**

Create `frontend/src/components/layout/queue-indicator.tsx`:

```typescript
"use client";

import { Loader2 } from "lucide-react";

interface QueueIndicatorProps {
  count: number;
  label: string;
}

export function QueueIndicator({ count, label }: QueueIndicatorProps) {
  if (count === 0) return null;

  return (
    <div className="flex items-center gap-2 rounded-lg border bg-background px-3 py-1.5 text-xs text-muted-foreground">
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
      <span>
        {count} {label}
      </span>
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
        {count}
      </span>
    </div>
  );
}
```

- [ ] **Step 3: Create Sidebar component**

Create `frontend/src/components/layout/sidebar.tsx`:

```typescript
"use client";

import { useParams } from "next/navigation";
import {
  LayoutDashboard,
  ClipboardList,
  ShieldAlert,
  FileText,
  Settings,
} from "lucide-react";
import { NavItem } from "./nav-item";

const navItems = [
  { key: "dashboard", icon: LayoutDashboard, path: "dashboard" },
  { key: "survey", icon: ClipboardList, path: "survey" },
  { key: "riskScoring", icon: ShieldAlert, path: "risk-scoring" },
  { key: "documents", icon: FileText, path: "documents" },
  { key: "settings", icon: Settings, path: "settings" },
] as const;

interface SidebarProps {
  labels: Record<string, string>;
}

export function Sidebar({ labels }: SidebarProps) {
  const { lang } = useParams<{ lang: string }>();

  return (
    <aside className="hidden w-64 flex-col border-r bg-[#18244E] lg:flex">
      <div className="px-6 py-5">
        <h1 className="text-lg font-extrabold text-white">N2O Sicurezza</h1>
      </div>
      <nav className="flex flex-1 flex-col gap-1 px-3">
        {navItems.slice(0, -1).map((item) => (
          <NavItem
            key={item.key}
            href={`/${lang}/${item.path}`}
            icon={item.icon}
            label={labels[item.key]}
          />
        ))}
      </nav>
      <div className="px-3 pb-4">
        <NavItem
          href={`/${lang}/settings`}
          icon={Settings}
          label={labels.settings}
        />
      </div>
    </aside>
  );
}
```

- [ ] **Step 4: Create Header component**

Create `frontend/src/components/layout/header.tsx`:

```typescript
"use client";

import { useRouter, useParams } from "next/navigation";
import { LogOut } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { QueueIndicator } from "./queue-indicator";

interface HeaderProps {
  title: string;
  subtitle?: string;
  queueCount?: number;
  queueLabel?: string;
  userInitials?: string;
}

export function Header({
  title,
  subtitle,
  queueCount = 0,
  queueLabel = "in generazione",
  userInitials = "U",
}: HeaderProps) {
  const router = useRouter();
  const { lang } = useParams<{ lang: string }>();

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push(`/${lang}/login`);
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b bg-background px-8">
      <div>
        <h2 className="text-xl font-bold tracking-tight">{title}</h2>
        {subtitle && (
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        )}
      </div>
      <div className="flex items-center gap-4">
        <QueueIndicator count={queueCount} label={queueLabel} />
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
          {userInitials}
        </div>
        <Button variant="ghost" size="icon" onClick={handleLogout}>
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
```

- [ ] **Step 5: Create the authenticated layout**

Create `frontend/src/app/[lang]/layout.tsx`:

```typescript
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { notFound } from "next/navigation";
import { locales } from "@/i18n/config";
import { Sidebar } from "@/components/layout/sidebar";

interface LayoutProps {
  children: React.ReactNode;
  params: Promise<{ lang: string }>;
}

export default async function LangLayout({ children, params }: LayoutProps) {
  const { lang } = await params;

  if (!locales.includes(lang as "it" | "en")) {
    notFound();
  }

  const messages = await getMessages();
  const navLabels = (messages as Record<string, Record<string, string>>).nav;

  return (
    <NextIntlClientProvider messages={messages}>
      <div className="flex h-screen overflow-hidden">
        <Sidebar labels={navLabels} />
        <main className="flex flex-1 flex-col overflow-auto bg-muted/30">
          {children}
        </main>
      </div>
    </NextIntlClientProvider>
  );
}
```

- [ ] **Step 6: Verify navigation renders**

```bash
cd /mnt/c/Dev/dlg/frontend
npm run dev -- --port 3000
```

Navigate to http://localhost:3000 — you should be redirected to login (no auth yet). The sidebar should render on the dashboard route if you temporarily bypass auth. Stop the server.

- [ ] **Step 7: Commit**

```bash
cd /mnt/c/Dev/dlg
git add frontend/
git commit -m "feat: add navigation shell with sidebar, header, and authenticated layout"
```

---

## Task 7: Shared Components (Empty State + Status Badge)

**Files:**
- Create: `frontend/src/components/shared/empty-state.tsx`
- Create: `frontend/src/components/shared/status-badge.tsx`

- [ ] **Step 1: Create EmptyState component**

Create `frontend/src/components/shared/empty-state.tsx`:

```typescript
import { type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  icon: LucideIcon;
  message: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({
  icon: Icon,
  message,
  description,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <Icon className="h-12 w-12 text-muted-foreground" />
      <p className="mt-4 text-lg font-medium">{message}</p>
      {description && (
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      )}
      {actionLabel && onAction && (
        <Button onClick={onAction} className="mt-6">
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create StatusBadge component**

Create `frontend/src/components/shared/status-badge.tsx`:

```typescript
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type SurveyStatus = "draft" | "inProgress" | "submitted" | "completed";

const statusStyles: Record<SurveyStatus, string> = {
  draft: "bg-muted text-muted-foreground hover:bg-muted",
  inProgress: "bg-amber-100 text-amber-800 hover:bg-amber-100",
  submitted: "bg-blue-100 text-blue-800 hover:bg-blue-100",
  completed: "bg-green-100 text-green-800 hover:bg-green-100",
};

interface StatusBadgeProps {
  status: SurveyStatus;
  label: string;
  className?: string;
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  return (
    <Badge
      variant="secondary"
      className={cn("text-xs font-semibold", statusStyles[status], className)}
    >
      {label}
    </Badge>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd /mnt/c/Dev/dlg
git add frontend/
git commit -m "feat: add reusable EmptyState and StatusBadge components"
```

---

## Task 8: Mock Data Layer

**Files:**
- Create: `frontend/src/lib/mock-data.ts`

- [ ] **Step 1: Create mock data matching dashboard spec**

Create `frontend/src/lib/mock-data.ts`:

```typescript
export type SurveyStatus = "draft" | "inProgress" | "submitted" | "completed";

export interface Azienda {
  id: string;
  ragioneSociale: string;
  sedeLegaleCitta: string;
  surveyStatus: SurveyStatus;
  documentsReady: number;
  documentsTotal: number;
}

export interface DashboardKpis {
  totalCompanies: number;
  activeSurveys: number;
  readyDocuments: number;
  generatingDocuments: number;
}

export const mockAziende: Azienda[] = [
  {
    id: "1",
    ragioneSociale: "N2O SRL",
    sedeLegaleCitta: "Gorgonzola (MI)",
    surveyStatus: "completed",
    documentsReady: 12,
    documentsTotal: 16,
  },
  {
    id: "2",
    ragioneSociale: "Rossi Costruzioni SpA",
    sedeLegaleCitta: "Milano (MI)",
    surveyStatus: "inProgress",
    documentsReady: 0,
    documentsTotal: 16,
  },
  {
    id: "3",
    ragioneSociale: "Bianchi Alimentari SRL",
    sedeLegaleCitta: "Bergamo (BG)",
    surveyStatus: "draft",
    documentsReady: 0,
    documentsTotal: 16,
  },
  {
    id: "4",
    ragioneSociale: "Verdi Logistica SRL",
    sedeLegaleCitta: "Brescia (BS)",
    surveyStatus: "submitted",
    documentsReady: 8,
    documentsTotal: 16,
  },
  {
    id: "5",
    ragioneSociale: "Ferrari Meccanica SpA",
    sedeLegaleCitta: "Monza (MB)",
    surveyStatus: "inProgress",
    documentsReady: 0,
    documentsTotal: 16,
  },
];

export const mockKpis: DashboardKpis = {
  totalCompanies: mockAziende.length,
  activeSurveys: mockAziende.filter((a) => a.surveyStatus === "inProgress")
    .length,
  readyDocuments: mockAziende.reduce((sum, a) => sum + a.documentsReady, 0),
  generatingDocuments: 2,
};
```

- [ ] **Step 2: Commit**

```bash
cd /mnt/c/Dev/dlg
git add frontend/
git commit -m "feat: add mock data layer for dashboard development"
```

---

## Task 9: Dashboard KPI Cards

**Files:**
- Create: `frontend/src/components/dashboard/kpi-cards.tsx`

- [ ] **Step 1: Create KpiCards component**

Create `frontend/src/components/dashboard/kpi-cards.tsx`:

```typescript
"use client";

import { Building2, ClipboardList, FileCheck, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { DashboardKpis } from "@/lib/mock-data";

interface KpiCardProps {
  label: string;
  value: number;
  icon: React.ReactNode;
  colorClass?: string;
}

function KpiCard({ label, value, icon, colorClass }: KpiCardProps) {
  return (
    <Card className="transition-all duration-200 hover:-translate-y-1 hover:shadow-md">
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {label}
            </p>
            <p
              className={cn(
                "mt-1 text-3xl font-bold tracking-tight",
                colorClass
              )}
            >
              {value}
            </p>
          </div>
          <div className="text-muted-foreground">{icon}</div>
        </div>
      </CardContent>
    </Card>
  );
}

interface KpiCardsProps {
  kpis: DashboardKpis;
  labels: {
    totalCompanies: string;
    activeSurveys: string;
    readyDocuments: string;
    generating: string;
  };
}

export function KpiCards({ kpis, labels }: KpiCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiCard
        label={labels.totalCompanies}
        value={kpis.totalCompanies}
        icon={<Building2 className="h-8 w-8" />}
      />
      <KpiCard
        label={labels.activeSurveys}
        value={kpis.activeSurveys}
        icon={<ClipboardList className="h-8 w-8" />}
        colorClass="text-amber-600"
      />
      <KpiCard
        label={labels.readyDocuments}
        value={kpis.readyDocuments}
        icon={<FileCheck className="h-8 w-8" />}
        colorClass="text-green-600"
      />
      <KpiCard
        label={labels.generating}
        value={kpis.generatingDocuments}
        icon={<Loader2 className="h-8 w-8 animate-spin" />}
        colorClass="text-blue-600"
      />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /mnt/c/Dev/dlg
git add frontend/
git commit -m "feat: add KPI cards component for dashboard"
```

---

## Task 10: Dashboard Client Table

**Files:**
- Create: `frontend/src/components/dashboard/client-table.tsx`

- [ ] **Step 1: Create ClientTable component with TanStack Table**

Create `frontend/src/components/dashboard/client-table.tsx`:

```typescript
"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowUpDown, Building2, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import type { Azienda, SurveyStatus } from "@/lib/mock-data";

interface ClientTableProps {
  data: Azienda[];
  labels: Record<string, string>;
  statusLabels: Record<SurveyStatus, string>;
}

export function ClientTable({ data, labels, statusLabels }: ClientTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const { lang } = useParams<{ lang: string }>();

  const columns = useMemo<ColumnDef<Azienda>[]>(
    () => [
      {
        accessorKey: "ragioneSociale",
        header: ({ column }) => (
          <Button
            variant="ghost"
            className="-ml-4 text-xs font-semibold uppercase tracking-wider"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            {labels.companyName}
            <ArrowUpDown className="ml-2 h-3 w-3" />
          </Button>
        ),
        cell: ({ row }) => (
          <span className="font-semibold">{row.getValue("ragioneSociale")}</span>
        ),
      },
      {
        accessorKey: "sedeLegaleCitta",
        header: ({ column }) => (
          <Button
            variant="ghost"
            className="-ml-4 text-xs font-semibold uppercase tracking-wider"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            {labels.location}
            <ArrowUpDown className="ml-2 h-3 w-3" />
          </Button>
        ),
        cell: ({ row }) => (
          <span className="text-muted-foreground">
            {row.getValue("sedeLegaleCitta")}
          </span>
        ),
      },
      {
        accessorKey: "surveyStatus",
        header: labels.surveyStatus,
        cell: ({ row }) => {
          const status = row.getValue("surveyStatus") as SurveyStatus;
          return <StatusBadge status={status} label={statusLabels[status]} />;
        },
      },
      {
        accessorKey: "documentsReady",
        header: ({ column }) => (
          <Button
            variant="ghost"
            className="-ml-4 text-xs font-semibold uppercase tracking-wider"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            {labels.documentsCount}
            <ArrowUpDown className="ml-2 h-3 w-3" />
          </Button>
        ),
        cell: ({ row }) => {
          const azienda = row.original;
          return (
            <span className="text-muted-foreground">
              {azienda.documentsReady}/{azienda.documentsTotal}
            </span>
          );
        },
      },
      {
        id: "actions",
        header: labels.actions,
        cell: ({ row }) => (
          <Link
            href={`/${lang}/survey/${row.original.id}`}
            className="text-sm font-medium text-primary underline-offset-4 hover:underline"
          >
            {labels.open}
          </Link>
        ),
      },
    ],
    [labels, statusLabels, lang]
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 10 } },
  });

  if (data.length === 0) {
    return (
      <EmptyState
        icon={Building2}
        message={labels.noCompanies}
        description={labels.createFirst}
        actionLabel={labels.newCompany}
        onAction={() => {
          /* TODO: open new company modal — implemented in Plan 3 */
        }}
      />
    );
  }

  return (
    <div className="rounded-xl border bg-card">
      <div className="flex items-center justify-between border-b px-5 py-3">
        <h3 className="font-semibold">{labels.companies}</h3>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder={labels.searchPlaceholder}
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              className="h-9 w-64 pl-9 text-sm"
            />
          </div>
          <Button size="sm">
            <Plus className="mr-1 h-4 w-4" />
            {labels.newCompany}
          </Button>
        </div>
      </div>

      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id} className="px-5 text-xs">
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext()
                      )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((row) => (
            <TableRow key={row.id} className="hover:bg-muted/50">
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id} className="px-5 py-3">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <div className="flex items-center justify-between border-t px-5 py-3">
        <p className="text-xs text-muted-foreground">
          {table.getFilteredRowModel().rows.length} {labels.companies.toLowerCase()}
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            {labels.previous}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            {labels.next}
          </Button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /mnt/c/Dev/dlg
git add frontend/
git commit -m "feat: add client table with TanStack Table, sorting, search, and pagination"
```

---

## Task 11: Dashboard Page (Assemble Everything)

**Files:**
- Create: `frontend/src/app/[lang]/dashboard/page.tsx`

- [ ] **Step 1: Create the Dashboard page**

Create `frontend/src/app/[lang]/dashboard/page.tsx`:

```typescript
import { getTranslations } from "next-intl/server";
import { Header } from "@/components/layout/header";
import { KpiCards } from "@/components/dashboard/kpi-cards";
import { ClientTable } from "@/components/dashboard/client-table";
import { mockAziende, mockKpis } from "@/lib/mock-data";

export default async function DashboardPage() {
  const t = await getTranslations("dashboard");
  const tStatus = await getTranslations("status");
  const tQueue = await getTranslations("queue");

  const statusLabels = {
    draft: tStatus("draft"),
    inProgress: tStatus("inProgress"),
    submitted: tStatus("submitted"),
    completed: tStatus("completed"),
  };

  const dashboardLabels = {
    companies: t("companies"),
    searchPlaceholder: t("searchPlaceholder"),
    newCompany: t("newCompany"),
    companyName: t("companyName"),
    location: t("location"),
    surveyStatus: t("surveyStatus"),
    documentsCount: t("documentsCount"),
    actions: t("actions"),
    open: t("open"),
    noCompanies: t("noCompanies"),
    createFirst: t("createFirst"),
    previous: t("previous"),
    next: t("next"),
  };

  const kpiLabels = {
    totalCompanies: t("totalCompanies"),
    activeSurveys: t("activeSurveys"),
    readyDocuments: t("readyDocuments"),
    generating: t("generating"),
  };

  return (
    <>
      <Header
        title={t("title")}
        subtitle={t("subtitle")}
        queueCount={mockKpis.generatingDocuments}
        queueLabel={tQueue("generating")}
        userInitials="LM"
      />
      <div className="space-y-6 p-8">
        <KpiCards kpis={mockKpis} labels={kpiLabels} />
        <ClientTable
          data={mockAziende}
          labels={dashboardLabels}
          statusLabels={statusLabels}
        />
      </div>
    </>
  );
}
```

- [ ] **Step 2: Run dev server and verify dashboard renders**

```bash
cd /mnt/c/Dev/dlg/frontend
npm run dev -- --port 3000
```

Navigate to http://localhost:3000/it/dashboard (you may need to temporarily comment out auth redirect in middleware to test).

Expected: Sidebar with 5 nav items, header with "Dashboard" title and queue indicator, 4 KPI cards, and a table with 5 mock companies. Search, sort, and pagination should work.

- [ ] **Step 3: Build to verify no TypeScript errors**

```bash
cd /mnt/c/Dev/dlg/frontend
npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 4: Commit**

```bash
cd /mnt/c/Dev/dlg
git add frontend/
git commit -m "feat: assemble Dashboard page with KPI cards, client table, and header"
```

---

## Task 12: Final Verification and Cleanup

**Files:**
- No new files. Verify everything works end-to-end.

- [ ] **Step 1: Verify full build passes**

```bash
cd /mnt/c/Dev/dlg/frontend
npm run build
```

Expected: Build succeeds, no TypeScript errors, no warnings.

- [ ] **Step 2: Verify dev server renders all pages**

```bash
cd /mnt/c/Dev/dlg/frontend
npm run dev -- --port 3000
```

Test:
- http://localhost:3000 → redirects to /it/dashboard (or /it/login if auth enabled)
- http://localhost:3000/it/login → login form renders
- http://localhost:3000/it/dashboard → full dashboard with sidebar, header, KPIs, table
- http://localhost:3000/en/dashboard → same but with English labels
- Responsive: resize to <1024px → sidebar should collapse (icon-only not yet, just hidden)
- Table search: type "N2O" → filters to 1 row
- Table sort: click "Ragione Sociale" header → sorts alphabetically
- Table pagination: works with prev/next buttons

- [ ] **Step 3: Commit final state**

```bash
cd /mnt/c/Dev/dlg
git add frontend/
git commit -m "chore: verify frontend foundation build and functionality"
```

---

## Summary

After completing all 12 tasks, you'll have:

- **Working Next.js 16 app** at `frontend/` with TypeScript strict mode
- **shadcn/ui** initialized with 11 core components
- **next-intl** configured with Italian (primary) and English translations
- **Supabase Auth** with login page, session middleware, route protection
- **Navigation shell**: sidebar (navy) + header with queue indicator
- **Dashboard page**: 4 KPI cards + searchable/sortable client table
- **Reusable components**: EmptyState, StatusBadge
- **Mock data layer** ready to swap for real API (Plan 2)

**Not included** (deferred to later plans):
- Backend API (Plan 2)
- Survey Wizard (Plan 3)
- Risk Scoring + SDS (Plan 4)
- Document Generation (Plan 5)
- Responsive collapsed sidebar (icon-only at <1024px) — add in Plan 3 when more screens exist
- PWA/offline support — add in Plan 3 with survey form
