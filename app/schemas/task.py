from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.task import TaskStatus, TaskPriority


class UserBase(BaseModel):
    id: int
    username: str
    full_name: str
    email: str
    avatar_url: Optional[str] = None

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to_id: Optional[int] = None
    reviewer_id: Optional[int] = None
    due_date: Optional[datetime] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assigned_to_id: Optional[int] = None
    reviewer_id: Optional[int] = None
    due_date: Optional[datetime] = None
    estimated_minutes: Optional[int] = None
    board_position: Optional[int] = None

class TaskReview(BaseModel):
    review_notes: Optional[str] = None
    review_status: str  # approved, rejected, pending

class TaskComment(BaseModel):
    comment: str

class TaskCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    comment: str
    created_at: datetime
    user: UserBase

class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    updated_at: Optional[datetime]
    due_date: Optional[datetime]
    board_position: int
    
    # Review fields
    review_notes: Optional[str]
    review_status: str
    reviewed_at: Optional[datetime]
    
    # User relationships
    assigned_to: Optional[UserBase]
    reviewer: Optional[UserBase]
    created_by: UserBase

class BoardColumn(BaseModel):
    status: TaskStatus
    title: str
    tasks: List[TaskResponse]
    task_count: int

class BoardResponse(BaseModel):
    columns: List[BoardColumn]
    total_tasks: int

class Task(TaskBase):
    id: int
    owner_id: int
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskWithOwner(Task):
    owner: "User"  # Forward reference

from app.schemas.user import User
TaskWithOwner.model_rebuild()