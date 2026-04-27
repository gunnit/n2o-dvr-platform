"""
Reference data for Italian workplace safety assessments.

Contains lookup tables, risk category definitions, environment types,
document type metadata, and NIOSH factor tables — all extracted from
N2O's completed template documents.
"""

# ---------------------------------------------------------------------------
# 11 Risk categories evaluated per work environment (SI/NO)
# ---------------------------------------------------------------------------

RISK_CATEGORIES: list[dict] = [
    {
        "numero": 1,
        "macro_categoria": "Rischi per la Sicurezza",
        "categoria": "Strutture",
        "field_key": "risk_structures",
    },
    {
        "numero": 2,
        "macro_categoria": "Rischi per la Sicurezza",
        "categoria": "Macchine",
        "field_key": "risk_machines",
    },
    {
        "numero": 3,
        "macro_categoria": "Rischi per la Sicurezza",
        "categoria": "Impianti Elettrici",
        "field_key": "risk_electrical",
    },
    {
        "numero": 4,
        "macro_categoria": "Rischi per la Sicurezza",
        "categoria": "Incendio-Esplosioni",
        "field_key": "risk_fire",
    },
    {
        "numero": 5,
        "macro_categoria": "Rischi per la Salute",
        "categoria": "Agenti Chimici",
        "field_key": "risk_chemical",
    },
    {
        "numero": 6,
        "macro_categoria": "Rischi per la Salute",
        "categoria": "Agenti Fisici",
        "field_key": "risk_physical",
    },
    {
        "numero": 7,
        "macro_categoria": "Rischi per la Salute",
        "categoria": "Agenti Biologici",
        "field_key": "risk_biological",
    },
    {
        "numero": 8,
        "macro_categoria": "Rischi per la Salute",
        "categoria": "Agenti Cancerogeni",
        "field_key": "risk_carcinogenic",
    },
    {
        "numero": 9,
        "macro_categoria": "Rischi Trasversali",
        "categoria": "Organizzazione del Lavoro",
        "field_key": "risk_work_org",
    },
    {
        "numero": 10,
        "macro_categoria": "Rischi Trasversali",
        "categoria": "Fattori Psicologici",
        "field_key": "risk_psychological",
    },
    {
        "numero": 11,
        "macro_categoria": "Rischi Trasversali",
        "categoria": "Fattori Ergonomici",
        "field_key": "risk_ergonomic",
    },
]

# Flat list of category names for quick access
RISK_CATEGORY_NAMES: list[str] = [rc["categoria"] for rc in RISK_CATEGORIES]

# ---------------------------------------------------------------------------
# Short ↔ long category name mapping
#
# The frontend wizard (step-rischi.tsx) and the DB persist SHORT names
# ("Elettrici", "Incendio", "Chimici", ...). The DVR template / hazard
# library / RISK_CATEGORIES schema uses LONG names ("Impianti Elettrici",
# "Incendio-Esplosioni", "Agenti Chimici", ...). Any code that crosses the
# DB → DVR generator boundary MUST normalize through these maps, otherwise
# the SI/NO checklist silently flags every category "NO" because the
# lookup keys don't match. Found by Phase 8.3 audit.
# ---------------------------------------------------------------------------

CATEGORIA_SHORT_TO_LONG: dict[str, str] = {
    "Strutture": "Strutture",
    "Macchine": "Macchine",
    "Elettrici": "Impianti Elettrici",
    "Incendio": "Incendio-Esplosioni",
    "Chimici": "Agenti Chimici",
    "Fisici": "Agenti Fisici",
    "Biologici": "Agenti Biologici",
    "Cancerogeni": "Agenti Cancerogeni",
    "Organizzazione": "Organizzazione del Lavoro",
    "Psicologici": "Fattori Psicologici",
    "Ergonomici": "Fattori Ergonomici",
}

CATEGORIA_LONG_TO_SHORT: dict[str, str] = {
    long: short for short, long in CATEGORIA_SHORT_TO_LONG.items()
}

RISK_CATEGORY_SHORT_NAMES: list[str] = list(CATEGORIA_SHORT_TO_LONG.keys())


def normalize_categoria_to_long(name: str | None) -> str | None:
    """Convert a short DB name to its canonical long form.

    Returns None if name is None/empty. Returns the input unchanged when
    it's already a long name (idempotent) or unrecognized — defensive so
    legacy rows that happen to have long names already don't get mangled.
    """
    if not name:
        return None
    stripped = name.strip()
    if stripped in CATEGORIA_SHORT_TO_LONG:
        return CATEGORIA_SHORT_TO_LONG[stripped]
    return stripped

# ---------------------------------------------------------------------------
# Environment types
# ---------------------------------------------------------------------------

ENVIRONMENT_TYPES: list[str] = [
    "Ufficio",
    "Magazzino",
    "Cucina",
    "Laboratorio",
    "Officina",
    "Sala Corsi",
    "Esterno",
    "Bagno/Spogliatoio",
]

# ---------------------------------------------------------------------------
# Document types with metadata
# ---------------------------------------------------------------------------

DOCUMENT_TYPES: dict[str, dict] = {
    "dvr_master": {
        "nome": "DVR - Documento di Valutazione dei Rischi",
        "abbreviazione": "DVR",
        "fase": 2,
        "complessita": "Alta",
        "template_disponibile": True,
    },
    "allegato_mmc": {
        "nome": "Allegato Rischio MMC - Movimentazione Manuale dei Carichi",
        "abbreviazione": "MMC",
        "fase": 3,
        "complessita": "Media",
        "template_disponibile": True,
    },
    "allegato_vdt": {
        "nome": "Allegato Rischio VDT - Videoterminali",
        "abbreviazione": "VDT",
        "fase": 3,
        "complessita": "Media",
        "template_disponibile": True,
    },
    "allegato_stress": {
        "nome": "Allegato Stress da Lavoro Correlato",
        "abbreviazione": "Stress",
        "fase": 3,
        "complessita": "Media",
        "template_disponibile": True,
    },
    "allegato_gestanti": {
        "nome": "Allegato Rischio Gestanti e Puerpere",
        "abbreviazione": "Gestanti",
        "fase": 3,
        "complessita": "Bassa",
        "template_disponibile": True,
    },
    "allegato_incendio": {
        "nome": "Allegato Rischio Incendio",
        "abbreviazione": "Incendio",
        "fase": 3,
        "complessita": "Media",
        "template_disponibile": True,
    },
    "allegato_microclima": {
        "nome": "Allegato Rischio Microclima",
        "abbreviazione": "Microclima",
        "fase": 3,
        "complessita": "Alta",
        "template_disponibile": False,
    },
    "pee": {
        "nome": "Piano di Emergenza ed Evacuazione",
        "abbreviazione": "PEE",
        "fase": 4,
        "complessita": "Media",
        "template_disponibile": True,
    },
    "haccp": {
        "nome": "HACCP - Manuale di Autocontrollo",
        "abbreviazione": "HACCP",
        "fase": 4,
        "complessita": "Media",
        "template_disponibile": True,
    },
    "duvri": {
        "nome": "DUVRI - Documento Unico Valutazione Rischi Interferenze",
        "abbreviazione": "DUVRI",
        "fase": 4,
        "complessita": "Bassa",
        "template_disponibile": True,
    },
    "pos": {
        "nome": "POS - Piano Operativo di Sicurezza",
        "abbreviazione": "POS",
        "fase": 4,
        "complessita": "Media",
        "template_disponibile": True,
    },
}

# ---------------------------------------------------------------------------
# NIOSH Factor lookup tables
# Extracted from ALLEGATO RISCHIO MMC.docx
# ---------------------------------------------------------------------------

# Factor A -- Fattore Altezza (Height Multiplier)
# Key: height from floor in cm, Value: multiplier
# Formula: A = 1 - (0.003 * |V - 75|), optimal at V=75 cm
NIOSH_FACTOR_A: dict[int, float] = {
    0: 0.78,
    25: 0.85,
    50: 0.93,
    75: 1.00,
    100: 0.93,
    125: 0.85,
    150: 0.78,
    175: 0.00,
}

# Factor B -- Fattore Dislocazione Verticale (Vertical Displacement)
# Key: vertical displacement in cm, Value: multiplier
# Formula: B = 0.82 + (4.5 / X)
NIOSH_FACTOR_B: dict[int, float] = {
    25: 1.00,
    30: 0.97,
    40: 0.93,
    50: 0.91,
    70: 0.88,
    100: 0.87,
    170: 0.85,
    175: 0.00,
}

# Factor C -- Fattore Orizzontale (Horizontal Distance)
# Key: horizontal distance in cm, Value: multiplier
# Formula: C = 25 / H
NIOSH_FACTOR_C: dict[int, float] = {
    25: 1.00,
    30: 0.83,
    40: 0.63,
    50: 0.50,
    55: 0.45,
    60: 0.42,
    63: 0.00,
}

# Factor D -- Fattore Dislocazione Angolare (Asymmetry)
# Key: angle of asymmetry in degrees, Value: multiplier
# Formula: D_factor = 1 - (0.0032 * y)
NIOSH_FACTOR_D: dict[int, float] = {
    0: 1.00,
    30: 0.90,
    60: 0.81,
    90: 0.71,
    120: 0.62,
    135: 0.57,
    180: 0.00,  # >135 degrees: factor is 0.00
}

# Factor E -- Fattore Presa (Grip Quality)
# Key: grip quality judgment, Value: multiplier
NIOSH_FACTOR_E: dict[str, float] = {
    "Buona": 1.00,
    "Sufficiente": 0.95,
    "Scarsa": 0.90,
}

# Factor F -- Fattore Frequenza (Frequency)
# Key: frequency in actions/minute
# Value: dict with duration keys (breve, media, lunga)
NIOSH_FACTOR_F: dict[float, dict[str, float]] = {
    0.2: {"breve": 1.00, "media": 0.95, "lunga": 0.85},
    0.5: {"breve": 0.97, "media": 0.92, "lunga": 0.81},
    1: {"breve": 0.94, "media": 0.88, "lunga": 0.75},
    2: {"breve": 0.91, "media": 0.84, "lunga": 0.65},
    3: {"breve": 0.88, "media": 0.79, "lunga": 0.55},
    4: {"breve": 0.84, "media": 0.72, "lunga": 0.45},
    5: {"breve": 0.80, "media": 0.60, "lunga": 0.35},
    6: {"breve": 0.75, "media": 0.50, "lunga": 0.27},
    7: {"breve": 0.70, "media": 0.42, "lunga": 0.22},
    8: {"breve": 0.60, "media": 0.35, "lunga": 0.18},
    9: {"breve": 0.52, "media": 0.30, "lunga": 0.15},
    10: {"breve": 0.45, "media": 0.26, "lunga": 0.13},
    11: {"breve": 0.41, "media": 0.23, "lunga": 0.00},
    12: {"breve": 0.37, "media": 0.21, "lunga": 0.00},
    13: {"breve": 0.34, "media": 0.00, "lunga": 0.00},
    14: {"breve": 0.31, "media": 0.00, "lunga": 0.00},
    15: {"breve": 0.28, "media": 0.00, "lunga": 0.00},
    16: {"breve": 0.00, "media": 0.00, "lunga": 0.00},  # >15
}

# CP -- Costante di Peso (Weight Constant)
NIOSH_CP: dict[str, dict[str, float]] = {
    ">18": {"maschi": 25.0, "femmine": 20.0},
    "15-18": {"maschi": 15.0, "femmine": 10.0},
}

# ---------------------------------------------------------------------------
# Standard Hazard Library (Fattori di Pericolo per categoria)
# Extracted from DVR RISCHIO MASTER.docx
# ---------------------------------------------------------------------------

HAZARD_LIBRARY: dict[str, list[str]] = {
    "Strutture": [
        "Altezza dell'Ambiente",
        "Superficie dell'Ambiente",
        "Volume dell'Ambiente",
        "Illuminazione (normale e in emergenza)",
        "Pavimenti (lisci o sconnessi)",
        "Pareti (semplici o attrezzate: scaffalatura, apparecchiatura)",
        "Viabilita interna, esterna; movimentazione manuale dei carichi",
        "Solai (stabilita)",
        "Soppalchi (destinazione, praticabilita, tenuta, portata)",
        "Botole (visibili e con chiusura a sicurezza)",
        "Uscite (in numero sufficiente in funzione del personale)",
        "Porte (in numero sufficiente in funzione del personale)",
        "Locali sotterranei (dimensioni, ricambi d'aria)",
    ],
    "Macchine": [
        "Protezione degli organi di avviamento",
        "Protezione degli organi di trasmissione",
        "Protezione degli organi di lavoro",
        "Protezione degli organi di comando",
        "Macchine con marchio CE",
        "Macchine rispondenti ai requisiti di sicurezza",
        "Protezione nell'uso di apparecchi di sollevamento",
        "Protezione nell'uso di ascensori e montacarchi",
        "Protezione nell'uso di apparecchi a pressione (bombole e circuiti)",
        "Protezione nell'accesso a vasche, serbatoi e simili",
    ],
    "Impianti Elettrici": [
        "Idoneita del progetto",
        "Idoneita d'uso",
        "Impianti a sicurezza intrinseca in atmosfere a rischio di incendio o di esplosione",
        "Impianti speciali a carattere di ridondanza",
    ],
    "Incendio-Esplosioni": [
        "Presenza di materiali infiammabili d'uso",
        "Presenza di armadi di conservazione (caratteristiche strutturali e di aerazione)",
        "Presenza di depositi di materiali infiammabili (caratteristiche strutturali e di ricambi d'aria)",
        "Carenza di sistemi antincendio",
        "Carenza di segnaletica di sicurezza",
    ],
    "Agenti Chimici": [
        "Rischi di esposizione connessi con l'impiego di sostanze chimiche, tossiche o nocive "
        "(ingestione, contatto cutaneo, inalazione — polveri, fumi, nebbie, gas, vapori)",
    ],
    "Agenti Fisici": [
        "Rumore",
        "Vibrazioni",
        "Radiazioni non ionizzanti",
        "Microclima (temperatura, umidita relativa, ventilazione, calore radiante, condizionamento)",
        "Illuminazione (livelli di illuminamento ambientale e dei posti di lavoro)",
        "VDT (posizionamento, illuminotecnica, postura, microclima)",
        "Radiazioni ionizzanti",
    ],
    "Agenti Biologici": [
        "Emissione involontaria (impianto di condizionamento, polveri organiche)",
        "Emissione incontrollata (impianti depurazione acque, materiali infetti, rifiuti)",
        "Trattamento o manipolazione volontaria (biotecnologie)",
    ],
    "Agenti Cancerogeni": [
        "Materie prime nel ciclo produttivo",
        "Materie ausiliarie nel ciclo produttivo",
        "Trattamento o manipolazione volontaria nel ciclo produttivo",
        "Emissione incontrollata da componenti strutturali (es. amianto)",
        "Emissione incontrollata da componenti impiantistiche (es. PCB)",
    ],
    "Organizzazione del Lavoro": [
        "Processi di lavoro usuranti: lavori in continuo, sistemi di turni, lavoro notturno",
        "Pianificazione degli aspetti attinenti alla sicurezza e la salute",
        "Manutenzione degli impianti, comprese le attrezzature di sicurezza",
        "Procedure adeguate per far fronte a incidenti e situazioni di emergenza",
        "Movimentazione manuale dei carichi",
        "Lavoro ai VDT (Data Entry)",
    ],
    "Fattori Psicologici": [
        "Intensita, monotonia, solitudine, ripetitivita del lavoro",
        "Carenze di contributo al processo decisionale e situazioni di conflittualita",
        "Complessita delle mansioni e carenza di controllo",
        "Reattivita anomala a condizioni di emergenza",
    ],
    "Fattori Ergonomici": [
        "Fattori Ergonomici",
        "Sistemi di sicurezza e affidabilita delle informazioni",
        "Conoscenze e capacita del personale",
        "Norme di comportamento",
        "Soddisfacente comunicazione e istruzioni corrette in condizioni variabili",
    ],
}

# ---------------------------------------------------------------------------
# Default risk applicability per environment type
# Maps environment type -> which risk categories are typically applicable (SI)
# ---------------------------------------------------------------------------

_DEFAULT_APPLICABLE_RISKS: dict[str, list[str]] = {
    "Ufficio": [
        "Strutture",
        "Impianti Elettrici",
        "Incendio-Esplosioni",
        "Agenti Fisici",
        "Organizzazione del Lavoro",
        "Fattori Psicologici",
        "Fattori Ergonomici",
    ],
    "Magazzino": [
        "Strutture",
        "Macchine",
        "Impianti Elettrici",
        "Incendio-Esplosioni",
        "Agenti Chimici",
        "Agenti Fisici",
        "Organizzazione del Lavoro",
        "Fattori Ergonomici",
    ],
    "Cucina": [
        "Strutture",
        "Macchine",
        "Impianti Elettrici",
        "Incendio-Esplosioni",
        "Agenti Chimici",
        "Agenti Fisici",
        "Agenti Biologici",
        "Organizzazione del Lavoro",
        "Fattori Ergonomici",
    ],
    "Laboratorio": [
        "Strutture",
        "Macchine",
        "Impianti Elettrici",
        "Incendio-Esplosioni",
        "Agenti Chimici",
        "Agenti Fisici",
        "Agenti Biologici",
        "Agenti Cancerogeni",
        "Organizzazione del Lavoro",
        "Fattori Ergonomici",
    ],
    "Officina": [
        "Strutture",
        "Macchine",
        "Impianti Elettrici",
        "Incendio-Esplosioni",
        "Agenti Chimici",
        "Agenti Fisici",
        "Organizzazione del Lavoro",
        "Fattori Ergonomici",
    ],
    "Sala Corsi": [
        "Strutture",
        "Impianti Elettrici",
        "Incendio-Esplosioni",
        "Agenti Fisici",
        "Organizzazione del Lavoro",
        "Fattori Psicologici",
        "Fattori Ergonomici",
    ],
    "Esterno": [
        "Strutture",
        "Macchine",
        "Incendio-Esplosioni",
        "Agenti Chimici",
        "Agenti Fisici",
        "Agenti Biologici",
        "Organizzazione del Lavoro",
        "Fattori Ergonomici",
    ],
    "Bagno/Spogliatoio": [
        "Strutture",
        "Impianti Elettrici",
        "Agenti Biologici",
    ],
}

# Default P and D values per risk category (conservative defaults)
_DEFAULT_PD: dict[str, tuple[int, int]] = {
    "Strutture": (1, 2),
    "Macchine": (1, 3),
    "Impianti Elettrici": (1, 3),
    "Incendio-Esplosioni": (1, 3),
    "Agenti Chimici": (1, 2),
    "Agenti Fisici": (1, 2),
    "Agenti Biologici": (1, 2),
    "Agenti Cancerogeni": (1, 4),
    "Organizzazione del Lavoro": (1, 1),
    "Fattori Psicologici": (1, 1),
    "Fattori Ergonomici": (1, 2),
}


def get_risks_for_environment(env_type: str) -> list[dict]:
    """Return default risk items for a given environment type.

    Each item includes the risk category, whether it is applicable by default,
    and the standard hazard items from the hazard library.

    Args:
        env_type: One of the ENVIRONMENT_TYPES values.

    Returns:
        List of dicts, one per risk category, each with keys:
            - categoria: risk category name
            - macro_categoria: parent category grouping
            - field_key: database field key
            - applicabile: whether this risk is typically applicable
            - pericoli: list of standard hazard items for the category
            - default_p: default probability value
            - default_d: default damage value
    """
    applicable = _DEFAULT_APPLICABLE_RISKS.get(env_type, [])

    results = []
    for rc in RISK_CATEGORIES:
        cat_name = rc["categoria"]
        is_applicable = cat_name in applicable
        p_default, d_default = _DEFAULT_PD.get(cat_name, (1, 1))

        results.append({
            "categoria": cat_name,
            "macro_categoria": rc["macro_categoria"],
            "field_key": rc["field_key"],
            "applicabile": is_applicable,
            "pericoli": HAZARD_LIBRARY.get(cat_name, []),
            "default_p": p_default,
            "default_d": d_default,
        })

    return results


def get_default_pd(categoria: str) -> tuple[int, int]:
    """Return the default Probability (P) and Damage (D) for a risk category.

    Args:
        categoria: Risk category name (must match one of RISK_CATEGORY_NAMES).

    Returns:
        Tuple of (P, D) integers.

    Raises:
        ValueError: If the category is not recognized.
    """
    if categoria not in _DEFAULT_PD:
        raise ValueError(
            f"Unknown risk category: '{categoria}'. "
            f"Valid categories: {RISK_CATEGORY_NAMES}"
        )
    return _DEFAULT_PD[categoria]


# ---------------------------------------------------------------------------
# Default risk scoring matrix (US-2.3)
# Maps (ambiente_tipo, categoria_rischio) -> (p_default, d_default).
# Keys use the short category names exposed in the survey wizard
# (Strutture, Macchine, Elettrici, Incendio, Chimici, Fisici, Biologici,
# Cancerogeni, Organizzazione, Psicologici, Ergonomici) and the lowercase
# environment tipo values ("ufficio", "magazzino", "produzione", "cucina",
# "laboratorio", "esterno", "negozio", "altro"). This shape is intentionally
# mirrored in the frontend (step-rischi.tsx) as a static lookup.
# Values reflect conservative Italian-safety-consultant defaults: offices low
# (P=1, D=1-2), kitchens/production medium (P=2, D=2), hazardous categories
# in risky environments higher (P=2, D=3).
# ---------------------------------------------------------------------------

DEFAULT_RISK_CATEGORIES: list[str] = [
    "Strutture",
    "Macchine",
    "Elettrici",
    "Incendio",
    "Chimici",
    "Fisici",
    "Biologici",
    "Cancerogeni",
    "Organizzazione",
    "Psicologici",
    "Ergonomici",
]

DEFAULT_ENVIRONMENT_TIPI: list[str] = [
    "ufficio",
    "magazzino",
    "produzione",
    "officina",
    "cucina",
    "laboratorio",
    "esterno",
    "negozio",
    "altro",
]

DEFAULT_RISK_SCORES: dict[tuple[str, str], tuple[int, int]] = {
    # Ufficio -- low-risk indoor environment
    ("ufficio", "Strutture"): (1, 2),
    ("ufficio", "Macchine"): (1, 1),
    ("ufficio", "Elettrici"): (1, 2),
    ("ufficio", "Incendio"): (1, 2),
    ("ufficio", "Chimici"): (1, 1),
    ("ufficio", "Fisici"): (1, 2),
    ("ufficio", "Biologici"): (1, 1),
    ("ufficio", "Cancerogeni"): (1, 1),
    ("ufficio", "Organizzazione"): (1, 1),
    ("ufficio", "Psicologici"): (2, 2),
    ("ufficio", "Ergonomici"): (2, 2),
    # Magazzino -- storage, manual handling, forklifts
    ("magazzino", "Strutture"): (2, 2),
    ("magazzino", "Macchine"): (2, 3),
    ("magazzino", "Elettrici"): (1, 2),
    ("magazzino", "Incendio"): (2, 3),
    ("magazzino", "Chimici"): (1, 2),
    ("magazzino", "Fisici"): (2, 2),
    ("magazzino", "Biologici"): (1, 1),
    ("magazzino", "Cancerogeni"): (1, 1),
    ("magazzino", "Organizzazione"): (2, 2),
    ("magazzino", "Psicologici"): (1, 1),
    ("magazzino", "Ergonomici"): (2, 3),
    # Produzione -- manufacturing floor
    ("produzione", "Strutture"): (2, 2),
    ("produzione", "Macchine"): (2, 3),
    ("produzione", "Elettrici"): (2, 3),
    ("produzione", "Incendio"): (2, 3),
    ("produzione", "Chimici"): (2, 3),
    ("produzione", "Fisici"): (2, 3),
    ("produzione", "Biologici"): (1, 2),
    ("produzione", "Cancerogeni"): (1, 3),
    ("produzione", "Organizzazione"): (2, 2),
    ("produzione", "Psicologici"): (1, 2),
    ("produzione", "Ergonomici"): (2, 3),
    # Officina -- mechanical workshop (L2 fix — was defaulting to "altro"
    # so every category rendered Accettabile, which is unrealistic).
    ("officina", "Strutture"): (2, 2),
    ("officina", "Macchine"): (2, 3),
    ("officina", "Elettrici"): (2, 3),
    ("officina", "Incendio"): (2, 3),
    ("officina", "Chimici"): (2, 2),
    ("officina", "Fisici"): (2, 3),
    ("officina", "Biologici"): (1, 1),
    ("officina", "Cancerogeni"): (1, 2),
    ("officina", "Organizzazione"): (2, 2),
    ("officina", "Psicologici"): (1, 2),
    ("officina", "Ergonomici"): (2, 3),
    # Cucina -- food preparation
    ("cucina", "Strutture"): (2, 2),
    ("cucina", "Macchine"): (2, 2),
    ("cucina", "Elettrici"): (2, 2),
    ("cucina", "Incendio"): (2, 3),
    ("cucina", "Chimici"): (2, 2),
    ("cucina", "Fisici"): (2, 2),
    ("cucina", "Biologici"): (2, 2),
    ("cucina", "Cancerogeni"): (1, 1),
    ("cucina", "Organizzazione"): (2, 2),
    ("cucina", "Psicologici"): (2, 2),
    ("cucina", "Ergonomici"): (2, 2),
    # Laboratorio -- chemical/biological lab work
    ("laboratorio", "Strutture"): (2, 2),
    ("laboratorio", "Macchine"): (2, 3),
    ("laboratorio", "Elettrici"): (2, 3),
    ("laboratorio", "Incendio"): (2, 3),
    ("laboratorio", "Chimici"): (2, 3),
    ("laboratorio", "Fisici"): (2, 2),
    ("laboratorio", "Biologici"): (2, 3),
    ("laboratorio", "Cancerogeni"): (2, 3),
    ("laboratorio", "Organizzazione"): (2, 2),
    ("laboratorio", "Psicologici"): (1, 2),
    ("laboratorio", "Ergonomici"): (2, 2),
    # Esterno -- outdoor work
    ("esterno", "Strutture"): (2, 2),
    ("esterno", "Macchine"): (1, 2),
    ("esterno", "Elettrici"): (1, 2),
    ("esterno", "Incendio"): (2, 2),
    ("esterno", "Chimici"): (1, 1),
    ("esterno", "Fisici"): (2, 3),
    ("esterno", "Biologici"): (1, 2),
    ("esterno", "Cancerogeni"): (1, 1),
    ("esterno", "Organizzazione"): (2, 2),
    ("esterno", "Psicologici"): (1, 1),
    ("esterno", "Ergonomici"): (2, 3),
    # Negozio -- retail shop
    ("negozio", "Strutture"): (1, 2),
    ("negozio", "Macchine"): (1, 1),
    ("negozio", "Elettrici"): (1, 2),
    ("negozio", "Incendio"): (2, 2),
    ("negozio", "Chimici"): (1, 1),
    ("negozio", "Fisici"): (1, 2),
    ("negozio", "Biologici"): (1, 1),
    ("negozio", "Cancerogeni"): (1, 1),
    ("negozio", "Organizzazione"): (1, 2),
    ("negozio", "Psicologici"): (1, 2),
    ("negozio", "Ergonomici"): (2, 2),
    # Altro -- generic fallback
    ("altro", "Strutture"): (1, 2),
    ("altro", "Macchine"): (1, 2),
    ("altro", "Elettrici"): (1, 2),
    ("altro", "Incendio"): (1, 2),
    ("altro", "Chimici"): (1, 2),
    ("altro", "Fisici"): (1, 2),
    ("altro", "Biologici"): (1, 2),
    ("altro", "Cancerogeni"): (1, 2),
    ("altro", "Organizzazione"): (1, 2),
    ("altro", "Psicologici"): (1, 2),
    ("altro", "Ergonomici"): (1, 2),
}


def get_default_scores(
    ambiente_tipo: str, categoria: str
) -> tuple[int, int]:
    """Return default (P, D) scores for a given environment tipo and category.

    Looks up the DEFAULT_RISK_SCORES matrix by the lowercase ambiente tipo
    and short risk category name. Falls back to (1, 1) for unknown pairs
    so callers always receive a valid low-risk baseline.

    Args:
        ambiente_tipo: Environment tipo (e.g. "ufficio", "magazzino").
        categoria: Short risk category name (e.g. "Strutture", "Macchine").

    Returns:
        Tuple of (P, D) integers. Defaults to (1, 1) on miss.
    """
    key = (ambiente_tipo.lower() if isinstance(ambiente_tipo, str) else "", categoria)
    return DEFAULT_RISK_SCORES.get(key, (1, 1))


def get_default_risk_matrix() -> dict[tuple[str, str], tuple[int, int]]:
    """Return the full default risk scoring matrix.

    Exposes the lookup table as a plain dict so callers (or a future API
    endpoint) can serialize it for the frontend if needed. The frontend
    currently embeds the same shape client-side to avoid a runtime fetch.
    """
    return dict(DEFAULT_RISK_SCORES)


# ---------------------------------------------------------------------------
# DPI (Dispositivi di Protezione Individuale) catalog — per-mansione
#
# Source: elenco DPI fornito da N2O (Luca Marchetti) il 2026-04. Questo
# catalogo e' pensato per la scheda di valutazione in campo: l'operatore
# "flagra" i DPI in uso per ciascuna mansione, il Medico del Lavoro usa
# il risultato per tarare il protocollo delle visite mediche.
#
# Differente da `services.dpi_rules.DPI_CATALOG` che e' molto piu' ristretto
# (10 voci con codici EN) e riservato al motore DPI x fase del POS (US-4.8).
# I due cataloghi convivono perche' servono casi d'uso diversi; nessuna
# logica condivisa. Se in futuro si vogliono unificare, mappare i codici EN
# del POS dentro questo superset.
# ---------------------------------------------------------------------------

# Body area groups — canonical order for UI rendering
DPI_BODY_AREAS: list[str] = [
    "Testa",
    "Vista",
    "Viso",
    "Udito",
    "Vie Respiratorie",
    "Mani",
    "Piedi",
    "Corpo",
    "Anticaduta",
]

# Catalog items: code -> {etichetta, area}
# Codes are stable slugs (snake_case, no accents, no spaces). Labels are the
# Italian strings Luca sent verbatim (only light punctuation tweaks for
# consistency). Never rename a code in place — add a new one and deprecate.
DPI_CATALOG: dict[str, dict[str, str]] = {
    # Testa
    "caschi_industria": {
        "etichetta": "Caschi di protezione per l'industria",
        "area": "Testa",
    },
    "copricapo_leggero": {
        "etichetta": "Copricapo leggero per proteggere il cuoio capelluto",
        "area": "Testa",
    },
    "copricapo_protezione": {
        "etichetta": "Copricapo di protezione",
        "area": "Testa",
    },
    # Vista
    "occhiali_stanghette": {
        "etichetta": "Occhiali a stanghette",
        "area": "Vista",
    },
    "occhiali_maschera": {
        "etichetta": "Occhiali a maschera",
        "area": "Vista",
    },
    "occhiali_raggi": {
        "etichetta": (
            "Occhiali di protezione contro raggi X, laser, UV, IR e visibili"
        ),
        "area": "Vista",
    },
    "occhiali_uv": {
        "etichetta": "Occhiali protettivi UV",
        "area": "Vista",
    },
    # Viso
    "schermo_facciale": {
        "etichetta": "Schermi facciali",
        "area": "Viso",
    },
    "visiera_protettiva": {
        "etichetta": "Visiera protettiva",
        "area": "Viso",
    },
    "maschera_saldatura_arco": {
        "etichetta": "Maschera e caschi per saldatura ad arco",
        "area": "Viso",
    },
    "maschera_saldatura_cristalli_liquidi": {
        "etichetta": "Maschera per saldatrice con cristalli liquidi",
        "area": "Viso",
    },
    "maschera_taglio_ferrite_filtri": {
        "etichetta": "Maschera per taglio ferrite con filtri",
        "area": "Viso",
    },
    # Udito
    "cuffie_antirumore": {
        "etichetta": "Cuffie antirumore",
        "area": "Udito",
    },
    "cuffie_insonorizzate": {
        "etichetta": "Cuffie insonorizzate",
        "area": "Udito",
    },
    "otoprotettori": {
        "etichetta": "Otoprotettori",
        "area": "Udito",
    },
    # Vie Respiratorie
    "mascherina_tnt_igienica": {
        "etichetta": "Mascherina filtrante igienica in TNT",
        "area": "Vie Respiratorie",
    },
    "mascherina_chirurgica": {
        "etichetta": "Mascherina chirurgica",
        "area": "Vie Respiratorie",
    },
    "mascherina_ffp2_ffp3": {
        "etichetta": "Mascherina antipolvere FFP2/FFP3",
        "area": "Vie Respiratorie",
    },
    "mascherina_carboni_attivi": {
        "etichetta": "Mascherina ai carboni attivi",
        "area": "Vie Respiratorie",
    },
    "mascherina_polvere_verniciatura": {
        "etichetta": "Mascherina di protezione da polvere di verniciatura",
        "area": "Vie Respiratorie",
    },
    "maschera_verniciatura_ffa1p2": {
        "etichetta": "Maschera per verniciatura FFA1P2",
        "area": "Vie Respiratorie",
    },
    "maschera_pieno_facciale_filtro": {
        "etichetta": "Maschera a pieno facciale con filtro",
        "area": "Vie Respiratorie",
    },
    "maschera_pieno_facciale_aria": {
        "etichetta": "Maschera a pieno facciale con aria respirabile",
        "area": "Vie Respiratorie",
    },
    "respiratore_saldatura_amovibile": {
        "etichetta": "Apparecchi respiratori con maschera per saldatura amovibile",
        "area": "Vie Respiratorie",
    },
    # Mani
    "guanti_pvc": {
        "etichetta": "Guanti in PVC",
        "area": "Mani",
    },
    "guanti_lattice": {
        "etichetta": "Guanti in lattice",
        "area": "Mani",
    },
    "guanti_vinile": {
        "etichetta": "Guanti in vinile",
        "area": "Mani",
    },
    "guanti_nitrile": {
        "etichetta": "Guanti in nitrile",
        "area": "Mani",
    },
    "guanti_maglia_acciaio": {
        "etichetta": "Guanti in maglia d'acciaio",
        "area": "Mani",
    },
    "guanti_anticalore": {
        "etichetta": "Guanti anticalore",
        "area": "Mani",
    },
    "guanti_antitermici": {
        "etichetta": "Guanti antitermici",
        "area": "Mani",
    },
    "guanti_meccanici": {
        "etichetta": "Guanti contro le aggressioni meccaniche",
        "area": "Mani",
    },
    "guanti_chimici": {
        "etichetta": "Guanti contro le aggressioni chimiche",
        "area": "Mani",
    },
    "guanti_isolanti_elettrici": {
        "etichetta": "Guanti isolanti per elettricisti",
        "area": "Mani",
    },
    "guanti_antitaglio_affettatrice": {
        "etichetta": "Guanti antitaglio per affettatrice",
        "area": "Mani",
    },
    "guanti_lavaggio_verniciatura": {
        "etichetta": "Guanti per lavaggio verniciatura",
        "area": "Mani",
    },
    "guanti_mezze_dita": {
        "etichetta": "Guanti a mezze dita",
        "area": "Mani",
    },
    "ditali": {
        "etichetta": "Ditali",
        "area": "Mani",
    },
    "manicotti": {
        "etichetta": "Manicotti",
        "area": "Mani",
    },
    # Piedi
    "scarpe_antisdrucciolevole": {
        "etichetta": "Scarpe con suola antisdrucciolevole",
        "area": "Piedi",
    },
    "scarpe_basse": {
        "etichetta": "Scarpe basse",
        "area": "Piedi",
    },
    "scarpe_punta_rinforzata": {
        "etichetta": "Scarpe con protezione supplementare della punta del piede",
        "area": "Piedi",
    },
    "scarpe_sganciamento_rapido": {
        "etichetta": "Scarpe a sganciamento rapido",
        "area": "Piedi",
    },
    "stivali_sicurezza": {
        "etichetta": "Stivali di sicurezza",
        "area": "Piedi",
    },
    "zoccolo_sanitario": {
        "etichetta": "Zoccolo sanitario ad uso professionale",
        "area": "Piedi",
    },
    # Corpo
    "abbigliamento_da_lavoro": {
        "etichetta": "Abbigliamento da lavoro",
        "area": "Corpo",
    },
    "camice_da_lavoro": {
        "etichetta": "Camice da lavoro",
        "area": "Corpo",
    },
    "grembiuli_divisa": {
        "etichetta": "Grembiuli e divisa",
        "area": "Corpo",
    },
    "indumenti_due_pezzi": {
        "etichetta": "Indumenti di lavoro a due pezzi",
        "area": "Corpo",
    },
    "tuta_monouso": {
        "etichetta": "Tuta intera da lavoro monouso",
        "area": "Corpo",
    },
    "copri_barba_alimentare": {
        "etichetta": "Copribarba per uso alimentare",
        "area": "Corpo",
    },
    "grembiule_cerato": {
        "etichetta": "Grembiule di lavoro cerato",
        "area": "Corpo",
    },
    "grembiuli_meccanici": {
        "etichetta": "Grembiuli contro le aggressioni meccaniche",
        "area": "Corpo",
    },
    "grembiuli_chimici": {
        "etichetta": "Grembiuli contro le aggressioni chimiche",
        "area": "Corpo",
    },
    "indumenti_meccanici": {
        "etichetta": "Indumenti di protezione contro le aggressioni meccaniche",
        "area": "Corpo",
    },
    "indumenti_chimici": {
        "etichetta": "Indumenti di protezione contro le aggressioni chimiche",
        "area": "Corpo",
    },
    "indumenti_calore": {
        "etichetta": "Indumenti di protezione contro il calore",
        "area": "Corpo",
    },
    "indumenti_freddo": {
        "etichetta": "Indumenti di protezione contro il freddo",
        "area": "Corpo",
    },
    "indumenti_radioattiva": {
        "etichetta": "Indumenti di protezione contro la contaminazione radioattiva",
        "area": "Corpo",
    },
    "indumenti_antipolvere": {
        "etichetta": "Indumenti antipolvere",
        "area": "Corpo",
    },
    "indumenti_antigas": {
        "etichetta": "Indumenti antigas",
        "area": "Corpo",
    },
    "indumenti_fluorescenti": {
        "etichetta": (
            "Indumenti e accessori fluorescenti di segnalazione, catarifrangenti"
        ),
        "area": "Corpo",
    },
    "giubbotti_termici": {
        "etichetta": "Giubbotti termici",
        "area": "Corpo",
    },
    "abbigliamento_arco_elettrico": {
        "etichetta": "Abbigliamento protettivo arco elettrico",
        "area": "Corpo",
    },
    "abiti_anti_impigliamento": {
        "etichetta": "Abiti anti-impigliamento",
        "area": "Corpo",
    },
    "maniche_isolanti": {
        "etichetta": "Maniche isolanti",
        "area": "Corpo",
    },
    "ginocchiere": {
        "etichetta": "Ginocchiere",
        "area": "Corpo",
    },
    "creme_protettive": {
        "etichetta": "Creme protettive",
        "area": "Corpo",
    },
    # Anticaduta
    "cintura_sicurezza_tronco": {
        "etichetta": "Cintura di sicurezza del tronco",
        "area": "Anticaduta",
    },
    "imbracatura_sicurezza": {
        "etichetta": "Dispositivo di sostegno del corpo (imbracatura di sicurezza)",
        "area": "Anticaduta",
    },
    "attrezzature_cadute": {
        "etichetta": "Attrezzature di protezione contro le cadute",
        "area": "Anticaduta",
    },
}


def get_dpi_catalog_grouped() -> list[dict]:
    """Return DPI catalog grouped by body area, in canonical order.

    Shape: ``[{area: "Testa", items: [{code, etichetta}, ...]}, ...]``.
    Used by the ``/lookup/dpi-catalog`` endpoint so the frontend can
    render one section per body area without having to re-group.
    """
    by_area: dict[str, list[dict]] = {a: [] for a in DPI_BODY_AREAS}
    for code, meta in DPI_CATALOG.items():
        area = meta["area"]
        if area not in by_area:
            by_area[area] = []
        by_area[area].append({"code": code, "etichetta": meta["etichetta"]})
    return [
        {"area": area, "items": by_area[area]}
        for area in DPI_BODY_AREAS
        if by_area.get(area)
    ]


# ---------------------------------------------------------------------------
# Rischi Specifici D.Lgs. 81/08 — per-mansione
#
# Source: elenco "RISCHI D.LGS. 81\08" fornito da N2O (Luca Marchetti) il
# 2026-04. Questi sono rischi specifici (piu' granulari delle 11 macro
# categorie di RISK_CATEGORIES) che l'operatore flagra per mansione per
# abilitare il Medico del Lavoro a definire il protocollo delle visite.
#
# NB: sono complementari ai rischi generali per ambiente (ValutazioneRischio,
# step Rischi del wizard) — non sostituiscono quelli. Qui si traccia "questa
# mansione e' esposta al rumore", nel wizard Rischi si quantifica P/D per
# ambiente.
# ---------------------------------------------------------------------------

RISCHI_SPECIFICI_MACRO: list[str] = [
    "Ambienti e Luoghi",
    "Attrezzature e Impianti",
    "Incendio ed Esplosione",
    "Agenti Fisici",
    "Agenti Chimici e Biologici",
    "Organizzazione e Fattori Umani",
    "Movimentazione e Posture",
    "Lavori in Quota e Veicoli",
]

RISCHI_SPECIFICI_CATALOG: dict[str, dict[str, str]] = {
    # Ambienti e Luoghi
    "luoghi_lavoro_strutture": {
        "etichetta": "Luoghi di lavoro e Strutture",
        "macro": "Ambienti e Luoghi",
    },
    "spazi_confinati": {
        "etichetta": "Lavori in spazi confinati o sospetti di inquinamento",
        "macro": "Ambienti e Luoghi",
    },
    "atmosfere_esplosive": {
        "etichetta": "Atmosfere esplosive (ATEX)",
        "macro": "Ambienti e Luoghi",
    },
    "lavoro_difficile": {
        "etichetta": "Condizione di lavoro difficile",
        "macro": "Ambienti e Luoghi",
    },
    # Attrezzature e Impianti
    "utilizzo_attrezzature": {
        "etichetta": "Utilizzo di attrezzature di lavoro",
        "macro": "Attrezzature e Impianti",
    },
    "utilizzo_dpi": {
        "etichetta": "Utilizzo di dispositivi di protezione individuale",
        "macro": "Attrezzature e Impianti",
    },
    "apparecchiature_elettriche": {
        "etichetta": "Utilizzo di apparecchiature elettriche",
        "macro": "Attrezzature e Impianti",
    },
    "impianti_elettrici_elettrocuzione": {
        "etichetta": "Impianti elettrici ed elettrocuzione",
        "macro": "Attrezzature e Impianti",
    },
    # Incendio
    "incendio_esplosioni": {
        "etichetta": "Possibile insorgenza di incendi ed esplosioni",
        "macro": "Incendio ed Esplosione",
    },
    # Agenti Fisici
    "af_microclima": {
        "etichetta": "Agenti fisici - Microclima",
        "macro": "Agenti Fisici",
    },
    "af_rumore": {
        "etichetta": "Agenti fisici - Rumore",
        "macro": "Agenti Fisici",
    },
    "af_vibrazioni": {
        "etichetta": "Agenti fisici - Vibrazioni",
        "macro": "Agenti Fisici",
    },
    "af_campi_em": {
        "etichetta": "Agenti fisici - Campi elettromagnetici",
        "macro": "Agenti Fisici",
    },
    "af_radiazioni_ottiche": {
        "etichetta": "Agenti fisici - Radiazioni ottiche artificiali",
        "macro": "Agenti Fisici",
    },
    # Chimici e Biologici
    "agenti_chimici": {
        "etichetta": "Agenti chimici",
        "macro": "Agenti Chimici e Biologici",
    },
    "cancerogeni_mutageni": {
        "etichetta": "Agenti cancerogeni e mutageni",
        "macro": "Agenti Chimici e Biologici",
    },
    "amianto": {
        "etichetta": "Esposizione ad amianto",
        "macro": "Agenti Chimici e Biologici",
    },
    "agenti_biologici": {
        "etichetta": "Agenti biologici",
        "macro": "Agenti Chimici e Biologici",
    },
    # Organizzazione e Fattori Umani
    "organizzazione_lavoro": {
        "etichetta": "Organizzazione del lavoro",
        "macro": "Organizzazione e Fattori Umani",
    },
    "psicologici": {
        "etichetta": "Fattori psicologici",
        "macro": "Organizzazione e Fattori Umani",
    },
    "ergonomici": {
        "etichetta": "Fattori ergonomici",
        "macro": "Organizzazione e Fattori Umani",
    },
    # Movimentazione e Posture
    "mmc": {
        "etichetta": "Movimentazione manuale dei carichi (MMC)",
        "macro": "Movimentazione e Posture",
    },
    "vdt": {
        "etichetta": "Lavori ai videoterminali (VDT)",
        "macro": "Movimentazione e Posture",
    },
    # Lavori in Quota e Veicoli
    "lavori_quota": {
        "etichetta": "Lavori in quota",
        "macro": "Lavori in Quota e Veicoli",
    },
    "carrello_elevatore": {
        "etichetta": "Utilizzo carrello elevatore",
        "macro": "Lavori in Quota e Veicoli",
    },
    "ple": {
        "etichetta": "Utilizzo piattaforma di lavoro elevabile (PLE)",
        "macro": "Lavori in Quota e Veicoli",
    },
    "gru": {
        "etichetta": "Utilizzo gru",
        "macro": "Lavori in Quota e Veicoli",
    },
    "ruspa_escavatore": {
        "etichetta": "Utilizzo ruspa / escavatore",
        "macro": "Lavori in Quota e Veicoli",
    },
    "guida_automezzi_cde": {
        "etichetta": "Guida automezzi (patente C-D-E)",
        "macro": "Lavori in Quota e Veicoli",
    },
    "adr": {
        "etichetta": "Trasporto ADR (merci pericolose)",
        "macro": "Lavori in Quota e Veicoli",
    },
}


def get_rischi_specifici_catalog_grouped() -> list[dict]:
    """Return rischi specifici grouped by macro, in canonical order.

    Shape: ``[{macro: "Agenti Fisici", items: [{code, etichetta}, ...]}, ...]``.
    Mirrors ``get_dpi_catalog_grouped`` so the frontend can render both
    with the same component.
    """
    by_macro: dict[str, list[dict]] = {m: [] for m in RISCHI_SPECIFICI_MACRO}
    for code, meta in RISCHI_SPECIFICI_CATALOG.items():
        macro = meta["macro"]
        if macro not in by_macro:
            by_macro[macro] = []
        by_macro[macro].append({"code": code, "etichetta": meta["etichetta"]})
    return [
        {"macro": macro, "items": by_macro[macro]}
        for macro in RISCHI_SPECIFICI_MACRO
        if by_macro.get(macro)
    ]
