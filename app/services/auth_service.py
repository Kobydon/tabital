import hmac
import secrets
from datetime import datetime, timedelta

from flask import current_app
from flask_mail import Message
from flask_restful import Resource, request
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from ..extensions import db, guard, mail
from ..models.user import User


# Only these fields can be set at sign-up. Status, KYC, IDs, commission and payout fields
# are set by Tabital, never by the person registering. Admins are created with a CLI command.
CUSTOMER_SIGNUP_FIELDS = {
    'full_name', 'business_email', 'phone', 'dob', 'city', 'gps', 'address',
    'designation', 'company', 'income_range', 'ref_name', 'ref_phone',
    'ref_relationship', 'agree',
}
MERCHANT_SIGNUP_FIELDS = {
    'business_name', 'owner_name', 'phone', 'city', 'address', 'product_type',
    'has_shop', 'shop_url', 'years_in_business', 'business_type', 'business_address',
    'business_phone', 'business_email', 'description', 'agree',
}
SIGNUP_FIELDS = {'customer': CUSTOMER_SIGNUP_FIELDS, 'merchant': MERCHANT_SIGNUP_FIELDS}

MIN_PASSWORD_LENGTH = 6
OTP_TTL = timedelta(minutes=10)
OTP_RESEND_AFTER = timedelta(minutes=1)
OTP_MAX_ATTEMPTS = 5
RESET_TOKEN_TTL = timedelta(minutes=30)


class RegistrationError(ValueError):
    def __init__(self, field, message, status=400):
        super().__init__(message)
        self.field = field
        self.message = message
        self.status = status


def register_user(data):
    role = (data.get('role') or '').strip().lower()
    if role not in SIGNUP_FIELDS:
        raise RegistrationError('role', 'Role must be customer or merchant')

    password = data.get('password') or ''
    if len(password) < MIN_PASSWORD_LENGTH:
        raise RegistrationError('password', f'Password must be at least {MIN_PASSWORD_LENGTH} characters')
    if not (data.get('phone') or '').strip():
        raise RegistrationError('phone', 'Phone number is required')

    fields = {k: v for k, v in data.items() if k in SIGNUP_FIELDS[role]}
    if fields.get('business_email'):
        fields['business_email'] = fields['business_email'].strip().lower()

    user = User(**fields)
    user.role = role
    user.status = 'pending'
    user.password = guard.hash_password(password)

    try:
        db.session.add(user)
        db.session.commit()
        return user
    except IntegrityError as e:
        db.session.rollback()
        error_message = str(e.orig).lower() if e.orig else str(e).lower()
        if 'business_email' in error_message:
            raise RegistrationError('business_email', 'This email address is already registered. Please use a different email or login.', 409)
        if 'phone' in error_message:
            raise RegistrationError('phone', 'This phone number is already registered. Please use a different number or login.', 409)
        raise RegistrationError('general', 'Registration failed. The information you provided may already be registered.', 409)


class AuthError(Exception):
    def __init__(self, message, status):
        super().__init__(message)
        self.message = message
        self.status = status


def login_user(identifier, password):
    """Login with phone OR business_email. Returns a JWT or raises AuthError."""
    identifier = (identifier or '').strip()
    if not identifier or not password:
        raise AuthError('Phone and password are required', 400)

    user = User.query.filter(
        or_(User.phone == identifier, User.business_email == identifier.lower())
    ).first()

    if not user or not guard.pwd_ctx.verify(password, user.password):
        raise AuthError('Invalid phone or password', 401)

    if user.status not in ('approved', 'active'):
        raise AuthError('Account not approved yet. Please wait for admin approval.', 403)

    return guard.encode_jwt_token(user)


def _generic_reset_response():
    # Same response whether or not the account exists, so the endpoint can't be used to find accounts
    return {"message": "If your account exists, you will receive a password reset email"}, 200


class ForgotPasswordResource(Resource):
    def post(self):
        """Request password reset - sends OTP to user's email"""
        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()

        if not email:
            return {"error": "Email address is required"}, 400

        user = User.query.filter_by(business_email=email).first()
        if not user:
            return _generic_reset_response()

        now = datetime.utcnow()
        # Throttle: one code per minute
        if user.reset_otp_expiry and user.reset_otp_expiry - OTP_TTL + OTP_RESEND_AFTER > now:
            return _generic_reset_response()

        otp = f"{secrets.randbelow(1_000_000):06d}"
        user.reset_otp = otp
        user.reset_otp_expiry = now + OTP_TTL
        user.reset_otp_attempts = 0
        db.session.commit()

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
                            <p>&copy; Tabital Pay. All rights reserved.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
            )
            mail.send(msg)
        except Exception:
            current_app.logger.exception("Failed to send password reset email")
            return {"error": "Failed to send reset email. Please try again."}, 500

        return _generic_reset_response()


class VerifyResetOTPResource(Resource):
    def post(self):
        """Verify OTP and return reset token"""
        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()
        otp = str(data.get('otp') or '').strip()

        if not email or not otp:
            return {"error": "Email and OTP are required"}, 400

        user = User.query.filter_by(business_email=email).first()
        if not user or not user.reset_otp:
            return {"error": "Invalid or expired OTP code"}, 401

        if user.reset_otp_expiry and user.reset_otp_expiry < datetime.utcnow():
            return {"error": "OTP has expired. Please request a new one."}, 401

        if (user.reset_otp_attempts or 0) >= OTP_MAX_ATTEMPTS:
            user.reset_otp = None
            db.session.commit()
            return {"error": "Too many attempts. Please request a new code."}, 429

        if not hmac.compare_digest(user.reset_otp, otp):
            user.reset_otp_attempts = (user.reset_otp_attempts or 0) + 1
            db.session.commit()
            return {"error": "Invalid OTP code"}, 401

        user.reset_otp = None
        user.reset_otp_attempts = 0
        user.reset_token = secrets.token_urlsafe(32)
        user.reset_token_expiry = datetime.utcnow() + RESET_TOKEN_TTL
        db.session.commit()

        return {
            "message": "OTP verified successfully",
            "reset_token": user.reset_token
        }, 200


class ResetPasswordResource(Resource):
    def post(self):
        """Reset password using token"""
        data = request.get_json() or {}
        reset_token = data.get('reset_token')
        new_password = data.get('new_password') or ''

        if not reset_token or not new_password:
            return {"error": "Reset token and new password are required"}, 400

        if len(new_password) < MIN_PASSWORD_LENGTH:
            return {"error": f"Password must be at least {MIN_PASSWORD_LENGTH} characters"}, 400

        user = User.query.filter_by(reset_token=reset_token).first()
        if not user:
            return {"error": "Invalid or expired reset token"}, 404

        if user.reset_token_expiry and user.reset_token_expiry < datetime.utcnow():
            return {"error": "Reset token has expired. Please request a new one."}, 401

        user.password = guard.hash_password(new_password)
        user.reset_otp = None
        user.reset_otp_expiry = None
        user.reset_otp_attempts = 0
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()

        recipient = user.business_email or user.email
        if recipient:
            try:
                msg = Message(
                    subject="Tabital Pay - Password Changed Successfully",
                    recipients=[recipient],
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
            except Exception:
                current_app.logger.exception("Failed to send password change confirmation")

        return {"message": "Password reset successfully. You can now login."}, 200


def change_password(user, current_password, new_password):
    """Shared by the customer and merchant password endpoints. Returns (body, status)."""
    if not current_password or not new_password:
        return {"error": "Current password and new password are required"}, 400
    if not guard.pwd_ctx.verify(current_password, user.password):
        return {"error": "Current password is incorrect"}, 401
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return {"error": f"New password must be at least {MIN_PASSWORD_LENGTH} characters"}, 400
    user.password = guard.hash_password(new_password)
    db.session.commit()
    return {"message": "Password updated successfully"}, 200
