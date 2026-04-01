# Email templates for different notification types
import functools
import inspect

# Base URL - change this if your frontend runs on different port
BASE_URL = "http://localhost:8000"  # Backend serves frontend now

def flexible_template(func):
    """Decorator to make template functions ignore extra arguments"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get the function's argument names
        sig = inspect.signature(func)
        valid_args = {}
        
        # Sirf wahi arguments pass karo jo function accept karta hai
        for key, value in kwargs.items():
            if key in sig.parameters:
                valid_args[key] = value
        
        return func(*args, **valid_args)
    return wrapper

@flexible_template
def get_welcome_email_template(user_name: str, login_url: str = None) -> str:
    """Welcome email for new registration"""
    if login_url is None:
        login_url = f"{BASE_URL}/login.html"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A1929, #1A2A3A); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .btn {{ background: #F0B90B; color: #0A1929; padding: 12px 30px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎓 Placement System</h1>
                <p>Welcome Aboard!</p>
            </div>
            <div class="content">
                <h2>Hello {user_name}!</h2>
                <p>Thank you for registering with our AI-Powered Placement System. Your account has been successfully created.</p>
                
                <h3>🚀 Next Steps:</h3>
                <ul>
                    <li>Complete your profile with academic details</li>
                    <li>Upload your resume for AI analysis</li>
                    <li>Browse active placement drives</li>
                    <li>Get personalized job recommendations</li>
                </ul>
                
                <div style="text-align: center;">
                    <a href="{login_url}" class="btn">Login to Dashboard</a>
                </div>
                
                <p><strong>Quick Tips:</strong><br>
                • A complete profile increases your chances by 70%<br>
                • AI predictions help you prepare better<br>
                • Apply early to avoid missing deadlines</p>
            </div>
            <div class="footer">
                <p>© 2026 Placement System. All rights reserved.<br>
                This is an automated message, please do not reply.</p>
            </div>
        </div>
    </html>
    """

@flexible_template
def get_drive_announcement_template(drive_title: str, company_name: str, last_date: str, eligibility: str, drive_url: str = None) -> str:
    """New drive announcement email"""
    if drive_url is None:
        drive_url = f"{BASE_URL}/drives.html"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A1929, #1A2A3A); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .btn {{ background: #F0B90B; color: #0A1929; padding: 12px 30px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block; margin: 20px 0; }}
            .info-box {{ background: white; border-left: 4px solid #F0B90B; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎓 Placement System</h1>
                <p>New Opportunity Alert!</p>
            </div>
            <div class="content">
                <h2>New Placement Drive: {drive_title}</h2>
                
                <div class="info-box">
                    <p><strong>🏢 Company:</strong> {company_name}</p>
                    <p><strong>📅 Last Date to Apply:</strong> {last_date}</p>
                    <p><strong>🎯 Eligibility:</strong> {eligibility}</p>
                </div>
                
                <p>A new placement opportunity has been announced. Check your eligibility and apply before the deadline!</p>
                
                <div style="text-align: center;">
                    <a href="{drive_url}" class="btn">View Drive Details</a>
                </div>
                
                <p><small>⚠️ Don't wait until the last day - apply early!</small></p>
            </div>
            <div class="footer">
                <p>© 2026 Placement System. All rights reserved.</p>
            </div>
        </div>
    </html>
    """

@flexible_template
def get_status_update_template(student_name: str, company_name: str, job_title: str, old_status: str, new_status: str, dashboard_url: str = None) -> str:
    """Application status change notification"""
    
    if dashboard_url is None:
        dashboard_url = f"{BASE_URL}/applications.html"
    
    # Status ke according color aur message
    status_colors = {
        'shortlisted': '#27AE60',
        'selected': '#27AE60',
        'rejected': '#EB5757',
        'applied': '#F0B90B'
    }
    
    status_messages = {
        'shortlisted': 'Congratulations! You have been shortlisted for the next round.',
        'selected': '🎉 Congratulations! You have been selected!',
        'rejected': 'We regret to inform you that you have not been selected for this position.',
        'applied': 'Your application status has been updated.'
    }
    
    color = status_colors.get(new_status, '#F0B90B')
    message = status_messages.get(new_status, f'Your application status changed from {old_status} to {new_status}')
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A1929, #1A2A3A); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .btn {{ background: #F0B90B; color: #0A1929; padding: 12px 30px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block; margin: 20px 0; }}
            .status-box {{ background: white; border-left: 4px solid {color}; padding: 20px; margin: 20px 0; border-radius: 5px; }}
            .old-status {{ color: #999; text-decoration: line-through; }}
            .new-status {{ color: {color}; font-weight: bold; font-size: 18px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎓 Placement System</h1>
                <p>Application Status Update</p>
            </div>
            <div class="content">
                <h2>Hello {student_name}!</h2>
                
                <p>Your application status has been updated for <strong>{company_name} - {job_title}</strong></p>
                
                <div class="status-box">
                    <p><span class="old-status">{old_status}</span> → <span class="new-status">{new_status}</span></p>
                    <p style="margin-top: 15px;"><strong>{message}</strong></p>
                </div>
                
                <div style="text-align: center;">
                    <a href="{dashboard_url}" class="btn">View My Applications</a>
                </div>
            </div>
            <div class="footer">
                <p>© 2026 Placement System. All rights reserved.</p>
            </div>
        </div>
    </html>
    """

@flexible_template
def get_password_reset_template(user_name: str, reset_link: str, expiry_hours: int = 24) -> str:
    """Password reset email"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A1929, #1A2A3A); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .btn {{ background: #F0B90B; color: #0A1929; padding: 12px 30px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block; margin: 20px 0; }}
            .warning {{ background: #FFEBEE; color: #EB5757; padding: 15px; border-radius: 5px; margin: 20px 0; font-size: 14px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎓 Placement System</h1>
                <p>Password Reset Request</p>
            </div>
            <div class="content">
                <h2>Hello {user_name}!</h2>
                
                <p>We received a request to reset your password. Click the button below to set a new password:</p>
                
                <div style="text-align: center;">
                    <a href="{reset_link}" class="btn">Reset Password</a>
                </div>
                
                <div class="warning">
                    <p><strong>⚠️ Important:</strong></p>
                    <ul>
                        <li>This link will expire in {expiry_hours} hours</li>
                        <li>If you didn't request this, please ignore this email</li>
                        <li>Never share this link with anyone</li>
                    </ul>
                </div>
                
                <p>Or copy this link to your browser:<br>
                <small>{reset_link}</small></p>
            </div>
            <div class="footer">
                <p>© 2026 Placement System. All rights reserved.</p>
            </div>
        </div>
    </html>
    """

@flexible_template
def get_simple_text_email(title: str, message: str) -> str:
    """Simple email template for general notifications"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A1929, #1A2A3A); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎓 Placement System</h1>
                <p>{title}</p>
            </div>
            <div class="content">
                <p>{message}</p>
            </div>
            <div class="footer">
                <p>© 2026 Placement System. All rights reserved.</p>
            </div>
        </div>
    </html>
    """

# ===== NEW OTP Templates =====

@flexible_template
def get_verify_otp_template(user_name: str, otp_code: str, expiry_minutes: int = 10, email: str = None) -> str:
    """OTP verification email template"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A1929, #1A2A3A); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .otp-box {{ background: #0A1929; color: #F0B90B; font-size: 32px; font-weight: bold; padding: 20px; text-align: center; border-radius: 10px; letter-spacing: 5px; margin: 20px 0; }}
            .btn {{ background: #F0B90B; color: #0A1929; padding: 12px 30px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block; margin: 20px 0; }}
            .warning {{ background: #FFEBEE; color: #EB5757; padding: 15px; border-radius: 5px; margin: 20px 0; font-size: 14px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎓 Placement System</h1>
                <p>Email Verification</p>
            </div>
            <div class="content">
                <h2>Hello {user_name}!</h2>
                <p>Thank you for registering with our AI-Powered Placement System. Please verify your email address using the OTP below:</p>
                
                <div class="otp-box">
                    {otp_code}
                </div>
                
                <p>This OTP will expire in <strong>{expiry_minutes} minutes</strong>.</p>
                
                <div class="warning">
                    <p><strong>⚠️ Important:</strong></p>
                    <ul>
                        <li>Never share this OTP with anyone</li>
                        <li>Our team will never ask for your OTP</li>
                        <li>If you didn't request this, please ignore this email</li>
                    </ul>
                </div>
                
                <div style="text-align: center;">
                    <a href="{BASE_URL}/verify-otp.html?email={email}" class="btn">Verify Email</a>
                </div>
            </div>
            <div class="footer">
                <p>© 2026 Placement System. All rights reserved.</p>
            </div>
        </div>
    </html>
    """

@flexible_template
def get_password_reset_otp_template(user_name: str, otp_code: str, expiry_minutes: int = 10, email: str = None) -> str:
    """Password reset OTP email template"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A1929, #1A2A3A); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .otp-box {{ background: #0A1929; color: #F0B90B; font-size: 32px; font-weight: bold; padding: 20px; text-align: center; border-radius: 10px; letter-spacing: 5px; margin: 20px 0; }}
            .btn {{ background: #F0B90B; color: #0A1929; padding: 12px 30px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block; margin: 20px 0; }}
            .warning {{ background: #FFEBEE; color: #EB5757; padding: 15px; border-radius: 5px; margin: 20px 0; font-size: 14px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎓 Placement System</h1>
                <p>Password Reset Request</p>
            </div>
            <div class="content">
                <h2>Hello {user_name}!</h2>
                
                <p>We received a request to reset your password. Use the OTP below to proceed:</p>
                
                <div class="otp-box">
                    {otp_code}
                </div>
                
                <p>This OTP will expire in <strong>{expiry_minutes} minutes</strong>.</p>
                
                <div class="warning">
                    <p><strong>⚠️ Important:</strong></p>
                    <ul>
                        <li>Never share this OTP with anyone</li>
                        <li>If you didn't request this, please ignore this email</li>
                        <li>After OTP verification, you'll be able to set a new password</li>
                    </ul>
                </div>
                
                <div style="text-align: center;">
                    <a href="{BASE_URL}/reset-password.html?email={email}" class="btn">Reset Password</a>
                </div>
            </div>
            <div class="footer">
                <p>© 2026 Placement System. All rights reserved.</p>
            </div>
        </div>
    </html>
    """

@flexible_template
def get_shortlist_email_template(student_name: str, company_name: str, job_title: str, dashboard_url: str = None) -> str:
    """Shortlist notification email template"""
    
    if dashboard_url is None:
        dashboard_url = f"{BASE_URL}/applications.html"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A1929, #1A2A3A); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .btn {{ background: #F0B90B; color: #0A1929; padding: 12px 30px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block; margin: 20px 0; }}
            .success-box {{ background: #D4EDDA; border-left: 4px solid #27AE60; padding: 20px; margin: 20px 0; border-radius: 5px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎓 Placement System</h1>
                <p>Application Status Update</p>
            </div>
            <div class="content">
                <div class="success-box">
                    <h2 style="color: #27AE60; margin-top: 0;">🎉 Congratulations {student_name}!</h2>
                </div>
                
                <h3>You have been <span style="color: #27AE60; font-weight: bold;">SHORTLISTED</span>!</h3>
                
                <p>We are pleased to inform you that you have been shortlisted for the next round of:</p>
                
                <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0; border: 1px solid #E0E0E0;">
                    <p style="font-size: 18px; margin: 0;">
                        <strong>🏢 Company:</strong> {company_name}<br>
                        <strong>💼 Position:</strong> {job_title}
                    </p>
                </div>
                
                <p><strong>📌 Next Steps:</strong></p>
                <ul>
                    <li>Check your dashboard for further updates</li>
                    <li>Prepare for the next round of interviews</li>
                    <li>Keep an eye on your email for further communication</li>
                </ul>
                
                <div style="text-align: center;">
                    <a href="{dashboard_url}" class="btn">View Application Status</a>
                </div>
                
                <p style="margin-top: 30px; font-style: italic;">
                    "Success is not final, failure is not fatal: it is the courage to continue that counts."
                </p>
            </div>
            <div class="footer">
                <p>© 2026 Placement System. All rights reserved.</p>
                <p>This is an automated message, please do not reply.</p>
            </div>
        </div>
    </html>
    """

@flexible_template
def get_drive_update_template(student_name: str = None, drive_title: str = None, 
                              company_name: str = None, last_date: str = None, 
                              eligibility: str = None, changes: list = None, 
                              changes_html: str = None, drive_url: str = None, 
                              old_last_date: str = None, old_job_title: str = None, 
                              is_update: bool = True, **kwargs) -> str:
    """Drive update announcement email with detailed changes - FIXED VERSION"""
    
    if drive_url is None:
        drive_url = f"{BASE_URL}/drives.html"
    
    # ✅ Default values handle karo
    student_name = student_name or "Student"
    drive_title = drive_title or "Position"
    company_name = company_name or "Company"
    last_date = last_date or "N/A"
    eligibility = eligibility or "N/A"
    
    # ✅ Changes ko properly format karo
    changes_display = ""
    if changes and len(changes) > 0:
        changes_list_html = ""
        for change in changes:
            changes_list_html += f"<li>{change}</li>"
        
        changes_display = f"""
        <div class="update-box" style="background: #FFF3E0; border-left: 4px solid #F2994A; padding: 15px; margin: 20px 0; border-radius: 5px;">
            <p><strong>📋 What Changed:</strong></p>
            <ul style="margin: 10px 0;">
                {changes_list_html}
            </ul>
        </div>
        """
    else:
        changes_display = f"""
        <div class="update-box" style="background: #FFF3E0; border-left: 4px solid #F2994A; padding: 15px; margin: 20px 0; border-radius: 5px;">
            <p><strong>📋 Drive Details Updated:</strong> The placement drive information has been modified. Please review the updated details below.</p>
        </div>
        """
    
    # ✅ Proper HTML email with inline styles
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A1929, #1A2A3A); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .btn {{ background: #F0B90B; color: #0A1929; padding: 12px 30px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block; margin: 20px 0; }}
            .info-box {{ background: white; border-left: 4px solid #F0B90B; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            .update-box {{ background: #FFF3E0; border-left: 4px solid #F2994A; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎓 Placement System</h1>
                <p>Drive Details Updated!</p>
            </div>
            <div class="content">
                <h2>Hello {student_name}!</h2>
                
                <p>A placement drive you might be interested in has been updated:</p>
                
                <div class="info-box">
                    <p><strong>🏢 Company:</strong> {company_name}</p>
                    <p><strong>💼 Position:</strong> {drive_title}</p>
                    <p><strong>📅 Last Date to Apply:</strong> <span style="color: #EB5757; font-weight: bold;">{last_date}</span></p>
                    <p><strong>🎯 Eligibility:</strong> {eligibility}</p>
                </div>
                
                {changes_display}
                
                <p>Please review the updated details carefully. If you haven't applied yet, make sure to check the new requirements.</p>
                
                <div style="text-align: center;">
                    <a href="{drive_url}" class="btn">View Updated Drive Details</a>
                </div>
                
                <p><small>⚠️ Don't wait until the last day - apply early if you're eligible!</small></p>
                
                <hr style="margin: 20px 0; border-color: #E5E7EB;">
                
                <p style="font-size: 12px; color: #666;">
                    This is an automated notification from Placement System. If you have already applied for this drive, 
                    your application remains valid. The drive details have been updated by the admin.
                </p>
            </div>
            <div class="footer">
                <p>© 2026 Placement System. All rights reserved.</p>
                <p>This is an automated message, please do not reply.</p>
            </div>
        </div>
    </html>
    """
    
    return html