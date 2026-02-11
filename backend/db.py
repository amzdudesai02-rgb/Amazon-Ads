import os
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required (PostgreSQL connection string).")


engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class AmazonAdsToken(Base):
    __tablename__ = "amazon_ads_tokens"

    id = Column(Integer, primary_key=True, index=True)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, nullable=True)
    email = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("ChatSession", back_populates="user")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


class CampaignSnapshot(Base):
    __tablename__ = "campaign_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(String, nullable=False)
    raw_json = Column(Text, nullable=False)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db() -> None:
    """Create tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()


def get_tokens() -> Optional[AmazonAdsToken]:
    with get_session() as db:
        return db.query(AmazonAdsToken).first()


def save_tokens(access_token: str, refresh_token: str, expires_at: datetime) -> None:
    with get_session() as db:
        token = db.query(AmazonAdsToken).first()
        if token is None:
            token = AmazonAdsToken()
            db.add(token)
        token.access_token = access_token
        token.refresh_token = refresh_token
        token.expires_at = expires_at
        db.commit()


def get_or_create_default_user_id() -> int:
    """
    For now we assume a single user. This returns its ID, creating it if needed.
    """
    with get_session() as db:
        user = db.query(User).first()
        if user is None:
            user = User()
            db.add(user)
            db.commit()
            db.refresh(user)
        return user.id


def create_chat_session(user_id: int, title: Optional[str] = None) -> int:
    with get_session() as db:
        session = ChatSession(user_id=user_id, title=title)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.id


def log_chat_message(session_id: int, role: str, content: str) -> None:
    with get_session() as db:
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        db.add(msg)
        # update last_message_at on the session
        session = db.query(ChatSession).get(session_id)
        if session is not None:
            session.last_message_at = datetime.utcnow()
        db.commit()


def save_campaign_snapshot(profile_id: str, raw_json: str, note: Optional[str] = None) -> None:
    with get_session() as db:
        snap = CampaignSnapshot(profile_id=profile_id, raw_json=raw_json, note=note)
        db.add(snap)
        db.commit()

