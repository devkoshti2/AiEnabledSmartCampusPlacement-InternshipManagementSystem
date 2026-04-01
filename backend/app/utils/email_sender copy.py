import smtplib
import logging
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from app.config import settings
from app.database import get_db_connection
from datetime import datetime
from app.utils.otp_generator import otp_generator

# Email templates import karo
from app.utils.email_templates import (
    get_welcome_email_template,
    get_drive_announcement_template,
    get_status_update_template,
    get_password_reset_template,
    get_simple_text_email,
    get_verify_otp_template,
    get_password_reset_otp_template,
    get_shortlist_email_template
)

logger = logging.getLogger(__name__)

# Base URL for links
BASE_URL = "http://localhost:8000"

class EmailSender:
    """Email bhejne ka main class"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME
        
        # Debug - check if settings are loaded (remove in production)
        logger.info(f"📧 EmailSender initialized with: {self.smtp_user}")
    
    def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Single email bhejo"""
        try:
            # Email message banaye
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # HTML part
            part = MIMEText(html_content, 'html')
            msg.attach(part)
            
            # SMTP se connect karo
            logger.info(f"📡 Connecting to {self.smtp_host}:{self.smtp_port}")
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            
            logger.info(f"🔐 Logging in as {self.smtp_user}")
            server.login(self.smtp_user, self.smtp_password)
            
            # Email bhejo
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email send failed to {to_email}: {str(e)}")
            return False
    
    def send_bulk_emails(self, to_emails: List[str], subject: str, html_content: str) -> dict:
        """Bulk emails bhejo (batch mein)"""
        results = {
            'total': len(to_emails),
            'success': 0,
            'failed': 0,
            'failed_emails': []
        }
        
        for email in to_emails:
            success = self.send_email(email, subject, html_content)
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
                results['failed_emails'].append(email)
        
        logger.info(f"Bulk email complete: {results['success']} success, {results['failed']} failed")
        return results

# ===== EMAIL QUEUE FUNCTIONS =====

def add_to_email_queue(notification_id: int, user_email: str, subject: str, template_name: str, template_data: dict):
    """Notification ko email queue mein add karo - WITHOUT LOCKS"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("❌ Failed to connect to database for email queue")
            return False
        
        cursor = conn.cursor()
        
        # ❌ YEH LINE HATAA DO - Lock timeout set karne ki need nahi
        # cursor.execute("SET SESSION innodb_lock_wait_timeout = 50")  # ← ISKO HATAAO
        
        if isinstance(template_data, dict):
            template_data_str = json.dumps(template_data)
        else:
            template_data_str = str(template_data)
        
        logger.info(f"📝 Attempting to insert email into queue: {user_email}, {subject}, {template_name}")
        
        cursor.execute("""
            INSERT INTO email_queue 
            (notification_id, user_email, subject, template_name, template_data, status, created_at)
            VALUES (%s, %s, %s, %s, %s, 'pending', NOW())
        """, (notification_id, user_email, subject, template_name, template_data_str))
        
        inserted_id = cursor.lastrowid
        conn.commit()
        logger.info(f"✅ Added to email queue: ID={inserted_id}, {subject} -> {user_email}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to add to email queue: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def process_email_queue():
    """Email queue process karo - WITH DEBUG LOGGING"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to connect to database")
            return
        
        cursor = conn.cursor(dictionary=True)
        
        # First, check total counts
        cursor.execute("SELECT COUNT(*) as total, status FROM email_queue GROUP BY status")
        counts = cursor.fetchall()
        logger.info(f"📊 Email queue stats: {counts}")
        
        # Then get pending emails
        cursor.execute("""
            SELECT * FROM email_queue 
            WHERE status = 'pending' 
            AND attempts < 3
            ORDER BY created_at ASC
            LIMIT 10
        """)
        
        emails = cursor.fetchall()
        logger.info(f"📧 Found {len(emails)} pending emails in queue")
        
        # Log the IDs if found
        if emails:
            email_ids = [e['id'] for e in emails]
            logger.info(f"📋 Pending email IDs: {email_ids}")
        else:
            # If no pending emails, check if there are any emails at all
            cursor.execute("SELECT COUNT(*) as total FROM email_queue")
            total = cursor.fetchone()['total']
            logger.info(f"📊 Total emails in queue table: {total}")
            
            if total > 0:
                # Show some recent emails
                cursor.execute("""
                    SELECT id, user_email, status, created_at 
                    FROM email_queue 
                    ORDER BY id DESC 
                    LIMIT 5
                """)
                recent = cursor.fetchall()
                logger.info(f"📨 Recent emails: {recent}")
        
        if not emails:
            return
            
        email_sender = EmailSender()
        
        for email in emails:
            try:
                logger.info(f"📨 Processing email ID {email['id']} to {email['user_email']}")
                logger.info(f"📧 Template: {email['template_name']}, Subject: {email['subject']}")
                
                # JSON string ko dict mein convert karo
                if email['template_data']:
                    template_data = json.loads(email['template_data'])
                    logger.info(f"📦 Template data: {template_data}")
                else:
                    template_data = {}
                    logger.warning(f"⚠️ No template data for email {email['id']}")
                
                # Get appropriate template
                if email['template_name'] == 'welcome':
                    html = get_welcome_email_template(**template_data)
                elif email['template_name'] == 'drive':
                    html = get_drive_announcement_template(**template_data)
                elif email['template_name'] == 'status':
                    html = get_status_update_template(**template_data)
                elif email['template_name'] == 'reset':
                    html = get_password_reset_template(**template_data)
                elif email['template_name'] == 'verify_otp':
                    html = get_verify_otp_template(**template_data)
                elif email['template_name'] == 'reset_otp':
                    html = get_password_reset_otp_template(**template_data)
                elif email['template_name'] == 'shortlist':
                    logger.info(f"🎯 Processing shortlist email for {template_data.get('student_name')}")
                    html = get_shortlist_email_template(**template_data)
                else:
                    logger.warning(f"⚠️ Unknown template: {email['template_name']}")
                    html = get_simple_text_email("Notification", str(template_data))
                
                # Email bhejo
                logger.info(f"📤 Attempting to send email to {email['user_email']}")
                success = email_sender.send_email(email['user_email'], email['subject'], html)
                
                # Update cursor
                update_cursor = conn.cursor()
                if success:
                    logger.info(f"✅ Email sent successfully to {email['user_email']}")
                    update_cursor.execute("""
                        UPDATE email_queue 
                        SET status = 'sent', sent_at = NOW() 
                        WHERE id = %s
                    """, (email['id'],))
                    
                    if email['notification_id']:
                        update_cursor.execute("""
                            UPDATE notifications 
                            SET email_sent = TRUE, email_sent_at = NOW() 
                            WHERE id = %s
                        """, (email['notification_id'],))
                else:
                    logger.error(f"❌ Failed to send email to {email['user_email']}")
                    update_cursor.execute("""
                        UPDATE email_queue 
                        SET attempts = attempts + 1,
                            status = CASE WHEN attempts + 1 >= 3 THEN 'failed' ELSE 'pending' END
                        WHERE id = %s
                    """, (email['id'],))
                
                update_cursor.close()
                conn.commit()
                
            except Exception as e:
                logger.error(f"💥 Error processing email {email['id']}: {str(e)}")
                import traceback
                traceback.print_exc()
                error_cursor = conn.cursor()
                error_cursor.execute("""
                    UPDATE email_queue 
                    SET attempts = attempts + 1, error_message = %s
                    WHERE id = %s
                """, (str(e)[:200], email['id']))
                error_cursor.close()
                conn.commit()
                
    except Exception as e:
        logger.error(f"💥 Email queue processing error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ===== TRIGGER FUNCTIONS =====

def send_welcome_email(user_id: int, user_email: str, user_name: str):
    """Welcome email bhejo (registration par)"""
    subject = "Welcome to Placement System! 🎓"
    template_data = {
        'user_name': user_name,
        'login_url': f'{BASE_URL}/login.html'
    }
    
    # Direct send karo (queue mein nahi dalna)
    email_sender = EmailSender()
    html = get_welcome_email_template(**template_data)
    
    logger.info(f"📧 Attempting to send welcome email to {user_email}")
    result = email_sender.send_email(user_email, subject, html)
    if result:
        logger.info(f"✅ Welcome email sent to {user_email}")
    else:
        logger.error(f"❌ Failed to send welcome email to {user_email}")
    return result

def send_drive_notifications(drive_id: int, drive_title: str, company_name: str, last_date: str, eligibility: str):
    """New drive ke liye saare students ko email"""
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Saare students ki email lo
        cursor.execute("""
            SELECT u.id, u.email, u.full_name 
            FROM users u
            WHERE u.role = 'student' AND u.is_active = TRUE
        """)
        
        students = cursor.fetchall()
        
        subject = f"New Placement Drive: {drive_title} at {company_name}"
        
        for student in students:
            template_data = {
                'drive_title': drive_title,
                'company_name': company_name,
                'last_date': last_date,
                'eligibility': eligibility,
                'drive_url': f'{BASE_URL}/drives.html?id={drive_id}',
                'drive_id': drive_id
            }
            
            # Pehle notification insert karo
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, type, link)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                student['id'],
                f"New Drive: {drive_title}",
                f"{company_name} is hiring for {drive_title}. Apply before {last_date}",
                'info',
                f'/drives.html?id={drive_id}'
            ))
            
            notification_id = cursor.lastrowid
            
            # template_data ko JSON string mein convert karo
            template_data_str = json.dumps(template_data)
            
            # Email queue mein add karo
            cursor.execute("""
                INSERT INTO email_queue (notification_id, user_email, subject, template_name, template_data)
                VALUES (%s, %s, %s, %s, %s)
            """, (notification_id, student['email'], subject, 'drive', template_data_str))
        
        conn.commit()
        logger.info(f"✅ Drive notifications queued for {len(students)} students")
        
    except Exception as e:
        logger.error(f"Error queueing drive notifications: {e}")
    finally:
        cursor.close()
        conn.close()

def send_status_update_email(application_id: int, student_id: int, old_status: str, new_status: str):
    """Application status change par email"""
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Student details
        cursor.execute("""
            SELECT u.email, u.full_name, u.id
            FROM users u
            WHERE u.id = %s
        """, (student_id,))
        
        student = cursor.fetchone()
        
        # Application aur drive details
        cursor.execute("""
            SELECT a.*, pd.job_title, c.name as company_name
            FROM applications a
            JOIN placement_drives pd ON a.drive_id = pd.id
            JOIN companies c ON pd.company_id = c.id
            WHERE a.id = %s
        """, (application_id,))
        
        app = cursor.fetchone()
        
        if student and app:
            subject = f"Application Status Update: {app['company_name']} - {app['job_title']}"
            
            template_data = {
                'student_name': student['full_name'],
                'company_name': app['company_name'],
                'job_title': app['job_title'],
                'old_status': old_status,
                'new_status': new_status,
                'dashboard_url': f'{BASE_URL}/applications.html'
            }
            
            # Notification insert karo
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, type, link)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                student['id'],
                f"Application {new_status}",
                f"Your application for {app['company_name']} - {app['job_title']} is now {new_status}",
                'success' if new_status in ['shortlisted', 'selected'] else 'danger',
                '/applications.html'
            ))
            
            notification_id = cursor.lastrowid
            
            # template_data ko JSON string mein convert karo
            template_data_str = json.dumps(template_data)
            
            # Email queue mein add
            cursor.execute("""
                INSERT INTO email_queue (notification_id, user_email, subject, template_name, template_data)
                VALUES (%s, %s, %s, %s, %s)
            """, (notification_id, student['email'], subject, 'status', template_data_str))
            
            conn.commit()
            logger.info(f"✅ Status update email queued for {student['email']}")
        
    except Exception as e:
        logger.error(f"Error queueing status update email: {e}")
    finally:
        cursor.close()
        conn.close()

# ===== OTP EMAIL FUNCTIONS =====

def send_verification_otp(user_id: int, email: str, user_name: str):
    """
    Registration ke time OTP bhejo
    """
    conn = None
    cursor = None
    try:
        # OTP generate karo
        otp_code = otp_generator.generate_otp()
        expires_at = otp_generator.generate_expiry(minutes=10)
        
        print(f"\n🔐 ===== OTP GENERATED ===== 🔐")
        print(f"📧 Email: {email}")
        print(f"🔑 OTP: {otp_code}")
        print(f"⏰ Expires: {expires_at}")
        print(f"===========================\n")
        
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        cursor = conn.cursor()
        
        # Purane OTP delete karo
        cursor.execute("""
            DELETE FROM email_verification 
            WHERE email = %s AND purpose = 'registration' AND is_verified = FALSE
        """, (email,))
        
        # Naya OTP insert karo
        cursor.execute("""
            INSERT INTO email_verification (user_id, email, otp_code, purpose, expires_at)
            VALUES (%s, %s, %s, 'registration', %s)
        """, (user_id, email, otp_code, expires_at))
        
        conn.commit()
        print(f"✅ OTP saved to database for {email}")
        
        # Email bhejo
        subject = f"Your OTP: {otp_code} - Verify Email"
        
        # Simple HTML template
        html = f"""
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h2>Hello {user_name}!</h2>
            <p>Your verification OTP is:</p>
            <h1 style="font-size: 40px; color: #0A1929; background: #F0B90B; padding: 20px; text-align: center;">
                {otp_code}
            </h1>
            <p>This OTP will expire in 10 minutes.</p>
        </body>
        </html>
        """
        
        email_sender = EmailSender()
        result = email_sender.send_email(email, subject, html)
        
        if result:
            print(f"✅ Email sent to {email}")
        else:
            print(f"❌ Email sending failed")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def send_password_reset_otp(email: str, user_id: int, user_name: str):
    """
    Forgot password ke time OTP bhejo
    """
    conn = None
    cursor = None
    try:
        # OTP generate karo
        otp_code = otp_generator.generate_otp()
        expires_at = otp_generator.generate_expiry(minutes=10)
        
        # ===== IMPORTANT: YEH PRINT DONO FILES MEIN ADD KARO =====
        print(f"\n🔐 ===== PASSWORD RESET OTP GENERATED ===== 🔐")
        print(f"📧 Email: {email}")
        print(f"👤 User: {user_name}")
        print(f"🔑 OTP: {otp_code}")
        print(f"⏰ Expires: {expires_at}")
        print(f"🆔 User ID: {user_id}")
        print(f"===========================================\n")
        
        # Force log flush
        import sys
        sys.stdout.flush()
        
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to connect to database")
            return False
        
        cursor = conn.cursor()
        
        # Purane OTP delete karo
        cursor.execute("""
            DELETE FROM email_verification 
            WHERE email = %s AND purpose = 'password_reset' AND is_verified = FALSE
        """, (email,))
        deleted_count = cursor.rowcount
        logger.info(f"Deleted {deleted_count} old OTPs for {email}")
        
        # Naya OTP insert karo
        cursor.execute("""
            INSERT INTO email_verification (user_id, email, otp_code, purpose, expires_at)
            VALUES (%s, %s, %s, 'password_reset', %s)
        """, (user_id, email, otp_code, expires_at))
        
        conn.commit()
        logger.info(f"✅ Password reset OTP saved to database for {email}")
        
        # Email bhejo
        subject = f"Password Reset OTP: {otp_code}"
        
        # Simple HTML template
        html = f"""
        <html>
        <body style="font-family: Arial; padding: 20px; background: #f5f5f5;">
            <div style="max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px;">
                <h2 style="color: #0A1929;">Hello {user_name}!</h2>
                <p>Your password reset OTP is:</p>
                <div style="background: #0A1929; color: #F0B90B; font-size: 40px; font-weight: bold; padding: 20px; text-align: center; border-radius: 10px; letter-spacing: 5px; margin: 20px 0;">
                    {otp_code}
                </div>
                <p>This OTP will expire in <strong>10 minutes</strong>.</p>
                <p style="color: #666; font-size: 12px;">If you didn't request this, please ignore this email.</p>
            </div>
        </body>
        </html>
        """
        
        email_sender = EmailSender()
        result = email_sender.send_email(email, subject, html)
        
        if result:
            logger.info(f"✅ Password reset OTP email sent to {email}")
        else:
            logger.error(f"❌ Failed to send password reset OTP email to {email}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error sending password reset OTP: {e}")
        print(f"❌ ERROR in send_password_reset_otp: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def verify_otp(email: str, otp_code: str, purpose: str) -> dict:
    """
    OTP verify karo
    Returns: {'success': bool, 'user_id': int or None, 'message': str}
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return {'success': False, 'message': 'Database connection failed'}
        
        cursor = conn.cursor(dictionary=True)
        
        # OTP check karo
        cursor.execute("""
            SELECT * FROM email_verification 
            WHERE email = %s AND otp_code = %s AND purpose = %s 
            AND is_verified = FALSE AND expires_at > NOW()
            ORDER BY created_at DESC LIMIT 1
        """, (email, otp_code, purpose))
        
        record = cursor.fetchone()
        
        if not record:
            return {'success': False, 'message': 'Invalid or expired OTP'}
        
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
        
        conn.commit()
        
        return {
            'success': True, 
            'user_id': record['user_id'],
            'message': 'OTP verified successfully'
        }
        
    except Exception as e:
        logger.error(f"OTP verification error: {e}")
        if conn:
            conn.rollback()
        return {'success': False, 'message': str(e)}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def process_single_email(email_id: int) -> bool:
    """Process a single email by ID"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to connect to database")
            return False
        
        cursor = conn.cursor(dictionary=True)
        
        # Get the email
        cursor.execute("SELECT * FROM email_queue WHERE id = %s", (email_id,))
        email = cursor.fetchone()
        
        if not email:
            logger.error(f"Email {email_id} not found")
            return False
        
        logger.info(f"📨 Manually processing email {email_id} to {email['user_email']}")
        logger.info(f"📧 Template: {email['template_name']}, Subject: {email['subject']}")
        
        # Process the email
        email_sender = EmailSender()
        
        # Parse template data
        if email['template_data']:
            template_data = json.loads(email['template_data'])
            logger.info(f"📦 Template data: {template_data}")
        else:
            template_data = {}
        
        # Get template
        if email['template_name'] == 'shortlist':
            logger.info(f"🎯 Processing shortlist email for {template_data.get('student_name')}")
            html = get_shortlist_email_template(**template_data)
        elif email['template_name'] == 'drive':
            html = get_drive_announcement_template(**template_data)
        elif email['template_name'] == 'welcome':
            html = get_welcome_email_template(**template_data)
        elif email['template_name'] == 'status':
            html = get_status_update_template(**template_data)
        else:
            html = get_simple_text_email("Notification", str(template_data))
        
        # Send email
        logger.info(f"📤 Attempting to send email to {email['user_email']}")
        success = email_sender.send_email(email['user_email'], email['subject'], html)
        
        if success:
            cursor.execute("""
                UPDATE email_queue 
                SET status = 'sent', sent_at = NOW() 
                WHERE id = %s
            """, (email_id,))
            conn.commit()
            logger.info(f"✅ Manually sent email {email_id}")
            return True
        else:
            logger.error(f"❌ Failed to manually send email {email_id}")
            # Log the failure but don't update status (will retry)
            return False
            
    except Exception as e:
        logger.error(f"Error processing email {email_id}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()