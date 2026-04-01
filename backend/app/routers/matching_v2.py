"""
Advanced Resume-Job Matching API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from app.auth import get_current_active_user, require_admin
from app.database import get_db_connection
from app.ai.resume_job_matcher import ResumeJobMatcher, create_matcher
from app.utils.resume_parser import ResumeParser
import logging
import os
import shutil
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/matching-v2", tags=["Advanced Matching"])
logger = logging.getLogger(__name__)

# Initialize matcher - WITHOUT any argument
matcher = create_matcher()  # ✅ REMOVED use_sbert=True

# Upload directory
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/match-resume-job")
async def match_resume_with_job(
    resume_file: UploadFile = File(...),
    job_description: str = Form(...),
    current_user = Depends(get_current_active_user)
):
    """
    Match uploaded resume with job description using semantic similarity
    """
    
    # Validate file
    if not resume_file.filename.endswith(('.pdf', '.docx', '.doc')):
        raise HTTPException(status_code=400, detail="Only PDF/DOC files allowed")
    
    # Save file temporarily
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"temp_{timestamp}_{resume_file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(resume_file.file, buffer)
        
        # Extract text from resume
        parser = ResumeParser()
        if resume_file.filename.endswith('.pdf'):
            resume_text = parser.extract_text_from_pdf(file_path)
        else:
            resume_text = parser.extract_text_from_docx(file_path)
        
        if not resume_text:
            raise HTTPException(status_code=400, detail="Could not extract text from resume")
        
        # Perform matching
        match_result = matcher.match_job_description(resume_text, job_description)
        
        return {
            'filename': resume_file.filename,
            'match_result': match_result
        }
        
    except Exception as e:
        logger.error(f"Matching error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/match-student/{student_id}/{drive_id}")
async def match_student_with_drive(
    student_id: int,
    drive_id: int,
    admin = Depends(require_admin)
):
    """
    Match a specific student with a drive using semantic similarity
    """
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get student profile and resume
        cursor.execute("""
            SELECT u.full_name, sp.*, u.email
            FROM student_profiles sp
            JOIN users u ON sp.user_id = u.id
            WHERE sp.user_id = %s
        """, (student_id,))
        
        student = cursor.fetchone()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Get resume text
        resume_text = ""
        if student.get('resume_path'):
            resume_path = os.path.join(UPLOAD_DIR, student['resume_path'])
            if os.path.exists(resume_path):
                parser = ResumeParser()
                if resume_path.endswith('.pdf'):
                    resume_text = parser.extract_text_from_pdf(resume_path)
                else:
                    resume_text = parser.extract_text_from_docx(resume_path)
        
        # Get drive details
        cursor.execute("""
            SELECT pd.*, c.name as company_name, c.industry
            FROM placement_drives pd
            JOIN companies c ON pd.company_id = c.id
            WHERE pd.id = %s
        """, (drive_id,))
        
        drive = cursor.fetchone()
        if not drive:
            raise HTTPException(status_code=404, detail="Drive not found")
        
        # Prepare job description
        job_description = f"""
        {drive['job_title']} at {drive['company_name']}
        
        Description: {drive['job_description']}
        
        Required Skills: {drive['required_skills']}
        
        Eligibility: CGPA >= {drive['eligibility_cgpa']}
        """
        
        # Perform matching
        if resume_text:
            match_result = matcher.match_job_description(resume_text, job_description)
        else:
            # Use profile data if no resume
            profile_text = f"""
            Student: {student['full_name']}
            Branch: {student['branch']}
            CGPA: {student['cgpa']}
            Skills: {student['skills']}
            """
            match_result = matcher.match_job_description(profile_text, job_description)
        
        return {
            'student_name': student['full_name'],
            'company': drive['company_name'],
            'job_title': drive['job_title'],
            'match_result': match_result
        }
        
    except Exception as e:
        logger.error(f"Matching error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/rank-candidates/{drive_id}")
async def rank_candidates_for_drive(
    drive_id: int,
    limit: int = 20,
    admin = Depends(require_admin)
):
    """
    Rank all candidates for a drive using semantic matching
    """
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get drive details
        cursor.execute("""
            SELECT pd.*, c.name as company_name
            FROM placement_drives pd
            JOIN companies c ON pd.company_id = c.id
            WHERE pd.id = %s
        """, (drive_id,))
        
        drive = cursor.fetchone()
        if not drive:
            raise HTTPException(status_code=404, detail="Drive not found")
        
        # Prepare job description
        job_description = f"""
        {drive['job_title']} at {drive['company_name']}
        
        Description: {drive['job_description']}
        
        Required Skills: {drive['required_skills']}
        
        Eligibility: CGPA >= {drive['eligibility_cgpa']}
        """
        
        # Get all students with profiles
        cursor.execute("""
            SELECT u.id, u.full_name, sp.*
            FROM student_profiles sp
            JOIN users u ON sp.user_id = u.id
        """)
        
        students = cursor.fetchall()
        
        # Prepare candidate list for ranking
        candidates = []
        for student in students:
            # Use profile data
            profile_text = f"""
            Student: {student['full_name']}
            Branch: {student['branch']}
            CGPA: {student['cgpa']}
            Skills: {student['skills']}
            """
            
            candidates.append({
                'id': student['id'],
                'name': student['full_name'],
                'text': profile_text
            })
        
        # Rank candidates
        ranked = matcher.rank_candidates(candidates, job_description)
        
        return {
            'drive_id': drive_id,
            'job_title': drive['job_title'],
            'company': drive['company_name'],
            'total_candidates': len(ranked),
            'ranked_candidates': ranked[:limit]
        }
        
    except Exception as e:
        logger.error(f"Ranking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/compare-two-resumes")
async def compare_two_resumes(
    resume1: UploadFile = File(...),
    resume2: UploadFile = File(...),
    current_user = Depends(get_current_active_user)
):
    """
    Compare two resumes using semantic similarity
    """
    
    files = []
    
    try:
        results = []
        
        for i, file in enumerate([resume1, resume2]):
            # Save temporarily
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"temp_{timestamp}_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            files.append(file_path)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Extract text
            parser = ResumeParser()
            if file.filename.endswith('.pdf'):
                text = parser.extract_text_from_pdf(file_path)
            else:
                text = parser.extract_text_from_docx(file_path)
            
            results.append({
                'filename': file.filename,
                'text': text
            })
        
        # Compute similarity
        similarity = matcher.semantic_similarity(results[0]['text'], results[1]['text'])
        
        # Extract skills from both
        from app.utils.resume_parser import SkillExtractor
        extractor = SkillExtractor()
        
        skills1 = extractor.extract_skills(results[0]['text'])
        skills2 = extractor.extract_skills(results[1]['text'])
        
        common_skills = set(skills1) & set(skills2)
        unique1 = set(skills1) - set(skills2)
        unique2 = set(skills2) - set(skills1)
        
        return {
            'similarity_score': round(similarity * 100, 1),
            'resume1': {
                'filename': results[0]['filename'],
                'skills': skills1[:20]
            },
            'resume2': {
                'filename': results[1]['filename'],
                'skills': skills2[:20]
            },
            'common_skills': list(common_skills)[:15],
            'unique_to_resume1': list(unique1)[:10],
            'unique_to_resume2': list(unique2)[:10]
        }
        
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp files
        for file_path in files:
            if os.path.exists(file_path):
                os.remove(file_path)


@router.get("/model-info")
async def get_matcher_info(
    admin = Depends(require_admin)
):
    """
    Get information about the matching model
    """
    
    return {
        'model_type': 'TF-IDF',
        'model_name': 'fallback',
        'cross_encoder': False,
        'section_weights': matcher.section_weights if hasattr(matcher, 'section_weights') else {},
        'skill_weights_count': len(matcher.skill_weights) if hasattr(matcher, 'skill_weights') else 0
    }