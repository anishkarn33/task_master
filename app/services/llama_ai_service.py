import requests
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.user import User
from app.core.config import settings

class LlamaAIService:
    def __init__(self):
        self.ollama_url = settings.OLLAMA_URL or "http://localhost:11434"
        self.model_name = settings.LLAMA_MODEL or "llama2"
        self.temperature = settings.AI_TEMPERATURE or 0.3
        
    def _call_ollama(self, prompt: str, system_prompt: str = None) -> str:
        """Call Ollama API with LLaMA 2 model"""
        try:
            url = f"{self.ollama_url}/api/generate"
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "top_p": 0.9,
                    "max_tokens": 800
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
            
        except requests.exceptions.RequestException as e:
            print(f"Error calling Ollama API: {e}")
            raise Exception(f"AI service unavailable: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise Exception(f"AI processing error: {e}")
    
    async def parse_natural_language_task(self, user_input: str, current_user_id: int, db: Session) -> Dict[str, Any]:
        """Parse natural language input into structured task data"""
        
        users = db.query(User).all()
        user_names = [{"id": u.id, "name": u.username, "full_name": u.full_name} for u in users]
        
        system_prompt = f"""You are a helpful task management assistant. Convert natural language into structured task data.

Available users: {json.dumps(user_names)}
Current user ID: {current_user_id}
Current date: {datetime.now().strftime('%Y-%m-%d')}

Guidelines:
- Extract title, description, priority, status, assignee, and due date
- Priority: "low", "medium", "high", or "urgent"
- Status: "todo", "in_progress", "in_review", or "completed"
- If "tomorrow" mentioned, set due_date to tomorrow
- If "next week" mentioned, set due_date to 7 days from now
- Default priority is "medium", default status is "todo"
- Return ONLY valid JSON format

Example output:
{{"title": "Fix login bug", "description": "Urgent bug fix needed", "priority": "high", "status": "todo", "assigned_to_id": 2, "due_date": "2024-01-15T23:59:59Z"}}"""

        prompt = f"""Convert this request to JSON: "{user_input}"

Return only the JSON object with these fields:
- title (required)
- description (optional)
- priority (low/medium/high/urgent)
- status (todo/in_progress/in_review/completed)
- assigned_to_id (number, optional)
- due_date (ISO format, optional)
- estimated_minutes (number, optional)

JSON:"""
        
        try:
            response = self._call_ollama(prompt, system_prompt)
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                return self._validate_parsed_task(result)
            else:
                return self._fallback_parse(user_input)
                
        except Exception as e:
            print(f"Error parsing with LLaMA: {e}")
            return self._fallback_parse(user_input)
    
    def _validate_parsed_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean parsed task data"""
        
        if not task_data.get('title'):
            task_data['title'] = "New Task"
        
        valid_priorities = ['low', 'medium', 'high', 'urgent']
        if task_data.get('priority') not in valid_priorities:
            task_data['priority'] = 'medium'
            
        valid_statuses = ['todo', 'in_progress', 'in_review', 'completed']
        if task_data.get('status') not in valid_statuses:
            task_data['status'] = 'todo'
        
        if task_data.get('due_date'):
            try:
                if 'T' not in task_data['due_date']:
                    task_data['due_date'] = task_data['due_date'] + 'T23:59:59Z'
            except:
                task_data.pop('due_date', None)
        
        if task_data.get('assigned_to_id'):
            try:
                task_data['assigned_to_id'] = int(task_data['assigned_to_id'])
            except:
                task_data.pop('assigned_to_id', None)
        
        return task_data
    
    def _fallback_parse(self, user_input: str) -> Dict[str, Any]:
        """Simple fallback parsing without AI"""
        
        title = user_input.split('.')[0].strip()
        if len(title) > 100:
            title = title[:97] + "..."
            
        priority = 'medium'
        if any(word in user_input.lower() for word in ['urgent', 'asap', 'critical']):
            priority = 'urgent'
        elif any(word in user_input.lower() for word in ['high', 'important']):
            priority = 'high'
        elif any(word in user_input.lower() for word in ['low', 'minor']):
            priority = 'low'
        
        due_date = None
        if 'tomorrow' in user_input.lower():
            due_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%dT23:59:59Z')
        elif 'next week' in user_input.lower():
            due_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%dT23:59:59Z')
        
        return {
            'title': title,
            'description': user_input,
            'priority': priority,
            'status': 'todo',
            'due_date': due_date
        }
    
    def check_ollama_status(self) -> Dict[str, Any]:
        """Check if Ollama is running and model is available"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            
            return {
                'status': 'available',
                'models': model_names,
                'current_model': self.model_name,
                'model_available': any(self.model_name in name for name in model_names)
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'status': 'unavailable',
                'error': str(e),
                'message': 'Ollama is not running or unreachable'
            }
    
    async def process_chat_message(self, message: str, user_id: int, db: Session) -> Dict[str, Any]:
        """Process chat message and determine appropriate action"""
        
        # Use AI to classify the intent
        intent = await self._classify_intent(message, user_id, db)
        
        # Handle different intents
        if intent['action'] == 'create_task':
            return await self._handle_create_task(message, user_id, db)
        elif intent['action'] == 'edit_task':
            return await self._handle_edit_task(message, user_id, db, intent.get('data', {}))
        elif intent['action'] == 'delete_task':
            return await self._handle_delete_task(message, user_id, db, intent.get('data', {}))
        elif intent['action'] == 'move_task':
            return await self._handle_move_task(message, user_id, db, intent.get('data', {}))
        elif intent['action'] == 'assign_task':
            return await self._handle_assign_task(message, user_id, db, intent.get('data', {}))
        elif intent['action'] == 'query_tasks':
            return await self._handle_query_tasks(message, user_id, db, intent.get('data', {}))
        elif intent['action'] == 'bulk_operation':
            return await self._handle_bulk_operation(message, user_id, db, intent.get('data', {}))
        elif intent['action'] == 'status_request':
            return await self._handle_status_request(message, user_id, db)
        elif intent['action'] == 'help':
            return self._handle_help_request()
        else:
            return await self._handle_general_query(message, user_id, db)
    
    async def _classify_intent(self, message: str, user_id: int, db: Session) -> Dict[str, Any]:
        """Use AI to classify user intent"""
        
        # Get user's recent tasks for context
        recent_tasks = db.query(Task).filter(Task.owner_id == user_id).order_by(Task.created_at.desc()).limit(10).all()
        task_list = [{"id": t.id, "title": t.title, "status": t.status.value, "priority": t.priority.value} for t in recent_tasks]
        
        system_prompt = f"""You are an intelligent task management assistant. Analyze the user's message and classify their intent.

User's recent tasks: {json.dumps(task_list)}

Available actions:
1. create_task - User wants to create a new task
2. edit_task - User wants to modify an existing task (change priority, status, description, etc.)
3. delete_task - User wants to delete a task
4. move_task - User wants to move a task between boards/statuses (todo, in_progress, in_review, completed)
5. assign_task - User wants to assign a task to someone
6. query_tasks - User wants to find/filter/search tasks
7. bulk_operation - User wants to perform actions on multiple tasks
8. status_request - User wants to see their overall task status
9. help - User needs help
10. general - General conversation

Return JSON with:
- action: one of the above actions
- confidence: 0.0-1.0 confidence score
- data: any extracted parameters (task_id, new_priority, new_status, search_terms, etc.)
- reasoning: brief explanation

Examples:
- "Change task #5 priority to high" → {{"action": "edit_task", "confidence": 0.9, "data": {{"task_id": 5, "field": "priority", "value": "high"}}}}
- "Move the login bug task to in review" → {{"action": "move_task", "confidence": 0.8, "data": {{"task_search": "login bug", "new_status": "in_review"}}}}
- "Delete all completed tasks" → {{"action": "bulk_operation", "confidence": 0.9, "data": {{"operation": "delete", "filter": "completed"}}}}"""

        prompt = f"""Analyze this message: "{message}"

Return JSON with action classification:"""
        
        try:
            response = self._call_ollama(prompt, system_prompt)
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                return result
            else:
                return self._fallback_classify(message)
                
        except Exception as e:
            print(f"Error classifying intent: {e}")
            return self._fallback_classify(message)
    
    def _fallback_classify(self, message: str) -> Dict[str, Any]:
        """Simple fallback classification"""
        message_lower = message.lower()
        
        # Simple keyword matching
        if any(word in message_lower for word in ['create', 'add', 'new task', 'make']):
            return {'action': 'create_task', 'confidence': 0.7, 'data': {}}
        elif any(word in message_lower for word in ['edit', 'change', 'update', 'modify']):
            return {'action': 'edit_task', 'confidence': 0.6, 'data': {}}
        elif any(word in message_lower for word in ['delete', 'remove', 'cancel']):
            return {'action': 'delete_task', 'confidence': 0.6, 'data': {}}
        elif any(word in message_lower for word in ['move', 'transfer', 'shift']):
            return {'action': 'move_task', 'confidence': 0.6, 'data': {}}
        elif any(word in message_lower for word in ['assign', 'give to']):
            return {'action': 'assign_task', 'confidence': 0.6, 'data': {}}
        elif any(word in message_lower for word in ['find', 'search', 'show', 'list']):
            return {'action': 'query_tasks', 'confidence': 0.6, 'data': {}}
        elif any(word in message_lower for word in ['status', 'progress', 'summary']):
            return {'action': 'status_request', 'confidence': 0.7, 'data': {}}
        elif any(word in message_lower for word in ['help', 'what can you do']):
            return {'action': 'help', 'confidence': 0.8, 'data': {}}
        else:
            return {'action': 'general', 'confidence': 0.5, 'data': {}}
    
    async def _handle_create_task(self, message: str, user_id: int, db: Session) -> Dict[str, Any]:
        """Handle task creation"""
        try:
            task_data = await self.parse_natural_language_task(message, user_id, db)
            
            return {
                'action': 'create_task',
                'data': task_data,
                'message': f"I can create a task titled '{task_data['title']}' with {task_data['priority']} priority. Would you like me to proceed?",
                'confirmation_needed': True
            }
        except Exception as e:
            return {
                'action': 'error',
                'message': f"I couldn't parse your task request. Please try again with more details."
            }
    
    async def _handle_edit_task(self, message: str, user_id: int, db: Session, intent_data: Dict) -> Dict[str, Any]:
        """Handle task editing"""
        try:
            # Find the task to edit
            task = await self._find_task_from_message(message, user_id, db)
            
            if not task:
                return {
                    'action': 'error',
                    'message': "I couldn't find the task you want to edit. Please be more specific or provide the task ID."
                }
            
            # Extract what to change
            changes = await self._extract_changes_from_message(message, task)
            
            return {
                'action': 'edit_task',
                'data': {
                    'task_id': task.id,
                    'task_title': task.title,
                    'changes': changes
                },
                'message': f"I can update the task '{task.title}' with the following changes: {self._format_changes(changes)}. Should I proceed?",
                'confirmation_needed': True
            }
            
        except Exception as e:
            return {
                'action': 'error',
                'message': f"Error processing edit request: {str(e)}"
            }
    
    async def _handle_move_task(self, message: str, user_id: int, db: Session, intent_data: Dict) -> Dict[str, Any]:
        """Handle moving tasks between boards/statuses"""
        try:
            task = await self._find_task_from_message(message, user_id, db)
            
            if not task:
                return {
                    'action': 'error',
                    'message': "I couldn't find the task you want to move. Please be more specific."
                }
            
            # Extract target status
            new_status = self._extract_status_from_message(message)
            
            if not new_status:
                return {
                    'action': 'error',
                    'message': "I couldn't determine where you want to move the task. Please specify: todo, in progress, in review, or completed."
                }
            
            return {
                'action': 'move_task',
                'data': {
                    'task_id': task.id,
                    'task_title': task.title,
                    'current_status': task.status.value,
                    'new_status': new_status
                },
                'message': f"I can move the task '{task.title}' from {task.status.value} to {new_status}. Should I proceed?",
                'confirmation_needed': True
            }
            
        except Exception as e:
            return {
                'action': 'error',
                'message': f"Error processing move request: {str(e)}"
            }
    
    async def _handle_delete_task(self, message: str, user_id: int, db: Session, intent_data: Dict) -> Dict[str, Any]:
        """Handle task deletion"""
        try:
            task = await self._find_task_from_message(message, user_id, db)
            
            if not task:
                return {
                    'action': 'error',
                    'message': "I couldn't find the task you want to delete. Please be more specific."
                }
            
            return {
                'action': 'delete_task',
                'data': {
                    'task_id': task.id,
                    'task_title': task.title
                },
                'message': f"Are you sure you want to delete the task '{task.title}'? This action cannot be undone.",
                'confirmation_needed': True
            }
            
        except Exception as e:
            return {
                'action': 'error',
                'message': f"Error processing delete request: {str(e)}"
            }
    
    async def _handle_assign_task(self, message: str, user_id: int, db: Session, intent_data: Dict) -> Dict[str, Any]:
        """Handle task assignment"""
        try:
            task = await self._find_task_from_message(message, user_id, db)
            
            if not task:
                return {
                    'action': 'error',
                    'message': "I couldn't find the task you want to assign. Please be more specific."
                }
            
            # Extract assignee
            assignee = await self._extract_assignee_from_message(message, db)
            
            if not assignee:
                return {
                    'action': 'error',
                    'message': "I couldn't determine who you want to assign the task to. Please specify a username."
                }
            
            return {
                'action': 'assign_task',
                'data': {
                    'task_id': task.id,
                    'task_title': task.title,
                    'assignee_id': assignee.id,
                    'assignee_name': assignee.username
                },
                'message': f"I can assign the task '{task.title}' to {assignee.username}. Should I proceed?",
                'confirmation_needed': True
            }
            
        except Exception as e:
            return {
                'action': 'error',
                'message': f"Error processing assignment request: {str(e)}"
            }
    
    async def _handle_query_tasks(self, message: str, user_id: int, db: Session, intent_data: Dict) -> Dict[str, Any]:
        """Handle task queries and searches"""
        try:
            # Extract search parameters
            filters = self._extract_filters_from_message(message)
            
            # Build query
            query = db.query(Task).filter(Task.owner_id == user_id)
            
            if filters.get('status'):
                query = query.filter(Task.status == filters['status'])
            
            if filters.get('priority'):
                query = query.filter(Task.priority == filters['priority'])
            
            if filters.get('search_term'):
                query = query.filter(
                    or_(
                        Task.title.ilike(f"%{filters['search_term']}%"),
                        Task.description.ilike(f"%{filters['search_term']}%")
                    )
                )
            
            tasks = query.limit(10).all()
            
            if not tasks:
                return {
                    'action': 'query_result',
                    'message': "No tasks found matching your criteria."
                }
            
            # Format results
            result_text = f"Found {len(tasks)} tasks:\n\n"
            for task in tasks:
                result_text += f"• #{task.id} - {task.title} ({task.priority.value} priority, {task.status.value})\n"
            
            return {
                'action': 'query_result',
                'message': result_text,
                'data': {'tasks': [{'id': t.id, 'title': t.title, 'status': t.status.value, 'priority': t.priority.value} for t in tasks]}
            }
            
        except Exception as e:
            return {
                'action': 'error',
                'message': f"Error searching tasks: {str(e)}"
            }
    
    async def _handle_bulk_operation(self, message: str, user_id: int, db: Session, intent_data: Dict) -> Dict[str, Any]:
        """Handle bulk operations on multiple tasks"""
        try:
            # Extract operation type and filters
            operation = intent_data.get('operation', 'unknown')
            filters = self._extract_filters_from_message(message)
            
            # Build query for affected tasks
            query = db.query(Task).filter(Task.owner_id == user_id)
            
            if filters.get('status'):
                query = query.filter(Task.status == filters['status'])
            
            if filters.get('priority'):
                query = query.filter(Task.priority == filters['priority'])
            
            tasks = query.all()
            
            if not tasks:
                return {
                    'action': 'error',
                    'message': "No tasks found matching your criteria for bulk operation."
                }
            
            return {
                'action': 'bulk_operation',
                'data': {
                    'operation': operation,
                    'task_count': len(tasks),
                    'task_ids': [t.id for t in tasks]
                },
                'message': f"This will {operation} {len(tasks)} tasks. Are you sure you want to proceed?",
                'confirmation_needed': True
            }
            
        except Exception as e:
            return {
                'action': 'error',
                'message': f"Error processing bulk operation: {str(e)}"
            }
    
    async def _handle_status_request(self, message: str, user_id: int, db: Session) -> Dict[str, Any]:
        """Handle status requests"""
        tasks = db.query(Task).filter(Task.owner_id == user_id).all()
        
        if not tasks:
            return {
                'action': 'status_summary',
                'message': "You don't have any tasks yet. Would you like me to create one for you?"
            }
        
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        summary = f"""📊 **Your Task Summary:**

• Total tasks: {total_tasks}
• Completed: {completed_tasks} ({completion_rate:.1f}%)
• In Progress: {len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])}
• To Do: {len([t for t in tasks if t.status == TaskStatus.TODO])}
• In Review: {len([t for t in tasks if t.status == TaskStatus.IN_REVIEW])}

Great job on your progress! 🎉"""
        
        return {
            'action': 'status_summary',
            'message': summary
        }
    
    def _handle_help_request(self) -> Dict[str, Any]:
        """Handle help requests"""
        help_text = """🤖 **AI Task Assistant - Full Automation Commands:**

**✨ Task Creation:**
• "Create a high priority task to fix the login bug"
• "Add a meeting task for tomorrow at 2 PM"

**🔧 Task Editing:**
• "Change task #5 priority to high"
• "Update the API task description to include documentation"

**🔄 Task Movement:**
• "Move the login bug task to in review"
• "Put task #3 in the completed board"

**👥 Task Assignment:**
• "Assign the code review task to John"
• "Give task #7 to Sarah"

**❌ Task Deletion:**
• "Delete the old meeting task"
• "Remove task #12"

**🔍 Task Queries:**
• "Show me all high priority tasks"
• "Find tasks with 'bug' in the title"
• "List all completed tasks"

**📊 Bulk Operations:**
• "Delete all completed tasks"
• "Move all todo tasks to in progress"

**📈 Status & Analytics:**
• "What's my task status?"
• "Show me my progress"

Just type what you need in natural language! 🚀"""
        
        return {
            'action': 'help',
            'message': help_text
        }
    
    async def _handle_general_query(self, message: str, user_id: int, db: Session) -> Dict[str, Any]:
        """Handle general queries"""
        return {
            'action': 'general_response',
            'message': "I'm here to help you manage your tasks! Try asking me to create, edit, move, assign, or search for tasks. Type 'help' for more commands."
        }
    
    # Helper methods for task operations
    async def _find_task_from_message(self, message: str, user_id: int, db: Session) -> Optional[Task]:
        """Find a task based on message content"""
        
        # Look for task ID pattern (#123 or task 123)
        id_match = re.search(r'#(\d+)|task\s+(\d+)', message, re.IGNORECASE)
        if id_match:
            task_id = int(id_match.group(1) or id_match.group(2))
            return db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
        
        # Look for task title keywords
        keywords = self._extract_keywords_from_message(message)
        if keywords:
            # Search for tasks containing these keywords
            query = db.query(Task).filter(Task.owner_id == user_id)
            for keyword in keywords:
                query = query.filter(
                    or_(
                        Task.title.ilike(f"%{keyword}%"),
                        Task.description.ilike(f"%{keyword}%")
                    )
                )
            
            tasks = query.limit(5).all()
            if len(tasks) == 1:
                return tasks[0]
            elif len(tasks) > 1:
                # Return the most recently created task
                return max(tasks, key=lambda t: t.created_at)
        
        return None
    
    def _extract_keywords_from_message(self, message: str) -> List[str]:
        """Extract potential task keywords from message"""
        # Remove common words
        stop_words = {'the', 'a', 'an', 'to', 'from', 'in', 'on', 'at', 'for', 'with', 'by', 'and', 'or', 'but', 'task', 'change', 'update', 'move', 'edit', 'delete', 'priority', 'status'}
        
        words = message.lower().split()
        keywords = [word.strip('.,!?;:') for word in words if word.strip('.,!?;:') not in stop_words and len(word) > 2]
        
        return keywords[:3]  # Return top 3 keywords
    
    async def _extract_changes_from_message(self, message: str, task: Task) -> Dict[str, str]:
        """Extract what changes to make to a task"""
        changes = {}
        message_lower = message.lower()
        
        # Priority changes
        if 'priority' in message_lower:
            for priority in ['urgent', 'high', 'medium', 'low']:
                if priority in message_lower:
                    changes['priority'] = priority
                    break
        
        # Status changes
        status_keywords = {
            'todo': ['todo', 'to do', 'pending'],
            'in_progress': ['in progress', 'progress', 'working', 'active'],
            'in_review': ['in review', 'review', 'reviewing'],
            'completed': ['completed', 'done', 'finished', 'complete']
        }
        
        for status, keywords in status_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                changes['status'] = status
                break
        
        # Description changes
        if 'description' in message_lower:
            # Try to extract new description
            desc_match = re.search(r'description\s+to\s+["\']?([^"\']+)["\']?', message, re.IGNORECASE)
            if desc_match:
                changes['description'] = desc_match.group(1).strip()
        
        return changes
    
    def _extract_status_from_message(self, message: str) -> Optional[str]:
        """Extract target status from message"""
        message_lower = message.lower()
        
        status_keywords = {
            'todo': ['todo', 'to do', 'pending'],
            'in_progress': ['in progress', 'progress', 'working', 'active'],
            'in_review': ['in review', 'review', 'reviewing'],
            'completed': ['completed', 'done', 'finished', 'complete']
        }
        
        for status, keywords in status_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return status
        
        return None
    
    async def _extract_assignee_from_message(self, message: str, db: Session) -> Optional[User]:
        """Extract assignee from message"""
        # Look for username patterns
        users = db.query(User).all()
        
        for user in users:
            if user.username.lower() in message.lower():
                return user
            if user.full_name and user.full_name.lower() in message.lower():
                return user
        
        return None
    
    def _extract_filters_from_message(self, message: str) -> Dict[str, str]:
        """Extract search filters from message"""
        filters = {}
        message_lower = message.lower()
        
        # Priority filters
        for priority in ['urgent', 'high', 'medium', 'low']:
            if priority in message_lower:
                filters['priority'] = TaskPriority(priority)
                break
        
        # Status filters
        status_keywords = {
            'todo': ['todo', 'to do', 'pending'],
            'in_progress': ['in progress', 'progress', 'working'],
            'in_review': ['in review', 'review', 'reviewing'],
            'completed': ['completed', 'done', 'finished']
        }
        
        for status, keywords in status_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                filters['status'] = TaskStatus(status)
                break
        
        # Search term extraction
        search_terms = []
        if 'with' in message_lower:
            # Extract terms after "with"
            with_match = re.search(r'with\s+["\']?([^"\']+)["\']?', message, re.IGNORECASE)
            if with_match:
                search_terms.append(with_match.group(1).strip())
        
        if 'containing' in message_lower:
            # Extract terms after "containing"
            containing_match = re.search(r'containing\s+["\']?([^"\']+)["\']?', message, re.IGNORECASE)
            if containing_match:
                search_terms.append(containing_match.group(1).strip())
        
        if search_terms:
            filters['search_term'] = ' '.join(search_terms)
        
        return filters
    
    def _format_changes(self, changes: Dict[str, str]) -> str:
        """Format changes for display"""
        if not changes:
            return "no changes detected"
        
        formatted = []
        for field, value in changes.items():
            formatted.append(f"{field} → {value}")
        
        return ", ".join(formatted)
    
    # Task execution methods
    async def execute_task_creation(self, task_data: Dict[str, Any], user_id: int, db: Session) -> Dict[str, Any]:
        """Execute task creation"""
        try:
            from app.models.task import Task as TaskModel
            
            # Map string values to enums
            status_map = {
                'todo': TaskStatus.TODO,
                'in_progress': TaskStatus.IN_PROGRESS,
                'in_review': TaskStatus.IN_REVIEW,
                'completed': TaskStatus.COMPLETED
            }
            
            priority_map = {
                'low': TaskPriority.LOW,
                'medium': TaskPriority.MEDIUM,
                'high': TaskPriority.HIGH,
                'urgent': TaskPriority.URGENT
            }
            
            db_task = TaskModel(
                title=task_data['title'],
                description=task_data.get('description', ''),
                status=status_map.get(task_data.get('status', 'todo'), TaskStatus.TODO),
                priority=priority_map.get(task_data.get('priority', 'medium'), TaskPriority.MEDIUM),
                owner_id=user_id,
                created_by_id=user_id,
                assigned_to_id=task_data.get('assigned_to_id'),
                reviewer_id=task_data.get('reviewer_id'),
                due_date=task_data.get('due_date'),
                estimated_minutes=task_data.get('estimated_minutes')
            )
            
            db.add(db_task)
            db.commit()
            db.refresh(db_task)
            
            return {
                'success': True,
                'task': db_task,
                'message': f"✅ Task '{task_data['title']}' created successfully!"
            }
            
        except Exception as e:
            db.rollback()
            return {
                'success': False,
                'message': f"❌ Failed to create task: {str(e)}"
            }
    
    async def execute_task_edit(self, task_id: int, changes: Dict[str, str], user_id: int, db: Session) -> Dict[str, Any]:
        """Execute task editing"""
        try:
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            
            if not task:
                return {
                    'success': False,
                    'message': "❌ Task not found"
                }
            
            # Apply changes
            status_map = {
                'todo': TaskStatus.TODO,
                'in_progress': TaskStatus.IN_PROGRESS,
                'in_review': TaskStatus.IN_REVIEW,
                'completed': TaskStatus.COMPLETED
            }
            
            priority_map = {
                'low': TaskPriority.LOW,
                'medium': TaskPriority.MEDIUM,
                'high': TaskPriority.HIGH,
                'urgent': TaskPriority.URGENT
            }
            
            updated_fields = []
            
            for field, value in changes.items():
                if field == 'priority' and value in priority_map:
                    task.priority = priority_map[value]
                    updated_fields.append(f"priority → {value}")
                elif field == 'status' and value in status_map:
                    task.status = status_map[value]
                    updated_fields.append(f"status → {value}")
                elif field == 'description':
                    task.description = value
                    updated_fields.append(f"description → {value}")
                elif field == 'title':
                    task.title = value
                    updated_fields.append(f"title → {value}")
            
            if updated_fields:
                task.updated_at = datetime.now()
                db.commit()
                db.refresh(task)
                
                return {
                    'success': True,
                    'task': task,
                    'message': f"✅ Task '{task.title}' updated successfully! Changes: {', '.join(updated_fields)}"
                }
            else:
                return {
                    'success': False,
                    'message': "❌ No valid changes found"
                }
                
        except Exception as e:
            db.rollback()
            return {
                'success': False,
                'message': f"❌ Failed to update task: {str(e)}"
            }
    
    async def execute_task_move(self, task_id: int, new_status: str, user_id: int, db: Session) -> Dict[str, Any]:
        """Execute task movement"""
        try:
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            
            if not task:
                return {
                    'success': False,
                    'message': "❌ Task not found"
                }
            
            status_map = {
                'todo': TaskStatus.TODO,
                'in_progress': TaskStatus.IN_PROGRESS,
                'in_review': TaskStatus.IN_REVIEW,
                'completed': TaskStatus.COMPLETED
            }
            
            if new_status not in status_map:
                return {
                    'success': False,
                    'message': f"❌ Invalid status: {new_status}"
                }
            
            old_status = task.status.value
            task.status = status_map[new_status]
            task.updated_at = datetime.now()
            
            # Set completed_at if moving to completed
            if new_status == 'completed':
                task.completed_at = datetime.now()
            elif task.completed_at:
                task.completed_at = None
            
            db.commit()
            db.refresh(task)
            
            return {
                'success': True,
                'task': task,
                'message': f"✅ Task '{task.title}' moved from {old_status} to {new_status}!"
            }
            
        except Exception as e:
            db.rollback()
            return {
                'success': False,
                'message': f"❌ Failed to move task: {str(e)}"
            }
    
    async def execute_task_assignment(self, task_id: int, assignee_id: int, user_id: int, db: Session) -> Dict[str, Any]:
        """Execute task assignment"""
        try:
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            assignee = db.query(User).filter(User.id == assignee_id).first()
            
            if not task:
                return {
                    'success': False,
                    'message': "❌ Task not found"
                }
            
            if not assignee:
                return {
                    'success': False,
                    'message': "❌ Assignee not found"
                }
            
            task.assigned_to_id = assignee_id
            task.updated_at = datetime.now()
            
            db.commit()
            db.refresh(task)
            
            return {
                'success': True,
                'task': task,
                'message': f"✅ Task '{task.title}' assigned to {assignee.username}!"
            }
            
        except Exception as e:
            db.rollback()
            return {
                'success': False,
                'message': f"❌ Failed to assign task: {str(e)}"
            }
    
    async def execute_task_deletion(self, task_id: int, user_id: int, db: Session) -> Dict[str, Any]:
        """Execute task deletion"""
        try:
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            
            if not task:
                return {
                    'success': False,
                    'message': "❌ Task not found"
                }
            
            task_title = task.title
            db.delete(task)
            db.commit()
            
            return {
                'success': True,
                'message': f"✅ Task '{task_title}' deleted successfully!"
            }
            
        except Exception as e:
            db.rollback()
            return {
                'success': False,
                'message': f"❌ Failed to delete task: {str(e)}"
            }
    
    async def execute_bulk_operation(self, operation: str, task_ids: List[int], user_id: int, db: Session) -> Dict[str, Any]:
        """Execute bulk operations"""
        try:
            tasks = db.query(Task).filter(Task.id.in_(task_ids), Task.owner_id == user_id).all()
            
            if not tasks:
                return {
                    'success': False,
                    'message': "❌ No tasks found"
                }
            
            if operation == 'delete':
                for task in tasks:
                    db.delete(task)
                db.commit()
                return {
                    'success': True,
                    'message': f"✅ {len(tasks)} tasks deleted successfully!"
                }
            
            elif operation == 'complete':
                for task in tasks:
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now()
                    task.updated_at = datetime.now()
                db.commit()
                return {
                    'success': True,
                    'message': f"✅ {len(tasks)} tasks marked as completed!"
                }
            
            else:
                return {
                    'success': False,
                    'message': f"❌ Unsupported bulk operation: {operation}"
                }
                
        except Exception as e:
            db.rollback()
            return {
                'success': False,
                'message': f"❌ Failed to execute bulk operation: {str(e)}"
            }