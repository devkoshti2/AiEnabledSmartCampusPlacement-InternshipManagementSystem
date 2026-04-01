from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from app.auth import get_current_active_user
from app.database import get_db_connection
from app.utils.resume_parser import ResumeParser, SkillExtractor
from app.utils.ai_resume_parser import enhanced_parse_resume
import os
import shutil
from datetime import datetime
import logging
import json

router = APIRouter(prefix="/upload", tags=["Upload"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = "app/static/uploads"
PARSED_DIR = "app/static/parsed"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PARSED_DIR, exist_ok=True)

# Initialize parsers
resume_parser = ResumeParser()
skill_extractor = SkillExtractor()

@router.post("/resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user = Depends(get_current_active_user)
):
    """Resume upload kare aur automatically profile mein data fill kare"""
    
    # File type check
    if not file.filename.endswith(('.pdf', '.docx', '.doc')):
        raise HTTPException(status_code=400, detail="Only PDF/DOC files allowed")
    
    # File size check (5MB max)
    file_size = 0
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)
    
    if file_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{current_user['id']}_{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # ===== NEW: Variable to track if replacing =====
    was_replaced = False
    old_filename = None
    
    try:
        # ===== NEW CODE: DELETE OLD RESUME =====
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            
            # Get existing resume path
            cursor.execute("SELECT resume_path FROM student_profiles WHERE user_id = %s", (current_user['id'],))
            existing = cursor.fetchone()
            
            if existing and existing['resume_path']:
                old_filename = existing['resume_path']
                old_file_path = os.path.join(UPLOAD_DIR, existing['resume_path'])
                # Delete old file if it exists
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
                    was_replaced = True
                    logger.info(f"🗑️ Deleted old resume: {existing['resume_path']}")
            
            cursor.close()
            conn.close()
        # ===== END NEW CODE =====
        
        # Save new file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"📄 New file saved: {filename}")
        
        # Determine file type
        file_type = 'pdf' if file.filename.endswith('.pdf') else 'docx'
        
        # Parse resume using AI
        parsed_result = enhanced_parse_resume(file_path, file_type)
        
        if 'error' in parsed_result:
            # Fallback to basic parsing
            parsed_result = parse_basic_resume(file_path, file_type)
        
        # Save parsed data to JSON
        json_filename = f"{current_user['id']}_{timestamp}_parsed.json"
        json_path = os.path.join(PARSED_DIR, json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_result, f, indent=2, default=str)
        
        logger.info(f"💾 Parsed data saved: {json_filename}")
        
        # Extract data for profile
        basic_data = parsed_result.get('basic', {})
        skills = basic_data.get('skills', [])
        skills_str = ', '.join(skills) if skills else ''
        
        education = basic_data.get('education', {})
        branch = education.get('branch', '')
        
        # ===== FIX: Handle CGPA properly =====
        cgpa_value = education.get('cgpa', '')
        if cgpa_value and str(cgpa_value).strip():
            try:
                cgpa = float(cgpa_value)
            except:
                cgpa = None
        else:
            cgpa = None
        
        # Update database with parsed data
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = conn.cursor()
        
        # Check if student profile exists
        cursor.execute("SELECT id FROM student_profiles WHERE user_id = %s", (current_user['id'],))
        profile = cursor.fetchone()
        
        if profile:
            # Update existing profile with parsed data
            cursor.execute("""
                UPDATE student_profiles 
                SET resume_path = %s, skills = %s, branch = %s, cgpa = %s
                WHERE user_id = %s
            """, (filename, skills_str, branch, cgpa, current_user['id']))
        else:
            # Create new profile with parsed data
            cursor.execute("""
                INSERT INTO student_profiles (user_id, resume_path, skills, branch, cgpa) 
                VALUES (%s, %s, %s, %s, %s)
            """, (current_user['id'], filename, skills_str, branch, cgpa))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Prepare response with parsed data
        response_data = {
            "message": "Resume uploaded and parsed successfully",
            "filename": filename,
            "replaced": was_replaced,  # ===== NEW FLAG =====
            "old_filename": old_filename,  # ===== NEW: Old filename for info =====
            "parsed_data": {
                "name": basic_data.get('name', ''),
                "email": basic_data.get('email', ''),
                "phone": basic_data.get('phone', ''),
                "skills": skills[:10],
                "education": education,
                "branch": branch,
                "cgpa": cgpa
            }
        }
        
        return JSONResponse(response_data)
        
    except Exception as e:
        logger.error(f"❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

def parse_basic_resume(file_path: str, file_type: str) -> dict:
    """Basic resume parsing fallback"""
    
    # Extract text
    text = ""
    if file_type == 'pdf':
        text = resume_parser.extract_text_from_pdf(file_path)
    elif file_type == 'docx':
        text = resume_parser.extract_text_from_docx(file_path)
    
    if not text:
        return {"error": "Could not extract text"}
    
    # Extract information
    skills = skill_extractor.extract_skills(text)
    education = skill_extractor.extract_education(text)
    experience = skill_extractor.extract_experience(text)
    projects = skill_extractor.extract_projects(text)
    email = resume_parser.extract_email(text)
    phone = resume_parser.extract_phone(text)
    name = resume_parser.extract_name(text)
    
    return {
        'basic': {
            'name': name,
            'email': email,
            'phone': phone,
            'skills': skills,
            'education': education,
            'experience': experience,
            'projects': projects
        }
    }


@router.get("/parsed-data")
async def get_parsed_resume_data(
    current_user = Depends(get_current_active_user)
):
    """Get parsed resume data for auto-filling profile"""
    
    import glob
    
    pattern = os.path.join(PARSED_DIR, f"{current_user['id']}_*_parsed.json")
    files = glob.glob(pattern)
    
    if not files:
        return {"parsed_data": None}
    
    # Get latest file
    latest_file = max(files, key=os.path.getctime)
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    basic = data.get('basic', {})
    education = basic.get('education', {})
    
    return {
        "parsed_data": {
            "name": basic.get('name', ''),
            "email": basic.get('email', ''),
            "phone": basic.get('phone', ''),
            "skills": basic.get('skills', []),
            "branch": education.get('branch', ''),
            "cgpa": education.get('cgpa', ''),
            "degree": education.get('degree', ''),
            "year": education.get('year', ''),
            "institution": education.get('institution', '')
        }
    }