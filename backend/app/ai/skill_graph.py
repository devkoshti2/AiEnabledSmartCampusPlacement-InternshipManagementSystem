"""
Advanced Skill Gap Analysis with Skill Graph
Features:
- Prerequisite skill graph (Python → Pandas → NumPy → TensorFlow)
- Sequential learning path generation
- Market demand analysis
- Personalized learning pace recommendations
- Skill clustering and relationships
"""

import json
import logging
import math
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, Counter
import datetime
import random

logger = logging.getLogger(__name__)


class SkillGraph:
    """
    Skill Graph with prerequisite relationships
    """
    
    def __init__(self):
        self.graph = {}  # skill -> list of prerequisite skills
        self.skill_categories = {}  # skill -> category
        self.skill_difficulty = {}  # skill -> difficulty level (1-5)
        self.skill_demand = {}  # skill -> market demand score (0-1)
        self.skill_trends = {}  # skill -> trend (rising/stable/falling)
        
        # Build the skill graph
        self._build_skill_graph()
        
        logger.info(f"✅ SkillGraph initialized with {len(self.graph)} skills")
    
    def _build_skill_graph(self):
        """Build comprehensive skill graph with prerequisites"""
        
        # Programming Languages (Foundation)
        self._add_skill("python", [], "programming_language", 2, 0.95, "rising")
        self._add_skill("java", [], "programming_language", 2, 0.90, "stable")
        self._add_skill("javascript", [], "programming_language", 2, 0.92, "rising")
        self._add_skill("c++", [], "programming_language", 3, 0.75, "stable")
        self._add_skill("c#", [], "programming_language", 3, 0.70, "stable")
        self._add_skill("ruby", [], "programming_language", 2, 0.50, "falling")
        self._add_skill("php", [], "programming_language", 2, 0.55, "falling")
        self._add_skill("go", [], "programming_language", 3, 0.65, "rising")
        self._add_skill("rust", [], "programming_language", 4, 0.60, "rising")
        self._add_skill("swift", [], "programming_language", 3, 0.70, "rising")
        self._add_skill("kotlin", [], "programming_language", 3, 0.68, "rising")
        self._add_skill("typescript", ["javascript"], "programming_language", 3, 0.85, "rising")
        
        # Python Data Science Stack
        self._add_skill("python_basics", ["python"], "python_foundation", 1, 0.95, "stable")
        self._add_skill("pandas", ["python"], "data_science", 3, 0.90, "rising")
        self._add_skill("numpy", ["python"], "data_science", 3, 0.88, "rising")
        self._add_skill("scipy", ["numpy", "python"], "data_science", 4, 0.75, "stable")
        self._add_skill("matplotlib", ["python", "numpy"], "visualization", 3, 0.80, "stable")
        self._add_skill("seaborn", ["matplotlib", "python"], "visualization", 3, 0.75, "rising")
        self._add_skill("plotly", ["python"], "visualization", 3, 0.70, "rising")
        
        # Machine Learning Stack
        self._add_skill("machine_learning", ["python", "numpy", "pandas"], "ai_ml", 4, 0.95, "rising")
        self._add_skill("scikit_learn", ["python", "numpy", "machine_learning"], "ai_ml", 3, 0.88, "rising")
        self._add_skill("tensorflow", ["python", "numpy", "machine_learning"], "deep_learning", 4, 0.90, "rising")
        self._add_skill("keras", ["tensorflow", "python"], "deep_learning", 3, 0.85, "rising")
        self._add_skill("pytorch", ["python", "numpy", "machine_learning"], "deep_learning", 4, 0.92, "rising")
        self._add_skill("nlp", ["python", "machine_learning"], "ai_ml", 4, 0.88, "rising")
        self._add_skill("transformers", ["nlp", "python", "pytorch"], "deep_learning", 5, 0.85, "rising")
        self._add_skill("langchain", ["python", "nlp"], "ai_ml", 4, 0.80, "rising")
        self._add_skill("llm", ["nlp", "transformers", "python"], "ai_ml", 5, 0.95, "rising")
        self._add_skill("rag", ["llm", "langchain", "python"], "ai_ml", 5, 0.85, "rising")
        self._add_skill("vector_databases", ["python", "rag"], "ai_ml", 4, 0.75, "rising")
        self._add_skill("embeddings", ["nlp", "python"], "ai_ml", 4, 0.80, "rising")
        
        # Web Development Stack
        self._add_skill("html", [], "web", 1, 0.90, "stable")
        self._add_skill("css", ["html"], "web", 2, 0.88, "stable")
        self._add_skill("javascript_web", ["javascript"], "web", 3, 0.92, "rising")
        self._add_skill("react", ["javascript_web", "html"], "frontend", 4, 0.95, "rising")
        self._add_skill("vue", ["javascript_web", "html"], "frontend", 4, 0.80, "rising")
        self._add_skill("angular", ["javascript_web", "typescript"], "frontend", 4, 0.75, "stable")
        self._add_skill("nodejs", ["javascript"], "backend", 3, 0.88, "rising")
        self._add_skill("express", ["nodejs"], "backend", 3, 0.85, "stable")
        self._add_skill("django", ["python"], "backend", 3, 0.80, "stable")
        self._add_skill("flask", ["python"], "backend", 3, 0.75, "stable")
        self._add_skill("fastapi", ["python"], "backend", 3, 0.82, "rising")
        
        # Databases
        self._add_skill("sql", [], "database", 2, 0.95, "stable")
        self._add_skill("mysql", ["sql"], "database", 2, 0.88, "stable")
        self._add_skill("postgresql", ["sql"], "database", 3, 0.85, "rising")
        self._add_skill("mongodb", [], "database", 3, 0.80, "rising")
        self._add_skill("redis", [], "database", 3, 0.70, "rising")
        self._add_skill("elasticsearch", [], "database", 4, 0.65, "rising")
        
        # Cloud & DevOps
        self._add_skill("git", [], "devops", 2, 0.95, "stable")
        self._add_skill("docker", ["git"], "devops", 3, 0.90, "rising")
        self._add_skill("kubernetes", ["docker"], "devops", 4, 0.85, "rising")
        self._add_skill("jenkins", ["git"], "devops", 3, 0.70, "stable")
        self._add_skill("aws", [], "cloud", 3, 0.95, "rising")
        self._add_skill("azure", [], "cloud", 3, 0.85, "rising")
        self._add_skill("gcp", [], "cloud", 3, 0.80, "rising")
        self._add_skill("terraform", ["aws", "cloud"], "devops", 4, 0.75, "rising")
        self._add_skill("ansible", [], "devops", 3, 0.65, "stable")
        
        # Add all skills to graph (including those without prerequisites)
        all_skills = list(self.skill_categories.keys())
        for skill in all_skills:
            if skill not in self.graph:
                self.graph[skill] = []
    
    def _add_skill(self, skill: str, prerequisites: List[str], 
                  category: str, difficulty: int, demand: float, trend: str):
        """Add a skill to the graph"""
        self.graph[skill] = prerequisites
        self.skill_categories[skill] = category
        self.skill_difficulty[skill] = difficulty
        self.skill_demand[skill] = demand
        self.skill_trends[skill] = trend
    
    def get_prerequisites(self, skill: str) -> List[str]:
        """Get all prerequisites for a skill"""
        return self.graph.get(skill, [])
    
    def get_all_prerequisites_recursive(self, skill: str, visited: Set[str] = None) -> List[str]:
        """Get all prerequisites recursively"""
        if visited is None:
            visited = set()
        
        if skill in visited:
            return []
        
        visited.add(skill)
        prerequisites = []
        
        for prereq in self.graph.get(skill, []):
            prerequisites.append(prereq)
            prerequisites.extend(self.get_all_prerequisites_recursive(prereq, visited))
        
        return list(set(prerequisites))  # Remove duplicates
    
    def get_learning_path(self, target_skill: str, current_skills: List[str]) -> List[Dict]:
        """
        Generate optimal learning path from current skills to target skill
        """
        # Get all required prerequisites
        all_required = self.get_all_prerequisites_recursive(target_skill)
        all_required.append(target_skill)
        
        # Remove skills already known
        current_skills_lower = [s.lower().strip() for s in current_skills]
        skills_to_learn = [s for s in all_required if s not in current_skills_lower]
        
        # Sort by difficulty and prerequisites
        def skill_score(skill):
            # Count how many prerequisites are already known
            prereqs = self.graph.get(skill, [])
            known_prereqs = sum(1 for p in prereqs if p in current_skills_lower)
            total_prereqs = len(prereqs)
            
            # Priority: skills with more known prerequisites first
            if total_prereqs > 0:
                readiness = known_prereqs / total_prereqs
            else:
                readiness = 1.0
            
            # Combine with difficulty (easier first)
            difficulty = self.skill_difficulty.get(skill, 3)
            
            return (readiness, -difficulty)  # Higher readiness first, then easier
        
        skills_to_learn.sort(key=skill_score, reverse=True)
        
        # Generate learning path with estimates
        learning_path = []
        total_hours = 0
        
        for i, skill in enumerate(skills_to_learn):
            # Estimate hours based on difficulty
            difficulty = self.skill_difficulty.get(skill, 3)
            hours = difficulty * 10  # 10-50 hours per skill
            
            total_hours += hours
            
            learning_path.append({
                'step': i + 1,
                'skill': skill,
                'display_name': skill.replace('_', ' ').title(),
                'category': self.skill_categories.get(skill, 'unknown'),
                'difficulty': difficulty,
                'estimated_hours': hours,
                'prerequisites': self.graph.get(skill, []),
                'market_demand': self.skill_demand.get(skill, 0.5),
                'trend': self.skill_trends.get(skill, 'stable')
            })
        
        return learning_path
    
    def get_skill_recommendations(self, current_skills: List[str], 
                                  career_goal: str = None,
                                  limit: int = 10) -> List[Dict]:
        """
        Recommend next skills to learn based on market demand and graph
        """
        current_skills_lower = [s.lower().strip() for s in current_skills]
        
        # Find all skills that are not yet learned
        all_skills = set(self.graph.keys())
        unknown_skills = all_skills - set(current_skills_lower)
        
        recommendations = []
        
        for skill in unknown_skills:
            # Check prerequisites
            prereqs = self.graph.get(skill, [])
            prereqs_known = all(p in current_skills_lower for p in prereqs)
            
            if not prereqs_known:
                continue  # Skip if prerequisites not met
            
            # Calculate score based on multiple factors
            demand_score = self.skill_demand.get(skill, 0.5)
            
            # Trend bonus
            trend = self.skill_trends.get(skill, 'stable')
            trend_bonus = {
                'rising': 0.2,
                'stable': 0.0,
                'falling': -0.1
            }.get(trend, 0)
            
            # Difficulty factor (easier skills recommended first)
            difficulty = self.skill_difficulty.get(skill, 3)
            difficulty_score = 1.0 - (difficulty - 1) / 4  # Normalize to 0-1
            
            # Career goal matching (simplified)
            goal_match = 1.0
            if career_goal:
                if career_goal.lower() in ['data science', 'ai', 'ml']:
                    if self.skill_categories.get(skill) in ['data_science', 'ai_ml', 'deep_learning']:
                        goal_match = 1.5
                elif career_goal.lower() in ['web development', 'frontend', 'backend']:
                    if self.skill_categories.get(skill) in ['web', 'frontend', 'backend']:
                        goal_match = 1.5
            
            # Combined score
            score = (demand_score + trend_bonus) * 0.5 + difficulty_score * 0.3 + goal_match * 0.2
            
            recommendations.append({
                'skill': skill,
                'display_name': skill.replace('_', ' ').title(),
                'category': self.skill_categories.get(skill, 'unknown'),
                'demand_score': round(demand_score, 2),
                'trend': trend,
                'difficulty': difficulty,
                'estimated_hours': difficulty * 10,
                'prerequisites': prereqs,
                'score': round(score, 2)
            })
        
        # Sort by score
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        return recommendations[:limit]
    
    def get_market_trends(self) -> Dict:
        """Get market demand trends for skills"""
        
        # Group by category
        category_trends = defaultdict(lambda: {'count': 0, 'avg_demand': 0, 'rising': 0})
        
        for skill, category in self.skill_categories.items():
            category_trends[category]['count'] += 1
            category_trends[category]['avg_demand'] += self.skill_demand.get(skill, 0)
            
            if self.skill_trends.get(skill) == 'rising':
                category_trends[category]['rising'] += 1
        
        # Calculate averages
        for cat in category_trends:
            if category_trends[cat]['count'] > 0:
                category_trends[cat]['avg_demand'] /= category_trends[cat]['count']
                category_trends[cat]['avg_demand'] = round(category_trends[cat]['avg_demand'], 2)
        
        # Top rising skills
        rising_skills = [
            {'skill': s.replace('_', ' ').title(), 'demand': self.skill_demand.get(s, 0)}
            for s in self.graph.keys() if self.skill_trends.get(s) == 'rising'
        ]
        rising_skills.sort(key=lambda x: x['demand'], reverse=True)
        
        return {
            'categories': dict(category_trends),
            'top_rising_skills': rising_skills[:10],
            'total_skills': len(self.graph),
            'last_updated': datetime.datetime.now().isoformat()
        }


class SkillGapAnalyzer:
    """
    Complete Skill Gap Analysis with personalized recommendations
    """
    
    def __init__(self):
        self.skill_graph = SkillGraph()
        self.user_progress = {}  # user_id -> {skill: proficiency, time_spent}
        
        # Learning pace estimation (hours per week)
        self.default_pace = 10  # hours/week
        
        logger.info("✅ SkillGapAnalyzer initialized")
    
    def analyze_skill_gap(self, user_id: int, current_skills: List[str], 
                          target_role: str = None) -> Dict:
        """
        Complete skill gap analysis for a user
        """
        current_skills_lower = [s.lower().strip() for s in current_skills]
        
        # Get missing skills for target role
        if target_role:
            role_skills = self._get_role_skills(target_role)
        else:
            # If no target role, recommend based on market demand
            role_skills = [s for s in self.skill_graph.graph.keys() 
                          if s not in current_skills_lower][:20]
        
        # Get learning path for each missing skill
        missing_skills = [s for s in role_skills if s not in current_skills_lower]
        
        # Group by category
        skill_categories = defaultdict(list)
        for skill in missing_skills:
            cat = self.skill_graph.skill_categories.get(skill, 'other')
            skill_categories[cat].append(skill)
        
        # Generate learning paths
        learning_paths = {}
        for skill in missing_skills[:5]:  # Top 5 skills
            path = self.skill_graph.get_learning_path(skill, current_skills)
            if path:
                learning_paths[skill] = path
        
        # Get personalized pace
        pace = self._get_user_pace(user_id)
        
        # Calculate time estimates
        total_hours = sum(self.skill_graph.skill_difficulty.get(s, 3) * 10 
                         for s in missing_skills)
        
        weeks_needed = math.ceil(total_hours / pace)
        months_needed = math.ceil(weeks_needed / 4)
        
        # Get skill recommendations
        recommendations = self.skill_graph.get_skill_recommendations(
            current_skills, target_role, limit=10
        )
        
        # Get market trends
        market_trends = self.skill_graph.get_market_trends()
        
        return {
            'user_id': user_id,
            'target_role': target_role,
            'current_skills_count': len(current_skills),
            'missing_skills_count': len(missing_skills),
            'missing_skills_by_category': dict(skill_categories),
            'total_learning_hours': total_hours,
            'estimated_weeks': weeks_needed,
            'estimated_months': months_needed,
            'learning_pace_hours_per_week': pace,
            'learning_paths': learning_paths,
            'recommended_next_skills': recommendations,
            'market_trends': market_trends,
            'proficiency_score': self._calculate_proficiency_score(current_skills)
        }
    
    def _get_role_skills(self, role: str) -> List[str]:
        """Get skills required for a specific role"""
        
        role_skills = {
            'data scientist': [
                'python', 'pandas', 'numpy', 'scikit_learn', 'tensorflow',
                'pytorch', 'sql', 'matplotlib', 'machine_learning', 'nlp'
            ],
            'machine learning engineer': [
                'python', 'tensorflow', 'pytorch', 'docker', 'kubernetes',
                'aws', 'mlops', 'scikit_learn', 'pandas', 'numpy'
            ],
            'frontend developer': [
                'javascript', 'html', 'css', 'react', 'vue', 'typescript',
                'webpack', 'redux', 'jest'
            ],
            'backend developer': [
                'python', 'java', 'nodejs', 'sql', 'postgresql', 'mongodb',
                'docker', 'aws', 'django', 'flask', 'fastapi'
            ],
            'full stack developer': [
                'javascript', 'python', 'html', 'css', 'react', 'nodejs',
                'sql', 'mongodb', 'git', 'docker', 'aws'
            ],
            'devops engineer': [
                'linux', 'docker', 'kubernetes', 'jenkins', 'aws', 'terraform',
                'ansible', 'git', 'python', 'prometheus', 'grafana'
            ],
            'data engineer': [
                'python', 'sql', 'spark', 'hadoop', 'kafka', 'airflow',
                'aws', 'docker', 'postgresql', 'mongodb', 'pandas'
            ],
            'ai engineer': [
                'python', 'tensorflow', 'pytorch', 'nlp', 'transformers',
                'langchain', 'llm', 'rag', 'docker', 'aws', 'vector_databases'
            ]
        }
        
        # Normalize role
        role_lower = role.lower()
        for key in role_skills:
            if key in role_lower:
                return role_skills[key]
        
        # Default to trending skills
        trending = [
            s for s, trend in self.skill_graph.skill_trends.items() 
            if trend == 'rising'
        ]
        return trending[:15]
    
    def _get_user_pace(self, user_id: int) -> int:
        """Get user's learning pace (hours per week)"""
        
        if user_id in self.user_progress:
            # Calculate from history
            progress = self.user_progress.get(user_id, {})
            total_hours = progress.get('total_hours', 0)
            days_active = progress.get('days_active', 1)
            
            if days_active > 0:
                avg_daily = total_hours / days_active
                return int(avg_daily * 7)  # Weekly pace
        else:
            # Initialize new user
            self.user_progress[user_id] = {
                'total_hours': 0,
                'days_active': 0,
                'skills': {}
            }
        
        return self.default_pace
    
    def _calculate_proficiency_score(self, skills: List[str]) -> float:
        """Calculate overall proficiency score"""
        
        if not skills:
            return 0.0
        
        total_score = 0
        for skill in skills:
            skill_lower = skill.lower().strip()
            difficulty = self.skill_graph.skill_difficulty.get(skill_lower, 3)
            demand = self.skill_graph.skill_demand.get(skill_lower, 0.5)
            
            # Score based on difficulty and demand
            score = (difficulty / 5) * 0.4 + demand * 0.6
            total_score += score
        
        avg_score = total_score / len(skills)
        return round(avg_score * 100, 1)
    
    def update_user_progress(self, user_id: int, skill: str, hours_spent: int):
        """Update user's learning progress"""
        
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {
                'total_hours': 0,
                'days_active': 0,
                'skills': {}
            }
        
        self.user_progress[user_id]['total_hours'] += hours_spent
        self.user_progress[user_id]['days_active'] += 1
        
        if skill not in self.user_progress[user_id]['skills']:
            self.user_progress[user_id]['skills'][skill] = 0
        
        self.user_progress[user_id]['skills'][skill] += hours_spent
    
    def get_personalized_learning_plan(self, user_id: int, 
                                       current_skills: List[str],
                                       weekly_hours: int = None,
                                       target_role: str = None) -> Dict:
        """
        Generate personalized learning plan based on user's pace
        """
        # Get user's pace
        if weekly_hours:
            pace = weekly_hours
        else:
            pace = self._get_user_pace(user_id)
        
        # Get skill gap analysis
        gap_analysis = self.analyze_skill_gap(user_id, current_skills, target_role)
        
        # Create weekly plan
        weekly_plan = []
        total_hours_planned = 0
        week = 1
        
        for rec in gap_analysis['recommended_next_skills']:
            skill = rec['skill']
            hours_needed = rec['estimated_hours']
            
            # Calculate weeks needed for this skill
            weeks_for_skill = math.ceil(hours_needed / pace)
            
            weekly_plan.append({
                'week': week,
                'skill': rec['display_name'],
                'hours': hours_needed,
                'weeks_needed': weeks_for_skill,
                'prerequisites': rec['prerequisites'],
                'category': rec['category'],
                'resources': self._get_learning_resources(skill)
            })
            
            total_hours_planned += hours_needed
            week += weeks_for_skill
        
        return {
            'user_id': user_id,
            'weekly_pace': pace,
            'total_weeks': week - 1,
            'total_hours': total_hours_planned,
            'weekly_plan': weekly_plan,
            'skill_recommendations': gap_analysis['recommended_next_skills'],
            'market_insights': gap_analysis['market_trends']['top_rising_skills'][:5]
        }
    
    def _get_learning_resources(self, skill: str) -> List[Dict]:
        """Get learning resources for a skill"""
        
        resources = {
            'python': [
                {'name': 'Python for Beginners', 'platform': 'Coursera', 'url': 'https://www.coursera.org/learn/python', 'hours': 40},
                {'name': 'Complete Python Bootcamp', 'platform': 'Udemy', 'url': 'https://www.udemy.com/course/python-bootcamp/', 'hours': 60}
            ],
            'pandas': [
                {'name': 'Pandas for Data Science', 'platform': 'Coursera', 'url': 'https://www.coursera.org/learn/pandas', 'hours': 20},
                {'name': 'Data Analysis with Pandas', 'platform': 'YouTube', 'url': 'https://youtube.com/playlist?list=...', 'hours': 15}
            ],
            'tensorflow': [
                {'name': 'TensorFlow Developer Certificate', 'platform': 'Coursera', 'url': 'https://www.coursera.org/professional-certificates/tensorflow', 'hours': 80},
                {'name': 'TensorFlow for Deep Learning', 'platform': 'Udemy', 'url': 'https://www.udemy.com/course/tensorflow/', 'hours': 40}
            ]
        }
        
        skill_lower = skill.lower().replace(' ', '_')
        if skill_lower in resources:
            return resources[skill_lower]
        
        # Default resource
        return [
            {'name': f'Learn {skill}', 'platform': 'Coursera', 
             'url': f'https://www.coursera.org/search?query={skill}', 'hours': 30},
            {'name': f'{skill} Tutorial', 'platform': 'YouTube', 
             'url': f'https://www.youtube.com/results?search_query={skill}', 'hours': 20}
        ]
    
    def get_skill_clusters(self, skills: List[str]) -> Dict:
        """
        Group related skills into clusters
        """
        clusters = defaultdict(list)
        
        for skill in skills:
            skill_lower = skill.lower().strip()
            category = self.skill_graph.skill_categories.get(skill_lower, 'other')
            clusters[category].append(skill)
        
        return dict(clusters)


# Singleton instance
_analyzer = None

def get_skill_gap_analyzer():
    """Get or create SkillGapAnalyzer singleton"""
    global _analyzer
    if _analyzer is None:
        _analyzer = SkillGapAnalyzer()
    return _analyzer