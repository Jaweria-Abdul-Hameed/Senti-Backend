import datetime
import re
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize_text(value: str) -> str:
    """Strip null bytes and other non-printable control characters from
    free-typed user text before it's stored. These have no legitimate use in
    a username/title/message and are sometimes used to break downstream
    parsers, log files, or terminal-based tooling that later reads this data.
    Ordinary whitespace (space, tab \\x09, newline \\x0a, carriage return
    \\x0d) is left alone since messages are allowed to span multiple lines."""
    return _CONTROL_CHARS_RE.sub("", value)


def _validate_password_strength(password: str) -> str:
    """Shared rule for anywhere a user sets/resets a password:
    at least 8 chars, one letter, one digit. Kept intentionally simple —
    strict rules (special-char requirements etc.) mostly push people
    toward "Password1!" and password reuse, not stronger passwords."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one number")
    return password


# --- Users / Auth ---

class SignUpRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(max_length=128)

    @field_validator("username")
    @classmethod
    def strip_username(cls, v: str) -> str:
        v = _sanitize_text(v).strip()
        if not v:
            raise ValueError("Username cannot be empty")
        return v

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str
    created_at: datetime.datetime


class TokenResponse(BaseModel):
    """Returned by /login, /signup, and /google — the client stores access_token
    and sends it back as `Authorization: Bearer <access_token>` on every
    other request."""
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class GoogleAuthRequest(BaseModel):
    # The ID token string from Credential Manager / Google Identity Services
    # on the Android side, NOT an access token.
    id_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class MessageResponse(BaseModel):
    message: str


# --- Conversations ---

class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(default="New Reflection", max_length=200)

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = _sanitize_text(v).strip()
        return cleaned or "New Reflection"


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    title: str
    created_at: datetime.datetime


# --- Messages ---

class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conversation_id: int
    sender: str
    message_text: str
    emotion_scores: Optional[dict] = None
    timestamp: datetime.datetime


class SendMessageRequest(BaseModel):
    conversation_id: int
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        v = _sanitize_text(v).strip()
        if not v:
            raise ValueError("Message text cannot be empty")
        return v


class SendMessageResponse(BaseModel):
    user_message: MessageOut
    senti_message: MessageOut
    distress_triggered: bool
    ai_provider_used: str


# --- Survey ---

class SurveyResponseRequest(BaseModel):
    survey_data: dict


class SurveyResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    survey_data: dict
    timestamp: datetime.datetime


# --- Insights (Insights & Profile screen's weekly graph) ---

class WeeklyStabilityOut(BaseModel):
    date: str
    day_label: str
    stability: Optional[float] = None  # None = no messages that day
    message_count: int


# --- Crisis map / nearby resources ---

class NearbyResourceOut(BaseModel):
    name: str
    lat: float
    lon: float
    distance_km: float
    address: Optional[str] = None
    phone: Optional[str] = None
    kind: str  # "hospital" | "clinic" | "doctors" | "social_facility" | "counselling"