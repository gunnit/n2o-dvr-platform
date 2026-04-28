from app.services.ai.attrezzature_suggester import (
    AttrezzaturaSuggerita,
    AttrezzatureSuggerite,
    suggest_attrezzature,
)
from app.services.ai.attrezzature_vision_extractor import (
    AttrezzaturaIdentificata,
    AttrezzatureIdentificate,
    extract_attrezzature_from_photos,
)
from app.services.ai.client import (
    extract_from_images,
    extract_from_pdf,
    generate_structured,
    generate_text,
    get_client,
)
from app.services.ai.company_description import generate_company_description
from app.services.ai.improvement_measures import (
    MisuraSuggerita,
    MisureSuggerite,
    suggest_measures,
)
from app.services.ai.mansione_protocol_suggester import (
    MansioneProtocolSuggerito,
    suggest_mansione_protocol,
)
from app.services.ai.rischi_suggester import (
    RischiSuggeriti,
    RischioSuggerito,
    suggest_rischi,
)
from app.services.ai.sds_extractor import (
    extract_sds,
    is_failed_extraction,
    low_confidence_fields,
    to_db_dict,
)

__all__ = [
    # Generic helpers
    "get_client",
    "generate_text",
    "generate_structured",
    "extract_from_pdf",
    "extract_from_images",
    # SDS extraction
    "extract_sds",
    "to_db_dict",
    "low_confidence_fields",
    "is_failed_extraction",
    # Company description
    "generate_company_description",
    # Improvement measures
    "suggest_measures",
    "MisuraSuggerita",
    "MisureSuggerite",
    # Attrezzature suggestions (Phase 5.3)
    "suggest_attrezzature",
    "AttrezzaturaSuggerita",
    "AttrezzatureSuggerite",
    # Attrezzature vision extraction (from ambiente photos)
    "extract_attrezzature_from_photos",
    "AttrezzaturaIdentificata",
    "AttrezzatureIdentificate",
    # Mansione protocol suggestions (Phase 5.1 + 5.2)
    "suggest_mansione_protocol",
    "MansioneProtocolSuggerito",
    # Rischi suggestions per ambiente (Phase 8.3)
    "suggest_rischi",
    "RischioSuggerito",
    "RischiSuggeriti",
]
