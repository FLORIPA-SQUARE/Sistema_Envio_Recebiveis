from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["version"])

_version_file = Path(__file__).resolve().parent.parent.parent.parent / "VERSION"
_app_version = (
    _version_file.read_text(encoding="utf-8").strip()
    if _version_file.exists()
    else "unknown"
)


@router.get("/version")
async def get_version():
    return {
        "version": _app_version,
        "name": "Sistema Automacao Boletos - JotaJota",
    }
