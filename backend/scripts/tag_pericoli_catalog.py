"""One-shot script to populate ambiente_tipi + attrezzatura_keywords on
each pericolo in pericoli_catalog.json.

Tagging strategy
================
ambiente_tipi values are the lowercase canonical buckets the survey uses
(matches frontend/src/components/survey/steps/step-rischi.tsx
RISCHI_PER_AMBIENTE keys and backend reference_data.DEFAULT_RISK_SCORES):

    ufficio | magazzino | cucina | produzione | laboratorio
    | esterno | negozio | officina | altro

Empty list ([]) means "not applicable to any environment by default" — currently
unused. When the value is the special sentinel ALL the pericolo is universal
and applies regardless of environment tipo.

Conservative bias: when in doubt, include. The surveyor can always uncheck
in the UI; surfacing too few rows would silently drop relevant hazards.

attrezzatura_keywords trigger the pericolo *in addition* to the ambiente
filter — they are case-insensitive substrings matched against
attrezzatura.descrizione. Empty list means no equipment-specific trigger.

Run with:
    python -m scripts.tag_pericoli_catalog
"""
from __future__ import annotations

import json
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "pericoli_catalog.json"

ALL = ["ufficio", "magazzino", "cucina", "produzione", "laboratorio", "esterno", "negozio", "officina", "altro"]
INDUSTRIAL = ["magazzino", "produzione", "officina", "laboratorio", "esterno", "altro"]
INDOOR_NON_INDUSTRIAL = ["ufficio", "cucina", "negozio", "altro"]

# code -> (ambiente_tipi, attrezzatura_keywords)
TAGS: dict[str, tuple[list[str], list[str]]] = {
    # ---------- Strutture ----------
    "ST-01": (["magazzino", "produzione", "officina", "esterno", "altro"], []),  # mezzi esterno
    "ST-02": (["magazzino", "produzione", "officina", "altro"], []),  # mezzi interno
    "ST-03": (INDUSTRIAL, []),  # aperture nel vuoto
    "ST-04": (ALL, []),  # ingombri vie uscita
    "ST-05": (ALL, ["sgabello"]),  # sgabelli — common everywhere
    "ST-06": (ALL, ["scala portatile", "scala", "scala a pioli"]),
    "ST-07": (INDUSTRIAL, ["trabattello", "ponte su cavalletti", "ponteggio"]),
    "ST-08": (ALL, []),  # gradini, scale fisse
    "ST-09": (ALL, []),  # piani lavoro spigoli acuti
    "ST-10": (["magazzino", "produzione", "officina", "esterno", "altro"], ["carroponte", "gru", "paranco"]),
    "ST-11": (["produzione", "officina", "laboratorio", "esterno", "altro"], ["serbatoio", "vasca", "cisterna"]),
    "ST-12": (["produzione", "officina", "laboratorio", "esterno", "altro"], []),
    "ST-13": (["magazzino", "produzione", "officina", "altro"], []),
    "ST-14": (ALL, []),  # illum esterna
    "ST-15": (ALL, []),  # illum locali
    "ST-16": (ALL, []),  # illum emergenza
    "ST-17": (["ufficio", "magazzino", "negozio", "produzione", "officina", "laboratorio", "altro"], ["scaffale", "scaffalatura"]),
    "ST-18": (["magazzino", "produzione", "officina", "altro"], ["soppalco"]),
    "ST-19": (ALL, []),
    "ST-20": (["magazzino", "produzione", "officina", "esterno", "altro"], []),
    "ST-21": (ALL, []),
    "ST-22": (ALL, []),  # rischi esterni (Seveso) — universal flag

    # ---------- Macchine ----------
    # Generic machine guards — surface where any machinery exists. UI further
    # narrows by attrezzatura presence.
    "MA-01": (["cucina", "magazzino", "produzione", "officina", "laboratorio", "esterno", "altro"],
              ["tornio", "fresa", "pressa", "trapano", "saldatrice", "carroponte", "rettificatrice",
               "affettatrice", "tritacarne", "impastatrice", "centrifuga", "autoclave",
               "betoniera", "escavatore", "compressore", "lavastoviglie industriale",
               "nastro trasportatore"]),
    "MA-02": (["cucina", "magazzino", "produzione", "officina", "laboratorio", "altro"],
              ["tornio", "fresa", "pressa", "carroponte", "nastro trasportatore",
               "rettificatrice", "affettatrice", "tritacarne", "impastatrice", "centrifuga"]),
    "MA-03": (["cucina", "magazzino", "produzione", "officina", "laboratorio", "esterno", "altro"],
              ["tornio", "fresa", "pressa", "trapano", "saldatrice", "carroponte",
               "affettatrice", "tritacarne", "impastatrice", "centrifuga", "autoclave",
               "compressore"]),
    "MA-04": (["cucina", "magazzino", "produzione", "officina", "laboratorio", "altro"],
              ["tornio", "fresa", "pressa", "carroponte", "nastro trasportatore",
               "rettificatrice", "affettatrice", "tritacarne", "impastatrice"]),
    "MA-05": (["magazzino", "produzione", "officina", "laboratorio", "esterno", "altro"], []),
    "MA-06": (["magazzino", "produzione", "officina", "esterno", "altro"],
              ["muletto", "carrello elevatore", "transpallet", "carroponte", "gru", "paranco", "ple", "piattaforma"]),
    "MA-07": (["produzione", "officina", "esterno", "altro"],
              ["betoniera", "escavatore", "ruspa", "rullo", "martello demolitore"]),
    "MA-08": (ALL, ["ascensore", "montacarichi"]),
    "MA-09": (["produzione", "officina", "esterno", "altro"], ["compressore"]),
    "MA-10": (["produzione", "officina", "laboratorio", "esterno", "altro"],
              ["tornio", "fresa", "rettificatrice", "smerigliatrice", "mola"]),
    "MA-11": (["magazzino", "produzione", "officina", "esterno", "cucina", "laboratorio", "altro"],
              ["martello", "scalpello", "smerigliatrice", "mola", "trapano"]),
    "MA-12": (ALL, []),  # attrezzature manuali — universal
    "MA-13": (["cucina", "magazzino", "produzione", "officina", "laboratorio", "altro"],
              ["coltello", "mannaia", "affettatrice", "taglierina", "cesoia", "forbici"]),
    "MA-14": (ALL, []),  # manipolazione manuale oggetti

    # ---------- Impianti Elettrici ----------
    # Electrical hazards exist in every environment. Manutenzione/parti attive
    # variants stay narrower (specialist work).
    "EL-01": (ALL, []),
    "EL-02": (INDUSTRIAL + ["ufficio"], []),
    "EL-03": (ALL, []),
    "EL-04": (INDUSTRIAL + ["ufficio"], []),
    "EL-05": (ALL, []),
    "EL-06": (["produzione", "officina", "laboratorio", "esterno", "altro"], ["compressore", "saldatrice"]),
    "EL-07": (ALL, []),
    "EL-08": (ALL, []),
    "EL-09": (["produzione", "officina", "laboratorio", "esterno", "altro"], []),
    "EL-10": (["produzione", "officina", "laboratorio", "esterno", "altro"], []),

    # ---------- Incendio-Esplosioni ----------
    "IN-01": (ALL, []),
    "IN-02": (INDUSTRIAL + ["cucina"], []),
    "IN-03": (["cucina", "produzione", "officina", "laboratorio", "esterno", "altro"],
              ["forno", "piano cottura", "fornello", "friggitrice", "saldatrice"]),
    "IN-04": (["magazzino", "produzione", "officina", "laboratorio", "esterno", "altro"], []),
    "IN-05": (ALL, []),
    "IN-06": (ALL, []),
    "IN-07": (["produzione", "officina", "altro"], ["generatore di vapore", "caldaia"]),
    "IN-08": (["produzione", "officina", "altro"], ["generatore di vapore", "caldaia"]),
    "IN-09": (["produzione", "officina", "laboratorio", "esterno", "altro"], []),

    # ---------- Agenti Chimici ----------
    # Cleaning chemicals exist in every environment. Lab/officina/produzione
    # carry the heavier exposure, but pulizie applies broadly.
    "CH-01": (ALL, []),
    "CH-02": (["cucina", "magazzino", "produzione", "officina", "laboratorio", "esterno", "altro"], []),
    "CH-03": (["cucina", "magazzino", "produzione", "officina", "laboratorio", "esterno", "altro"], []),
    "CH-04": (["cucina", "magazzino", "produzione", "officina", "laboratorio", "esterno", "altro"], []),
    "CH-05": (ALL, []),
    "CH-06": (ALL, []),
    "CH-07": (["magazzino", "produzione", "officina", "laboratorio", "esterno", "altro"], []),

    # ---------- Agenti Fisici ----------
    "FI-01": (["cucina", "magazzino", "produzione", "officina", "laboratorio", "esterno", "altro"],
              ["compressore", "tornio", "fresa", "pressa", "carroponte", "nastro trasportatore",
               "betoniera", "martello demolitore"]),
    "FI-02": (["produzione", "officina", "esterno", "altro"],
              ["martello demolitore", "trapano", "smerigliatrice", "mola", "tassellatore"]),
    "FI-03": (["produzione", "officina", "esterno", "altro"],
              ["muletto", "carrello elevatore", "escavatore", "ruspa", "rullo", "betoniera"]),
    "FI-04": (["laboratorio", "produzione", "officina", "altro"], ["saldatrice"]),
    "FI-05": (["officina", "produzione", "laboratorio", "altro"], ["saldatrice", "laser"]),
    "FI-06": (["laboratorio", "altro"], []),
    "FI-07": (ALL, []),  # microclima
    "FI-08": (["esterno", "altro"], []),
    "FI-09": (["cucina", "produzione", "officina", "esterno", "altro"], ["forno", "piano cottura"]),
    "FI-10": (["magazzino", "esterno", "altro"], ["frigorifero industriale", "abbattitore", "cella frigo"]),
    "FI-11": (ALL, []),
    "FI-12": (ALL, []),

    # ---------- Agenti Biologici ----------
    "BI-01": (["cucina", "laboratorio", "esterno", "altro"], []),
    "BI-02": (["laboratorio", "altro"], []),  # gruppo 2/3/4 — solo lab
    "BI-03": (ALL, []),  # primo soccorso

    # ---------- Agenti Cancerogeni ----------
    "CA-01": (["produzione", "officina", "laboratorio", "altro"], []),
    "CA-02": (["produzione", "laboratorio", "altro"], []),
    "CA-03": (["produzione", "laboratorio", "altro"], []),
    "CA-04": (["produzione", "officina", "laboratorio", "altro"], []),
    "CA-05": (["produzione", "officina", "laboratorio", "altro"], []),
    "CA-06": (["produzione", "officina", "laboratorio", "altro"], []),
    # Amianto rows — all 5 are surfaced in environments where renovation/demolition
    # could occur. Keep narrow: edilizia/officina/esterno (manutenzioni straord).
    "CA-07": (["officina", "esterno", "altro"], []),
    "CA-08": (["officina", "esterno", "altro"], []),
    "CA-09": (["officina", "produzione", "esterno", "altro"], []),
    "CA-10": (["esterno", "altro"], []),
    "CA-11": (["esterno", "altro"], []),

    # ---------- Organizzazione del Lavoro ----------
    "OR-01": (ALL, []),
    "OR-02": (ALL, []),
    "OR-03": (ALL, []),  # gestanti — applicabile in ogni azienda
    "OR-04": (ALL, []),
    "OR-05": (ALL, []),
    "OR-06": (ALL, []),
    "OR-07": (ALL, []),  # MMC — anywhere with manual handling
    "OR-08": (["ufficio", "negozio", "altro"], []),  # VDT — primarily desk roles

    # ---------- Fattori Psicologici ----------
    # Universal stressors. PS-08 (guida) only roles that drive.
    "PS-01": (ALL, []),
    "PS-02": (ALL, []),
    "PS-03": (ALL, []),
    "PS-04": (ALL, []),
    "PS-05": (ALL, []),
    "PS-06": (["ufficio", "negozio", "altro"], []),
    "PS-07": (ALL, []),
    "PS-08": (["esterno", "altro"], []),  # guida prolungata

    # ---------- Fattori Ergonomici ----------
    "ER-01": (ALL, []),
    "ER-02": (ALL, []),
    "ER-03": (ALL, []),
}


def main() -> None:
    with CATALOG_PATH.open() as f:
        data = json.load(f)

    pericoli = data["pericoli"]
    expected_codes = {p["code"] for p in pericoli}
    tag_codes = set(TAGS.keys())

    missing_in_tags = expected_codes - tag_codes
    extra_in_tags = tag_codes - expected_codes
    if missing_in_tags:
        raise SystemExit(f"Codes in catalog but not tagged: {sorted(missing_in_tags)}")
    if extra_in_tags:
        raise SystemExit(f"Codes tagged but not in catalog: {sorted(extra_in_tags)}")

    for p in pericoli:
        ambiente_tipi, kw = TAGS[p["code"]]
        p["ambiente_tipi"] = ambiente_tipi
        p["attrezzatura_keywords"] = kw

    # Update meta
    data["_meta"]["notes"] = [
        n for n in data["_meta"]["notes"]
        if not n.startswith("ambiente_tipi and attrezzatura_keywords are null")
    ] + [
        "ambiente_tipi tagged conservatively (when in doubt, include) — operator can override in UI.",
        "attrezzatura_keywords are case-insensitive substrings matched against attrezzatura.descrizione.",
    ]

    with CATALOG_PATH.open("w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Stats
    print(f"Tagged {len(pericoli)} pericoli.")
    universal = sum(1 for p in pericoli if set(p["ambiente_tipi"]) == set(ALL))
    print(f"  Universal (all env): {universal}")
    with_kw = sum(1 for p in pericoli if p["attrezzatura_keywords"])
    print(f"  With equipment keywords: {with_kw}")


if __name__ == "__main__":
    main()
