"""
Advanced Resume-Job Matching using Semantic Similarity
PURE PYTHON IMPLEMENTATION - No PyTorch/TensorFlow required
Uses TF-IDF + WordNet for semantic matching
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Any, Optional
import re
from collections import Counter
import math
import os

# Use sklearn for TF-IDF (lightweight)
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ sklearn not installed. Install with: pip install scikit-learn")

# Optional: WordNet for synonyms
try:
    import nltk
    from nltk.corpus import wordnet
    NLTK_AVAILABLE = True
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet', quiet=True)
        nltk.download('omw-1.4', quiet=True)
except ImportError:
    NLTK_AVAILABLE = False

logger = logging.getLogger(__name__)


class ResumeJobMatcher:
    """
    Advanced Resume-Job Matching using Semantic Similarity
    Pure Python implementation - No deep learning frameworks
    """
    
    def __init__(self):
        """Initialize the matcher"""
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            lowercase=True,
            analyzer='word'
        )
        self.is_fitted = False
        
        # Skill importance weights (can be learned from data)
        self.skill_weights = self._load_skill_weights()
        
        # Section weights for overall score
        self.section_weights = {
            'skills': 0.40,
            'experience': 0.30,
            'education': 0.20,
            'projects': 0.10
        }
        
        # Common skill synonyms
        self.skill_synonyms = self._load_skill_synonyms()
        
        logger.info("✅ ResumeJobMatcher initialized (Pure Python)")
    
    def _load_skill_weights(self) -> Dict[str, float]:
        """Load or create skill importance weights"""
        
        # Default weights based on skill categories
        weights = {
            # Programming languages
            'python': 0.9, 'java': 0.85, 'javascript': 0.85, 'c++': 0.8, 'c#': 0.8,
            'ruby': 0.7, 'php': 0.7, 'swift': 0.8, 'kotlin': 0.8, 'go': 0.8,
            'rust': 0.75, 'typescript': 0.85, 'scala': 0.75,
            
            # Web technologies
            'react': 0.85, 'angular': 0.8, 'vue': 0.8, 'node.js': 0.85, 
            'django': 0.8, 'flask': 0.75, 'spring': 0.8, 'html': 0.6, 'css': 0.6,
            
            # Databases
            'sql': 0.8, 'mysql': 0.75, 'postgresql': 0.8, 'mongodb': 0.75,
            'oracle': 0.7, 'redis': 0.7, 'elasticsearch': 0.7,
            
            # Cloud & DevOps
            'aws': 0.9, 'azure': 0.85, 'gcp': 0.85, 'docker': 0.85, 'kubernetes': 0.85,
            'jenkins': 0.75, 'git': 0.7, 'terraform': 0.8, 'ansible': 0.75,
            
            # Data Science & AI
            'machine learning': 0.9, 'deep learning': 0.9, 'tensorflow': 0.85,
            'pytorch': 0.85, 'pandas': 0.75, 'numpy': 0.75, 'nlp': 0.85,
            
            # Soft skills (lower weight)
            'communication': 0.5, 'leadership': 0.5, 'teamwork': 0.5,
            'problem solving': 0.6, 'time management': 0.4
        }
        
        return weights
    
    def _load_skill_synonyms(self) -> Dict[str, List[str]]:
        """Load synonyms for skills"""
        return {
            'python': ['python3', 'python programming', 'python language'],
            'javascript': ['js', 'ecmascript', 'java script'],
            'react': ['reactjs', 'react.js', 'react js'],
            'node.js': ['node', 'nodejs', 'node js'],
            'machine learning': ['ml', 'machine-learning'],
            'deep learning': ['dl', 'deep-learning'],
            'aws': ['amazon web services', 'amazon aws'],
            'gcp': ['google cloud', 'google cloud platform'],
            'c++': ['cpp', 'cplusplus'],
            'c#': ['csharp', 'c sharp'],
            'sql': ['structured query language'],
            'nosql': ['no sql'],
            'git': ['github', 'gitlab'],
        }
    
    def get_wordnet_synonyms(self, word: str) -> List[str]:
        """Get synonyms using WordNet (if available)"""
        synonyms = []
        
        if NLTK_AVAILABLE:
            for syn in wordnet.synsets(word):
                for lemma in syn.lemmas():
                    synonym = lemma.name().replace('_', ' ')
                    if synonym != word and synonym not in synonyms:
                        synonyms.append(synonym)
        
        return synonyms[:5]  # Limit to 5 synonyms
    
    def extract_resume_sections(self, resume_text: str) -> Dict[str, str]:
        """
        Extract different sections from resume text
        """
        sections = {
            'skills': '',
            'experience': '',
            'education': '',
            'projects': '',
            'certifications': '',
            'summary': ''
        }
        
        # Common section headers
        section_patterns = {
            'skills': r'(skills|technical skills|technologies|competencies)[\s:]*?(.*?)(?=\n\n|\n[A-Z]|\Z)',
            'experience': r'(experience|work experience|employment|work history)[\s:]*?(.*?)(?=\n\n|\n[A-Z]|\Z)',
            'education': r'(education|academic background|qualifications)[\s:]*?(.*?)(?=\n\n|\n[A-Z]|\Z)',
            'projects': r'(projects|academic projects|personal projects)[\s:]*?(.*?)(?=\n\n|\n[A-Z]|\Z)',
            'certifications': r'(certifications|certificates|courses)[\s:]*?(.*?)(?=\n\n|\n[A-Z]|\Z)',
            'summary': r'(summary|profile|objective)[\s:]*?(.*?)(?=\n\n|\n[A-Z]|\Z)'
        }
        
        text_lower = resume_text.lower()
        
        for section, pattern in section_patterns.items():
            match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
            if match and len(match.group(2).strip()) > 20:
                sections[section] = match.group(2).strip()
        
        # If sections not found, use whole text
        for section in sections:
            if not sections[section]:
                sections[section] = resume_text[:500]  # First 500 chars as fallback
        
        return sections
    
    def extract_skills_with_context(self, text: str, skill_list: List[str]) -> List[Dict]:
        """
        Extract skills with surrounding context for better matching
        """
        skills_with_context = []
        
        for skill in skill_list:
            skill_lower = skill.lower()
            
            # Find skill in text
            pattern = r'(^|\s|,|\.)' + re.escape(skill_lower) + r'(\s|,|\.|$)'
            matches = list(re.finditer(pattern, text.lower()))
            
            for match in matches:
                # Get context (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                # Detect experience level from context
                level = self._detect_experience_level(context, skill)
                
                skills_with_context.append({
                    'skill': skill,
                    'context': context,
                    'level': level['level'],
                    'years': level['years'],
                    'position': match.start()
                })
        
        return skills_with_context
    
    def _detect_experience_level(self, context: str, skill: str) -> Dict:
        """
        Detect experience level from context
        """
        context_lower = context.lower()
        
        # Look for years of experience
        year_patterns = [
            r'(\d+)\+?\s*years?',
            r'(\d+)\s*yr',
            r'experience.*?(\d+)\s*years?'
        ]
        
        years = 0
        for pattern in year_patterns:
            match = re.search(pattern, context_lower)
            if match:
                years = int(match.group(1))
                break
        
        # Determine level
        if years >= 5:
            level = 'expert'
        elif years >= 3:
            level = 'advanced'
        elif years >= 1:
            level = 'intermediate'
        else:
            # Check for keywords
            if any(word in context_lower for word in ['expert', 'master', 'lead', 'architect']):
                level = 'expert'
                years = max(years, 5)
            elif any(word in context_lower for word in ['advanced', 'proficient', 'extensive']):
                level = 'advanced'
                years = max(years, 3)
            elif any(word in context_lower for word in ['intermediate', 'working knowledge']):
                level = 'intermediate'
                years = max(years, 1)
            else:
                level = 'beginner'
        
        return {'level': level, 'years': years}
    
    def compute_tfidf_similarity(self, text1: str, text2: str) -> float:
        """
        Compute TF-IDF cosine similarity between two texts
        """
        if not SKLEARN_AVAILABLE:
            # Fallback: simple word overlap
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union)
        
        try:
            # Fit vectorizer on both texts
            texts = [text1, text2]
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # Compute cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            self.is_fitted = True
            return float(similarity)
            
        except Exception as e:
            logger.error(f"TF-IDF similarity error: {e}")
            return 0.5  # Default fallback
    
    def semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Compute semantic similarity between two texts
        Uses TF-IDF + word overlap + synonym matching
        """
        # TF-IDF similarity
        tfidf_sim = self.compute_tfidf_similarity(text1, text2)
        
        # Word overlap with synonyms
        words1 = set(re.findall(r'\b[a-z]+\b', text1.lower()))
        words2 = set(re.findall(r'\b[a-z]+\b', text2.lower()))
        
        if not words1 or not words2:
            return tfidf_sim
        
        # Direct overlap
        direct_overlap = len(words1.intersection(words2)) / len(words2)
        
        # Synonym overlap (if WordNet available)
        synonym_overlap = 0
        if NLTK_AVAILABLE:
            synonym_matches = 0
            for word2 in words2:
                for word1 in words1:
                    if word1 == word2:
                        synonym_matches += 1
                        break
                    # Check if words are synonyms
                    syns1 = self.get_wordnet_synonyms(word1)
                    if word2 in syns1:
                        synonym_matches += 0.8
                        break
            
            synonym_overlap = synonym_matches / len(words2) if words2 else 0
        
        # Combine scores
        final_sim = tfidf_sim * 0.5 + direct_overlap * 0.3 + synonym_overlap * 0.2
        
        return min(max(final_sim, 0), 1)  # Clamp between 0 and 1
    
    def match_skills_semantic(self, resume_skills: List[str], job_skills: List[str]) -> Dict:
        """
        Match skills semantically (not just exact match)
        """
        if not job_skills:
            return {
                'score': 1.0,
                'matched': [],
                'missing': [],
                'partial_matches': []
            }
        
        # Normalize skills
        resume_skills_norm = [s.lower().strip() for s in resume_skills]
        job_skills_norm = [s.lower().strip() for s in job_skills]
        
        matched = []
        missing = []
        partial_matches = []
        
        for job_skill in job_skills_norm:
            # Check exact match
            if job_skill in resume_skills_norm:
                matched.append(job_skill)
                continue
            
            # Check synonyms
            synonym_match = False
            for base_skill, synonyms in self.skill_synonyms.items():
                if job_skill == base_skill or job_skill in synonyms:
                    # Check if any synonym is in resume
                    for resume_skill in resume_skills_norm:
                        if resume_skill == base_skill or resume_skill in synonyms:
                            partial_matches.append({
                                'job_skill': job_skill,
                                'resume_skill': resume_skill,
                                'similarity': 0.85
                            })
                            synonym_match = True
                            break
                    if synonym_match:
                        break
            
            if synonym_match:
                continue
            
            # Check partial match (skill contained in another)
            partial_found = False
            for resume_skill in resume_skills_norm:
                if job_skill in resume_skill or resume_skill in job_skill:
                    partial_matches.append({
                        'job_skill': job_skill,
                        'resume_skill': resume_skill,
                        'similarity': 0.7
                    })
                    partial_found = True
                    break
            
            if not partial_found:
                missing.append(job_skill)
        
        # Calculate weighted score
        total_weight = 0
        matched_weight = 0
        
        for skill in job_skills_norm:
            weight = self.skill_weights.get(skill, 0.7)
            total_weight += weight
            
            if skill in matched:
                matched_weight += weight
            elif any(p['job_skill'] == skill for p in partial_matches):
                # Partial match gets partial weight
                partial = next(p for p in partial_matches if p['job_skill'] == skill)
                matched_weight += weight * partial['similarity']
        
        score = matched_weight / total_weight if total_weight > 0 else 0
        
        return {
            'score': round(score, 3),
            'matched': matched,
            'missing': missing,
            'partial_matches': partial_matches,
            'weighted_score': round(matched_weight / total_weight * 100, 1) if total_weight > 0 else 100
        }
    
    def match_experience(self, resume_sections: Dict, job_description: str) -> Dict:
        """
        Match experience section with job description
        """
        resume_exp = resume_sections.get('experience', '')
        
        if not resume_exp:
            return {'score': 0, 'details': 'No experience section found'}
        
        # Compute similarity
        similarity = self.semantic_similarity(resume_exp, job_description)
        
        # Extract years of experience
        exp_years = self._extract_total_experience(resume_exp)
        required_years = self._extract_required_experience(job_description)
        
        years_score = 1.0
        if required_years > 0:
            years_score = min(exp_years / required_years, 1.5) / 1.5
        
        # Combine scores
        final_score = similarity * 0.6 + years_score * 0.4
        
        return {
            'score': round(final_score, 3),
            'similarity': round(similarity, 3),
            'years_match': round(years_score, 3),
            'candidate_years': exp_years,
            'required_years': required_years
        }
    
    def _extract_total_experience(self, text: str) -> float:
        """Extract total years of experience from resume"""
        year_patterns = [
            r'(\d+)\+?\s*years?.*?experience',
            r'experience.*?(\d+)\+?\s*years?',
            r'(\d+)\s*yr',
            r'(\d+)\s*years?'
        ]
        
        years = 0
        for pattern in year_patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                years = max([int(m) for m in matches])
                break
        
        return years
    
    def _extract_required_experience(self, text: str) -> float:
        """Extract required years of experience from job description"""
        patterns = [
            r'(\d+)\+?\s*years?.*?experience',
            r'experience.*?(\d+)\+?\s*years?',
            r'minimum.*?(\d+)\s*years?',
            r'at least.*?(\d+)\s*years?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return int(match.group(1))
        
        return 0
    
    def match_education(self, resume_sections: Dict, job_description: str) -> Dict:
        """
        Match education with job requirements
        """
        resume_edu = resume_sections.get('education', '')
        
        if not resume_edu:
            return {'score': 0.5, 'details': 'No education section found'}
        
        # Extract degree and branch
        resume_degree = self._extract_degree(resume_edu)
        required_degree = self._extract_degree(job_description)
        
        degree_score = 1.0
        if required_degree and resume_degree:
            degree_score = 1.0 if required_degree.lower() in resume_degree.lower() else 0.5
        
        # CGPA/GPA check
        cgpa_score = 1.0
        cgpa_match = re.search(r'cgpa[:\s]*([0-9.]+)', resume_edu.lower())
        if cgpa_match:
            cgpa = float(cgpa_match.group(1))
            cgpa_score = min(cgpa / 8.0, 1.0)  # Normalize to 8.0
        
        return {
            'score': round(degree_score * 0.7 + cgpa_score * 0.3, 3),
            'degree_match': degree_score,
            'cgpa_score': cgpa_score,
            'candidate_degree': resume_degree,
            'required_degree': required_degree
        }
    
    def _extract_degree(self, text: str) -> str:
        """Extract degree information from text"""
        degree_patterns = [
            r'(b\.?tech|bachelor of technology)',
            r'(m\.?tech|master of technology)',
            r'(b\.?sc|bachelor of science)',
            r'(m\.?sc|master of science)',
            r'(bca|bachelor of computer applications)',
            r'(mca|master of computer applications)',
            r'(b\.?e|bachelor of engineering)',
            r'(m\.?e|master of engineering)',
            r'(ph\.?d|doctor of philosophy)',
            r'(bachelor|master|phd)'
        ]
        
        for pattern in degree_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(0)
        
        return ''
    
    def match_job_description(self, resume_text: str, job_description: str) -> Dict:
        """
        Complete resume-job matching
        """
        # Extract sections
        resume_sections = self.extract_resume_sections(resume_text)
        
        # Extract skills from resume
        from app.utils.resume_parser import SkillExtractor
        skill_extractor = SkillExtractor()
        resume_skills = skill_extractor.extract_skills(resume_text)
        
        # Extract skills from job description
        job_skills = skill_extractor.extract_skills(job_description)
        
        # Match skills semantically
        skill_match = self.match_skills_semantic(resume_skills, job_skills)
        
        # Match experience
        exp_match = self.match_experience(resume_sections, job_description)
        
        # Match education
        edu_match = self.match_education(resume_sections, job_description)
        
        # Overall score with section weights
        overall_score = (
            self.section_weights['skills'] * skill_match['score'] +
            self.section_weights['experience'] * exp_match['score'] +
            self.section_weights['education'] * edu_match['score']
        )
        
        # Overall similarity (full document)
        full_similarity = self.semantic_similarity(resume_text[:1000], job_description[:1000])
        
        # Combine with overall similarity
        final_score = overall_score * 0.7 + full_similarity * 0.3
        
        return {
            'overall_score': round(final_score * 100, 1),
            'overall_match_percentage': round(final_score * 100, 1),
            'category_scores': {
                'skills': {
                    'score': round(skill_match['score'] * 100, 1),
                    'matched': skill_match['matched'][:10],
                    'missing': skill_match['missing'][:10],
                    'partial': skill_match['partial_matches'][:5]
                },
                'experience': {
                    'score': round(exp_match['score'] * 100, 1),
                    'candidate_years': exp_match['candidate_years'],
                    'required_years': exp_match['required_years']
                },
                'education': {
                    'score': round(edu_match['score'] * 100, 1),
                    'candidate_degree': edu_match['candidate_degree'],
                    'required_degree': edu_match['required_degree']
                }
            },
            'semantic_similarity': round(full_similarity * 100, 1),
            'recommendations': self._generate_recommendations(skill_match, exp_match, edu_match)
        }
    
    def _generate_recommendations(self, skill_match, exp_match, edu_match) -> List[str]:
        """Generate recommendations based on gaps"""
        recommendations = []
        
        # Skill recommendations
        if skill_match['missing']:
            missing_str = ', '.join(skill_match['missing'][:5])
            recommendations.append(f"Learn these missing skills: {missing_str}")
        
        if skill_match['partial_matches']:
            for p in skill_match['partial_matches'][:2]:
                recommendations.append(
                    f"Your {p['resume_skill']} is similar to required {p['job_skill']} "
                    f"(similarity: {p['similarity']:.0%})"
                )
        
        # Experience recommendations
        if exp_match['candidate_years'] < exp_match['required_years']:
            recommendations.append(
                f"Gain {exp_match['required_years'] - exp_match['candidate_years']} more years of experience"
            )
        
        # Education recommendations
        if edu_match['required_degree'] and edu_match['required_degree'] != edu_match['candidate_degree']:
            recommendations.append(
                f"Consider higher education in {edu_match['required_degree']}"
            )
        
        return recommendations[:5]  # Top 5 recommendations
    
    def rank_candidates(self, resumes: List[Dict], job_description: str) -> List[Dict]:
        """
        Rank multiple candidates for a job
        """
        ranked = []
        
        for resume in resumes:
            resume_text = resume.get('text', '')
            if not resume_text and 'file_path' in resume:
                # Extract text from file
                from app.utils.resume_parser import ResumeParser
                parser = ResumeParser()
                if resume['file_path'].endswith('.pdf'):
                    resume_text = parser.extract_text_from_pdf(resume['file_path'])
                else:
                    resume_text = parser.extract_text_from_docx(resume['file_path'])
            
            match_result = self.match_job_description(resume_text, job_description)
            
            ranked.append({
                'candidate_id': resume.get('id'),
                'name': resume.get('name'),
                'match_score': match_result['overall_score'],
                'details': match_result['category_scores'],
                'recommendations': match_result['recommendations']
            })
        
        # Sort by match score
        ranked.sort(key=lambda x: x['match_score'], reverse=True)
        
        return ranked


# Wrapper function for easy use
def create_matcher():
    """
    Create a resume-job matcher instance
    """
    return ResumeJobMatcher()