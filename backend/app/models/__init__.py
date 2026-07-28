from app.models.organization import Organization
from app.models.user import User
from app.models.azienda import Azienda
from app.models.persona import Persona
from app.models.ambiente import Ambiente
from app.models.ambiente_foto import AmbienteFoto
from app.models.persone_ambienti import persone_ambienti
from app.models.attrezzatura import Attrezzatura
from app.models.sostanza_chimica import SostanzaChimica
from app.models.valutazione_rischio import ValutazioneRischio
from app.models.pericolo_libreria import PericoloLibreria
from app.models.pericolo_valutazione import PericoloValutazione
from app.models.documento_generato import DocumentoGenerato

# Assessment-specific models (Wave 1.1)
from app.models.mmc_valutazione import MmcValutazione
from app.models.vdt_valutazione import VdtValutazione
from app.models.stress_valutazione import StressValutazione
from app.models.incendio_valutazione import IncendioValutazione
from app.models.microclima_valutazione import MicroclimaValutazione
from app.models.gestanti_valutazione import GestantiValutazione
from app.models.biologico_valutazione import BiologicoValutazione
from app.models.rischio_chimico_esposizione import RischioChimicoEsposizione
from app.models.stress_misura_libreria import StressMisuraLibreria
from app.models.rischio_misura_libreria import RischioMisuraLibreria
from app.models.misura_miglioramento import MisuraMiglioramento

# Complementary document models
from app.models.haccp_form import HaccpConfig, HaccpFormState
from app.models.pee_plan import PeePlan
from app.models.duvri import Duvri
from app.models.pos import Pos

# Monetization (billing Phase 0). Plan catalogue + entitlement/usage records.
# Imported here so `from app.models import *` in alembic/env.py registers them
# on Base.metadata for autogenerate.
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.usage_counter import UsageCounter
from app.models.ai_usage_event import AiUsageEvent
from app.models.active_company_period import ActiveCompanyPeriod
from app.models.billing_webhook_event import BillingWebhookEvent
from app.models.credit_purchase import CreditPurchase

# Cross-cutting
from app.models.audit_log import AuditLog
from app.models.ai_feedback import AiFeedback
from app.models.user_feedback import UserFeedback
from app.models.description_revision import DescriptionRevision

__all__ = [
    "Organization",
    "User",
    "Azienda",
    "Persona",
    "Ambiente",
    "AmbienteFoto",
    "persone_ambienti",
    "Attrezzatura",
    "SostanzaChimica",
    "ValutazioneRischio",
    "PericoloLibreria",
    "PericoloValutazione",
    "DocumentoGenerato",
    "MmcValutazione",
    "VdtValutazione",
    "StressValutazione",
    "IncendioValutazione",
    "MicroclimaValutazione",
    "GestantiValutazione",
    "BiologicoValutazione",
    "RischioChimicoEsposizione",
    "StressMisuraLibreria",
    "RischioMisuraLibreria",
    "MisuraMiglioramento",
    "HaccpConfig",
    "HaccpFormState",
    "PeePlan",
    "Duvri",
    "Pos",
    "Plan",
    "Subscription",
    "UsageCounter",
    "AiUsageEvent",
    "ActiveCompanyPeriod",
    "BillingWebhookEvent",
    "CreditPurchase",
    "AuditLog",
    "AiFeedback",
    "UserFeedback",
    "DescriptionRevision",
]
