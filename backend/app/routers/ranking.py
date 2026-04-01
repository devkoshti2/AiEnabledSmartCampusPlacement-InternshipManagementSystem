"""
Advanced Candidate Ranking API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from app.auth import get_current_active_user, require_admin
from app.database import get_db_connection
from app.ai.candidate_ranker import get_candidate_ranker
from app.utils.resume_parser import SkillExtractor
import logging
from typing import List, Dict, Optional
from datetime import datetime

router = APIRouter(prefix="/ranking", tags=["Candidate Ranking"])
logger = logging.getLogger(__name__)

# Get ranker instance
ranker = get_candidate_ranker()


@router.post("/train")
async def train_ranking_models(
    n_samples: int = Query(2000, description="Number of training samples"),
    admin = Depends(require_admin)
):
    """Train ranking models"""
    try:
        results = ranker.train_ranking_models(n_samples=n_samples)
        return {
            'message': 'Ranking models trained successfully',
            'results': results
        }
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def rank_candidates_rule_based(candidates: List[Dict], drive: Dict, top_k: Optional[int] = None) -> List[Dict]:
    """Simple rule-based ranking as fallback"""
    ranked = []
    required_cgpa = float(drive.get('eligibility_cgpa', 0))
    required_skills_str = drive.get('required_skills', '')
    required_skills_list = [s.strip().lower() for s in required_skills_str.split(',') if s.strip()]
    
    for candidate in candidates:
        cgpa = float(candidate.get('cgpa', 0) or 0)
        skills_str = candidate.get('skills', '') or ''
        skills_list = [s.strip().lower() for s in skills_str.split(',') if s.strip()]
        
        # Calculate simple score
        if required_cgpa > 0:
            cgpa_score = min(cgpa / required_cgpa, 1.5) / 1.5
        else:
            cgpa_score = cgpa / 10.0
        
        if required_skills_list:
            matched_skills = set(skills_list) & set(required_skills_list)
            skill_score = len(matched_skills) / len(required_skills_list) if required_skills_list else 0
        else:
            skill_score = 0.8
        
        total_score = (cgpa_score * 0.5) + (skill_score * 0.5)
        
        ranked.append({
            'candidate_id': candidate.get('user_id'),
            'name': candidate.get('full_name', 'Unknown'),
            'rank_score': total_score,
            'component_scores': {
                'cgpa_score': cgpa_score,
                'skill_score': skill_score,
                'experience_score': 0,
                'project_score': 0
            },
            'eligibility': {
                'eligible': cgpa >= required_cgpa,
                'cgpa_met': cgpa >= required_cgpa
            }
        })
    
    ranked.sort(key=lambda x: x['rank_score'], reverse=True)
    for idx, candidate in enumerate(ranked):
        candidate['rank'] = idx + 1
    
    if top_k:
        ranked = ranked[:top_k]
    return ranked

@router.get("/rank-candidates/{drive_id}")
async def rank_candidates_advanced(
    drive_id: int,
    method: str = Query('ensemble', description="Ranking method"),
    include_ineligible: bool = Query(False, description="Include ineligible candidates"),
    top_k: Optional[int] = Query(None, description="Number of top candidates"),
    only_applied: bool = Query(True, description="Show only students who have applied"),
    admin = Depends(require_admin)
):
    """Rank candidates for a drive"""
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
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
        
        required_cgpa = float(drive.get('eligibility_cgpa', 0) or 0)
        required_skills_str = drive.get('required_skills', '') or ''
        required_skills_list = [s.strip().lower() for s in required_skills_str.split(',') if s.strip()]
        
        # ===== FIXED 1: Applied Only Query =====
        if only_applied:
            # SIRF APPLIED STUDENTS - with CORRECT status
            cursor.execute("""
                SELECT 
                    u.id as user_id,
                    u.full_name,
                    u.email,
                    sp.id as profile_id,
                    sp.roll_number,
                    sp.branch,
                    sp.semester,
                    sp.cgpa,
                    sp.skills,
                    sp.resume_path,
                    a.status as application_status,  -- ✅ YAHI SE STATUS AAYEGA
                    a.applied_at,
                    a.id as application_id
                FROM applications a
                JOIN student_profiles sp ON a.student_id = sp.id
                JOIN users u ON sp.user_id = u.id
                WHERE a.drive_id = %s
                ORDER BY a.applied_at DESC
            """, (drive_id,))
            
            students = cursor.fetchall()
            logger.info(f"Applied Only: Found {len(students)} students")
            
        else:
            # ===== FIXED 2: All Eligible Students =====
            cursor.execute("""
                SELECT 
                    u.id as user_id,
                    u.full_name,
                    u.email,
                    sp.id as profile_id,
                    sp.roll_number,
                    sp.branch,
                    sp.semester,
                    sp.cgpa,
                    sp.skills,
                    sp.resume_path,
                    CASE 
                        WHEN a.id IS NOT NULL THEN a.status
                        ELSE 'not_applied'
                    END as application_status,
                    a.applied_at,
                    a.id as application_id
                FROM student_profiles sp
                JOIN users u ON sp.user_id = u.id
                LEFT JOIN applications a ON a.student_id = sp.id AND a.drive_id = %s
                WHERE u.role = 'student'
                ORDER BY sp.cgpa DESC
            """, (drive_id,))
            
            all_students = cursor.fetchall()
            logger.info(f"All Eligible: Found {len(all_students)} total students")
            
            # ===== FIXED: Filter by FULL eligibility (CGPA + 70% skills) =====
            students = []
            for student in all_students:
                # Parse skills
                skills_str = student.get('skills', '') or ''
                skills_list = [s.strip().lower() for s in skills_str.split(',') if s.strip()]
                
                # Calculate skill match
                if required_skills_list:
                    matched_skills = [s for s in required_skills_list if s in skills_list]
                    skill_match_percent = (len(matched_skills) / len(required_skills_list)) * 100
                else:
                    skill_match_percent = 100
                    matched_skills = []
                
                # Check eligibility
                cgpa = float(student.get('cgpa', 0) or 0)
                cgpa_eligible = cgpa >= required_cgpa
                skills_eligible = skill_match_percent >= 70 if required_skills_list else True
                
                student['skill_match_percent'] = skill_match_percent
                student['cgpa_eligible'] = cgpa_eligible
                student['skills_eligible'] = skills_eligible
                
                if cgpa_eligible and skills_eligible:
                    students.append(student)
            
            logger.info(f"After eligibility filter: {len(students)} eligible students")
        
        # Enhance student data for ranking
        enhanced_students = []
        for student in students:
            skills_str = student.get('skills', '') or ''
            skills_list = [s.strip().lower() for s in skills_str.split(',') if s.strip()]
            
            enhanced_student = dict(student)
            enhanced_student['num_skills'] = len(skills_list)
            enhanced_student['experience_months'] = 0
            enhanced_student['num_projects'] = 0
            enhanced_student['has_resume'] = 1 if student.get('resume_path') else 0
            
            enhanced_students.append(enhanced_student)
        
        # Filter by eligibility (if include_ineligible is False)
        if not include_ineligible and not only_applied:
            # Already filtered above for All Eligible
            candidates_to_rank = enhanced_students
        elif not include_ineligible and only_applied:
            # For Applied Only, filter by eligibility
            filtered = []
            for student in enhanced_students:
                cgpa = float(student.get('cgpa', 0) or 0)
                skills_str = student.get('skills', '') or ''
                skills_list = [s.strip().lower() for s in skills_str.split(',') if s.strip()]
                
                if required_skills_list:
                    matched = [s for s in required_skills_list if s in skills_list]
                    skill_match = (len(matched) / len(required_skills_list)) * 100
                else:
                    skill_match = 100
                
                if cgpa >= required_cgpa and skill_match >= 70:
                    filtered.append(student)
            
            candidates_to_rank = filtered
            logger.info(f"Applied Only after eligibility: {len(candidates_to_rank)} students")
        else:
            # Include ineligible = True
            candidates_to_rank = enhanced_students
        
        # Rank candidates
        ranked = []
        for candidate in candidates_to_rank:
            cgpa = float(candidate.get('cgpa', 0) or 0)
            skills_str = candidate.get('skills', '') or ''
            skills_list = [s.strip().lower() for s in skills_str.split(',') if s.strip()]
            
            # Calculate scores
            if required_cgpa > 0:
                cgpa_score = min(cgpa / required_cgpa, 1.5) / 1.5
            else:
                cgpa_score = cgpa / 10.0
            
            if required_skills_list:
                matched = set(skills_list) & set(required_skills_list)
                skill_score = len(matched) / len(required_skills_list)
            else:
                skill_score = 0.8
            
            total_score = (cgpa_score * 0.5) + (skill_score * 0.5)
            
            ranked.append({
                'candidate_id': candidate.get('user_id'),
                'name': candidate.get('full_name', 'Unknown'),
                'rank_score': total_score,
                'component_scores': {
                    'cgpa_score': cgpa_score,
                    'skill_score': skill_score,
                    'experience_score': 0,
                    'project_score': 0
                },
                'application_status': candidate.get('application_status', 'not_applied'),  # ✅ YAHI SE STATUS
                'eligibility': {
                    'eligible': cgpa >= required_cgpa,
                    'cgpa_met': cgpa >= required_cgpa
                }
            })
        
        # Sort by score
        ranked.sort(key=lambda x: x['rank_score'], reverse=True)
        for idx, candidate in enumerate(ranked):
            candidate['rank'] = idx + 1
        
        if top_k and int(top_k) > 0:
            ranked = ranked[:int(top_k)]
        
        # Calculate counts
        applied_count = 0
        shortlisted_count = 0
        selected_count = 0
        
        for student in students:
            status = student.get('application_status', '')
            if status == 'applied':
                applied_count += 1
            elif status == 'shortlisted':
                shortlisted_count += 1
                applied_count += 1
            elif status == 'selected':
                selected_count += 1
                applied_count += 1
        
        return {
            'drive_id': drive_id,
            'job_title': drive['job_title'],
            'company': drive['company_name'],
            'ranking_method': 'rule-based',
            'total_candidates': len(ranked),
            'applied_candidates': applied_count,
            'shortlisted_candidates': shortlisted_count,
            'selected_candidates': selected_count,
            'ranked_candidates': ranked
        }
        
    except Exception as e:
        logger.error(f"Ranking error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.post("/rank-with-weights/{drive_id}")
async def rank_candidates_with_custom_weights(
    drive_id: int,
    weights: Dict[str, float] = Body({
        'cgpa_score': 0.20,
        'skill_score': 0.35,
        'experience_score': 0.15,
        'project_score': 0.15,
        'soft_skills_score': 0.10,
        'certification_score': 0.05
    }),
    top_k: Optional[int] = Query(10, description="Number of top candidates"),
    admin = Depends(require_admin)
):
    """
    Rank candidates with custom weights for different criteria
    Allows admin to prioritize different factors
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
        
        # Get all students
        cursor.execute("""
            SELECT u.id as user_id, u.full_name, sp.*
            FROM student_profiles sp
            JOIN users u ON sp.user_id = u.id
        """)
        
        students = cursor.fetchall()
        
        # Rank with custom weights
        ranked = ranker.rank_with_custom_weights(
            candidates=students,
            drive_data=drive,
            weights=weights,
            top_k=top_k
        )
        
        return {
            'drive_id': drive_id,
            'job_title': drive['job_title'],
            'company': drive['company_name'],
            'weights_used': weights,
            'total_candidates': len(students),
            'top_candidates': ranked
        }
        
    except Exception as e:
        logger.error(f"Custom ranking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/compare-rankers/{drive_id}")
async def compare_ranking_methods(
    drive_id: int,
    top_k: int = Query(10, description="Number of top candidates"),
    admin = Depends(require_admin)
):
    """
    Compare different ranking methods for the same drive
    Shows how different algorithms rank candidates
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
        
        # Get all students
        cursor.execute("""
            SELECT u.id as user_id, u.full_name, sp.*
            FROM student_profiles sp
            JOIN users u ON sp.user_id = u.id
        """)
        
        students = cursor.fetchall()
        
        # Rank with different methods
        methods = ['pointwise', 'pairwise', 'ensemble']
        comparison = {}
        
        for method in methods:
            try:
                ranked = ranker.rank_candidates_advanced(
                    candidates=students,
                    drive_data=drive,
                    method=method,
                    top_k=top_k
                )
                comparison[method] = ranked
            except Exception as e:
                comparison[method] = {'error': str(e)}
        
        # Find consensus candidates (appear in top K of all methods)
        if all(method in comparison for method in methods):
            consensus = {}
            for candidate_id in set().union(*[
                {c['candidate_id'] for c in comparison[method] if 'candidate_id' in c}
                for method in methods if method in comparison
            ]):
                avg_rank = 0
                count = 0
                for method in methods:
                    for idx, c in enumerate(comparison[method]):
                        if c.get('candidate_id') == candidate_id:
                            avg_rank += (idx + 1)
                            count += 1
                            break
                if count > 0:
                    consensus[candidate_id] = avg_rank / count
            
            # Sort by average rank
            consensus_list = sorted(consensus.items(), key=lambda x: x[1])
            comparison['consensus'] = [
                {'candidate_id': cid, 'avg_rank': rank}
                for cid, rank in consensus_list[:top_k]
            ]
        
        return {
            'drive_id': drive_id,
            'job_title': drive['job_title'],
            'company': drive['company_name'],
            'total_candidates': len(students),
            'methods_comparison': comparison
        }
        
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/candidate/{candidate_id}/rank-explanation/{drive_id}")
async def get_candidate_rank_explanation(
    candidate_id: int,
    drive_id: int,
    admin = Depends(require_admin)
):
    """
    Get detailed explanation of why a candidate got their rank
    """
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get candidate details
        cursor.execute("""
            SELECT u.id as user_id, u.full_name, sp.*
            FROM student_profiles sp
            JOIN users u ON sp.user_id = u.id
            WHERE u.id = %s
        """, (candidate_id,))
        
        candidate = cursor.fetchone()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
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
        
        # Calculate component scores
        cgpa_score = ranker._calculate_cgpa_score(candidate, drive)
        skill_score = ranker._calculate_skill_score(candidate, drive)
        exp_score = ranker._calculate_experience_score(candidate)
        project_score = ranker._calculate_project_score(candidate)
        
        # Get explanation
        explanation = ranker._generate_ranking_explanation(
            candidate, cgpa_score, skill_score, exp_score, project_score
        )
        
        # Get features
        features = ranker.extract_candidate_features(candidate, drive)
        
        # Get all candidates for comparison
        cursor.execute("""
            SELECT u.id as user_id, u.full_name, sp.cgpa, sp.skills
            FROM student_profiles sp
            JOIN users u ON sp.user_id = u.id
        """)
        
        all_candidates = cursor.fetchall()
        
        # Calculate percentile
        all_scores = []
        for cand in all_candidates:
            cgpa = float(cand.get('cgpa', 0))
            required = float(drive.get('eligibility_cgpa', 0))
            if required > 0:
                score = min(cgpa / required, 1.5) / 1.5
            else:
                score = cgpa / 10.0
            all_scores.append(score)
        
        percentile = sum(1 for s in all_scores if s < cgpa_score) / len(all_scores) * 100 if all_scores else 50
        
        return {
            'candidate_name': candidate['full_name'],
            'drive': drive['company_name'] + ' - ' + drive['job_title'],
            'rank_explanation': explanation,
            'component_scores': {
                'cgpa_score': cgpa_score,
                'skill_score': skill_score,
                'experience_score': exp_score,
                'project_score': project_score
            },
            'percentile_rank': round(percentile, 1),
            'feature_vector': features.tolist() if hasattr(features, 'tolist') else features,
            'eligibility': ranker._check_eligibility(candidate, drive)
        }
        
    except Exception as e:
        logger.error(f"Explanation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/model-info")
async def get_ranking_model_info(
    admin = Depends(require_admin)
):
    """Get information about ranking models"""
    
    return {
        'pointwise_model': ranker.pointwise_model is not None,
        'pairwise_model': ranker.pairwise_model is not None,
        'listwise_model': ranker.listwise_model is not None,
        'feature_count': len(ranker.feature_names) if ranker.feature_names else 0,
        'ranking_weights': ranker.ranking_weights,
        'status': 'trained' if ranker.pointwise_model else 'not_trained'
    }