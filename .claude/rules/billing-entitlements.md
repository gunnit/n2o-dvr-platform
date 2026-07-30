---
paths:
  - "backend/app/billing/**"
  - "backend/app/api/**"
  - "backend/tests/test_billing*.py"
  - "frontend/src/lib/billing.ts"
  - "frontend/src/**/billing/**"
---

# Entitlements and billing

The platform sells plans — consultant (`A_*`) and direct-company (`B_*`) — through PayPal, and `ENTITLEMENTS_ENFORCE=true` in production means plan limits actually return `402`. Source of truth for plans and limits: `backend/app/billing/plan_catalogue.py` (mirrors `docs/pricing/`). Phase history and deviations: `docs/build/MONETIZATION-BUILD-PLAN.md`.

- **Every write path that produces new work needs an entitlement gate.** Document generation, azienda creation, user invites and all 13 AI endpoints are gated. `backend/tests/test_billing_enforcement.py` fails the build if a new bypass appears.
- **Read and download paths are deliberately never gated.** D.Lgs. 81/2008 retention means a lapsed tenant keeps its existing documents.
- **`ai_credits_year = None` means "pooled and unmetered" (Enterprise), not "no credits".** Use `0` for a tenant that bought nothing. Getting this backwards hands non-payers unlimited OpenAI spend.
- **Credit top-ups are sellable** (€79 / €249 / €990, `backend/app/billing/credit_packs.py`) as one-time PayPal *Orders*, not subscriptions. They land on `usage_counters.overage_credits` for the **current period only** — packs do not roll over, and `/billing` says so next to the buy button. The grant is exactly-once via the `credit_purchases.status` flip, because the browser return and the webhook both settle the same order. Never call `metering.grant_overage_credits` from anywhere but `billing/credits.py`.
- **Production runs PayPal in *sandbox* on purpose**, so the funnel can be walked with test money. `plans.paypal_plan_id` holds sandbox ids; going live requires reissuing them per `DEPLOY.md` §4b-bis, not an env-var flip.

Plan entitlements answer *what the organization bought* and fail with `402`. That is a different question from *what this person may do*, which fails with `403` — see the permissions rule. Both apply to the same endpoints.
