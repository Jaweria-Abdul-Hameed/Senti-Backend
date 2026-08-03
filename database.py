import datetime
import os
from typing import List, Optional

from sqlalchemy import create_engine, ForeignKey, String, Text, Float, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.dialects.postgresql import JSONB

# Same connection string shape as your original database.py, now overridable via env
# so PyCharm / prod / docker can point it somewhere else without editing code.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:1234@localhost:5432/senti_db",
)

engine = create_engine(DATABASE_URL, echo=os.getenv("SQL_ECHO", "false").lower() == "true")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # Nullable because a Google Sign-In-only account never sets a password.
    # Such a user can still call POST /auth/forgot-password to set one later
    # if they want email+password login too.
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Google's stable per-user id ("sub" claim), set the first time someone
    # signs in with Google. Lets a later Google Sign-In find the same row
    # even if the user's Google email display name changes.
    google_sub: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    conversations: Mapped[List["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    survey_responses: Mapped[List["SurveyResponse"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(100), default="New Reflection")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.timestamp",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender: Mapped[str] = mapped_column(String(10), nullable=False)  # "user" or "senti"
    message_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Legacy single-value field from the original schema — left in place so nothing
    # that already relies on it breaks. Not written to by the new chat logic.
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # The 6-class emotion vector the Kotlin app used to store as a local JSON string
    # (Fear/Sadness/Anger/Joy/Love/Surprise), now stored properly as JSONB.
    emotion_scores: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    survey_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="survey_responses")


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)


def get_db():
    """FastAPI dependency — one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database():
    print("Connecting to PostgreSQL and compiling complete system architecture tables...")
    Base.metadata.create_all(bind=engine)
    print("All system tables generated successfully inside PostgreSQL!")


if __name__ == "__main__":
    initialize_database()
