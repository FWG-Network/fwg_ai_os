from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String, Integer, Float,
    DateTime, ForeignKey, JSON, Text,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped,
    mapped_column, relationship,
    sessionmaker,
)
from sqlalchemy import create_engine

try:
    from backend.core.config import settings
    DB_URL = getattr(settings, "DATABASE_URL", "postgresql://...")  # ★ indent ឲ្យត្រូវ
except Exception:
    DB_URL = "postgresql://..."
def _now() -> datetime:
    return datetime.now(timezone.utc)   # ✅ fix: utcnow deprecated


# ─── Base ─────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ─── Creator ──────────────────────────────────────────────────────────
class Creator(Base):
    __tablename__ = "creators"

    id:         Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    handle:     Mapped[str]  = mapped_column(String(100), unique=True, index=True, nullable=False)
    platform:   Mapped[str]  = mapped_column(String(50),  default="youtube")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    mentions: Mapped[list["CreatorMention"]] = relationship(back_populates="creator")

    def __repr__(self) -> str:
        return f"<Creator handle={self.handle}>"


# ─── CreatorMention ───────────────────────────────────────────────────
class CreatorMention(Base):
    __tablename__ = "creator_mentions"

    id:               Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    creator_id:       Mapped[int] = mapped_column(ForeignKey("creators.id"), nullable=False)
    source_channel:   Mapped[str] = mapped_column(String(100), nullable=False)
    source_video_url: Mapped[str] = mapped_column(String(500), nullable=False)
    mentioned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    creator: Mapped["Creator"] = relationship(back_populates="mentions")

    def __repr__(self) -> str:
        return f"<CreatorMention creator_id={self.creator_id}>"


# ─── Goal (aios) ──────────────────────────────────────────────────────
class Goal(Base):
    __tablename__ = "goals"

    id:          Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:     Mapped[Optional[str]]  = mapped_column(String(100), nullable=True)
    description: Mapped[str]            = mapped_column(Text, nullable=False)
    status:      Mapped[str]            = mapped_column(String(50), default="pending")
    created_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=_now)

    tasks: Mapped[list["Task"]] = relationship(back_populates="goal")

    def __repr__(self) -> str:
        return f"<Goal id={self.id} status={self.status}>"


# ─── Task (task_planner.py) ───────────────────────────────────────────
class Task(Base):
    __tablename__ = "tasks"

    id:          Mapped[int]             = mapped_column(Integer, primary_key=True, autoincrement=True)
    goal_id:     Mapped[int]             = mapped_column(ForeignKey("goals.id"), nullable=False)
    description: Mapped[str]             = mapped_column(Text, nullable=False)
    tool_name:   Mapped[Optional[str]]   = mapped_column(String(100), nullable=True)
    tool_params: Mapped[Optional[dict]]  = mapped_column(JSON, nullable=True)
    status:      Mapped[str]             = mapped_column(String(50), default="pending")
    result:      Mapped[Optional[dict]]  = mapped_column(JSON, nullable=True)
    created_at:  Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=_now)

    goal: Mapped["Goal"] = relationship(back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task id={self.id} tool={self.tool_name} status={self.status}>"


# ─── User (personalization) ───────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id:         Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:    Mapped[str]            = mapped_column(String(100), unique=True, nullable=False)
    interests:  Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=_now)

    def __repr__(self) -> str:
        return f"<User user_id={self.user_id}>"


# ─── Engine + Session ─────────────────────────────────────────────────
engine       = create_engine(DB_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """FastAPI dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables at startup."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/updated.")

# ✅ Dev: alias for compatibility
create_db_and_tables = init_db
