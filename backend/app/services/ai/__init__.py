from app.services.ai.client import (
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
]
