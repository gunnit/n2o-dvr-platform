from app.services.risk_calculator import (
    calculate_fire_risk,
    calculate_niosh,
    calculate_risk_index,
)
from app.services.reference_data import (
    DOCUMENT_TYPES,
    ENVIRONMENT_TYPES,
    HAZARD_LIBRARY,
    NIOSH_CP,
    NIOSH_FACTOR_A,
    NIOSH_FACTOR_B,
    NIOSH_FACTOR_C,
    NIOSH_FACTOR_D,
    NIOSH_FACTOR_E,
    NIOSH_FACTOR_F,
    RISK_CATEGORIES,
    RISK_CATEGORY_NAMES,
    get_default_pd,
    get_risks_for_environment,
)
from app.services.document_generator import (
    BaseDocumentGenerator,
    DVRMasterGenerator,
)
from app.services.ai import (
    extract_from_pdf,
    generate_structured,
    generate_text,
    get_client,
)

__all__ = [
    # Risk calculator
    "calculate_risk_index",
    "calculate_niosh",
    "calculate_fire_risk",
    # Reference data
    "RISK_CATEGORIES",
    "RISK_CATEGORY_NAMES",
    "ENVIRONMENT_TYPES",
    "DOCUMENT_TYPES",
    "HAZARD_LIBRARY",
    "NIOSH_FACTOR_A",
    "NIOSH_FACTOR_B",
    "NIOSH_FACTOR_C",
    "NIOSH_FACTOR_D",
    "NIOSH_FACTOR_E",
    "NIOSH_FACTOR_F",
    "NIOSH_CP",
    "get_risks_for_environment",
    "get_default_pd",
    # Document generators
    "BaseDocumentGenerator",
    "DVRMasterGenerator",
    # AI client helpers
    "get_client",
    "generate_text",
    "generate_structured",
    "extract_from_pdf",
]
