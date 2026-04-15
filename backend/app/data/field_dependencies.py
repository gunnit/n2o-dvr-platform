"""Field-to-document dependency catalog (US-5.2 AC3).

Maps survey field paths (e.g. ``persona.mansione``,
``ambiente.superficie_mq``) to the list of generated documents that
consume them. Powers the field-dependency tooltip in the survey form
("changing this updates DVR, PEE, POS").

The catalog is hand-curated — small enough that an explicit list is
clearer (and cheaper) than introspecting generators. When a new
generator starts depending on a field, add the document type here.

Document type identifiers match ``app.services.document_generator.dispatcher``
(``dvr_master``, ``pee_azienda``, ``pee_comune``, ``mmc``, ``vdt``,
``stress``, ``incendio``, ``microclima``, ``gestanti``, ``biologico``,
``duvri``, ``pos``, ``haccp``, ``haccp_forms``).
"""

from __future__ import annotations


# Each key is ``<entity>.<field>`` matching the SQLAlchemy model attribute.
# Values are sorted lists for deterministic UI ordering. Any field NOT in
# this map produces an empty dependency list — the tooltip then shows
# "(nessun documento dipende da questo campo)".
FIELD_DEPENDENCIES: dict[str, list[str]] = {
    # -- Azienda anagrafica ----------------------------------------------
    "azienda.ragione_sociale": [
        "dvr_master",
        "duvri",
        "haccp",
        "haccp_forms",
        "pee_azienda",
        "pee_comune",
        "pos",
    ],
    "azienda.partita_iva": ["dvr_master", "duvri", "pos"],
    "azienda.codice_ateco": ["dvr_master", "duvri", "pos"],
    "azienda.attivita": ["dvr_master", "duvri", "pos"],
    "azienda.sede_legale_via": ["dvr_master", "duvri"],
    "azienda.sede_legale_citta": ["dvr_master", "duvri"],
    "azienda.sede_operativa_via": [
        "dvr_master",
        "duvri",
        "haccp",
        "pee_azienda",
        "pos",
    ],
    "azienda.sede_operativa_citta": [
        "dvr_master",
        "duvri",
        "haccp",
        "pee_azienda",
        "pee_comune",
        "pos",
    ],
    "azienda.orario_lavoro": ["dvr_master", "stress"],
    "azienda.metratura_totale": ["dvr_master", "incendio", "pee_azienda"],
    "azienda.zona_sismica": ["dvr_master", "pee_azienda"],
    "azienda.descrizione_attivita": ["dvr_master", "duvri", "pos"],
    "azienda.contesto_territoriale": ["dvr_master"],
    # -- Persone --------------------------------------------------------
    "persona.nominativo": [
        "dvr_master",
        "duvri",
        "gestanti",
        "haccp",
        "pee_azienda",
        "pos",
    ],
    "persona.mansione": [
        "dvr_master",
        "mmc",
        "vdt",
        "stress",
        "gestanti",
        "haccp",
        "pos",
    ],
    "persona.tipologia_contrattuale": ["dvr_master"],
    "persona.sesso": ["dvr_master", "mmc", "gestanti"],
    "persona.fascia_eta": ["dvr_master", "mmc", "gestanti"],
    "persona.ruolo_rspp": ["dvr_master", "duvri", "pee_azienda"],
    "persona.ruolo_rls": ["dvr_master", "duvri", "pee_azienda"],
    "persona.ruolo_primo_soccorso": ["dvr_master", "pee_azienda", "pee_comune"],
    "persona.ruolo_antincendio": [
        "dvr_master",
        "incendio",
        "pee_azienda",
        "pee_comune",
    ],
    "persona.ruolo_preposto": ["dvr_master", "duvri"],
    "persona.ruolo_datore_lavoro": [
        "dvr_master",
        "duvri",
        "haccp",
        "pee_azienda",
        "pos",
    ],
    "persona.qualifiche": ["dvr_master", "haccp"],
    # -- Ambienti -------------------------------------------------------
    "ambiente.nome": [
        "dvr_master",
        "incendio",
        "microclima",
        "pee_azienda",
        "pee_comune",
    ],
    "ambiente.tipo": [
        "dvr_master",
        "incendio",
        "microclima",
        "biologico",
        "haccp",
    ],
    "ambiente.superficie_mq": [
        "dvr_master",
        "incendio",
        "microclima",
        "pee_azienda",
    ],
    "ambiente.descrizione_attivita": ["dvr_master", "haccp"],
    # -- Attrezzature ---------------------------------------------------
    "attrezzatura.descrizione": ["dvr_master", "mmc", "pos"],
    "attrezzatura.marcatura_ce": ["dvr_master"],
    "attrezzatura.verifiche_periodiche": ["dvr_master"],
    # -- Sostanze chimiche ----------------------------------------------
    "sostanza.nome_prodotto": ["dvr_master", "biologico"],
    "sostanza.produttore": ["dvr_master"],
    "sostanza.pittogrammi": ["dvr_master"],
    "sostanza.frasi_h": ["dvr_master"],
    "sostanza.frasi_p": ["dvr_master"],
    # -- Valutazioni rischio --------------------------------------------
    "rischio.categoria_rischio": ["dvr_master"],
    "rischio.applicabile": ["dvr_master"],
    "rischio.probabilita_p": ["dvr_master"],
    "rischio.danno_d": ["dvr_master"],
    "rischio.misure_prevenzione": ["dvr_master"],
}


def dependencies_for(field_path: str) -> list[str]:
    """Return the document types that consume ``field_path``.

    Returns an empty list if the field isn't catalogued (treat as
    "no known dependencies"). Path matching is exact — callers are
    expected to pass canonical ``entity.field`` strings.
    """
    return list(FIELD_DEPENDENCIES.get(field_path, []))


def all_field_dependencies() -> dict[str, list[str]]:
    """Snapshot for the lookup endpoint — caller-immutable copy."""
    return {k: list(v) for k, v in FIELD_DEPENDENCIES.items()}
