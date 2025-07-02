from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, event
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone
from app.database import Base


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    estimated_minutes = Column(Integer, nullable=True)  # Estimated completion time
    actual_minutes = Column(Integer, nullable=True) 
    
    # Foreign key to user
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationship with user
    owner = relationship("User", back_populates="tasks")

# @event.listens_for(Task.status, 'set')
# def task_status_changed(target, value, oldvalue, initiator):
#     """Automatically set completed_at when task is marked as completed"""
#     if value == TaskStatus.COMPLETED and oldvalue != TaskStatus.COMPLETED:
#         target.completed_at = datetime.now(timezone.utc)
        
#         # Calculate actual completion time if task was created today
#         if target.created_at and target.created_at.date() == datetime.utcnow().date():
#             time_diff = datetime.utcnow() - target.created_at
#             target.actual_minutes = int(time_diff.total_seconds() / 60)
#     elif value != TaskStatus.COMPLETED and oldvalue == TaskStatus.COMPLETED:
#         # If uncompleting a task, remove completed_at
#         target.completed_at = None
#         target.actual_minutes = None