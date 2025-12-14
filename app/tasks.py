from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Task, User, Comment, UserRole, TaskPriority, TaskStatus
from schemas import (TaskCreate, TaskUpdate, TaskResponse, 
                     CommentCreate, CommentResponse)
from auth import get_active_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.get("/")
def get_tasks(
    author_id: Optional[int] = None,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    deadline_before: Optional[datetime] = None,
    deadline_after: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_current_user)
):
    """
    # Getting data with filter
    
    Returns all tasks by filtering

    ### Filters:
    - Author
    - Status
    - Priority
    - Before deadline
    - After deadline
    
    ## Errors:
    If returns nothing, then raises `HTTPException` with status code `404`, meaning tasks
    is **not founded**.
    """
    query = db.query(Task)
        
    if author_id:
        query = query.filter(Task.author_id == author_id)
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    if deadline_before:
        query = query.filter(Task.deadline >= deadline_before)
    if deadline_after:
        query = query.filter(Task.deadline <= deadline_after)
    
    tasks = query.all()

    if tasks == []:
        raise HTTPException(status_code=404, detail="No tasks found")

    return tasks


@router.post("/", response_model= TaskResponse)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_current_user)
    ):
    """
    # Create a new task
    
    Creates a task (available only to administrators)
    
    ## Errors:
    1. User is not an administrator: `HTTPException` status `403` requiring admin role
    2. Assignee user doesn't exist: `HTTPException` status `422`
    """

    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(status_code=403, detail="Admin role required")

    if not db.query(User).filter(User.id == task_data.assignee_id).first():
        raise HTTPException(status_code=422, detail="Assignee user doesn't exists")
    

    taskdb = Task(
        **task_data.dict(),
        author_id=current_user.id
    )


    db.add(taskdb)
    db.commit()
    
    return TaskResponse(
        title= task_data.title,
        description= task_data.description,
        deadline= task_data.deadline,
        status= task_data.status,
        created_at= taskdb.created_at,
        author_id= taskdb.author_id,
        assignee_id= task_data.assignee_id
    )

@router.get("/{task_id}", response_model=TaskResponse)
def get_task_detail(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_active_current_user)):
    """
    # Get task details by ID
    
    Returns details of task
    
    ## Errors:
    1. Task not found: `HTTPException` status `404`
    """
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task doesn't exists")

    return TaskResponse(
	    title= task.title,
	    description= task.description,
	    priority= task.priority,
	    created_at= task.created_at,
	    assignee_id= task.assignee_id,
	    status= task.status,
	    deadline= task.deadline,
	    author_id= task.author_id
)

@router.put("/{task_id}")
def update_task(task_id: int, up_task: TaskUpdate, db: Session = Depends(get_db), 
                current_user: User = Depends(get_active_current_user)):
    """
    # Update task by ID
    
    Updates task fields (available for admins (as task author that can update own task) and superadmins)
    
    ## Errors:
    1. User is not admin: `HTTPException` status `403`
    2. Task not found: `HTTPException` status `404`
    3. Access denied for non-author ADMIN: `HTTPException` status `403`
    """

    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(status_code=403, detail="Admin role required")
    

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    

    if current_user.role == UserRole.ADMIN and task.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    

    for key, value in up_task.dict(exclude_unset=True).items():
        setattr(task, key, value)
    
    db.commit()
    db.refresh(task)
    return {"msg": "Task updated", "task_id": task_id}

@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_active_current_user)):
    """
    # Delete task by ID
    
    Deletes selected task by id (available for admins (as task author that can update own task) and superadmins)
    
    ## Errors:
    1. User is not admin: `HTTPException` status `403`
    2. Task not found: `HTTPException` status `404`
    3. Access denied for non-author ADMIN: `HTTPException` status `403`
    """

    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(status_code=403, detail="Admin role required")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task doesn't exists")

    if current_user.role == UserRole.ADMIN and task.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.delete(task)
    db.commit()
    return {"msg": "Task is deleted successfully"}

@router.post("/{task_id}/comments", response_model= CommentResponse)
def comment_to_task(task_id: int, comment: CommentCreate,current_user: User = Depends(get_active_current_user), db: Session = Depends(get_db)): 
    """
    # Add comment to task
    
    Adds a comment to selected task by id
    
    ## Errors:
    1. Task not found: `HTTPException` status `404`
    """
    
    new_comment = CommentCreate(
        text= comment.text
    )

    db.add(Comment(
        **new_comment.dict(),
        task_id = task_id,
        author_id= current_user.id
    ))

    db.commit()

    return CommentResponse(
        task_id= task_id,
        text= comment.text,
        author= current_user.username,
        created_at= datetime.now(timezone.utc),
    )