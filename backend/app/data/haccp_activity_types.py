"""HACCP food-activity-type catalog with default CCPs (US-4.3 AC1).

Each activity type ships a curated set of Critical Control Points with
temperature limits and monitoring cadence drawn from Reg. CE 852/2004
and the HACCP Codex Alimentarius guidelines that N2O's consultants use
in the field.

Activity types are keyed by short slugs so the frontend can send them on
the wire without Italian-locale coupling, and the Italian display label
lives in ``nome``. ``get_default_ccps(slug)`` is the single helper the
config API uses to pre-load a fresh azienda.
"""

from __future__ import annotations

from typing import TypedDict


class Ccp(TypedDict):
    codice: str
    nome: str
    fase: str
    pericolo: str
    limite_critico: str
    monitoraggio: str
    azione_correttiva: str
    frequenza: str


class ActivityType(TypedDict):
    slug: str
    nome: str
    descrizione: str
    ccps: list[Ccp]


# Common CCPs reused across multiple activity types — defined once so
# tweaking e.g. the cooking temperature limit updates every activity.
_CCP_COTTURA: Ccp = {
    "codice": "CCP1",
    "nome": "Cottura",
    "fase": "Cottura / trattamento termico",
    "pericolo": "Sopravvivenza di microrganismi patogeni (Salmonella, Listeria, E. coli)",
    "limite_critico": "Temperatura al cuore dell'alimento >= 75 C per almeno 2 minuti",
    "monitoraggio": "Termometro a sonda calibrato sul pezzo piu spesso",
    "azione_correttiva": "Prolungare la cottura fino al raggiungimento del limite; se impossibile, scartare",
    "frequenza": "Ogni cottura",
}

_CCP_CONSERVAZIONE_FREDDA: Ccp = {
    "codice": "CCP2",
    "nome": "Conservazione a freddo",
    "fase": "Stoccaggio refrigerato",
    "pericolo": "Crescita microbica in alimenti deperibili",
    "limite_critico": "T frigo 0-4 C per prodotti deperibili; T congelatore <= -18 C",
    "monitoraggio": "Termometro calibrato / data-logger in ciascun comparto",
    "azione_correttiva": "Trasferire alimenti in comparto conforme; valutare scarto se T > 8 C per >2 h",
    "frequenza": "2 volte al giorno (mattina / sera)",
}

_CCP_SCONGELAMENTO: Ccp = {
    "codice": "CCP3",
    "nome": "Scongelamento",
    "fase": "Preparazione",
    "pericolo": "Crescita microbica durante lo scongelamento a T ambiente",
    "limite_critico": "Scongelamento in frigo a 0-4 C; mai a T ambiente > 2 h",
    "monitoraggio": "Registrazione su scheda SA-05 con orari inizio/fine",
    "azione_correttiva": "Cuocere subito oppure scartare se superati i tempi",
    "frequenza": "Ogni scongelamento",
}

_CCP_RICEVIMENTO: Ccp = {
    "codice": "CCP4",
    "nome": "Ricevimento materie prime",
    "fase": "Accettazione merci",
    "pericolo": "Alimenti contaminati o con temperatura non conforme all'ingresso",
    "limite_critico": "T merce refrigerata <= 4 C; T surgelati <= -15 C; imballaggio integro; etichetta leggibile",
    "monitoraggio": "Controllo visivo + termometro a sonda sul mezzo di trasporto",
    "azione_correttiva": "Respingere la fornitura e compilare scheda di reclamo SA-08",
    "frequenza": "Ogni consegna",
}

_CCP_ABBATTIMENTO: Ccp = {
    "codice": "CCP5",
    "nome": "Abbattimento temperatura",
    "fase": "Raffreddamento rapido post-cottura",
    "pericolo": "Permanenza prolungata in zona di rischio (10-60 C)",
    "limite_critico": "Da 60 C a 10 C in <= 2 h; porzioni < 5 kg",
    "monitoraggio": "Termometro / abbattitore con grafico",
    "azione_correttiva": "Ridurre pezzatura; se > 4 h in zona rischio, scartare",
    "frequenza": "Ogni abbattimento",
}

_CCP_TRASPORTO: Ccp = {
    "codice": "CCP6",
    "nome": "Trasporto pasti",
    "fase": "Trasporto a destinazione",
    "pericolo": "Perdita del regime termico durante il trasporto",
    "limite_critico": "Pasti caldi >= 65 C, pasti freddi <= 10 C per tutto il trasporto",
    "monitoraggio": "Contenitori termici + data-logger",
    "azione_correttiva": "Rigenerazione in sede oppure scarto se violato",
    "frequenza": "Ogni trasporto",
}

_CCP_IGIENE_PERSONALE: Ccp = {
    "codice": "CCP7",
    "nome": "Igiene del personale",
    "fase": "Prima di ogni lavorazione",
    "pericolo": "Contaminazione crociata da mani / divise",
    "limite_critico": "Lavaggio mani + DPI (cuffia, camice pulito); niente gioielli",
    "monitoraggio": "Osservazione del responsabile HACCP",
    "azione_correttiva": "Formazione immediata; annotazione sulla scheda SA-14",
    "frequenza": "Continua",
}

_CCP_PULIZIA_SUPERFICI: Ccp = {
    "codice": "CCP8",
    "nome": "Pulizia e sanificazione superfici",
    "fase": "Fine turno / fine lavorazione",
    "pericolo": "Contaminazione residua da superfici non sanificate",
    "limite_critico": "Piano di sanificazione rispettato; residui ATP < 100 RLU sulle superfici critiche",
    "monitoraggio": "Check-list SA-11 + tampone ATP periodico",
    "azione_correttiva": "Ripetere sanificazione; verificare prodotti e dosaggi",
    "frequenza": "Fine turno + campionamento mensile",
}


_ACTIVITY_TYPES: list[ActivityType] = [
    {
        "slug": "ristorante_con_cucina",
        "nome": "Ristorante con cucina",
        "descrizione": "Cottura e somministrazione di pasti preparati in loco.",
        "ccps": [
            _CCP_RICEVIMENTO,
            _CCP_CONSERVAZIONE_FREDDA,
            _CCP_SCONGELAMENTO,
            _CCP_COTTURA,
            _CCP_ABBATTIMENTO,
            _CCP_IGIENE_PERSONALE,
            _CCP_PULIZIA_SUPERFICI,
        ],
    },
    {
        "slug": "bar_caffetteria",
        "nome": "Bar / caffetteria",
        "descrizione": "Bevande, snack e alimenti preconfezionati; cottura minima.",
        "ccps": [
            _CCP_RICEVIMENTO,
            _CCP_CONSERVAZIONE_FREDDA,
            _CCP_IGIENE_PERSONALE,
            _CCP_PULIZIA_SUPERFICI,
        ],
    },
    {
        "slug": "mensa_aziendale",
        "nome": "Mensa aziendale",
        "descrizione": "Produzione volumi medio-alti di pasti cotti + distribuzione interna.",
        "ccps": [
            _CCP_RICEVIMENTO,
            _CCP_CONSERVAZIONE_FREDDA,
            _CCP_SCONGELAMENTO,
            _CCP_COTTURA,
            _CCP_ABBATTIMENTO,
            _CCP_TRASPORTO,
            _CCP_IGIENE_PERSONALE,
            _CCP_PULIZIA_SUPERFICI,
        ],
    },
    {
        "slug": "gastronomia_take_away",
        "nome": "Gastronomia / take-away",
        "descrizione": "Pasti cotti destinati al consumo differito fuori sede.",
        "ccps": [
            _CCP_RICEVIMENTO,
            _CCP_CONSERVAZIONE_FREDDA,
            _CCP_COTTURA,
            _CCP_ABBATTIMENTO,
            _CCP_TRASPORTO,
            _CCP_IGIENE_PERSONALE,
            _CCP_PULIZIA_SUPERFICI,
        ],
    },
    {
        "slug": "panetteria_pasticceria",
        "nome": "Panetteria / pasticceria",
        "descrizione": "Prodotti da forno; conservazione creme e farciture refrigerate.",
        "ccps": [
            _CCP_RICEVIMENTO,
            _CCP_CONSERVAZIONE_FREDDA,
            _CCP_COTTURA,
            _CCP_IGIENE_PERSONALE,
            _CCP_PULIZIA_SUPERFICI,
        ],
    },
    {
        "slug": "pizzeria",
        "nome": "Pizzeria",
        "descrizione": "Cottura in forno, conservazione impasto e ingredienti refrigerati.",
        "ccps": [
            _CCP_RICEVIMENTO,
            _CCP_CONSERVAZIONE_FREDDA,
            _CCP_SCONGELAMENTO,
            _CCP_COTTURA,
            _CCP_IGIENE_PERSONALE,
            _CCP_PULIZIA_SUPERFICI,
        ],
    },
    {
        "slug": "catering",
        "nome": "Catering / banqueting",
        "descrizione": "Preparazione in sede + trasporto e rigenerazione presso terzi.",
        "ccps": [
            _CCP_RICEVIMENTO,
            _CCP_CONSERVAZIONE_FREDDA,
            _CCP_SCONGELAMENTO,
            _CCP_COTTURA,
            _CCP_ABBATTIMENTO,
            _CCP_TRASPORTO,
            _CCP_IGIENE_PERSONALE,
            _CCP_PULIZIA_SUPERFICI,
        ],
    },
    {
        "slug": "supermercato_retail",
        "nome": "Supermercato / retail alimentare",
        "descrizione": "Vendita al dettaglio di alimenti; focus su catena del freddo.",
        "ccps": [
            _CCP_RICEVIMENTO,
            _CCP_CONSERVAZIONE_FREDDA,
            _CCP_IGIENE_PERSONALE,
            _CCP_PULIZIA_SUPERFICI,
        ],
    },
]


_ACTIVITY_BY_SLUG: dict[str, ActivityType] = {
    at["slug"]: at for at in _ACTIVITY_TYPES
}


def list_activity_types() -> list[dict]:
    """Return catalog entries ready for JSON serialisation."""
    return [
        {
            "slug": at["slug"],
            "nome": at["nome"],
            "descrizione": at["descrizione"],
            "ccp_count": len(at["ccps"]),
        }
        for at in _ACTIVITY_TYPES
    ]


def get_activity_type(slug: str) -> ActivityType | None:
    return _ACTIVITY_BY_SLUG.get(slug)


def get_default_ccps(slug: str) -> list[dict]:
    """Return a deep-copy of the default CCPs for ``slug``.

    Callers persist the result onto ``HaccpConfig.ccps`` so the subsequent
    merge logic can compare operator edits against a known baseline.
    """
    at = _ACTIVITY_BY_SLUG.get(slug)
    if at is None:
        return []
    # Return copies so mutation by the caller never bleeds back into the
    # module-level constants.
    return [dict(c) for c in at["ccps"]]


def merge_ccps(
    existing: list[dict] | None, new_defaults: list[dict]
) -> tuple[list[dict], list[str]]:
    """Merge operator-customised CCPs into a fresh default set (AC3).

    Strategy:

      * For each default CCP, look up the same ``codice`` in ``existing``.
        If found and it diverges from the shipped default (the operator
        edited it), keep the customised row and record its ``codice`` in
        the returned ``preserved`` list so the UI can surface "N CCP
        personalizzati mantenuti".
      * CCPs present in ``existing`` with a ``codice`` that starts with
        ``"CUSTOM"`` or that is not in the new defaults are appended
        verbatim — operators can add activity-specific CCPs and they
        survive a regeneration.
      * CCPs in the defaults with no counterpart in ``existing`` are added
        fresh.
    """
    existing = existing or []
    existing_by_codice = {c.get("codice", ""): c for c in existing if c.get("codice")}
    default_codici = {c["codice"] for c in new_defaults}

    merged: list[dict] = []
    preserved: list[str] = []

    for default in new_defaults:
        codice = default["codice"]
        match = existing_by_codice.get(codice)
        if match is None:
            merged.append(dict(default))
            continue
        # Diff every field — if the operator touched anything, keep their row.
        if any(match.get(k) != default.get(k) for k in default.keys()):
            merged.append(dict(match))
            preserved.append(codice)
        else:
            merged.append(dict(default))

    # Append operator-added customs that aren't in the new defaults.
    for codice, row in existing_by_codice.items():
        if codice not in default_codici:
            merged.append(dict(row))

    return merged, preserved
