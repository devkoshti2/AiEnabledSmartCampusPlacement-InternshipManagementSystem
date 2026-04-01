import random
from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_active_user, require_admin
from app.database import get_db_connection
from app.ai.models import EligibilityPredictor, SelectionProbabilityPredictor
from app.utils.resume_parser import SkillExtractor
import logging

router = APIRouter(prefix="/ai", tags=["AI Predictions"])
logger = logging.getLogger(__name__)

# Initialize models
eligibility_predictor = EligibilityPredictor()
selection_predictor = SelectionProbabilityPredictor()
skill_extractor = SkillExtractor()

@router.post("/train-models")
async def train_ai_models(admin = Depends(require_admin)):
    """AI models train kare (Admin only)"""
    
    try:
        # Train eligibility model
        logger.info("Training eligibility model...")
        eligibility_result = eligibility_predictor.train_model()
        
        # Train selection model
        logger.info("Training selection model...")
        selection_predictor.train_model()
        
        return {
            "message": "Models trained successfully",
            "eligibility_model": eligibility_result
        }
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@router.get("/predict-eligibility/{drive_id}")
async def predict_eligibility(
    drive_id: int,
    current_user = Depends(get_current_active_user)
):
    """Student ke liye eligibility predict kare - SYNCED with students.py logic"""
    
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
        
        # Get student data
        student_cgpa = float(student.get('cgpa', 0))
        required_cgpa = float(drive.get('eligibility_cgpa', 0))
        
        # Parse skills
        student_skills = student.get('skills', '')
        required_skills = drive.get('required_skills', '')
        
        if isinstance(student_skills, str):
            student_skills_list = [s.strip().lower() for s in student_skills.split(',') if s.strip()]
        else:
            student_skills_list = student_skills or []
        
        if isinstance(required_skills, str):
            required_skills_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
        else:
            required_skills_list = required_skills or []
        
        # EXACT MATCHING - same as students.py
        matched_skills = []
        missing_skills = []
        
        for req_skill in required_skills_list:
            if req_skill in student_skills_list:  # Exact match only
                matched_skills.append(req_skill)
            else:
                missing_skills.append(req_skill)
        
        # Calculate match percentage
        total_required = len(required_skills_list)
        matched_count = len(matched_skills)
        match_percentage = round((matched_count / total_required * 100), 1) if total_required > 0 else 100
        
        # STRICT ELIGIBILITY - same as students.py
        cgpa_eligible = student_cgpa >= required_cgpa
        skills_eligible = match_percentage >= 70
        is_eligible = cgpa_eligible and skills_eligible
        
        # Make prediction (use rule-based for consistency)
        prediction = {
            'eligible': is_eligible,
            'probability': match_percentage / 100 if total_required > 0 else 0.8,
            'confidence': 0.9,
            'method': 'rule',
            'details': {
                'cgpa_match': cgpa_eligible,
                'skill_match_percent': match_percentage,
                'matched_skills': matched_skills,
                'missing_skills': missing_skills
            }
        }
        
        # Course recommendations
        recommendations = []
        for skill in missing_skills[:3]:
            recommendations.append({
                "skill": skill,
                "course": f"Learn {skill.title()}",
                "platform": random.choice(["Coursera", "Udemy", "YouTube"]),
                "url": f"https://www.google.com/search?q=learn+{skill}"
            })
        
        # Check if already applied
        cursor.execute("""
            SELECT a.id FROM applications a
            JOIN student_profiles sp ON a.student_id = sp.id
            WHERE sp.user_id = %s AND a.drive_id = %s
        """, (current_user['id'], drive_id))
        
        already_applied = cursor.fetchone() is not None
        
        # IMPORTANT: Return with "matched" field (not "matched_count")
        return {
            "student_name": current_user['full_name'],
            "company": drive['company_name'],
            "job_title": drive['job_title'],
            "already_applied": already_applied,
            "prediction": prediction,
            "skill_analysis": {
                "total_required": total_required,
                "matched": matched_count,  # ✅ YEH "matched" hona chahiye
                "match_percentage": match_percentage,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "recommendations": recommendations
            }
        }
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")
    finally:
        cursor.close()
        conn.close()

@router.get("/recommend-candidates/{drive_id}")
async def recommend_candidates(
    drive_id: int,
    limit: int = 10,
    admin = Depends(require_admin)
):
    """AI-based candidate recommendation"""
    
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
        
        # Get all students
        cursor.execute("""
            SELECT u.id as user_id, u.full_name, sp.* 
            FROM student_profiles sp
            JOIN users u ON sp.user_id = u.id
        """)
        
        students = cursor.fetchall()
        
        # Get predictions for each student
        recommendations = []
        
        for student in students:
            prediction = eligibility_predictor.predict(student, drive)
            
            # Calculate overall score
            cgpa = float(student.get('cgpa', 0))
            cgpa_score = min(cgpa / 10, 1.0) * 30  # 30% weight
            
            skill_match = prediction.get('details', {}).get('skill_match_percent', 0) * 0.4  # 40% weight
            prob_score = prediction.get('probability', 0) * 30  # 30% weight
            
            total_score = cgpa_score + skill_match + prob_score
            
            recommendations.append({
                "user_id": student['user_id'],
                "name": student['full_name'],
                "cgpa": cgpa,
                "skills": student.get('skills', ''),
                "eligibility_prediction": prediction,
                "overall_score": round(total_score, 2)
            })
        
        # Sort by score
        recommendations.sort(key=lambda x: x['overall_score'], reverse=True)
        
        return {
            "drive_id": drive_id,
            "job_title": drive['job_title'],
            "total_evaluated": len(recommendations),
            "top_candidates": recommendations[:limit]
        }
        
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(status_code=500, detail="Recommendation failed")
    finally:
        cursor.close()
        conn.close()

@router.get("/placement-trends")
async def get_placement_trends(admin = Depends(require_admin)):
    """AI-based placement trend analysis"""
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get all drives
        cursor.execute("""
            SELECT pd.*, c.name as company_name 
            FROM placement_drives pd
            JOIN companies c ON pd.company_id = c.id
        """)
        
        drives = cursor.fetchall()
        
        # Get all applications with status
        cursor.execute("""
            SELECT a.*, pd.job_title, pd.required_skills, sp.branch, sp.cgpa
            FROM applications a
            JOIN placement_drives pd ON a.drive_id = pd.id
            JOIN student_profiles sp ON a.student_id = sp.id
        """)
        
        applications = cursor.fetchall()
        
        # Analyze trends
        branch_stats = {}
        skill_demand = {}
        company_stats = {}
        
        for app in applications:
            # Branch-wise stats
            branch = app.get('branch', 'Unknown')
            if branch not in branch_stats:
                branch_stats[branch] = {'total': 0, 'selected': 0}
            
            branch_stats[branch]['total'] += 1
            if app['status'] in ['selected', 'shortlisted']:
                branch_stats[branch]['selected'] += 1
            
            # Skill demand
            skills = app.get('required_skills', '')
            if skills:
                for skill in skills.split(','):
                    skill = skill.strip().lower()
                    if skill:
                        skill_demand[skill] = skill_demand.get(skill, 0) + 1
        
        for drive in drives:
            company = drive.get('company_name', 'Unknown')
            if company not in company_stats:
                company_stats[company] = {'total_drives': 0, 'total_offers': 0}
            
            company_stats[company]['total_drives'] += 1
            company_stats[company]['total_offers'] += drive.get('max_offers', 0)
        
        # Sort skill demand
        top_skills = sorted(skill_demand.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Calculate placement percentages
        branch_percentages = {}
        for branch, stats in branch_stats.items():
            if stats['total'] > 0:
                percentage = (stats['selected'] / stats['total']) * 100
                branch_percentages[branch] = round(percentage, 2)
        
        return {
            "total_drives": len(drives),
            "total_applications": len(applications),
            "branch_wise_placement": branch_percentages,
            "top_demand_skills": [{"skill": s, "count": c} for s, c in top_skills],
            "company_hiring_stats": company_stats,
            "trends": {
                "most_active_companies": sorted(company_stats.items(), key=lambda x: x[1]['total_drives'], reverse=True)[:5],
                "highest_hiring_companies": sorted(company_stats.items(), key=lambda x: x[1]['total_offers'], reverse=True)[:5],
                "top_branches": sorted(branch_percentages.items(), key=lambda x: x[1], reverse=True)[:3]
            }
        }
        
    except Exception as e:
        logger.error(f"Trend analysis error: {e}")
        raise HTTPException(status_code=500, detail="Trend analysis failed")
    finally:
        cursor.close()
        conn.close()

@router.post("/batch-predict/{drive_id}")
async def batch_predict(
    drive_id: int,
    admin = Depends(require_admin)
):
    """Predict eligibility for all students for a drive"""
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
        
        # Get all students
        cursor.execute("""
            SELECT u.id as user_id, u.full_name, sp.* 
            FROM student_profiles sp
            JOIN users u ON sp.user_id = u.id
        """)
        
        students = cursor.fetchall()
        
        results = []
        for student in students:
            prediction = eligibility_predictor.predict(student, drive)
            results.append({
                "student_id": student['user_id'],
                "name": student['full_name'],
                "eligible": prediction['eligible'],
                "probability": prediction['probability'],
                "confidence": prediction['confidence'],
                "method": prediction['method']
            })
        
        # Sort by probability
        results.sort(key=lambda x: x['probability'], reverse=True)
        
        return {
            "drive_id": drive_id,
            "job_title": drive['job_title'],
            "total_students": len(results),
            "eligible_count": sum(1 for r in results if r['eligible']),
            "predictions": results[:50]  # Top 50
        }
        
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail="Batch prediction failed")
    finally:
        cursor.close()
        conn.close()

@router.get("/model-status")
async def get_model_status(admin = Depends(require_admin)):
    """Check if AI models are trained"""
    import os
    
    eligibility_exists = os.path.exists("app/ai/models/eligibility_model.pkl")
    selection_exists = os.path.exists("app/ai/models/selection_model.pkl")
    
    return {
        "eligibility": eligibility_exists,
        "selection": selection_exists
    }