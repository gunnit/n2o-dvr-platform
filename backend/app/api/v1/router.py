from fastapi import APIRouter

from app.api.v1.ambienti import router as ambienti_router
from app.api.v1.attrezzature import router as attrezzature_router
from app.api.v1.auth import router as auth_router
from app.api.v1.aziende import router as aziende_router
from app.api.v1.calculations import router as calculations_router
from app.api.v1.documents import router as documents_router
from app.api.v1.persone import router as persone_router
from app.api.v1.rischi import router as rischi_router
from app.api.v1.sostanze_chimiche import router as sostanze_chimiche_router
from app.api.v1.survey import router as survey_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(aziende_router)
api_router.include_router(persone_router)
api_router.include_router(ambienti_router)
api_router.include_router(attrezzature_router)
api_router.include_router(sostanze_chimiche_router)
api_router.include_router(rischi_router)
api_router.include_router(survey_router)
api_router.include_router(documents_router)
api_router.include_router(calculations_router)
