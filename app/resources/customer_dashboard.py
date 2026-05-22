# resources/customer_dashboard.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.user import User
from ..models.transaction import Transaction
from ..models.instalment import InstalmentPlan
from ..models.instalment_payment import InstalmentPayment
from ..extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, and_

def safe_str(v): return v if v is not None else ""
def safe_float(v): return v if v is not None else 0.0
def safe_int(v): return v if v is not None else 0

class CustomerDashboardStatsResource(Resource):
    @auth_required
    def get(self):
        """Get customer dashboard statistics"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        # Get all active instalment plans for this customer
        active_plans = InstalmentPlan.query.filter(
            InstalmentPlan.customer_id == current_customer.id,
            InstalmentPlan.status == 'active'
        ).all()
        
        # Calculate total outstanding
        total_outstanding = sum(p.remaining_amount for p in active_plans)
        total_outstanding_plans_count = len(active_plans)
        
        # Get next payment
        next_payment = InstalmentPayment.query.join(
            InstalmentPlan
        ).filter(
            InstalmentPlan.customer_id == current_customer.id,
            InstalmentPayment.status == 'pending',
            InstalmentPayment.due_date >= datetime.now()
        ).order_by(InstalmentPayment.due_date.asc()).first()
        
        next_payment_amount = next_payment.amount if next_payment else 0
        next_payment_date = next_payment.due_date.isoformat() if next_payment else ""
        next_payment_plan_name = next_payment.plan.plan_name if next_payment else ""
        
        # Calculate paid to date (this year)
        year_start = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0)
        paid_payments = InstalmentPayment.query.join(
            InstalmentPlan
        ).filter(
            InstalmentPlan.customer_id == current_customer.id,
            InstalmentPayment.status == 'paid',
            InstalmentPayment.paid_date >= year_start
        ).all()
        
        paid_to_date = sum(p.amount for p in paid_payments)
        
        # Account status
        account_status = 'good_standing'
        account_status_message = 'Good Standing'
        
        # Check for overdue payments
        overdue_count = InstalmentPayment.query.join(
            InstalmentPlan
        ).filter(
            InstalmentPlan.customer_id == current_customer.id,
            InstalmentPayment.status == 'overdue',
            InstalmentPayment.due_date < datetime.now()
        ).count()
        
        if overdue_count > 0:
            account_status = 'overdue'
            account_status_message = f'Overdue ({overdue_count} payments)'
        
        return {
            "total_outstanding": safe_float(total_outstanding),
            "total_outstanding_plans_count": safe_int(total_outstanding_plans_count),
            "next_payment_amount": safe_float(next_payment_amount),
            "next_payment_date": next_payment_date,
            "next_payment_plan_name": safe_str(next_payment_plan_name),
            "paid_to_date": safe_float(paid_to_date),
            "paid_to_date_period": str(datetime.now().year),
            "active_plans_count": safe_int(len(active_plans)),
            "account_status": account_status,
            "account_status_message": account_status_message,
            "customer_name": safe_str(current_customer.full_name or current_customer.business_name),
            "customer_id": safe_str(current_customer.customer_id),
            "email": safe_str(current_customer.business_email or current_customer.email),
            "phone": safe_str(current_customer.phone)
        }

class CustomerPaymentOverviewResource(Resource):
    @auth_required
    def get(self):
        """Get payment overview chart data for the last 12 months"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        monthly_data = []
        total_paid = 0
        total_outstanding = 0
        
        # Get last 12 months from current date
        today = datetime.now()
        
        for i in range(11, -1, -1):
            # Calculate the target month
            target_month = today.month - i
            target_year = today.year
            
            if target_month <= 0:
                target_month += 12
                target_year -= 1
            
            month_start = datetime(target_year, target_month, 1, 0, 0, 0)
            
            # Calculate next month
            if target_month == 12:
                next_month = datetime(target_year + 1, 1, 1, 0, 0, 0)
            else:
                next_month = datetime(target_year, target_month + 1, 1, 0, 0, 0)
            
            # Get paid payments for this month
            paid_payments = InstalmentPayment.query.join(
                InstalmentPlan
            ).filter(
                InstalmentPlan.customer_id == current_customer.id,
                InstalmentPayment.status == 'paid',
                InstalmentPayment.paid_date >= month_start,
                InstalmentPayment.paid_date < next_month
            ).all()
            
            paid_amount = sum(p.amount for p in paid_payments)
            
            # Get pending payments due this month
            pending_payments = InstalmentPayment.query.join(
                InstalmentPlan
            ).filter(
                InstalmentPlan.customer_id == current_customer.id,
                InstalmentPayment.status == 'pending',
                InstalmentPayment.due_date >= month_start,
                InstalmentPayment.due_date < next_month
            ).all()
            
            pending_amount = sum(p.amount for p in pending_payments)
            
            # Only add months that have data or are recent months
            # Use consistent month format without year for chart
            monthly_data.append({
                "month": month_start.strftime("%b"),
                "paid": float(paid_amount),
                "outstanding": float(pending_amount)
            })
            
            total_paid += paid_amount
            total_outstanding += pending_amount
        
        return {
            "monthly_data": monthly_data,
            "total_paid": float(total_paid),
            "total_outstanding": float(total_outstanding)
        }, 200

class CustomerUpcomingPaymentsResource(Resource):
    @auth_required
    def get(self):
        """Get upcoming payments for customer"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        limit = request.args.get('limit', 5, type=int)
        
        upcoming_payments = InstalmentPayment.query.join(
            InstalmentPlan
        ).filter(
            InstalmentPlan.customer_id == current_customer.id,
            InstalmentPayment.status.in_(['pending', 'overdue']),
            InstalmentPayment.due_date >= datetime.now()
        ).order_by(InstalmentPayment.due_date.asc()).limit(limit).all()
        
        result = []
        for payment in upcoming_payments:
            plan = payment.plan
            result.append({
                "id": plan.id,
                "plan_id": safe_str(plan.plan_id),
                "transaction_id": safe_str(plan.transaction_id),
                "product_name": safe_str(plan.plan_name),
                "product_description": safe_str(plan.description),
                "merchant_name": safe_str(plan.merchant.business_name or plan.merchant.full_name),
                "merchant_phone": safe_str(plan.merchant.phone),
                "total_amount": safe_float(plan.total_amount),
                "amount_paid": safe_float(plan.total_amount - plan.remaining_amount),
                "amount_outstanding": safe_float(plan.remaining_amount),
                "instalment_term": safe_int(plan.number_of_installments),
                "instalment_frequency": safe_str(plan.frequency),
                "instalment_amount": safe_float(plan.installment_amount),
                "next_payment_date": payment.due_date.isoformat() if payment.due_date else "",
                "next_payment_amount": safe_float(payment.amount),
                "due_date": payment.due_date.isoformat() if payment.due_date else "",
                "status": safe_str(plan.status),
                "created_at": plan.created_at.isoformat() if plan.created_at else ""
            })
        
        return result


class CustomerRecentTransactionsResource(Resource):
    @auth_required
    def get(self):
        """Get recent transactions for customer"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        limit = request.args.get('limit', 5, type=int)
        
        # Get completed instalment payments
        payments = InstalmentPayment.query.join(
            InstalmentPlan
        ).filter(
            InstalmentPlan.customer_id == current_customer.id,
            InstalmentPayment.status == 'paid'
        ).order_by(InstalmentPayment.paid_date.desc()).limit(limit).all()
        
        result = []
        for payment in payments:
            plan = payment.plan
            result.append({
                "id": payment.id,
                "transaction_id": safe_str(payment.payment_id),
                "merchant_name": safe_str(plan.merchant.business_name or plan.merchant.full_name),
                "product_name": safe_str(plan.plan_name),
                "product_description": safe_str(plan.description),
                "amount": safe_float(payment.amount),
                "payment_method": safe_str(payment.payment_method),
                "payment_plan": "Instalment",
                "status": "completed",
                "transaction_date": payment.paid_date.isoformat() if payment.paid_date else "",
                "delivery_status": "completed"
            })
        
        return result


class CustomerInstalmentsResource(Resource):
    @auth_required
    def get(self):
        """Get customer's instalment plans"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        status = request.args.get('status', 'all')
        limit = request.args.get('limit', 50, type=int)
        page = request.args.get('page', 1, type=int)
        
        query = InstalmentPlan.query.filter(
            InstalmentPlan.customer_id == current_customer.id
        )
        
        if status != 'all':
            query = query.filter(InstalmentPlan.status == status)
        
        total = query.count()
        plans = query.order_by(InstalmentPlan.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        
        result = []
        for plan in plans:
            # Get next payment
            next_payment = InstalmentPayment.query.filter(
                InstalmentPayment.plan_id == plan.id,
                InstalmentPayment.status.in_(['pending', 'overdue'])
            ).order_by(InstalmentPayment.due_date.asc()).first()
            
            result.append({
                "id": plan.id,
                "plan_id": safe_str(plan.plan_id),
                "transaction_id": safe_str(plan.transaction_id),
                "product_name": safe_str(plan.plan_name),
                "product_description": safe_str(plan.description),
                "merchant_name": safe_str(plan.merchant.business_name or plan.merchant.full_name),
                "merchant_phone": safe_str(plan.merchant.phone),
                "total_amount": safe_float(plan.total_amount),
                "amount_paid": safe_float(plan.total_amount - plan.remaining_amount),
                "amount_outstanding": safe_float(plan.remaining_amount),
                "instalment_term": safe_int(plan.number_of_installments),
                "instalment_frequency": safe_str(plan.frequency),
                "instalment_amount": safe_float(plan.installment_amount),
                "next_payment_date": next_payment.due_date.isoformat() if next_payment else "",
                "next_payment_amount": safe_float(next_payment.amount) if next_payment else 0,
                "due_date": plan.end_date.isoformat() if plan.end_date else "",
                "status": safe_str(plan.status),
                "created_at": plan.created_at.isoformat() if plan.created_at else "",
                "completed_at": plan.completed_at.isoformat() if plan.completed_at else ""
            })
        
        return {
            "plans": result,
            "total": total,
            "page": page,
            "limit": limit
        }


class CustomerPlanDetailsResource(Resource):
    @auth_required
    def get(self, plan_id):
        """Get detailed instalment plan information"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        plan = InstalmentPlan.query.filter_by(
            id=plan_id,
            customer_id=current_customer.id
        ).first()
        
        if not plan:
            return {"error": "Plan not found"}, 404
        
        # Get payment schedule
        payments = InstalmentPayment.query.filter_by(
            plan_id=plan.id
        ).order_by(InstalmentPayment.installment_number).all()
        
        payment_schedule = []
        for payment in payments:
            payment_schedule.append({
                "id": payment.id,
                "instalment_number": payment.installment_number,
                "due_date": payment.due_date.isoformat() if payment.due_date else "",
                "amount": safe_float(payment.amount),
                "status": safe_str(payment.status),
                "paid_date": payment.paid_date.isoformat() if payment.paid_date else "",
                "payment_reference": safe_str(payment.payment_reference)
            })
        
        return {
            "id": plan.id,
            "plan_id": safe_str(plan.plan_id),
            "transaction_id": safe_str(plan.transaction_id),
            "product_name": safe_str(plan.plan_name),
            "product_description": safe_str(plan.description),
            "merchant_name": safe_str(plan.merchant.business_name or plan.merchant.full_name),
            "merchant_phone": safe_str(plan.merchant.phone),
            "total_amount": safe_float(plan.total_amount),
            "amount_paid": safe_float(plan.total_amount - plan.remaining_amount),
            "amount_outstanding": safe_float(plan.remaining_amount),
            "instalment_term": safe_int(plan.number_of_installments),
            "instalment_frequency": safe_str(plan.frequency),
            "instalment_amount": safe_float(plan.installment_amount),
            "down_payment": safe_float(plan.down_payment),
            "start_date": plan.start_date.isoformat() if plan.start_date else "",
            "end_date": plan.end_date.isoformat() if plan.end_date else "",
            "status": safe_str(plan.status),
            "payment_status": safe_str(plan.payment_status),
            "paid_installments": safe_int(plan.paid_installments),
            "created_at": plan.created_at.isoformat() if plan.created_at else "",
            "payment_schedule": payment_schedule
        }


class CustomerMakePaymentResource(Resource):
    @auth_required
    def post(self):
        """Make a payment on an instalment plan"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        plan_id = data.get('plan_id')
        amount = data.get('amount')
        payment_method = data.get('payment_method')
        
        if not plan_id or not amount:
            return {"error": "Plan ID and amount are required"}, 400
        
        plan = InstalmentPlan.query.filter_by(
            id=plan_id,
            customer_id=current_customer.id
        ).first()
        
        if not plan:
            return {"error": "Plan not found"}, 404
        
        # Get the next pending payment
        pending_payment = InstalmentPayment.query.filter_by(
            plan_id=plan.id,
            status='pending'
        ).order_by(InstalmentPayment.installment_number).first()
        
        if not pending_payment:
            return {"error": "No pending payments found"}, 400
        
        # Process payment (integrate with payment gateway here)
        # For now, simulate successful payment
        
        # Update payment record
        pending_payment.status = 'paid'
        pending_payment.paid_date = datetime.now()
        pending_payment.payment_method = payment_method
        pending_payment.payment_reference = f"PAY_{datetime.now().timestamp()}"
        
        # Update plan
        plan.paid_installments += 1
        plan.remaining_amount -= amount
        
        if plan.remaining_amount <= 0:
            plan.status = 'completed'
            plan.payment_status = 'completed'
            plan.completed_at = datetime.now()
        
        db.session.commit()
        
        return {
            "message": "Payment successful",
            "payment_id": pending_payment.payment_id,
            "payment_reference": pending_payment.payment_reference,
            "amount_paid": amount,
            "remaining_amount": safe_float(plan.remaining_amount),
            "plan_status": plan.status
        }, 200