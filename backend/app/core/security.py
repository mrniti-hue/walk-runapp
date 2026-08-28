import time

import jwt

from app.core.config import settings

_ALGORITHM = "HS256"
# One event day plus margin — long enough that a member isn't logged out
# mid-route, short enough that a leaked token doesn't stay valid for weeks.
_TOKEN_TTL_SECONDS = 16 * 60 * 60


def create_member_token(member_id: str, team_id: str) -> str:
    now = int(time.time())
    payload = {"sub": member_id, "team_id": team_id, "iat": now, "exp": now + _TOKEN_TTL_SECONDS}
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_member_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
