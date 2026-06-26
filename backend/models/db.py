# backend/models/db.py

import uuid
from sqlalchemy import (
    create_engine, Column, String, Text, ForeignKey,
    Integer, DateTime, func
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID

from backend.core.config import settings

# ==========================================================
# Database Setup (No Changes Here)
# ==========================================================
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==========================================================
# Existing AI-OS Core Models (No Changes Here)
# ==========================================================
class Goal(Base):
    __tablename__ = "goals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(Text, nullable=False)
    status = Column(String, default="pending")
    tasks = relationship("Task", back_populates="goal")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(Text, nullable=False)
    status = Column(String, default="pending")
    result = Column(Text, nullable=True)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id"))
    goal = relationship("Goal", back_populates="tasks")


# ==========================================================
# 🚀 UPGRADE V3: Trend Forecaster Models
# These new tables will create the "Trend Memory"
# ==========================================================
class Creator(Base):
    """
    Stores information about a unique content creator.
    This table acts as the central directory for all creators discovered.
    """
    __tablename__ = "creators"
    
    id = Column(Integer, primary_key=True, index=True)
    # The unique YouTube handle (e.g., '@MrBeast'). Indexed for fast lookups.
    handle = Column(String, unique=True, index=True, nullable=False)
    
    # This relationship creates a link to the CreatorMention table.
    # It allows you to easily query all mentions for a specific creator.
    # e.g., my_creator.mentions
    mentions = relationship("CreatorMention", back_populates="creator", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Creator(handle='{self.handle}')>"

class CreatorMention(Base):
    """
    Records a single instance of a creator being mentioned or credited.
    Each row is a "data point" in our trend analysis.
    """
    __tablename__ = "creator_mentions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key linking this mention back to the Creator table.
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    
    # The timestamp of when this mention was recorded.
    # `server_default=func.now()` means PostgreSQL will automatically set the current time.
    mentioned_at = Column(DateTime, server_default=func.now())
    
    # Information about where the mention was found.
    source_channel = Column(String, nullable=False) # e.g., 'PolarRanks'
    source_video_url = Column(String, nullable=False)
    
    # This relationship links back to the Creator object.
    # It allows you to access creator details from a mention object.
    # e.g., my_mention.creator.handle
    creator = relationship("Creator", back_populates="mentions")

    def __repr__(self):
        return f"<CreatorMention(creator_handle='{self.creator.handle}' at {self.mentioned_at})>"


# ==========================================================
# Create all tables if they don't exist
# This line will now create 'goals', 'tasks', 'creators', and 'creator_mentions'
# ==========================================================
print("🚀 Initializing database and creating tables if they don't exist...")
Base.metadata.create_all(bind=engine)
print("✅ Database tables initialized.")


# ==========================================================
# Database Session Dependency (No Changes Here)
# ==========================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
