from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    avatar_url = Column(String(255), nullable=True)
    role = Column(String(50), default="user")

    # Relationship with tasks
    tasks = relationship("Task",foreign_keys="Task.owner_id", back_populates="owner", cascade="all, delete-orphan")
    assigned_tasks = relationship("Task", foreign_keys="Task.assigned_to_id", back_populates="assigned_to", overlaps="tasks")
    review_tasks = relationship("Task", foreign_keys="Task.reviewer_id", back_populates="reviewer",overlaps="tasks,assigned_tasks")
    created_tasks = relationship("Task", foreign_keys="Task.created_by_id", back_populates="created_by",overlaps="tasks,assigned_tasks,review_tasks")