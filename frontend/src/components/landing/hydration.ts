/**
 * Tells globals.css that a script is running, so it may hold animated content
 * back for that script to reveal (`html[data-hydrated]`). Until then it shows
 * everything after 4s on its own, in case the bundle never arrives.
 *
 * Decided once per document, on the first call: if hydration lands after that
 * fallback may already have fired, the flag stays unset for good, because
 * setting it would snap content the visitor is reading back to hidden. Such a
 * slow session simply keeps the fallback: content appears, without the
 * scroll-in animation.
 */
const FALLBACK_SAFE_MS = 3600;
let hydratedInTime: boolean | null = null;

export function markHydrated() {
  hydratedInTime ??= performance.now() < FALLBACK_SAFE_MS;
  if (hydratedInTime) document.documentElement.dataset.hydrated = "";
}
