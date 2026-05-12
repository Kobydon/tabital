from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.user import User
from ..models.transaction import Transaction
from ..models.instalment import *

from ..extensions import db
from datetime import datetime, timedelta

def safe_str(v): return v if v is not None else ""
def safe_float(v): return v if v is not None else 0.0
def safe_int(v): return v if v is not None else 0

class GetMerchantInstalmentsResource(Resource):
    @auth_required
    def get(self):
        """Get all instalment plans for the merchant"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        status = request.args.get('status', '').strip()
        
        query = InstalmentPlan.query.filter_by(merchant_id=current_merchant.id)
        
        if status:
            query = query.filter_by(status=status)
        
        plans = query.order_by(InstalmentPlan.created_at.desc()).all()
        
        return [{
            "id": p.id,
            "plan_id": safe_str(p.plan_id),
            "plan_name": safe_str(p.plan_name),
            "description": safe_str(p.description),
            "customer_name": safe_str(p.customer_name),
            "customer_phone": safe_str(p.customer_phone),
            "customer_email": safe_str(p.customer_email),
            "total_amount": safe_float(p.total_amount),
            "down_payment": safe_float(p.down_payment),
            "remaining_amount": safe_float(p.remaining_amount),
            "number_of_installments": safe_int(p.number_of_installments),
            "installment_amount": safe_float(p.installment_amount),
            "frequency": safe_str(p.frequency),
            "paid_installments": safe_int(p.paid_installments),
            "missed_payments": safe_int(p.missed_payments),
            "status": safe_str(p.status),
            "payment_status": safe_str(p.payment_status),
            "start_date": p.start_date.isoformat() if p.start_date else "",
            "end_date": p.end_date.isoformat() if p.end_date else "",
            "created_at": p.created_at.isoformat() if p.created_at else "",
            "completed_at": p.completed_at.isoformat() if p.completed_at else ""
        } for p in plans]


class CreateInstalmentPlanResource(Resource):
    @auth_required
    def post(self):
        """Create a new instalment plan"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        
        required_fields = ['plan_name', 'customer_name', 'customer_phone', 'total_amount', 
                          'number_of_installments', 'installment_amount', 'start_date']
        
        for field in required_fields:
            if field not in data:
                return {"error": f"{field} is required"}, 400
        
        # Check if customer exists or create new
        customer = User.query.filter_by(phone=data['customer_phone']).first()
        customer_id = customer.id if customer else None
        
        # Calculate remaining amount
        down_payment = data.get('down_payment', 0)
        remaining_amount = data['total_amount'] - down_payment
        
        # Calculate end date
        start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
        frequency = data.get('frequency', 'monthly')
        
        if frequency == 'weekly':
            end_date = start_date + timedelta(weeks=data['number_of_installments'])
        elif frequency == 'biweekly':
            end_date = start_date + timedelta(weeks=data['number_of_installments'] * 2)
        else:  # monthly
            end_date = start_date + timedelta(days=30 * data['number_of_installments'])
        
        plan = InstalmentPlan(
            merchant_id=current_merchant.id,
            customer_id=customer_id,
            plan_name=data['plan_name'],
            description=data.get('description', ''),
            total_amount=data['total_amount'],
            down_payment=down_payment,
            remaining_amount=remaining_amount,
            number_of_installments=data['number_of_installments'],
            installment_amount=data['installment_amount'],
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            customer_name=data['customer_name'],
            customer_phone=data['customer_phone'],
            customer_email=data.get('customer_email', ''),
            status='active',
            payment_status='pending'
        )
        
        plan.plan_id = plan.generate_plan_id()
        
        db.session.add(plan)
        db.session.commit()
        
        # Create individual payment schedules
        for i in range(1, data['number_of_installments'] + 1):
            if frequency == 'weekly':
                due_date = start_date + timedelta(weeks=i)
            elif frequency == 'biweekly':
                due_date = start_date + timedelta(weeks=i * 2)
            else:
                due_date = start_date + timedelta(days=30 * i)
            
            payment = InstalmentPayment(
                plan_id=plan.id,
                installment_number=i,
                due_date=due_date,
                amount=data['installment_amount'],
                status='pending'
            )
            payment.payment_id = payment.generate_payment_id()
            db.session.add(payment)
        
        db.session.commit()
        
        return {
            "message": "Instalment plan created successfully",
            "plan_id": plan.plan_id,
            "id": plan.id
        }, 201


class UpdateInstalmentPlanResource(Resource):
    @auth_required
    def put(self, plan_id):
        """Update an instalment plan"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        plan = InstalmentPlan.query.get(plan_id)
        
        if not plan or plan.merchant_id != current_merchant.id:
            return {"error": "Instalment plan not found"}, 404
        
        data = request.get_json()
        
        allowed_fields = ['plan_name', 'description', 'status', 'customer_name', 
                         'customer_phone', 'customer_email']
        
        for field in allowed_fields:
            if field in data:
                setattr(plan, field, data[field])
        
        if 'status' in data and data['status'] == 'cancelled':
            plan.cancelled_at = datetime.utcnow()
        
        if 'status' in data and data['status'] == 'completed':
            plan.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return {"message": "Instalment plan updated successfully"}, 200


class DeleteInstalmentPlanResource(Resource):
    @auth_required
    def delete(self, plan_id):
        """Delete an instalment plan"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        plan = InstalmentPlan.query.get(plan_id)
        
        if not plan or plan.merchant_id != current_merchant.id:
            return {"error": "Instalment plan not found"}, 404
        
        # Delete all associated payments first
        InstalmentPayment.query.filter_by(plan_id=plan.id).delete()
        
        db.session.delete(plan)
        db.session.commit()
        
        return {"message": "Instalment plan deleted successfully"}, 200


class GetInstalmentPlanDetailsResource(Resource):
    @auth_required
    def get(self, plan_id):
        """Get instalment plan details with payment schedule"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        plan = InstalmentPlan.query.get(plan_id)
        
        if not plan or plan.merchant_id != current_merchant.id:
            return {"error": "Instalment plan not found"}, 404
        
        # Get all payments for this plan
        payments = InstalmentPayment.query.filter_by(plan_id=plan.id).order_by(
            InstalmentPayment.installment_number
        ).all()
        
        return {
            "id": plan.id,
            "plan_id": safe_str(plan.plan_id),
            "plan_name": safe_str(plan.plan_name),
            "description": safe_str(plan.description),
            "customer_name": safe_str(plan.customer_name),
            "customer_phone": safe_str(plan.customer_phone),
            "customer_email": safe_str(plan.customer_email),
            "total_amount": safe_float(plan.total_amount),
            "down_payment": safe_float(plan.down_payment),
            "remaining_amount": safe_float(plan.remaining_amount),
            "number_of_installments": safe_int(plan.number_of_installments),
            "installment_amount": safe_float(plan.installment_amount),
            "frequency": safe_str(plan.frequency),
            "paid_installments": safe_int(plan.paid_installments),
            "missed_payments": safe_int(plan.missed_payments),
            "status": safe_str(plan.status),
            "payment_status": safe_str(plan.payment_status),
            "start_date": plan.start_date.isoformat() if plan.start_date else "",
            "end_date": plan.end_date.isoformat() if plan.end_date else "",
            "created_at": plan.created_at.isoformat() if plan.created_at else "",
            "payments": [{
                "id": p.id,
                "payment_id": safe_str(p.payment_id),
                "installment_number": p.installment_number,
                "due_date": p.due_date.isoformat() if p.due_date else "",
                "paid_date": p.paid_date.isoformat() if p.paid_date else "",
                "amount": safe_float(p.amount),
                "paid_amount": safe_float(p.paid_amount),
                "status": safe_str(p.status),
                "late_fee": safe_float(p.late_fee),
                "payment_method": safe_str(p.payment_method)
            } for p in payments]
        }


class RecordInstalmentPaymentResource(Resource):
    @auth_required
    def post(self, plan_id):
        """Record a payment for an instalment"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        plan = InstalmentPlan.query.get(plan_id)
        
        if not plan or plan.merchant_id != current_merchant.id:
            return {"error": "Instalment plan not found"}, 404
        
        data = request.get_json()
        
        installment_number = data.get('installment_number')
        payment_method = data.get('payment_method', 'cash')
        payment_reference = data.get('payment_reference', '')
        
        if not installment_number:
            return {"error": "Installment number is required"}, 400
        
        payment = InstalmentPayment.query.filter_by(
            plan_id=plan.id,
            installment_number=installment_number
        ).first()
        
        if not payment:
            return {"error": "Payment record not found"}, 404
        
        if payment.status == 'paid':
            return {"error": "This installment has already been paid"}, 400
        
        # Record the payment
        payment.status = 'paid'
        payment.paid_date = datetime.utcnow()
        payment.paid_amount = payment.amount
        payment.payment_method = payment_method
        payment.payment_reference = payment_reference
        
        # Update plan statistics
        plan.paid_installments += 1
        plan.remaining_amount -= payment.amount
        
        if plan.paid_installments >= plan.number_of_installments:
            plan.status = 'completed'
            plan.payment_status = 'completed'
            plan.completed_at = datetime.utcnow()
        elif plan.paid_installments > 0:
            plan.payment_status = 'partial'
        
        db.session.commit()
        
        return {
            "message": "Payment recorded successfully",
            "paid_installments": plan.paid_installments,
            "remaining_amount": safe_float(plan.remaining_amount)
        }, 200