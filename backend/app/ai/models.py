import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib
import os
import logging
import random
from datetime import datetime
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class EligibilityPredictor:
    """Eligibility prediction ML model - FIXED LabelEncoder error"""
    
    def __init__(self, model_path="app/ai/models/eligibility_model.pkl"):
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        
        # Try to load existing model
        self.load_model()
        
        # Auto-train if no model exists
        if self.model is None:
            logger.info("No existing model found. Training new model...")
            self.train_model()
    
    def generate_synthetic_data(self, n_samples=1000) -> pd.DataFrame:
        """Synthetic training data generate kare"""
        data = []
        
        branches = ['CSE', 'IT', 'ECE', 'EEE', 'MECH', 'CIVIL', 'AI', 'DATA']
        skills_pool = ['Python', 'Java', 'SQL', 'Machine Learning', 'JavaScript', 
                      'React', 'AWS', 'Docker', 'C++', 'Ruby', 'PHP', 'Swift']
        
        for i in range(n_samples):
            cgpa = round(random.uniform(5.0, 10.0), 2)
            branch = random.choice(branches)
            semester = random.randint(3, 8)
            
            num_skills = random.randint(3, 15)
            student_skills = random.sample(skills_pool, min(num_skills, len(skills_pool)))
            
            has_experience = random.choice([0, 1])
            experience_months = random.randint(0, 24) if has_experience else 0
            num_projects = random.randint(0, 5)
            
            required_cgpa = round(random.uniform(6.0, 8.5), 2)
            required_skills_count = random.randint(5, 10)
            required_skills = random.sample(skills_pool, min(required_skills_count, len(skills_pool)))
            
            # EXACT skill matching - no partial matches
            matched_skills = set(student_skills) & set(required_skills)
            skill_match_percent = len(matched_skills) / len(required_skills) * 100 if required_skills else 0
            
            # Eligibility based on CGPA and 70% skill match
            eligible = 0
            if cgpa >= required_cgpa and skill_match_percent >= 70:
                eligible = 1
            
            # Add some noise for realism
            if random.random() < 0.05:
                eligible = 1 - eligible
            
            data.append({
                'cgpa': cgpa,
                'branch': branch,
                'semester': semester,
                'num_skills': len(student_skills),
                'skill_match_percent': skill_match_percent,
                'has_experience': has_experience,
                'experience_months': experience_months,
                'num_projects': num_projects,
                'required_cgpa': required_cgpa,
                'required_skills_count': len(required_skills),
                'eligible': eligible
            })
        
        return pd.DataFrame(data)
    
    def prepare_features(self, student_data: Dict, job_data: Dict) -> np.ndarray:
        """Features prepare kare for prediction"""
        
        features = []
        
        # CGPA
        features.append(float(student_data.get('cgpa', 0)))
        
        # Branch - FIXED: Safe branch encoding
        branch = student_data.get('branch', 'CSE')
        # Check if branch encoder exists and branch is in it
        if 'branch' in self.label_encoders and hasattr(self.label_encoders['branch'], 'classes_'):
            try:
                if branch in self.label_encoders['branch'].classes_:
                    branch_encoded = self.label_encoders['branch'].transform([branch])[0]
                else:
                    branch_encoded = 0
            except:
                branch_encoded = 0
        else:
            branch_encoded = 0
        features.append(branch_encoded)
        
        # Semester
        features.append(int(student_data.get('semester', 0)))
        
        # Skills
        student_skills = student_data.get('skills', '')
        if isinstance(student_skills, str):
            student_skills_list = [s.strip().lower() for s in student_skills.split(',') if s.strip()]
        else:
            student_skills_list = student_skills or []
        
        required_skills = job_data.get('required_skills', '')
        if isinstance(required_skills, str):
            required_skills_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
        else:
            required_skills_list = required_skills or []
        
        # EXACT skill match calculation
        if required_skills_list:
            matched = set(student_skills_list) & set(required_skills_list)
            skill_match = len(matched) / len(required_skills_list) * 100
        else:
            skill_match = 100
        
        features.append(skill_match)
        features.append(len(student_skills_list))
        features.append(len(required_skills_list))
        
        # Experience
        features.append(int(student_data.get('has_experience', 0)))
        features.append(int(student_data.get('experience_months', 0)))
        
        # Required CGPA
        features.append(float(job_data.get('eligibility_cgpa', 0)))
        
        return np.array(features).reshape(1, -1)
    
    def train_model(self):
        """Model train kare on synthetic data"""
        logger.info("Generating synthetic training data...")
        df = self.generate_synthetic_data(2000)
        
        # Prepare features
        X = df[['cgpa', 'skill_match_percent', 'num_skills', 'required_cgpa', 
                'required_skills_count', 'has_experience', 'experience_months', 
                'num_projects']].values
        
        # Encode branch
        self.label_encoders['branch'] = LabelEncoder()
        df['branch_encoded'] = self.label_encoders['branch'].fit_transform(df['branch'])
        
        branch_encoded = df['branch_encoded'].values.reshape(-1, 1)
        X = np.hstack([X, branch_encoded])
        
        y = df['eligible'].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        
        logger.info("Training Random Forest model...")
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.model.fit(X_train, y_train)
        
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        logger.info(f"Train accuracy: {train_score:.3f}")
        logger.info(f"Test accuracy: {test_score:.3f}")
        
        feature_names = ['cgpa', 'skill_match', 'num_skills', 'required_cgpa', 
                        'required_skills_count', 'has_experience', 'experience_months',
                        'num_projects', 'branch']
        importance = self.model.feature_importances_
        
        for name, imp in zip(feature_names, importance):
            logger.info(f"{name}: {imp:.3f}")
        
        self.save_model()
        
        return {
            'train_accuracy': train_score,
            'test_accuracy': test_score,
            'feature_importance': dict(zip(feature_names, importance))
        }
    
    def predict(self, student_data: Dict, job_data: Dict) -> Dict:
        """Eligibility predict kare - FIXED with safe error handling"""
        
        if self.model is None:
            logger.warning("Model not trained. Training now...")
            self.train_model()
        
        try:
            # Try ML prediction first
            features = self.prepare_features(student_data, job_data)
            features_scaled = self.scaler.transform(features)
            
            proba = self.model.predict_proba(features_scaled)[0]
            
            eligible_prob = proba[1] if len(proba) > 1 else proba[0]
            prediction = self.model.predict(features_scaled)[0]
            
            return {
                'eligible': bool(prediction),
                'probability': float(eligible_prob),
                'confidence': float(max(proba)),
                'method': 'ml'
            }
        except Exception as e:
            logger.error(f"ML prediction error: {e}, falling back to rules")
            return self.rule_based_prediction(student_data, job_data)
    
    def rule_based_prediction(self, student_data: Dict, job_data: Dict) -> Dict:
        """Rule-based fallback prediction - FIXED with 70% threshold and safe handling"""
        
        # Get CGPA values
        student_cgpa = float(student_data.get('cgpa', 0))
        required_cgpa = float(job_data.get('eligibility_cgpa', 0))
        
        # Get skills
        student_skills = student_data.get('skills', '')
        required_skills = job_data.get('required_skills', '')
        
        # Parse student skills
        if isinstance(student_skills, str):
            student_skills_list = [s.strip().lower() for s in student_skills.split(',') if s.strip()]
        else:
            student_skills_list = student_skills or []
        
        # Parse required skills
        if isinstance(required_skills, str):
            required_skills_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
        else:
            required_skills_list = required_skills or []
        
        # Calculate exact skill matches
        matched_skills = []
        if required_skills_list:
            for skill in required_skills_list:
                if skill in student_skills_list:  # EXACT match only
                    matched_skills.append(skill)
            match_percent = len(matched_skills) / len(required_skills_list) * 100
        else:
            match_percent = 100
            matched_skills = student_skills_list
        
        # Calculate missing skills
        missing_skills = [s for s in required_skills_list if s not in matched_skills]
        
        # STRICT ELIGIBILITY: CGPA >= required AND skills >= 70%
        cgpa_eligible = student_cgpa >= required_cgpa
        skills_eligible = match_percent >= 70
        eligible = cgpa_eligible and skills_eligible
        
        # Calculate probability score
        cgpa_score = min(student_cgpa / required_cgpa, 1.5) / 1.5 * 0.4 if required_cgpa > 0 else 0.4
        skill_score = match_percent / 100 * 0.6
        probability = min(cgpa_score + skill_score, 1.0)
        
        return {
            'eligible': eligible,
            'probability': probability,
            'confidence': 0.8,
            'method': 'rule',
            'details': {
                'cgpa_match': cgpa_eligible,
                'skill_match_percent': match_percent,
                'matched_skills': matched_skills,
                'missing_skills': missing_skills
            }
        }
    
    def save_model(self):
        """Model save kare"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'label_encoders': self.label_encoders
        }, self.model_path)
        logger.info(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Model load kare"""
        if os.path.exists(self.model_path):
            try:
                data = joblib.load(self.model_path)
                self.model = data['model']
                self.scaler = data['scaler']
                self.label_encoders = data['label_encoders']
                logger.info(f"Model loaded from {self.model_path}")
                return True
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                return False
        return False


class SelectionProbabilityPredictor:
    """Selection probability prediction model"""
    
    def __init__(self, model_path="app/ai/models/selection_model.pkl"):
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        
        self.load_model()
        
        # Auto-train if no model exists
        if self.model is None:
            logger.info("No existing selection model found. Training new model...")
            self.train_model()
    
    def train_model(self):
        """Train regression model for selection probability"""
        
        np.random.seed(42)
        n_samples = 1000
        
        X = np.random.rand(n_samples, 5)
        
        y = 0.3*X[:,0] + 0.4*X[:,1] + 0.2*X[:,2] + 0.1*X[:,3] + np.random.normal(0, 0.1, n_samples)
        y = np.clip(y, 0, 1)
        
        X_scaled = self.scaler.fit_transform(X)
        
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.model.fit(X_scaled, y)
        
        self.save_model()
        
        logger.info("Selection probability model trained")
    
    def predict(self, features: List[float]) -> float:
        """Selection probability predict kare"""
        if self.model is None:
            return 0.5
        
        features_scaled = self.scaler.transform([features])
        prob = self.model.predict(features_scaled)[0]
        return float(np.clip(prob, 0, 1))
    
    def save_model(self):
        """Model save kare"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler
        }, self.model_path)
    
    def load_model(self):
        """Model load kare"""
        if os.path.exists(self.model_path):
            try:
                data = joblib.load(self.model_path)
                self.model = data['model']
                self.scaler = data['scaler']
                return True
            except:
                return False
        return False