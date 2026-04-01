from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.models import UserCreate, Token, UserResponse
from app.auth import get_password_hash, authenticate_user, create_access_token, get_current_active_user
from app.database import get_db_connection
from app.utils.email_sender import send_welcome_email, add_to_email_queue, send_verification_otp
from app.utils.otp_generator import otp_generator
from datetime import datetime, timedelta
import mysql.connector
import logging

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@router.post("/register")
def register(user: UserCreate, background_tasks: BackgroundTasks):
    """User register kare - OTP verification required"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    # Check if user exists
    cursor.execute("SELECT id, email_verified FROM users WHERE email = %s", (user.email,))
    existing = cursor.fetchone()
    if existing:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user (unverified)
    hashed_password = get_password_hash(user.password)
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash, full_name, role, email_verified) VALUES (%s, %s, %s, %s, %s)",
            (user.email, hashed_password, user.full_name, user.role, False)
        )
        conn.commit()
        
        # Get created user
        user_id = cursor.lastrowid
        cursor.execute("SELECT id, email, full_name, role, created_at, email_verified FROM users WHERE id = %s", (user_id,))
        new_user = cursor.fetchone()
        
        # Verification OTP bhejo (background task)
        background_tasks.add_task(
            send_verification_otp,
            user_id,
            user.email,
            user.full_name
        )
        logger.info(f"Verification OTP queued for {user.email}")
        
        cursor.close()
        conn.close()
        
        logger.info(f"New user registered (unverified): {user.email}")
        
        return {
            "id": new_user['id'],
            "email": new_user['email'],
            "full_name": new_user['full_name'],
            "role": new_user['role'],
            "created_at": new_user['created_at'],
            "message": "Registration successful! Please verify your email with OTP sent to your inbox.",
            "needs_verification": True
        }
        
    except mysql.connector.Error as err:
        conn.rollback()
        cursor.close()
        conn.close()
        logger.error(f"Registration error: {err}")
        raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """User login kare aur token return kare - Email verified hona chahiye"""
    logger.info(f"Login attempt for: {form_data.username}")
    
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning(f"Login failed for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if email is verified
    if not user.get('email_verified', False):
        logger.warning(f"Login attempt with unverified email: {form_data.username}")
        
        # Check if there's any pending OTP
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM email_verification 
            WHERE email = %s AND purpose = 'registration' AND is_verified = FALSE AND expires_at > NOW()
        """, (form_data.username,))
        pending = cursor.fetchone()
        cursor.close()
        conn.close()
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Email not verified. Please verify your email first.",
                "needs_verification": True,
                "has_pending_otp": pending is not None,
                "email": form_data.username
            }
        )
    
    # Create token with role
    access_token = create_access_token(
        data={"sub": user['email'], "role": user['role']}
    )
    
    logger.info(f"Login successful for: {form_data.username} (Role: {user['role']})")
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "role": user['role'],
        "email": user['email'],
        "full_name": user['full_name']
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user = Depends(get_current_active_user)):
    """Current user details return kare"""
    return current_user

@router.get("/check-role")
def check_role(current_user = Depends(get_current_active_user)):
    """Check current user role (debugging endpoint)"""
    return {
        "email": current_user['email'],
        "role": current_user['role'],
        "full_name": current_user['full_name']
    }

@router.post("/login-after-verification")
async def login_after_verification(email: str):
    """
    Verification ke baad auto-login ke liye - email pre-fill karega
    """
    return {
        "message": "Email verified successfully",
        "email": email,
        "redirect": "/login.html"
    }

@router.post("/forgot-password")
async def forgot_password(email: str, background_tasks: BackgroundTasks):
    """Send password reset OTP (replaces link-based version)"""
    
    # OTP router ke endpoint ko call karo
    from app.routers.otp import forgot_password as otp_forgot_password
    return await otp_forgot_password(email, background_tasks)

@router.post("/reset-password")
async def reset_password(email: str, otp: str, new_password: str, reset_token: str = None):
    """Reset password using OTP verification"""
    logger.info(f"Reset password attempt for {email}")
    
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = conn.cursor(dictionary=True)
        
        # ===== FIX: Direct OTP check ki jagah token check karo =====
        # User ID find karo
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user['id']
        
        # Check if OTP is already verified
        cursor.execute("""
            SELECT * FROM email_verification 
            WHERE email = %s AND otp_code = %s AND purpose = 'password_reset'
            AND is_verified = TRUE
            ORDER BY created_at DESC LIMIT 1
        """, (email, otp))
        
        verified_otp = cursor.fetchone()
        
        if not verified_otp:
            # Agar OTP verified nahi hai to verify karo
            cursor.execute("""
                SELECT * FROM email_verification 
                WHERE email = %s AND otp_code = %s AND purpose = 'password_reset'
                AND is_verified = FALSE AND expires_at > NOW()
                ORDER BY created_at DESC LIMIT 1
            """, (email, otp))
            
            pending_otp = cursor.fetchone()
            
            if not pending_otp:
                raise HTTPException(status_code=400, detail="Invalid or expired OTP")
            
            # Mark OTP as verified
            cursor.execute("""
                UPDATE email_verification 
                SET is_verified = TRUE 
                WHERE id = %s
            """, (pending_otp['id'],))
            
            logger.info(f"OTP verified for {email}")
        
        # Update password
        hashed = get_password_hash(new_password)
        cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hashed, user_id))
        
        # Delete used tokens
        cursor.execute("DELETE FROM password_reset_tokens WHERE user_id = %s", (user_id,))
        
        conn.commit()
        logger.info(f"✅ Password reset successful for {email}")
        
        return {"message": "Password reset successful"}
        
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Reset password error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset password: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()