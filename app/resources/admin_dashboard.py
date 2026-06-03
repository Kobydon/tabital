from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.models.instalment import InstalmentPlan
from app.models.instalment_payment import InstalmentPayment
from app.models.document import Document
from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, and_

class AdminDashboardStatsResource(Resource):
    @auth_required
    def get(self):
        """Get admin dashboard statistics"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Date calculations
        today = datetime.now().date()
        last_30_days = today - timedelta(days=30)
        previous_30_days = last_30_days - timedelta(days=30)
        
        # Total Financed (All Time) - Using customer_id instead of user_id
        total_financed = db.session.query(func.sum(InstalmentPlan.total_amount)).scalar() or 0
        
        # Total Financed (Last 30 days)
        total_financed_last_30 = db.session.query(func.sum(InstalmentPlan.total_amount))\
            .filter(InstalmentPlan.created_at >= last_30_days).scalar() or 0
        
        # Previous 30 days for growth calculation
        total_financed_previous_30 = db.session.query(func.sum(InstalmentPlan.total_amount))\
            .filter(InstalmentPlan.created_at.between(previous_30_days, last_30_days)).scalar() or 0
        
        financed_growth = 0
        if total_financed_previous_30 > 0:
            financed_growth = ((total_financed_last_30 - total_financed_previous_30) / total_financed_previous_30) * 100
        
        # Active Customers (customers with at least one plan) - FIXED: use customer_id
        active_customers = db.session.query(func.count(func.distinct(InstalmentPlan.customer_id)))\
            .filter(InstalmentPlan.status.in_(['active', 'completed'])).scalar() or 0
        
        active_customers_last_30 = db.session.query(func.count(func.distinct(InstalmentPlan.customer_id)))\
            .filter(InstalmentPlan.created_at >= last_30_days).scalar() or 0
        
        active_customers_previous_30 = db.session.query(func.count(func.distinct(InstalmentPlan.customer_id)))\
            .filter(InstalmentPlan.created_at.between(previous_30_days, last_30_days)).scalar() or 0
        
        customers_growth = 0
        if active_customers_previous_30 > 0:
            customers_growth = ((active_customers_last_30 - active_customers_previous_30) / active_customers_previous_30) * 100
        
        # Active Merchants (merchants with approved status)
        active_merchants = User.query.filter(
            User.role == 'merchant',
            User.status == 'approved'
        ).count()
        
        active_merchants_last_30 = User.query.filter(
            User.role == 'merchant',
            User.status == 'approved',
            User.created_at >= last_30_days
        ).count()
        
        active_merchants_previous_30 = User.query.filter(
            User.role == 'merchant',
            User.status == 'approved',
            User.created_at.between(previous_30_days, last_30_days)
        ).count()
        
        merchants_growth = 0
        if active_merchants_previous_30 > 0:
            merchants_growth = ((active_merchants_last_30 - active_merchants_previous_30) / active_merchants_previous_30) * 100
        
        # Repayment Rate (percentage of completed plans)
        total_plans = InstalmentPlan.query.count()
        completed_plans = InstalmentPlan.query.filter_by(status='completed').count()
        repayment_rate = (completed_plans / total_plans * 100) if total_plans > 0 else 0
        
        repayment_rate_last_30 = 0
        completed_last_30 = InstalmentPlan.query.filter(
            InstalmentPlan.status == 'completed',
            InstalmentPlan.completed_at >= last_30_days
        ).count()
        total_last_30 = InstalmentPlan.query.filter(InstalmentPlan.created_at >= last_30_days).count()
        if total_last_30 > 0:
            repayment_rate_last_30 = (completed_last_30 / total_last_30) * 100
        
        # Default Rate
        defaulted_plans = InstalmentPlan.query.filter_by(status='defaulted').count()
        default_rate = (defaulted_plans / total_plans * 100) if total_plans > 0 else 0
        
        # Revenue MTD (commission earned this month)
        current_month_start = today.replace(day=1)
        # Assuming commission is 10% of total_amount (you can adjust based on your logic)
        revenue_mtd = db.session.query(func.sum(InstalmentPlan.total_amount * 0.1))\
            .filter(InstalmentPlan.status == 'completed',
                   InstalmentPlan.completed_at >= current_month_start).scalar() or 0
        
        revenue_last_month = db.session.query(func.sum(InstalmentPlan.total_amount * 0.1))\
            .filter(InstalmentPlan.status == 'completed',
                   InstalmentPlan.completed_at.between(current_month_start - timedelta(days=30), current_month_start)).scalar() or 0
        
        revenue_growth = 0
        if revenue_last_month > 0:
            revenue_growth = ((revenue_mtd - revenue_last_month) / revenue_last_month) * 100
        
        # Portfolio Overview - Using remaining_amount
        total_exposure = total_financed
        # For risk calculation, we need to query payments that are overdue
        # Get sum of overdue payments from InstalmentPayment table
        overdue_payments_sum = db.session.query(func.sum(InstalmentPayment.amount))\
            .filter(InstalmentPayment.status == 'overdue',
                   InstalmentPayment.due_date < datetime.now()).scalar() or 0
        
        # Simplified risk calculation (you can adjust based on your business logic)
        early_risk = overdue_payments_sum * 0.3  # Placeholder
        late_risk = overdue_payments_sum * 0.5   # Placeholder
        default_risk = overdue_payments_sum * 0.2  # Placeholder
        
        # Alerts
        alerts = {
            "high_risk_transactions": 23,
            "failed_payments": 54,
            "overdue_installments": InstalmentPayment.query.filter(InstalmentPayment.status == 'overdue').count(),
            "chargebacks": 17,
            "system_notifications": 12
        }
        
        # Pending Approvals
        pending_approvals = {
            "kyc_verifications": Document.query.filter_by(status='pending').count(),
            "merchant_onboarding": User.query.filter_by(role='merchant', status='pending').count(),
            "transaction_approvals": 12,
            "refund_requests": 5,
            "limit_increase_requests": 9
        }
        
        # Installment Status - Using InstalmentPayment for more accurate stats
        paid_on_time = InstalmentPayment.query.filter_by(status='paid').count()
        paid_late = InstalmentPayment.query.filter(InstalmentPayment.status == 'paid', InstalmentPayment.late_fee > 0).count()
        upcoming = InstalmentPayment.query.filter_by(status='pending').filter(InstalmentPayment.due_date >= datetime.now()).count()
        overdue = InstalmentPayment.query.filter_by(status='overdue').count()
        
        total_payments = paid_on_time + paid_late + upcoming + overdue
        
        # Top Merchants by GMV
        top_merchants = db.session.query(
            User.business_name,
            func.sum(InstalmentPlan.total_amount).label('gmv')
        ).join(InstalmentPlan, User.id == InstalmentPlan.merchant_id)\
         .filter(User.role == 'merchant')\
         .group_by(User.id)\
         .order_by(func.sum(InstalmentPlan.total_amount).desc())\
         .limit(5).all()
        
        merchants_list = [{"name": m[0] or "Unknown", "gmv": float(m[1])} for m in top_merchants]
        
        # Recent Transactions - Fixed to use customer relationship
        recent_transactions = db.session.query(
            InstalmentPlan.plan_id.label('txn_id'),
            User.full_name.label('customer'),
            User.business_name.label('merchant'),
            InstalmentPlan.total_amount.label('amount'),
            InstalmentPlan.number_of_installments.label('plan'),
            InstalmentPlan.status.label('status'),
            InstalmentPlan.created_at.label('time')
        ).join(User, InstalmentPlan.customer_id == User.id)\
         .order_by(InstalmentPlan.created_at.desc())\
         .limit(5).all()
        
        transactions = []
        for t in recent_transactions:
            status_display = 'Completed' if t.status == 'completed' else 'Approved' if t.status == 'active' else 'Pending' if t.status == 'pending' else 'Failed'
            transactions.append({
                "txn_id": t.txn_id,
                "customer": t.customer or 'N/A',
                "merchant": t.merchant or 'N/A',
                "amount": float(t.amount),
                "plan": f"Pay in {t.plan}",
                "status": status_display,
                "time": t.time.strftime("%d %b, %I:%M %p") if t.time else ""
            })
        
        return {
            "stats": {
                "total_financed": float(total_financed),
                "total_financed_growth": round(financed_growth, 1),
                "active_customers": active_customers,
                "active_customers_growth": round(customers_growth, 1),
                "active_merchants": active_merchants,
                "active_merchants_growth": round(merchants_growth, 1),
                "repayment_rate": round(repayment_rate, 1),
                "repayment_rate_growth": round(repayment_rate_last_30 - repayment_rate, 1),
                "default_rate": round(default_rate, 1),
                "revenue_mtd": float(revenue_mtd),
                "revenue_growth": round(revenue_growth, 1)
            },
            "portfolio": {
                "total_exposure": float(total_exposure),
                "early_risk": float(early_risk),
                "early_percentage": round((early_risk / total_exposure * 100) if total_exposure > 0 else 0, 1),
                "late_risk": float(late_risk),
                "late_percentage": round((late_risk / total_exposure * 100) if total_exposure > 0 else 0, 1),
                "default_risk": float(default_risk),
                "default_percentage": round((default_risk / total_exposure * 100) if total_exposure > 0 else 0, 1)
            },
            "alerts": alerts,
            "pending_approvals": pending_approvals,
            "installment_status": {
                "paid_on_time": paid_on_time,
                "paid_on_time_percentage": round((paid_on_time / total_payments * 100) if total_payments > 0 else 0, 1),
                "paid_late": paid_late,
                "paid_late_percentage": round((paid_late / total_payments * 100) if total_payments > 0 else 0, 1),
                "upcoming": upcoming,
                "upcoming_percentage": round((upcoming / total_payments * 100) if total_payments > 0 else 0, 1),
                "overdue": overdue,
                "overdue_percentage": round((overdue / total_payments * 100) if total_payments > 0 else 0, 1)
            },
            "top_merchants": merchants_list,
            "recent_transactions": transactions
        }, 200


class AdminRecentTransactionsResource(Resource):
    @auth_required
    def get(self):
        """Get recent transactions for admin dashboard"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        limit = request.args.get('limit', 10, type=int)
        
        recent_transactions = db.session.query(
            InstalmentPlan.plan_id.label('txn_id'),
            User.full_name.label('customer'),
            User.business_name.label('merchant'),
            InstalmentPlan.total_amount.label('amount'),
            InstalmentPlan.number_of_installments.label('plan'),
            InstalmentPlan.status.label('status'),
            InstalmentPlan.created_at.label('time')
        ).join(User, InstalmentPlan.customer_id == User.id)\
         .order_by(InstalmentPlan.created_at.desc())\
         .limit(limit).all()
        
        transactions = []
        for t in recent_transactions:
            status_display = 'Completed' if t.status == 'completed' else 'Approved' if t.status == 'active' else 'Pending' if t.status == 'pending' else 'Failed'
            transactions.append({
                "txn_id": t.txn_id,
                "customer": t.customer or 'N/A',
                "merchant": t.merchant or 'N/A',
                "amount": float(t.amount),
                "plan": f"Pay in {t.plan}",
                "status": status_display,
                "time": t.time.strftime("%d %b, %I:%M %p") if t.time else ""
            })
        
        return {"transactions": transactions}, 200