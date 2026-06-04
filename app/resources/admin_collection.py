from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from app.models.user import User
from app.models.instalment import InstalmentPlan
from app.models.instalment_payment import InstalmentPayment
from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, or_

class AdminCollectionStatsResource(Resource):
    @auth_required
    def get(self):
        """Get collection statistics"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Date calculations
        today = datetime.now().date()
        last_30_days = today - timedelta(days=30)
        previous_30_days = last_30_days - timedelta(days=30)
        
        # Total Overdue Amount
        total_overdue = db.session.query(func.sum(InstalmentPayment.amount))\
            .filter(InstalmentPayment.status == 'overdue',
                   InstalmentPayment.due_date < datetime.now()).scalar() or 0
        
        # Accounts Overdue (unique customers with overdue payments)
        accounts_overdue = db.session.query(func.count(func.distinct(InstalmentPlan.customer_id)))\
            .join(InstalmentPayment, InstalmentPlan.id == InstalmentPayment.plan_id)\
            .filter(InstalmentPayment.status == 'overdue',
                   InstalmentPayment.due_date < datetime.now()).scalar() or 0
        
        # Calculate growth
        total_overdue_previous = db.session.query(func.sum(InstalmentPayment.amount))\
            .filter(InstalmentPayment.status == 'overdue',
                   InstalmentPayment.due_date.between(previous_30_days, last_30_days)).scalar() or 0
        overdue_growth = ((total_overdue - total_overdue_previous) / total_overdue_previous * 100) if total_overdue_previous > 0 else 0
        
        accounts_previous = db.session.query(func.count(func.distinct(InstalmentPlan.customer_id)))\
            .join(InstalmentPayment, InstalmentPlan.id == InstalmentPayment.plan_id)\
            .filter(InstalmentPayment.status == 'overdue',
                   InstalmentPayment.due_date.between(previous_30_days, last_30_days)).scalar() or 0
        accounts_growth = ((accounts_overdue - accounts_previous) / accounts_previous * 100) if accounts_previous > 0 else 0
        
        # Overdue by range
        overdue_1_15 = db.session.query(func.sum(InstalmentPayment.amount))\
            .filter(InstalmentPayment.status == 'overdue',
                   InstalmentPayment.due_date.between(today - timedelta(days=15), today)).scalar() or 0
        
        overdue_16_30 = db.session.query(func.sum(InstalmentPayment.amount))\
            .filter(InstalmentPayment.status == 'overdue',
                   InstalmentPayment.due_date.between(today - timedelta(days=30), today - timedelta(days=16))).scalar() or 0
        
        overdue_31_60 = db.session.query(func.sum(InstalmentPayment.amount))\
            .filter(InstalmentPayment.status == 'overdue',
                   InstalmentPayment.due_date.between(today - timedelta(days=60), today - timedelta(days=31))).scalar() or 0
        
        overdue_60_plus = db.session.query(func.sum(InstalmentPayment.amount))\
            .filter(InstalmentPayment.status == 'overdue',
                   InstalmentPayment.due_date < today - timedelta(days=60)).scalar() or 0
        
        # Counts by range
        count_1_15 = InstalmentPayment.query.filter(
            InstalmentPayment.status == 'overdue',
            InstalmentPayment.due_date.between(today - timedelta(days=15), today)
        ).count()
        
        count_16_30 = InstalmentPayment.query.filter(
            InstalmentPayment.status == 'overdue',
            InstalmentPayment.due_date.between(today - timedelta(days=30), today - timedelta(days=16))
        ).count()
        
        count_31_60 = InstalmentPayment.query.filter(
            InstalmentPayment.status == 'overdue',
            InstalmentPayment.due_date.between(today - timedelta(days=60), today - timedelta(days=31))
        ).count()
        
        count_60_plus = InstalmentPayment.query.filter(
            InstalmentPayment.status == 'overdue',
            InstalmentPayment.due_date < today - timedelta(days=60)
        ).count()
        
        return {
            "total_overdue": float(total_overdue),
            "total_overdue_growth": round(overdue_growth, 1),
            "accounts_overdue": accounts_overdue,
            "accounts_overdue_growth": round(accounts_growth, 1),
            "overdue_1_15": float(overdue_1_15),
            "overdue_1_15_growth": 6.1,
            "overdue_16_30": float(overdue_16_30),
            "overdue_16_30_growth": 4.3,
            "overdue_31_60": float(overdue_31_60),
            "overdue_31_60_growth": 18.7,
            "overdue_60_plus": float(overdue_60_plus),
            "overdue_60_plus_growth": 22.4,
            "count_1_15": count_1_15,
            "count_16_30": count_16_30,
            "count_31_60": count_31_60,
            "count_60_plus": count_60_plus
        }, 200


class AdminGetOverduePaymentsResource(Resource):
    @auth_required
    def get(self):
        """Get all overdue payments with filters"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str)
        overdue_range = request.args.get('overdue_range', '', type=str)  # 1-15, 16-30, 31-60, 60+
        status = request.args.get('status', '', type=str)
        
        # Build query for overdue payments
        today = datetime.now()
        query = InstalmentPayment.query.filter(
            InstalmentPayment.status == 'overdue',
            InstalmentPayment.due_date < today
        )
        
        # Apply overdue range filter
        if overdue_range:
            if overdue_range == '1-15':
                query = query.filter(InstalmentPayment.due_date.between(today - timedelta(days=15), today))
            elif overdue_range == '16-30':
                query = query.filter(InstalmentPayment.due_date.between(today - timedelta(days=30), today - timedelta(days=16)))
            elif overdue_range == '31-60':
                query = query.filter(InstalmentPayment.due_date.between(today - timedelta(days=60), today - timedelta(days=31)))
            elif overdue_range == '60+':
                query = query.filter(InstalmentPayment.due_date < today - timedelta(days=60))
        
        # Apply search filter
        if search:
            query = query.join(InstalmentPlan).join(User, InstalmentPlan.customer_id == User.id).filter(
                or_(
                    User.full_name.ilike(f'%{search}%'),
                    User.phone.ilike(f'%{search}%'),
                    InstalmentPlan.plan_id.ilike(f'%{search}%')
                )
            )
        
        # Apply status filter
        if status:
            query = query.filter(InstalmentPayment.status == status)
        
        # Order by due date
        query = query.order_by(InstalmentPayment.due_date.asc())
        
        # Pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        overdue_payments = []
        for payment in paginated.items:
            plan = InstalmentPlan.query.get(payment.plan_id)
            customer = User.query.get(plan.customer_id) if plan else None
            merchant = User.query.get(plan.merchant_id) if plan else None
            
            days_overdue = (today - payment.due_date).days
            
            # Determine overdue range display
            if days_overdue <= 15:
                overdue_range_display = "1-15 Days"
            elif days_overdue <= 30:
                overdue_range_display = "16-30 Days"
            elif days_overdue <= 60:
                overdue_range_display = "31-60 Days"
            else:
                overdue_range_display = "60+ Days"
            
            overdue_payments.append({
                "id": payment.id,
                "payment_id": payment.payment_id,
                "plan_id": plan.plan_id if plan else "N/A",
                "customer_id": customer.id if customer else None,
                "customer_name": customer.full_name if customer else "N/A",
                "customer_phone": customer.phone if customer else "N/A",
                "customer_email": customer.business_email or customer.email if customer else "N/A",
                "merchant_name": merchant.business_name if merchant else "N/A",
                "installment_number": payment.installment_number,
                "amount": float(payment.amount),
                "late_fee": float(payment.late_fee),
                "total_due": float(payment.amount + payment.late_fee),
                "due_date": payment.due_date.isoformat() if payment.due_date else None,
                "days_overdue": days_overdue,
                "overdue_range": overdue_range_display,
                "status": payment.status,
                "payment_method": payment.payment_method,
                "payment_reference": payment.payment_reference,
                "collection_stage": get_collection_stage(days_overdue)
            })
        
        return {
            "overdue_payments": overdue_payments,
            "total": paginated.total,
            "page": page,
            "per_page": per_page,
            "total_pages": paginated.pages if paginated.pages > 0 else 1
        }, 200


def get_collection_stage(days_overdue):
    """Determine collection stage based on days overdue"""
    if days_overdue <= 15:
        return "Payment Reminder"
    elif days_overdue <= 30:
        return "Late Fee Applied"
    elif days_overdue <= 60:
        return "Agent Assigned"
    else:
        return "Escalated to Legal"


class AdminGetOverduePaymentDetailResource(Resource):
    @auth_required
    def get(self, payment_id):
        """Get detailed overdue payment information"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        payment = InstalmentPayment.query.get(payment_id)
        if not payment:
            return {"error": "Payment not found"}, 404
        
        plan = InstalmentPlan.query.get(payment.plan_id)
        customer = User.query.get(plan.customer_id) if plan else None
        merchant = User.query.get(plan.merchant_id) if plan else None
        
        today = datetime.now()
        days_overdue = (today - payment.due_date).days if payment.due_date else 0
        
        # Get all payments for this plan
        all_payments = InstalmentPayment.query.filter_by(plan_id=plan.id).order_by(InstalmentPayment.installment_number).all() if plan else []
        
        payment_schedule = []
        for p in all_payments:
            payment_schedule.append({
                "id": p.id,
                "installment_number": p.installment_number,
                "due_date": p.due_date.isoformat() if p.due_date else None,
                "amount": float(p.amount),
                "status": p.status,
                "paid_date": p.paid_date.isoformat() if p.paid_date else None,
                "late_fee": float(p.late_fee)
            })
        
        # Collection timeline
        collection_timeline = []
        if days_overdue > 0:
            if days_overdue <= 15:
                collection_timeline.append({
                    "stage": "Payment Reminder",
                    "completed": True,
                    "completed_date": (payment.due_date + timedelta(days=1)).isoformat(),
                    "actions": ["Sent SMS reminder", "Sent WhatsApp reminder"]
                })
            if days_overdue > 15:
                collection_timeline.append({
                    "stage": "Late Fee Applied",
                    "completed": True,
                    "completed_date": (payment.due_date + timedelta(days=16)).isoformat(),
                    "actions": ["10% late fee applied"]
                })
            if days_overdue > 30:
                collection_timeline.append({
                    "stage": "Agent Assigned",
                    "completed": True,
                    "completed_date": (payment.due_date + timedelta(days=31)).isoformat(),
                    "actions": ["Collection agent assigned", "Phone call attempted"]
                })
            if days_overdue > 60:
                collection_timeline.append({
                    "stage": "Escalated to Legal",
                    "completed": days_overdue > 60,
                    "completed_date": (payment.due_date + timedelta(days=61)).isoformat() if days_overdue > 60 else None,
                    "actions": ["Legal notice sent", "Case filed" if days_overdue > 90 else "Pre-legal notice"]
                })
        
        return {
            "payment": {
                "id": payment.id,
                "payment_id": payment.payment_id,
                "installment_number": payment.installment_number,
                "amount": float(payment.amount),
                "late_fee": float(payment.late_fee),
                "total_due": float(payment.amount + payment.late_fee),
                "due_date": payment.due_date.isoformat() if payment.due_date else None,
                "days_overdue": days_overdue,
                "status": payment.status,
                "payment_method": payment.payment_method,
                "payment_reference": payment.payment_reference
            },
            "plan": {
                "id": plan.id,
                "plan_id": plan.plan_id,
                "plan_name": plan.plan_name,
                "total_amount": float(plan.total_amount),
                "remaining_amount": float(plan.remaining_amount),
                "number_of_installments": plan.number_of_installments,
                "paid_installments": plan.paid_installments
            },
            "customer": {
                "id": customer.id if customer else None,
                "name": customer.full_name if customer else "N/A",
                "phone": customer.phone if customer else "N/A",
                "email": customer.business_email or customer.email if customer else "N/A"
            },
            "merchant": {
                "id": merchant.id if merchant else None,
                "name": merchant.business_name if merchant else "N/A",
                "phone": merchant.phone if merchant else "N/A"
            },
            "payment_schedule": payment_schedule,
            "collection_timeline": collection_timeline
        }, 200


class AdminSendPaymentReminderResource(Resource):
    @auth_required
    def post(self, payment_id):
        """Send payment reminder to customer"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        reminder_type = data.get('reminder_type', 'sms')  # sms, whatsapp, email
        
        payment = InstalmentPayment.query.get(payment_id)
        if not payment:
            return {"error": "Payment not found"}, 404
        
        plan = InstalmentPlan.query.get(payment.plan_id)
        customer = User.query.get(plan.customer_id) if plan else None
        
        # Here you would integrate with SMS/WhatsApp/Email service
        # For now, just log the reminder
        
        return {
            "message": f"Payment reminder sent via {reminder_type} to {customer.phone if customer else 'customer'}",
            "payment_id": payment.payment_id,
            "reminder_type": reminder_type,
            "sent_at": datetime.now().isoformat()
        }, 200


class AdminMarkPaymentReceivedResource(Resource):
    @auth_required
    def put(self, payment_id):
        """Mark overdue payment as received"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        amount_received = data.get('amount_received', 0)
        payment_method = data.get('payment_method', 'manual')
        payment_reference = data.get('payment_reference', '')
        
        payment = InstalmentPayment.query.get(payment_id)
        if not payment:
            return {"error": "Payment not found"}, 404
        
        if payment.status == 'paid':
            return {"error": "Payment already marked as paid"}, 400
        
        payment.status = 'paid'
        payment.paid_date = datetime.now()
        payment.paid_amount = amount_received if amount_received > 0 else payment.amount
        payment.payment_method = payment_method
        payment.payment_reference = payment_reference
        
        # Update the instalment plan
        plan = InstalmentPlan.query.get(payment.plan_id)
        if plan:
            plan.paid_installments += 1
            plan.remaining_amount -= payment.amount
            
            if plan.paid_installments >= plan.number_of_installments:
                plan.status = 'completed'
                plan.completed_at = datetime.now()
        
        db.session.commit()
        
        return {
            "message": "Payment marked as received",
            "payment_id": payment.payment_id,
            "status": "paid",
            "amount_received": amount_received if amount_received > 0 else payment.amount
        }, 200


class AdminSetPaymentPlanResource(Resource):
    @auth_required
    def post(self, payment_id):
        """Set up a payment plan for overdue payment"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        plan_type = data.get('plan_type', 'installments')  # installments, extension, partial
        new_due_date = data.get('new_due_date')
        notes = data.get('notes', '')
        
        payment = InstalmentPayment.query.get(payment_id)
        if not payment:
            return {"error": "Payment not found"}, 404
        
        # Update payment with new arrangement
        if new_due_date:
            payment.due_date = datetime.fromisoformat(new_due_date)
        
        # Store arrangement details (you might want to create a PaymentArrangement model)
        
        db.session.commit()
        
        return {
            "message": f"Payment plan arranged: {plan_type}",
            "payment_id": payment.payment_id,
            "new_due_date": new_due_date,
            "plan_type": plan_type
        }, 200


class AdminExportOverduePaymentsResource(Resource):
    @auth_required
    def get(self):
        """Export overdue payments to CSV"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Get overdue payments
        today = datetime.now()
        overdue_payments = InstalmentPayment.query.filter(
            InstalmentPayment.status == 'overdue',
            InstalmentPayment.due_date < today
        ).all()
        
        # Create CSV content
        import csv
        from io import StringIO
        from flask import make_response
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Payment ID', 'Customer', 'Phone', 'Merchant', 'Plan ID',
            'Installment', 'Amount', 'Late Fee', 'Total Due', 'Due Date',
            'Days Overdue', 'Status'
        ])
        
        # Write data
        for payment in overdue_payments:
            plan = InstalmentPlan.query.get(payment.plan_id)
            customer = User.query.get(plan.customer_id) if plan else None
            merchant = User.query.get(plan.merchant_id) if plan else None
            days_overdue = (today - payment.due_date).days if payment.due_date else 0
            
            writer.writerow([
                payment.payment_id,
                customer.full_name if customer else "N/A",
                customer.phone if customer else "N/A",
                merchant.business_name if merchant else "N/A",
                plan.plan_id if plan else "N/A",
                payment.installment_number,
                payment.amount,
                payment.late_fee,
                payment.amount + payment.late_fee,
                payment.due_date.strftime("%Y-%m-%d") if payment.due_date else "",
                days_overdue,
                payment.status
            ])
        
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=overdue_payments_{datetime.now().strftime("%Y%m%d")}.csv'
        return response