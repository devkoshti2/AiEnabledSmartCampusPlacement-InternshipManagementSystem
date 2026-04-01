from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_active_user
from app.database import get_db_connection
from app.utils.resume_parser import SkillExtractor
import logging
from typing import Dict, List

router = APIRouter(prefix="/matching", tags=["Matching"])
logger = logging.getLogger(__name__)

skill_extractor = SkillExtractor()

def calculate_skill_match(student_skills: str, required_skills: str) -> Dict:
    """Skills ka match percentage calculate kare"""
    
    # Convert strings to lists
    if isinstance(student_skills, str):
        student_skills_list = [s.strip().lower() for s in student_skills.split(',') if s.strip()]
    else:
        student_skills_list = student_skills or []
    
    if isinstance(required_skills, str):
        required_skills_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
    else:
        required_skills_list = required_skills or []
    
    if not required_skills_list:
        return {
            "match_percentage": 100,
            "matched_skills": student_skills_list,
            "missing_skills": [],
            "total_required": 0,
            "total_matched": len(student_skills_list)
        }
    
    # Find matching skills
    matched = []
    missing = []
    
    for req_skill in required_skills_list:
        found = False
        for stu_skill in student_skills_list:
            # Partial matching bhi karo (e.g., "python" matches "python programming")
            if req_skill in stu_skill or stu_skill in req_skill:
                matched.append(req_skill)
                found = True
                break
        if not found:
            missing.append(req_skill)
    
    # Remove duplicates
    matched = list(set(matched))
    missing = list(set(missing))
    
    # Calculate percentage
    total_required = len(required_skills_list)
    total_matched = len(matched)
    
    if total_required > 0:
        match_percentage = (total_matched / total_required) * 100
    else:
        match_percentage = 100
    
    return {
        "match_percentage": round(match_percentage, 2),
        "matched_skills": matched,
        "missing_skills": missing,
        "total_required": total_required,
        "total_matched": total_matched
    }

def check_eligibility(student_data: Dict, job_data: Dict) -> Dict:
    """Eligibility check kare based on CGPA and other criteria"""
    
    result = {
        "eligible": False,
        "reasons": [],
        "cgpa_status": False,
        "skill_status": False
    }
    
    # CGPA check
    student_cgpa = float(student_data.get('cgpa', 0))
    required_cgpa = float(job_data.get('eligibility_cgpa', 0))
    
    if student_cgpa >= required_cgpa:
        result['cgpa_status'] = True
    else:
        result['reasons'].append(f"CGPA {student_cgpa} is less than required {required_cgpa}")
    
    # Skills check (minimum 60% skills match)
    student_skills = student_data.get('skills', '')
    required_skills = job_data.get('required_skills', '')
    
    skill_match = calculate_skill_match(student_skills, required_skills)
    
    if skill_match['match_percentage'] >= 60:
        result['skill_status'] = True
    else:
        result['reasons'].append(f"Skills match only {skill_match['match_percentage']}% (minimum 60% required)")
    
    # Final eligibility
    if result['cgpa_status'] and result['skill_status']:
        result['eligible'] = True
    
    result['skill_match'] = skill_match
    
    return result

def check_enhanced_eligibility(student_data: Dict, job_data: Dict) -> Dict:
    """Enhanced eligibility check with more criteria"""
    
    result = {
        "eligible": False,
        "reasons": [],
        "criteria": {}
    }
    
    # CGPA check
    student_cgpa = float(student_data.get('cgpa', 0))
    required_cgpa = float(job_data.get('eligibility_cgpa', 0))
    
    if student_cgpa >= required_cgpa:
        result['criteria']['cgpa'] = True
    else:
        result['reasons'].append(f"CGPA {student_cgpa} < {required_cgpa}")
        result['criteria']['cgpa'] = False
    
    # Branch check
    allowed_branches = job_data.get('allowed_branches', '')
    if allowed_branches:
        student_branch = student_data.get('branch', '')
        if student_branch in allowed_branches.split(','):
            result['criteria']['branch'] = True
        else:
            result['reasons'].append(f"Branch {student_branch} not allowed")
            result['criteria']['branch'] = False
    else:
        result['criteria']['branch'] = True
    
    # Skills check
    student_skills = student_data.get('skills', '')
    required_skills = job_data.get('required_skills', '')
    
    skill_match = calculate_skill_match(student_skills, required_skills)
    result['criteria']['skills'] = skill_match['match_percentage'] >= 60
    
    if not result['criteria']['skills']:
        result['reasons'].append(f"Skills match only {skill_match['match_percentage']}%")
    
    # Backlogs check (if we have this data)
    student_backlogs = int(student_data.get('backlogs', 0))
    max_backlogs = int(job_data.get('max_backlogs', 99))
    
    if student_backlogs <= max_backlogs:
        result['criteria']['backlogs'] = True
    else:
        result['reasons'].append(f"Has {student_backlogs} backlogs (max {max_backlogs})")
        result['criteria']['backlogs'] = False
    
    # Final eligibility - all criteria must be True
    result['eligible'] = all(result['criteria'].values())
    result['skill_match'] = skill_match
    
    return result

@router.get("/match-student/{drive_id}")
async def match_student_for_drive(
    drive_id: int,
    current_user = Depends(get_current_active_user)
):
    """Student ko specific drive ke liye match kare"""
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get student profile
        cursor.execute("""
            SELECT sp.* FROM student_profiles sp
            WHERE sp.user_id = %s
        """, (current_user['id'],))
        
        student = cursor.fetchone()
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found")
        
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
        
        # Calculate match
        eligibility = check_eligibility(student, drive)
        
        # Check if already applied
        cursor.execute("""
            SELECT id FROM applications 
            WHERE student_id = %s AND drive_id = %s
        """, (student['id'], drive_id))
        
        already_applied = cursor.fetchone() is not None
        
        return {
            "student_name": current_user['full_name'],
            "company": drive['company_name'],
            "job_title": drive['job_title'],
            "eligibility": eligibility,
            "already_applied": already_applied,
            "recommendation": "Strong Match" if eligibility['eligible'] else "Needs Improvement"
        }
        
    except Exception as e:
        logger.error(f"Matching error: {e}")
        raise HTTPException(status_code=500, detail="Matching failed")
    finally:
        cursor.close()
        conn.close()

@router.get("/rank-candidates/{drive_id}")
async def rank_candidates_for_drive(
    drive_id: int,
    admin = Depends(get_current_active_user)
):
    """Drive ke liye candidates ko rank kare (Admin only)"""
    
    if admin['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get drive details
        cursor.execute("SELECT * FROM placement_drives WHERE id = %s", (drive_id,))
        drive = cursor.fetchone()
        if not drive:
            raise HTTPException(status_code=404, detail="Drive not found")
        
        # Get all students who have profiles
        cursor.execute("""
            SELECT u.id as user_id, u.full_name, sp.* 
            FROM student_profiles sp
            JOIN users u ON sp.user_id = u.id
        """)
        
        students = cursor.fetchall()
        
        # Calculate match score for each student
        ranked_candidates = []
        
        for student in students:
            eligibility = check_eligibility(student, drive)
            
            # Calculate overall score (weighted)
            cgpa_score = min(float(student.get('cgpa', 0)) / 10 * 40, 40)  # 40% weight
            skill_score = eligibility['skill_match']['match_percentage'] * 0.6  # 60% weight
            
            total_score = cgpa_score + skill_score
            
            ranked_candidates.append({
                "user_id": student['user_id'],
                "name": student['full_name'],
                "cgpa": student.get('cgpa'),
                "skills": student.get('skills'),
                "match_percentage": round(eligibility['skill_match']['match_percentage'], 2),
                "eligible": eligibility['eligible'],
                "overall_score": round(total_score, 2),
                "missing_skills": eligibility['skill_match']['missing_skills']
            })
        
        # Sort by overall score (highest first)
        ranked_candidates.sort(key=lambda x: x['overall_score'], reverse=True)
        
        return {
            "drive_id": drive_id,
            "job_title": drive['job_title'],
            "total_candidates": len(ranked_candidates),
            "eligible_candidates": sum(1 for c in ranked_candidates if c['eligible']),
            "ranked_candidates": ranked_candidates[:20]  # Top 20
        }
        
    except Exception as e:
        logger.error(f"Ranking error: {e}")
        raise HTTPException(status_code=500, detail="Ranking failed")
    finally:
        cursor.close()
        conn.close()