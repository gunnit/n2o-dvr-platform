/**
 * Public price list.
 *
 * The annual prices here MUST match `price_year_cents` in
 * `backend/app/billing/plan_catalogue.py` — that module is the authority and
 * the only thing PayPal is ever told about. Everything else on this page
 * (one-time onboarding fees, add-ons, support SLAs) is commercial copy that
 * deliberately has no home in the catalogue: fees are invoiced separately, not
 * charged through the subscription.
 *
 * `cta: "checkout"` means the plan is genuinely self-serve — the customer signs
 * up and pays through PayPal unattended. `cta: "contact"` is for plans whose
 * activation involves a quote or a migration a human has to price.
 */

export type Audience = "consulenti" | "aziende";

export type PricingPlan = {
  /** Matches `plans.plan_code`. Carried through signup as `?piano=`. */
  planCode: string;
  name: string;
  audience: string;
  /** Formatted for display; the numeric source of truth is the catalogue. */
  price: string;
  priceNote: string;
  /** One-time charge, invoiced outside the subscription. */
  setupNote: string;
  features: string[];
  cta: "checkout" | "contact";
  ctaLabel: string;
  featured?: boolean;
  /** Enterprise renders inverted. */
  dark?: boolean;
};

export const PLANS: Record<Audience, PricingPlan[]> = {
  consulenti: [
    {
      planCode: "A_SOLO",
      name: "Solo",
      audience: "RSPP freelance o consulente singolo",
      price: "€1.490",
      priceNote: "all'anno, IVA esclusa",
      setupNote: "Nessun costo di attivazione",
      features: [
        "1 utente",
        "15 aziende clienti attive",
        "Tutti e 17 i tipi di documento",
        "2.500 crediti AI l'anno",
        "Carta intestata white-label",
      ],
      cta: "checkout",
      ctaLabel: "Attiva Solo",
    },
    {
      planCode: "A_STUDIO",
      name: "Studio",
      audience: "Studio da 3 a 8 persone",
      price: "€3.900",
      priceNote: "all'anno, IVA esclusa",
      setupNote: "+ €1.500 di onboarding una tantum, fatturato a parte",
      features: [
        "5 utenti",
        "60 aziende clienti attive",
        "9.000 crediti AI l'anno",
        "Migrazione di 1 set di template",
        "API in sola lettura",
      ],
      cta: "checkout",
      ctaLabel: "Attiva Studio",
      featured: true,
    },
    {
      planCode: "A_NETWORK",
      name: "Network",
      audience: "Rete multi-sede, 15+ tecnici",
      price: "€8.900",
      priceNote: "all'anno, IVA esclusa",
      setupNote: "+ €3.500 di onboarding una tantum",
      features: [
        "15 utenti",
        "200 aziende clienti attive",
        "30.000 crediti AI l'anno",
        "Dominio white-label e 10 sub-tenant",
        "Referente dedicato, risposta in 4 h",
      ],
      cta: "contact",
      ctaLabel: "Parla con noi",
    },
    {
      planCode: "A_ENTERPRISE",
      name: "Enterprise",
      audience: "Franchising, associazioni, reseller",
      price: "da €18.000",
      priceNote: "all'anno, IVA esclusa",
      setupNote: "Onboarding su preventivo",
      features: [
        "40 utenti, aziende illimitate",
        "Crediti AI a pool, non misurati",
        "Sub-tenant illimitati",
        "API completa e webhook",
        "SLA 99,5% · revisione trimestrale",
      ],
      cta: "contact",
      ctaLabel: "Richiedi un preventivo",
      dark: true,
    },
  ],
  aziende: [
    {
      planCode: "B_BASE",
      name: "Base",
      audience: "Micro impresa fino a 15 addetti, rischio basso o medio",
      price: "€490",
      priceNote: "all'anno, IVA esclusa",
      setupNote: "Primo anno €690, setup guidato incluso",
      features: [
        "1 sede, 2 utenti",
        "DVR + MMC, VDT, stress, gestanti, incendio",
        "500 crediti AI l'anno",
        "Revisioni e rigenerazioni illimitate",
        "Promemoria art. 29 c.3",
      ],
      cta: "contact",
      ctaLabel: "Richiedi l'accesso",
    },
    {
      planCode: "B_PLUS",
      name: "Plus",
      audience: "PMI da 15 a 50 addetti",
      price: "€990",
      priceNote: "all'anno, IVA esclusa",
      setupNote: "Primo anno €1.290, setup guidato incluso",
      features: [
        "3 sedi, 5 utenti",
        "Tutto Base + microclima, biologico, PEE, DUVRI",
        "1.000 crediti AI l'anno",
        "Data certa inclusa",
        "1 revisione RSPP l'anno",
      ],
      cta: "contact",
      ctaLabel: "Richiedi l'accesso",
      featured: true,
    },
    {
      planCode: "B_MULTISEDE",
      name: "Multi-sede",
      audience: "Da 10 a 249 addetti su più unità locali",
      price: "€2.400",
      priceNote: "all'anno, IVA esclusa",
      setupNote: "Primo anno €2.900, setup guidato incluso",
      features: [
        "10 sedi, 15 utenti",
        "Tutto Plus + PEE per strutture pubbliche",
        "2.500 crediti AI l'anno",
        "2 revisioni RSPP l'anno",
        "Telefono e referente dedicato",
      ],
      cta: "contact",
      ctaLabel: "Richiedi l'accesso",
    },
  ],
};

export type ComparisonTable = {
  columns: string[];
  /** `highlight` is the 0-based column index rendered on the tinted band. */
  highlight: number;
  rows: [string, ...string[]][];
  note: string;
};

export const COMPARISON: Record<Audience, ComparisonTable> = {
  consulenti: {
    columns: ["Solo", "Studio", "Network", "Enterprise"],
    highlight: 1,
    rows: [
      ["Prezzo annuo", "€1.490", "€3.900", "€8.900", "da €18.000"],
      ["Onboarding una tantum", "€0", "€1.500", "€3.500", "su preventivo"],
      ["Utenti inclusi", "1", "5", "15", "40"],
      ["Aziende clienti attive", "15", "60", "200", "illimitate"],
      ["Tipi di documento", "tutti 17", "tutti 17", "tutti 17", "tutti 17"],
      ["Crediti AI l'anno", "2.500", "9.000", "30.000", "a pool"],
      ["Carta intestata white-label", "Sì", "Sì", "Sì", "Sì"],
      ["Dominio proprio, marchio rimosso", "—", "add-on", "Sì", "Sì"],
      ["Migrazione dei tuoi template", "add-on", "1 set incluso", "3 set inclusi", "illimitata"],
      ["Portali self-service per i clienti", "—", "—", "10", "illimitati"],
      ["API", "—", "sola lettura", "completa", "completa + webhook"],
      [
        "Supporto",
        "email, 3 giorni",
        "email e chat, 1 giorno",
        "referente dedicato, 4 h",
        "SLA 99,5%, 2 h",
      ],
    ],
    note: "Si conta come azienda attiva quella per cui è stato generato o revisionato almeno un documento nell'anno di abbonamento. Le aziende archiviate restano consultabili per sempre e non rientrano nel conteggio.",
  },
  aziende: {
    columns: ["Base", "Plus", "Multi-sede"],
    highlight: 1,
    rows: [
      ["Prezzo annuo", "€490", "€990", "€2.400"],
      ["Primo anno con setup guidato", "€690", "€1.290", "€2.900"],
      ["Sedi e unità locali", "1", "3", "10"],
      ["Utenti", "2", "5", "15"],
      ["Tipi di documento inclusi", "6", "13", "14"],
      ["Crediti AI l'anno", "500", "1.000", "2.500"],
      ["App di sopralluogo", "Sì", "Sì", "Sì"],
      ["Revisioni e rigenerazioni", "illimitate", "illimitate", "illimitate"],
      ["Promemoria art. 29 c.3", "Sì", "Sì", "Sì"],
      ["Data certa", "add-on €149", "inclusa", "inclusa"],
      ["Revisione RSPP con controfirma", "add-on", "1 l'anno", "2 l'anno"],
      ["Supporto", "email, 3 giorni", "email e chat, 1 giorno", "telefono e referente"],
    ],
    note: "POS e manuale HACCP non rientrano nei piani diretti: sono documenti da cantiere e da filiera alimentare che passano da uno studio partner.",
  },
};

export type AddOn = { name: string; price: string; per?: string; note?: string };

export const ADDONS: Record<Audience, AddOn[]> = {
  consulenti: [
    { name: "25 aziende attive in più", price: "€600", per: "/anno" },
    { name: "Utente aggiuntivo", price: "€240", per: "/anno" },
    { name: "Pacchetto 2.000 crediti AI", price: "€249" },
    { name: "Dominio white-label", price: "€1.200", per: "/anno" },
    {
      name: "Data certa illimitata",
      price: "€149",
      per: "/anno",
      note: "Marca temporale qualificata e deposito PEC",
    },
    {
      name: "Nuovo tipo di documento",
      price: "da €4.500",
      note: "PSC, MOG, ISO 45001 e simili",
    },
  ],
  aziende: [
    { name: "Sede aggiuntiva", price: "€180", per: "/anno" },
    { name: "Revisione RSPP con controfirma", price: "€390", per: "/set" },
    { name: "Data certa illimitata", price: "€149", per: "/anno" },
    { name: "Tipo di documento in più su Base", price: "€190", per: "/anno" },
    { name: "Pacchetto 500 crediti AI", price: "€79" },
    { name: "Sopralluogo in sede", price: "su preventivo" },
  ],
};

export const SUPPORT_EMAIL = "support@dvr-sicurezza.it";
