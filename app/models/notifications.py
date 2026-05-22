# models/notification.py
from ..extensions import db
from datetime import datetime
import json

class Notifications(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    notifications_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Recipient
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_role = db.Column(db.String(50), nullable=False)  # customer, merchant, admin
    
    # Notifications Details
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # payment, transaction, kyc, promotion, system, order, reminder
    
    # Status
    read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    # Action
    link = db.Column(db.String(500))
    action_text = db.Column(db.String(100))
    
    # extra_data (JSON for additional data)
    extra_data = db.Column(db.Text)  # JSON string
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
    
    def generate_notification_id(self):
        """Generate a notifications ID in format NOT001, NOT002, etc."""
        from sqlalchemy import func
        result = db.session.query(
            func.max(func.substr(Notifications.notification_id, 4).cast(db.Integer))
        ).filter(Notifications.notification_id.isnot(None)).scalar()
        return f"NOT{(result + 1) if result else 1:04d}"
    
    @staticmethod
    def create_notification(user_id, user_role, title, message, type, link=None, action_text=None, extra_data=None):
        """Create a new notifications"""
        notifications = Notifications(
            notifications_id=Notifications.generate_notification_id(Notifications),
            user_id=user_id,
            user_role=user_role,
            title=title,
            message=message,
            type=type,
            link=link,
            action_text=action_text,
            extra_data=json.dumps(extra_data) if extra_data else None
        )
        db.session.add(notifications)
        db.session.commit()
        return notifications