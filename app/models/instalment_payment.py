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
    late_fee_applied_date = db.Column(db.DateTime)  # Track when late fee was applied
    
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
    
    def apply_late_fee(self):
        """
        Apply 10% late fee if payment is overdue by at least one day.
        Late fee is 10% of the original payment amount.
        """
        if self.status == 'paid':
            return False
        
        if not self.due_date:
            return False
        
        today = datetime.utcnow()
        
        # Check if payment is overdue by at least one day
        if today > self.due_date:
            days_overdue = (today - self.due_date).days
            
            # Apply late fee only if not already applied
            if self.late_fee == 0 and self.late_fee_paid == False:
                # Calculate 10% late fee
                self.late_fee = self.amount * 0.10
                self.late_fee_applied_date = today
                self.status = 'overdue'
                db.session.commit()
                return True
        
        return False
    
    def get_total_due(self):
        """Get total amount due including late fee"""
        return self.amount + (self.late_fee if not self.late_fee_paid else 0)
    
    @staticmethod
    def apply_late_fees_for_all_overdue_payments():
        """Static method to apply late fees to all overdue payments (for cron jobs)"""
        overdue_payments = InstalmentPayment.query.filter(
            InstalmentPayment.status.in_(['pending', 'overdue']),
            InstalmentPayment.due_date < datetime.utcnow(),
            InstalmentPayment.late_fee == 0,
            InstalmentPayment.late_fee_paid == False
        ).all()
        
        applied_count = 0
        for payment in overdue_payments:
            if payment.apply_late_fee():
                applied_count += 1
        
        return applied_count