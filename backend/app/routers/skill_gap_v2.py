"""
Advanced Skill Gap Analysis API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth import get_current_active_user, require_admin
from app.database import get_db_connection
from app.ai.skill_graph import get_skill_gap_analyzer
from app.utils.resume_parser import SkillExtractor
import logging
from typing import List, Optional

router = APIRouter(prefix="/skill-gap-v2", tags=["Skill Gap Analysis V2"])
logger = logging.getLogger(__name__)

# Get analyzer instance
analyzer = get_skill_gap_analyzer()


@router.get("/analyze")
async def analyze_skill_gap(
    target_role: Optional[str] = Query(None, description="Target job role"),
    current_user = Depends(get_current_active_user)
):
    """
    Analyze skill gap for current user
    """
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get student profile
        cursor.execute("""
            SELECT sp.*, u.full_name
            FROM student_profiles sp
            JOIN users u ON sp.user_id = u.id
            WHERE sp.user_id = %s
        """, (current_user['id'],))
        
        student = cursor.fetchone()
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found")
        
        # Get current skills
        skills_str = student.get('skills', '')
        if skills_str:
            current_skills = [s.strip() for s in skills_str.split(',') if s.strip()]
        else:
            current_skills = []
        
        # Perform analysis
        analysis = analyzer.analyze_skill_gap(
            user_id=current_user['id'],
            current_skills=current_skills,
            target_role=target_role
        )
        
        return {
            'user_name': student['full_name'],
            'analysis': analysis
        }
        
    except Exception as e:
        logger.error(f"Skill gap analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/learning-path/{target_skill}")
async def get_learning_path(
    target_skill: str,
    current_user = Depends(get_current_active_user)
):
    """
    Get learning path for a target skill
    """
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get student's current skills
        cursor.execute("SELECT skills FROM student_profiles WHERE user_id = %s", 
                      (current_user['id'],))
        
        student = cursor.fetchone()
        current_skills = []
        
        if student and student.get('skills'):
            current_skills = [s.strip() for s in student['skills'].split(',') if s.strip()]
        
        # Get learning path
        path = analyzer.skill_graph.get_learning_path(target_skill, current_skills)
        
        return {
            'target_skill': target_skill,
            'current_skills': current_skills,
            'learning_path': path,
            'total_steps': len(path),
            'total_hours': sum(p['estimated_hours'] for p in path)
        }
        
    except Exception as e:
        logger.error(f"Learning path error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/recommendations")
async def get_skill_recommendations(
    career_goal: Optional[str] = Query(None, description="Career goal"),
    limit: int = Query(10, description="Number of recommendations"),
    current_user = Depends(get_current_active_user)
):
    """
    Get personalized skill recommendations
    """
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get student's current skills
        cursor.execute("SELECT skills FROM student_profiles WHERE user_id = %s", 
                      (current_user['id'],))
        
        student = cursor.fetchone()
        current_skills = []
        
        if student and student.get('skills'):
            current_skills = [s.strip() for s in student['skills'].split(',') if s.strip()]
        
        # Get recommendations
        recommendations = analyzer.skill_graph.get_skill_recommendations(
            current_skills=current_skills,
            career_goal=career_goal,
            limit=limit
        )
        
        return {
            'current_skills_count': len(current_skills),
            'recommendations': recommendations,
            'career_goal': career_goal
        }
        
    except Exception as e:
        logger.error(f"Recommendations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/market-trends")
async def get_market_trends(
    admin = Depends(require_admin)
):
    """
    Get market demand trends for skills
    """
    
    trends = analyzer.skill_graph.get_market_trends()
    
    return trends


@router.post("/personalized-plan")
async def get_personalized_learning_plan(
    weekly_hours: Optional[int] = Query(None, description="Hours per week"),
    target_role: Optional[str] = Query(None, description="Target job role"),
    current_user = Depends(get_current_active_user)
):
    """
    Get personalized learning plan based on user's pace
    """
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get student's current skills
        cursor.execute("SELECT skills FROM student_profiles WHERE user_id = %s", 
                      (current_user['id'],))
        
        student = cursor.fetchone()
        current_skills = []
        
        if student and student.get('skills'):
            current_skills = [s.strip() for s in student['skills'].split(',') if s.strip()]
        
        # Get personalized plan
        plan = analyzer.get_personalized_learning_plan(
            user_id=current_user['id'],
            current_skills=current_skills,
            weekly_hours=weekly_hours,
            target_role=target_role
        )
        
        return plan
        
    except Exception as e:
        logger.error(f"Personalized plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/update-progress")
async def update_learning_progress(
    skill: str,
    hours_spent: int,
    current_user = Depends(get_current_active_user)
):
    """
    Update user's learning progress
    """
    
    analyzer.update_user_progress(
        user_id=current_user['id'],
        skill=skill,
        hours_spent=hours_spent
    )
    
    return {
        'message': f'Progress updated for skill: {skill}',
        'hours_spent': hours_spent
    }


@router.get("/skill-clusters")
async def get_skill_clusters(
    skills: str = Query(..., description="Comma-separated skills"),
    current_user = Depends(get_current_active_user)
):
    """
    Group skills into clusters/categories
    """
    
    skill_list = [s.strip() for s in skills.split(',') if s.strip()]
    
    clusters = analyzer.get_skill_clusters(skill_list)
    
    return {
        'skills': skill_list,
        'clusters': clusters,
        'cluster_count': len(clusters)
    }


@router.get("/graph-info")
async def get_skill_graph_info(
    admin = Depends(require_admin)
):
    """
    Get information about the skill graph
    """
    
    return {
        'total_skills': len(analyzer.skill_graph.graph),
        'categories': set(analyzer.skill_graph.skill_categories.values()),
        'skills_by_category': dict(analyzer.skill_graph.skill_categories),
        'trending_skills': [s for s, t in analyzer.skill_graph.skill_trends.items() if t == 'rising'][:20]
    }