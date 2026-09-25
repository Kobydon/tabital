from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from app.models.user import User
from app.models.instalment import InstalmentPlan
from app.models.instalment_payment import InstalmentPayment
from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, or_

# §8.4 buckets: (key, label, min days past due, max days past due or None)
BUCKETS = [
    ('dpd_1_30', '1-30', 1, 30),
    ('dpd_31_60', '31-60', 31, 60),
    ('dpd_61_90', '61-90', 61, 90),
    ('dpd_90_plus', '90+', 91, None),
]


def _overdue_query(min_days, max_days, today):
    """Unpaid overdue instalments whose days past due fall in [min_days, max_days]."""
    start_of_today = datetime(today.year, today.month, today.day)
    q = InstalmentPayment.query.filter(
        InstalmentPayment.status == 'overdue',
        InstalmentPayment.due_date <= start_of_today - timedelta(days=min_days))
    if max_days is not None:
        q = q.filter(InstalmentPayment.due_date > start_of_today - timedelta(days=max_days + 1))
    return q


class AdminCollectionStatsResource(Resource):
    @auth_required
    def get(self):
        """Collection statistics by §8.4 delinquency bucket (real figures only)."""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        today = datetime.now().date()
        overdue = InstalmentPayment.query.filter(InstalmentPayment.status == 'overdue').all()
        total_overdue = sum((p.amount or 0) + (p.late_fee or 0 if not p.late_fee_paid else 0) for p in overdue)
        accounts_overdue = len({p.plan.customer_id for p in overdue if p.plan})
        
        body = {
            "total_overdue": float(total_overdue),
            "accounts_overdue": accounts_overdue,
        }
        for key, label, lo, hi in BUCKETS:
            rows = _overdue_query(lo, hi, today).all()
            body[f"overdue_{key}"] = float(sum((p.amount or 0) + (p.late_fee or 0) for p in rows))
            body[f"count_{key}"] = len(rows)
        body["buckets"] = [{"key": k, "label": f"{label} days"} for k, label, _, _ in BUCKETS]
        return body, 200


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
        overdue_range = request.args.get('overdue_range', '', type=str)  # 1-30, 31-60, 61-90, 90+ (§8.4)
        status = request.args.get('status', '', type=str)
        
        # Build query for overdue payments
        today = datetime.now()
        query = InstalmentPayment.query.filter(
            InstalmentPayment.status == 'overdue',
            InstalmentPayment.due_date < today
        )
        
        # Apply overdue range filter
        if overdue_range:
            for _key, label, lo, hi in BUCKETS:
                if overdue_range == label:
                    start_of_today = datetime(today.year, today.month, today.day)
                    query = query.filter(InstalmentPayment.due_date <= start_of_today - timedelta(days=lo))
                    if hi is not None:
                        query = query.filter(InstalmentPayment.due_date > start_of_today - timedelta(days=hi + 1))
        
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
            
            days_overdue = (today.date() - payment.due_date.date()).days
            overdue_range_display = next((f"{label} Days" for _k, label, lo, hi in BUCKETS
                                          if days_overdue >= lo and (hi is None or days_overdue <= hi)), "Current")
            
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
                "collection_stage": get_collection_stage(days_overdue, plan)
            })
        
        return {
            "overdue_payments": overdue_payments,
            "total": paginated.total,
            "page": page,
            "per_page": per_page,
            "total_pages": paginated.pages if paginated.pages > 0 else 1
        }, 200


STAGE_LABELS = {
    'reminders': 'Automated reminders',
    'call_centre': 'Collections call centre',
    'employer_contact': 'Employer-assisted contact',
    'bureau_reporting': 'Credit bureau reporting',
    'legal_recovery': 'Legal recovery (high-ticket)',
}


def get_collection_stage(days_overdue, plan=None):
    """§8.5 recovery ladder for this many days past due."""
    from app.models.system_settings import SystemSetting
    from app.services.servicing import collection_stage
    stage = collection_stage(days_overdue, plan.total_amount if plan else None,
                             SystemSetting.get_value("high_ticket_threshold", 10000))
    return STAGE_LABELS.get(stage, 'Current')


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
        days_overdue = (today.date() - payment.due_date.date()).days if payment.due_date else 0
        
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
        
        # Timeline of what actually happened: late fees charged and messages actually sent
        from app.models.message_outbox import MessageOutbox
        collection_timeline = []
        if payment.late_fee_applied_date:
            collection_timeline.append({"stage": "Late fee charged", "completed": True,
                                        "completed_date": payment.late_fee_applied_date.isoformat(),
                                        "actions": ["First late fee"]})
        if payment.second_late_fee_applied_date:
            collection_timeline.append({"stage": "Second late fee charged", "completed": True,
                                        "completed_date": payment.second_late_fee_applied_date.isoformat(),
                                        "actions": ["Additional late fee (31+ days past due)"]})
        for m in MessageOutbox.query.filter_by(payment_id=payment.id).order_by(MessageOutbox.created_at).all():
            collection_timeline.append({"stage": f"Reminder: {m.template.replace('_', ' ')}",
                                        "completed": m.status == MessageOutbox.SENT,
                                        "completed_date": (m.sent_at or m.created_at).isoformat(),
                                        "actions": [f"{m.channel.upper()} {m.status}"]})
        collection_timeline.sort(key=lambda x: x["completed_date"] or "")
        current_stage = get_collection_stage(days_overdue, plan)
        
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
                "remaining_amount": plan.outstanding_balance,
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
            "collection_timeline": collection_timeline,
            "collection_stage": current_stage
        }, 200


class AdminSendPaymentReminderResource(Resource):
    @auth_required
    def post(self, payment_id):
        """Send payment reminder to customer"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        from app.extensions import db as _db
        from app.models.message_outbox import MessageOutbox
        from app.services import reminders
        from app.services.sms import to_e164

        data = request.get_json() or {}
        channel = data.get('reminder_type', 'sms')
        if channel not in ('sms', 'whatsapp', 'in_app'):
            return {"error": "reminder_type must be sms, whatsapp or in_app"}, 400

        payment = InstalmentPayment.query.get(payment_id)
        if not payment:
            return {"error": "Payment not found"}, 404
        if payment.status == 'paid':
            return {"error": "This instalment is already paid"}, 400

        plan = InstalmentPlan.query.get(payment.plan_id)
        customer = User.query.get(plan.customer_id) if plan else None
        if not customer:
            return {"error": "Customer not found"}, 404

        template = 'late_fee_charged' if payment.late_fee_applied_date else 'due_today'
        title, body = reminders.render(template, payment, plan)
        to = to_e164(customer.phone) if channel != 'in_app' else None
        if channel != 'in_app' and not to:
            return {"error": "The customer has no valid phone number"}, 400
        msg = MessageOutbox(user_id=customer.id, channel=channel, to_address=to, template='manual_reminder',
                            title=title, body=body, plan_id=plan.id, payment_id=payment.id,
                            dedupe_key=f"manual:{payment.id}:{channel}:{datetime.utcnow().timestamp()}")
        _db.session.add(msg)
        _db.session.commit()
        reminders.dispatch_pending()

        return {
            "message": f"Reminder {msg.status} via {channel}" + (f" ({msg.provider})" if msg.provider else ""),
            "payment_id": payment.payment_id,
            "reminder_type": channel,
            "status": msg.status,
            "provider": msg.provider,
            "sent_at": msg.sent_at.isoformat() if msg.sent_at else None
        }, 200


class AdminMarkPaymentReceivedResource(Resource):
    @auth_required
    def put(self, payment_id):
        """Mark overdue payment as received"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        from app.services.payments import mark_instalment_paid

        data = request.get_json() or {}
        amount_received = float(data.get('amount_received') or 0)
        payment_method = data.get('payment_method') or 'manual'
        payment_reference = (data.get('payment_reference') or '').strip()

        payment = InstalmentPayment.query.get(payment_id)
        if not payment:
            return {"error": "Payment not found"}, 404

        if payment.status == 'paid':
            return {"error": "Payment already marked as paid"}, 400

        payment_reference = payment_reference or payment.payment_reference
        if not payment_reference:
            return {"error": "Enter the MoMo/bank reference of the money received"}, 400

        total_due = payment.get_total_due()
        if amount_received and amount_received + 0.005 < total_due:
            # Partial payments need the ledger (Phase 1); don't mark a short payment as paid
            return {"error": f"Amount received is less than the {total_due:.2f} due"}, 400

        mark_instalment_paid(payment, payment_method, payment_reference, amount_received or None,
                             user=current_admin)
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
