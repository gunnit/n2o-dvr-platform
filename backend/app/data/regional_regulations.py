"""Italian regional safety regulations lookup (US-2.2 AC1, second half).

Every regione in Italy publishes its own implementation of the national
workplace-safety framework on top of D.Lgs. 81/2008: a Piano Regionale
della Prevenzione (PRP) per the State-Regions accord, plus assorted
regional laws on specific hazards (amianto, radon, radiazioni, stress,
microclima, etc.). These references belong in the DVR's Parte II
"Contesto Territoriale" section so the operator reviewing the draft
sees the applicable regional frame without looking it up.

Data shape:
  regione (str) -> list[Regulation]
  Regulation = {"titolo": str, "riferimento": str, "ambito": str}

Coverage philosophy: for each regione we ship 2-3 anchor references —
the current PRP and 1-2 region-specific laws most frequently cited in
DVR audits. This is *not* exhaustive (Italian regional law is vast
and fast-moving); operators review and add what's missing. We mark
every entry with its ``ambito`` so the DVR reads right ("Sicurezza sul
lavoro", "Amianto", "Radon", etc.).

Lookup is always driven by the comune name: we resolve comune ->
regione via ``seismic_zones.lookup_regione`` so both lookups stay in
lock-step with the same 158-comune registry.
"""

from __future__ import annotations

from typing import TypedDict

from app.data.seismic_zones import lookup_regione


class Regulation(TypedDict):
    titolo: str
    riferimento: str
    ambito: str


# Piano Regionale della Prevenzione (PRP) 2020-2025 is the common spine —
# each regione approved one via DGR. The specific DGR number differs and we
# cite the one currently in force per the Ministero della Salute cross-ref.
_REGULATIONS: dict[str, list[Regulation]] = {
    "Abruzzo": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Abruzzo 636/2021",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Norme per la tutela della salute e la promozione della sicurezza sui luoghi di lavoro",
            "riferimento": "L.R. Abruzzo 22/2000",
            "ambito": "Sicurezza sul lavoro",
        },
    ],
    "Basilicata": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Basilicata 807/2021",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Piano regionale amianto",
            "riferimento": "L.R. Basilicata 27/1993",
            "ambito": "Amianto",
        },
    ],
    "Calabria": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Calabria 461/2022",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Norme per il censimento, la gestione e lo smaltimento dell'amianto",
            "riferimento": "L.R. Calabria 14/2011",
            "ambito": "Amianto",
        },
    ],
    "Campania": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Campania 77/2022",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Linee guida regionali sulla prevenzione degli infortuni in edilizia",
            "riferimento": "D.G.R. Campania 288/2019",
            "ambito": "Edilizia",
        },
    ],
    "Emilia-Romagna": [
        {
            "titolo": "Piano Regionale della Prevenzione 2021-2025",
            "riferimento": "D.G.R. Emilia-Romagna 1798/2021",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Norme in materia di salute e sicurezza sul lavoro",
            "riferimento": "L.R. Emilia-Romagna 3/2016",
            "ambito": "Sicurezza sul lavoro",
        },
        {
            "titolo": "Linee guida radon negli ambienti di lavoro",
            "riferimento": "D.G.R. Emilia-Romagna 1017/2016",
            "ambito": "Radon",
        },
    ],
    "Friuli-Venezia Giulia": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. FVG 1072/2021",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Disposizioni sulla sicurezza nei cantieri temporanei o mobili",
            "riferimento": "L.R. Friuli-Venezia Giulia 5/2007",
            "ambito": "Cantieri",
        },
    ],
    "Lazio": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Lazio 413/2022",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Norme per la sicurezza del lavoro nei cantieri edili",
            "riferimento": "L.R. Lazio 7/2019",
            "ambito": "Cantieri",
        },
        {
            "titolo": "Prevenzione del rischio radon",
            "riferimento": "L.R. Lazio 14/2016",
            "ambito": "Radon",
        },
    ],
    "Liguria": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Liguria 1104/2021",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Piano regionale amianto",
            "riferimento": "L.R. Liguria 20/2006",
            "ambito": "Amianto",
        },
    ],
    "Lombardia": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Lombardia XI/4508/2021",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Linee guida per l'applicazione del D.Lgs. 81/2008 nel sistema sanitario regionale",
            "riferimento": "D.G.R. Lombardia X/6886/2017",
            "ambito": "Sicurezza sul lavoro",
        },
        {
            "titolo": "Misure di prevenzione per il rischio radon",
            "riferimento": "D.G.R. Lombardia XI/1277/2021",
            "ambito": "Radon",
        },
    ],
    "Marche": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Marche 1392/2021",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Norme in materia di sicurezza e qualita nei cantieri edili",
            "riferimento": "L.R. Marche 33/2008",
            "ambito": "Cantieri",
        },
    ],
    "Molise": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Molise 373/2022",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Disposizioni per la tutela della salute e della sicurezza sul lavoro",
            "riferimento": "L.R. Molise 17/2009",
            "ambito": "Sicurezza sul lavoro",
        },
    ],
    "Piemonte": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Piemonte 30-4485/2022",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Norme per la prevenzione del rischio radon",
            "riferimento": "D.G.R. Piemonte 16-3983/2016",
            "ambito": "Radon",
        },
        {
            "titolo": "Piano regionale amianto",
            "riferimento": "L.R. Piemonte 30/2008",
            "ambito": "Amianto",
        },
    ],
    "Puglia": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Puglia 2105/2021",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Norme in materia di sicurezza e regolarita nei cantieri",
            "riferimento": "L.R. Puglia 4/2010",
            "ambito": "Cantieri",
        },
    ],
    "Sardegna": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Sardegna 32/27/2022",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Interventi per la tutela della salute e sicurezza sul lavoro",
            "riferimento": "L.R. Sardegna 9/2006",
            "ambito": "Sicurezza sul lavoro",
        },
    ],
    "Sicilia": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.A. Sicilia 1329/2022",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Norme in materia di tutela della salute e della sicurezza nei luoghi di lavoro",
            "riferimento": "L.R. Sicilia 6/2009",
            "ambito": "Sicurezza sul lavoro",
        },
    ],
    "Toscana": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Toscana 1354/2021",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Norme per la tutela della salute e della sicurezza sul lavoro",
            "riferimento": "L.R. Toscana 32/2002",
            "ambito": "Sicurezza sul lavoro",
        },
        {
            "titolo": "Tutela dei lavoratori dalle esposizioni ad amianto",
            "riferimento": "L.R. Toscana 51/2013",
            "ambito": "Amianto",
        },
    ],
    "Trentino-Alto Adige": [
        {
            "titolo": "Piano Provinciale della Prevenzione 2020-2025 (Trento)",
            "riferimento": "D.G.P. Trento 1854/2021",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Norme sulla sicurezza nei cantieri edili",
            "riferimento": "L.P. Trento 4/2008",
            "ambito": "Cantieri",
        },
        {
            "titolo": "Piano Provinciale della Prevenzione 2020-2025 (Bolzano)",
            "riferimento": "D.G.P. Bolzano 947/2021",
            "ambito": "Prevenzione e sicurezza",
        },
    ],
    "Umbria": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Umbria 1213/2021",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Norme in materia di salute e sicurezza sul lavoro",
            "riferimento": "L.R. Umbria 2/2007",
            "ambito": "Sicurezza sul lavoro",
        },
    ],
    "Valle d'Aosta": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Valle d'Aosta 1487/2021",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Disposizioni in materia di sicurezza sul lavoro",
            "riferimento": "L.R. Valle d'Aosta 18/2008",
            "ambito": "Sicurezza sul lavoro",
        },
    ],
    "Veneto": [
        {
            "titolo": "Piano Regionale della Prevenzione 2020-2025",
            "riferimento": "D.G.R. Veneto 1764/2021",
            "ambito": "Prevenzione e sicurezza",
        },
        {
            "titolo": "Disposizioni in materia di sicurezza sul lavoro",
            "riferimento": "L.R. Veneto 7/2019",
            "ambito": "Sicurezza sul lavoro",
        },
        {
            "titolo": "Piano regionale amianto",
            "riferimento": "L.R. Veneto 55/1987",
            "ambito": "Amianto",
        },
    ],
}


def get_regulations_for_regione(regione: str) -> list[Regulation]:
    """Return the applicable regional regulations for a named regione.

    Case-sensitive on the canonical regione spelling used in seismic_zones
    (e.g. "Emilia-Romagna", "Valle d'Aosta"). Returns an empty list for
    unmapped regioni so callers can surface a "Regolamenti regionali non
    disponibili" banner without raising.
    """
    return list(_REGULATIONS.get(regione, ()))


def get_regulations_for_comune(comune: str) -> tuple[str | None, list[Regulation]]:
    """Resolve comune -> (regione, regulations).

    Thin convenience wrapper that does the comune -> regione hop and the
    regione -> regulations hop in one call. Returns ``(None, [])`` for
    comuni not in the seismic_zones table.
    """
    regione = lookup_regione(comune)
    if regione is None:
        return None, []
    return regione, get_regulations_for_regione(regione)


def covered_regioni() -> set[str]:
    """Exposed for tests: the set of regioni we publish regulations for."""
    return set(_REGULATIONS.keys())
