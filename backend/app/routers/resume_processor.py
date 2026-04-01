from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from app.auth import get_current_active_user
from app.database import get_db_connection
from app.utils.resume_parser import ResumeParser, SkillExtractor
from app.utils.ai_resume_parser import enhanced_parse_resume, TrainingDataCollector
import os
import shutil
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

router = APIRouter(prefix="/resume", tags=["Resume Processing"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = "app/static/uploads"
PARSED_DIR = "app/static/parsed"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PARSED_DIR, exist_ok=True)

# Initialize parsers
resume_parser = ResumeParser()
skill_extractor = SkillExtractor()
training_collector = TrainingDataCollector()

@router.post("/upload-and-parse")
async def upload_and_parse_resume(
    file: UploadFile = File(...),
    use_ai: bool = Query(True, description="Use AI for enhanced parsing"),
    current_user = Depends(get_current_active_user)
):
    """
    Resume upload kare aur automatically parse kare
    use_ai=true for AI-enhanced parsing (recommended)
    use_ai=false for basic parsing (faster but less accurate)
    """
    
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
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"📄 File saved: {filename}")
        
        # Determine file type
        file_type = 'pdf' if file.filename.endswith('.pdf') else 'docx'
        
        # Parse resume
        if use_ai:
            logger.info("🤖 Using AI-enhanced resume parsing...")
            parsed_result = enhanced_parse_resume(file_path, file_type)
            
            if 'error' in parsed_result:
                logger.warning(f"⚠️ AI parsing failed: {parsed_result['error']}")
                # Fallback to basic
                parsed_result = parse_basic_resume(file_path, file_type)
                parsed_result['ai_used'] = False
            else:
                parsed_result['ai_used'] = True
        else:
            logger.info("📝 Using basic resume parsing...")
            parsed_result = parse_basic_resume(file_path, file_type)
            parsed_result['ai_used'] = False
        
        # Save parsed data to JSON
        json_filename = f"{current_user['id']}_{timestamp}_parsed.json"
        json_path = os.path.join(PARSED_DIR, json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_result, f, indent=2, default=str)
        
        logger.info(f"💾 Parsed data saved: {json_filename}")
        
        # Save for training data (only if AI was used and confidence is good)
        if use_ai and parsed_result.get('confidence_report', {}).get('overall_confidence', 0) > 0.7:
            training_collector.save_parsed_resume(
                current_user['id'],
                parsed_result
            )
        
        # Update database
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = conn.cursor()
        
        # Extract skills for database update
        skills_to_save = []
        if use_ai and parsed_result.get('enhanced', {}).get('skills_with_confidence'):
            # Use AI skills with high confidence
            skills_with_conf = parsed_result['enhanced']['skills_with_confidence']
            skills_to_save = [s['skill'] for s in skills_with_conf if s['confidence'] > 0.7]
        else:
            # Use basic skills
            skills_to_save = parsed_result['basic']['skills']
        
        skills_str = ', '.join(skills_to_save) if skills_to_save else ''
        
        # Get name from parsed result
        student_name = parsed_result['basic'].get('name', '')
        
        # Update or create student profile
        cursor.execute("SELECT id FROM student_profiles WHERE user_id = %s", (current_user['id'],))
        profile = cursor.fetchone()
        
        if profile:
            # Update existing profile
            cursor.execute("""
                UPDATE student_profiles 
                SET resume_path = %s, skills = %s
                WHERE user_id = %s
            """, (filename, skills_str, current_user['id']))
        else:
            # Create new profile
            cursor.execute("""
                INSERT INTO student_profiles (user_id, resume_path, skills) 
                VALUES (%s, %s, %s)
            """, (current_user['id'], filename, skills_str))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Prepare response
        response_data = {
            "message": "Resume uploaded and parsed successfully",
            "filename": filename,
            "ai_used": use_ai,
            "parsed_data": {
                "name": student_name,
                "email": parsed_result['basic'].get('email', ''),
                "phone": parsed_result['basic'].get('phone', ''),
                "skills_count": len(skills_to_save),
                "skills": skills_to_save[:10],  # First 10 skills
                "education": parsed_result['basic'].get('education', {})
            }
        }
        
        # Add confidence report if available
        if 'confidence_report' in parsed_result:
            response_data['confidence'] = parsed_result['confidence_report']
        
        return JSONResponse(response_data)
        
    except Exception as e:
        logger.error(f"❌ Resume processing error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Resume processing failed: {str(e)}")

def parse_basic_resume(file_path: str, file_type: str) -> Dict:
    """Basic resume parsing (existing logic)"""
    
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
    include_raw: bool = Query(False, description="Include raw parsed data"),
    current_user = Depends(get_current_active_user)
):
    """
    Parsed resume data return kare
    include_raw=true for complete AI-enhanced data
    """
    
    import glob
    
    pattern = os.path.join(PARSED_DIR, f"{current_user['id']}_*_parsed.json")
    files = glob.glob(pattern)
    
    if not files:
        return {"message": "No parsed resume found"}
    
    # Get latest file
    latest_file = max(files, key=os.path.getctime)
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not include_raw:
        # Return simplified version
        simplified = {
            'name': data.get('basic', {}).get('name', ''),
            'email': data.get('basic', {}).get('email', ''),
            'phone': data.get('basic', {}).get('phone', ''),
            'skills': data.get('basic', {}).get('skills', []),
            'education': data.get('basic', {}).get('education', {}),
            'ai_used': data.get('ai_used', False)
        }
        
        if 'confidence_report' in data:
            simplified['confidence'] = data['confidence_report']
        
        return simplified
    
    return data

@router.post("/feedback")
async def submit_parsing_feedback(
    corrections: Dict,
    current_user = Depends(get_current_active_user)
):
    """
    Submit corrections for parsed data (helps improve AI model)
    """
    
    import glob
    
    pattern = os.path.join(PARSED_DIR, f"{current_user['id']}_*_parsed.json")
    files = glob.glob(pattern)
    
    if not files:
        raise HTTPException(status_code=404, detail="No parsed resume found")
    
    latest_file = max(files, key=os.path.getctime)
    parse_id = os.path.basename(latest_file).replace('_parsed.json', '')
    
    # Save feedback
    training_collector.save_feedback(
        parse_id,
        corrections,
        current_user['id']
    )
    
    return {"message": "Feedback submitted successfully. Thank you for helping improve the AI!"}

@router.get("/confidence")
async def get_parsing_confidence(
    current_user = Depends(get_current_active_user)
):
    """
    Get confidence score for last parsed resume
    """
    
    import glob
    
    pattern = os.path.join(PARSED_DIR, f"{current_user['id']}_*_parsed.json")
    files = glob.glob(pattern)
    
    if not files:
        return {"message": "No parsed resume found"}
    
    latest_file = max(files, key=os.path.getctime)
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'confidence_report' in data:
        return data['confidence_report']
    
    return {
        "overall_confidence": 0.7,
        "message": "Basic parsing used. Use AI for better confidence scores."
    }