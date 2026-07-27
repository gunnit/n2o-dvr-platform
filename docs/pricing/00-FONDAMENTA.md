# Pricing Foundations — evidence, cost base, and the add-on catalogue

*Shared backbone for the two go-to-market one-pagers. Rev. 2026-07-23.*

> **Client-facing version:** [Modello-di-Pricing-Piattaforma-DVR.pdf](Modello-di-Pricing-Piattaforma-DVR.pdf) (Italian, NIUEXA-branded, 13 pp) — built from `pricing-deck-it.html` via `build_pdf.py`. These markdown files are the working source; the PDF is what goes to the client.
>
> **All margins below use loaded cost: direct variable cost +200 %**, to absorb support, regulatory maintenance, payment fees and redundancy. Base direct cost is shown alongside so the uplift can be re-tuned in one place.

---

## 1. What is actually being sold

Measured from the repo, not from the brochure:

| Dimension | Built |
|---|---|
| Document types generated | **17** (DVR Master ~187pp + 16 attachments/complementary docs) |
| Risk/compliance calculators | **7** (Risk Index I=2D+P, NIOSH, VDT, INAIL Stress, Fire INF+SI+PI, PMV/PPD, PHS) + MoVaRisCh chemical |
| AI services | **11** (SDS PDF extraction, equipment-from-photo vision, risk suggester, DPI matrix, improvement measures, HACCP CCP, POS phases, POS DPI matrix, stress measures, company description, registry consolidator) |
| Data enrichment | VIES + Registro Imprese (openapi.com) + Serper + Firecrawl → autofill from P.IVA alone |
| API surface | 184 endpoints, 33 tables, 49 migrations |
| Codebase | ~35.8k LOC backend, ~45.0k LOC frontend |
| Multi-tenancy | `Organization` → users + aziende, already isolated |
| White-label | Per-org logo, letterhead, P.IVA, RSPP name printed on every generated `.docx` |
| Live editing | In-browser `.docx` preview + inline editing with locked-paragraph rules (since 2026-07-20) |

The white-label + multi-tenant layer is the single most important pricing fact: **the platform can already be resold to a firm that puts its own letterhead on the output.** That is the entire basis of the consultant model.

---

## 2. Cost base — why this is a value-priced, not cost-priced, product

Variable cost of producing one complete client engagement (typical PMI: 5 environments, 6 job roles, 25 risk rows, 8 chemical SDS, 15 photos, full 17-document set):

| Component | Model | Cost |
|---|---|---|
| SDS PDF extraction ×8 | gpt-5.5 | €0.99 |
| Equipment-from-photo ×5 | gpt-5.5 | €0.26 |
| Improvement measures ×25 | gpt-5.4-mini | €0.12 |
| Risk suggester ×5 (medium effort) | gpt-5.4-mini | €0.09 |
| DPI matrix ×6 | gpt-5.4-mini | €0.07 |
| All other AI calls | mini/nano | €0.11 |
| Visura camerale + search + scrape | openapi.com / Serper / Firecrawl | €0.21 |
| **Total direct COGS / engagement** | | **≈ €1.85** |
| **Loaded COGS (+200 %)** — absorbs support, regulatory maintenance, payment fees, redundancy | | **≈ €5.55** |
| Heavy engagement, loaded (20 SDS, 12 environments, premium toggle) | | ≈ €12.60 |

Infrastructure (Render, Frankfurt): €51/month for the current single stack; at ~100 tenants on a scaled stack, ≈ €33 per organisation per year direct, **≈ €99 loaded**; at 300 tenants, ≈ €20 direct.

**Implication:** even with costs tripled, gross margin sits at **78–91 %** across every plan below. Cost recovery is irrelevant to the pricing decision. The only defensible anchors are (a) the buyer's own billable output and (b) what the market already pays for weaker tools. Both are documented next.

---

## 3. Market evidence — anchor A: what competing software costs

| Product | Model | Price (excl. VAT) |
|---|---|---|
| [DVR Suite](https://dvrsuite.it/) Starter | cloud, 1 DVR, 50 MB | **€120/yr** |
| DVR Suite Basic | 10 DVR, 500 MB — "for consultants" | **€420/yr** |
| DVR Suite Pro | 50 DVR, 1 GB — "professional firms" | **€1,200/yr** |
| DVR Suite Unlimited | 120 DVR, 5 GB | **€2,400/yr** |
| [VRC Protection DVR-C](https://www.vrcprotection.it/product/consulente-sicurezza/) | 5 users, 15 DVR, 4 h support | **€950** |
| [Easywork "DVR Generator" Safety Box](https://www.giornalepartiteiva.it/2026/07/09/leggi-notizia/argomenti/news-4/articolo/sicurezza-sul-lavoro-1.html) | DIY single DVR, physical box + web login | **€350–380** one-off |
| Blumatica DVR Classico | perpetual desktop licence | €490 |
| Blumatica Rischi Specifici (22 risk types) | perpetual | €1,320 list / €390 promo; **€60 per risk type** |
| Blumatica DUVRI / POS / PSC / Lavoratrici Madri | perpetual, per module | €125 / €155 / €155 / €69 |
| Blumatica "Bundle RSPP" | DVR + madri + rischi specifici + MOG | €950 |

> Blumatica figures come from an archived 2014 listino ([Ordine Ingegneri RC](https://www.ordingrc.it/index.php/post/downloadAllegato?title=listino-blumatica-pdf&pid=39&id=20&c=1525282999)); nominal prices are stale, but the **relative module weighting** — that a firm pays ~€60–155 *per risk type or per document type* — is the durable signal, and it is the strongest justification for our per-document breadth.

**Read-through:** the market's ceiling for a DVR-only cloud tool is ~€2,400/yr. Nobody in that table generates 17 document types, and nobody applies AI to SDS extraction or photo-based equipment capture. We are not competing on the same axis — but we cannot pretend the €120–2,400 band does not exist. It sets the *floor of credibility*, not the ceiling of value.

---

## 4. Market evidence — anchor B: what the buyer bills for the same output

| Deliverable | Market fee to end client |
|---|---|
| DVR, low risk, ≤5 workers | €100–250 |
| DVR, up to 15 workers | €300–450 |
| DVR, PMI | €600–1,500 |
| DVR, high risk / complex organisation | €2,000–3,000+ |
| DVR, cooperative listino 2023 (documented) | €400 members / €425 non-members |
| Stress lavoro-correlato (SLC) | €175 / €200 |
| VDT — ≤5 / 6–9 / 10–15 workstations | €350 / €400 / €450 (+€25 non-members) |
| RSPP esterno, <15 workers, annual mandate | €450–600/yr |
| Manuale HACCP | from €200 |
| Data certa (timestamp → notarised copy) | €300–1,500 |

Sources: [coopcommercialisti 2023 listino](https://coopcommercialisti.it/wp-content/uploads/2023/10/Listino-prezzi-consulenza-servizi_2023.pdf), [scuolasicurezza.it](https://www.scuolasicurezza.it/prezzo-dvr-quanto-costa-il-documento-valutazione-rischi/), [gms-srl.it](https://www.gms-srl.it/sicurezza-sul-lavoro/dvr-documento-valutazione-rischi/), [sicurezza.com](https://www.sicurezza.com/costi).

**Read-through:** a consultant's full N2O-style engagement (DVR + 5–8 attachments) invoices at **€1,500–4,000**. A single studio doing 60 clients/year bills €90k–240k of document work. Software priced at €3,900/yr is **1.6–4 % of the revenue it produces**. That is the number to put in the sales deck.

---

## 5. Regulatory tailwinds worth pricing against

| Driver | Commercial consequence |
|---|---|
| DVR mandatory for **every** employer with ≥1 worker (D.Lgs. 81/2008) | ~1.5 M obligated entities; no discretionary spend |
| **Art. 29 c.3** — update within **30 days** of new equipment, accidents, or organisational change | Recurring revision demand → justifies subscription over one-off licence |
| **Art. 28 c.2 — data certa**; [Cass. 14579/2026](https://www.puntosicuro.it/pubbliredazionale-C-119/dvr-senza-data-certa-la-cassazione-fa-chiarezza-con-la-sentenza-14579/2026-AR-26559/); fine **€1,228.50–2,457.02** without it | Sellable paid add-on with a quantified downside |
| **Legge PMI 2026** (L. 11 marzo 2026 n. 34, in force 7 Apr 2026) — INAIL simplified MOG templates due; **mandatory annual written smart-working risk notice, with sanctions**; VR/simulation training with digital traceability | Two *new recurring document types* land in our engine's scope. Ship them as paid modules in 2027. |

Addressable base: ~5.08 M active Italian firms, of which ~221 k have 10–249 employees and 94.6 % are micro (<10). The micro tail is the direct-sales segment; the 10–249 band is where consultants live.

---

## 6. The metering decision — what to charge for, what to include

Loaded COGS is €5.55 per engagement. Metering every AI call would create friction worth a few euro. **Recommendation: bundle the cheap reasoning calls generously; meter only the three genuinely expensive or externally-billed actions.**

Credit weights (1 credit ≈ €0.10–0.16 at list), recalibrated on **loaded** cost — at the earlier weights (SDS 3, visura 5) both would have run below cost:

| Action | Loaded cost | Credits | Margin on the credit |
|---|---|---|---|
| Improvement measure / risk suggestion / DPI matrix / POS phase / HACCP CCP / company description | €0.004–0.055 | **1** | 56–97 % |
| Equipment recognition from site photo (gpt-5.5 vision) | €0.155 | **4** | 69 % |
| SDS PDF extraction (gpt-5.5, structured) | €0.373 | **8** | 63 % |
| Visura camerale / Registro Imprese lookup (billed by openapi.com) | €0.600 | **15** | 68 % |

A complete engagement consumes **≈ 136 credits**. Plan inclusions below are sized against that. Overage packs: 500 = €79, 2,000 = €249, 10,000 = €990 (59–74 % GM on the pack itself).

---

## 7. Add-on catalogue (applies to both models)

| Add-on | Price | Why it prices this way |
|---|---|---|
| **Onboarding & template migration** | €1,500–4,000 one-off | The firm's own boilerplate, layout and risk library get loaded into the engine. Real delivery work, and the single strongest lock-in we have. Never discount to zero. |
| **Custom document type** | from €4,500 | New generator built to their template (e.g. PSC, MOG, ISO 45001 manual) |
| **Extra seat** | €240/yr | Well above marginal cost; keeps expansion revenue honest |
| **Extra active company block** (+25) | €600/yr | Scales with their book of business |
| **AI credit packs** | €79 / €249 / €990 | See §6 |
| **Data certa** — qualified timestamp + PEC deposit per document | €19/doc or €149/yr unlimited | Anchored against €300–1,500 notarised alternative and the €1,228–2,457 fine |
| **Google Drive / gestionale delivery integration** | €900/yr | Already built for Drive; sell it |
| **White-label domain + full brand removal** | €1,200/yr | Consultant tiers only |
| **Assisted review by a certified RSPP** (N2O service) | €390–1,200 per document set | Pure services margin; also the legal-risk answer for the direct channel |
| **On-site sopralluogo** | market rate, quoted | Keeps N2O's existing service business intact |
| **Priority SLA + named CSM** | 15 % of ACV | Standard |

---

## 8. Channel conflict — the one thing that can break this

Selling to consultants **and** to the companies those consultants serve is a real conflict. Resolve it structurally, before the first contract:

- **Segment by size and risk class.** Direct plans are sold only to firms with **<15 workers in low/medium risk classes**. Everything above that is routed to a partner consultant. Put this in the consultant contract in writing.
- **Give consultants the override.** A partner-referred company converts to the consultant's tenant, and the consultant keeps the client relationship and a 20 % revenue share on that seat.
- **Never publish direct pricing that undercuts a partner's engagement fee.** €490/yr for a self-served DVR sits *below* the €600–1,500 a consultant charges for a PMI DVR — but it buys a template-driven document without professional judgement, which is a genuinely different product. Say so explicitly in the marketing.
- **Legal exposure note:** the *datore di lavoro* signs the DVR and carries liability. A pure DIY tier invites blame if an inspection goes badly. Position the direct product as **"DVR assistito"** with the optional RSPP review attached, not as "DVR fai-da-te".

---

## 9. Commercial hygiene

- All prices **excl. IVA 22 %**, billed annually in advance, EUR.
- Annual commitment; 12-month auto-renew with 60-day notice.
- Monthly billing available at **+20 %** (discourages it, funds the churn risk).
- 3-year prepay: **−15 %**.
- Uplift clause: **CPI + 3 %** annually, capped at 8 %.
- 30-day trial on direct plans; 45-day pilot (2 real companies) on consultant plans, converting to paid.
- No perpetual licences. The regulatory content requires maintenance; a perpetual sale creates an unfunded liability.
