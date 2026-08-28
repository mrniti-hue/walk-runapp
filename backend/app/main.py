from fastapi import FastAPI

from app.api import checkpoints, teams
from app.core.config import settings

app = FastAPI(title="Walk & Run Community API", version="0.1.0")
app.include_router(teams.router)
app.include_router(checkpoints.router)


@app.get("/health")
async def health():
    """Liveness/readiness check — used by Railway and by us to confirm deploy worked."""
    return {"status": "ok", "env": settings.env}
