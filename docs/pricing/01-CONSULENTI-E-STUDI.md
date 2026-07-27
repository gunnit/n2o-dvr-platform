# Pricing Model A — Consultancies & Studi (multi-client)

*Buyer: a firm like N2O SRL. Sells safety compliance to many client companies and needs the platform to produce billable documents at scale under its own brand.*
*Rev. 2026-07-23. Prices excl. IVA 22 %, annual commitment.*

---

## The plans

| | **Solo** | **Studio** ★ | **Network** | **Enterprise / Reseller** |
|---|---|---|---|---|
| **Price** | **€1,490/yr** | **€3,900/yr** | **€8,900/yr** | **from €18,000/yr** |
| Target | single RSPP / freelance consultant | 3–8 person studio (this is N2O today) | multi-office network, 15+ technicians | franchise, association, or software reseller |
| Seats included | 1 | 5 | 15 | 40 |
| Active client companies | 15 | 60 | 200 | unlimited |
| Document types | all 17 | all 17 | all 17 | all 17 |
| AI credits / yr | 2,500 | 9,000 | 30,000 | pooled, unmetered |
| White-label letterhead (logo, P.IVA, RSPP) | ✓ | ✓ | ✓ | ✓ |
| White-label domain + brand removal | — | add-on | ✓ | ✓ |
| Own template migration | add-on | **included (1 template set)** | included (3 sets) | included, unlimited |
| Sub-tenants (client self-service portals) | — | — | 10 | unlimited |
| API access | — | read-only | full | full + webhooks |
| Support | email, 3 business days | email + chat, 1 business day | named CSM, 4 h | SLA 99.5 %, 2 h, quarterly review |
| Onboarding fee (one-off) | €0 | **€1,500** | **€3,500** | quoted |

**"Active client company"** = an azienda with at least one document generated or revised in the subscription year. Archived clients stay readable forever and do not count. This is the fairest possible metric and it is the one the buyer already thinks in — it is their client book.

---

## Why these numbers

### 1. Priced as a share of the revenue it produces

A studio's engagement (DVR + 5–8 attachments) invoices at **€1,500–4,000** to the end client. Documented market fees: DVR PMI €600–1,500; DVR high-risk €2,000–3,000+; stress lavoro-correlato €175–200; VDT €350–450; HACCP manual from €200.

| Plan | Client engagements | Studio's gross billings | Platform cost | **% of billings** |
|---|---|---|---|---|
| Solo | 15 | €22k–45k | €1,490 | **3.3–6.6 %** |
| Studio | 60 | €90k–240k | €3,900 + €1,500 setup | **2.2–6.0 %** yr 1, **1.6–4.3 %** after |
| Network | 200 | €300k–800k | €8,900 + €3,500 setup | **1.5–4.1 %** yr 1 |

Every tier lands in the **2–6 % of produced revenue** band. Professional-tools spend is defensible up to ~10 %; we are comfortably under, which means the objection will not be price, it will be switching cost — handled by the onboarding fee and template migration below.

### 2. Priced against the labour it replaces

The stated product goal is **60–70 % time reduction** on document production. A senior technician's fully-loaded cost is €35–55/hour. A manual full document set is 12–20 hours.

At the Studio tier: 60 engagements × 14 hours saved × €40/h = **€33,600 of recovered capacity per year** against €3,900. **8.6× return**, and that is before counting the engagements the studio can now accept because capacity exists.

This is the number to lead with in the sales conversation, not the feature list.

### 3. Priced against what the market already pays for less

| Competitor | What you get | Price |
|---|---|---|
| DVR Suite Pro | 50 DVR, cloud, **DVR only** | €1,200/yr |
| DVR Suite Unlimited | 120 DVR, **DVR only** | €2,400/yr |
| VRC Protection DVR-C | 5 users, 15 DVR, 4 h support | €950 |
| Blumatica "Bundle RSPP" | DVR + madri + rischi specifici + MOG, desktop, perpetual | €950 |
| Blumatica per-risk modules | **€60 each**, 22 risk types | up to €1,320 |

Our **Studio** tier at €3,900 is ~3× DVR Suite Pro. The premium is carried by four things a competitor comparison makes obvious:

1. **17 document types vs 1.** Blumatica's own listino prices modules at €60–155 *each*; at their unit economics our attachment library alone lists above €1,300.
2. **AI that removes data entry**, not just formats it — SDS PDF → structured chemical record, site photo → equipment inventory, risk library → suggested measures. No Italian competitor does this today.
3. **The digital survey (sopralluogo) app** — the studio's field technician captures once; office staff never re-key. This is the "review, not entry" principle and it is the actual time saving.
4. **White-label output.** The client firm's logo, P.IVA and RSPP name print on every document. The platform is invisible to the end client, which is exactly what a consultancy requires and what a desktop licence cannot deliver.

### 4. Why "active companies", not seats, is the primary meter

Seats scale with headcount; revenue scales with clients. A 3-person studio serving 80 companies is a bigger account than a 10-person studio serving 20. Metering on active companies aligns our revenue with theirs, makes expansion automatic, and removes the incentive to password-share. Seats stay as a secondary meter to prevent a 40-person firm buying Solo.

---

## Unit economics

**All costs loaded at +200 %** over measured direct cost (see [Foundations §2](00-FONDAMENTA.md)).

| Plan | Price | Engagements | Variable COGS | Infra | **Gross margin** |
|---|---|---|---|---|---|
| Solo | €1,490 | 15 | €110 | €99 | **86.0 %** |
| Studio | €3,900 | 60 | €439 | €99 | **86.2 %** |
| Network | €8,900 | 200 | €1,463 | €99 | **82.5 %** |
| Enterprise | €18,000 | 500 | €3,656 | €360 | **77.7 %** |

*Variable COGS = AI tokens (gpt-5.5 for SDS/vision, gpt-5.4-mini for reasoning, gpt-5.4-nano for boilerplate) + Registro Imprese/search/scrape calls, at 25 % heavy-engagement mix, uplifted 200 %.*

Illustrative acquisition economics (assumes 90 % gross retention, 3-year horizon):

| Plan | ACV | CAC target | Payback | LTV | LTV/CAC |
|---|---|---|---|---|---|
| Solo | €1,490 | €900 | 7.2 mo | €4,023 | 4.5× |
| Studio | €3,900 | €2,500 | 7.7 mo | €10,530 | 4.2× |
| Network | €8,900 | €6,000 | 8.1 mo | €24,030 | 4.0× |

All three clear the 3× LTV/CAC and <12-month payback thresholds with room. **This segment can absorb a real sales motion** — inside sales, ordini professionali partnerships, trade events — which the direct segment cannot.

---

## Add-ons that matter most here

| Add-on | Price | Attach-rate expectation |
|---|---|---|
| Onboarding & template migration | €1,500–4,000 | 100 % on Studio+ (mandatory) |
| Extra 25 active companies | €600/yr | ~40 % of Studio accounts by year 2 |
| Extra seat | €240/yr | ~50 % |
| AI credit pack (2,000) | €249 | ~25 % |
| White-label domain + brand removal | €1,200/yr | ~30 % of Studio, included in Network |
| Custom document type (PSC, MOG, ISO 45001…) | from €4,500 | ~15 %, high strategic value |
| Data certa — qualified timestamp + PEC deposit | €149/yr unlimited | ~50 %; anchored against €300–1,500 notarised alternative and the €1,228.50–2,457.02 fine for a DVR without certain date |
| Drive / gestionale delivery integration | €900/yr | ~20 % |
| Priority SLA + named CSM | 15 % of ACV | Network+ |

Modelled net revenue retention with these attach rates: **112–118 %**. The add-on layer, not the base plan, is what makes this segment compound.

---

## The 2027 expansion lane, already visible

**Legge PMI 2026** (L. 11 marzo 2026 n. 34, in force 7 April 2026) introduces two new recurring obligations that land inside our existing engine:

- **Simplified INAIL MOG templates** for PMI — a new generator, sellable as a €4,500 custom module or a €600/yr add-on across the base.
- **Mandatory annual written smart-working risk notice**, now backed by a sanctions regime — a short, high-volume, recurring document. Perfect fit for the existing data layer, and it recurs *every year for every client*.

Both should be built and priced before the market's incumbents notice. They also give a clean, non-discount reason to raise prices at renewal.

---

## Risks to this model

| Risk | Mitigation |
|---|---|
| N2O is both first customer and prospective competitor to other studios | Sell N2O a perpetual founding-partner discount (e.g. Studio at €0 for 3 years, or revenue share) in exchange for reference rights and template contribution. Do not let this be renegotiated annually. |
| "Active company" gaming — archive/unarchive churn | Count any azienda touched in the period; archived clients readable but frozen. Enforce in code before first external sale. |
| Studios expect perpetual licences (Blumatica has trained them to) | Refuse. Lead with regulatory maintenance: content that tracks D.Lgs. 81/2008 amendments cannot be sold once. Offer 3-year prepay at −15 % as the compromise. |
| Price objection anchored on DVR Suite's €1,200 | Reframe on document count (17 vs 1) and hours saved (€33.6k), never on feature parity. |
| No billing infrastructure exists in the codebase yet | Stripe subscriptions + a `Subscription`/`UsageCounter` model on `Organization` are prerequisites for any external sale. Estimate before committing to a launch date. |

---

## Recommended launch position

**Lead with Studio at €3,900 + €1,500 onboarding.** It is the tier N2O itself occupies, so it comes with a real reference story; it prices at ~2–4 % of the buyer's billings; and it clears CAC in under 8 months. Solo exists to make Studio look reasonable and to catch freelancers; Network exists to give Studio somewhere to grow into.
