"use client";

import Link from "next/link";
import { useSession } from "next-auth/react";
import { Database } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsPage() {
  const { data: session } = useSession();
  const role = (session?.user as { role?: string } | undefined)?.role;
  const isAdmin = role === "admin";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Impostazioni</h1>
        <p className="text-muted-foreground">Gestione account e preferenze</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profilo</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
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
            <p className="text-sm text-muted-foreground">
              Stato dei backup automatici del database, cronologia eventi e
              istruzioni per il ripristino dal pannello Render.
            </p>
            <Link
              href="/settings/backups"
              className="inline-flex h-8 items-center justify-center rounded-lg border border-input bg-background px-3 text-sm font-medium transition-colors hover:bg-muted"
            >
              Apri pannello backup
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
