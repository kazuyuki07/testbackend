from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import jwt
from hashlib import sha256
import os
from dotenv import load_dotenv

from database import get_db
from models import User, UserRole
from schemas import UserCreate, UserResponse, Token, LoginRequest

load_dotenv()

KEY = os.getenv("KEY")
ALGORITHM = "HS256" #!!! DO NOT CHANGE ALGORITHM !!!
TOKEN_EXPIRE_DAYS = 30 # epire days customizable



router = APIRouter(prefix="/auth", tags=["Auth"])

def create_token(user_id: int, role: UserRole):
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS) #* days можно изменить
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, KEY, algorithm=ALGORITHM)


def get_current_user(request: Request, db: Session = Depends(get_db)):
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authentificated")
    
    try:
        payload = jwt.decode(access_token, KEY, algorithms=ALGORITHM)
        user_id = int(payload.get("sub"))
        user =  db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
def get_active_current_user(current_user: User = Depends(get_current_user)):
    return current_user

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if sha256(plain_password.encode()).hexdigest() == hashed_password:
        return True

def hash_password(password: str) -> str:
    return sha256(password.encode()).hexdigest()

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    # Regestration

    Adds user values to database
    
    ## Errors:
    If `Email` exists, then raises `HTTPException` with status code `400` as `Email already registered` 
    """

    exiting_user = db.query(User).filter(User.email == user_data.email).first()
    if exiting_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    password = hash_password(user_data.password)
    user = User(
        email= user_data.email,
        username = user_data.username,
        hashed_password = password
    )

    db.add(user)
    db.commit()
    return user

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """
    # Login

    Log in's your profile and writes JWT token to cookies that will use
    as current user.
    
    ## Errors:
    Wrong passwords or data raises `HTTPException` with status code `401` as `Invalid credentials`
    """

    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_token(user.id, user.role)
    
    response.set_cookie(key="access_token", 
                        value=access_token, 
                        httponly= True
                        )

    return Token(access_token=access_token)

@router.post("/refresh", response_model=Token)
def refresh(request: Request, response: Response):
    """
    # Refresh JWT token
    
    Updates JWT access token in **cookie**
    
    ## Errors:
    1. No access token in cookies: `HTTPException` status `401`
    2. Invalid or expired token: `HTTPException` status `401`
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="No access token")
    
    try:
        payload = jwt.decode(access_token, KEY, algorithms=ALGORITHM, 
                            options={"verify_exp": False})
        user_id = int(payload.get("sub"))
        role = UserRole(payload.get("role"))

        new_access_token = create_token(user_id, role)

        response.set_cookie(key="access_token", 
                            value=new_access_token, 
                            httponly=True
                            )
        
        return Token(access_token=new_access_token)
    
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")