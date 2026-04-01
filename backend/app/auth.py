from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.config import settings
from app.database import get_db_connection
from app.models import TokenData
import mysql.connector
import logging
import bcrypt

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ========== PASSWORD HASHING ==========

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Password verify kare using bcrypt"""
    try:
        if isinstance(plain_password, str):
            plain_password = plain_password.encode('utf-8')
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Password hash kare using bcrypt"""
    try:
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password, salt)
        
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Password hashing error: {e}")
        raise

def create_access_token(data: dict):
    """JWT token create kare"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_user_by_email(email: str):
    """Email se user dhundhe"""
    conn = get_db_connection()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def authenticate_user(email: str, password: str):
    """User authenticate kare"""
    user = get_user_by_email(email)
    if not user:
        logger.warning(f"User not found: {email}")
        return False
    
    if not verify_password(password, user['password_hash']):
        logger.warning(f"Invalid password for: {email}")
        return False
    
    logger.info(f"User authenticated: {email} (Role: {user['role']})")
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Current user get kare from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, role=role)
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception
    
    user = get_user_by_email(email=token_data.email)
    if user is None:
        raise credentials_exception
    
    # Log user role for debugging
    logger.info(f"Current user: {user['email']} (Role: {user['role']})")
    return user

async def get_current_active_user(current_user = Depends(get_current_user)):
    """Active user check kare"""
    if not current_user['is_active']:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def require_admin(current_user = Depends(get_current_active_user)):
    """Admin role check kare - FIXED with better error message"""
    logger.info(f"Checking admin access for user: {current_user['email']} (Role: {current_user['role']})")
    
    if current_user['role'] != 'admin':
        logger.warning(f"Access denied for user {current_user['email']} - not admin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. Current role: " + current_user['role']
        )
    return current_user