from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, event
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone
from app.database import Base


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
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
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    estimated_minutes = Column(Integer, nullable=True)  # Estimated completion time
    actual_minutes = Column(Integer, nullable=True) 
    
   # Review fields
    review_notes = Column(Text, nullable=True)
    review_status = Column(String(50), default="pending")  # pending, approved, rejected
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Board position for drag-and-drop
    board_position = Column(Integer, default=0)
    
    # Relationships
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], back_populates="assigned_tasks",overlaps="owner")
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="review_tasks",overlaps="owner,assigned_to")
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="created_tasks",overlaps="owner,assigned_to,reviewer")

    # Foreign key to user
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationship with user
    owner = relationship("User",foreign_keys=[owner_id], back_populates="tasks")

# Task comment
class TaskComment(Base):
    __tablename__ = "task_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    task = relationship("Task")
    user = relationship("User")

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