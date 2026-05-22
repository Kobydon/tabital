# resources/customer_instalments.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.instalment import InstalmentPlan
from ..models.instalment_payment import InstalmentPayment
from ..models.user import User
from ..extensions import db
from datetime import datetime

def safe_str(v): return v if v is not None else ""
def safe_float(v): return v if v is not None else 0.0

class CustomerInstalmentsResource(Resource):
    @auth_required
    def get(self):
        """Get customer's instalment plans with payment schedule"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        status = request.args.get('status', 'all')
        
        query = InstalmentPlan.query.filter(
            InstalmentPlan.customer_id == current_customer.id
        )
        
        if status != 'all':
            query = query.filter(InstalmentPlan.status == status)
        
        plans = query.order_by(InstalmentPlan.created_at.desc()).all()
        
        result = []
        for plan in plans:
            # Get merchant name
            merchant = User.query.get(plan.merchant_id)
            merchant_name = merchant.business_name or merchant.full_name or merchant.phone if merchant else "Merchant"
            
            # Get payment schedule from instalment_payments table - THIS IS THE KEY PART
            payments = InstalmentPayment.query.filter_by(
                plan_id=plan.id
            ).order_by(InstalmentPayment.installment_number).all()
            
            # Build payment schedule array
            payment_schedule = []
            paid_amount = 0
            
            for p in payments:
                payment_schedule.append({
                    "id": p.id,
                    "installment_number": p.installment_number,
                    "due_date": p.due_date.strftime('%Y-%m-%d') if p.due_date else "",
                    "amount": p.amount,
                    "status": p.status,
                    "paid_date": p.paid_date.strftime('%Y-%m-%d') if p.paid_date else "",
                    "payment_reference": p.payment_reference or "",
                    "late_fee": p.late_fee or 0
                })
                
                if p.status == 'paid':
                    paid_amount += p.amount
            
            remaining_amount = plan.total_amount - paid_amount
            
            result.append({
                "id": plan.id,
                "plan_id": plan.plan_id,
                "product_name": plan.plan_name,
                "description": plan.description or "",
                "merchant_name": merchant_name,
                "merchant_phone": merchant.phone if merchant else "",
                "total_amount": plan.total_amount,
                "amount_paid": paid_amount,
                "amount_outstanding": remaining_amount,
                "number_of_installments": plan.number_of_installments,
                "paid_installments": len([p for p in payments if p.status == 'paid']),
                "installment_amount": plan.installment_amount,
                "down_payment": plan.down_payment,
                "frequency": plan.frequency,
                "start_date": plan.start_date.isoformat() if plan.start_date else "",
                "end_date": plan.end_date.isoformat() if plan.end_date else "",
                "status": plan.status,
                "payment_status": plan.payment_status,
                "payment_schedule": payment_schedule  # THIS MUST BE INCLUDED
            })
        
        return {
            "plans": result,
            "total": len(result)
        }, 200