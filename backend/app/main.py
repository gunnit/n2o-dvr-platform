from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings

app = FastAPI(title=settings.APP_NAME, docs_url="/docs", redoc_url="/redoc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Needed so the browser lets the frontend read Content-Disposition
    # (otherwise authenticated downloads lose their server-provided filename).
    expose_headers=["Content-Disposition"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
