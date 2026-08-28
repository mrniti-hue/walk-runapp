from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class MemberRegisterRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=1, le=120)
    email: str | None = None


class TeamRegisterRequest(BaseModel):
    community_slug: str
    team_name: str = Field(min_length=1, max_length=120)
    members: list[MemberRegisterRequest]

    @field_validator("members")
    @classmethod
    def team_size_between_2_and_4(cls, members: list[MemberRegisterRequest]) -> list[MemberRegisterRequest]:
        if not 2 <= len(members) <= 4:
            raise ValueError("a team must have between 2 and 4 members")
        return members


class MemberCredential(BaseModel):
    member_code: str
    display_name: str
    # Shown once, at registration — only its hash is stored, so this cannot be
    # recovered later. Whoever is registering the team is responsible for
    # delivering it to that member.
    passkey: str


class TeamRegisterResponse(BaseModel):
    team_id: str
    team_code: str
    members: list[MemberCredential]


class LoginRequest(BaseModel):
    passkey: str


class LoginResponse(BaseModel):
    access_token: str
    member_id: str
    team_id: str
    display_name: str


class PositionSubmitRequest(BaseModel):
    lat: float
    lng: float
    accuracy_m: float
    # Device clock — stored for audit only. Never used to decide dwell/quorum;
    # see checkpoints.py for why.
    reported_at: datetime


class PositionSubmitResponse(BaseModel):
    accepted: bool
    reject_reason: str | None
    distance_m: float
    checkpoint_completed: bool


class TeammatePosition(BaseModel):
    member_id: str
    display_name: str
    lat: float | None
    lng: float | None
    updated_at: datetime | None
    distance_from_you_m: float | None


class TeamStatusResponse(BaseModel):
    team_id: str
    team_name: str
    completed_checkpoints: list[str]
    teammates: list[TeammatePosition]
