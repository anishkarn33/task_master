from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.task import Task
from app.services.llama_ai_service import LlamaAIService

router = APIRouter()

# Pydantic models
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    action: str
    message: str
    data: Dict[str, Any] = None
    confirmation_needed: bool = False

class NLPTaskRequest(BaseModel):
    natural_language: str

class ConfirmActionRequest(BaseModel):
    action: str
    data: Dict[str, Any]

class LlamaHealthResponse(BaseModel):
    status: str
    models: List[str] = []
    current_model: str = ""
    model_available: bool = False
    error: str = None
    message: str = None

# Initialize LLaMA service
llama_service = LlamaAIService()

@router.get("/health", response_model=LlamaHealthResponse)
async def check_llama_health():
    """Check if LLaMA/Ollama is available"""
    try:
        health_status = llama_service.check_ollama_status()
        return LlamaHealthResponse(**health_status)
    except Exception as e:
        return LlamaHealthResponse(
            status="error",
            error=str(e),
            message="Failed to check LLaMA health"
        )

@router.post("/chat", response_model=ChatResponse)
async def chat_with_llama(
    chat_message: ChatMessage,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Main LLaMA chat endpoint - handles all task operations"""
    try:
        # Check if LLaMA is available
        health = llama_service.check_ollama_status()
        if health['status'] != 'available':
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLaMA service is not available. Please check if Ollama is running."
            )
        
        print(f"Processing chat message: {chat_message.message}")
        
        response = await llama_service.process_chat_message(
            chat_message.message, 
            current_user.id, 
            db
        )
        
        print(f"AI Response: {response}")
        return ChatResponse(**response)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLaMA processing error: {str(e)}"
        )

@router.post("/confirm-action")
async def confirm_ai_action(
    request: ConfirmActionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Confirm and execute AI-suggested actions"""
    try:
        action = request.action
        data = request.data
        
        print(f"Confirming action: {action} with data: {data}")
        
        if action == 'create_task':
            result = await llama_service.execute_task_creation(
                data, current_user.id, db
            )
            
        elif action == 'edit_task':
            result = await llama_service.execute_task_edit(
                data['task_id'], data['changes'], current_user.id, db
            )
            
        elif action == 'move_task':
            result = await llama_service.execute_task_move(
                data['task_id'], data['new_status'], current_user.id, db
            )
            
        elif action == 'assign_task':
            result = await llama_service.execute_task_assignment(
                data['task_id'], data['assignee_id'], current_user.id, db
            )
            
        elif action == 'delete_task':
            result = await llama_service.execute_task_deletion(
                data['task_id'], current_user.id, db
            )
            
        elif action == 'bulk_operation':
            result = await llama_service.execute_bulk_operation(
                data['operation'], data['task_ids'], current_user.id, db
            )
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported action: {action}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Action confirmation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute action: {str(e)}"
        )

@router.post("/create-from-nl")
async def create_task_from_natural_language(
    nlp_request: NLPTaskRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a task directly from natural language"""
    try:
        # Parse the natural language
        task_data = await llama_service.parse_natural_language_task(
            nlp_request.natural_language,
            current_user.id,
            db
        )
        
        # Execute task creation
        result = await llama_service.execute_task_creation(
            task_data, current_user.id, db
        )
        
        if result['success']:
            return {
                "success": True,
                "task": result['task'],
                "message": result['message'],
                "ai_provider": "llama2"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task with LLaMA: {str(e)}"
        )

@router.post("/smart-update/{task_id}")
async def smart_update_task(
    task_id: int,
    nlp_request: NLPTaskRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a task using natural language"""
    try:
        # Check if task exists
        task = db.query(Task).filter(
            Task.id == task_id,
            Task.owner_id == current_user.id
        ).first()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Extract changes from natural language
        changes = await llama_service._extract_changes_from_message(
            nlp_request.natural_language, task
        )
        
        # Execute the update
        result = await llama_service.execute_task_edit(
            task_id, changes, current_user.id, db
        )
        
        if result['success']:
            return {
                "success": True,
                "task": result['task'],
                "message": result['message'],
                "ai_provider": "llama2"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task with LLaMA: {str(e)}"
        )

@router.post("/move-task/{task_id}")
async def move_task_with_ai(
    task_id: int,
    nlp_request: NLPTaskRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Move a task using natural language"""
    try:
        # Extract status from natural language
        new_status = llama_service._extract_status_from_message(
            nlp_request.natural_language
        )
        
        if not new_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not determine target status from message"
            )
        
        # Execute the move
        result = await llama_service.execute_task_move(
            task_id, new_status, current_user.id, db
        )
        
        if result['success']:
            return {
                "success": True,
                "task": result['task'],
                "message": result['message'],
                "ai_provider": "llama2"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to move task with LLaMA: {str(e)}"
        )

@router.post("/assign-task/{task_id}")
async def assign_task_with_ai(
    task_id: int,
    nlp_request: NLPTaskRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Assign a task using natural language"""
    try:
        # Extract assignee from natural language
        assignee = await llama_service._extract_assignee_from_message(
            nlp_request.natural_language, db
        )
        
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not determine assignee from message"
            )
        
        # Execute the assignment
        result = await llama_service.execute_task_assignment(
            task_id, assignee.id, current_user.id, db
        )
        
        if result['success']:
            return {
                "success": True,
                "task": result['task'],
                "message": result['message'],
                "ai_provider": "llama2"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign task with LLaMA: {str(e)}"
        )

@router.post("/bulk-operation")
async def bulk_operation_with_ai(
    nlp_request: NLPTaskRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Perform bulk operations using natural language"""
    try:
        # Process the request through AI
        response = await llama_service.process_chat_message(
            nlp_request.natural_language,
            current_user.id,
            db
        )
        
        if response['action'] == 'bulk_operation' and response.get('confirmation_needed'):
            # Return confirmation request
            return {
                "success": False,
                "confirmation_needed": True,
                "message": response['message'],
                "data": response['data']
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not process bulk operation request"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process bulk operation: {str(e)}"
        )

@router.get("/insights")
async def get_llama_insights(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive LLaMA insights about tasks and productivity"""
    try:
        # Get basic analysis
        response = await llama_service._handle_status_request("status", current_user.id, db)
        
        # Get recent tasks
        recent_tasks = db.query(Task).filter(
            Task.owner_id == current_user.id
        ).order_by(Task.updated_at.desc()).limit(5).all()
        
        # Check LLaMA status
        health = llama_service.check_ollama_status()
        
        return {
            "analysis": response,
            "recent_activity": [
                {
                    "id": task.id,
                    "title": task.title,
                    "status": task.status.value,
                    "updated_at": task.updated_at
                }
                for task in recent_tasks
            ],
            "recommendations": [
                "🦙 Using LLaMA 2 for 100% free and private AI assistance",
                "🤖 Try: 'Change task #5 priority to high'",
                "🔄 Try: 'Move the login bug task to in review'",
                "❌ Try: 'Delete all completed tasks'",
                "👥 Try: 'Assign the API task to John'",
                "📊 Try: 'Show me all high priority tasks'"
            ],
            "ai_provider": "llama2",
            "llama_status": health,
            "commands": {
                "create": "Create a high priority task to fix the login bug",
                "edit": "Change task #5 priority to high",
                "move": "Move the API task to in review",
                "assign": "Assign task #3 to John",
                "delete": "Delete the old meeting task",
                "query": "Show me all high priority tasks",
                "bulk": "Delete all completed tasks"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get LLaMA insights: {str(e)}"
        )

@router.get("/commands")
async def get_ai_commands():
    """Get available AI commands and examples"""
    return {
        "commands": {
            "task_creation": {
                "description": "Create new tasks from natural language",
                "examples": [
                    "Create a high priority task to fix the login bug",
                    "Add a meeting task for tomorrow at 2 PM",
                    "Make a code review task and assign it to John"
                ]
            },
            "task_editing": {
                "description": "Edit existing tasks",
                "examples": [
                    "Change task #5 priority to high",
                    "Update the API task description",
                    "Edit task #3 to add more details"
                ]
            },
            "task_movement": {
                "description": "Move tasks between boards",
                "examples": [
                    "Move the login bug task to in review",
                    "Put task #3 in the completed board",
                    "Move all todo tasks to in progress"
                ]
            },
            "task_assignment": {
                "description": "Assign tasks to team members",
                "examples": [
                    "Assign the code review task to John",
                    "Give task #7 to Sarah",
                    "Assign all bug tasks to the QA team"
                ]
            },
            "task_deletion": {
                "description": "Delete tasks",
                "examples": [
                    "Delete the old meeting task",
                    "Remove task #12",
                    "Delete all completed tasks"
                ]
            },
            "task_queries": {
                "description": "Search and filter tasks",
                "examples": [
                    "Show me all high priority tasks",
                    "Find tasks with 'bug' in the title",
                    "List all tasks assigned to John"
                ]
            },
            "status_analytics": {
                "description": "Get task status and analytics",
                "examples": [
                    "What's my task status?",
                    "Show me my progress",
                    "How many tasks are completed?"
                ]
            }
        },
        "tips": [
            "Be specific about task IDs when editing: 'Change task #5 priority to high'",
            "Use natural language: 'Move the login bug task to in review'",
            "Bulk operations work: 'Delete all completed tasks'",
            "Search is flexible: 'Find tasks with bug in the title'",
            "Assignment is smart: 'Assign task #3 to John'"
        ]
    }