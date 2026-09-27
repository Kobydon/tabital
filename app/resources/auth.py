from flask import request
from flask_restful import Resource

from app.models.user import User
from ..services.auth_service import AuthError, RegistrationError, login_user, register_user


class RegisterResource(Resource):
    def post(self):
        """Sign-up. It has to say when a phone/email is already registered, so failed sign-ups are
        limited per IP (services/attempts.py) to stop it being used to look up who has an account."""
        from datetime import datetime, timedelta
        from flask import current_app
        from ..models.login_attempt import LoginAttempt
        from ..services import attempts

        data = request.get_json() or {}
        ip = attempts.client_ip()
        now = datetime.utcnow()
        window = now - timedelta(minutes=current_app.config.get('LOGIN_WINDOW_MINUTES', 15))
        subject = f"ip:{ip}"
        if ip and attempts.failures(LoginAttempt.SIGNUP, subject, window) >= \
                current_app.config.get('SIGNUP_MAX_FAILURES_PER_IP', 10):
            return {"error": "Too many sign-up attempts. Please wait a few minutes and try again."}, 429
        try:
            register_user(data)
        except RegistrationError as e:
            if e.status == 409:            # "already registered" answers are what an attacker wants
                attempts.begin(LoginAttempt.SIGNUP, subject, (data.get('phone') or '')[:120], ip, now)
            return {"error": e.message, "field": e.field, e.field: e.message}, e.status
        return {"message": "User registered successfully"}, 201


class LoginResource(Resource):
    def post(self):
        data = request.get_json() or {}
        try:
            token = login_user(data.get("phone"), data.get("password"))
        except AuthError as e:
            return {"error": e.message, "message": e.message}, e.status
        _record_login_device(data.get("phone"))
        return {"access_token": token}, 200


def _record_login_device(phone):
    """Device checks (§9D). Never stops a login: a failure here is only logged."""
    from flask import current_app
    from ..extensions import db
    from ..services import fraud
    try:
        user = User.query.filter_by(phone=(phone or '').strip()).first()
        if user:
            fraud.record_device(user)
            db.session.commit()
    except Exception:                      # noqa: BLE001
        db.session.rollback()
        current_app.logger.exception("Device check failed at login")


class CheckUserExistsResource(Resource):
    def post(self):
        """Turned off: a public "is this phone/email registered?" lookup let anyone collect the phone
        numbers of Tabital customers. Sign-up reports a duplicate when the form is submitted."""
        return {"error": "Not available. Sign-up tells you if the phone or email is already registered."}, 410
