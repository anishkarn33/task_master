from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from datetime import datetime
from app.database import get_db
from app.schemas.task import (
    Task,                    
    TaskResponse,           
    TaskCreate, 
    TaskUpdate,
    TaskReview, 
    TaskComment as TaskCommentSchema, 
    TaskCommentResponse,
    BoardResponse, 
    BoardColumn
)
from app.models.task import Task as TaskModel, TaskStatus, TaskPriority, TaskComment
from app.models.user import User as UserModel
from app.api.deps import get_current_active_user

router = APIRouter()


@router.get("/", response_model=List[TaskResponse])
def read_tasks(
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of tasks to return"),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by task priority"),
    assigned_to: Optional[int] = Query(None, description="Filter by assigned user ID"),
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
    
    if assigned_to:
        query = query.filter(TaskModel.assigned_to_id == assigned_to)
    
    # Apply sorting
    sort_column = getattr(TaskModel, sort_by, TaskModel.created_at)
    if sort_order.lower() == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))
    
    tasks = query.offset(skip).limit(limit).all()
    return tasks


# ================= FIXED: Board endpoint without response_model =================
@router.get("/board")  # Removed response_model=BoardResponse
def get_board_view(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get board view for Kanban interface"""
    columns = []
    total_tasks = 0
    
    # Define status titles for display
    status_titles = {
        TaskStatus.TODO: "To Do",
        TaskStatus.IN_PROGRESS: "In Progress", 
        TaskStatus.IN_REVIEW: "In Review",
        TaskStatus.COMPLETED: "Done"
    }
    
    # Get tasks for each status column
    for status in TaskStatus:
        tasks = db.query(TaskModel).filter(
            TaskModel.owner_id == current_user.id,
            TaskModel.status == status
        ).order_by(TaskModel.board_position, TaskModel.created_at).all()
        
        # Convert tasks to dict format to avoid Pydantic validation issues
        tasks_data = []
        for task in tasks:
            task_dict = {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
                "priority": task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "board_position": getattr(task, 'board_position', 0),
                "owner_id": task.owner_id,
                
                # Handle foreign key IDs safely
                "assigned_to_id": getattr(task, 'assigned_to_id', None),
                "reviewer_id": getattr(task, 'reviewer_id', None), 
                "created_by_id": getattr(task, 'created_by_id', None),
                
                # Review fields
                "review_notes": getattr(task, 'review_notes', None),
                "review_status": getattr(task, 'review_status', 'pending'),
                "reviewed_at": getattr(task, 'reviewed_at', None),
                
                # Time tracking
                "estimated_minutes": getattr(task, 'estimated_minutes', None),
                "actual_minutes": getattr(task, 'actual_minutes', None),
                
                # Initialize relationships as None (avoid SQLAlchemy object issues)
                "assigned_to": None,
                "reviewer": None,
                "created_by": None
            }
            
            # Safely handle user relationships
            try:
                if hasattr(task, 'assigned_to') and task.assigned_to:
                    task_dict["assigned_to"] = {
                        "id": task.assigned_to.id,
                        "username": task.assigned_to.username,
                        "full_name": task.assigned_to.full_name or task.assigned_to.username,
                        "email": task.assigned_to.email,
                        "avatar_url": getattr(task.assigned_to, 'avatar_url', None)
                    }
            except:
                pass
                
            try:
                if hasattr(task, 'reviewer') and task.reviewer:
                    task_dict["reviewer"] = {
                        "id": task.reviewer.id,
                        "username": task.reviewer.username,
                        "full_name": task.reviewer.full_name or task.reviewer.username,
                        "email": task.reviewer.email,
                        "avatar_url": getattr(task.reviewer, 'avatar_url', None)
                    }
            except:
                pass
                
            try:
                if hasattr(task, 'created_by') and task.created_by:
                    task_dict["created_by"] = {
                        "id": task.created_by.id,
                        "username": task.created_by.username,
                        "full_name": task.created_by.full_name or task.created_by.username,
                        "email": task.created_by.email,
                        "avatar_url": getattr(task.created_by, 'avatar_url', None)
                    }
                else:
                    # Fallback to current user if created_by is not set
                    task_dict["created_by"] = {
                        "id": current_user.id,
                        "username": current_user.username,
                        "full_name": current_user.full_name or current_user.username,
                        "email": current_user.email,
                        "avatar_url": getattr(current_user, 'avatar_url', None)
                    }
            except:
                # Fallback to current user
                task_dict["created_by"] = {
                    "id": current_user.id,
                    "username": current_user.username,
                    "full_name": current_user.full_name or current_user.username,
                    "email": current_user.email,
                    "avatar_url": getattr(current_user, 'avatar_url', None)
                }
            
            tasks_data.append(task_dict)
        
        columns.append({
            "status": status.value if hasattr(status, 'value') else str(status),
            "title": status_titles.get(status, status.value if hasattr(status, 'value') else str(status)),
            "tasks": tasks_data,
            "task_count": len(tasks_data)
        })
        total_tasks += len(tasks_data)
    
    return {
        "columns": columns,
        "total_tasks": total_tasks
    }


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new task"""
    db_task = TaskModel(
        **task.model_dump(),
        owner_id=current_user.id,
        created_by_id=current_user.id
    )
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    return db_task


@router.get("/{task_id}", response_model=TaskResponse)
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


@router.put("/{task_id}", response_model=TaskResponse)
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
    
    update_data = task_update.model_dump(exclude_unset=True)
    
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


@router.put("/{task_id}/move")
def move_task(
    task_id: int,
    new_status: TaskStatus,
    new_position: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Move task to new status and position (for Kanban drag-and-drop)"""
    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.owner_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task.status = new_status
    task.board_position = new_position
    
    # Reorder other tasks in the same column
    other_tasks = db.query(TaskModel).filter(
        TaskModel.owner_id == current_user.id,
        TaskModel.status == new_status,
        TaskModel.id != task_id
    ).all()
    
    for i, other_task in enumerate(other_tasks):
        if i >= new_position:
            other_task.board_position = i + 1
        else:
            other_task.board_position = i
    
    db.commit()
    return {"message": "Task moved successfully"}


@router.put("/{task_id}/review", response_model=TaskResponse)
def review_task(
    task_id: int,
    review: TaskReview,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Review a task (for tasks in review status)"""
    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.owner_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if (task.reviewer_id and task.reviewer_id != current_user.id and 
        task.owner_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to review this task"
        )
    
    task.review_notes = review.review_notes
    task.review_status = review.review_status
    task.reviewed_at = datetime.utcnow()
    
    if review.review_status == "approved":
        task.status = TaskStatus.COMPLETED
    elif review.review_status == "rejected":
        task.status = TaskStatus.IN_PROGRESS
    
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/comments", response_model=TaskCommentResponse)
def add_comment(
    task_id: int,
    comment: TaskCommentSchema,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a comment to a task"""
    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.owner_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    db_comment = TaskComment(
        task_id=task_id,
        user_id=current_user.id,
        comment=comment.comment
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


@router.get("/{task_id}/comments", response_model=List[TaskCommentResponse])
def get_comments(
    task_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all comments for a task"""
    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.owner_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    comments = db.query(TaskComment).filter(
        TaskComment.task_id == task_id
    ).order_by(TaskComment.created_at.desc()).all()
    
    return comments


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

    in_review_tasks = db.query(TaskModel).filter(
        TaskModel.owner_id == current_user.id,
        TaskModel.status == TaskStatus.IN_REVIEW
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
        "in_review_tasks": in_review_tasks,
        "overdue_tasks": overdue_tasks,
        "completion_rate": round((completed_tasks / total_tasks * 100), 2) if total_tasks > 0 else 0
    }