"""Stripe integration.

**Intentionally empty in Phase 0.** Filled in Phase 3/4:

* ``MB-3.2`` — create a Stripe Customer per organization, one-off Payment Link.
* ``MB-4.1`` — products/prices setup script writing ``plans.stripe_price_id``.
* ``MB-4.2`` — hosted Checkout Session.
* ``MB-4.3`` — the webhook, idempotent by ``event.id``.
* ``MB-4.4`` — Billing Portal session.

INV-2: Stripe owns the *payment lifecycle* only. Entitlements and usage are
read from Postgres, joined to Stripe via ``plans.stripe_price_id``. The webhook
is the sole writer of ``subscriptions.status`` and ``current_period_*`` — no
other code path may set them.

Prices are exclusive of IVA 22%; the organization's P.IVA / codice fiscale
(already on ``Organization``) is collected as the Stripe tax id. Stripe does not
emit Italian e-invoices (SdI) — see OPEN-DECISION-3.
"""
