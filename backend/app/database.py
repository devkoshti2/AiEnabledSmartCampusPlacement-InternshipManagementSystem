import mysql.connector
from mysql.connector import Error
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """MySQL database connection create kare"""
    try:
        connection = mysql.connector.connect(
            host=settings.DB_HOST or "localhost",
            user=settings.DB_USER or "root",
            password=settings.DB_PASSWORD or "dev02koshti0227",
            database=settings.DB_NAME or "placement_db",
            # port=settings.DB_PORT or 3306
        )
        if connection.is_connected():
            logger.info("✅ Database connected successfully")
            return connection
    except Error as e:
        logger.error(f"❌ Database connection failed: {e}")
        return None

def create_tables():
    """Saari tables create kare agar exist nahi karti"""
    connection = get_db_connection()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            role ENUM('student', 'admin') DEFAULT 'student',
            is_active BOOLEAN DEFAULT TRUE,
            email_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Students profile table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_profiles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT UNIQUE,
            roll_number VARCHAR(20) NULL,
            branch VARCHAR(50) NULL,
            semester INT NULL,
            cgpa DECIMAL(3,2) NULL,
            skills TEXT NULL,
            resume_path VARCHAR(255) NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # Companies table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT NULL,
            industry VARCHAR(100) NULL,
            website VARCHAR(255) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Placement drives table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS placement_drives (
            id INT AUTO_INCREMENT PRIMARY KEY,
            company_id INT,
            job_title VARCHAR(100),
            job_description TEXT,
            eligibility_cgpa DECIMAL(3,2),
            required_skills TEXT,
            min_experience INT DEFAULT 0,
            max_offers INT,
            last_date DATE,
            allowed_branches VARCHAR(255) NULL,
            status ENUM('active', 'closed', 'draft') DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        )
    """)
    
    # Add columns if not exist
    try:
        cursor.execute("SHOW COLUMNS FROM placement_drives LIKE 'allowed_branches'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE placement_drives ADD COLUMN allowed_branches VARCHAR(255) NULL")
            logger.info("✅ Added allowed_branches column")
        
        cursor.execute("SHOW COLUMNS FROM placement_drives LIKE 'max_backlogs'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE placement_drives ADD COLUMN max_backlogs INT DEFAULT 0")
            logger.info("✅ Added max_backlogs column")
        
        cursor.execute("SHOW COLUMNS FROM placement_drives LIKE 'min_tenth'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE placement_drives ADD COLUMN min_tenth DECIMAL(4,2) NULL")
            logger.info("✅ Added min_tenth column")
        
        cursor.execute("SHOW COLUMNS FROM placement_drives LIKE 'min_twelfth'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE placement_drives ADD COLUMN min_twelfth DECIMAL(4,2) NULL")
            logger.info("✅ Added min_twelfth column")
            
    except Exception as e:
        logger.error(f"Error adding columns: {e}")
    
    # Applications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            drive_id INT,
            status ENUM('applied', 'shortlisted', 'rejected', 'selected') DEFAULT 'applied',
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES student_profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (drive_id) REFERENCES placement_drives(id) ON DELETE CASCADE,
            UNIQUE KEY unique_application (student_id, drive_id)
        )
    """)
    
    # Skills table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INT AUTO_INCREMENT PRIMARY KEY,
            skill_name VARCHAR(50) UNIQUE NOT NULL,
            category VARCHAR(50)
        )
    """)
    
    # Password reset tokens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            token VARCHAR(100) UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_token (token)
        )
    """)
    
    # Notifications table
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
    logger.info("✅ Notifications table created/verified")
    
    # Email queue table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_queue (
            id INT AUTO_INCREMENT PRIMARY KEY,
            notification_id INT NULL,
            user_email VARCHAR(100) NOT NULL,
            subject VARCHAR(200) NOT NULL,
            template_name VARCHAR(50) NOT NULL,
            template_data TEXT,
            status ENUM('pending', 'sent', 'failed') DEFAULT 'pending',
            attempts INT DEFAULT 0,
            error_message TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP NULL,
            INDEX idx_status (status),
            INDEX idx_created (created_at),
            FOREIGN KEY (notification_id) REFERENCES notifications(id) ON DELETE SET NULL
        )
    """)
    logger.info("✅ Email queue table created/verified")
    
    # ===== FIXED: OTP Verification Table =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_verification (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            email VARCHAR(100) NOT NULL,
            otp_code VARCHAR(6) NOT NULL,
            purpose ENUM('registration', 'password_reset') NOT NULL,
            expires_at DATETIME NOT NULL,
            is_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_email_purpose (email, purpose),
            INDEX idx_otp (otp_code)
        )
    """)
    logger.info("✅ Email verification table created")

    # ==================== AI MODEL TABLES ====================

    # Model versions table - FIXED with backticks for reserved keywords

    # Alternative approach - use different column names
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_versions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            model_type VARCHAR(50) NOT NULL,
            version VARCHAR(20) NOT NULL,
            accuracy FLOAT,
            precision_score FLOAT,
            recall_score FLOAT,
            f1_score_value FLOAT,
            samples INT,
            model_path VARCHAR(255),
            is_current BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INT,
            training_time INT,
            metrics JSON,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
            INDEX idx_model_current (model_type, is_current)
        )
    """)

    # Training logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS training_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            model_type VARCHAR(50) NOT NULL,
            status ENUM('started', 'completed', 'failed') DEFAULT 'started',
            message TEXT,
            accuracy FLOAT,
            samples INT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            created_by INT,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
            INDEX idx_model_status (model_type, status)
        )
    """)

    # Model feedback table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_feedback (
            id INT AUTO_INCREMENT PRIMARY KEY,
            drive_id INT,
            student_id INT,
            predicted_probability FLOAT,
            actual_outcome BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (drive_id) REFERENCES placement_drives(id) ON DELETE CASCADE,
            INDEX idx_feedback (drive_id, student_id)
        )
    """)
    
    # Add email_verified column to users table if not exists
    try:
        cursor.execute("SHOW COLUMNS FROM users LIKE 'email_verified'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE")
            logger.info("✅ Added email_verified column to users")
    except Exception as e:
        logger.error(f"Error adding email_verified column: {e}")
    
    # Add email columns to notifications table
    try:
        cursor.execute("SHOW COLUMNS FROM notifications LIKE 'email_sent'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE notifications ADD COLUMN email_sent BOOLEAN DEFAULT FALSE")
            logger.info("✅ Added email_sent column to notifications")
        
        cursor.execute("SHOW COLUMNS FROM notifications LIKE 'email_sent_at'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE notifications ADD COLUMN email_sent_at TIMESTAMP NULL")
            logger.info("✅ Added email_sent_at column to notifications")
    except Exception as e:
        logger.error(f"Error adding columns to notifications: {e}")

    # Check if tables exist
    cursor.execute("SHOW TABLES LIKE 'training_logs'")
    if cursor.fetchone():
        print("✅ training_logs table exists")
    else:
        print("❌ training_logs table missing")

    cursor.execute("SHOW TABLES LIKE 'model_versions'")
    if cursor.fetchone():
        print("✅ model_versions table exists")
    else:
        print("❌ model_versions table missing")
    
    # Check current table structure
    cursor.execute("DESCRIBE model_versions")
    columns = cursor.fetchall()
    print("Current columns:", [col[0] for col in columns])
    
    connection.commit()
    cursor.close()
    connection.close()
    logger.info("✅ All tables created/verified")

if __name__ == "__main__":
    create_tables()