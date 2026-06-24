from sqlalchemy import create_engine, Column, String, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from backend.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
