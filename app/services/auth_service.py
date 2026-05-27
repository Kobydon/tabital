from psycopg2 import IntegrityError

from ..models.user import User
from ..extensions import *

def register_user(data):
    user = User(**data)

    user.password = guard.hash_password(data.get("password"))

    # IMPORTANT LOGIC
    if user.role == "admin":
        user.status = "approved"
    else:
        user.status = "pending"

    try:
        db.session.add(user)
        db.session.commit()
        return user
        
    except IntegrityError as e:
        db.session.rollback()  # CRITICAL: Rollback the failed transaction
        
        error_message = str(e.orig) if e.orig else str(e)
        
        # Check for duplicate email (business_email)
        if 'business_email' in error_message.lower():
            raise ValueError({
                'field': 'business_email',
                'message': 'This email address is already registered. Please use a different email or login.'
            })
        
        # Check for duplicate phone number
        elif 'phone' in error_message.lower():
            raise ValueError({
                'field': 'phone',
                'message': 'This phone number is already registered. Please use a different number or login.'
            })
        
        # Generic integrity error
        else:
            raise ValueError({
                'field': 'general',
                'message': 'Registration failed. The information you provided may already be registered.'
            })
            
    except Exception as e:
        db.session.rollback()
        raise e


from sqlalchemy import or_

def login_user(identifier, password):
    """
    Login with phone OR business_email
    """

    # FIND USER BY PHONE OR BUSINESS EMAIL
    user = User.query.filter(
        or_(
            User.phone == identifier,
            User.business_email == identifier.lower()
        )
    ).first()

    # USER NOT FOUND
    if not user:
        raise Exception("Invalid phone/email or password")

    # VERIFY PASSWORD
    if not guard.pwd_ctx.verify(password, user.password):
        raise Exception("Invalid phone/email or password")

    # CHECK APPROVAL
    if user.status != "approved":
        raise Exception(
            "Account not approved yet. Please wait for admin approval."
        )

    # GENERATE TOKEN
    token = guard.encode_jwt_token(user)

    return token



# resources/auth.py - Updated with Flask-Mail
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from flask_mail import Message
from ..models.user import User
from ..extensions import db, mail
from datetime import datetime, timedelta
import random
import string

class ForgotPasswordResource(Resource):
    def post(self):
        """Request password reset - sends OTP to user's email"""
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return {"error": "Email address is required"}, 400
        
        # Find user by email
        user = User.query.filter_by(business_email=email).first()
        
        if not user:
            # For security, don't reveal if user exists
            return {"message": "If your account exists, you will receive a password reset email"}, 200
        
        # Generate 6-digit OTP
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Store OTP with expiry (10 minutes)
        user.reset_otp = otp
        user.reset_otp_expiry = datetime.now() + timedelta(minutes=10)
        db.session.commit()
        
        # Send email with OTP
        try:
            msg = Message(
                subject="Tabital Pay - Password Reset Code",
                recipients=[email],
                html=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Password Reset - Tabital Pay</title>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            background-color: #f5f7fa;
                            margin: 0;
                            padding: 0;
                        }}
                        .container {{
                            max-width: 600px;
                            margin: 0 auto;
                            background: white;
                            border-radius: 16px;
                            overflow: hidden;
                            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                        }}
                        .header {{
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            padding: 30px;
                            text-align: center;
                        }}
                        .header h1 {{
                            color: white;
                            margin: 0;
                            font-size: 28px;
                        }}
                        .content {{
                            padding: 30px;
                        }}
                        .otp-code {{
                            background: #f0f2f5;
                            padding: 20px;
                            text-align: center;
                            font-size: 32px;
                            font-weight: 700;
                            letter-spacing: 8px;
                            color: #667eea;
                            border-radius: 12px;
                            margin: 20px 0;
                        }}
                        .button {{
                            display: inline-block;
                            padding: 12px 30px;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            text-decoration: none;
                            border-radius: 30px;
                            margin: 20px 0;
                        }}
                        .footer {{
                            padding: 20px;
                            text-align: center;
                            background: #f8f9fa;
                            color: #6c757d;
                            font-size: 12px;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>🔐 Tabital Pay</h1>
                        </div>
                        <div class="content">
                            <h2>Password Reset Request</h2>
                            <p>Hello {user.full_name or user.business_name or 'User'},</p>
                            <p>We received a request to reset your password. Use the OTP code below to proceed:</p>
                            <div class="otp-code">
                                {otp}
                            </div>
                            <p>This OTP is valid for <strong>10 minutes</strong>. If you didn't request this, please ignore this email.</p>
                            <p>For security reasons, never share this OTP with anyone.</p>
                        </div>
                        <div class="footer">
                            <p>&copy; 2024 Tabital Pay. All rights reserved.</p>
                            <p>Secure payment platform for your business</p>
                        </div>
                    </div>
                </body>
                </html>
                """
            )
            mail.send(msg)
            print(f"Password reset OTP sent to {email}: {otp}")  # For debugging
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return {"error": "Failed to send reset email. Please try again."}, 500
        
        return {
            "message": "Password reset code sent to your email",
            "email": email
        }, 200


class VerifyResetOTPResource(Resource):
    def post(self):
        """Verify OTP and return reset token"""
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')
        
        if not email or not otp:
            return {"error": "Email and OTP are required"}, 400
        
        user = User.query.filter_by(business_email=email).first()
        
        if not user:
            return {"error": "Invalid request"}, 404
        
        if not user.reset_otp or user.reset_otp != otp:
            return {"error": "Invalid OTP code"}, 401
        
        if user.reset_otp_expiry and user.reset_otp_expiry < datetime.now():
            return {"error": "OTP has expired. Please request a new one."}, 401
        
        # Generate reset token
        reset_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        user.reset_token = reset_token
        user.reset_token_expiry = datetime.now() + timedelta(minutes=30)
        db.session.commit()
        
        return {
            "message": "OTP verified successfully",
            "reset_token": reset_token
        }, 200


class ResetPasswordResource(Resource):
    def post(self):
        """Reset password using token"""
        data = request.get_json()
        reset_token = data.get('reset_token')
        new_password = data.get('new_password')
        
        if not reset_token or not new_password:
            return {"error": "Reset token and new password are required"}, 400
        
        if len(new_password) < 6:
            return {"error": "Password must be at least 6 characters"}, 400
        
        user = User.query.filter_by(reset_token=reset_token).first()
        
        if not user:
            return {"error": "Invalid or expired reset token"}, 404
        
        if user.reset_token_expiry and user.reset_token_expiry < datetime.now():
            return {"error": "Reset token has expired. Please request a new one."}, 401
        
        # Update password
        # from flask_praetorian import Praetorian
        # guard = Praetorian()
        user.password = guard.encrypt_password(new_password)
        
        # Clear reset fields
        user.reset_otp = None
        user.reset_otp_expiry = None
        user.reset_token = None
        user.reset_token_expiry = None
        
        db.session.commit()
        
        # Send confirmation email
        try:
            msg = Message(
                subject="Tabital Pay - Password Changed Successfully",
                recipients=[user.email],
                html=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Password Changed - Tabital Pay</title>
                </head>
                <body style="font-family: Arial, sans-serif;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #28a745;">✅ Password Changed Successfully</h2>
                        <p>Hello {user.full_name or user.business_name or 'User'},</p>
                        <p>Your password has been successfully changed.</p>
                        <p>If you did not make this change, please contact our support team immediately.</p>
                        <hr>
                        <p style="color: #6c757d; font-size: 12px;">Tabital Pay - Secure Payment Platform</p>
                    </div>
                </body>
                </html>
                """
            )
            mail.send(msg)
        except Exception as e:
            print(f"Error sending confirmation email: {e}")
        
        return {"message": "Password reset successfully. You can now login."}, 200