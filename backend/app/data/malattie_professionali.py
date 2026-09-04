"""Malattie professionali — reference table for the protocollo sanitario.

Curated subset of the Italian occupational-disease tables (D.M. 9 aprile
2008, "Nuove tabelle delle malattie professionali nell'industria e
nell'agricoltura", ex art. 3 DPR 1124/1965) plus the diseases that are NOT
tabellate but still fall under mandatory health surveillance or under the
"elenco delle malattie per le quali e' obbligatoria la denuncia" (D.M. 10
giugno 2014, Lista I/II ex art. 139 DPR 1124/1965).

Each entry is keyed to the app's own vocabulary so the protocollo sanitario
can be prefilled from what the operator already flagged:

  * ``rischi_specifici_codes`` — codes from
    ``app.services.reference_data.RISCHI_SPECIFICI_CATALOG`` (the per-mansione
    flags on ``Persona.rischi_specifici_codes``);
  * ``categorie`` — the 11 canonical DVR risk categories, SHORT form
    (``RISK_CATEGORY_SHORT_NAMES``: "Fisici", "Chimici", ...).

``tabella`` is the human-readable citation. Voce numbers are quoted only
where they are stable and well known (amianto 56, silice 57, rumore 75,
vibrazioni 76/77, sovraccarico biomeccanico 78/79, ernia discale da MMC 80);
chemical agents are cited by agent name because the industry table lists
one voce per agent and the exact voce depends on the substance the MC
identifies. ``tabellata=False`` entries are deliberately included (VDT,
biological, microclima, stress): the client asked for the diseases "a cui
gli operatori sono esposti", and the MC needs to see the non-tabellate ones
to plan the sorveglianza, even though they are recognised through the
"sistema misto" rather than by presumption.

This is a REFERENCE list for prefill and citation. Whether a disease is
correlated to a given mansione is a medical judgement: every output that
reaches a document is reviewed by the Medico Competente (art. 41 D.Lgs.
81/2008 and art. 25 for the protocollo). Nothing here is personal data.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypedDict


class MalattiaProfessionale(TypedDict):
    codice: str
    malattia: str
    agente_o_rischio: str
    tabella: str
    tabellata: bool
    rischi_specifici_codes: list[str]
    categorie: list[str]


_TAB_IND = "D.M. 9/4/2008 — Tab. Industria"
_TAB_AGR = "D.M. 9/4/2008 — Tab. Agricoltura"
_LISTA_I_BIO = (
    "Non tabellata — Lista I gruppo 4 D.M. 10/06/2014 (obbligo di denuncia "
    "art. 139 DPR 1124/1965); sorveglianza ex Titolo X D.Lgs. 81/2008"
)
_ART_176 = (
    "Non tabellata — sorveglianza sanitaria art. 176 D.Lgs. 81/2008 "
    "(Titolo VII, videoterminali)"
)


MALATTIE_PROFESSIONALI: list[MalattiaProfessionale] = [
    # ---- Agenti fisici: rumore ------------------------------------------
    {
        "codice": "ipoacusia_rumore",
        "malattia": "Ipoacusia da rumore",
        "agente_o_rischio": "Rumore (LEX,8h >= 80 dB(A))",
        "tabella": f"{_TAB_IND} voce 75",
        "tabellata": True,
        "rischi_specifici_codes": ["af_rumore"],
        "categorie": ["Fisici"],
    },
    # ---- Agenti fisici: vibrazioni mano-braccio --------------------------
    {
        "codice": "raynaud_vibrazioni_mano_braccio",
        "malattia": "Sindrome di Raynaud secondaria (angiopatia da vibrazioni)",
        "agente_o_rischio": "Vibrazioni mano-braccio (utensili vibranti)",
        "tabella": f"{_TAB_IND} voce 76",
        "tabellata": True,
        "rischi_specifici_codes": ["af_vibrazioni"],
        "categorie": ["Fisici"],
    },
    {
        "codice": "neuropatia_vibrazioni_mano_braccio",
        "malattia": "Neuropatia periferica e osteoartropatie da vibrazioni mano-braccio",
        "agente_o_rischio": "Vibrazioni mano-braccio (utensili vibranti)",
        "tabella": f"{_TAB_IND} voce 76",
        "tabellata": True,
        "rischi_specifici_codes": ["af_vibrazioni"],
        "categorie": ["Fisici"],
    },
    # ---- Agenti fisici: vibrazioni corpo intero --------------------------
    {
        "codice": "spondilodiscopatia_vibrazioni_corpo_intero",
        "malattia": "Spondilodiscopatia del tratto lombare",
        "agente_o_rischio": "Vibrazioni trasmesse al corpo intero (conduzione di mezzi)",
        "tabella": f"{_TAB_IND} voce 77",
        "tabellata": True,
        "rischi_specifici_codes": [
            "af_vibrazioni",
            "carrello_elevatore",
            "ruspa_escavatore",
            "guida_automezzi_cde",
            "gru",
        ],
        "categorie": ["Fisici"],
    },
    {
        "codice": "ernia_discale_vibrazioni_corpo_intero",
        "malattia": "Ernia discale lombare da vibrazioni corpo intero",
        "agente_o_rischio": "Vibrazioni trasmesse al corpo intero (conduzione di mezzi)",
        "tabella": f"{_TAB_IND} voce 77",
        "tabellata": True,
        "rischi_specifici_codes": [
            "af_vibrazioni",
            "carrello_elevatore",
            "ruspa_escavatore",
            "guida_automezzi_cde",
        ],
        "categorie": ["Fisici"],
    },
    # ---- Movimentazione manuale dei carichi ------------------------------
    {
        "codice": "ernia_discale_mmc",
        "malattia": "Ernia discale lombare",
        "agente_o_rischio": "Movimentazione manuale di carichi (sollevamento, traino, spinta)",
        "tabella": f"{_TAB_IND} voce 80",
        "tabellata": True,
        "rischi_specifici_codes": ["mmc"],
        "categorie": ["Ergonomici"],
    },
    # ---- Sovraccarico biomeccanico arto superiore ------------------------
    {
        "codice": "tendinopatie_arto_superiore",
        "malattia": "Tendiniti e tenosinoviti dell'arto superiore (spalla, gomito, polso-mano)",
        "agente_o_rischio": "Movimenti ripetuti e posture incongrue dell'arto superiore",
        "tabella": f"{_TAB_IND} voce 78",
        "tabellata": True,
        "rischi_specifici_codes": ["ergonomici", "mmc"],
        "categorie": ["Ergonomici"],
    },
    {
        "codice": "tunnel_carpale",
        "malattia": "Sindrome del tunnel carpale",
        "agente_o_rischio": "Movimenti ripetuti, uso di forza e vibrazioni al polso-mano",
        "tabella": f"{_TAB_IND} voce 78",
        "tabellata": True,
        "rischi_specifici_codes": ["ergonomici", "af_vibrazioni", "mmc"],
        "categorie": ["Ergonomici"],
    },
    {
        "codice": "epicondilite",
        "malattia": "Epicondilite ed epitrocleite",
        "agente_o_rischio": "Movimenti ripetuti del gomito con uso di forza",
        "tabella": f"{_TAB_IND} voce 78",
        "tabellata": True,
        "rischi_specifici_codes": ["ergonomici"],
        "categorie": ["Ergonomici"],
    },
    {
        "codice": "sovraccarico_ginocchio",
        "malattia": "Borsite, tendinopatia del quadricipite, meniscopatia degenerativa (sovraccarico del ginocchio)",
        "agente_o_rischio": "Lavoro prolungato in ginocchio o accovacciato (pavimentisti, posatori)",
        "tabella": f"{_TAB_IND} voce 79",
        "tabellata": True,
        "rischi_specifici_codes": ["ergonomici", "lavoro_difficile"],
        "categorie": ["Ergonomici"],
    },
    # ---- Videoterminali (non tabellate) ---------------------------------
    {
        "codice": "astenopia_vdt",
        "malattia": "Astenopia (affaticamento visivo)",
        "agente_o_rischio": "Uso di videoterminali >= 20 ore settimanali",
        "tabella": _ART_176,
        "tabellata": False,
        "rischi_specifici_codes": ["vdt"],
        "categorie": ["Ergonomici"],
    },
    {
        "codice": "dms_vdt",
        "malattia": "Disturbi muscolo-scheletrici del rachide cervicale e dell'arto superiore da postura al VDT",
        "agente_o_rischio": "Postura fissa prolungata alla postazione videoterminale",
        "tabella": _ART_176,
        "tabellata": False,
        "rischi_specifici_codes": ["vdt", "ergonomici"],
        "categorie": ["Ergonomici"],
    },
    # ---- Agenti chimici --------------------------------------------------
    {
        "codice": "dermatite_allergica_contatto",
        "malattia": "Dermatite allergica da contatto",
        "agente_o_rischio": "Agenti chimici sensibilizzanti (cromo, nichel, resine epossidiche, isocianati, detergenti)",
        "tabella": f"{_TAB_IND} — voce dell'agente sensibilizzante (es. voce 4 cromo, voce 7 nichel)",
        "tabellata": True,
        "rischi_specifici_codes": ["agenti_chimici"],
        "categorie": ["Chimici"],
    },
    {
        "codice": "dermatite_irritativa_contatto",
        "malattia": "Dermatite irritativa da contatto",
        "agente_o_rischio": "Agenti chimici irritanti, lavoro a umido, detergenti e solventi",
        "tabella": f"{_TAB_IND} — voce dell'agente irritante",
        "tabellata": True,
        "rischi_specifici_codes": ["agenti_chimici"],
        "categorie": ["Chimici"],
    },
    {
        "codice": "asma_bronchiale_professionale",
        "malattia": "Asma bronchiale professionale",
        "agente_o_rischio": "Agenti asmogeni (isocianati, aldeidi, polveri di legno, farine, lattice, resine)",
        "tabella": f"{_TAB_IND} — voce dell'agente asmogeno",
        "tabellata": True,
        "rischi_specifici_codes": ["agenti_chimici"],
        "categorie": ["Chimici"],
    },
    {
        "codice": "rinite_allergica_professionale",
        "malattia": "Rinite allergica professionale",
        "agente_o_rischio": "Agenti sensibilizzanti inalatori (farine, polveri di legno, lattice, enzimi)",
        "tabella": f"{_TAB_IND} — voce dell'agente sensibilizzante",
        "tabellata": True,
        "rischi_specifici_codes": ["agenti_chimici"],
        "categorie": ["Chimici"],
    },
    {
        "codice": "encefalopatia_solventi",
        "malattia": "Encefalopatia tossica cronica e polineuropatia da solventi organici",
        "agente_o_rischio": "Solventi organici (toluene, xilene, n-esano, derivati alogenati)",
        "tabella": f"{_TAB_IND} — voci degli idrocarburi aromatici, alifatici e alogenati",
        "tabellata": True,
        "rischi_specifici_codes": ["agenti_chimici"],
        "categorie": ["Chimici"],
    },
    {
        "codice": "allergia_lattice",
        "malattia": "Allergia al lattice (dermatite, orticaria, asma)",
        "agente_o_rischio": "Guanti e presidi in lattice (sanità, alimentare, pulizie)",
        "tabella": f"{_TAB_IND} — voce lattice",
        "tabellata": True,
        "rischi_specifici_codes": ["agenti_chimici", "agenti_biologici", "utilizzo_dpi"],
        "categorie": ["Chimici"],
    },
    # ---- Polveri: silice -------------------------------------------------
    {
        "codice": "silicosi",
        "malattia": "Silicosi",
        "agente_o_rischio": "Polveri contenenti silice libera cristallina (edilizia, taglio pietra, sabbiatura, ceramica)",
        "tabella": f"{_TAB_IND} voce 57",
        "tabellata": True,
        "rischi_specifici_codes": ["agenti_chimici", "cancerogeni_mutageni"],
        "categorie": ["Chimici", "Cancerogeni"],
    },
    {
        "codice": "carcinoma_polmonare_silice",
        "malattia": "Carcinoma polmonare da silice libera cristallina",
        "agente_o_rischio": "Polveri contenenti silice libera cristallina",
        "tabella": f"{_TAB_IND} voce 57",
        "tabellata": True,
        "rischi_specifici_codes": ["cancerogeni_mutageni"],
        "categorie": ["Cancerogeni"],
    },
    # ---- Amianto ---------------------------------------------------------
    {
        "codice": "asbestosi",
        "malattia": "Asbestosi",
        "agente_o_rischio": "Fibre di amianto (bonifiche, manutenzioni su manufatti in cemento-amianto)",
        "tabella": f"{_TAB_IND} voce 56",
        "tabellata": True,
        "rischi_specifici_codes": ["amianto", "cancerogeni_mutageni"],
        "categorie": ["Cancerogeni"],
    },
    {
        "codice": "mesotelioma",
        "malattia": "Mesotelioma pleurico, pericardico e peritoneale",
        "agente_o_rischio": "Fibre di amianto",
        "tabella": f"{_TAB_IND} voce 56",
        "tabellata": True,
        "rischi_specifici_codes": ["amianto", "cancerogeni_mutageni"],
        "categorie": ["Cancerogeni"],
    },
    {
        "codice": "carcinoma_polmonare_amianto",
        "malattia": "Carcinoma polmonare da amianto",
        "agente_o_rischio": "Fibre di amianto",
        "tabella": f"{_TAB_IND} voce 56",
        "tabellata": True,
        "rischi_specifici_codes": ["amianto"],
        "categorie": ["Cancerogeni"],
    },
    {
        "codice": "placche_pleuriche",
        "malattia": "Placche e ispessimenti pleurici",
        "agente_o_rischio": "Fibre di amianto",
        "tabella": f"{_TAB_IND} voce 56",
        "tabellata": True,
        "rischi_specifici_codes": ["amianto"],
        "categorie": ["Cancerogeni"],
    },
    # ---- Altri cancerogeni ----------------------------------------------
    {
        "codice": "leucemia_benzene",
        "malattia": "Leucemie e altre emopatie da benzene",
        "agente_o_rischio": "Benzene (carburanti, solventi, industria chimica)",
        "tabella": f"{_TAB_IND} — voce benzene",
        "tabellata": True,
        "rischi_specifici_codes": ["cancerogeni_mutageni", "agenti_chimici"],
        "categorie": ["Cancerogeni"],
    },
    {
        "codice": "carcinoma_vescica_amine",
        "malattia": "Carcinoma della vescica da amine aromatiche",
        "agente_o_rischio": "Amine aromatiche (coloranti, gomma, industria chimica)",
        "tabella": f"{_TAB_IND} — voce amine aromatiche",
        "tabellata": True,
        "rischi_specifici_codes": ["cancerogeni_mutageni"],
        "categorie": ["Cancerogeni"],
    },
    {
        "codice": "adenocarcinoma_nasosinusale_legno",
        "malattia": "Adenocarcinoma naso-sinusale da polveri di legno duro e di cuoio",
        "agente_o_rischio": "Polveri di legno duro e di cuoio (falegnamerie, calzaturifici)",
        "tabella": f"{_TAB_IND} — voce polveri di legno duro / cuoio",
        "tabellata": True,
        "rischi_specifici_codes": ["cancerogeni_mutageni", "agenti_chimici"],
        "categorie": ["Cancerogeni"],
    },
    {
        "codice": "tumori_ipa",
        "malattia": "Tumori cutanei e polmonari da idrocarburi policiclici aromatici (IPA)",
        "agente_o_rischio": "Fumi di combustione, catrame, bitume, oli minerali usati",
        "tabella": f"{_TAB_IND} — voce IPA / catrame e derivati",
        "tabellata": True,
        "rischi_specifici_codes": ["cancerogeni_mutageni"],
        "categorie": ["Cancerogeni"],
    },
    # ---- Agenti biologici -----------------------------------------------
    {
        "codice": "epatite_b_c",
        "malattia": "Epatite virale B e C",
        "agente_o_rischio": "Agenti biologici a trasmissione ematica (sanità, assistenza, laboratori, rifiuti)",
        "tabella": _LISTA_I_BIO + "; vaccinazione HBV art. 279",
        "tabellata": False,
        "rischi_specifici_codes": ["agenti_biologici"],
        "categorie": ["Biologici"],
    },
    {
        "codice": "tubercolosi",
        "malattia": "Tubercolosi",
        "agente_o_rischio": "Mycobacterium tuberculosis (sanità, assistenza, comunità, carceri)",
        "tabella": _LISTA_I_BIO,
        "tabellata": False,
        "rischi_specifici_codes": ["agenti_biologici"],
        "categorie": ["Biologici"],
    },
    {
        "codice": "zoonosi",
        "malattia": "Brucellosi, leptospirosi, tetano e altre zoonosi",
        "agente_o_rischio": "Contatto con animali, deiezioni e terreno (agricoltura, allevamento, macellazione, giardinaggio)",
        "tabella": f"{_TAB_AGR} — malattie infettive e parassitarie",
        "tabellata": True,
        "rischi_specifici_codes": ["agenti_biologici"],
        "categorie": ["Biologici"],
    },
    # ---- Radiazioni ottiche ---------------------------------------------
    {
        "codice": "cheratocongiuntivite_uv",
        "malattia": "Cheratocongiuntivite da radiazioni ultraviolette",
        "agente_o_rischio": "Radiazioni UV artificiali (saldatura ad arco) e solari (lavoro all'aperto)",
        "tabella": f"{_TAB_IND} — voce radiazioni ultraviolette",
        "tabellata": True,
        "rischi_specifici_codes": ["af_radiazioni_ottiche"],
        "categorie": ["Fisici"],
    },
    {
        "codice": "epiteliomi_cutanei_uv",
        "malattia": "Epiteliomi cutanei da radiazioni ultraviolette",
        "agente_o_rischio": "Radiazioni UV artificiali e solari (esposizione cronica)",
        "tabella": f"{_TAB_IND} — voce radiazioni ultraviolette",
        "tabellata": True,
        "rischi_specifici_codes": ["af_radiazioni_ottiche"],
        "categorie": ["Fisici", "Cancerogeni"],
    },
    {
        "codice": "cataratta_ir",
        "malattia": "Cataratta da radiazioni infrarosse",
        "agente_o_rischio": "Radiazioni infrarosse (forni, vetrerie, fonderie, saldatura)",
        "tabella": f"{_TAB_IND} — voce radiazioni infrarosse",
        "tabellata": True,
        "rischi_specifici_codes": ["af_radiazioni_ottiche", "af_microclima"],
        "categorie": ["Fisici"],
    },
    # ---- Microclima (non tabellate) -------------------------------------
    {
        "codice": "patologie_da_calore",
        "malattia": "Colpo di calore, esaurimento e crampi da calore",
        "agente_o_rischio": "Microclima severo caldo (forni, cucine, lavori estivi all'aperto)",
        "tabella": (
            "Non tabellata — sorveglianza sanitaria mirata ex art. 41 D.Lgs. "
            "81/2008 (Titolo VIII, microclima)"
        ),
        "tabellata": False,
        "rischi_specifici_codes": ["af_microclima"],
        "categorie": ["Fisici"],
    },
    {
        "codice": "patologie_da_freddo",
        "malattia": "Patologie da freddo (geloni, fenomeno di Raynaud da freddo, ipotermia)",
        "agente_o_rischio": "Microclima severo freddo (celle frigorifere, lavori invernali all'aperto)",
        "tabella": (
            "Non tabellata — sorveglianza sanitaria mirata ex art. 41 D.Lgs. "
            "81/2008 (Titolo VIII, microclima)"
        ),
        "tabellata": False,
        "rischi_specifici_codes": ["af_microclima"],
        "categorie": ["Fisici"],
    },
    # ---- Stress lavoro-correlato (non tabellata) ------------------------
    {
        "codice": "disturbi_adattamento_stress",
        "malattia": "Disturbo dell'adattamento cronico e disturbo post-traumatico da stress",
        "agente_o_rischio": "Stress lavoro-correlato e organizzazione del lavoro (turni, carichi, conflitti)",
        "tabella": (
            "Non tabellata — Lista II gruppo 7 D.M. 10/06/2014 (origine "
            "lavorativa di limitata probabilità)"
        ),
        "tabellata": False,
        "rischi_specifici_codes": ["psicologici", "organizzazione_lavoro"],
        "categorie": ["Psicologici", "Organizzazione"],
    },
]


MALATTIE_BY_CODICE: dict[str, MalattiaProfessionale] = {
    entry["codice"]: entry for entry in MALATTIE_PROFESSIONALI
}

REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "codice",
        "malattia",
        "agente_o_rischio",
        "tabella",
        "tabellata",
        "rischi_specifici_codes",
        "categorie",
    }
)


def _normalize_categoria(name: str) -> str:
    """Accept both the short ("Fisici") and long ("Agenti Fisici") forms."""
    from app.services.reference_data import CATEGORIA_LONG_TO_SHORT

    stripped = (name or "").strip()
    return CATEGORIA_LONG_TO_SHORT.get(stripped, stripped)


def malattie_per_rischi(
    rischi_codes: Iterable[str] | None,
    categorie: Iterable[str] | None = None,
) -> list[MalattiaProfessionale]:
    """Diseases whose exposure matches any of the given rischi codes or DVR
    categories. Preserves catalogue order, no duplicates.

    ``rischi_codes`` are RISCHI_SPECIFICI_CATALOG codes; ``categorie`` may be
    short or long DVR category names. Either argument may be empty — an
    empty union simply yields an empty list, never the whole table.
    """
    codes = {c for c in (rischi_codes or []) if c}
    cats = {_normalize_categoria(c) for c in (categorie or []) if c}
    out: list[MalattiaProfessionale] = []
    for entry in MALATTIE_PROFESSIONALI:
        if codes & set(entry["rischi_specifici_codes"]) or cats & set(entry["categorie"]):
            out.append(entry)
    return out


def get_malattia(codice: str) -> MalattiaProfessionale | None:
    return MALATTIE_BY_CODICE.get((codice or "").strip())
