"""Usage metering — AI credits and active companies.

**Intentionally empty in Phase 0.** The module exists now so the seam is
established and nothing else grows its own metering; the implementation lands
with the enforcement phase:

* ``MB-2.3`` — ``record_active_company(org_id, azienda_id, db)``: INSERT into
  ``active_company_periods`` … ON CONFLICT DO NOTHING, from the Celery worker
  at the moment a document reaches ``completed``.
* ``MB-2.4`` — ``spend_credits(org_id, kind, idem_key, db, ent)``: the atomic
  conditional UPDATE on ``usage_counters`` plus the ``ai_usage_events`` insert,
  raising 402 when the UPDATE matches zero rows.

Two rules the implementation must keep (INV-6 / INV-7):

* Charge **before** the OpenAI call and 402 early — never bill for work that
  was never done.
* Every write is idempotent. Celery retries, document restore, Google-Doc sync,
  save-edited-version and plain double-clicks must not double-count.

Both entry points must no-op (compute + log only) while
``settings.ENTITLEMENTS_ENFORCE`` is false.
"""
