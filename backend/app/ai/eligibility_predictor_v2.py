# app/ai/eligibility_predictor_v2.py - COMPLETE FIXED VERSION

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report
import xgboost as xgb
import lightgbm as lgb
import joblib
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import random
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class EligibilityPredictorV2:
    """
    Advanced Eligibility Prediction Model
    Features: XGBoost/LightGBM, Advanced Feature Engineering, Multi-class Classification
    """
    
    def __init__(self, model_path="app/ai/models/eligibility_v2/"):
        self.model_path = model_path
        os.makedirs(model_path, exist_ok=True)
        
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_names = []
        self.model_type = 'xgboost'
        self.class_mapping = {}
        self.inverse_class_mapping = {}
        
        # Feature weights for different factors
        self.feature_weights = {
            'cgpa': 0.25,
            'cgpa_trend': 0.10,
            'skill_match': 0.20,
            'skill_diversity': 0.10,
            'project_complexity': 0.10,
            'certification_quality': 0.10,
            'experience': 0.10,
            'backlogs': 0.05
        }
        
        # Hardcoded class mapping as backup
        self.default_class_mapping = {0: 'high', 1: 'low', 2: 'medium'}
        self.default_inverse_mapping = {'high': 0, 'low': 1, 'medium': 2}
        
        # Try to load existing model
        self.load_model()
        
        logger.info("✅ EligibilityPredictorV2 initialized")
    
    def generate_synthetic_data(self, n_samples=2000) -> pd.DataFrame:
        """Generate enhanced synthetic training data with advanced features"""
        
        data = []
        
        branches = ['CSE', 'IT', 'ECE', 'EEE', 'MECH', 'CIVIL', 'AI', 'DATA', 'CS', 'AIML']
        semesters = [3, 4, 5, 6, 7, 8]
        
        # Skill pools
        programming_skills = ['Python', 'Java', 'C++', 'JavaScript', 'C#', 'Ruby', 'Go', 'Rust']
        web_skills = ['HTML', 'CSS', 'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask']
        db_skills = ['SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Cassandra']
        cloud_skills = ['AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Terraform']
        ds_skills = ['Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Pandas', 'NumPy']
        soft_skills = ['Communication', 'Leadership', 'Teamwork', 'Problem Solving']
        
        all_skills = programming_skills + web_skills + db_skills + cloud_skills + ds_skills + soft_skills
        
        for i in range(n_samples):
            # Basic info
            branch = random.choice(branches)
            semester = random.choice(semesters)
            
            # CGPA with realistic distribution
            if branch in ['CSE', 'IT', 'AI', 'DATA', 'AIML']:
                cgpa = round(random.uniform(6.0, 10.0), 2)
            else:
                cgpa = round(random.uniform(5.5, 9.5), 2)
            
            # CGPA trend (improving, stable, declining)
            if cgpa > 8.5:
                cgpa_trend = random.choice(['improving', 'stable'])
            elif cgpa < 6.5:
                cgpa_trend = random.choice(['stable', 'declining'])
            else:
                cgpa_trend = random.choice(['improving', 'stable', 'declining'])
            
            cgpa_trend_score = {
                'improving': 1.0,
                'stable': 0.7,
                'declining': 0.3
            }[cgpa_trend]
            
            # Skills
            num_skills = random.randint(3, 20)
            student_skills = random.sample(all_skills, min(num_skills, len(all_skills)))
            
            # Skill diversity (different categories)
            skill_categories = set()
            for skill in student_skills:
                if skill in programming_skills:
                    skill_categories.add('programming')
                elif skill in web_skills:
                    skill_categories.add('web')
                elif skill in db_skills:
                    skill_categories.add('database')
                elif skill in cloud_skills:
                    skill_categories.add('cloud')
                elif skill in ds_skills:
                    skill_categories.add('datascience')
                elif skill in soft_skills:
                    skill_categories.add('soft')
            
            skill_diversity_score = len(skill_categories) / 6.0
            
            # Projects
            num_projects = random.randint(0, 5)
            project_complexity = 0
            
            for _ in range(num_projects):
                tech_count = random.randint(1, 5)
                if tech_count >= 4:
                    project_complexity += 0.3
                elif tech_count >= 2:
                    project_complexity += 0.2
                else:
                    project_complexity += 0.1
            
            project_complexity = min(project_complexity, 1.0)
            
            # Certifications
            num_certs = random.randint(0, 4)
            cert_quality = 0
            
            cert_levels = ['beginner', 'intermediate', 'advanced']
            for _ in range(num_certs):
                level = random.choice(cert_levels)
                if level == 'advanced':
                    cert_quality += 0.4
                elif level == 'intermediate':
                    cert_quality += 0.25
                else:
                    cert_quality += 0.1
            
            cert_quality = min(cert_quality, 1.0)
            
            # Experience (months)
            has_experience = random.choice([0, 1])
            experience_months = random.randint(0, 24) if has_experience else 0
            experience_score = min(experience_months / 24.0, 1.0)
            
            # Backlogs
            backlogs = random.randint(0, 3)
            
            # Job requirements
            required_cgpa = round(random.uniform(6.0, 8.5), 2)
            
            # Required skills (5-10 skills)
            num_required = random.randint(5, 10)
            required_skills = random.sample(all_skills, min(num_required, len(all_skills)))
            
            # Skill match calculation
            matched_skills = set(student_skills) & set(required_skills)
            skill_match_percent = len(matched_skills) / len(required_skills) * 100 if required_skills else 0
            
            # Calculate overall eligibility score (0-100)
            eligibility_score = 0
            
            cgpa_contrib = min(cgpa / required_cgpa, 1.5) * self.feature_weights['cgpa'] * 100
            eligibility_score += cgpa_contrib
            eligibility_score += cgpa_trend_score * self.feature_weights['cgpa_trend'] * 100
            eligibility_score += (skill_match_percent / 100) * self.feature_weights['skill_match'] * 100
            eligibility_score += skill_diversity_score * self.feature_weights['skill_diversity'] * 100
            eligibility_score += project_complexity * self.feature_weights['project_complexity'] * 100
            eligibility_score += cert_quality * self.feature_weights['certification_quality'] * 100
            eligibility_score += experience_score * self.feature_weights['experience'] * 100
            
            backlog_penalty = max(0, (backlogs - 1) * 5)
            eligibility_score -= backlog_penalty
            eligibility_score = max(0, min(100, eligibility_score))
            
            # Determine class based on score
            if eligibility_score >= 70:
                eligibility_class = 'high'
            elif eligibility_score >= 40:
                eligibility_class = 'medium'
            else:
                eligibility_class = 'low'
            
            # Add some noise for realism
            if random.random() < 0.05:
                if eligibility_class == 'high':
                    eligibility_class = 'medium'
                elif eligibility_class == 'medium':
                    eligibility_class = random.choice(['high', 'low'])
                else:
                    eligibility_class = 'medium'
            
            data.append({
                'cgpa': cgpa,
                'cgpa_trend': cgpa_trend_score,
                'branch': branch,
                'semester': semester,
                'num_skills': len(student_skills),
                'skill_match_percent': skill_match_percent,
                'skill_diversity': skill_diversity_score,
                'project_complexity': project_complexity,
                'certification_quality': cert_quality,
                'has_experience': has_experience,
                'experience_months': experience_months,
                'experience_score': experience_score,
                'backlogs': backlogs,
                'required_cgpa': required_cgpa,
                'required_skills_count': len(required_skills),
                'eligibility_score': eligibility_score,
                'eligibility_class': eligibility_class
            })
        
        return pd.DataFrame(data)
    
    def prepare_features(self, student_data: Dict, job_data: Dict) -> np.ndarray:
        """Prepare enhanced features for prediction - 13 features version"""
    
        features = []
    
    # 1. CGPA (normalized)
        cgpa = float(student_data.get('cgpa', 0))
        features.append(cgpa / 10.0)
    
    # 2. CGPA trend
        cgpa_trend = float(student_data.get('cgpa_trend', 0.7))
        features.append(cgpa_trend)
    
    # 3. Branch (encoded) - FIXED
        branch = student_data.get('branch', 'CSE')
        branch_encoded = 0
    
        if 'branch' in self.label_encoders:
            try:
                possible_branches = self.label_encoders['branch'].classes_
                if branch in possible_branches:
                    branch_encoded = self.label_encoders['branch'].transform([branch])[0]
                else:
                    branch_encoded = 0
            except:
                branch_encoded = 0
    
        features.append(branch_encoded / 10.0)  # Normalize
    
    # 4. Semester
        semester = int(student_data.get('semester', 0))
        features.append(semester / 8.0)
    
    # 5. Number of skills
        student_skills = student_data.get('skills', '')
        if isinstance(student_skills, str):
            student_skills_list = [s.strip().lower() for s in student_skills.split(',') if s.strip()]
        else:
            student_skills_list = student_skills or []
        features.append(len(student_skills_list) / 20.0)
    
    # 6. Skill match percentage
        required_skills = job_data.get('required_skills', '')
        if isinstance(required_skills, str):
            required_skills_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
        else:
            required_skills_list = required_skills or []
    
        if required_skills_list:
            matched = set(student_skills_list) & set(required_skills_list)
            skill_match = len(matched) / len(required_skills_list) if required_skills_list else 0
        else:
            skill_match = 1.0
        features.append(skill_match)
    
    # 7. Skill diversity
        skill_diversity = float(student_data.get('skill_diversity', 0.5))
        features.append(skill_diversity)
    
    # 8. Project complexity
        project_complexity = float(student_data.get('project_complexity', 0.5))
        features.append(project_complexity)
    
    # 9. Certification quality
        cert_quality = float(student_data.get('certification_quality', 0.3))
        features.append(cert_quality)
    
    # 10. Experience (has_experience)
        has_experience = int(student_data.get('has_experience', 0))
        features.append(has_experience)
    
    # 11. Experience score (experience_months normalized)
        exp_months = int(student_data.get('experience_months', 0))
        exp_score = min(exp_months / 24.0, 1.0)  # Max 24 months
        features.append(exp_score)

    # 12. Backlogs penalty
        backlogs = int(student_data.get('backlogs', 0))
        backlogs_penalty = min(backlogs / 3.0, 1.0)
        features.append(backlogs_penalty)
    
    # 13. Required CGPA normalized
        required_cgpa = float(job_data.get('eligibility_cgpa', 0))
        features.append(required_cgpa / 10.0)
    
    # Total features = 13 - matches training
    
        return np.array(features).reshape(1, -1)
    
    def train_model(self, model_type='xgboost', n_samples=2000, test_size=0.2):
        """Train enhanced eligibility model"""
        
        logger.info(f"📊 Generating {n_samples} synthetic samples...")
        df = self.generate_synthetic_data(n_samples)
        
        # Prepare features
        feature_columns = [
            'cgpa', 'cgpa_trend', 'num_skills', 'skill_match_percent', 
            'skill_diversity', 'project_complexity', 'certification_quality',
            'has_experience', 'experience_score', 'backlogs',
            'required_cgpa', 'required_skills_count'
        ]
        
        # Encode branch
        self.label_encoders['branch'] = LabelEncoder()
        df['branch_encoded'] = self.label_encoders['branch'].fit_transform(df['branch'])
        
        # Combine all features
        X = df[feature_columns + ['branch_encoded']].values
        y = df['eligibility_class'].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Encode string labels to numbers
        self.label_encoders['eligibility_class'] = LabelEncoder()
        y_train_encoded = self.label_encoders['eligibility_class'].fit_transform(y_train)
        y_test_encoded = self.label_encoders['eligibility_class'].transform(y_test)
        
        # Store class mapping for later use
        self.class_mapping = dict(zip(
            self.label_encoders['eligibility_class'].classes_,
            range(len(self.label_encoders['eligibility_class'].classes_))
        ))
        self.inverse_class_mapping = {v: k for k, v in self.class_mapping.items()}
        
        logger.info(f"📊 Class mapping: {self.class_mapping}")
        
        self.model_type = model_type
        self.feature_names = feature_columns + ['branch_encoded']
        
        # Train model based on type
        if model_type == 'xgboost':
            logger.info("🚀 Training XGBoost model...")
            self.model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                use_label_encoder=False,
                eval_metric='mlogloss'
            )
        else:
            logger.info("🚀 Training LightGBM model...")
            self.model = lgb.LGBMClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbosity=-1
            )
        
        # Train with encoded labels
        self.model.fit(X_train, y_train_encoded)
        
        # Predictions
        y_pred_encoded = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)
        
        # Convert back to original labels for metrics
        y_pred = self.label_encoders['eligibility_class'].inverse_transform(y_pred_encoded)
        
        # Metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted')
        recall = recall_score(y_test, y_pred, average='weighted')
        f1 = f1_score(y_test, y_pred, average='weighted')
        
        # Cross-validation
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        y_all_encoded = self.label_encoders['eligibility_class'].transform(y)
        cv_scores = cross_val_score(self.model, X_scaled, y_all_encoded, cv=cv, scoring='accuracy')
        
        # Feature importance
        importance = self.model.feature_importances_
        feature_importance = dict(zip(self.feature_names, importance))
        
        # Classification report
        class_report = classification_report(y_test, y_pred, output_dict=True)
        
        logger.info(f"\n📊 Model Performance:")
        logger.info(f"   Accuracy: {accuracy:.3f}")
        logger.info(f"   Precision: {precision:.3f}")
        logger.info(f"   Recall: {recall:.3f}")
        logger.info(f"   F1-Score: {f1:.3f}")
        logger.info(f"   CV Accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std()*2:.3f})")
        
        logger.info(f"\n📈 Feature Importance:")
        for name, imp in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"   {name}: {imp:.3f}")
        
        # Save model
        self.save_model()
        
        return {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'cv_mean': float(cv_scores.mean()),
            'cv_std': float(cv_scores.std()),
            'feature_importance': {str(k): float(v) for k, v in feature_importance.items()},
            'classification_report': class_report,  # Already dict
            'classes': [str(c) for c in self.class_mapping.keys()]
        }
    
    def predict(self, student_data: Dict, job_data: Dict) -> Dict:
        """
        Predict eligibility with class and probability - FIXED VERSION
        """
        
        if self.model is None:
            logger.warning("Model not trained. Training now...")
            self.train_model()
        
        try:
            # Prepare features
            features = self.prepare_features(student_data, job_data)
            features_scaled = self.scaler.transform(features)
            
            # Get prediction (returns encoded values 0, 1, 2)
            pred_encoded = self.model.predict(features_scaled)[0]
            pred_proba = self.model.predict_proba(features_scaled)[0]
            
            # FIX: Convert encoded number to class label using multiple methods
            pred_class = None
            
            # Method 1: Use inverse_class_mapping if available
            if hasattr(self, 'inverse_class_mapping') and isinstance(self.inverse_class_mapping, dict):
                if pred_encoded in self.inverse_class_mapping:
                    pred_class = self.inverse_class_mapping[pred_encoded]
            
            # Method 2: Use label_encoder if method 1 failed
            if pred_class is None and 'eligibility_class' in self.label_encoders:
                try:
                    pred_class = self.label_encoders['eligibility_class'].inverse_transform([pred_encoded])[0]
                except:
                    pass
            
            # Method 3: Use default hardcoded mapping
            if pred_class is None:
                # From your training output, classes were ['high', 'low', 'medium']
                # But order might be different, so let's check model.classes_
                if hasattr(self.model, 'classes_'):
                    # model.classes_ contains the encoded values in order
                    # For example, if model.classes_ = [0, 1, 2], then:
                    # index 0 -> class 0, index 1 -> class 1, etc.
                    class_order = self.model.classes_
                    if len(class_order) == 3:
                        # This is the safe mapping based on your actual training
                        # The classes are ['high', 'low', 'medium'] but encoded as 0,1,2
                        # We need to map encoded value to correct label
                        if pred_encoded == class_order[0]:
                            pred_class = 'high'
                        elif pred_encoded == class_order[1]:
                            pred_class = 'low'
                        elif pred_encoded == class_order[2]:
                            pred_class = 'medium'
                        else:
                            pred_class = 'medium'
                    else:
                        # Fallback
                        default_map = {0: 'high', 1: 'low', 2: 'medium'}
                        pred_class = default_map.get(pred_encoded, 'medium')
                else:
                    # Ultimate fallback
                    default_map = {0: 'high', 1: 'low', 2: 'medium'}
                    pred_class = default_map.get(pred_encoded, 'medium')
            
            # Get probability for predicted class
            class_idx = list(self.model.classes_).index(pred_encoded)
            probability = pred_proba[class_idx]
            
            # Calculate confidence
            sorted_proba = sorted(pred_proba, reverse=True)
            if len(sorted_proba) > 1:
                margin = sorted_proba[0] - sorted_proba[1]
                confidence = min(0.5 + margin, 0.95)
            else:
                confidence = 0.9
            
            # Calculate raw score
            score = self._calculate_eligibility_score(student_data, job_data)
            
            # Get feature contributions
            contributions = self._get_feature_contributions(student_data, job_data)
            
            # Create class probabilities with proper labels
            class_probs = {}
            for i, prob in enumerate(pred_proba):
                encoded_val = self.model.classes_[i]
                
                # Map encoded value to label
                if hasattr(self, 'inverse_class_mapping') and encoded_val in self.inverse_class_mapping:
                    label = self.inverse_class_mapping[encoded_val]
                else:
                    # Default mapping based on position
                    if i == 0:
                        label = 'high'
                    elif i == 1:
                        label = 'low'
                    else:
                        label = 'medium'
                
                class_probs[label] = float(prob)
            
            return {
                'class': pred_class,
                'probability': float(probability),
                'confidence': float(confidence),
                'score': score,
                'method': 'ml_v2',
                'model_type': self.model_type,
                'details': {
                    'predicted_class': pred_class,
                    'class_probabilities': class_probs,
                    'feature_contributions': contributions,
                    'recommendation': self._get_recommendation(pred_class, contributions)
                }
            }
            
        except Exception as e:
            logger.error(f"ML prediction error: {e}, falling back to rules")
            import traceback
            traceback.print_exc()
            return self.rule_based_prediction(student_data, job_data)
    
    def _calculate_eligibility_score(self, student_data: Dict, job_data: Dict) -> float:
        """Calculate raw eligibility score 0-100"""
        
        score = 0
        
        # CGPA (max 30 points)
        student_cgpa = float(student_data.get('cgpa', 0))
        required_cgpa = float(job_data.get('eligibility_cgpa', 0))
        
        if required_cgpa > 0:
            cgpa_ratio = student_cgpa / required_cgpa
            if cgpa_ratio >= 1.2:
                score += 30
            elif cgpa_ratio >= 1.0:
                score += 25
            elif cgpa_ratio >= 0.9:
                score += 15
            else:
                score += 5
        else:
            score += 20
        
        # Skills match (max 40 points)
        student_skills = student_data.get('skills', '')
        required_skills = job_data.get('required_skills', '')
        
        if isinstance(student_skills, str):
            student_skills_list = [s.strip().lower() for s in student_skills.split(',') if s.strip()]
        else:
            student_skills_list = student_skills or []
        
        if isinstance(required_skills, str):
            required_skills_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
        else:
            required_skills_list = required_skills or []
        
        if required_skills_list:
            matched = set(student_skills_list) & set(required_skills_list)
            match_percent = len(matched) / len(required_skills_list)
            score += match_percent * 40
        else:
            score += 20
        
        # Experience (max 15 points)
        exp_months = int(student_data.get('experience_months', 0))
        if exp_months >= 12:
            score += 15
        elif exp_months >= 6:
            score += 10
        elif exp_months >= 3:
            score += 5
        
        # Projects (max 15 points)
        projects = student_data.get('projects', [])
        if projects:
            project_score = min(len(projects) * 3, 15)
            score += project_score
        
        return min(score, 100)
    
    def _get_feature_contributions(self, student_data: Dict, job_data: Dict) -> Dict:
        """Get contribution of each feature to the prediction"""
        
        contributions = {}
        
        # CGPA contribution
        student_cgpa = float(student_data.get('cgpa', 0))
        required_cgpa = float(job_data.get('eligibility_cgpa', 0))
        
        if required_cgpa > 0:
            cgpa_ratio = student_cgpa / required_cgpa
            if cgpa_ratio >= 1.0:
                contributions['cgpa'] = 'positive'
            else:
                contributions['cgpa'] = 'negative'
        else:
            contributions['cgpa'] = 'neutral'
        
        # Skills contribution
        student_skills = student_data.get('skills', '')
        required_skills = job_data.get('required_skills', '')
        
        if isinstance(student_skills, str):
            student_skills_list = [s.strip().lower() for s in student_skills.split(',') if s.strip()]
        else:
            student_skills_list = student_skills or []
        
        if isinstance(required_skills, str):
            required_skills_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
        else:
            required_skills_list = required_skills or []
        
        if required_skills_list:
            matched = set(student_skills_list) & set(required_skills_list)
            match_percent = len(matched) / len(required_skills_list)
            
            if match_percent >= 0.7:
                contributions['skills'] = 'positive'
            elif match_percent >= 0.4:
                contributions['skills'] = 'neutral'
            else:
                contributions['skills'] = 'negative'
        else:
            contributions['skills'] = 'neutral'
        
        # Experience contribution
        exp_months = int(student_data.get('experience_months', 0))
        if exp_months >= 6:
            contributions['experience'] = 'positive'
        elif exp_months >= 3:
            contributions['experience'] = 'neutral'
        else:
            contributions['experience'] = 'negative'
        
        return contributions
    
    def _get_recommendation(self, pred_class: str, contributions: Dict) -> str:
        """Generate recommendation based on prediction"""
        
        if pred_class == 'high':
            return "✅ Strong candidate! Highly eligible for this position."
        
        elif pred_class == 'medium':
            improvements = []
            for feature, status in contributions.items():
                if status == 'negative':
                    if feature == 'cgpa':
                        improvements.append("improve CGPA")
                    elif feature == 'skills':
                        improvements.append("acquire more relevant skills")
                    elif feature == 'experience':
                        improvements.append("gain more experience")
            
            if improvements:
                return f"⚠️ Medium chance. Consider: {', '.join(improvements)}"
            else:
                return "⚠️ Medium chance. Profile needs strengthening."
        
        else:
            return "❌ Low chance. Consider improving CGPA and acquiring relevant skills before applying."
    
    def rule_based_prediction(self, student_data: Dict, job_data: Dict) -> Dict:
        """Rule-based fallback prediction"""
        
        student_cgpa = float(student_data.get('cgpa', 0))
        required_cgpa = float(job_data.get('eligibility_cgpa', 0))
        
        student_skills = student_data.get('skills', '')
        required_skills = job_data.get('required_skills', '')
        
        if isinstance(student_skills, str):
            student_skills_list = [s.strip().lower() for s in student_skills.split(',') if s.strip()]
        else:
            student_skills_list = student_skills or []
        
        if isinstance(required_skills, str):
            required_skills_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
        else:
            required_skills_list = required_skills or []
        
        if required_skills_list:
            matched = set(student_skills_list) & set(required_skills_list)
            match_percent = len(matched) / len(required_skills_list)
        else:
            match_percent = 1.0
        
        # Calculate score
        score = self._calculate_eligibility_score(student_data, job_data)
        
        # Determine class
        if student_cgpa >= required_cgpa and match_percent >= 0.7:
            pred_class = 'high'
        elif student_cgpa >= required_cgpa * 0.9 and match_percent >= 0.5:
            pred_class = 'medium'
        else:
            pred_class = 'low'
        
        return {
            'class': pred_class,
            'probability': 0.8,
            'confidence': 0.7,
            'score': score,
            'method': 'rule',
            'details': {
                'cgpa_match': student_cgpa >= required_cgpa,
                'skill_match_percent': match_percent * 100,
                'matched_skills': list(matched) if required_skills_list else student_skills_list
            }
        }
    
    def predict_batch(self, students_data: List[Dict], job_data: Dict) -> List[Dict]:
        """Predict for multiple students"""
        
        results = []
        for student in students_data:
            pred = self.predict(student, job_data)
            results.append({
                'student_id': student.get('user_id'),
                'name': student.get('full_name'),
                'prediction': pred
            })
        
        # Sort by score
        results.sort(key=lambda x: x['prediction']['score'], reverse=True)
        
        return results
    
    def save_model(self):
        """Save model and preprocessors"""
        model_file = os.path.join(self.model_path, 'eligibility_model.pkl')
        
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'feature_names': self.feature_names,
            'model_type': self.model_type,
            'class_mapping': self.class_mapping,
            'inverse_class_mapping': self.inverse_class_mapping
        }, model_file)
        
        logger.info(f"✅ Model saved to {model_file}")
    
    def load_model(self):
        """Load saved model"""
        model_file = os.path.join(self.model_path, 'eligibility_model.pkl')
        
        if os.path.exists(model_file):
            try:
                data = joblib.load(model_file)
                self.model = data['model']
                self.scaler = data['scaler']
                self.label_encoders = data['label_encoders']
                self.feature_names = data['feature_names']
                self.model_type = data.get('model_type', 'xgboost')
                self.class_mapping = data.get('class_mapping', {})
                self.inverse_class_mapping = data.get('inverse_class_mapping', {})
                logger.info(f"✅ Model loaded from {model_file}")
                return True
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                return False
        return False