from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["version"])

_version_file = Path(__file__).resolve().parent.parent.parent.parent / "VERSION"


@router.get("/version")
async def get_version():
    version = (
        _version_file.read_text(encoding="utf-8").strip()
        if _version_file.exists()
        else "unknown"
    )
    return {
        "version": version,
        "name": "Sistema Automacao Boletos - JotaJota",
    }
