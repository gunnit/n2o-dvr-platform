"use client";

import Link from "next/link";
import { useSession } from "next-auth/react";
import { Database, Sparkles } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsPage() {
  const { data: session } = useSession();
  const role = (session?.user as { role?: string } | undefined)?.role;
  const isAdmin = role === "admin";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="type-h1">Impostazioni</h1>
        <p className="type-body mt-2">Gestione account e preferenze</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profilo</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="type-body">
            Le impostazioni del profilo saranno disponibili a breve.
          </p>
        </CardContent>
      </Card>

      {/* US-5.4: only admins should see the backup status entry. The
          backup page itself also gates by role + bounces on render. */}
      {isAdmin && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-4 w-4" />
              Backup &amp; ripristino
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="type-body">
              Stato dei backup automatici del database, cronologia eventi e
              istruzioni per il ripristino dal pannello Render.
            </p>
            <Link
              href="/settings/backups"
              className="inline-flex h-9 items-center justify-center rounded-md border border-[#e5edf5] bg-white px-4 text-[13px] font-medium text-[#273951] transition-colors hover:bg-[#f6f9fc]"
            >
              Apri pannello backup
            </Link>
          </CardContent>
        </Card>
      )}

      {/* US-5.3: admin-only AI feedback panel — the page itself bounces
          non-admins, but we hide the entry too to keep the UI honest. */}
      {isAdmin && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              Feedback AI
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="type-body">
              Conteggi di accettazioni / rifiuti dei suggerimenti AI per
              superficie e cronologia degli ultimi 50 segnali — utile per
              capire dove migliorare i prompt.
            </p>
            <Link
              href="/admin/ai-feedback"
              className="inline-flex h-9 items-center justify-center rounded-md border border-[#e5edf5] bg-white px-4 text-[13px] font-medium text-[#273951] transition-colors hover:bg-[#f6f9fc]"
            >
              Apri pannello feedback AI
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
