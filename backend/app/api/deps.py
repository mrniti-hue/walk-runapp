from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_member_token
from app.models.team import TeamMember

_bearer = HTTPBearer()


async def get_current_member(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> TeamMember:
    try:
        payload = decode_member_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token")

    member = await db.get(TeamMember, UUID(payload["sub"]))
    if member is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "member_not_found")
    return member
