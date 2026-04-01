import random
from typing import List, Dict

class CourseRecommender:
    """Recommend courses based on missing skills"""
    
    def __init__(self):
        self.course_db = self._load_courses()
    
    def _load_courses(self) -> Dict:
        """Load course database"""
        return {
            'python': [
                {'name': 'Python for Beginners', 'platform': 'Coursera', 'url': 'https://www.coursera.org/learn/python', 'free': True},
                {'name': 'Complete Python Bootcamp', 'platform': 'Udemy', 'url': 'https://www.udemy.com/course/python-bootcamp/', 'free': False},
                {'name': 'Python Tutorial', 'platform': 'YouTube', 'url': 'https://www.youtube.com/watch?v=_uQrJ0TkZlc', 'free': True}
            ],
            'java': [
                {'name': 'Java Programming', 'platform': 'Coursera', 'url': 'https://www.coursera.org/learn/java-programming', 'free': True},
                {'name': 'Java Masterclass', 'platform': 'Udemy', 'url': 'https://www.udemy.com/course/java-the-complete-java-developer-course/', 'free': False},
                {'name': 'Java Tutorial', 'platform': 'YouTube', 'url': 'https://www.youtube.com/watch?v=eIrMbAQSU34', 'free': True}
            ],
            'sql': [
                {'name': 'SQL for Data Science', 'platform': 'Coursera', 'url': 'https://www.coursera.org/learn/sql-data-science', 'free': True},
                {'name': 'The Complete SQL Course', 'platform': 'Udemy', 'url': 'https://www.udemy.com/course/the-complete-sql-course/', 'free': False},
                {'name': 'SQL Tutorial', 'platform': 'YouTube', 'url': 'https://www.youtube.com/watch?v=HXV3zeQKqGY', 'free': True}
            ],
            'machine learning': [
                {'name': 'Machine Learning', 'platform': 'Coursera', 'url': 'https://www.coursera.org/learn/machine-learning', 'free': True},
                {'name': 'Machine Learning A-Z', 'platform': 'Udemy', 'url': 'https://www.udemy.com/course/machinelearning/', 'free': False},
                {'name': 'ML for Beginners', 'platform': 'YouTube', 'url': 'https://www.youtube.com/watch?v=NWONeJKn6kc', 'free': True}
            ],
            'javascript': [
                {'name': 'JavaScript Basics', 'platform': 'Coursera', 'url': 'https://www.coursera.org/learn/javascript-basics', 'free': True},
                {'name': 'The Complete JavaScript Course', 'platform': 'Udemy', 'url': 'https://www.udemy.com/course/the-complete-javascript-course/', 'free': False},
                {'name': 'JavaScript Tutorial', 'platform': 'YouTube', 'url': 'https://www.youtube.com/watch?v=PkZNo7MFNFg', 'free': True}
            ],
            'react': [
                {'name': 'React Basics', 'platform': 'Coursera', 'url': 'https://www.coursera.org/learn/react-basics', 'free': True},
                {'name': 'React - The Complete Guide', 'platform': 'Udemy', 'url': 'https://www.udemy.com/course/react-the-complete-guide/', 'free': False},
                {'name': 'React Tutorial', 'platform': 'YouTube', 'url': 'https://www.youtube.com/watch?v=Ke90Tje7VS0', 'free': True}
            ],
            'aws': [
                {'name': 'AWS Fundamentals', 'platform': 'Coursera', 'url': 'https://www.coursera.org/learn/aws-fundamentals', 'free': True},
                {'name': 'AWS Certified Solutions Architect', 'platform': 'Udemy', 'url': 'https://www.udemy.com/course/aws-certified-solutions-architect/', 'free': False},
                {'name': 'AWS Tutorial', 'platform': 'YouTube', 'url': 'https://www.youtube.com/watch?v=ulprqHHWlng', 'free': True}
            ],
            'docker': [
                {'name': 'Docker Essentials', 'platform': 'Coursera', 'url': 'https://www.coursera.org/learn/docker-essentials', 'free': True},
                {'name': 'Docker Masterclass', 'platform': 'Udemy', 'url': 'https://www.udemy.com/course/docker-masterclass/', 'free': False},
                {'name': 'Docker Tutorial', 'platform': 'YouTube', 'url': 'https://www.youtube.com/watch?v=3c-iBn73dDE', 'free': True}
            ]
        }
    
    def recommend_courses(self, missing_skills: List[str], max_recommendations: int = 5) -> List[Dict]:
        """Recommend courses for missing skills"""
        recommendations = []
        
        for skill in missing_skills[:max_recommendations]:
            skill_lower = skill.lower()
            
            # Find matching skill in database
            matched_skill = None
            for db_skill in self.course_db:
                if db_skill in skill_lower or skill_lower in db_skill:
                    matched_skill = db_skill
                    break
            
            if matched_skill:
                courses = self.course_db[matched_skill]
                # Recommend 1-2 courses per skill
                for course in courses[:2]:
                    recommendations.append({
                        'skill': matched_skill,
                        'name': course['name'],
                        'platform': course['platform'],
                        'url': course['url'],
                        'free': course['free']
                    })
            else:
                # Generic recommendation
                recommendations.append({
                    'skill': skill,
                    'name': f'Learn {skill.title()}',
                    'platform': 'Google Search',
                    'url': f'https://www.google.com/search?q=learn+{skill}',
                    'free': True
                })
        
        return recommendations
    
    def get_learning_path(self, skill: str) -> Dict:
        """Get complete learning path for a skill"""
        skill_lower = skill.lower()
        
        paths = {
            'python': {
                'beginner': ['Python Basics', 'Data Types', 'Functions'],
                'intermediate': ['OOP', 'File Handling', 'Modules'],
                'advanced': ['Decorators', 'Generators', 'Multithreading'],
                'projects': ['Web Scraper', 'CLI Tool', 'Data Analysis']
            },
            'java': {
                'beginner': ['Java Basics', 'OOP Concepts', 'Collections'],
                'intermediate': ['Exceptions', 'I/O', 'Multithreading'],
                'advanced': ['Streams', 'Lambdas', 'Design Patterns'],
                'projects': ['Banking App', 'Library System', 'REST API']
            },
            'machine learning': {
                'beginner': ['Python for ML', 'Statistics', 'Pandas'],
                'intermediate': ['Regression', 'Classification', 'Clustering'],
                'advanced': ['Neural Networks', 'Deep Learning', 'NLP'],
                'projects': ['Price Prediction', 'Image Classifier', 'Chatbot']
            }
        }
        
        for key in paths:
            if key in skill_lower:
                return paths[key]
        
        return {
            'beginner': [f'{skill} Basics'],
            'intermediate': [f'Advanced {skill}'],
            'advanced': [f'Master {skill}'],
            'projects': [f'{skill} Project']
        }