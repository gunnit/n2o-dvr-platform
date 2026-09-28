import { IBM_Plex_Mono } from "next/font/google";

/**
 * Monospace face for the landing page's technical annotations — formulas,
 * norm references, document codes.
 *
 * Loaded here rather than in the root layout so only the public landing
 * preloads it: the application keeps its own `font-mono` (system monospace),
 * and nothing behind the login pays for a face it never renders. The page
 * puts `plexMono.variable` on its root, and `font-plex` (globals.css) reads it.
 */
export const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
});
