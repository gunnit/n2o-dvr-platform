from fastapi import APIRouter

from app.api.v1.ai_feedback import router as ai_feedback_router
from app.api.v1.ambienti import router as ambienti_router
from app.api.v1.attrezzature import router as attrezzature_router
from app.api.v1.auth import router as auth_router
from app.api.v1.aziende import router as aziende_router
from app.api.v1.calculations import router as calculations_router
from app.api.v1.documents import download_router as documents_download_router
from app.api.v1.documents import router as documents_router
from app.api.v1.duvri import router as duvri_router
from app.api.v1.gestanti import router as gestanti_router
from app.api.v1.lookups import router as lookups_router
from app.api.v1.pee_procedures import router as pee_procedures_router
from app.api.v1.persone import router as persone_router
from app.api.v1.pos import router as pos_router
from app.api.v1.rischi import router as rischi_router
from app.api.v1.rischi_misure import router as rischi_misure_router
from app.api.v1.sorveglianza import router as sorveglianza_router
from app.api.v1.sostanze_chimiche import router as sostanze_chimiche_router
from app.api.v1.stress_misure import router as stress_misure_router
from app.api.v1.survey import router as survey_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(aziende_router)
api_router.include_router(persone_router)
api_router.include_router(ambienti_router)
api_router.include_router(attrezzature_router)
api_router.include_router(sostanze_chimiche_router)
api_router.include_router(rischi_router)
api_router.include_router(rischi_misure_router)
api_router.include_router(survey_router)
api_router.include_router(documents_router)
api_router.include_router(documents_download_router)
api_router.include_router(calculations_router)
api_router.include_router(ai_feedback_router)
api_router.include_router(gestanti_router)
api_router.include_router(pee_procedures_router)
api_router.include_router(lookups_router)
api_router.include_router(duvri_router)
api_router.include_router(sorveglianza_router)
api_router.include_router(pos_router)
api_router.include_router(stress_misure_router)
