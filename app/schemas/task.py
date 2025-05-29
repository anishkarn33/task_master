from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.task import TaskStatus, TaskPriority


# Shared properties
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None


# Properties to receive via API on creation
class TaskCreate(TaskBase):
    pass


# Properties to receive via API on update
class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None


# Properties to return to client
class Task(TaskBase):
    id: int
    owner_id: int
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Task with owner information
class TaskWithOwner(Task):
    owner: "User"  # Forward reference

# Import User schema to resolve forward reference
from app.schemas.user import User
TaskWithOwner.model_rebuild()