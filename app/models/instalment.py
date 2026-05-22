# models/instalment.py
from ..extensions import db
from datetime import datetime
import sqlalchemy as sa

class InstalmentPlan(db.Model):
    __tablename__ = 'instalment_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    
    # Plan Details
    plan_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    total_amount = db.Column(db.Float, nullable=False)
    down_payment = db.Column(db.Float, default=0)
    remaining_amount = db.Column(db.Float, default=0)
    
    # Payment Schedule
    number_of_installments = db.Column(db.Integer, nullable=False)
    installment_amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(20), default='monthly')
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    
    # Status
    status = db.Column(db.String(50), default='active')
    payment_status = db.Column(db.String(50), default='pending')
    
    # Tracking
    paid_installments = db.Column(db.Integer, default=0)
    missed_payments = db.Column(db.Integer, default=0)
    
    # Customer Info (denormalized for quick access)
    customer_name = db.Column(db.String(200))
    customer_phone = db.Column(db.String(20))
    customer_email = db.Column(db.String(200))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    # Relationships
    merchant = db.relationship('User', foreign_keys=[merchant_id], backref='merchant_instalments')
    customer = db.relationship('User', foreign_keys=[customer_id], backref='customer_instalments')
    transaction = db.relationship('Transaction', foreign_keys=[transaction_id], backref='instalment_plan')
    
    def generate_plan_id(self):
        """Generate a plan ID in format IP001, IP002, etc."""
        from sqlalchemy import func
        result = db.session.query(
            func.max(func.substr(InstalmentPlan.plan_id, 3).cast(sa.Integer))
        ).filter(InstalmentPlan.plan_id.isnot(None)).scalar()
        return f"IP{(result + 1) if result else 1:03d}"