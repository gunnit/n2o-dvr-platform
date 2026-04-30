"""Seed fixture: ACME MECCANICA COMPOSITA SRL.

A composite real-looking Italian company covering all scenarios needed
to exercise the full 16-document pipeline:
- metalworking (officina)            -> MMC, VDT, Rumore, Vibrazioni, Fire
- internal canteen/kitchen (mensa)   -> HACCP, Biologico Alimentare
- warehouse (magazzino)              -> MMC, Fire, VDT for logistics PC
- office (uffici)                    -> VDT, Stress, Microclima
- chemical storage (deposito)        -> Chemical SDS, Fire
- external construction site         -> POS
- contractor (pulizie industriali)   -> DUVRI
- pregnant worker (gestante)         -> Gestanti

Idempotent: checks whether the azienda already exists before seeding.

Run with:
    python -m app.db.fixtures.acme_meccanica
"""

import asyncio
import logging
import uuid
from datetime import date, datetime

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.ambiente import Ambiente
from app.models.attrezzatura import Attrezzatura
from app.models.azienda import Azienda
from app.models.biologico_valutazione import BiologicoValutazione
from app.models.duvri import Duvri
from app.models.gestanti_valutazione import GestantiValutazione
from app.models.haccp_form import HaccpConfig, HaccpFormState
from app.models.incendio_valutazione import IncendioValutazione
from app.models.microclima_valutazione import MicroclimaValutazione
from app.models.mmc_valutazione import MmcValutazione
from app.models.organization import Organization
from app.models.pee_plan import PeePlan
from app.models.persona import Persona
from app.models.pos import Pos
from app.models.sostanza_chimica import SostanzaChimica
from app.models.stress_valutazione import StressValutazione
from app.models.user import User
from app.models.valutazione_rischio import ValutazioneRischio
from app.models.vdt_valutazione import VdtValutazione

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACME_AZIENDA_NAME = "ACME MECCANICA COMPOSITA SRL"
ACME_ADMIN_EMAIL = "admin@acme-meccanica.test"
ACME_ADMIN_PASSWORD = "Acme2026!"


async def seed_acme(session: AsyncSession) -> Azienda:
    """Seed the Acme Meccanica fixture. Idempotent."""
    # 1. Organization
    result = await session.execute(select(Organization).where(Organization.name == "N2O SRL (demo)"))
    org = result.scalar_one_or_none()
    if not org:
        org = Organization(name="N2O SRL (demo)")
        session.add(org)
        await session.flush()
        log.info("Created organization: N2O SRL (demo)")

    # 2. Admin user
    result = await session.execute(select(User).where(User.email == ACME_ADMIN_EMAIL))
    admin = result.scalar_one_or_none()
    if not admin:
        admin = User(
            organization_id=org.id,
            email=ACME_ADMIN_EMAIL,
            hashed_password=pwd_context.hash(ACME_ADMIN_PASSWORD),
            full_name="Luca Marchetti (demo admin)",
            role="admin",
        )
        session.add(admin)
        await session.flush()
        log.info("Created admin user: %s / %s", ACME_ADMIN_EMAIL, ACME_ADMIN_PASSWORD)

    # 3. Azienda (check by ragione_sociale within this org)
    result = await session.execute(
        select(Azienda).where(Azienda.organization_id == org.id, Azienda.ragione_sociale == ACME_AZIENDA_NAME)
    )
    az = result.scalar_one_or_none()
    if az:
        log.info("Acme already seeded (azienda_id=%s). Skipping.", az.id)
        return az

    az = Azienda(
        organization_id=org.id,
        ragione_sociale=ACME_AZIENDA_NAME,
        partita_iva="04567890123",
        codice_fiscale="04567890123",
        telefono="+39 0521 555 0042",
        email="info@acme-meccanica.it",
        pec="acme.meccanica@pec.it",
        sede_legale_via="Via dell'Industria 42",
        sede_legale_citta="Parma (PR)",
        sede_operativa_via="Via dell'Industria 42",
        sede_operativa_citta="Parma (PR)",
        attivita=(
            "Lavorazioni meccaniche di precisione con mensa aziendale interna e "
            "saltuaria attivita di installazione presso cantieri clienti"
        ),
        codice_ateco="25.62.00",
        orario_lavoro="08:00-17:00 (lun-ven), con pausa mensa 12:30-13:30",
        metratura_totale=2400.0,
        zona_sismica=3,
        descrizione_attivita=(
            "ACME Meccanica Composita S.r.l. opera nel settore delle lavorazioni meccaniche "
            "di precisione e nella prefabbricazione di componenti metallici per il comparto "
            "food & beverage. L'azienda dispone di un'unita produttiva articolata in uffici "
            "tecnici e amministrativi, officina meccanica, magazzino merci, mensa aziendale "
            "con cucina interna, deposito prodotti chimici e area esterna per movimentazione."
        ),
        contesto_territoriale="Zona industriale di Parma, area servita da rete idrica, elettrica e telefonica.",
        survey_status="completed",
    )
    session.add(az)
    await session.flush()
    log.info("Created azienda: %s (%s)", az.ragione_sociale, az.id)

    # 4. Ambienti
    ambienti_data = [
        {"nome": "Uffici amministrativi e tecnici", "tipo": "Ufficio", "superficie_mq": 220, "desc": "Uffici con postazioni VDT"},
        {"nome": "Officina meccanica", "tipo": "Officina", "superficie_mq": 850, "desc": "Tornitura, fresatura, saldatura"},
        {"nome": "Magazzino materie prime e prodotti finiti", "tipo": "Magazzino", "superficie_mq": 620, "desc": "Scaffalature, carrelli elevatori"},
        {"nome": "Mensa aziendale con cucina", "tipo": "Cucina", "superficie_mq": 180, "desc": "Preparazione, cottura, somministrazione pasti"},
        {"nome": "Deposito prodotti chimici", "tipo": "Magazzino", "superficie_mq": 90, "desc": "Stoccaggio oli e detergenti industriali"},
        {"nome": "Area esterna e cantiere temporaneo", "tipo": "Esterno", "superficie_mq": 440, "desc": "Movimentazione e stoccaggio esterno"},
    ]
    ambienti: list[Ambiente] = []
    for a in ambienti_data:
        amb = Ambiente(
            azienda_id=az.id,
            nome=a["nome"],
            tipo=a["tipo"],
            superficie_mq=a["superficie_mq"],
            descrizione_attivita=a["desc"],
        )
        session.add(amb)
        ambienti.append(amb)
    await session.flush()
    log.info("Created %d ambienti", len(ambienti))

    # 5. Persone (18)
    persone_data = [
        {"nome": "Mario Rossi",        "mans": "Datore di Lavoro", "role_dl": True},
        {"nome": "Luca Bianchi",       "mans": "RSPP",             "role_rspp": True},
        {"nome": "Giulia Verdi",       "mans": "RLS",              "role_rls": True},
        {"nome": "Dott. Paolo Neri",   "mans": "Medico Competente", "role_mc": True},
        {"nome": "Franco Gialli",      "mans": "Preposto Officina",       "role_prep": True, "role_anti": True},
        {"nome": "Antonio Marrone",    "mans": "Operaio Tornitore",       "role_ps": True},
        {"nome": "Giuseppe Russo",     "mans": "Operaio Fresatore"},
        {"nome": "Marco Esposito",     "mans": "Operaio Saldatore",       "role_anti": True},
        {"nome": "Davide Romano",      "mans": "Operaio Montatore"},
        {"nome": "Elena Colombo",      "mans": "Impiegata amministrativa", "role_ps": True},
        {"nome": "Sara Ferrari",       "mans": "Impiegata tecnica"},
        {"nome": "Laura Galli",        "mans": "Impiegata commerciale",   "sesso": "F"},
        {"nome": "Maria Conti",        "mans": "Cuoca (mensa)",           "sesso": "F"},
        {"nome": "Anna Ricci",         "mans": "Aiuto cuoca (mensa)",     "sesso": "F"},
        {"nome": "Roberto Moretti",    "mans": "Magazziniere",            "role_ps": True},
        {"nome": "Francesco Costa",    "mans": "Magazziniere - Carrellista"},
        {"nome": "Valentina Rinaldi",  "mans": "Impiegata tecnica (GESTANTE)", "sesso": "F"},
        {"nome": "Matteo Ferri",       "mans": "Apprendista Operaio",     "fascia": "<18"},
    ]
    persone: dict[str, Persona] = {}
    for p in persone_data:
        pers = Persona(
            azienda_id=az.id,
            nominativo=p["nome"],
            mansione=p["mans"],
            tipologia_contrattuale="Indeterminato",
            sesso=p.get("sesso", "M"),
            fascia_eta=p.get("fascia", ">18"),
            ruolo_rspp=bool(p.get("role_rspp")),
            ruolo_rls=bool(p.get("role_rls")),
            ruolo_primo_soccorso=bool(p.get("role_ps")),
            ruolo_antincendio=bool(p.get("role_anti")),
            ruolo_preposto=bool(p.get("role_prep")),
            ruolo_datore_lavoro=bool(p.get("role_dl")),
            ruolo_medico_competente=bool(p.get("role_mc")),
        )
        session.add(pers)
        persone[p["nome"]] = pers
    await session.flush()
    log.info("Created %d persone", len(persone))

    # Link persone <-> ambienti via raw insert into junction table to avoid
    # async lazy-load on the M2M relationship.
    from app.models.persone_ambienti import persone_ambienti
    (ufficio, officina, magazzino, mensa, deposito, esterno) = ambienti
    pairs: list[tuple[uuid.UUID, uuid.UUID]] = []
    for amb, names in [
        (officina, ["Franco Gialli", "Antonio Marrone", "Giuseppe Russo", "Marco Esposito", "Davide Romano", "Matteo Ferri"]),
        (ufficio, ["Mario Rossi", "Luca Bianchi", "Elena Colombo", "Sara Ferrari", "Laura Galli", "Valentina Rinaldi"]),
        (magazzino, ["Roberto Moretti", "Francesco Costa"]),
        (mensa, ["Maria Conti", "Anna Ricci"]),
        (deposito, ["Franco Gialli", "Roberto Moretti"]),
        (esterno, ["Franco Gialli", "Marco Esposito", "Davide Romano"]),
    ]:
        for n in names:
            pairs.append((persone[n].id, amb.id))
    if pairs:
        await session.execute(
            persone_ambienti.insert(),
            [{"persona_id": pid, "ambiente_id": aid} for pid, aid in pairs],
        )

    # Assign Franco Gialli as preposto on the ambienti he supervises.
    # Without this, the DVR Master ambiente identity table renders
    # "Preposto per la sicurezza: —" everywhere.
    franco_id = persone["Franco Gialli"].id
    for amb in (officina, deposito, esterno):
        amb.preposto_id = franco_id
    await session.flush()

    # 6. Attrezzature (12)
    attrezzature_data = [
        ("Tornio parallelo CNC", True, True),
        ("Fresatrice a controllo numerico", True, True),
        ("Saldatrice MIG/MAG", True, True),
        ("Trapano a colonna", True, False),
        ("Carrello elevatore elettrico", True, True),
        ("Postazione VDT uffici 1", True, False),
        ("Postazione VDT uffici 2", True, False),
        ("Postazione VDT uffici 3", True, False),
        ("Postazione VDT uffici 4", True, False),
        ("Forno elettrico industriale (mensa)", True, True),
        ("Frigorifero verticale (mensa)", True, True),
        ("Transpallet manuale", True, False),
    ]
    for desc, ce, verifiche in attrezzature_data:
        session.add(Attrezzatura(azienda_id=az.id, descrizione=desc, marcatura_ce=ce, verifiche_periodiche=verifiche))
    log.info("Created %d attrezzature", len(attrezzature_data))

    # 7. Sostanze chimiche (8)
    sostanze_data = [
        {"nome": "Olio da taglio solubile emulsionabile", "prod": "ChemCo", "pitto": ["GHS07"], "h": ["H315", "H319"], "p": ["P264", "P280", "P305+P351+P338"], "stato": "Liquido"},
        {"nome": "Sgrassante industriale alcalino",       "prod": "CleanSpa", "pitto": ["GHS05", "GHS07"], "h": ["H314", "H335"], "p": ["P260", "P280", "P303+P361+P353"], "stato": "Liquido"},
        {"nome": "Disinfettante per superfici cucina",    "prod": "FoodSafe", "pitto": ["GHS07"], "h": ["H319"], "p": ["P264", "P305+P351+P338"], "stato": "Liquido"},
        {"nome": "Detergente lavastoviglie professionale", "prod": "CleanSpa", "pitto": ["GHS05"], "h": ["H314"], "p": ["P260", "P280", "P310"], "stato": "Liquido"},
        {"nome": "Gas di saldatura (Argon + CO2)",        "prod": "GasTech", "pitto": ["GHS04"], "h": ["H280"], "p": ["P410+P403"], "stato": "Gas compresso"},
        {"nome": "Solvente per pulitura metalli",         "prod": "ChemCo", "pitto": ["GHS02", "GHS07"], "h": ["H226", "H336"], "p": ["P210", "P233", "P240"], "stato": "Liquido"},
        {"nome": "Anticalcare industriale",               "prod": "CleanSpa", "pitto": ["GHS05"], "h": ["H314"], "p": ["P260", "P280", "P301+P330+P331"], "stato": "Liquido"},
        {"nome": "Olio idraulico",                        "prod": "LubTech", "pitto": [], "h": [], "p": [], "stato": "Liquido"},
    ]
    for s in sostanze_data:
        session.add(SostanzaChimica(
            azienda_id=az.id,
            nome_prodotto=s["nome"],
            produttore=s["prod"],
            attivita_uso="Uso produttivo",
            pittogrammi=s["pitto"],
            stato_miscela=s["stato"],
            frasi_h=s["h"],
            frasi_p=s["p"],
            ai_extracted=False,
            human_reviewed=True,
        ))
    log.info("Created %d sostanze chimiche", len(sostanze_data))

    # 8. ValutazioneRischio per ambiente (cover 11 categories; simplified representative risks)
    from app.services.reference_data import RISK_CATEGORY_NAMES
    for amb in ambienti:
        for cat in RISK_CATEGORY_NAMES:
            # Assign P/D values varying by ambiente+category (simple heuristic)
            p, d = _heuristic_pd(amb.tipo, cat)
            applicabile = not (amb.tipo == "Esterno" and cat in ("Impianti Elettrici",))
            session.add(ValutazioneRischio(
                ambiente_id=amb.id,
                categoria_rischio=cat,
                applicabile=applicabile,
                pericolo=f"Rischio {cat} in {amb.nome}",
                condizioni_esposizione="Esposizione durante attivita lavorative ordinarie",
                rischio=f"Possibile esposizione a {cat.lower()}",
                misure_prevenzione="Misure tecniche, organizzative, DPI e formazione specifica.",
                probabilita_p=p if applicabile else None,
                danno_d=d if applicabile else None,
            ))
    log.info("Created %d valutazioni rischio", len(ambienti) * len(RISK_CATEGORY_NAMES))

    # 9. MMC (NIOSH) - 2 tasks
    plr1 = 25 * 0.93 * 0.93 * 0.83 * 0.85 * 1.0 * 0.88
    ir1 = 15 / plr1
    session.add(MmcValutazione(
        azienda_id=az.id, persona_id=persone["Antonio Marrone"].id, ambiente_id=officina.id,
        compito="Carico/scarico pezzi grezzi dal magazzino al tornio",
        peso_kg=15.0, sesso="M", fascia_eta=">18",
        altezza_cm=50, dislocazione_cm=50, distanza_cm=30,
        angolo_gradi=30, giudizio_presa="Buono",
        frequenza_atti_min=2.0, durata_min=120,
        cp=25.0, fattore_a=0.93, fattore_b=0.93, fattore_c=0.83, fattore_d=0.85, fattore_e=1.0, fattore_f=0.88,
        plr=plr1, indice_ir=ir1,
        livello_rischio="GIALLO" if ir1 > 0.75 else "VERDE",
        area_classificazione="Gialla" if ir1 > 0.75 else "Verde",
        misure_proposte=(
            "Introdurre carrello a sponde ribaltabili per ridurre la flessione del "
            "tronco; sorveglianza sanitaria mirata; formazione art. 169 D.Lgs. 81/08."
        ),
    ))
    plr2 = 25 * 1.0 * 1.0 * 1.0 * 1.0 * 1.0 * 0.95
    ir2 = 12 / plr2
    session.add(MmcValutazione(
        azienda_id=az.id, persona_id=persone["Roberto Moretti"].id, ambiente_id=magazzino.id,
        compito="Movimentazione scatole materie prime dal pallet allo scaffale",
        peso_kg=12.0, sesso="M", fascia_eta=">18",
        altezza_cm=75, dislocazione_cm=25, distanza_cm=25,
        angolo_gradi=0, giudizio_presa="Buono",
        frequenza_atti_min=0.5, durata_min=60,
        cp=25.0, fattore_a=1.0, fattore_b=1.0, fattore_c=1.0, fattore_d=1.0, fattore_e=1.0, fattore_f=0.95,
        plr=plr2, indice_ir=ir2,
        livello_rischio="VERDE",
        area_classificazione="Verde",
        misure_proposte=(
            "Mantenere le condizioni operative attuali; rivalutazione in occasione "
            "di modifiche del ciclo produttivo."
        ),
    ))

    # 10. VDT (4 postazioni) — each worker seeded with a different
    # surveillance cadence so the US-3.5 "Visite in scadenza" / "Visite
    # scadute" dashboard widgets have demonstrable content out of the box.
    # Dates are anchored against date.today() so the fixture stays
    # relevant whenever it is re-seeded.
    from datetime import timedelta as _td
    today = date.today()
    vdt_seed = [
        # (name, over_50, last_visit offset from today, postazione)
        ("Elena Colombo", False, _td(days=-365 * 5 - 20), "Ufficio 1"),   # 5y+20d ago -> 20d SCADUTA
        ("Sara Ferrari", False, _td(days=-365 * 5 + 45), "Ufficio 2"),    # 5y-45d ago -> 45d IN_SCADENZA
        ("Laura Galli", True, _td(days=-365 * 2 + 15), "Ufficio 3"),      # 50+, 2y-15d -> 15d IN_SCADENZA
        ("Valentina Rinaldi", False, _td(days=-30), "Ufficio 4"),         # just had visit -> FUTURE
    ]
    for name, over_50, last_offset, postazione in vdt_seed:
        last_visit = today + last_offset
        cadence_years = 2 if over_50 else 5
        # Clamp Feb 29 to Feb 28 for non-leap destinations.
        try:
            next_visit = last_visit.replace(year=last_visit.year + cadence_years)
        except ValueError:
            next_visit = last_visit.replace(year=last_visit.year + cadence_years, day=28)
        session.add(VdtValutazione(
            azienda_id=az.id, persona_id=persone[name].id, ambiente_id=ufficio.id,
            postazione=postazione,
            ore_settimanali=32.0, esposto=True,
            idoneita_visiva="idoneo",
            periodicita_sorveglianza="biennale" if over_50 else "quinquennale",
            data_ultima_visita=last_visit,
            data_prossima_visita=next_visit,
            eta_50_plus=over_50,
        ))

    # 11. Stress — INAIL (computed later, but store the area payloads)
    session.add(StressValutazione(
        azienda_id=az.id,
        gruppo_omogeneo="Azienda intera",
        area_a_eventi_sentinella={"infortuni_biennio": 1, "assenze_malattia": 5, "turnover": 2},
        area_b_contenuto_lavoro={"monotonia": False, "ritmi_elevati": True, "lavoro_turni": False},
        area_c_contesto_lavoro={"comunicazione": True, "autonomia": True, "conflitti": False},
        punteggio_a=2, punteggio_b=3, punteggio_c=1,
        punteggio_totale=6, livello_rischio="BASSO",
        misure_correttive="Mantenimento delle attuali misure di prevenzione. Monitoraggio annuale.",
    ))

    # 12. Incendio (1 per ambiente, INF+SI+PI)
    fire_configs = [
        (ufficio.id, 1, 2, 2),   # low flammability, few ignition sources, some people
        (officina.id, 3, 3, 2),  # saldatrice, oli -> high
        (magazzino.id, 2, 1, 1),
        (mensa.id, 2, 3, 2),     # cucina -> high ignition
        (deposito.id, 3, 2, 1),  # chimici
        (esterno.id, 1, 1, 1),
    ]
    for amb_id, inf, si, pi in fire_configs:
        session.add(IncendioValutazione(
            azienda_id=az.id, ambiente_id=amb_id,
            inf=inf, si=si, pi=pi,
            misure_prevenzione="Estintori portatili a CO2 e polvere, idranti UNI 45, uscite di emergenza segnalate",
            estintori_presenti=4, idranti_presenti=2, uscite_emergenza=2,
        ))

    # 13. Microclima (1 per ambiente interno)
    micro_configs = [
        (ufficio.id, "moderato", 21.0, 21.0, 0.1, 50.0, 1.2, 0.7),
        (officina.id, "moderato", 19.0, 20.0, 0.2, 55.0, 1.6, 0.8),
        (magazzino.id, "moderato", 18.0, 18.0, 0.3, 55.0, 1.8, 0.8),
        (mensa.id, "severo_caldo", 28.0, 30.0, 0.1, 60.0, 1.7, 0.5),
        (deposito.id, "moderato", 18.0, 18.0, 0.2, 60.0, 1.3, 0.7),
    ]
    for (amb_id, tipo, t_air, t_rad, v_air, rh, met, clo) in micro_configs:
        session.add(MicroclimaValutazione(
            azienda_id=az.id, ambiente_id=amb_id,
            tipo_ambiente=tipo,
            temperatura_aria=t_air, temperatura_radiante=t_rad,
            velocita_aria=v_air, umidita_relativa=rh,
            metabolismo=met, isolamento_vestiario=clo,
        ))

    # 14. Gestanti
    session.add(GestantiValutazione(
        azienda_id=az.id, persona_id=persone["Valentina Rinaldi"].id,
        stato="gestante",
        data_notifica=date(2026, 3, 20),
        data_presunto_parto=date(2026, 10, 15),
        rischi_vietati=[
            {"rischio": "Posizioni di lavoro prolungate in piedi", "allegato": "A", "misura": "Astensione anticipata prevista art. 17"},
            {"rischio": "Movimentazione carichi > 3 kg", "allegato": "A", "misura": "Mansione alternativa in ufficio"},
        ],
        misure_adeguamento="Assegnata a mansione di supporto amministrativo seduta con possibilita di alternanza posturale.",
        mansione_alternativa="Impiegata amministrativa back-office",
        richiesta_astensione_anticipata=False,
        firma_lavoratrice="Valentina Rinaldi",
        firma_datore_lavoro="Mario Rossi",
        firma_rspp="Luca Bianchi",
        firma_medico_competente="Dott. Paolo Neri",
    ))

    # 15. Biologico (settore alimentare — mensa)
    session.add(BiologicoValutazione(
        azienda_id=az.id, settore="alimentare", ambiente_id=mensa.id,
        agenti_identificati=[
            {"nome": "Salmonella spp.", "gruppo": "2", "via": "ingestione"},
            {"nome": "Listeria monocytogenes", "gruppo": "2", "via": "ingestione"},
            {"nome": "Escherichia coli (ceppi patogeni)", "gruppo": "2", "via": "ingestione"},
        ],
        misure_protettive=[
            {"descrizione": "Catena del freddo ≤ 4°C per prodotti deperibili"},
            {"descrizione": "Cottura a cuore ≥ 75°C per carni"},
            {"descrizione": "Sanificazione piani di lavoro dopo ogni preparazione"},
        ],
        dpi_richiesti=[
            {"descrizione": "Camice monouso, copricapo, guanti monouso, mascherina se impaglottinante"},
        ],
        protocollo_sanitario="Sorveglianza sanitaria annuale, esami feci pre-assunzione, vaccinazione epatite A",
        formazione_specifica="Corso HACCP base + aggiornamento biennale",
        livello_rischio="MEDIO",
    ))

    # 16. HACCP config + forms
    session.add(HaccpConfig(
        azienda_id=az.id,
        tipologia_attivita="Mensa aziendale con cucina interna",
        numero_pasti_giorno=60,
        tipi_alimenti_trattati=["carne fresca", "pesce fresco", "verdure", "latticini", "cereali", "surgelati"],
        ccps=[
            {"codice": "CCP1", "nome": "Ricevimento merci", "limite_critico": "Temperatura ≤ 4°C per deperibili"},
            {"codice": "CCP2", "nome": "Stoccaggio frigorifero", "limite_critico": "0-4°C frigo; -18°C congelatore"},
            {"codice": "CCP3", "nome": "Cottura", "limite_critico": "T > 75°C al cuore"},
            {"codice": "CCP4", "nome": "Raffreddamento rapido", "limite_critico": "Da 60 a 10°C in max 2 ore"},
            {"codice": "CCP5", "nome": "Somministrazione", "limite_critico": "Caldi > 60°C, freddi < 10°C"},
        ],
        responsabile_haccp="Maria Conti",
    ))
    HACCP_FORMS = [
        ("SA-01", "Elenco fornitori qualificati"),
        ("SA-02", "Registro ricevimento merci"),
        ("SA-03", "Controllo temperature frigoriferi"),
        ("SA-04", "Controllo temperature congelatori"),
        ("SA-05", "Registro derattizzazione"),
        ("SA-06", "Registro sanificazione ambienti"),
        ("SA-07", "Controllo temperature cottura"),
        ("SA-08", "Registro raffreddamento rapido"),
        ("SA-09", "Controllo olio friggitrice"),
        ("SA-10", "Controllo acqua potabile"),
        ("SA-11", "Registro formazione personale"),
        ("SA-12", "Schede tecniche prodotti"),
        ("SA-13", "Non conformita e azioni correttive"),
        ("SA-14", "Controllo allergeni"),
        ("SA-15", "Registro pulizia attrezzature"),
        ("SA-16", "Piano autocontrollo annuale"),
    ]
    for code, title in HACCP_FORMS:
        session.add(HaccpFormState(azienda_id=az.id, form_code=code, form_title=title, data={"righe": []}))

    # 17. PEE (azienda)
    squadra = [
        {"nome": persone["Franco Gialli"].nominativo, "ruolo": "Coordinatore emergenza"},
        {"nome": persone["Marco Esposito"].nominativo, "ruolo": "Antincendio"},
        {"nome": persone["Roberto Moretti"].nominativo, "ruolo": "Primo soccorso"},
        {"nome": persone["Antonio Marrone"].nominativo, "ruolo": "Primo soccorso"},
    ]
    session.add(PeePlan(
        azienda_id=az.id, tipo="azienda",
        squadra_emergenza=squadra,
        addetti_primo_soccorso=[s for s in squadra if s["ruolo"] == "Primo soccorso"],
        addetti_antincendio=[s for s in squadra if s["ruolo"] == "Antincendio"],
        coordinatore_emergenza="Franco Gialli",
        telefoni_emergenza={
            "Numero unico europeo emergenze": "112",
            "Vigili del Fuoco": "115",
            "Pronto Soccorso": "118",
            "Carabinieri": "112",
            "Coordinatore interno": "+39 0521 000000",
        },
        scenari=[
            {"codice": "A", "titolo": "Incendio", "procedura": "Attivare allarme, chiamare 115, evacuare verso punto di raccolta"},
            {"codice": "B", "titolo": "Infortunio grave", "procedura": "Non spostare il ferito, chiamare 118, applicare primo soccorso"},
            {"codice": "C", "titolo": "Sversamento chimico", "procedura": "Isolare area, indossare DPI, assorbire con materiale idoneo"},
            {"codice": "D", "titolo": "Black-out", "procedura": "Illuminazione emergenza, sospensione macchine, evacuazione se prolungato"},
            {"codice": "E", "titolo": "Evento sismico", "procedura": "Mettersi sotto tavoli/architravi, evacuare a scossa terminata"},
        ],
        punto_raccolta="Piazzale antistante ingresso Via dell'Industria 42",
        vie_fuga="Uscita principale nord, uscita emergenza sud officina, uscita mensa ovest",
        tempo_evacuazione_stimato_min=3,
        frequenza_prove="annuale",
    ))
    # PEE comune (edificio condiviso) — optional second plan
    session.add(PeePlan(
        azienda_id=az.id, tipo="comune",
        squadra_emergenza=squadra,
        addetti_primo_soccorso=[s for s in squadra if s["ruolo"] == "Primo soccorso"],
        addetti_antincendio=[s for s in squadra if s["ruolo"] == "Antincendio"],
        coordinatore_emergenza="Franco Gialli",
        telefoni_emergenza={"Numero unico europeo": "112"},
        scenari=[],
        punto_raccolta="Piazzale condominiale comune",
        vie_fuga="Scale antincendio nord e sud",
        frequenza_prove="annuale",
    ))

    # 18. DUVRI
    session.add(Duvri(
        azienda_id=az.id,
        appaltatore_ragione_sociale="Pulizie Industriali Parma S.R.L.",
        appaltatore_partita_iva="01234567890",
        appaltatore_referente="Giovanni Pulito",
        oggetto_appalto="Servizio di pulizia giornaliera di uffici, officina e mensa",
        data_inizio=date(2026, 5, 1),
        data_fine=date(2027, 4, 30),
        importo_appalto=42000.00,
        interferenze=[
            {"rischio": "Scivolamento su pavimento bagnato", "misure": "Segnaletica e coordinamento orari", "dpi": ["scarpe antiscivolo"]},
            {"rischio": "Contatto con prodotti chimici di pulizia", "misure": "SDS comunicate", "dpi": ["guanti nitrile", "mascherina"]},
            {"rischio": "Interferenza con carrelli elevatori", "misure": "Orari scaglionati, corridoi dedicati", "dpi": ["gilet alta visibilita"]},
        ],
        costi_sicurezza=850.00,
    ))

    # 19. POS
    session.add(Pos(
        azienda_id=az.id,
        cantiere_indirizzo="Via dei Molini 15, Parma (PR)",
        cantiere_descrizione="Installazione linea meccanica presso stabilimento cliente",
        committente="Food&Pack SpA",
        direttore_lavori="Ing. Stefano Mazzi",
        coordinatore_sicurezza="Arch. Laura Bruni",
        data_inizio=date(2026, 6, 1),
        data_fine=date(2026, 7, 15),
        importo_lavori=85000.00,
        numero_massimo_lavoratori=4,
        fasi_lavorative=[
            {"fase": "Allestimento cantiere", "descrizione": "Delimitazione, segnaletica, baraccamenti", "rischi": ["caduta", "investimento"], "dpi": ["casco", "scarpe antinfortunistiche", "gilet alta visibilita"], "mezzi": ["furgone", "gru"]},
            {"fase": "Posa componenti meccanici", "descrizione": "Montaggio linea di produzione", "rischi": ["schiacciamento", "MMC", "cesoiamento"], "dpi": ["guanti", "casco"], "mezzi": ["transpallet", "carroponte cliente"]},
            {"fase": "Collegamenti elettrici", "descrizione": "Cablaggio bordo macchina", "rischi": ["elettrico"], "dpi": ["guanti dielettrici"], "mezzi": ["attrezzi isolati"]},
            {"fase": "Collaudi e test", "descrizione": "Verifica funzionale linea", "rischi": ["rumore", "proiezioni"], "dpi": ["otoprotettori", "occhiali"], "mezzi": []},
            {"fase": "Smontaggio cantiere", "descrizione": "Rimozione baraccamenti, pulizia", "rischi": ["MMC"], "dpi": ["guanti"], "mezzi": ["furgone"]},
        ],
        valutazione_rumore={"lex_8h_dba": 82, "fascia": "80-85", "dpi_obbligatori": True},
        valutazione_vibrazioni={"a8_mano_braccio": 2.1, "a8_corpo_intero": 0.4, "entro_limiti": True},
        mezzi_attrezzature=[
            {"tipo": "Transpallet manuale"},
            {"tipo": "Avvitatori a batteria"},
            {"tipo": "Attrezzatura da saldatura portatile"},
        ],
        sostanze_pericolose=[
            {"nome": "Solvente per pulitura metalli", "uso": "Preparazione superfici"},
        ],
    ))

    await session.commit()
    log.info("=" * 50)
    log.info("Acme Meccanica Composita SRL seeded successfully")
    log.info("  azienda_id: %s", az.id)
    log.info("  organization_id: %s", org.id)
    log.info("  admin login: %s / %s", ACME_ADMIN_EMAIL, ACME_ADMIN_PASSWORD)
    log.info("=" * 50)
    return az


def _heuristic_pd(ambiente_tipo: str, categoria: str) -> tuple[int, int]:
    """Produce plausible P, D values for ambiente/categoria pairs."""
    # Higher risk combinations
    high = {
        ("Officina", "Macchine"): (3, 3),
        ("Officina", "Agenti Fisici"): (3, 2),
        ("Officina", "Incendio-Esplosioni"): (2, 3),
        ("Magazzino", "Fattori Ergonomici"): (3, 2),
        ("Cucina", "Incendio-Esplosioni"): (2, 3),
        ("Cucina", "Agenti Biologici"): (2, 2),
        ("Ufficio", "Fattori Psicologici"): (2, 2),
    }
    if (ambiente_tipo, categoria) in high:
        return high[(ambiente_tipo, categoria)]
    return (1, 2)  # default low-medium


async def main() -> None:
    async with async_session_factory() as session:
        await seed_acme(session)


if __name__ == "__main__":
    asyncio.run(main())
