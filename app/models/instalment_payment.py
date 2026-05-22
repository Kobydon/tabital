from ..extensions import db
from datetime import datetime

class InstalmentPayment(db.Model):
    __tablename__ = 'instalment_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('instalment_plans.id'), nullable=False)
    
    # Payment Details
    installment_number = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    paid_date = db.Column(db.DateTime)
    amount = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0)
    
    # Status
    status = db.Column(db.String(50), default='pending')  # pending, paid, overdue, partial
    payment_method = db.Column(db.String(50))
    payment_reference = db.Column(db.String(100))
    
    # Late fee
    late_fee = db.Column(db.Float, default=0)
    late_fee_paid = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relationship
    plan = db.relationship('InstalmentPlan', backref='payments')
    
    def generate_payment_id(self):
        """Generate a payment ID in format PAY001, PAY002, etc."""
        from sqlalchemy import func
        result = db.session.query(
            func.max(func.substr(InstalmentPayment.payment_id, 4).cast(db.Integer))
        ).filter(InstalmentPayment.payment_id.isnot(None)).scalar()
        return f"PAY{(result + 1) if result else 1:03d}"