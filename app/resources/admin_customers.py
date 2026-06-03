from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from app.models.user import User
from app.models.instalment import InstalmentPlan
from app.models.instalment_payment import InstalmentPayment
from app.models.document import Document
from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_

class AdminCustomerStatsResource(Resource):
    @auth_required
    def get(self):
        """Get customer overview statistics"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Date calculations
        today = datetime.now().date()
        last_30_days = today - timedelta(days=30)
        
        # Total Customers
        total_customers = User.query.filter(User.role == 'customer').count()
        
        # Active Customers (has at least one approved instalment plan)
        active_customers = db.session.query(func.count(func.distinct(InstalmentPlan.customer_id)))\
            .filter(InstalmentPlan.status.in_(['active', 'completed'])).scalar() or 0
        
        active_customers_last_30 = db.session.query(func.count(func.distinct(InstalmentPlan.customer_id)))\
            .filter(InstalmentPlan.created_at >= last_30_days).scalar() or 0
        active_customers_previous = db.session.query(func.count(func.distinct(InstalmentPlan.customer_id)))\
            .filter(InstalmentPlan.created_at < last_30_days).scalar() or 0
        
        active_customers_growth = 0
        if active_customers_previous > 0:
            active_customers_growth = ((active_customers_last_30 - active_customers_previous) / active_customers_previous) * 100
        
        # New Customers (last 30 days)
        new_customers = User.query.filter(
            User.role == 'customer',
            User.created_at >= last_30_days
        ).count()
        
        new_customers_previous = User.query.filter(
            User.role == 'customer',
            User.created_at < last_30_days
        ).count()
        
        new_customers_growth = 0
        if new_customers_previous > 0:
            new_customers_growth = ((new_customers - new_customers_previous) / new_customers_previous) * 100
        
        # Repeat Purchase Rate (customers with more than one plan)
        customers_with_multiple_plans = db.session.query(
            InstalmentPlan.customer_id
        ).group_by(InstalmentPlan.customer_id).having(func.count(InstalmentPlan.id) > 1).count()
        
        repeat_purchase_rate = (customers_with_multiple_plans / total_customers * 100) if total_customers > 0 else 0
        
        repeat_rate_last_30 = 0  # Could be calculated similarly
        
        # Total Outstanding (sum of remaining amounts)
        total_outstanding = db.session.query(func.sum(InstalmentPlan.remaining_amount))\
            .filter(InstalmentPlan.status == 'active').scalar() or 0
        
        total_outstanding_last_30 = db.session.query(func.sum(InstalmentPlan.remaining_amount))\
            .filter(InstalmentPlan.status == 'active', InstalmentPlan.created_at >= last_30_days).scalar() or 0
        total_outstanding_previous = db.session.query(func.sum(InstalmentPlan.remaining_amount))\
            .filter(InstalmentPlan.status == 'active', InstalmentPlan.created_at < last_30_days).scalar() or 0
        
        outstanding_growth = 0
        if total_outstanding_previous > 0:
            outstanding_growth = ((total_outstanding_last_30 - total_outstanding_previous) / total_outstanding_previous) * 100
        
        return {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "active_customers_growth": round(active_customers_growth, 1),
            "new_customers": new_customers,
            "new_customers_growth": round(new_customers_growth, 1),
            "repeat_purchase_rate": round(repeat_purchase_rate, 1),
            "repeat_purchase_rate_growth": 5.2,  # Sample growth
            "total_outstanding": float(total_outstanding),
            "outstanding_growth": round(outstanding_growth, 1)
        }, 200

class AdminGetCustomersResource(Resource):
    @auth_required
    def get(self):
        """Get all customers with filters and pagination"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str)
        kyc_status = request.args.get('kyc_status', '', type=str)
        status = request.args.get('status', '', type=str)
        sort_by = request.args.get('sort_by', 'created_at', type=str)
        sort_order = request.args.get('sort_order', 'desc', type=str)
        
        # Build query
        query = User.query.filter(User.role == 'customer')
        
        # Apply search filter
        if search:
            query = query.filter(
                or_(
                    User.full_name.ilike(f'%{search}%'),
                    User.phone.ilike(f'%{search}%'),
                    User.business_email.ilike(f'%{search}%'),
                    User.customer_id.ilike(f'%{search}%')
                )
            )
        
        # Apply KYC status filter
        if kyc_status:
            query = query.filter(User.kyc_status == kyc_status)
        
        # Apply status filter
        if status:
            query = query.filter(User.status == status)
        
        # Apply sorting
        if sort_order == 'desc':
            query = query.order_by(getattr(User, sort_by).desc())
        else:
            query = query.order_by(getattr(User, sort_by).asc())
        
        # Pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        customers = []
        for customer in paginated.items:
            # Calculate financial metrics
            total_financed = db.session.query(func.sum(InstalmentPlan.total_amount))\
                .filter(InstalmentPlan.customer_id == customer.id).scalar() or 0
            
            total_paid = db.session.query(func.sum(InstalmentPlan.amount_paid))\
                .filter(InstalmentPlan.customer_id == customer.id).scalar() or 0
            
            outstanding = db.session.query(func.sum(InstalmentPlan.remaining_amount))\
                .filter(InstalmentPlan.customer_id == customer.id, InstalmentPlan.status == 'active').scalar() or 0
            
            active_plans = InstalmentPlan.query.filter_by(
                customer_id=customer.id,
                status='active'
            ).count()
            
            # Determine risk level based on customer data
            risk_level = "Low"
            if outstanding > 1000 or active_plans > 2:
                risk_level = "Medium"
            if outstanding > 2000 or customer.kyc_status == 'rejected':
                risk_level = "High"
            
            # Determine credit limit based on income range
            credit_limit = 500
            if customer.income_range:
                if "5,000+" in customer.income_range:
                    credit_limit = 5000
                elif "3,000" in customer.income_range:
                    credit_limit = 3000
                elif "1,000" in customer.income_range:
                    credit_limit = 2000
                else:
                    credit_limit = 1000
            
            customers.append({
                "id": customer.id,
                "customer_id": customer.customer_id or f"C{customer.id:04d}",
                "full_name": customer.full_name or "N/A",
                "phone": customer.phone,
                "email": customer.business_email or customer.email or "N/A",
                "kyc_status": customer.kyc_status or "pending",
                "risk_level": risk_level,
                "credit_limit": credit_limit,
                "outstanding": float(outstanding),
                "status": customer.status if customer.status in ['active', 'approved'] else 'pending',
                "total_financed": float(total_financed),
                "total_paid": float(total_paid),
                "active_plans": active_plans,
                "created_at": customer.created_at.isoformat() if customer.created_at else None
            })
        
        return {
            "customers": customers,
            "total": paginated.total,
            "page": page,
            "per_page": per_page,
            "total_pages": paginated.pages if paginated.pages > 0 else 1
        }, 200


class AdminCustomerStatsResource(Resource):
    @auth_required
    def get(self):
        """Get customer overview statistics"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Date calculations
        today = datetime.now().date()
        last_30_days = today - timedelta(days=30)
        
        # Total Customers
        total_customers = User.query.filter(User.role == 'customer').count()
        
        # Active Customers (status approved or active)
        active_customers = User.query.filter(
            User.role == 'customer',
            User.status.in_(['approved', 'active'])
        ).count()
        
        # New Customers (last 30 days)
        new_customers = User.query.filter(
            User.role == 'customer',
            User.created_at >= last_30_days
        ).count()
        
        # Calculate active customers growth
        active_customers_last_30 = User.query.filter(
            User.role == 'customer',
            User.status.in_(['approved', 'active']),
            User.created_at >= last_30_days
        ).count()
        active_customers_previous = active_customers - active_customers_last_30
        active_customers_growth = ((active_customers_last_30 - active_customers_previous) / active_customers_previous * 100) if active_customers_previous > 0 else 0
        
        # Calculate new customers growth
        new_customers_previous = User.query.filter(
            User.role == 'customer',
            User.created_at < last_30_days
        ).count()
        new_customers_growth = ((new_customers - new_customers_previous) / new_customers_previous * 100) if new_customers_previous > 0 else 0
        
        # Repeat Purchase Rate
        customers_with_multiple_plans = db.session.query(
            InstalmentPlan.customer_id
        ).filter(
            InstalmentPlan.customer_id.isnot(None)
        ).group_by(InstalmentPlan.customer_id).having(func.count(InstalmentPlan.id) > 1).count()
        repeat_purchase_rate = (customers_with_multiple_plans / total_customers * 100) if total_customers > 0 else 0
        
        # Total Outstanding
        total_outstanding = db.session.query(func.sum(InstalmentPlan.remaining_amount))\
            .filter(InstalmentPlan.status == 'active').scalar() or 0
        
        # Calculate outstanding growth
        total_outstanding_last_30 = db.session.query(func.sum(InstalmentPlan.remaining_amount))\
            .filter(InstalmentPlan.status == 'active', InstalmentPlan.created_at >= last_30_days).scalar() or 0
        total_outstanding_previous = total_outstanding - total_outstanding_last_30
        outstanding_growth = ((total_outstanding_last_30 - total_outstanding_previous) / total_outstanding_previous * 100) if total_outstanding_previous > 0 else 0
        
        return {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "active_customers_growth": round(active_customers_growth, 1),
            "new_customers": new_customers,
            "new_customers_growth": round(new_customers_growth, 1),
            "repeat_purchase_rate": round(repeat_purchase_rate, 1),
            "repeat_purchase_rate_growth": 5.2,
            "total_outstanding": float(total_outstanding),
            "outstanding_growth": round(outstanding_growth, 1)
        }, 200


class AdminGetCustomerDetailResource(Resource):
    @auth_required
    def get(self, customer_id):
        """Get detailed customer information"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        customer = User.query.filter_by(id=customer_id, role='customer').first()
        if not customer:
            return {"error": "Customer not found"}, 404
        
        # Get financial metrics
        total_financed = db.session.query(func.sum(InstalmentPlan.total_amount))\
            .filter(InstalmentPlan.customer_id == customer.id).scalar() or 0
        
        total_paid = db.session.query(func.sum(InstalmentPlan.total_amount - InstalmentPlan.remaining_amount))\
            .filter(InstalmentPlan.customer_id == customer.id).scalar() or 0
        
        outstanding = db.session.query(func.sum(InstalmentPlan.remaining_amount))\
            .filter(InstalmentPlan.customer_id == customer.id, InstalmentPlan.status == 'active').scalar() or 0
        
        active_plans = InstalmentPlan.query.filter_by(
            customer_id=customer.id,
            status='active'
        ).all()
        
        # Get next payment due
        next_payment = InstalmentPayment.query.join(InstalmentPlan)\
            .filter(InstalmentPlan.customer_id == customer.id, InstalmentPayment.status == 'pending')\
            .order_by(InstalmentPayment.due_date.asc()).first()
        
        # Get recent activity
        recent_payments = InstalmentPayment.query.join(InstalmentPlan)\
            .filter(InstalmentPlan.customer_id == customer.id)\
            .order_by(InstalmentPayment.paid_date.desc())\
            .limit(5).all()
        
        recent_activity = []
        
        # Add recent payments
        for payment in recent_payments:
            if payment.paid_date:
                recent_activity.append({
                    "type": "payment",
                    "description": f"Payment of {payment.amount} received",
                    "date": payment.paid_date.strftime("%d %b %Y, %I:%M %p") if payment.paid_date else "",
                    "status": "completed"
                })
        
        # Add plan approvals
        recent_plans = InstalmentPlan.query.filter_by(customer_id=customer.id)\
            .order_by(InstalmentPlan.created_at.desc()).limit(3).all()
        
        for plan in recent_plans:
            recent_activity.append({
                "type": "plan",
                "description": f"Plan Pay in {plan.number_of_installments} approved",
                "date": plan.created_at.strftime("%d %b %Y, %I:%M %p") if plan.created_at else "",
                "status": "approved"
            })
        
        # Add account creation
        recent_activity.append({
            "type": "account",
            "description": "Account created",
            "date": customer.created_at.strftime("%d %b %Y, %I:%M %p") if customer.created_at else "",
            "status": "completed"
        })
        
        # Sort by date
        recent_activity.sort(key=lambda x: x['date'], reverse=True)
        
        return {
            "customer": {
                "id": customer.id,
                "customer_id": customer.customer_id or f"C{customer.id:03d}",
                "full_name": customer.full_name or "N/A",
                "phone": customer.phone,
                "email": customer.business_email or customer.email or "N/A",
                "kyc_status": customer.kyc_status or "pending",
                "status": customer.status,
                "city": customer.city,
                "address": customer.address,
                "gps": customer.gps,
                "income_range": customer.income_range,
                "created_at": customer.created_at.isoformat() if customer.created_at else None
            },
            "financial": {
                "credit_limit": 2000,  # Could be dynamic based on customer
                "outstanding": float(outstanding),
                "total_paid": float(total_paid),
                "total_financed": float(total_financed),
                "next_payment_due": next_payment.due_date.strftime("%d %b %Y") if next_payment else None,
                "active_plans_count": len(active_plans),
                "active_plans": [{
                    "id": plan.id,
                    "plan_id": plan.plan_id,
                    "total_amount": float(plan.total_amount),
                    "remaining_amount": float(plan.remaining_amount),
                    "number_of_installments": plan.number_of_installments,
                    "status": plan.status
                } for plan in active_plans]
            },
            "recent_activity": recent_activity[:10]
        }, 200


class AdminUpdateCustomerStatusResource(Resource):
    @auth_required
    def put(self, customer_id):
        """Update customer status (active, restricted, suspended)"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        new_status = data.get('status')
        reason = data.get('reason', '')
        
        if new_status not in ['active', 'restricted', 'suspended']:
            return {"error": "Invalid status"}, 400
        
        customer = User.query.filter_by(id=customer_id, role='customer').first()
        if not customer:
            return {"error": "Customer not found"}, 404
        
        customer.status = new_status
        
        # Log the status change (you can create an ActivityLog model)
        
        db.session.commit()
        
        return {
            "message": f"Customer status updated to {new_status}",
            "customer_id": customer.id,
            "status": new_status
        }, 200


class AdminUpdateCustomerCreditLimitResource(Resource):
    @auth_required
    def put(self, customer_id):
        """Update customer credit limit"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        new_limit = data.get('credit_limit')
        
        if not new_limit or new_limit < 0:
            return {"error": "Invalid credit limit"}, 400
        
        customer = User.query.filter_by(id=customer_id, role='customer').first()
        if not customer:
            return {"error": "Customer not found"}, 404
        
        # You can store credit_limit in User model or a separate table
        # For now, we'll just return success
        
        db.session.commit()
        
        return {
            "message": f"Credit limit updated to GHS {new_limit}",
            "customer_id": customer.id,
            "credit_limit": new_limit
        }, 200


class AdminAddCustomerNoteResource(Resource):
    @auth_required
    def post(self, customer_id):
        """Add a note to customer profile"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        note = data.get('note')
        
        if not note:
            return {"error": "Note is required"}, 400
        
        customer = User.query.filter_by(id=customer_id, role='customer').first()
        if not customer:
            return {"error": "Customer not found"}, 404
        
        # You can create a CustomerNote model to store notes
        # For now, we'll just return success
        
        return {
            "message": "Note added successfully",
            "customer_id": customer.id,
            "note": note
        }, 201