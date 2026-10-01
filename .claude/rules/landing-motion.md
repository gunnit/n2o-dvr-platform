---
paths:
  - "frontend/src/components/landing/**"
  - "frontend/src/app/page.tsx"
  - "frontend/src/app/globals.css"
  - "frontend/scripts/build-hero-depth.py"
---

# Landing motion

The public landing animates; its content never depends on the animation.

- **The finished state is the default.** Everything is server-rendered visible. A hidden-until-animated state lives in `globals.css`, behind `@media (scripting: enabled) and (prefers-reduced-motion: no-preference)`, and unhides after 4s if `html[data-hydrated]` never appears. Never ship `opacity: 0` inline from React: that once left every section heading invisible without JavaScript.
- **Reduced motion means the finished state**, not a slower animation (`useSkipMotion`). Derive it in render; don't `setState` in an effect for it.
- **The hero image is the LCP and the fallback.** `hero-depth-gl.ts` (raw WebGL1, ~2.6 KB gzip) is a dynamic import loaded in idle time after the image paints. If WebGL is missing, software-only, slow or lost, the image stays and the pins rise on the same timetable. Don't bring in three.js or another 3D library for the hero.
- **The hero's images are derived, not drawn.** `officina-modello.webp` is the approved render with its pins inpainted out; `officina-profondita.webp` is its depth map, 1024×512 so WebGL1 can mipmap it. Both come from `frontend/scripts/build-hero-depth.py`, which also prints the pin coordinates and scan/ground constants in `hero-scene.ts`. A new render means re-running it and updating those numbers.
- **Risk numbers mirror the backend.** `risk.ts` matches `backend/app/services/risk_calculator.py` (I = 2·D + P, the four bands, their timeframes). `tests/landing-risk.test.mjs` fails if the hero's worked example stops adding up.
- **Decorative scroll motion is CSS scroll timelines** (`parallax-sm`, `parallax-lg`, `parallax-tile`), compositor-only. No scroll listeners for decoration; the hero's one listener feeds its WebGL tilt.
