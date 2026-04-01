from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime

# User models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "student"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    created_at: datetime

# Student profile models - FIXED with Optional fields
class StudentProfileCreate(BaseModel):
    full_name: Optional[str] = None  # ADD THIS LINE
    roll_number: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[int] = None
    cgpa: Optional[float] = None
    skills: Optional[str] = None

class StudentProfileResponse(BaseModel):
    id: int
    user_id: int
    full_name: Optional[str] = None  # ADD THIS LINE
    roll_number: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[int] = None
    cgpa: Optional[float] = None
    skills: Optional[str] = None
    resume_path: Optional[str] = None

# Token models
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

# Company models
class CompanyCreate(BaseModel):
    name: str
    description: str
    industry: str
    website: str

# Drive models
class DriveCreate(BaseModel):
    company_id: int
    job_title: str
    job_description: str
    eligibility_cgpa: float
    required_skills: str
    min_experience: int = 0
    max_offers: int
    last_date: date
    allowed_branches: Optional[str] = None
    max_backlogs: Optional[int] = 0
    min_tenth: Optional[float] = None
    min_twelfth: Optional[float] = None
    status: Optional[str] = "active"

class DriveResponse(DriveCreate):
    id: int
    status: str
    created_at: datetime
    company_name: Optional[str] = None