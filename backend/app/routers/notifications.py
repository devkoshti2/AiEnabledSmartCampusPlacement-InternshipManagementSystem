from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_active_user, require_admin
from app.database import get_db_connection
from app.utils.email_sender import add_to_email_queue
from app.database import get_db_connection
import logging
from datetime import datetime

router = APIRouter(prefix="/notifications", tags=["Notifications"])
logger = logging.getLogger(__name__)

# Create notifications table
def create_notifications_table():
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            title VARCHAR(200) NOT NULL,
            message TEXT NOT NULL,
            type ENUM('info', 'success', 'warning', 'danger') DEFAULT 'info',
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            link VARCHAR(255) NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_user_read (user_id, is_read)
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# Call this in main.py startup
create_notifications_table()

@router.post("/send")
async def send_notification(
    user_id: int,
    title: str,
    message: str,
    type: str = "info",
    link: str = None,
    send_email: bool = False,
    admin = Depends(require_admin)
):
    """Send notification to specific user"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO notifications (user_id, title, message, type, link)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, title, message, type, link))

        notification_id = cursor.lastrowid

        if send_email:
            # User ki email pata karo
            cursor.execute("SELECT email, full_name FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if user:
                email = user[0]
                user_name = user[1]
                
                template_data = {
                    'title': title,
                    'message': message,
                    'user_name': user_name
                }
                
                add_to_email_queue(
                    notification_id=notification_id,
                    user_email=email,
                    subject=title,
                    template_name='simple',
                    template_data=template_data
                )
        
        conn.commit()
        return {"message": "Notification sent", "id": notification_id}
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Notification error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send notification")
    finally:
        cursor.close()
        conn.close()

@router.post("/broadcast")
async def broadcast_notification(
    title: str,
    message: str,
    type: str = "info",
    role: str = None,  # If None, send to all
    admin = Depends(require_admin)
):
    """Send notification to all users or specific role"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor()
    
    try:
        if role:
            cursor.execute("SELECT id FROM users WHERE role = %s", (role,))
        else:
            cursor.execute("SELECT id FROM users")
        
        users = cursor.fetchall()
        
        for user in users:
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, type)
                VALUES (%s, %s, %s, %s)
            """, (user[0], title, message, type))
        
        conn.commit()
        return {"message": f"Notification sent to {len(users)} users"}
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Broadcast error: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast")
    finally:
        cursor.close()
        conn.close()

@router.get("/my-notifications")
async def get_my_notifications(
    limit: int = 20,
    unread_only: bool = False,
    current_user = Depends(get_current_active_user)
):
    """Get user's notifications"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
            SELECT * FROM notifications 
            WHERE user_id = %s
        """
        params = [current_user['id']]
        
        if unread_only:
            query += " AND is_read = FALSE"
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        notifications = cursor.fetchall()
        
        return notifications
        
    finally:
        cursor.close()
        conn.close()

@router.put("/mark-read/{notification_id}")
async def mark_notification_read(
    notification_id: int,
    current_user = Depends(get_current_active_user)
):
    """Mark notification as read"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE notifications 
            SET is_read = TRUE 
            WHERE id = %s AND user_id = %s
        """, (notification_id, current_user['id']))
        
        conn.commit()
        return {"message": "Marked as read"}
        
    finally:
        cursor.close()
        conn.close()

@router.put("/mark-all-read")
async def mark_all_read(current_user = Depends(get_current_active_user)):
    """Mark all notifications as read"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE notifications 
            SET is_read = TRUE 
            WHERE user_id = %s
        """, (current_user['id'],))
        
        conn.commit()
        return {"message": "All marked as read"}
        
    finally:
        cursor.close()
        conn.close()

@router.get("/unread-count")
async def get_unread_count(current_user = Depends(get_current_active_user)):
    """Get count of unread notifications"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM notifications 
            WHERE user_id = %s AND is_read = FALSE
        """, (current_user['id'],))
        
        count = cursor.fetchone()[0]
        return {"count": count}
        
    finally:
        cursor.close()
        conn.close()