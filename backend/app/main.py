from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(title="Walk & Run Community API", version="0.1.0")


@app.get("/health")
async def health():
    """Liveness/readiness check — used by Railway and by us to confirm deploy worked."""
    return {"status": "ok", "env": settings.env}
