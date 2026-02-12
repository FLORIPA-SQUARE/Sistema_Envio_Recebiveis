from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, auditoria, email_layout, fidcs, operacoes

app = FastAPI(
    title="Sistema Automação Boletos - JotaJota",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(fidcs.router, prefix="/api/v1")
app.include_router(operacoes.router, prefix="/api/v1")
app.include_router(auditoria.router, prefix="/api/v1")
app.include_router(email_layout.router, prefix="/api/v1")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
