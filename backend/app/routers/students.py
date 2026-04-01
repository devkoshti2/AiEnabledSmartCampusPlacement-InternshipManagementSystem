from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_active_user
from app.database import get_db_connection
from app.models import StudentProfileCreate, StudentProfileResponse
import logging
from datetime import date
import os
import json

router = APIRouter(prefix="/student", tags=["Student"])
logger = logging.getLogger(__name__)

@router.post("/profile")
def create_profile(
    profile: StudentProfileCreate,
    current_user = Depends(get_current_active_user)
):
    """Student profile create/update kare - Resume optional hai"""
    
    if current_user['role'] != 'student':
        raise HTTPException(status_code=403, detail="Only students can create profile")
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check if profile row exists (resume check removed)
        cursor.execute("SELECT id FROM student_profiles WHERE user_id = %s", (current_user['id'],))
        existing = cursor.fetchone()
        
        if not existing:
            # Create empty profile row first
            cursor.execute(
                "INSERT INTO student_profiles (user_id) VALUES (%s)",
                (current_user['id'],)
            )
        
        # Update users table for full_name
        if profile.full_name:
            cursor.execute("""
                UPDATE users SET full_name = %s WHERE id = %s
            """, (profile.full_name, current_user['id']))
        
        # Update student_profiles table
        cursor.execute("""
            UPDATE student_profiles 
            SET roll_number = %s, branch = %s, semester = %s, cgpa = %s, skills = %s
            WHERE user_id = %s
        """, (
            profile.roll_number,
            profile.branch,
            profile.semester,
            profile.cgpa,
            profile.skills,
            current_user['id']
        ))
        
        conn.commit()
        return {"message": "Profile updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Profile creation error: {e}")
        raise HTTPException(status_code=500, detail="Profile creation failed")
    finally:
        cursor.close()
        conn.close()


@router.get("/profile", response_model=StudentProfileResponse)
def get_profile(current_user = Depends(get_current_active_user)):
    """Student profile get kare - with parsed data if available"""
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT sp.*, u.full_name FROM student_profiles sp
        JOIN users u ON sp.user_id = u.id
        WHERE sp.user_id = %s
    """, (current_user['id'],))
    
    profile = cursor.fetchone()
    
    # Check if resume exists but profile fields are empty
    if profile and profile['resume_path']:
        # Check if we have parsed data
        parsed_dir = "app/static/parsed"
        pattern = f"{current_user['id']}_*_parsed.json"
        import glob
        files = glob.glob(os.path.join(parsed_dir, pattern))
        
        if files:
            # Get latest parsed file
            latest_file = max(files, key=os.path.getctime)
            with open(latest_file, 'r', encoding='utf-8') as f:
                parsed_data = json.load(f)
            
            # Add parsed data to profile response
            profile['parsed_data'] = {
                'name': parsed_data.get('basic', {}).get('name', ''),
                'email': parsed_data.get('basic', {}).get('email', ''),
                'phone': parsed_data.get('basic', {}).get('phone', ''),
                'skills': parsed_data.get('basic', {}).get('skills', []),
                'education': parsed_data.get('basic', {}).get('education', {}),
                'experience': parsed_data.get('basic', {}).get('experience', []),
                'projects': parsed_data.get('basic', {}).get('projects', [])
            }
    
    cursor.close()
    conn.close()
    
    if not profile:
        # Return empty profile with full_name from users table
        conn2 = get_db_connection()
        full_name = None
        if conn2:
            cur2 = conn2.cursor(dictionary=True)
            cur2.execute("SELECT full_name FROM users WHERE id = %s", (current_user['id'],))
            user_row = cur2.fetchone()
            if user_row:
                full_name = user_row['full_name']
            cur2.close()
            conn2.close()
        return {
            "id": 0,
            "user_id": current_user['id'],
            "full_name": full_name,
            "roll_number": None,
            "branch": None,
            "semester": None,
            "cgpa": None,
            "skills": None,
            "resume_path": None,
            "parsed_data": None
        }
    
    return profile


@router.get("/can-edit-profile")
def can_edit_profile(current_user = Depends(get_current_active_user)):
    """Student hamesha profile edit kar sakta hai - resume optional hai"""
    return {
        "can_edit": True,
        "message": "You can edit your profile"
    }


@router.get("/drives")
def get_active_drives(current_user = Depends(get_current_active_user)):
    """Sabhi drives dikhaye - active aur expired dono, lekin expired mein apply button nahi hoga"""
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # First, auto-deactivate expired drives in database
        cursor.execute("""
            UPDATE placement_drives 
            SET status = 'closed' 
            WHERE status = 'active' AND last_date < CURDATE()
        """)
        conn.commit()
        
        # Get student profile for eligibility calculation
        cursor.execute("SELECT cgpa, skills, branch FROM student_profiles WHERE user_id = %s", (current_user['id'],))
        student = cursor.fetchone()
        
        # Get current date for expiry check
        today = date.today()
        
        cursor.execute("""
            SELECT pd.*, c.name as company_name,
            (SELECT COUNT(*) FROM applications a 
             JOIN student_profiles sp ON a.student_id = sp.id
             WHERE a.drive_id = pd.id AND sp.user_id = %s) as applied
            FROM placement_drives pd
            JOIN companies c ON pd.company_id = c.id
            WHERE pd.status IN ('active', 'closed')
            ORDER BY 
                CASE 
                    WHEN pd.last_date >= CURDATE() THEN 0
                    ELSE 1
                END,
                pd.created_at DESC
        """, (current_user['id'],))
        
        drives = cursor.fetchall()
        
        # Add eligibility and expiry info to each drive
        for drive in drives:
            drive_date = drive['last_date']
            is_expired = drive_date < today if drive_date else False
            
            drive['is_expired'] = is_expired
            
            if is_expired:
                drive['status_display'] = 'expired'
                drive['is_eligible'] = False
                drive['cgpa_eligible'] = False
                drive['skills_eligible'] = False
                drive['skill_match_percent'] = 0
                drive['matched_skills'] = []
                drive['missing_skills'] = []
                drive['required_skills_list'] = []
                drive['expired_message'] = f"⛔ This drive expired on {drive_date.strftime('%d-%m-%Y')}"
                drive['can_apply'] = False
            else:
                drive['status_display'] = 'active'
                drive['can_apply'] = True
                
                if student:
                    student_cgpa = float(student['cgpa'] or 0)
                    required_cgpa = float(drive['eligibility_cgpa'] or 0)
                    
                    student_skills = student['skills'] or ''
                    required_skills = drive['required_skills'] or ''
                    
                    student_skills_list = [s.strip().lower() for s in student_skills.split(',') if s.strip()]
                    required_skills_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
                    
                    skill_match_percent = 0
                    matched_skills = []
                    missing_skills = []
                    
                    if required_skills_list:
                        matched_skills = [s for s in required_skills_list if s in student_skills_list]
                        skill_match_percent = round((len(matched_skills) / len(required_skills_list)) * 100, 1)
                        missing_skills = [s for s in required_skills_list if s not in student_skills_list]
                    
                    cgpa_eligible = student_cgpa >= required_cgpa
                    skills_eligible = skill_match_percent >= 70
                    
                    drive['is_eligible'] = cgpa_eligible and skills_eligible
                    drive['cgpa_eligible'] = cgpa_eligible
                    drive['skills_eligible'] = skills_eligible
                    drive['skill_match_percent'] = skill_match_percent
                    drive['matched_skills'] = matched_skills
                    drive['missing_skills'] = missing_skills
                    drive['student_cgpa'] = student_cgpa
                    drive['required_cgpa'] = required_cgpa
                    drive['required_skills_list'] = required_skills_list
                else:
                    drive['is_eligible'] = False
                    drive['cgpa_eligible'] = False
                    drive['skills_eligible'] = False
                    drive['skill_match_percent'] = 0
                    drive['matched_skills'] = []
                    drive['missing_skills'] = []
                    drive['required_skills_list'] = []
        
        cursor.close()
        conn.close()
        
        return drives
        
    except Exception as e:
        cursor.close()
        conn.close()
        logger.error(f"Error in drives: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch drives")


@router.post("/apply/{drive_id}")
def apply_for_drive(drive_id: int, current_user = Depends(get_current_active_user)):
    """Drive ke liye apply kare - STRICT EXPIRY CHECK KE SAATH"""
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Pehle expired drives ko deactivate karo
        cursor.execute("""
            UPDATE placement_drives 
            SET status = 'closed' 
            WHERE status = 'active' AND last_date < CURDATE()
        """)
        conn.commit()
        
        # Get student profile
        cursor.execute("SELECT id, cgpa, skills, branch FROM student_profiles WHERE user_id = %s", (current_user['id'],))
        student = cursor.fetchone()
        
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found. Please complete your profile first.")
        
        student_id = student['id']
        student_cgpa = float(student['cgpa'] or 0)
        
        # Get drive details with expiry check
        cursor.execute("""
            SELECT pd.*, c.name as company_name,
                   CASE 
                       WHEN pd.last_date < CURDATE() THEN 'expired'
                       ELSE pd.status
                   END as current_status
            FROM placement_drives pd
            JOIN companies c ON pd.company_id = c.id
            WHERE pd.id = %s
        """, (drive_id,))
        
        drive = cursor.fetchone()
        if not drive:
            raise HTTPException(status_code=404, detail="Drive not found")
        
        today = date.today()
        if drive['last_date'] and drive['last_date'] < today:
            raise HTTPException(
                status_code=400,
                detail=f"⛔ This drive expired on {drive['last_date'].strftime('%d-%m-%Y')} and has been deactivated. You cannot apply for expired drives."
            )
        
        if drive['status'] != 'active':
            raise HTTPException(status_code=400, detail="This drive is not active for applications")
        
        required_cgpa = float(drive['eligibility_cgpa'] or 0)
        
        student_skills = []
        if student['skills']:
            student_skills = [s.strip().lower() for s in student['skills'].split(',') if s.strip()]
        
        required_skills = []
        if drive['required_skills']:
            required_skills = [s.strip().lower() for s in drive['required_skills'].split(',') if s.strip()]
        
        skill_match_percent = 0
        if required_skills:
            matched_skills = [s for s in required_skills if s in student_skills]
            skill_match_percent = (len(matched_skills) / len(required_skills)) * 100
        
        if student_cgpa < required_cgpa:
            raise HTTPException(
                status_code=400, 
                detail=f"Not eligible: Your CGPA ({student_cgpa}) is less than required ({required_cgpa})"
            )
        
        if required_skills and skill_match_percent < 70:
            raise HTTPException(
                status_code=400,
                detail=f"Not eligible: Only {skill_match_percent:.1f}% skills match. Minimum 70% required."
            )
        
        cursor.execute(
            "SELECT id FROM applications WHERE student_id = %s AND drive_id = %s",
            (student_id, drive_id)
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Already applied for this drive")
        
        cursor.execute(
            "INSERT INTO applications (student_id, drive_id) VALUES (%s, %s)",
            (student_id, drive_id)
        )

        application_id = cursor.lastrowid

        cursor.execute("SELECT id FROM users WHERE role = 'admin'")
        admins = cursor.fetchall()
        
        for admin in admins:
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, type, link)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                admin['id'],
                "New Application Received",
                f"{current_user['full_name']} applied for {drive['company_name']} - {drive['job_title']}",
                'info',
                f"/admin/drives.html?id={drive_id}"
            ))
        
        conn.commit()
        
        return {"message": "Applied successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Application error: {e}")
        raise HTTPException(status_code=500, detail="Application failed")
    finally:
        cursor.close()
        conn.close()


@router.get("/my-applications")
def get_my_applications(current_user = Depends(get_current_active_user)):
    """Student ke applications dikhaye"""
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT a.*, pd.job_title, c.name as company_name, pd.last_date,
               CASE 
                   WHEN pd.last_date < CURDATE() THEN 'expired'
                   ELSE pd.status
               END as drive_status
        FROM applications a
        JOIN placement_drives pd ON a.drive_id = pd.id
        JOIN companies c ON pd.company_id = c.id
        JOIN student_profiles sp ON a.student_id = sp.id
        WHERE sp.user_id = %s
        ORDER BY a.applied_at DESC
    """, (current_user['id'],))
    
    applications = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return applications

@router.delete("/remove-resume")
async def remove_resume(current_user = Depends(get_current_active_user)):
    """Remove student's resume from server and database"""
    
    if current_user['role'] != 'student':
        raise HTTPException(status_code=403, detail="Only students can remove resume")
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get current resume path
        cursor.execute("SELECT resume_path, skills, branch, cgpa FROM student_profiles WHERE user_id = %s", (current_user['id'],))
        profile = cursor.fetchone()
        
        if not profile or not profile['resume_path']:
            raise HTTPException(status_code=404, detail="No resume found")
        
        # Delete file from server
        file_path = os.path.join("app/static/uploads", profile['resume_path'])
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"🗑️ Deleted resume: {profile['resume_path']}")
        
        # Update database - clear resume_path and associated parsed fields
        cursor.execute("""
            UPDATE student_profiles 
            SET resume_path = NULL, skills = NULL, branch = NULL, cgpa = NULL
            WHERE user_id = %s
        """, (current_user['id'],))
        
        # Also clear parsed JSON files
        import glob
        parsed_dir = "app/static/parsed"
        pattern = os.path.join(parsed_dir, f"{current_user['id']}_*_parsed.json")
        files = glob.glob(pattern)
        for f in files:
            try:
                os.remove(f)
                logger.info(f"🗑️ Deleted parsed data: {f}")
            except:
                pass
        
        conn.commit()
        
        return {"message": "Resume removed successfully", "resume_removed": True}
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Remove resume error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove resume: {str(e)}")
    finally:
        cursor.close()
        conn.close()