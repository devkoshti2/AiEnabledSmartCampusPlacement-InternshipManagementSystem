from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from app.database import get_db_connection
from app.utils.email_sender import verify_otp, send_verification_otp, send_password_reset_otp
from app.utils.otp_generator import otp_generator
from app.auth import get_user_by_email
import logging
from datetime import datetime

router = APIRouter(prefix="/otp", tags=["OTP Verification"])
logger = logging.getLogger(__name__)

@router.post("/send-verification")
async def send_verification(email: str, background_tasks: BackgroundTasks):
    """
    Registration ke baad verification OTP bhejo
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # User check karo
        cursor.execute("SELECT id, full_name, email_verified FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user['email_verified']:
            return {"message": "Email already verified"}
        
        # OTP bhejo
        background_tasks.add_task(
            send_verification_otp,
            user['id'],
            email,
            user['full_name']
        )
        
        return {"message": "Verification OTP sent to your email"}
        
    except Exception as e:
        logger.error(f"Send verification error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send OTP")
    finally:
        cursor.close()
        conn.close()

@router.post("/verify")
async def verify_email_otp(email: str, otp: str, purpose: str = "registration"):
    """
    OTP verify karo
    purpose: 'registration' ya 'password_reset'
    """
    logger.info(f"Verifying OTP for {email} with purpose {purpose}")
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # OTP check karo
        cursor.execute("""
            SELECT * FROM email_verification 
            WHERE email = %s AND otp_code = %s AND purpose = %s 
            AND is_verified = FALSE AND expires_at > NOW()
            ORDER BY created_at DESC LIMIT 1
        """, (email, otp, purpose))
        
        record = cursor.fetchone()
        
        if not record:
            # Check if OTP exists but expired
            cursor.execute("""
                SELECT * FROM email_verification 
                WHERE email = %s AND otp_code = %s AND purpose = %s 
                AND is_verified = FALSE
                ORDER BY created_at DESC LIMIT 1
            """, (email, otp, purpose))
            
            expired_record = cursor.fetchone()
            
            if expired_record:
                logger.warning(f"OTP expired for {email}")
                raise HTTPException(status_code=400, detail="OTP expired. Please request new OTP.")
            else:
                logger.warning(f"Invalid OTP for {email}")
                raise HTTPException(status_code=400, detail="Invalid OTP")
        
        # OTP verify mark karo
        cursor.execute("""
            UPDATE email_verification 
            SET is_verified = TRUE 
            WHERE id = %s
        """, (record['id'],))
        
        # Agar registration purpose hai to user ko verified mark karo
        if purpose == 'registration':
            cursor.execute("""
                UPDATE users 
                SET email_verified = TRUE 
                WHERE id = %s
            """, (record['user_id'],))
            logger.info(f"✅ User {record['user_id']} email verified successfully")
        
        conn.commit()
        
        return {
            "message": "OTP verified successfully",
            "verified": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OTP verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.post("/resend-verification")
async def resend_verification(email: str, background_tasks: BackgroundTasks):
    """
    Verification OTP dubara bhejo
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT id, full_name, email_verified FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user['email_verified']:
            return {"message": "Email already verified"}
        
        # Purane OTP delete karo
        cursor.execute("""
            DELETE FROM email_verification 
            WHERE email = %s AND purpose = 'registration' AND is_verified = FALSE
        """, (email,))
        conn.commit()
        
        # Naya OTP bhejo
        background_tasks.add_task(
            send_verification_otp,
            user['id'],
            email,
            user['full_name']
        )
        
        return {"message": "New verification OTP sent"}
        
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(status_code=500, detail="Failed to resend OTP")
    finally:
        cursor.close()
        conn.close()

@router.post("/forgot-password")
async def forgot_password(email: str, background_tasks: BackgroundTasks):
    """
    Forgot password ke liye OTP bhejo
    """
    user = get_user_by_email(email)
    if not user:
        # Security: User exist na kare to bhi same message do
        logger.info(f"Password reset requested for non-existent email: {email}")
        return {"message": "If email exists, OTP will be sent"}
    
    background_tasks.add_task(
        send_password_reset_otp,
        email,
        user['id'],
        user['full_name']
    )
    
    return {"message": "Password reset OTP sent to your email"}

@router.post("/verify-reset-otp")
async def verify_reset_otp(email: str, otp: str):
    """
    Password reset ke liye OTP verify karo
    """
    logger.info(f"Verifying reset OTP for {email} with OTP: {otp}")
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Pehle check karo ki OTP already verified to nahi hai
        cursor.execute("""
            SELECT * FROM email_verification 
            WHERE email = %s AND otp_code = %s AND purpose = 'password_reset'
            AND is_verified = TRUE
            ORDER BY created_at DESC LIMIT 1
        """, (email, otp))
        
        verified_record = cursor.fetchone()
        
        if verified_record:
            logger.info(f"OTP already verified for {email}")
            # Already verified hai to existing token do
            cursor.execute("""
                SELECT token FROM password_reset_tokens 
                WHERE user_id = %s AND used = FALSE AND expires_at > NOW()
                ORDER BY created_at DESC LIMIT 1
            """, (verified_record['user_id'],))
            
            token_record = cursor.fetchone()
            
            if token_record:
                return {
                    "message": "OTP already verified",
                    "reset_token": token_record['token']
                }
        
        # Nahi verified to verify karo
        cursor.execute("""
            SELECT * FROM email_verification 
            WHERE email = %s AND otp_code = %s AND purpose = 'password_reset'
            AND is_verified = FALSE AND expires_at > NOW()
            ORDER BY created_at DESC LIMIT 1
        """, (email, otp))
        
        record = cursor.fetchone()
        
        if not record:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
        # Mark OTP as verified
        cursor.execute("""
            UPDATE email_verification 
            SET is_verified = TRUE 
            WHERE id = %s
        """, (record['id'],))
        
        # Generate reset token
        temp_token = otp_generator.generate_secure_token()
        expires_at = otp_generator.generate_expiry(minutes=5)
        
        # Save token
        cursor.execute("""
            INSERT INTO password_reset_tokens (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """, (record['user_id'], temp_token, expires_at))
        
        conn.commit()
        
        logger.info(f"✅ Reset OTP verified successfully for {email}")
        
        return {
            "message": "OTP verified successfully",
            "reset_token": temp_token
        }
        
    except Exception as e:
        logger.error(f"Reset OTP verification error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()