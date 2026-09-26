"""Every login attempt: used to slow down password guessing (services/auth_service.py) and for audit."""
from datetime import datetime

from ..extensions import db


class LoginAttempt(db.Model):
    __tablename__ = 'login_attempts'

    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(120), nullable=False, index=True)   # phone or email as typed (normalised)
    ip = db.Column(db.String(64), index=True)
    success = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
