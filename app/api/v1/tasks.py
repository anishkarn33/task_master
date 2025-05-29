from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from datetime import datetime
from app.database import get_db
from app.schemas.task import Task, TaskCreate, TaskUpdate
from app.models.task import Task as TaskModel, TaskStatus, TaskPriority
from app.models.user import User as UserModel
from app.api.deps import get_current_active_user

router = APIRouter()


@router.get("/", response_model=List[Task])
def read_tasks(
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of tasks to return"),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by task priority"),
    sort_by: str = Query("created_at", description="Sort by field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all tasks for current user with filtering and sorting"""
    query = db.query(TaskModel).filter(TaskModel.owner_id == current_user.id)
    
    # Apply filters
    if status:
        query = query.filter(TaskModel.status == status)
    if priority:
        query = query.filter(TaskModel.priority == priority)
    
    # Apply sorting
    sort_column = getattr(TaskModel, sort_by, TaskModel.created_at)
    if sort_order.lower() == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))
    
    tasks = query.offset(skip).limit(limit).all()
    return tasks


@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new task"""
    db_task = TaskModel(
        **task.dict(),
        owner_id=current_user.id
    )
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    return db_task


@router.get("/{task_id}", response_model=Task)
def read_task(
    task_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific task by ID"""
    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.owner_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return task


@router.put("/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a specific task"""
    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.owner_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    update_data = task_update.dict(exclude_unset=True)
    
    # Set completed_at when status changes to completed
    if "status" in update_data:
        if update_data["status"] == TaskStatus.COMPLETED and task.status != TaskStatus.COMPLETED:
            update_data["completed_at"] = datetime.utcnow()
        elif update_data["status"] != TaskStatus.COMPLETED:
            update_data["completed_at"] = None
    
    # Update task fields
    for field, value in update_data.items():
        setattr(task, field, value)
    
    db.commit()
    db.refresh(task)
    
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a specific task"""
    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.owner_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    db.delete(task)
    db.commit()
    
    return None


@router.get("/stats/summary", response_model=dict)
def get_task_stats(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get task statistics for current user"""
    total_tasks = db.query(TaskModel).filter(TaskModel.owner_id == current_user.id).count()
    
    completed_tasks = db.query(TaskModel).filter(
        TaskModel.owner_id == current_user.id,
        TaskModel.status == TaskStatus.COMPLETED
    ).count()
    
    in_progress_tasks = db.query(TaskModel).filter(
        TaskModel.owner_id == current_user.id,
        TaskModel.status == TaskStatus.IN_PROGRESS
    ).count()
    
    todo_tasks = db.query(TaskModel).filter(
        TaskModel.owner_id == current_user.id,
        TaskModel.status == TaskStatus.TODO
    ).count()
    
    overdue_tasks = db.query(TaskModel).filter(
        TaskModel.owner_id == current_user.id,
        TaskModel.due_date < datetime.utcnow(),
        TaskModel.status != TaskStatus.COMPLETED
    ).count()
    
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "in_progress_tasks": in_progress_tasks,
        "todo_tasks": todo_tasks,
        "overdue_tasks": overdue_tasks,
        "completion_rate": round((completed_tasks / total_tasks * 100), 2) if total_tasks > 0 else 0
    }