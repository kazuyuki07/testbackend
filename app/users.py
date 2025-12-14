from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserRole
from schemas import UserResponse, UserUpdate, SUPERADMINUserUpdate
from auth import get_active_current_user, verify_password, hash_password

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_active_current_user)):
    """
    # Get current user profile
    
    Returns profile of authenticated user
    
    ## Errors:
    Not authorized: `HTTPException` status `400`
    """

    return current_user

@router.put("/me", response_model=UserResponse)
def update_current_user(
    user_data: UserUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_current_user)
):
    """
    # Update current user profile
    
    Updates own user profile (email, username, password)
    
    ## Errors:
    1. Email already registered: `HTTPException` status `400`
    """

    update_data = user_data.model_dump(exclude_unset=True)

    if 'email' in update_data and update_data['email'] != current_user.email:
        existing = db.query(User).filter(User.email == update_data['email']).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    response.delete_cookie("access_token")

    db.commit()
    db.refresh(current_user)
    return current_user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int, 
    user_data: SUPERADMINUserUpdate,
    current_user: User = Depends(get_active_current_user),
    db: Session = Depends(get_db)
):
    """
    # Update any user (SUPERADMIN only)
    
    `SUPERADMIN` can update any user profile or role
    
    ## Errors:
    1. User is not `SUPERADMIN`: `HTTPException` status `403`
    2. Target user not found: `HTTPException` status `404`
    3. `Email` already registered: `HTTPException` status `400`
    4. `SUPERADMIN` cannot change own role: `HTTPException` status `400`
    5. Current password incorrect (self password change): `HTTPException` status `400`
    6. `SUPERADMIN` cannot change other users' passwords: `HTTPException` status `400`
    """
    
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Superadmin role required")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User doesn't exist")
    
    is_self_update = current_user.id == user_id
    
    update_data = user_data.model_dump(exclude_unset=True)
    
    if 'email' in update_data and update_data['email'] != user.email:
        existing = db.query(User).filter(User.email == update_data['email']).first()
        if existing and existing.id != user_id:
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = update_data['email']
    
    if 'username' in update_data:
        user.username = update_data['username']
    
    if 'role' in update_data:
        if is_self_update:
            raise HTTPException(
                status_code=400, 
                detail="Superadmin cannot change own role"
            )
        user.role = update_data['role']
    if 'password' in update_data:
        password_data = update_data['password']
        
        if is_self_update:
            if not verify_password(password_data.current_password, current_user.hashed_password):
                raise HTTPException(status_code=400, detail="Current password is incorrect")
            user.hashed_password = hash_password(password_data.new_password)
        else:
            raise HTTPException(
                status_code=400, 
                detail="Superadmin cannot change other users' passwords"
            )
    
    db.commit()
    db.refresh(user)
    
    return user
    