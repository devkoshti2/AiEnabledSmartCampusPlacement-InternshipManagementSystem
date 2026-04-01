from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.auth import require_admin
from app.database import get_db_connection
import csv
import io
import pandas as pd
from datetime import datetime
import logging

router = APIRouter(prefix="/export", tags=["Export"])
logger = logging.getLogger(__name__)

@router.get("/students")
async def export_students(admin = Depends(require_admin)):
    """Export all students to CSV"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # REAL DATA - Sab students lo
        cursor.execute("""
            SELECT 
                u.id,
                u.full_name,
                u.email,
                u.role,
                u.created_at as registration_date,
                u.email_verified,
                sp.roll_number,
                sp.branch,
                sp.semester,
                sp.cgpa,
                sp.skills,
                sp.resume_path,
                (SELECT COUNT(*) FROM applications a JOIN student_profiles sp2 ON a.student_id = sp2.id WHERE sp2.user_id = u.id) as total_applications,
                (SELECT COUNT(*) FROM applications a 
                JOIN student_profiles sp2 ON a.student_id = sp2.id 
                WHERE sp2.user_id = u.id AND a.status = 'selected') as selections
            FROM users u
            LEFT JOIN student_profiles sp ON u.id = sp.user_id
            WHERE u.role = 'student'
            ORDER BY u.id
        """)
        
        students = cursor.fetchall()
        
        if not students:
            students = []  # Empty list agar koi student na ho
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        if students:
            writer.writerow(students[0].keys())
            for student in students:
                writer.writerow(student.values())
        else:
            writer.writerow(['id', 'name', 'email', 'branch', 'cgpa', 'applications'])
        
        output.seek(0)
        
        filename = f"students_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()
        
@router.get("/companies")
async def export_companies(admin = Depends(require_admin)):
    """Export all companies to CSV"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM companies ORDER BY name")
        companies = cursor.fetchall()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if companies:
            writer.writerow(companies[0].keys())
        
        for company in companies:
            writer.writerow(company.values())
        
        output.seek(0)
        
        filename = f"companies_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    finally:
        cursor.close()
        conn.close()

@router.get("/drives")
async def export_drives(admin = Depends(require_admin)):
    """Export all drives to CSV"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT 
                pd.id, c.name as company_name, pd.job_title, pd.job_description,
                pd.eligibility_cgpa, pd.required_skills, pd.min_experience,
                pd.max_offers, pd.last_date, pd.status, pd.created_at,
                (SELECT COUNT(*) FROM applications WHERE drive_id = pd.id) as total_applications
            FROM placement_drives pd
            JOIN companies c ON pd.company_id = c.id
            ORDER BY pd.created_at DESC
        """)
        
        drives = cursor.fetchall()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if drives:
            writer.writerow(drives[0].keys())
        
        for drive in drives:
            writer.writerow(drive.values())
        
        output.seek(0)
        
        filename = f"drives_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    finally:
        cursor.close()
        conn.close()

@router.get("/applications")
async def export_applications(admin = Depends(require_admin)):
    """Export all applications to CSV"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT 
                a.id, u.full_name as student_name, sp.roll_number, sp.branch, sp.cgpa,
                c.name as company_name, pd.job_title, a.status, a.applied_at
            FROM applications a
            JOIN student_profiles sp ON a.student_id = sp.id
            JOIN users u ON sp.user_id = u.id
            JOIN placement_drives pd ON a.drive_id = pd.id
            JOIN companies c ON pd.company_id = c.id
            ORDER BY a.applied_at DESC
        """)
        
        apps = cursor.fetchall()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if apps:
            writer.writerow(apps[0].keys())
        
        for app in apps:
            writer.writerow(app.values())
        
        output.seek(0)
        
        filename = f"applications_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    finally:
        cursor.close()
        conn.close()