from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
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

# ================= FIXED: Comment schemas =================
class TaskComment(BaseModel):
    comment: str

class TaskCommentCreate(BaseModel):
    """For creating comments with task_id"""
    task_id: int
    content: str

class TaskCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    comment: str
    created_at: datetime
    user_id: int
    task_id: int
    
    # Add computed fields for author info
    author: Optional[Dict[str, Any]] = None

# ================= ENHANCED: Task response schemas =================
class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    updated_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    board_position: int = 0
    completed_at: Optional[datetime] = None
    
    # IDs for relationships
    owner_id: int
    assigned_to_id: Optional[int] = None
    reviewer_id: Optional[int] = None
    created_by_id: Optional[int] = None
    
    # Review fields
    review_notes: Optional[str] = None
    review_status: str = "pending"
    reviewed_at: Optional[datetime] = None
    
    # Time tracking
    estimated_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    
    # User relationships (can be populated dynamically)
    assigned_to: Optional[UserBase] = None
    reviewer: Optional[UserBase] = None
    created_by: Optional[UserBase] = None

# ================= SIMPLIFIED: Board schemas for Kanban =================
class BoardTaskResponse(BaseModel):
    """Simplified task response for board view"""
    id: int
    title: str
    description: Optional[str] = None
    status: str  # String instead of enum for easier frontend handling
    priority: str  # String instead of enum for easier frontend handling
    created_at: Optional[str] = None  # ISO string
    updated_at: Optional[str] = None  # ISO string
    due_date: Optional[str] = None  # ISO string
    completed_at: Optional[str] = None  # ISO string
    board_position: int = 0
    
    # IDs
    owner_id: int
    assigned_to_id: Optional[int] = None
    reviewer_id: Optional[int] = None
    created_by_id: Optional[int] = None
    
    # Review fields
    review_notes: Optional[str] = None
    review_status: str = "pending"
    reviewed_at: Optional[str] = None
    
    # Time tracking
    estimated_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    
    # User relationships (as dicts for easier JSON serialization)
    assigned_to: Optional[Dict[str, Any]] = None
    reviewer: Optional[Dict[str, Any]] = None
    created_by: Optional[Dict[str, Any]] = None
    
    # Comment count for display
    comment_count: Optional[int] = 0

class BoardColumn(BaseModel):
    status: str
    title: str
    tasks: List[BoardTaskResponse]
    task_count: int

class BoardResponse(BaseModel):
    columns: List[BoardColumn]
    total_tasks: int

# ================= LEGACY: Keep for backward compatibility =================
class Task(TaskBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    owner_id: int
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class TaskWithOwner(Task):
    owner: "User"  # Forward reference

# ================= STATUS UPDATE: For drag & drop =================
class TaskStatusUpdate(BaseModel):
    status: str

# ================= COMMENT CREATION: Alternative formats =================
class CommentCreateAlternative(BaseModel):
    """Alternative comment creation format"""
    task_id: int
    content: str
    comment_type: Optional[str] = "general"

# Forward reference resolution
from app.schemas.user import User
TaskWithOwner.model_rebuild()