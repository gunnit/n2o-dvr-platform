"""AI credit packs — the top-up catalogue, as data.

Closes D-14. ``usage_counters.overage_credits`` has been read by the spend query
since Phase 0 and written by nothing, so under enforcement an organization that
burned through its yearly allowance had exactly one route: buy a bigger plan.
That is a terrible answer three weeks before a renewal, and the pricing docs
never intended it — they list packs at €79 / €249 / €990 precisely to "avoid
hard stops" (``docs/pricing/02-AZIENDE-DIRETTE.md`` §Add-ons).

Prices are **one-time, in euro cents, excluding IVA 22%**, and mirror
``docs/pricing/00-FONDAMENTA.md`` §7. Unlike plans, packs are not a PayPal
subscription: they are a single Orders-v2 capture, so there is no
``paypal_plan_id`` to provision and no webhook needed to sell one — see
``app.api.v1.billing`` for the checkout/capture pair.

**Packs land on the current billing period.** ``overage_credits`` lives on the
``(organization, period_start)`` counter row, so a pack tops up the allowance
for the period it was bought in and does not roll over. That is the honest
reading of the schema and of "avoid hard stops" — it exists to unblock work in
progress, not to be stockpiled — and the UI states the expiry date next to the
buy button rather than leaving the customer to discover it.
"""

from typing import Any

# Both channels buy the same packs. Model A's pricing table names the 2,000 pack
# and Model B's the 500, but neither is exclusive and building two catalogues
# would recreate the forked-code problem INV-4 exists to prevent.
CREDIT_PACKS: list[dict[str, Any]] = [
    {
        "pack_code": "PACK_500",
        "display_name": "500 crediti",
        "credits": 500,
        "price_cents": 7_900,
        "description": "Copre circa 60 estrazioni di schede di sicurezza.",
    },
    {
        "pack_code": "PACK_2000",
        "display_name": "2.000 crediti",
        "credits": 2_000,
        "price_cents": 24_900,
        "description": "Il taglio più richiesto dagli studi: circa 15 pratiche complete.",
        "recommended": True,
    },
    {
        "pack_code": "PACK_10000",
        "display_name": "10.000 crediti",
        "credits": 10_000,
        "price_cents": 99_000,
        "description": "Per chi lavora a volume: il costo per credito più basso.",
    },
]

PACKS_BY_CODE: dict[str, dict[str, Any]] = {p["pack_code"]: p for p in CREDIT_PACKS}

PACK_CODES: frozenset[str] = frozenset(PACKS_BY_CODE)


def get_pack(pack_code: str | None) -> dict[str, Any] | None:
    return PACKS_BY_CODE.get((pack_code or "").strip().upper())


def price_per_credit_cents(pack: dict[str, Any]) -> float:
    return pack["price_cents"] / pack["credits"]


def validate_catalogue() -> None:
    """Fail loudly on a catalogue that would misprice or misgrant. Tested.

    The bulk-discount check is the one that matters commercially: a bigger pack
    that costs *more* per credit is the kind of typo nobody notices until a
    customer does the arithmetic in a support ticket.
    """
    seen: set[str] = set()
    previous_unit: float | None = None
    previous_credits = 0

    for pack in CREDIT_PACKS:
        code = pack["pack_code"]
        if code in seen:
            raise ValueError(f"duplicate pack_code in catalogue: {code}")
        seen.add(code)
        if code != code.upper():
            raise ValueError(f"{code}: pack codes are uppercase by convention")
        if pack["credits"] < 1:
            raise ValueError(f"{code}: a pack must grant at least one credit")
        if pack["price_cents"] < 1:
            # A free pack would be a "grant credits" button anyone could press.
            raise ValueError(f"{code}: a pack must cost something")
        if pack["credits"] <= previous_credits:
            raise ValueError(
                f"{code}: the catalogue must be ordered by ascending credits — "
                "the UI renders it in order and prices the tiers against each other"
            )

        unit = price_per_credit_cents(pack)
        if previous_unit is not None and unit > previous_unit:
            raise ValueError(
                f"{code}: costs {unit:.2f}c per credit, more than the smaller pack's "
                f"{previous_unit:.2f}c — a larger pack must never be worse value"
            )
        previous_unit = unit
        previous_credits = pack["credits"]
