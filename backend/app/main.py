from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import checkpoints, teams
from app.core.config import settings

app = FastAPI(title="Walk & Run Community API", version="0.1.0")
app.include_router(teams.router)
app.include_router(checkpoints.router)
# Same-origin test client — talks to the API above with plain fetch(), no CORS
# setup needed. Not the Phase 3 participant app (see README), just enough to
# exercise the login/checkin flow from an actual phone browser.
app.mount("/app", StaticFiles(directory="app/static", html=True), name="static")


@app.get("/health")
async def health():
    """Liveness/readiness check — used by Railway and by us to confirm deploy worked."""
    return {"status": "ok", "env": settings.env}
