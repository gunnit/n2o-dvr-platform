import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        const res = await fetch(`${API_URL}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: credentials?.email,
            password: credentials?.password,
          }),
        });

        if (!res.ok) return null;

        const data = await res.json();
        const payload = JSON.parse(
          Buffer.from(data.access_token.split(".")[1], "base64").toString()
        );

        // The token deliberately carries no display name, so fetch the profile
        // once at sign-in. Without it `session.user.name` stayed undefined and
        // every screen fell back to the raw email — "Marco Bianchi" showed up
        // as `ai+dvrtest…@niuexa.ai` with the initials "AN" (P3-1).
        //
        // The same call now also returns the capability set the shell renders
        // its navigation from, so there is one round trip rather than two.
        //
        // Best-effort: a failure here must not cost the user their login. It
        // costs a nicer name, and `capabilitiesOf` falls back to a role-derived
        // set — which is safe, because every capability is re-checked
        // server-side on the endpoint that needs it.
        let fullName: string | undefined;
        let capabilities: string[] | undefined;
        let roleLabel: string | undefined;
        try {
          const me = await fetch(`${API_URL}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${data.access_token}` },
          });
          if (me.ok) {
            const profile = await me.json();
            fullName = profile.full_name || undefined;
            capabilities = Array.isArray(profile.capabilities)
              ? profile.capabilities
              : undefined;
            roleLabel = profile.role_label || undefined;
          }
        } catch {
          // ignore — falls back to the email and to role-derived capabilities
        }

        return {
          id: payload.sub,
          email: credentials?.email as string,
          name: fullName,
          accessToken: data.access_token,
          role: payload.role,
          roleLabel,
          // What this person may do inside the organization — a different
          // question from what the organization bought, which stays in
          // `/billing/entitlements`. Cosmetic: it decides which nav entries and
          // buttons render, never whether an action succeeds.
          capabilities,
          organizationId: payload.org,
          // 'consultant' | 'direct'. Absent on tokens issued before the direct
          // channel shipped, so treat undefined as 'consultant'. This decides
          // first-paint IA only — which price list to show. Every limit and
          // every purchase is re-resolved from the database server-side
          // (INV-3), so a stale claim can never grant anything.
          accountType: payload.account_type ?? "consultant",
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const u = user as any;
        token.accessToken = u.accessToken;
        token.role = u.role;
        token.roleLabel = u.roleLabel;
        token.capabilities = u.capabilities;
        token.organizationId = u.organizationId;
        token.accountType = u.accountType;
      }
      return token;
    },
    async session({ session, token }) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (session as any).accessToken = token.accessToken;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (session.user as any).role = token.role;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (session.user as any).roleLabel = token.roleLabel;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (session.user as any).capabilities = token.capabilities;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (session.user as any).organizationId = token.organizationId;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (session.user as any).accountType = token.accountType ?? "consultant";
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
});
