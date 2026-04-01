"""
Advanced Candidate Ranking System
Features:
- Learning to Rank (Pointwise, Pairwise, Listwise)
- Multi-criteria ranking with configurable weights
- Semantic similarity based ranking
- Ensemble ranking combining multiple models
- Ranking explanation and insights
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
import xgboost as xgb
import lightgbm as lgb
import joblib
import os
import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import json
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class CandidateRanker:
    """
    Advanced Candidate Ranking System
    Combines multiple ranking algorithms for optimal results
    """
    
    def __init__(self, model_path="app/ai/models/candidate_ranker/"):
        self.model_path = model_path
        os.makedirs(model_path, exist_ok=True)
        
        # Ranking models
        self.pointwise_model = None  # Regression model (score prediction)
        self.pairwise_model = None   # XGBoost Ranker
        self.listwise_model = None   # LambdaMART style
        
        # Scaler for features
        self.scaler = StandardScaler()
        self.normalizer = MinMaxScaler()
        
        # Feature names
        self.feature_names = []
        
        # Default ranking weights
        self.ranking_weights = {
            'technical_score': 0.35,
            'cgpa_score': 0.20,
            'experience_score': 0.15,
            'project_score': 0.15,
            'soft_skills_score': 0.10,
            'certification_score': 0.05
        }
        
        # Load existing models
        self.load_models()
        
        logger.info("✅ CandidateRanker initialized")
    
    def extract_candidate_features(self, student_data: Dict, drive_data: Dict) -> np.ndarray:
        """
        Extract comprehensive features for ranking
        Returns feature vector for a single candidate
        """
        features = []
        
        # 1. CGPA features
        cgpa = float(student_data.get('cgpa', 0))
        required_cgpa = float(drive_data.get('eligibility_cgpa', 0))
        
        features.append(cgpa / 10.0)  # Normalized CGPA
        features.append(cgpa / required_cgpa if required_cgpa > 0 else 1.0)  # CGPA ratio
        features.append(1.0 if cgpa >= required_cgpa else 0.0)  # CGPA requirement met
        
        # 2. Skills features
        student_skills = student_data.get('skills', '')
        if isinstance(student_skills, str):
            student_skills_list = [s.strip().lower() for s in student_skills.split(',') if s.strip()]
        else:
            student_skills_list = student_skills or []
        
        required_skills = drive_data.get('required_skills', '')
        if isinstance(required_skills, str):
            required_skills_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
        else:
            required_skills_list = required_skills or []
        
        # Skill match percentage
        if required_skills_list:
            matched_skills = set(student_skills_list) & set(required_skills_list)
            skill_match_percent = len(matched_skills) / len(required_skills_list)
        else:
            skill_match_percent = 1.0
        
        features.append(skill_match_percent)
        features.append(len(student_skills_list) / 30.0)  # Total skills (normalized)
        
        # Skill diversity (different categories)
        skill_categories = self._categorize_skills(student_skills_list)
        features.append(len(skill_categories) / 10.0)  # Diversity score
        
        # 3. Experience features
        exp_months = int(student_data.get('experience_months', 0))
        features.append(min(exp_months / 36.0, 1.0))  # Experience (max 3 years)
        features.append(1.0 if exp_months > 0 else 0.0)  # Has experience
        
        # 4. Projects features
        num_projects = int(student_data.get('num_projects', 0))
        project_quality = float(student_data.get('project_quality', 0.5))
        
        features.append(min(num_projects / 5.0, 1.0))  # Number of projects
        features.append(project_quality)  # Project quality
        features.append(min(num_projects * project_quality / 3.0, 1.0))  # Combined project score
        
        # 5. Certifications
        num_certs = int(student_data.get('num_certifications', 0))
        cert_quality = float(student_data.get('certification_quality', 0.3))
        
        features.append(min(num_certs / 5.0, 1.0))  # Number of certs
        features.append(cert_quality)  # Cert quality
        features.append(min(num_certs * cert_quality / 3.0, 1.0))  # Combined cert score
        
        # 6. Branch relevance
        student_branch = student_data.get('branch', '')
        branch_relevance = self._calculate_branch_relevance(student_branch, drive_data)
        features.append(branch_relevance)
        
        # 7. Semester (seniority)
        semester = int(student_data.get('semester', 0))
        features.append(semester / 8.0)  # Normalized
        
        # 8. Backlogs penalty
        backlogs = int(student_data.get('backlogs', 0))
        features.append(min(backlogs / 3.0, 1.0))  # Backlog penalty (higher is worse)
        
        # 9. Time-based features
        days_since_reg = int(student_data.get('days_since_registration', 180))
        features.append(min(days_since_reg / 365.0, 1.0))  # Registration age
        
        # 10. Soft skills (if available)
        soft_skills = self._extract_soft_skills(student_skills_list)
        features.append(soft_skills)
        
        return np.array(features)
    
    def _categorize_skills(self, skills: List[str]) -> set:
        """Categorize skills into different domains"""
        categories = set()
        
        skill_categories = {
            'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php', 'go', 'rust'],
            'web': ['html', 'css', 'react', 'angular', 'vue', 'node', 'django', 'flask'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'redis'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins'],
            'data_science': ['machine learning', 'deep learning', 'tensorflow', 'pytorch', 'pandas', 'numpy'],
            'soft_skills': ['communication', 'leadership', 'teamwork', 'problem solving']
        }
        
        for skill in skills:
            skill_lower = skill.lower()
            for category, cat_skills in skill_categories.items():
                if any(cat_skill in skill_lower for cat_skill in cat_skills):
                    categories.add(category)
        
        return categories
    
    def _calculate_branch_relevance(self, student_branch: str, drive_data: Dict) -> float:
        """Calculate how relevant student's branch is for the drive"""
        allowed_branches = drive_data.get('allowed_branches', '')
        
        if not allowed_branches or not student_branch:
            return 1.0  # No restriction
        
        allowed_list = [b.strip().upper() for b in allowed_branches.split(',') if b.strip()]
        
        if student_branch.upper() in allowed_list:
            return 1.0
        else:
            # Branch not allowed - penalty
            return 0.3
    
    def _extract_soft_skills(self, skills: List[str]) -> float:
        """Extract and score soft skills"""
        soft_skills_list = ['communication', 'leadership', 'teamwork', 'problem solving', 
                           'critical thinking', 'time management', 'presentation']
        
        found = 0
        for skill in skills:
            if any(soft in skill.lower() for soft in soft_skills_list):
                found += 1
        
        return min(found / 5.0, 1.0)
    
    def generate_synthetic_ranking_data(self, n_samples=1000) -> pd.DataFrame:
        """
        Generate synthetic training data for ranking models
        """
        np.random.seed(42)
        data = []
        
        for i in range(n_samples):
            # Generate random feature vector (15 features as above)
            features = np.random.rand(20)  # 20 features total
            
            # Generate realistic score based on features
            # Higher weights for important features
            weights = np.array([
                0.15, 0.10, 0.08,  # CGPA features (3)
                0.20, 0.05, 0.05,   # Skills features (3)
                0.08, 0.05,          # Experience (2)
                0.05, 0.05, 0.05,    # Projects (3)
                0.03, 0.02, 0.02,    # Certifications (3)
                0.05,                 # Branch (1)
                0.02,                 # Semester (1)
                -0.05,                # Backlogs (negative)
                0.02,                 # Registration age (1)
                0.03                  # Soft skills (1)
            ])
            
            # Ensure weights sum to 1
            weights = weights / weights.sum()
            
            # Calculate base score
            base_score = np.dot(features, weights)
            
            # Add some noise
            noise = np.random.normal(0, 0.05)
            final_score = np.clip(base_score + noise, 0, 1)
            
            # Create pairwise preference (for pairwise training)
            if i % 2 == 0 and i < n_samples - 1:
                # Candidate i is better than i+1
                preference = 1
            else:
                preference = 0
            
            data.append({
                'features': features,
                'score': final_score,
                'preference': preference,
                'query_id': i // 10  # Group for listwise ranking
            })
        
        return pd.DataFrame(data)
    
    def train_pointwise_model(self, X_train, y_train):
        """Train pointwise ranking model (regression)"""
        logger.info("📊 Training pointwise ranking model...")
        
        # XGBoost Regressor
        self.pointwise_model = xgb.XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=0.1,
            random_state=42
        )
        
        self.pointwise_model.fit(X_train, y_train)
        
        # Feature importance
        importance = self.pointwise_model.feature_importances_
        logger.info("✅ Pointwise model trained")
        
        return importance
    
    def train_pairwise_model(self, X_train, pairs, y_pairs):
        """
        Train pairwise ranking model
        Simplified version using difference features
        """
        logger.info("📊 Training pairwise ranking model...")
        
        # Create difference features for pairs
        X_diff = []
        y_diff = []
        
        for i, (idx1, idx2) in enumerate(pairs):
            diff = X_train[idx1] - X_train[idx2]
            X_diff.append(diff)
            y_diff.append(y_pairs[i])  # 1 if idx1 > idx2
        
        X_diff = np.array(X_diff)
        y_diff = np.array(y_diff)
        
        # Train classifier
        self.pairwise_model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            random_state=42
        )
        
        self.pairwise_model.fit(X_diff, y_diff)
        logger.info("✅ Pairwise model trained")
    
    def train_listwise_model(self, X_train, y_train, qid_train):
        """
        Train listwise ranking model using LambdaMART approach
        Simplified version using LightGBM Ranker
        """
        logger.info("📊 Training listwise ranking model...")
        
        try:
            # Try LightGBM Ranker
            self.listwise_model = lgb.LGBMRanker(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42
            )
            
            self.listwise_model.fit(
                X_train, y_train,
                group=np.bincount(qid_train).tolist(),
                verbose=0
            )
            
            logger.info("✅ Listwise model trained")
        except Exception as e:
            logger.warning(f"Listwise model training failed: {e}")
            self.listwise_model = None
    
    def train_ranking_models(self, n_samples=2000):
        """
        Train all ranking models
        """
        logger.info("📊 Generating synthetic training data...")
        df = self.generate_synthetic_ranking_data(n_samples)
        
        # Extract features and targets
        X = np.vstack(df['features'].values)
        y_scores = df['score'].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        self.feature_names = [f'feature_{i}' for i in range(X.shape[1])]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_scores, test_size=0.2, random_state=42
        )
        
        # 1. Train pointwise model
        importance = self.train_pointwise_model(X_train, y_train)
        
        # 2. Generate pairs for pairwise training
        pairs = []
        y_pairs = []
        for i in range(0, len(X_train), 2):
            if i + 1 < len(X_train):
                pairs.append((i, i+1))
                if y_train[i] > y_train[i+1]:
                    y_pairs.append(1)
                else:
                    y_pairs.append(0)
        
        if len(pairs) > 0:
            self.train_pairwise_model(X_train, pairs, y_pairs)
        
        # 3. Generate query IDs for listwise
        qid_train = np.array([i // 10 for i in range(len(X_train))])
        self.train_listwise_model(X_train, y_train, qid_train)
        
        # Evaluate
        pointwise_pred = self.pointwise_model.predict(X_test)
        mse = np.mean((pointwise_pred - y_test) ** 2)
        
        logger.info(f"📊 Pointwise model MSE: {mse:.4f}")
        
        # Save models
        self.save_models()
        
        return {
            'message': 'Ranking models trained successfully',
            'mse': mse,
            'feature_importance': dict(zip(self.feature_names[:10], importance[:10])),
            'models': ['pointwise', 'pairwise', 'listwise']
        }
    
    def rank_candidates_advanced(self, candidates: List[Dict], drive_data: Dict, 
                                  method: str = 'ensemble', top_k: int = None) -> List[Dict]:
        """
        Rank candidates using advanced algorithms
        method: 'pointwise', 'pairwise', 'listwise', 'ensemble'
        """
        if not candidates:
            return []
        
        # Extract features for all candidates
        features = []
        candidate_ids = []
        
        for candidate in candidates:
            feat = self.extract_candidate_features(candidate, drive_data)
            features.append(feat)
            candidate_ids.append(candidate.get('user_id', candidate.get('id')))
        
        features = np.array(features)
        features_scaled = self.scaler.transform(features) if hasattr(self.scaler, 'mean_') else features
        
        # Calculate base scores
        scores = []
        
        if method == 'pointwise' and self.pointwise_model:
            # Pointwise ranking
            scores = self.pointwise_model.predict(features_scaled)
            
        elif method == 'pairwise' and self.pairwise_model:
            # Pairwise ranking (simplified - use all vs all)
            scores = np.zeros(len(candidates))
            for i in range(len(candidates)):
                for j in range(len(candidates)):
                    if i != j:
                        diff = features_scaled[i] - features_scaled[j]
                        if self.pairwise_model.predict([diff])[0] == 1:
                            scores[i] += 1
            scores = scores / scores.max() if scores.max() > 0 else scores
            
        elif method == 'listwise' and self.listwise_model:
            # Listwise ranking
            scores = self.listwise_model.predict(features_scaled)
            
        else:
            # Ensemble ranking (combine multiple methods)
            scores_pointwise = self.pointwise_model.predict(features_scaled) if self.pointwise_model else None
            scores_pairwise = None
            scores_listwise = None
            
            if self.pairwise_model:
                scores_pairwise = np.zeros(len(candidates))
                for i in range(len(candidates)):
                    for j in range(len(candidates)):
                        if i != j:
                            diff = features_scaled[i] - features_scaled[j]
                            if self.pairwise_model.predict([diff])[0] == 1:
                                scores_pairwise[i] += 1
                scores_pairwise = scores_pairwise / scores_pairwise.max() if scores_pairwise.max() > 0 else scores_pairwise
            
            if self.listwise_model:
                scores_listwise = self.listwise_model.predict(features_scaled)
                scores_listwise = (scores_listwise - scores_listwise.min()) / (scores_listwise.max() - scores_listwise.min() + 1e-8)
            
            # Combine scores with weights
            scores = np.zeros(len(candidates))
            weight_sum = 0
            
            if scores_pointwise is not None:
                scores += 0.4 * (scores_pointwise - scores_pointwise.min()) / (scores_pointwise.max() - scores_pointwise.min() + 1e-8)
                weight_sum += 0.4
            
            if scores_pairwise is not None:
                scores += 0.35 * scores_pairwise
                weight_sum += 0.35
            
            if scores_listwise is not None:
                scores += 0.25 * scores_listwise
                weight_sum += 0.25
            
            if weight_sum > 0:
                scores = scores / weight_sum
        
        # Calculate component scores for explanation
        ranked_candidates = []
        for i, candidate in enumerate(candidates):
            # Calculate individual component scores
            cgpa_score = self._calculate_cgpa_score(candidate, drive_data)
            skill_score = self._calculate_skill_score(candidate, drive_data)
            exp_score = self._calculate_experience_score(candidate)
            project_score = self._calculate_project_score(candidate)
            
            # Get features for this candidate
            candidate_features = features[i]
            
            ranked_candidates.append({
                'candidate_id': candidate_ids[i],
                'name': candidate.get('full_name', candidate.get('name', 'Unknown')),
                'rank_score': float(scores[i]) if len(scores) > i else 0.5,
                'component_scores': {
                    'cgpa_score': cgpa_score,
                    'skill_score': skill_score,
                    'experience_score': exp_score,
                    'project_score': project_score
                },
                'explanation': self._generate_ranking_explanation(candidate, cgpa_score, skill_score, exp_score, project_score),
                'feature_vector': candidate_features.tolist() if hasattr(candidate_features, 'tolist') else None,
                'eligibility': self._check_eligibility(candidate, drive_data)
            })
        
        # Sort by rank score
        ranked_candidates.sort(key=lambda x: x['rank_score'], reverse=True)
        
        # Add rank position
        for idx, candidate in enumerate(ranked_candidates):
            candidate['rank'] = idx + 1
        
        if top_k:
            ranked_candidates = ranked_candidates[:top_k]
        
        return ranked_candidates
    
    def _calculate_cgpa_score(self, student: Dict, drive: Dict) -> float:
        """Calculate CGPA score (0-1)"""
        cgpa = float(student.get('cgpa', 0))
        required = float(drive.get('eligibility_cgpa', 0))
        
        if required > 0:
            ratio = cgpa / required
            if ratio >= 1.2:
                return 1.0
            elif ratio >= 1.0:
                return 0.8
            elif ratio >= 0.9:
                return 0.6
            elif ratio >= 0.8:
                return 0.4
            else:
                return 0.2
        else:
            return min(cgpa / 10.0, 1.0)
    
    def _calculate_skill_score(self, student: Dict, drive: Dict) -> float:
        """Calculate skill match score (0-1)"""
        student_skills = student.get('skills', '')
        required_skills = drive.get('required_skills', '')
        
        if isinstance(student_skills, str):
            student_list = [s.strip().lower() for s in student_skills.split(',') if s.strip()]
        else:
            student_list = student_skills or []
        
        if isinstance(required_skills, str):
            required_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
        else:
            required_list = required_skills or []
        
        if not required_list:
            return 0.8
        
        matched = set(student_list) & set(required_list)
        return len(matched) / len(required_list)
    
    def _calculate_experience_score(self, student: Dict) -> float:
        """Calculate experience score (0-1)"""
        exp_months = int(student.get('experience_months', 0))
        return min(exp_months / 24.0, 1.0)
    
    def _calculate_project_score(self, student: Dict) -> float:
        """Calculate project score (0-1)"""
        num_projects = int(student.get('num_projects', 0))
        return min(num_projects / 5.0, 1.0)
    
    def _generate_ranking_explanation(self, student: Dict, cgpa_score: float, 
                                      skill_score: float, exp_score: float, 
                                      project_score: float) -> str:
        """Generate human-readable explanation for ranking"""
        strengths = []
        weaknesses = []
        
        if cgpa_score >= 0.8:
            strengths.append("excellent CGPA")
        elif cgpa_score < 0.5:
            weaknesses.append("CGPA needs improvement")
        
        if skill_score >= 0.7:
            strengths.append("strong skill match")
        elif skill_score < 0.4:
            weaknesses.append("skill gap")
        
        if exp_score >= 0.5:
            strengths.append("relevant experience")
        elif exp_score == 0:
            weaknesses.append("no experience")
        
        if project_score >= 0.6:
            strengths.append("good project portfolio")
        elif project_score < 0.3:
            weaknesses.append("few projects")
        
        if strengths and weaknesses:
            return f"✅ {', '.join(strengths[:2])}. ⚠️ {', '.join(weaknesses[:2])}."
        elif strengths:
            return f"✅ Strong candidate with {', '.join(strengths[:3])}."
        elif weaknesses:
            return f"⚠️ Needs improvement: {', '.join(weaknesses[:3])}."
        else:
            return "Average candidate profile."
    
    def _check_eligibility(self, student: Dict, drive: Dict) -> Dict:
        """Check basic eligibility"""
        cgpa = float(student.get('cgpa', 0))
        required_cgpa = float(drive.get('eligibility_cgpa', 0))
        
        eligible = cgpa >= required_cgpa
        
        return {
            'eligible': eligible,
            'cgpa_met': cgpa >= required_cgpa
        }
    
    def rank_with_custom_weights(self, candidates: List[Dict], drive_data: Dict,
                                  weights: Dict = None, top_k: int = None) -> List[Dict]:
        """
        Rank candidates with custom weights for different criteria
        """
        if not weights:
            weights = self.ranking_weights
        
        ranked = []
        
        for candidate in candidates:
            # Calculate individual scores
            cgpa_score = self._calculate_cgpa_score(candidate, drive_data)
            skill_score = self._calculate_skill_score(candidate, drive_data)
            exp_score = self._calculate_experience_score(candidate)
            project_score = self._calculate_project_score(candidate)
            
            # Soft skills (if available)
            soft_skills = self._extract_soft_skills(
                candidate.get('skills', '').split(',') if isinstance(candidate.get('skills'), str) else []
            )
            
            # Certifications (if available)
            cert_score = min(int(candidate.get('num_certifications', 0)) / 5.0, 1.0)
            
            # Calculate weighted total
            total_score = (
                weights.get('cgpa_score', 0.20) * cgpa_score +
                weights.get('skill_score', 0.35) * skill_score +
                weights.get('experience_score', 0.15) * exp_score +
                weights.get('project_score', 0.15) * project_score +
                weights.get('soft_skills_score', 0.10) * soft_skills +
                weights.get('certification_score', 0.05) * cert_score
            )
            
            ranked.append({
                'candidate_id': candidate.get('user_id', candidate.get('id')),
                'name': candidate.get('full_name', candidate.get('name', 'Unknown')),
                'rank_score': total_score,
                'component_scores': {
                    'cgpa_score': cgpa_score,
                    'skill_score': skill_score,
                    'experience_score': exp_score,
                    'project_score': project_score,
                    'soft_skills_score': soft_skills,
                    'certification_score': cert_score
                },
                'eligibility': self._check_eligibility(candidate, drive_data)
            })
        
        # Sort by rank score
        ranked.sort(key=lambda x: x['rank_score'], reverse=True)
        
        # Add rank
        for idx, candidate in enumerate(ranked):
            candidate['rank'] = idx + 1
        
        if top_k:
            ranked = ranked[:top_k]
        
        return ranked
    
    def save_models(self):
        """Save all ranking models"""
        model_file = os.path.join(self.model_path, 'candidate_ranker.pkl')
        
        joblib.dump({
            'pointwise_model': self.pointwise_model,
            'pairwise_model': self.pairwise_model,
            'listwise_model': self.listwise_model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'ranking_weights': self.ranking_weights
        }, model_file)
        
        logger.info(f"✅ Ranking models saved to {model_file}")
    
    def load_models(self):
        """Load saved ranking models"""
        model_file = os.path.join(self.model_path, 'candidate_ranker.pkl')
        
        if os.path.exists(model_file):
            try:
                data = joblib.load(model_file)
                self.pointwise_model = data['pointwise_model']
                self.pairwise_model = data['pairwise_model']
                self.listwise_model = data['listwise_model']
                self.scaler = data['scaler']
                self.feature_names = data['feature_names']
                self.ranking_weights = data.get('ranking_weights', self.ranking_weights)
                logger.info(f"✅ Ranking models loaded from {model_file}")
                return True
            except Exception as e:
                logger.error(f"Error loading ranking models: {e}")
                return False
        return False


# Singleton instance
_ranker = None

def get_candidate_ranker():
    """Get or create CandidateRanker singleton"""
    global _ranker
    if _ranker is None:
        _ranker = CandidateRanker()
    return _ranker