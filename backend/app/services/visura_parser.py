"""Deterministic field parser for visura camerale plaintext.

Backs ``POST /aziende/visura/estrai`` — the "Carica visura camerale" control
that sits next to the P.IVA autofill at the *start* of the censimento
(client call 2026-09-04). The operator drops the CCIAA PDF, we hand back an
``AziendaAutofillResponse`` shaped exactly like the P.IVA flow's so the
new-azienda page can merge it with the same code path and badge every
field with its provenance.

Privacy posture — identical to the post-creation upload in
``api/v1/aziende.py`` and stricter than the P.IVA flow:

* Everything here is regex over text pypdf extracted **locally**. No AI
  helper is imported or called, nothing is metered, nothing leaves the
  process. The raw text (which carries soci / amministratori names and
  their personal codici fiscali) lives for one request and is discarded.
* Only *company-level* fields are pulled out. The codice fiscale is read
  from the impresa header label only, and a 16-character (natural-person)
  code is kept solely for a ditta individuale — where the titolare's code
  *is* the impresa's — and dropped otherwise, without falling back to any
  later "Codice fiscale" occurrence in the document.

Confidence: ``high`` for values anchored to an explicit registry label
("Numero REA", "Partita IVA", "Codice ATECO", ...), ``medium`` for the
heuristic ones (activity description, headcount, an address the layout
did not let us decompose fully). Nothing here is AI-derived.

The layout targeted is the Infocamere "Visura ordinaria" (the one every
CCIAA emits), with tolerance for the street-first address style used by
resellers. Unknown layouts degrade to fewer fields, never to wrong ones —
the operator reviews and the form validates on submit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.schemas.azienda import (
    AziendaAutofillFieldMeta,
    AziendaAutofillResponse,
    Confidence,
)

SOURCE_LABEL = "Visura camerale (PDF)"

# Label phrases that start a new "Label   value" row in the Infocamere
# layout. Multi-word on purpose: a single word such as "Stato" or
# "Attività" can legitimately appear inside a company name, a two-word
# registry label cannot. Used both to terminate a value that runs on the
# same line (pypdf sometimes flattens a table row) and to refuse a value
# that is really the next row's label.
_LABEL_PHRASES = (
    r"Dati anagrafici|Indirizzo Sede|Indirizzo|Domicilio digitale|Numero REA|"
    r"Codice fiscale|Partita IVA|Forma giuridica|Data atto|Data iscrizione|"
    r"Capitale sociale|Stato attivit[aà]|Data inizio|Codice ATECO|Sede legale|"
    r"Unit[aà]'? locale|Sede secondaria|Oggetto sociale|Importanza|Tipologia|"
    r"Attivit[aà]'? (?:prevalente|esercitata|principale)|Durata|Sistema di amministrazione|"
    r"Informazioni da statuto|Amministratori|Titolari di cariche|Soci e titolari|Addetti"
)
_LABEL_INLINE_RE = re.compile(rf"\b(?:{_LABEL_PHRASES})\b", re.IGNORECASE)
_LABEL_START_RE = re.compile(rf"^(?:{_LABEL_PHRASES})\b", re.IGNORECASE)

# --- label anchors -----------------------------------------------------------

_DENOMINAZIONE_LABEL_RE = re.compile(
    r"\b(?:denominazione|ragione\s+sociale|ditta(?!\s+individuale))\s*:?", re.IGNORECASE
)
# Infocamere prints the name on its own line right under the document title
# ("VISURA ORDINARIA SOCIETA' DI CAPITALE") before any label appears.
_HEADING_RE = re.compile(r"^VISURA\b[^\n]*\n+([^\n]+)", re.IGNORECASE | re.MULTILINE)
_FORMA_LABEL_RE = re.compile(r"\bforma\s+giuridica\s*:?", re.IGNORECASE)
_SEDE_LEGALE_LABEL_RE = re.compile(r"\b(?:indirizzo\s+)?sede\s+legale\s*:?", re.IGNORECASE)
_INDIRIZZO_LABEL_RE = re.compile(r"\bindirizzo\s*:?", re.IGNORECASE)
_ATTIVITA_LABEL_RE = re.compile(
    r"\battivit[aà]'?\s+(?:prevalente(?:\s+esercitata(?:\s+dall'?\s*impresa)?)?"
    r"|esercitata(?:\s+dall'?\s*impresa)?|principale)\s*:?",
    re.IGNORECASE,
)
_UNITA_LOCALE_RE = re.compile(
    r"\b(?:unit[aà]'?\s+locale|sede\s+secondaria|unit[aà]'?\s+operativa)\b", re.IGNORECASE
)

# The impresa's own code sits under "Codice fiscale e n.iscr. al Registro
# Imprese" (label may wrap across lines). First occurrence in the document
# is the header — persons' codes come pages later under the cariche.
_CF_RE = re.compile(
    r"\bcodice\s+fiscale"
    r"(?:\s+e\s+n(?:umero)?\.?\s*(?:di\s+)?iscr(?:izione|\.)?\s*(?:al\s+)?"
    r"(?:registro\s+(?:delle\s+)?imprese|r\.?\s*i\.?)?)?"
    r"\s*:?\s*([A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]|\d{11})\b",
    re.IGNORECASE,
)
_PIVA_RE = re.compile(r"\b(?:partita\s+iva|p\.?\s*iva)\s*:?\s*(\d{11})\b", re.IGNORECASE)
_REA_RE = re.compile(
    r"\b(?:numero\s+|n\.?\s*)?REA\s*:?\s*([A-Z]{2})\s*[-–]?\s*(\d{4,8})\b", re.IGNORECASE
)
_PEC_RE = re.compile(
    r"\b(?:domicilio\s+digitale(?:\s*/\s*PEC)?|indirizzo\s+PEC|PEC|posta\s+elettronica\s+certificata)"
    r"\s*:?\s*([\w.+-]+@[\w-]+\.[\w.-]+)",
    re.IGNORECASE,
)
_ATECO_RE = re.compile(
    r"\bcodice\s+ateco(?:\s*\(?\s*\d{4}\s*\)?)?\s*:?\s*(\d{2})\.?(\d{2})(?:\.(\d{1,2}))?\b"
    r"(?:\s*[-–]\s*([^\n]+))?",
    re.IGNORECASE,
)
_DATA_COSTITUZIONE_RE = re.compile(
    r"\bdata\s+(?:atto\s+di\s+)?costituzione\s*:?\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b",
    re.IGNORECASE,
)
_DATA_ISCRIZIONE_RE = re.compile(
    r"\bdata\s+iscrizione\s*:?\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", re.IGNORECASE
)
_CAPITALE_LABEL_RE = re.compile(r"\bcapitale\s+sociale\b", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)")
_SOTTOSCRITTO_RE = re.compile(
    r"sottoscritto\D{0,12}?(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)", re.IGNORECASE
)
_DIPENDENTI_RE = re.compile(r"\bdipendenti\s*:?\s*(\d{1,6})\b", re.IGNORECASE)
_ADDETTI_RE = re.compile(
    r"\b(?:numero\s+)?addetti(?:\s*\([^)]*\))?(?:\s+al\s+\d{1,2}/\d{1,2}/\d{4})?\s*:?\s*(\d{1,6})\b",
    re.IGNORECASE,
)

# Address shapes. Infocamere: "MILANO (MI) VIA ROMA 1 CAP 20100".
# Resellers: "VIA ROMA 1 - 20100 MILANO (MI)".
# The comune never carries a digit — that is what tells the two layouts
# apart when a street-first line also ends in "(MI)".
_ADDR_CITY_FIRST_RE = re.compile(
    r"^(?P<citta>[^()\d]+?)\s*\((?P<prov>[A-Za-z]{2})\)\s*(?P<via>.*?)\s*(?:\bCAP\s*(?P<cap>\d{5}))?\s*$",
    re.IGNORECASE,
)
_ADDR_STREET_FIRST_RE = re.compile(
    r"^(?P<via>.+?)\s*[-,–]?\s*(?P<cap>\d{5})\s+(?P<citta>[^()]+?)\s*\((?P<prov>[A-Za-z]{2})\)\s*$",
    re.IGNORECASE,
)

# Long legal forms as printed by the registry, checked in order: the more
# specific forms (semplificata, consortile, cooperativa) must win before the
# bare "responsabilità limitata" / "s.r.l." test claims them. Canonical
# values are the frontend's FORMA_GIURIDICA_OPTIONS — anything else is
# dropped rather than shown as an option the Select cannot render.
_FORMA_CANON: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern, re.IGNORECASE), canon)
    for pattern, canon in (
        (r"responsabilit[aà]'?\s+limitata\s+semplificata|\bs\.?\s?r\.?\s?l\.?\s?s\b", "SRLS"),
        (r"cooperativa", "Cooperativa"),
        (r"consorzio", "Consorzio"),
        (r"consortile|\bs\.?\s?c\.?\s?a\.?\s?r\.?\s?l\b|\bscrl\b", "SCARL"),
        (r"responsabilit[aà]'?\s+limitata|\bs\.?\s?r\.?\s?l\b", "SRL"),
        (r"accomandita\s+per\s+azioni|\bs\.?\s?a\.?\s?p\.?\s?a\b", "SAPA"),
        (r"per\s+azioni|\bs\.?\s?p\.?\s?a\b", "SPA"),
        (r"nome\s+collettivo|\bs\.?\s?n\.?\s?c\b", "SNC"),
        (r"accomandita\s+semplice|\bs\.?\s?a\.?\s?s\b", "SAS"),
        (
            r"impresa\s+individuale|ditta\s+individuale|imprenditore\s+individuale|"
            r"piccolo\s+imprenditore|persona\s+fisica",
            "Ditta Individuale",
        ),
        (r"societ[aà]'?\s+semplice", "Società Semplice"),
    )
)

_DITTA_INDIVIDUALE = "Ditta Individuale"


@dataclass
class ParsedVisura:
    """Field values the parser recognised, with per-field confidence.

    ``values`` is keyed by ``AziendaCreate`` field names; dates are ISO
    strings, money is a float in euro, ``sedi_operative_extra`` is the
    ``[{via, citta, comune, provincia, cap}]`` list the create payload
    accepts. Insertion order follows the visura, which keeps the toast
    count and any debugging output readable.
    """

    values: dict[str, Any] = field(default_factory=dict)
    confidence: dict[str, Confidence] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def set(self, name: str, value: Any, confidence: Confidence) -> None:
        if value is None or value == "" or value == []:
            return
        self.values[name] = value
        self.confidence[name] = confidence


# --- helpers ------------------------------------------------------------------


def _normalise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return text


def _value_after(label: re.Pattern[str], text: str, *, max_lines: int = 1) -> str | None:
    """The cell to the right of a registry label.

    Reads the rest of the label's line and, when the value wrapped or the
    label ended its line, up to ``max_lines`` following lines — stopping at
    a blank line or at the next label. A label phrase found *inside* a line
    (pypdf flattening two cells onto one line) cuts the value there.
    """
    m = label.search(text)
    if not m:
        return None
    collected: list[str] = []
    skipped_blank = False
    for line in text[m.end() :].split("\n")[: max_lines + 2]:
        stripped = line.strip()
        if not stripped:
            if collected or skipped_blank:
                break
            skipped_blank = True
            continue
        if _LABEL_START_RE.match(stripped):
            break
        cut = _LABEL_INLINE_RE.search(stripped)
        if cut:
            head = stripped[: cut.start()].strip()
            if head:
                collected.append(head)
            break
        collected.append(stripped)
        if len(collected) >= max_lines:
            break
    value = " ".join(collected).strip(" :;-")
    return value or None


def _parse_amount(raw: str) -> float | None:
    """"10.000,00" / "10000" / "10000,50" -> euro float; < 100 is a parse error."""
    try:
        value = float(raw.strip().replace(".", "").replace(",", "."))
    except ValueError:
        return None
    return value if value >= 100 else None


def _iso_date(d: str, m: str, y: str) -> str | None:
    try:
        parsed = date(int(y), int(m), int(d))
    except ValueError:
        return None
    return parsed.isoformat() if parsed.year >= 1900 else None


def _canonical_forma(raw: str | None) -> str | None:
    if not raw:
        return None
    for pattern, canon in _FORMA_CANON:
        if pattern.search(raw):
            return canon
    return None


def _parse_address(raw: str | None) -> dict[str, str] | None:
    """Split "COMUNE (PR) VIA ... CAP NNNNN" (or street-first) into parts."""
    if not raw:
        return None
    cleaned = re.sub(r"\s+", " ", raw).strip(" ,;-")
    for pattern in (_ADDR_CITY_FIRST_RE, _ADDR_STREET_FIRST_RE):
        m = pattern.match(cleaned)
        if not m:
            continue
        parts = {
            "via": (m.group("via") or "").strip(" ,;-"),
            "citta": (m.group("citta") or "").strip(" ,;-"),
            "provincia": (m.group("prov") or "").upper(),
            "cap": m.group("cap") or "",
        }
        if parts["citta"] or parts["via"]:
            return parts
    return None


def _address_confidence(parts: dict[str, str]) -> Confidence:
    return "high" if all(parts[k] for k in ("via", "citta", "provincia", "cap")) else "medium"


def _sentence_case(value: str) -> str:
    # Visure shout activity descriptions in capitals; the form field is
    # prose. Only touch all-caps values so mixed-case input stays as typed.
    return value.capitalize() if value.isupper() else value


# --- parser -------------------------------------------------------------------


def parse_visura(text: str) -> ParsedVisura:
    """Map visura plaintext onto ``AziendaCreate`` fields. Pure, no I/O."""
    text = _normalise(text)
    out = ParsedVisura()

    # Ragione sociale: explicit label first, document heading as fallback.
    name = _value_after(_DENOMINAZIONE_LABEL_RE, text)
    if name:
        out.set("ragione_sociale", name, "high")
    else:
        heading = _HEADING_RE.search(text)
        candidate = heading.group(1).strip() if heading else ""
        if (
            candidate
            and len(candidate) <= 120
            and re.search(r"[A-Za-z]", candidate)
            and not _LABEL_START_RE.match(candidate)
        ):
            out.set("ragione_sociale", candidate, "medium")

    forma_raw = _value_after(_FORMA_LABEL_RE, text)
    forma = _canonical_forma(forma_raw)
    if forma:
        out.set("forma_giuridica", forma, "high")
    else:
        forma = _canonical_forma(out.values.get("ragione_sociale"))
        if forma:
            out.set("forma_giuridica", forma, "medium")

    cf = _CF_RE.search(text)
    if cf:
        code = cf.group(1).upper()
        # A 16-char code is a natural person's. It is the impresa's own only
        # for a ditta individuale; for any company it would be a person named
        # on the visura, which never leaves this function.
        if len(code) == 11 or forma == _DITTA_INDIVIDUALE:
            out.set("codice_fiscale", code, "high")

    piva = _PIVA_RE.search(text)
    if piva:
        out.set("partita_iva", piva.group(1), "high")

    rea = _REA_RE.search(text)
    if rea:
        out.set("rea", f"{rea.group(1).upper()}-{rea.group(2)}", "high")

    pec = _PEC_RE.search(text)
    if pec:
        out.set("pec", pec.group(1).lower().rstrip("."), "high")

    sede = _parse_address(_value_after(_SEDE_LEGALE_LABEL_RE, text, max_lines=2))
    if sede:
        conf = _address_confidence(sede)
        out.set("sede_legale_via", sede["via"], conf)
        out.set("sede_legale_citta", sede["citta"], conf)
        out.set("cap_legale", sede["cap"], conf)
        out.set("provincia_legale", sede["provincia"], conf)

    ateco = _ATECO_RE.search(text)
    ateco_descr: str | None = None
    if ateco:
        a, b, c, descr = ateco.groups()
        out.set("codice_ateco", f"{a}.{b}.{c}" if c else f"{a}.{b}", "high")
        ateco_descr = descr.strip() if descr else None

    attivita = _value_after(_ATTIVITA_LABEL_RE, text, max_lines=2)
    if attivita:
        out.set("attivita", _sentence_case(attivita)[:300], "medium")
    elif ateco_descr:
        out.set("attivita", _sentence_case(ateco_descr)[:300], "medium")

    costituzione = _DATA_COSTITUZIONE_RE.search(text)
    if costituzione:
        out.set("data_costituzione", _iso_date(*costituzione.groups()), "high")
    else:
        iscrizione = _DATA_ISCRIZIONE_RE.search(text)
        if iscrizione:
            out.set("data_costituzione", _iso_date(*iscrizione.groups()), "medium")

    capitale_label = _CAPITALE_LABEL_RE.search(text)
    if capitale_label:
        window = text[capitale_label.end() : capitale_label.end() + 120]
        sottoscritto = _SOTTOSCRITTO_RE.search(window)
        amount = _parse_amount(sottoscritto.group(1)) if sottoscritto else None
        if amount is None:
            for candidate in _AMOUNT_RE.finditer(window):
                amount = _parse_amount(candidate.group(1))
                if amount is not None:
                    break
        out.set("capitale_sociale", amount, "high")

    headcount = _DIPENDENTI_RE.search(text) or _ADDETTI_RE.search(text)
    if headcount:
        out.set("numero_dipendenti_dichiarati", int(headcount.group(1)), "medium")

    # Unità locali: the first becomes the primary sede operativa (the
    # columns on the row), the rest go to the JSONB extras — the same
    # routing the openapi.com registry source uses in the P.IVA flow.
    sedi = _parse_unita_locali(text, sede)
    if sedi:
        primary = sedi[0]
        conf = _address_confidence(primary)
        out.set("sede_operativa_via", primary["via"], conf)
        out.set("sede_operativa_citta", primary["citta"], conf)
        out.set("cap_operativa", primary["cap"], conf)
        out.set("provincia_operativa", primary["provincia"], conf)
        extras = [
            {
                "via": s["via"],
                "citta": s["citta"],
                "comune": s["citta"],
                "provincia": s["provincia"],
                "cap": s["cap"],
            }
            for s in sedi[1:]
        ]
        out.set("sedi_operative_extra", extras, "high")

    if "ragione_sociale" not in out.values:
        out.warnings.append("Denominazione non riconosciuta nella visura: inseriscila a mano.")
    if "partita_iva" not in out.values:
        out.warnings.append("Partita IVA non trovata nella visura: inseriscila a mano.")
    if "sede_legale_via" not in out.values and "sede_legale_citta" not in out.values:
        out.warnings.append("Sede legale non riconosciuta nella visura: inseriscila a mano.")
    return out


def _parse_unita_locali(text: str, sede_legale: dict[str, str] | None) -> list[dict[str, str]]:
    matches = list(_UNITA_LOCALE_RE.finditer(text))
    seen: set[tuple[str, str, str]] = set()
    if sede_legale:
        seen.add((sede_legale["via"], sede_legale["citta"], sede_legale["cap"]))
    sedi: list[dict[str, str]] = []
    for idx, m in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else min(len(text), m.end() + 600)
        block = text[m.end() : end]
        parts = _parse_address(_value_after(_INDIRIZZO_LABEL_RE, block, max_lines=2))
        if not parts:
            continue
        key = (parts["via"], parts["citta"], parts["cap"])
        if key in seen:
            continue
        seen.add(key)
        sedi.append(parts)
    return sedi


def build_visura_autofill(text: str) -> AziendaAutofillResponse:
    """The ``POST /aziende/visura/estrai`` payload for one visura's text.

    Same envelope as ``POST /aziende/autofill`` so the frontend applies it
    with the code it already has: fill only empty fields, badge each with
    ``meta``, toast the ``warnings``.
    """
    parsed = parse_visura(text)
    meta = {
        name: AziendaAutofillFieldMeta(confidence=parsed.confidence[name], source=SOURCE_LABEL)
        for name in parsed.values
    }
    return AziendaAutofillResponse(
        partita_iva=str(parsed.values.get("partita_iva") or ""),
        values=parsed.values,
        meta=meta,
        warnings=parsed.warnings,
    )
