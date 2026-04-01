import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
import joblib
import os
import json
import re
from typing import List, Dict, Set, Tuple, Optional
import logging
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class SkillEnhancer:
    """
    Advanced skill extraction and enhancement using Word Embeddings,
    Taxonomy Learning, and Skill Level Detection
    """
    
    def __init__(self, model_path="app/ai/models/skill_models/"):
        self.model_path = model_path
        os.makedirs(model_path, exist_ok=True)
        
        # Skill databases
        self.skill_taxonomy = self._load_skill_taxonomy()
        self.skill_embeddings = None
        self.skill_vectors = None
        self.skill_clusters = None
        self.tfidf_vectorizer = TfidfVectorizer(max_features=5000)
        
        # Common skill variations
        self.skill_variations = self._load_skill_variations()
        
        # Skill level keywords
        self.level_keywords = {
            'beginner': ['beginner', 'basic', 'fundamental', 'learning', 'know', 'familiar', 'exposure', 'trained', 'studied', 'course'],
            'intermediate': ['intermediate', 'working knowledge', 'practical', 'applied', 'used', 'experience', 'worked', 'developed', 'created'],
            'advanced': ['advanced', 'expert', 'proficient', 'master', 'deep', 'extensive', 'lead', 'architect', 'designed', 'architected', 'optimized', 'scaled']
        }
        
        # Load or create embeddings
        self._initialize_embeddings()
        
        logger.info("✅ SkillEnhancer initialized")
    
    def _load_skill_taxonomy(self) -> Dict:
        """Load skill taxonomy/categories"""
        return {
            'programming_languages': {
                'python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php', 'swift',
                'kotlin', 'go', 'rust', 'typescript', 'scala', 'perl', 'r', 'matlab',
                'dart', 'elixir', 'haskell', 'clojure', 'c', 'objective-c', 'assembly',
                'vb.net', 'groovy', 'lua', 'julia'
            },
            'web_technologies': {
                'html', 'css', 'react', 'angular', 'vue', 'node.js', 'express',
                'django', 'flask', 'spring', 'asp.net', 'jquery', 'bootstrap',
                'tailwind', 'sass', 'webpack', 'babel', 'redux', 'next.js',
                'gatsby', 'nuxt.js', 'svelte', 'graphql', 'rest api', 'soap',
                'xml', 'json', 'ajax', 'webassembly', 'pwa', 'htmx'
            },
            'databases': {
                'mysql', 'postgresql', 'mongodb', 'oracle', 'sqlite', 'redis',
                'cassandra', 'elasticsearch', 'firebase', 'mariadb', 'dynamodb',
                'couchdb', 'neo4j', 'influxdb', 'sql server', 'db2', 'teradata',
                'snowflake', 'bigquery', 'redshift', 'cosmos db'
            },
            'cloud_devops': {
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git',
                'github', 'gitlab', 'ansible', 'terraform', 'prometheus', 'grafana',
                'circleci', 'travis ci', 'argo', 'helm', 'istio', 'puppet', 'chef',
                'vagrant', 'cloudformation', 'lambda', 'ec2', 's3', 'rds'
            },
            'data_science_ai': {
                'machine learning', 'deep learning', 'data science', 'tensorflow',
                'pytorch', 'keras', 'pandas', 'numpy', 'scikit-learn', 'opencv',
                'nlp', 'computer vision', 'llm', 'genai', 'langchain', 'spacy',
                'nltk', 'transformers', 'bert', 'gpt', 'llama', 'rag', 'ai',
                'artificial intelligence', 'data mining', 'statistics', 'probability',
                'linear algebra', 'calculus', 'optimization', 'neural networks'
            },
            'mobile_development': {
                'android', 'ios', 'react native', 'flutter', 'xamarin', 'swiftui',
                'jetpack compose', 'kotlin multiplatform', 'ionic', 'cordova',
                'objective-c', 'swift', 'kotlin', 'java android', 'android studio',
                'xcode', 'uikit', 'material design', 'mobile ui'
            },
            'soft_skills': {
                'communication', 'leadership', 'teamwork', 'problem solving',
                'critical thinking', 'time management', 'presentation', 'negotiation',
                'conflict resolution', 'emotional intelligence', 'adaptability',
                'creativity', 'collaboration', 'mentoring', 'public speaking',
                'writing', 'analytical thinking', 'decision making'
            },
            'testing': {
                'selenium', 'junit', 'pytest', 'jest', 'mocha', 'cypress',
                'playwright', 'testng', 'cucumber', 'robot framework', 'postman',
                'soapui', 'jmeter', 'loadrunner', 'unit testing', 'integration testing',
                'e2e testing', 'tdd', 'bdd', 'qa', 'quality assurance'
            },
            'networking_security': {
                'tcp/ip', 'dns', 'http', 'https', 'rest api', 'graphql',
                'websockets', 'networking', 'security', 'cybersecurity', 'encryption',
                'firewall', 'vpn', 'ssl/tls', 'oauth', 'jwt', 'cryptography',
                'penetration testing', 'ethical hacking', 'wireshark', 'nmap',
                'metasploit', 'burp suite', 'cisco', 'routing', 'switching'
            },
            'devops_tools': {
                'jenkins', 'gitlab ci', 'github actions', 'travis ci', 'circleci',
                'teamcity', 'bamboo', 'ansible', 'puppet', 'chef', 'saltstack',
                'terraform', 'cloudformation', 'pulumi', 'vagrant', 'packer',
                'consul', 'vault', 'nomad', 'spinnaker', 'argo cd'
            },
            'big_data': {
                'hadoop', 'spark', 'kafka', 'flink', 'storm', 'hive', 'pig',
                'hbase', 'cassandra', 'zookeeper', 'airflow', 'dbt', 'databricks',
                'snowflake', 'bigquery', 'redshift', 'presto', 'trino'
            }
        }
    
    def _load_skill_variations(self) -> Dict:
        """Load common skill name variations"""
        return {
            'python': ['python', 'python3', 'python programming', 'python language'],
            'javascript': ['javascript', 'js', 'ecmascript', 'java script'],
            'react': ['react', 'reactjs', 'react.js', 'react js'],
            'node.js': ['node', 'nodejs', 'node.js', 'node js'],
            'machine learning': ['ml', 'machine learning', 'machine-learning', 'machinelearning'],
            'deep learning': ['dl', 'deep learning', 'deep-learning', 'deeplearning'],
            'aws': ['aws', 'amazon web services', 'amazon aws'],
            'gcp': ['gcp', 'google cloud', 'google cloud platform'],
            'c++': ['c++', 'cpp', 'cplusplus', 'c plus plus'],
            'c#': ['c#', 'csharp', 'c sharp'],
            'tensorflow': ['tensorflow', 'tf', 'tensor flow'],
            'pytorch': ['pytorch', 'torch', 'py torch'],
            'nlp': ['nlp', 'natural language processing', 'natural language'],
            'computer vision': ['cv', 'computer vision', 'comp vision'],
            'docker': ['docker', 'docker container'],
            'kubernetes': ['kubernetes', 'k8s', 'kube'],
            'html': ['html', 'html5'],
            'css': ['css', 'css3'],
            'sql': ['sql', 'structured query language'],
            'nosql': ['nosql', 'no sql'],
            'git': ['git', 'github', 'gitlab'],
            'mongodb': ['mongodb', 'mongo', 'mongo db'],
            'postgresql': ['postgresql', 'postgres', 'psql'],
            'mysql': ['mysql', 'my sql'],
            'java': ['java', 'java programming'],
            'spring': ['spring', 'spring boot', 'spring framework'],
            'django': ['django', 'django framework'],
            'flask': ['flask', 'flask framework'],
            'fastapi': ['fastapi', 'fast api'],
            'pandas': ['pandas', 'pandas library'],
            'numpy': ['numpy', 'num py', 'numeric python'],
            'scikit-learn': ['scikit-learn', 'sklearn', 'scikit learn']
        }
    
    def _initialize_embeddings(self):
        """Initialize word embeddings or use fallback"""
        try:
            # Try to load pre-trained embeddings
            embedding_file = os.path.join(self.model_path, 'skill_embeddings.pkl')
            if os.path.exists(embedding_file):
                data = joblib.load(embedding_file)
                self.skill_embeddings = data['embeddings']
                self.skill_list = data['skill_list']
                self.tfidf_vectorizer = data['vectorizer']
                logger.info(f"✅ Loaded existing skill embeddings for {len(self.skill_list)} skills")
            else:
                # Create simple embeddings using TF-IDF as fallback
                self._create_fallback_embeddings()
        except Exception as e:
            logger.warning(f"Could not load embeddings: {e}, using fallback")
            self._create_fallback_embeddings()
    
    def _create_fallback_embeddings(self):
        """Create simple TF-IDF based skill vectors"""
        # Get all unique skills
        all_skills = set()
        for category, skills in self.skill_taxonomy.items():
            all_skills.update(skills)
        
        # Add variations
        for base, variations in self.skill_variations.items():
            all_skills.add(base)
            all_skills.update(variations)
        
        # Create skill descriptions
        skill_descriptions = []
        self.skill_list = list(all_skills)
        
        for skill in self.skill_list:
            # Create a simple description
            desc = f"{skill} {' '.join(self.skill_variations.get(skill, []))}"
            # Add category context
            for category, cat_skills in self.skill_taxonomy.items():
                if skill in cat_skills:
                    desc += f" {category.replace('_', ' ')}"
            skill_descriptions.append(desc)
        
        # Create TF-IDF vectors
        self.skill_vectors = self.tfidf_vectorizer.fit_transform(skill_descriptions)
        self.skill_embeddings = self.skill_vectors.toarray()
        
        # Save for next time
        self.save_models()
        
        logger.info(f"✅ Created fallback embeddings for {len(self.skill_list)} skills")
    
    def find_similar_skills(self, skill: str, threshold: float = 0.7, top_k: int = 5) -> List[Dict]:
        """
        Find similar skills using embeddings
        e.g., "TensorFlow" -> ["Keras", "PyTorch", "Deep Learning"]
        """
        skill_lower = skill.lower().strip()
        
        # Check if skill exists in our database
        if skill_lower not in self.skill_list:
            # Try to find close match
            skill_lower = self._find_closest_skill(skill_lower)
        
        if skill_lower not in self.skill_list:
            return []
        
        # Get index of skill
        skill_idx = self.skill_list.index(skill_lower)
        
        # Get similarity scores
        if hasattr(self, 'skill_vectors') and self.skill_vectors is not None:
            # Use TF-IDF vectors
            skill_vector = self.skill_vectors[skill_idx]
            similarities = cosine_similarity(skill_vector, self.skill_vectors)[0]
        else:
            # Use embeddings
            skill_embed = self.skill_embeddings[skill_idx].reshape(1, -1)
            similarities = cosine_similarity(skill_embed, self.skill_embeddings)[0]
        
        # Get top similar skills
        similar_indices = np.argsort(similarities)[::-1][1:top_k+1]
        
        similar_skills = []
        for idx in similar_indices:
            if similarities[idx] >= threshold:
                similar_skills.append({
                    'skill': self.skill_list[idx],
                    'similarity': float(round(similarities[idx], 2)),
                    'relationship': self._get_skill_relationship(skill_lower, self.skill_list[idx])
                })
        
        return similar_skills
    
    def _find_closest_skill(self, skill: str) -> str:
        """Find closest matching skill from database"""
        from difflib import get_close_matches
        
        matches = get_close_matches(skill, self.skill_list, n=1, cutoff=0.7)
        return matches[0] if matches else skill
    
    def _get_skill_relationship(self, skill1: str, skill2: str) -> str:
        """Determine relationship between two skills"""
        
        # Check if same category
        for category, skills in self.skill_taxonomy.items():
            if skill1 in skills and skill2 in skills:
                return f"same_category"
        
        # Check if one is subset of other
        if skill1 in skill2 or skill2 in skill1:
            return "subskill"
        
        # Check if variations
        for base, variations in self.skill_variations.items():
            if skill1 in variations and skill2 in variations:
                return "variation"
        
        # Check if complementary (often used together)
        complementary_pairs = [
            ('python', 'django'), ('python', 'flask'), ('python', 'fastapi'),
            ('javascript', 'react'), ('javascript', 'node.js'), ('javascript', 'vue'),
            ('tensorflow', 'keras'), ('pytorch', 'transformers'),
            ('docker', 'kubernetes'), ('aws', 'terraform'),
            ('sql', 'mongodb'), ('java', 'spring'),
            ('html', 'css'), ('react', 'redux'),
            ('django', 'postgresql'), ('flask', 'sqlalchemy'),
            ('machine learning', 'python'), ('deep learning', 'tensorflow')
        ]
        
        if (skill1, skill2) in complementary_pairs or (skill2, skill1) in complementary_pairs:
            return "complementary"
        
        return "related"
    
    def detect_skill_level(self, skill: str, context: str) -> Dict:
        """
        Detect skill level from context
        Returns: {'level': 'beginner/intermediate/advanced', 'confidence': 0.8}
        """
        context_lower = context.lower()
        
        # Look for level indicators in context
        scores = {'beginner': 0, 'intermediate': 0, 'advanced': 0}
        
        # Check for level keywords
        for level, keywords in self.level_keywords.items():
            for keyword in keywords:
                if keyword in context_lower:
                    scores[level] += 1
        
        # Check for experience indicators
        experience_patterns = [
            (r'(\d+)\s*years?', 'years'),
            (r'(\d+)\s*months?', 'months'),
            (r'experienced?', 'exp'),
            (r'proficient?', 'prof'),
            (r'expert', 'expert'),
            (r'beginner', 'beginner'),
            (r'intermediate', 'intermediate'),
            (r'advanced', 'advanced')
        ]
        
        for pattern, indicator in experience_patterns:
            match = re.search(pattern, context_lower)
            if match:
                if indicator == 'years':
                    years = int(match.group(1))
                    if years < 2:
                        scores['beginner'] += 2
                    elif years < 4:
                        scores['intermediate'] += 3
                    else:
                        scores['advanced'] += 4
                elif indicator == 'months':
                    months = int(match.group(1))
                    if months < 6:
                        scores['beginner'] += 1
                    else:
                        scores['intermediate'] += 2
                elif indicator in ['exp', 'prof']:
                    scores['intermediate'] += 2
                elif indicator == 'expert':
                    scores['advanced'] += 3
                elif indicator == 'beginner':
                    scores['beginner'] += 3
                elif indicator == 'intermediate':
                    scores['intermediate'] += 3
                elif indicator == 'advanced':
                    scores['advanced'] += 3
        
        # Check for project complexity
        complex_indicators = ['lead', 'architect', 'designed', 'developed', 'implemented', 'built']
        for indicator in complex_indicators:
            if indicator in context_lower:
                scores['intermediate'] += 1
        
        advanced_indicators = ['optimized', 'scaled', 'architected', 'research', 'invented', 'patented']
        for indicator in advanced_indicators:
            if indicator in context_lower:
                scores['advanced'] += 2
        
        # Determine level
        total_score = sum(scores.values())
        if total_score == 0:
            return {
                'level': 'unknown',
                'confidence': 0.5,
                'scores': scores
            }
        
        if scores['advanced'] > scores['intermediate'] and scores['advanced'] > scores['beginner']:
            level = 'advanced'
            confidence = min(0.5 + (scores['advanced'] / total_score * 0.5), 0.95)
        elif scores['intermediate'] > scores['beginner']:
            level = 'intermediate'
            confidence = min(0.5 + (scores['intermediate'] / total_score * 0.4), 0.9)
        else:
            level = 'beginner'
            confidence = min(0.5 + (scores['beginner'] / total_score * 0.3), 0.85)
        
        return {
            'level': level,
            'confidence': round(confidence, 2),
            'scores': scores
        }
    
    def cluster_skills(self, skills: List[str], eps: float = 0.5) -> Dict:
        """
        Group related skills using clustering
        """
        if len(skills) < 2:
            return {'clusters': {0: skills}, 'num_clusters': 1}
        
        # Get skill indices
        skill_indices = []
        valid_skills = []
        
        for skill in skills:
            skill_lower = skill.lower()
            if skill_lower in self.skill_list:
                skill_indices.append(self.skill_list.index(skill_lower))
                valid_skills.append(skill)
            else:
                # Try to find close match
                close_match = self._find_closest_skill(skill_lower)
                if close_match in self.skill_list:
                    skill_indices.append(self.skill_list.index(close_match))
                    valid_skills.append(close_match)
                else:
                    valid_skills.append(skill)  # Keep original
        
        if len(valid_skills) < 2:
            return {'clusters': {0: valid_skills}, 'num_clusters': 1}
        
        # Get embeddings for these skills
        if hasattr(self, 'skill_vectors') and self.skill_vectors is not None:
            if len(skill_indices) > 0:
                skill_embeds = self.skill_vectors[skill_indices].toarray()
            else:
                # Fallback: use random embeddings
                skill_embeds = np.random.rand(len(valid_skills), 100)
        else:
            if len(skill_indices) > 0:
                skill_embeds = self.skill_embeddings[skill_indices]
            else:
                skill_embeds = np.random.rand(len(valid_skills), self.skill_embeddings.shape[1])
        
        # Apply DBSCAN clustering
        clustering = DBSCAN(eps=eps, min_samples=1, metric='cosine')
        labels = clustering.fit_predict(skill_embeds)
        
        # Group skills by cluster
        clusters = {}
        for skill, label in zip(valid_skills, labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(skill)
        
        # Identify cluster themes
        cluster_themes = {}
        for label, cluster_skills in clusters.items():
            theme = self._identify_cluster_theme(cluster_skills)
            cluster_themes[int(label)] = {
                'skills': cluster_skills,
                'theme': theme,
                'size': len(cluster_skills)
            }
        
        return {
            'clusters': cluster_themes,
            'num_clusters': len(clusters)
        }
    
    def _identify_cluster_theme(self, skills: List[str]) -> str:
        """Identify the main theme of a skill cluster"""
        # Count category occurrences
        category_counts = Counter()
        
        for skill in skills:
            skill_lower = skill.lower()
            for category, category_skills in self.skill_taxonomy.items():
                if skill_lower in category_skills or any(s in skill_lower for s in category_skills):
                    category_counts[category] += 1
                    break
            else:
                category_counts['other'] += 1
        
        if category_counts:
            return category_counts.most_common(1)[0][0]
        
        return 'general'
    
    def detect_emerging_skills(self, recent_drives: List[Dict]) -> List[Dict]:
        """
        Detect emerging skills from recent job drives
        """
        skill_frequency = Counter()
        
        for drive in recent_drives:
            required_skills = drive.get('required_skills', '')
            if isinstance(required_skills, str):
                skills = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
                skill_frequency.update(skills)
        
        # Skills that appear frequently but might be new
        emerging = []
        total_drives = len(recent_drives) if recent_drives else 1
        
        for skill, count in skill_frequency.most_common(30):
            frequency = count / total_drives
            
            # Check if skill is in taxonomy
            is_in_taxonomy = any(skill in skills for skills in self.skill_taxonomy.values())
            
            # Check if skill is in variations
            is_variation = any(skill in variations for variations in self.skill_variations.values())
            
            if frequency > 0.1 and not is_in_taxonomy and not is_variation:
                # Potential emerging skill
                emerging.append({
                    'skill': skill,
                    'frequency': round(frequency, 2),
                    'mentions': count,
                    'status': 'emerging',
                    'suggestion': f"Consider adding '{skill}' to skill database"
                })
            elif frequency > 0.3 and (is_in_taxonomy or is_variation):
                # Trending skill
                emerging.append({
                    'skill': skill,
                    'frequency': round(frequency, 2),
                    'mentions': count,
                    'status': 'trending'
                })
        
        return emerging[:15]  # Top 15
    
    def get_skill_synonyms(self, skill: str) -> List[str]:
        """Get synonyms/alternative names for a skill"""
        synonyms = []
        skill_lower = skill.lower()
        
        # Check variations
        for base, variations in self.skill_variations.items():
            if skill_lower == base or skill_lower in variations:
                synonyms = [v for v in variations if v != skill_lower]
                # Add the base if it's different
                if base != skill_lower and base not in synonyms:
                    synonyms.append(base)
                break
        
        # Add related skills
        similar = self.find_similar_skills(skill, threshold=0.8, top_k=3)
        synonyms.extend([s['skill'] for s in similar if s['skill'] not in synonyms])
        
        return list(set(synonyms))[:5]
    
    def calculate_skill_match_score(self, student_skills: List[str], required_skills: List[str]) -> Dict:
        """
        Calculate enhanced skill match score with synonyms and related skills
        """
        student_skills_lower = [s.lower() for s in student_skills]
        required_skills_lower = [s.lower() for s in required_skills]
        
        exact_matches = []
        synonym_matches = []
        related_matches = []
        missing = []
        
        for req_skill in required_skills_lower:
            # Check exact match
            if req_skill in student_skills_lower:
                exact_matches.append(req_skill)
                continue
            
            # Check synonym match
            synonyms = self.get_skill_synonyms(req_skill)
            if any(syn in student_skills_lower for syn in synonyms):
                synonym_matches.append(req_skill)
                continue
            
            # Check related skills
            similar = self.find_similar_skills(req_skill, threshold=0.7, top_k=3)
            similar_skills = [s['skill'] for s in similar]
            if any(sim in student_skills_lower for sim in similar_skills):
                related_matches.append(req_skill)
                continue
            
            missing.append(req_skill)
        
        # Calculate weighted score
        total_required = len(required_skills_lower)
        if total_required == 0:
            return {
                'score': 100,
                'exact_matches': exact_matches,
                'synonym_matches': synonym_matches,
                'related_matches': related_matches,
                'missing': missing,
                'weights': {'exact': 1.0, 'synonym': 0.8, 'related': 0.5}
            }
        
        weighted_score = (
            len(exact_matches) * 1.0 +
            len(synonym_matches) * 0.8 +
            len(related_matches) * 0.5
        ) / total_required * 100
        
        return {
            'score': round(weighted_score, 2),
            'exact_matches': exact_matches,
            'synonym_matches': synonym_matches,
            'related_matches': related_matches,
            'missing': missing,
            'counts': {
                'exact': len(exact_matches),
                'synonym': len(synonym_matches),
                'related': len(related_matches),
                'missing': len(missing)
            }
        }
    
    def save_models(self):
        """Save trained models"""
        model_file = os.path.join(self.model_path, 'skill_embeddings.pkl')
        joblib.dump({
            'embeddings': self.skill_embeddings,
            'skill_list': self.skill_list,
            'vectorizer': self.tfidf_vectorizer
        }, model_file)
        logger.info(f"✅ Models saved to {model_file}")
    
    def load_models(self):
        """Load trained models"""
        model_file = os.path.join(self.model_path, 'skill_embeddings.pkl')
        if os.path.exists(model_file):
            try:
                data = joblib.load(model_file)
                self.skill_embeddings = data['embeddings']
                self.skill_list = data['skill_list']
                self.tfidf_vectorizer = data['vectorizer']
                logger.info("✅ Models loaded successfully")
                return True
            except Exception as e:
                logger.error(f"Error loading models: {e}")
                return False
        return False