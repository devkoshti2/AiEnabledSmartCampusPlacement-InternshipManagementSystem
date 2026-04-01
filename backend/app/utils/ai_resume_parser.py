import spacy
import re
from typing import Dict, List, Tuple, Any, Optional
import logging
from app.ai.skill_enhancer import SkillEnhancer
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class AIResumeParser:
    """
    AI-powered resume parser using transformers and spaCy
    This ENHANCES the existing ResumeParser, not replaces it
    """
    
    def __init__(self):
        logger.info("🤖 Loading AI models... (first time may take 30 seconds)")
        
        # Load spaCy model for NER
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✅ spaCy model loaded")
        except:
            logger.error("❌ Please run: python -m spacy download en_core_web_sm")
            raise
        
        # Section labels for classification
        self.section_labels = [
            "education", "experience", "projects", "skills", 
            "certifications", "summary", "publications", 
            "achievements", "personal details", "languages",
            "interests", "references", "additional information"
        ]
        
        logger.info("✅ AI Resume Parser initialized")
    
        self.skill_enhancer = SkillEnhancer()
        logger.info("✅ Skill enhancer loaded")
    
    def extract_entities_with_confidence(self, text: str) -> Dict[str, List[Dict]]:
        """
        Use transformer NER to extract entities with confidence scores
        """
        doc = self.nlp(text)
        
        entities = {}
        for ent in doc.ents:
            if ent.label_ not in entities:
                entities[ent.label_] = []
            
            entities[ent.label_].append({
                'text': ent.text,
                'confidence': 0.9,
                'start': ent.start_char,
                'end': ent.end_char
            })
        
        return entities
    
    def classify_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into sections and classify each section
        """
        # Simple section splitting
        lines = text.split('\n')
        sections = []
        current_section = []
        current_heading = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line looks like a heading
            if (line.isupper() and len(line.split()) < 6) or \
               (line.endswith(':') and len(line.split()) < 6) or \
               (line.istitle() and len(line.split()) < 4 and any(word in line.lower() for word in ['education', 'experience', 'project', 'skill'])):
                if current_section:
                    sections.append({
                        'heading': current_heading,
                        'content': '\n'.join(current_section)
                    })
                current_heading = line
                current_section = []
            else:
                current_section.append(line)
        
        # Add last section
        if current_section:
            sections.append({
                'heading': current_heading,
                'content': '\n'.join(current_section)
            })
        
        # Rule-based classification
        for section in sections:
            section['label'] = self._rule_based_section_classify(section['heading'] or section['content'][:50])
            section['confidence'] = 0.7
        
        return sections
    
    def _rule_based_section_classify(self, text: str) -> str:
        """Rule-based section classification fallback"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['education', 'academic', 'qualification', 'b.tech', 'm.tech']):
            return 'education'
        elif any(word in text_lower for word in ['experience', 'work', 'employment', 'job']):
            return 'experience'
        elif any(word in text_lower for word in ['project', 'academic project']):
            return 'projects'
        elif any(word in text_lower for word in ['skill', 'technical', 'technology', 'expertise']):
            return 'skills'
        elif any(word in text_lower for word in ['certification', 'certificate', 'course']):
            return 'certifications'
        elif any(word in text_lower for word in ['summary', 'profile', 'objective']):
            return 'summary'
        elif any(word in text_lower for word in ['language', 'spoken']):
            return 'languages'
        elif any(word in text_lower for word in ['achievement', 'award']):
            return 'achievements'
        elif any(word in text_lower for word in ['interest', 'hobby']):
            return 'interests'
        elif any(word in text_lower for word in ['publication', 'paper', 'research']):
            return 'publications'
        elif any(word in text_lower for word in ['reference']):
            return 'references'
        elif any(word in text_lower for word in ['personal', 'contact', 'address', 'phone']):
            return 'personal details'
        else:
            return 'other'
    
    def extract_skills_with_context(self, text: str, skill_keywords: List[str]) -> List[Dict]:
        """
        Extract skills with context and confidence
        """
        doc = self.nlp(text[:5000])  # Limit to first 5000 chars for performance
        found_skills = []
        
        # Convert skill keywords to set for faster lookup
        skill_set = set(s.lower() for s in skill_keywords)
        
        for token in doc:
            if token.text.lower() in skill_set:
                # Get surrounding context (±5 tokens)
                start = max(0, token.i - 5)
                end = min(len(doc), token.i + 5)
                context = doc[start:end].text
                
                found_skills.append({
                    'skill': token.text,
                    'confidence': 0.85,
                    'context': context,
                    'position': token.i
                })
        
        # Remove duplicates keeping highest confidence
        unique_skills = {}
        for skill in found_skills:
            key = skill['skill'].lower()
            if key not in unique_skills:
                unique_skills[key] = skill
        
        return list(unique_skills.values())
    
    def extract_company_names(self, text: str) -> List[Dict]:
        """
        Extract company names using NER
        """
        doc = self.nlp(text[:3000])  # Limit for performance
        companies = []
        
        edu_keywords = ['university', 'college', 'institute', 'school', 'iit', 'nit', 'bits']
        
        for ent in doc.ents:
            if ent.label_ == 'ORG':
                # Check if it's likely a company (not a university)
                is_company = True
                ent_lower = ent.text.lower()
                
                if any(keyword in ent_lower for keyword in edu_keywords):
                    is_company = False
                
                if is_company and len(ent.text) > 2:
                    companies.append({
                        'name': ent.text,
                        'confidence': 0.85,
                        'context': doc[max(0, ent.start-3):min(len(doc), ent.end+3)].text
                    })
        
        return companies
    
    def extract_dates(self, text: str) -> List[Dict]:
        """
        Extract dates using NER
        """
        doc = self.nlp(text)
        dates = []
        
        for ent in doc.ents:
            if ent.label_ == 'DATE':
                dates.append({
                    'text': ent.text,
                    'parsed': self._parse_date(ent.text),
                    'confidence': 0.9,
                    'context': doc[max(0, ent.start-3):min(len(doc), ent.end+3)].text
                })
        
        return dates
    
    def _parse_date(self, date_text: str) -> Dict:
        """
        Parse date text into structured format
        """
        import re
        
        result = {
            'year': None,
            'month': None,
            'day': None,
            'is_range': False,
            'start_year': None,
            'end_year': None
        }
        
        # Check for range (2020-2024)
        range_pattern = r'(\d{4})\s*[-–—]\s*(\d{4}|present|current)'
        range_match = re.search(range_pattern, date_text, re.IGNORECASE)
        if range_match:
            result['is_range'] = True
            result['start_year'] = int(range_match.group(1))
            end = range_match.group(2)
            result['end_year'] = end if end.lower() in ['present', 'current'] else int(end)
            return result
        
        # Match patterns like "May 2021", "05/2021", "2021"
        patterns = [
            (r'(\d{4})', lambda m: {'year': int(m.group(1))}),
            (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})', 
             lambda m: {'month': m.group(1), 'year': int(m.group(2))}),
            (r'(\d{1,2})/(\d{4})', lambda m: {'month': int(m.group(1)), 'year': int(m.group(2))}),
            (r'(\d{1,2})-(\d{4})', lambda m: {'month': int(m.group(1)), 'year': int(m.group(2))}),
        ]
        
        for pattern, handler in patterns:
            match = re.search(pattern, date_text, re.IGNORECASE)
            if match:
                result.update(handler(match))
                break
        
        return result
    
    def extract_education(self, text: str) -> Dict:
        """
        Enhanced education extraction with confidence
        """
        doc = self.nlp(text)
        
        result = {
            'degree': None,
            'branch': None,
            'institution': None,
            'year': None,
            'cgpa': None,
            'percentage': None,
            'confidence': {}
        }
        
        # Extract institution (ORG entities)
        for ent in doc.ents:
            if ent.label_ == 'ORG':
                edu_keywords = ['university', 'college', 'institute', 'school', 'iit', 'nit', 'bits']
                ent_lower = ent.text.lower()
                if any(keyword in ent_lower for keyword in edu_keywords):
                    result['institution'] = ent.text
                    result['confidence']['institution'] = 0.95
                    break
        
        # Extract degree
        degree_patterns = [
            (r'B\.?Tech|Bachelor of Technology', 'BTech'),
            (r'M\.?Tech|Master of Technology', 'MTech'),
            (r'B\.?E\.?|Bachelor of Engineering', 'BE'),
            (r'M\.?E\.?|Master of Engineering', 'ME'),
            (r'B\.?Sc|Bachelor of Science', 'BSc'),
            (r'M\.?Sc|Master of Science', 'MSc'),
            (r'BCA|Bachelor of Computer Applications', 'BCA'),
            (r'MCA|Master of Computer Applications', 'MCA'),
            (r'PhD|Doctor of Philosophy', 'PhD'),
            (r'BBA|Bachelor of Business Administration', 'BBA'),
            (r'MBA|Master of Business Administration', 'MBA'),
        ]
        
        for pattern, degree in degree_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                result['degree'] = degree
                result['confidence']['degree'] = 0.9
                break
        
        # Extract branch
        branch_patterns = {
            'CSE': r'computer\s*science|information\s*technology|it|cs|computers',
            'ECE': r'electronics|communication|ece',
            'EEE': r'electrical|electronics engineering|eee',
            'MECH': r'mechanical|mech',
            'CIVIL': r'civil',
            'AI': r'artificial intelligence|ai|ml',
            'DATA': r'data science|data',
        }
        
        for branch, pattern in branch_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                result['branch'] = branch
                result['confidence']['branch'] = 0.85
                break
        
        # Extract CGPA/Percentage
        cgpa_pattern = r'(?:CGPA|GPA|cgpa|gpa)[\s:]*([0-9]\.?[0-9]?)'
        cgpa_match = re.search(cgpa_pattern, text)
        if cgpa_match:
            result['cgpa'] = float(cgpa_match.group(1))
            result['confidence']['cgpa'] = 0.9
        
        percentage_pattern = r'(?:percentage|%|percent)[\s:]*([0-9]{2}(?:\.[0-9])?)%?'
        percentage_match = re.search(percentage_pattern, text, re.IGNORECASE)
        if percentage_match:
            result['percentage'] = float(percentage_match.group(1))
            result['confidence']['percentage'] = 0.9
        
        # Extract year
        year_pattern = r'\b(20\d{2})\b'
        years = re.findall(year_pattern, text)
        if years:
            # Usually graduation year is the most recent
            result['year'] = max(years)
            result['confidence']['year'] = 0.8
        
        return result
    
    def extract_experience(self, text: str) -> List[Dict]:
        """
        Enhanced experience extraction
        """
        doc = self.nlp(text)
        experiences = []
        
        # Find experience section
        experience_text = ""
        lines = text.split('\n')
        in_experience = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(word in line_lower for word in ['experience', 'work', 'employment']):
                in_experience = True
                continue
            if in_experience:
                if i < len(lines) - 1 and any(word in lines[i+1].lower() for word in ['education', 'project', 'skill']):
                    break
                experience_text += line + "\n"
        
        if not experience_text:
            return []
        
        # Parse experience entries
        exp_doc = self.nlp(experience_text)
        
        current_exp = {}
        
        for sent in exp_doc.sents:
            sent_text = sent.text.strip()
            if not sent_text or len(sent_text) < 10:
                continue
            
            # Check for company names (ORG entities)
            companies = []
            for ent in sent.ents:
                if ent.label_ == 'ORG':
                    companies.append(ent.text)
            
            # Check for dates
            dates = []
            for ent in sent.ents:
                if ent.label_ == 'DATE':
                    dates.append(ent.text)
            
            if companies:
                if current_exp and 'company' in current_exp:
                    experiences.append(current_exp)
                current_exp = {
                    'company': companies[0] if companies else None,
                    'title': self._extract_job_title(sent_text),
                    'duration': dates[0] if dates else None,
                    'description': sent_text,
                    'confidence': 0.85
                }
            elif current_exp:
                current_exp['description'] += " " + sent_text
        
        if current_exp and 'company' in current_exp:
            experiences.append(current_exp)
        
        return experiences
    
    def _extract_job_title(self, text: str) -> str:
        """Extract job title from text"""
        title_patterns = [
            r'(?:as a|as an|position of|role of)\s+([A-Z][A-Za-z\s]+)',
            r'^([A-Z][A-Za-z\s]+(?:Engineer|Developer|Manager|Analyst|Consultant))',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return text[:50] if len(text) < 100 else text[:50] + "..."
    
    def extract_projects(self, text: str) -> List[Dict]:
        """
        Enhanced project extraction
        """
        projects = []
        
        # Find projects section
        lines = text.split('\n')
        in_projects = False
        project_text = ""
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(word in line_lower for word in ['project', 'academic project', 'personal project']):
                in_projects = True
                continue
            if in_projects:
                if i < len(lines) - 1 and any(word in lines[i+1].lower() for word in ['education', 'experience', 'skill']):
                    break
                project_text += line + "\n"
        
        if not project_text:
            return []
        
        # Split into individual projects
        project_entries = re.split(r'\n\s*[-•*]\s*|\n\s*\d+\.\s*', project_text)
        
        for entry in project_entries:
            if len(entry.strip()) < 20:
                continue
            
            # Extract technologies used
            tech_keywords = ['python', 'java', 'javascript', 'react', 'node', 'django', 
                           'flask', 'tensorflow', 'pytorch', 'sql', 'mongodb', 'aws']
            
            technologies = []
            for token in entry.lower().split():
                if token in tech_keywords:
                    technologies.append(token)
            
            projects.append({
                'name': entry.split('\n')[0][:50] if entry.split('\n')[0] else "Project",
                'description': entry[:200],
                'technologies': list(set(technologies))[:5],
                'confidence': 0.8
            })
        
        return projects
    
    def get_confidence_report(self, parsed_data: Dict) -> Dict:
        """
        Generate confidence report for all extracted fields
        """
        report = {
            'overall_confidence': 0.0,
            'field_confidence': {},
            'low_confidence_fields': [],
            'suggestions': []
        }
       
        confidences = []
        
        # Basic fields
        if 'basic' in parsed_data:
            for field, value in parsed_data['basic'].items():
                if value:
                    if field == 'email' and '@' in value:
                        conf = 0.95
                    elif field == 'phone' and re.match(r'^[\d\+\-\s]{10,}$', value):
                        conf = 0.9
                    else:
                        conf = 0.7
                    
                    report['field_confidence'][field] = conf
                    confidences.append(conf)
                    
                    if conf < 0.8:
                        report['low_confidence_fields'].append(field)
        
        # Enhanced fields
        if 'enhanced' in parsed_data:
            enhanced = parsed_data['enhanced']
            
            if 'skills_with_confidence' in enhanced:
                skills = enhanced['skills_with_confidence']
                if skills:
                    avg_skill_conf = sum(s.get('confidence', 0) for s in skills) / len(skills)
                    report['field_confidence']['skills'] = avg_skill_conf
                    confidences.append(avg_skill_conf)
            
            if 'education' in enhanced and enhanced['education']:
                edu = enhanced['education']
                if edu.get('institution'):
                    report['field_confidence']['education'] = edu.get('confidence', {}).get('institution', 0.7)
                    confidences.append(report['field_confidence']['education'])
        
        # Calculate overall
        if confidences:
            report['overall_confidence'] = round(sum(confidences) / len(confidences), 2)
        
        # Generate suggestions
        if report['overall_confidence'] < 0.8:
            report['suggestions'].append("Consider uploading a clearer PDF version of your resume")
        
        if 'skills' in report['low_confidence_fields']:
            report['suggestions'].append("Skills section could not be clearly identified. Consider using standard section headings")
        
        if 'education' in report['low_confidence_fields']:
            report['suggestions'].append("Education details unclear. Please update manually in profile")
        
        return report
    
    def extract_skills_enhanced(self, text: str) -> Dict:
        """
        Enhanced skill extraction with embeddings, taxonomy, and level detection
        """
        from app.utils.resume_parser import SkillExtractor
    
        # First, get basic skills
        basic_extractor = SkillExtractor()
        basic_skills = basic_extractor.extract_skills(text)
    
        # Get sections for context
        sections = self.classify_sections(text)
    
        # Find context for each skill
        enhanced_skills = []
    
        for skill in basic_skills[:20]:  # Limit to 20 skills for performance
            # Find context
            context = ""
            for section in sections:
                if skill.lower() in section['content'].lower():
                    context = section['content'][:200]
                    break
        
            if not context:
                # Search in full text
                pos = text.lower().find(skill.lower())
                if pos >= 0:
                    start = max(0, pos - 50)
                    end = min(len(text), pos + 50)
                    context = text[start:end]
        
            # Get similar skills
            similar = self.skill_enhancer.find_similar_skills(skill, threshold=0.6, top_k=3)
        
            # Detect skill level
            level_info = self.skill_enhancer.detect_skill_level(skill, context)
        
            # Get synonyms
            synonyms = self.skill_enhancer.get_skill_synonyms(skill)
        
            enhanced_skills.append({
                'skill': skill,
                'context': context[:100] + "..." if len(context) > 100 else context,
                'level': level_info['level'],
                'level_confidence': level_info['confidence'],
                'similar_skills': similar,
                'synonyms': synonyms,
                'confidence': 0.85
            })
    
        # Cluster skills
        clusters = self.skill_enhancer.cluster_skills(basic_skills)
    
        return {
            'skills': enhanced_skills,
            'clusters': clusters,
            'total_skills': len(enhanced_skills)
        }


# Wrapper function to use with existing ResumeParser
def enhanced_parse_resume(file_path: str, file_type: str) -> Dict:
    """
    Use AI parser to enhance the existing parsing
    """
    from app.utils.resume_parser import ResumeParser, SkillExtractor
    
    # First, use existing parser
    basic_parser = ResumeParser()
    skill_extractor = SkillExtractor()
    
    # Extract text based on file type
    if file_type == 'pdf':
        text = basic_parser.extract_text_from_pdf(file_path)
    elif file_type == 'docx':
        text = basic_parser.extract_text_from_docx(file_path)
    else:
        text = ""
    
    if not text:
        return {"error": "Could not extract text from file"}
    
    # Use AI parser for enhancement
    try:
        ai_parser = AIResumeParser()
    except Exception as e:
        logger.error(f"Failed to initialize AI parser: {e}")
        # Fallback to basic
        return {
            'basic': {
                'email': basic_parser.extract_email(text),
                'phone': basic_parser.extract_phone(text),
                'name': basic_parser.extract_name(text),
                'skills': skill_extractor.extract_skills(text),
                'education': skill_extractor.extract_education(text),
                'experience': skill_extractor.extract_experience(text),
                'projects': skill_extractor.extract_projects(text)
            },
            'enhanced': {},
            'ai_available': False
        }
    
    # Get AI-based extractions
    entities = ai_parser.extract_entities_with_confidence(text)
    sections = ai_parser.classify_sections(text)
    
    # Get basic skills
    basic_skills = skill_extractor.extract_skills(text)
    
    # Enhance skills with AI
    enhanced_skills = ai_parser.extract_skills_with_context(text, basic_skills)
    
    # Get company names
    companies = ai_parser.extract_company_names(text)
    
    # Get dates
    dates = ai_parser.extract_dates(text)
    
    # Get enhanced education
    enhanced_education = ai_parser.extract_education(text)
    
    # Get enhanced experience
    enhanced_experience = ai_parser.extract_experience(text)
    
    # Get enhanced projects
    enhanced_projects = ai_parser.extract_projects(text)
    
    # Get basic info
    basic_name = basic_parser.extract_name(text)
    basic_email = basic_parser.extract_email(text)
    basic_phone = basic_parser.extract_phone(text)
    
    # Use AI name if better
    ai_name = None
    if entities.get('PERSON'):
        # Get highest confidence person name
        persons = sorted(entities['PERSON'], key=lambda x: x['confidence'], reverse=True)
        if persons and persons[0]['confidence'] > 0.8:
            ai_name = persons[0]['text']
    
    # Combine results
    result = {
        'basic': {
            'email': basic_email,
            'phone': basic_phone,
            'name': ai_name if ai_name else basic_name,
            'skills': basic_skills,
            'education': skill_extractor.extract_education(text),
            'experience': skill_extractor.extract_experience(text),
            'projects': skill_extractor.extract_projects(text)
        },
        'enhanced': {
            'entities': entities,
            'sections': sections,
            'skills_with_confidence': enhanced_skills,
            'companies': companies,
            'dates': dates,
            'education': enhanced_education,
            'experience': enhanced_experience,
            'projects': enhanced_projects
        },
        'ai_available': True
    }
    
    # Add confidence report
    result['confidence_report'] = ai_parser.get_confidence_report(result)
    
    return result


class TrainingDataCollector:
    """
    Collects parsed resume data for future model training
    """
    
    def __init__(self, data_dir="app/ai/training_data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"📊 Training data collector initialized at {data_dir}")
    
    def save_parsed_resume(self, user_id: int, parsed_data: Dict, feedback: Optional[Dict] = None) -> str:
        """
        Save parsed resume with optional human feedback
        """
        filename = f"resume_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        data = {
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'parsed_data': parsed_data,
            'feedback': feedback  # Human correction if any
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"💾 Saved training data: {filepath}")
        return filepath
    
    def save_feedback(self, parse_id: str, corrections: Dict, user_id: int) -> bool:
        """
        Save user feedback for improving model
        """
        feedback_file = os.path.join(self.data_dir, "feedback", f"feedback_{parse_id}.json")
        os.makedirs(os.path.dirname(feedback_file), exist_ok=True)
        
        data = {
            'parse_id': parse_id,
            'user_id': user_id,
            'corrections': corrections,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return True