from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import auth, auditoria, email_layout, fidcs, operacoes, version

_version_file = Path(__file__).resolve().parent.parent / "VERSION"
_app_version = (
    _version_file.read_text(encoding="utf-8").strip()
    if _version_file.exists()
    else "1.0.0"
)

app = FastAPI(
    title="Sistema Automação Boletos - JotaJota",
    version=_app_version,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(fidcs.router, prefix="/api/v1")
app.include_router(operacoes.router, prefix="/api/v1")
app.include_router(auditoria.router, prefix="/api/v1")
app.include_router(email_layout.router, prefix="/api/v1")
app.include_router(version.router, prefix="/api/v1")

app.mount("/api/v1/assets", StaticFiles(directory="app/assets"), name="assets")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
