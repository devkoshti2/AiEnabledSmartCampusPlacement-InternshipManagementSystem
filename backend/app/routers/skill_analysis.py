# app/routers/skill_analysis.py

from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth import get_current_active_user, require_admin
from app.database import get_db_connection
from app.ai.skill_enhancer import SkillEnhancer
import logging
from typing import List, Optional

router = APIRouter(prefix="/skills", tags=["Skill Analysis"])
logger = logging.getLogger(__name__)

# Initialize skill enhancer
skill_enhancer = SkillEnhancer()

@router.get("/similar/{skill}")
async def get_similar_skills(
    skill: str,
    threshold: float = Query(0.7, description="Similarity threshold (0-1)"),
    top_k: int = Query(5, description="Number of similar skills to return"),
    current_user = Depends(get_current_active_user)
):
    """Find similar skills using embeddings (e.g., TensorFlow → Keras, PyTorch)"""
    
    similar = skill_enhancer.find_similar_skills(skill, threshold, top_k)
    
    return {
        'skill': skill,
        'similar_skills': similar,
        'count': len(similar)
    }

@router.get("/synonyms/{skill}")
async def get_skill_synonyms(
    skill: str,
    current_user = Depends(get_current_active_user)
):
    """Get synonyms and variations for a skill (e.g., Python → Python3, python programming)"""
    
    synonyms = skill_enhancer.get_skill_synonyms(skill)
    
    return {
        'skill': skill,
        'synonyms': synonyms,
        'count': len(synonyms)
    }

@router.post("/analyze")
async def analyze_skills(
    skills: List[str],
    current_user = Depends(get_current_active_user)
):
    """Analyze a list of skills - cluster them into groups"""
    
    clusters = skill_enhancer.cluster_skills(skills)
    
    return {
        'skills': skills,
        'clusters': clusters,
        'total_skills': len(skills),
        'num_clusters': clusters.get('num_clusters', 0)
    }

@router.post("/detect-level")
async def detect_skill_level(
    skill: str,
    context: str,
    current_user = Depends(get_current_active_user)
):
    """Detect skill level (beginner/intermediate/advanced) from context"""
    
    level_info = skill_enhancer.detect_skill_level(skill, context)
    
    return {
        'skill': skill,
        'context': context[:100] + "..." if len(context) > 100 else context,
        'level': level_info['level'],
        'confidence': level_info['confidence'],
        'scores': level_info['scores']
    }

@router.get("/emerging")
async def get_emerging_skills(
    admin = Depends(require_admin)
):
    """Detect emerging skills from recent placement drives"""
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get recent drives (last 6 months)
        cursor.execute("""
            SELECT required_skills, created_at 
            FROM placement_drives 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            AND required_skills IS NOT NULL 
            AND required_skills != ''
            ORDER BY created_at DESC
        """)
        
        drives = cursor.fetchall()
        
        if not drives:
            return {
                'emerging_skills': [],
                'total_drives_analyzed': 0,
                'message': 'No drives found in last 6 months'
            }
        
        emerging = skill_enhancer.detect_emerging_skills(drives)
        
        return {
            'emerging_skills': emerging,
            'total_drives_analyzed': len(drives)
        }
        
    except Exception as e:
        logger.error(f"Error detecting emerging skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.post("/match-score")
async def calculate_match_score(
    student_skills: List[str],
    required_skills: List[str],
    current_user = Depends(get_current_active_user)
):
    """Calculate enhanced skill match score with synonyms and related skills"""
    
    result = skill_enhancer.calculate_skill_match_score(
        student_skills,
        required_skills
    )
    
    return result

@router.get("/taxonomy")
async def get_skill_taxonomy(
    current_user = Depends(get_current_active_user)
):
    """Get the complete skill taxonomy/categories"""
    
    taxonomy = {}
    for category, skills in skill_enhancer.skill_taxonomy.items():
        taxonomy[category] = list(skills)[:20]  # Limit to 20 per category
    
    return {
        'taxonomy': taxonomy,
        'categories': list(skill_enhancer.skill_taxonomy.keys())
    }

@router.get("/category/{skill}")
async def get_skill_category(
    skill: str,
    current_user = Depends(get_current_active_user)
):
    """Find which category a skill belongs to"""
    
    skill_lower = skill.lower()
    categories = []
    
    for category, skills in skill_enhancer.skill_taxonomy.items():
        if skill_lower in skills:
            categories.append(category)
    
    return {
        'skill': skill,
        'categories': categories if categories else ['uncategorized']
    }