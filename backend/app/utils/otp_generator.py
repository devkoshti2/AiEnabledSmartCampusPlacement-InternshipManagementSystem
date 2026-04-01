import random
from datetime import datetime, timedelta
import secrets

class OTPGenerator:
    @staticmethod
    def generate_otp(length=6):
        """6-digit OTP generate kare"""
        otp = ''.join([str(random.randint(0, 9)) for _ in range(length)])
        return otp
    
    @staticmethod
    def generate_expiry(minutes=10):
        """Expiry time calculate kare"""
        return datetime.now() + timedelta(minutes=minutes)
    
    @staticmethod
    def generate_secure_token():
        """Secure token generate kare"""
        return secrets.token_urlsafe(32)

otp_generator = OTPGenerator()