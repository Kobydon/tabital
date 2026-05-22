# resources/customer_payments.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.instalment import InstalmentPlan
from ..models.instalment_payment import InstalmentPayment
from ..models.user import User
from ..extensions import db
from datetime import datetime, timedelta
from sqlalchemy import or_

def safe_str(v): return v if v is not None else ""
def safe_float(v): return v if v is not None else 0.0


class CustomerGetPaymentsResource(Resource):
    @auth_required
    def get(self):
        """Get customer's payment history from instalment payments"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        search = request.args.get('search', '').strip()
        status = request.args.get('status', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # Build query - get all instalment payments for customer's plans
        query = InstalmentPayment.query.join(
            InstalmentPlan
        ).filter(
            InstalmentPlan.customer_id == current_customer.id
        )
        
        # Apply filters
        if search:
            query = query.filter(
                or_(
                    InstalmentPayment.payment_id.ilike(f'%{search}%'),
                    InstalmentPlan.plan_name.ilike(f'%{search}%')
                )
            )
        
        if status:
            query = query.filter(InstalmentPayment.status == status)
        
        if start_date:
            query = query.filter(InstalmentPayment.due_date >= start_date)
        
        if end_date:
            query = query.filter(InstalmentPayment.due_date <= end_date)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        payments = query.order_by(
            InstalmentPayment.due_date.desc()
        ).offset((page - 1) * limit).limit(limit).all()
        
        # Format response
        result = []
        for payment in payments:
            plan = InstalmentPlan.query.get(payment.plan_id)
            merchant = User.query.get(plan.merchant_id) if plan else None
            
            result.append({
                "id": payment.id,
                "payment_id": payment.payment_id,
                "plan_id": payment.plan_id,
                "plan_name": safe_str(plan.plan_name if plan else ""),
                "merchant_name": safe_str(merchant.business_name or merchant.full_name or merchant.phone if merchant else ""),
                "installment_number": payment.installment_number,
                "amount": payment.amount,
                "paid_amount": payment.paid_amount,
                "due_date": payment.due_date.isoformat() if payment.due_date else "",
                "paid_date": payment.paid_date.isoformat() if payment.paid_date else "",
                "status": payment.status,
                "payment_method": payment.payment_method or "",
                "payment_reference": payment.payment_reference or "",
                "late_fee": payment.late_fee or 0,
                "late_fee_paid": payment.late_fee_paid or False
            })
        
        return {
            "payments": result,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }, 200


class CustomerGetPaymentStatsResource(Resource):
    @auth_required
    def get(self):
        """Get payment statistics for customer"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        # Get all instalment payments for customer
        payments = InstalmentPayment.query.join(
            InstalmentPlan
        ).filter(
            InstalmentPlan.customer_id == current_customer.id
        ).all()
        
        total_paid = sum(p.amount for p in payments if p.status == 'paid')
        total_due = sum(p.amount for p in payments if p.status == 'pending')
        overdue_count = len([p for p in payments if p.status == 'pending' and p.due_date and p.due_date < datetime.now()])
        upcoming_count = len([p for p in payments if p.status == 'pending' and p.due_date and p.due_date >= datetime.now()])
        
        # Calculate on-time rate
        total_completed = len([p for p in payments if p.status == 'paid'])
        on_time = len([p for p in payments if p.status == 'paid' and p.due_date and p.paid_date and p.paid_date <= p.due_date])
        on_time_rate = (on_time / total_completed * 100) if total_completed > 0 else 100
        
        return {
            "total_paid": total_paid,
            "total_due": total_due,
            "overdue_count": overdue_count,
            "upcoming_count": upcoming_count,
            "on_time_rate": round(on_time_rate, 1)
        }, 200


class CustomerDownloadReceiptResource(Resource):
    @auth_required
    def get(self, payment_id):
        """Download receipt for a payment"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        from flask import Response
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from io import BytesIO
        
        payment = InstalmentPayment.query.get(payment_id)
        if not payment:
            return {"error": "Payment not found"}, 404
        
        plan = InstalmentPlan.query.get(payment.plan_id)
        if not plan or plan.customer_id != current_customer.id:
            return {"error": "Unauthorized"}, 403
        
        merchant = User.query.get(plan.merchant_id)
        
        # Create PDF receipt
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, "TABITAL PAY - PAYMENT RECEIPT")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 70, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        c.line(50, height - 80, width - 50, height - 80)
        
        # Payment Details
        y = height - 110
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "PAYMENT DETAILS")
        c.setFont("Helvetica", 10)
        y -= 20
        c.drawString(50, y, f"Receipt Number: {payment.payment_id}")
        y -= 15
        c.drawString(50, y, f"Payment Date: {payment.paid_date.strftime('%Y-%m-%d') if payment.paid_date else 'N/A'}")
        y -= 15
        c.drawString(50, y, f"Amount Paid: GHS {payment.amount:.2f}")
        y -= 15
        c.drawString(50, y, f"Payment Method: {payment.payment_method or 'N/A'}")
        y -= 15
        c.drawString(50, y, f"Reference: {payment.payment_reference or 'N/A'}")
        
        # Plan Details
        y -= 30
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "INSTALMENT PLAN DETAILS")
        c.setFont("Helvetica", 10)
        y -= 20
        c.drawString(50, y, f"Plan ID: {plan.plan_id}")
        y -= 15
        c.drawString(50, y, f"Product: {plan.plan_name}")
        y -= 15
        c.drawString(50, y, f"Merchant: {merchant.business_name or merchant.full_name if merchant else 'N/A'}")
        y -= 15
        c.drawString(50, y, f"Installment: {payment.installment_number} of {plan.number_of_installments}")
        
        # Footer
        c.line(50, y - 20, width - 50, y - 20)
        c.setFont("Helvetica", 8)
        c.drawString(50, y - 35, "Thank you for your payment!")
        c.drawString(50, y - 45, "This is a computer-generated receipt and does not require a signature.")
        
        c.save()
        buffer.seek(0)
        
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=receipt_{payment.payment_id}.pdf'
            }
        )


class CustomerPaymentReminderResource(Resource):
    @auth_required
    def post(self):
        """Request payment reminder for upcoming payments"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        # Get upcoming payments
        today = datetime.now()
        upcoming_payments = InstalmentPayment.query.join(
            InstalmentPlan
        ).filter(
            InstalmentPlan.customer_id == current_customer.id,
            InstalmentPayment.status == 'pending',
            InstalmentPayment.due_date >= today
        ).order_by(InstalmentPayment.due_date.asc()).limit(5).all()
        
        if not upcoming_payments:
            return {"message": "No upcoming payments found"}, 200
        
        # In production, send email/SMS reminders here
        # For now, just return success
        
        return {
            "message": f"Payment reminder sent for {len(upcoming_payments)} upcoming payment(s)",
            "reminders_sent": len(upcoming_payments)
        }, 200


class CustomerMakePaymentResource(Resource):
    @auth_required
    def post(self):
        """Make a payment for an installment"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        plan_id = data.get('plan_id')
        amount = data.get('amount')
        payment_method = data.get('payment_method')
        payment_reference = data.get('payment_reference', '')
        notes = data.get('notes', '')
        
        if not plan_id or not amount:
            return {"error": "Plan ID and amount are required"}, 400
        
        # Get the instalment plan
        plan = InstalmentPlan.query.filter_by(id=plan_id, customer_id=current_customer.id).first()
        if not plan:
            return {"error": "Instalment plan not found"}, 404
        
        # Find the next pending payment
        next_payment = InstalmentPayment.query.filter_by(
            plan_id=plan.id,
            status='pending'
        ).order_by(InstalmentPayment.installment_number).first()
        
        if not next_payment:
            return {"error": "No pending payments found for this plan"}, 400
        
        # Process payment
        next_payment.status = 'paid'
        next_payment.paid_date = datetime.now()
        next_payment.payment_method = payment_method
        next_payment.payment_reference = payment_reference
        next_payment.paid_amount = amount
        
        # Update plan
        plan.paid_installments += 1
        plan.remaining_amount -= amount
        
        if plan.paid_installments == plan.number_of_installments:
            plan.status = 'completed'
            plan.payment_status = 'completed'
            plan.completed_at = datetime.now()
        
        db.session.commit()
        
        return {
            "message": "Payment successful",
            "payment_reference": next_payment.payment_id,
            "remaining_balance": plan.remaining_amount,
            "paid_installments": plan.paid_installments,
            "total_installments": plan.number_of_installments
        }, 200


# resources/customer_paid_payments.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.instalment import InstalmentPlan
from ..models.instalment_payment import InstalmentPayment
from ..models.user import User
from ..extensions import db
from datetime import datetime
from sqlalchemy import or_

class CustomerPaidPaymentsResource(Resource):
    @auth_required
    def get(self):
        """Get customer's paid instalment payments"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        search = request.args.get('search', '').strip()
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        query = InstalmentPayment.query.join(
            InstalmentPlan
        ).filter(
            InstalmentPlan.customer_id == current_customer.id,
            InstalmentPayment.status == 'paid'
        )
        
        if search:
            query = query.filter(
                or_(
                    InstalmentPayment.payment_id.ilike(f'%{search}%'),
                    InstalmentPlan.plan_name.ilike(f'%{search}%')
                )
            )
        
        if start_date:
            query = query.filter(InstalmentPayment.paid_date >= start_date)
        if end_date:
            query = query.filter(InstalmentPayment.paid_date <= end_date)
        
        total = query.count()
        payments = query.order_by(InstalmentPayment.paid_date.desc()).offset((page - 1) * limit).limit(limit).all()
        
        result = []
        for payment in payments:
            plan = InstalmentPlan.query.get(payment.plan_id)
            merchant = User.query.get(plan.merchant_id) if plan else None
            
            result.append({
                "id": payment.id,
                "payment_id": payment.payment_id,
                "plan_id": payment.plan_id,
                "plan_name": plan.plan_name if plan else "",
                "merchant_name": merchant.business_name or merchant.full_name if merchant else "",
                "installment_number": payment.installment_number,
                "amount": payment.amount,
                "payment_method": payment.payment_method or "",
                "payment_reference": payment.payment_reference or "",
                "status": payment.status,
                "paid_date": payment.paid_date.isoformat() if payment.paid_date else "",
                "due_date": payment.due_date.isoformat() if payment.due_date else ""
            })
        
        return {
            "payments": result,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }, 200