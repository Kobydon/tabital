# resources/merchant_transactions.py - Update to show full amount
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user

from app.models.instalment import InstalmentPlan
from ..models.user import User
from ..models.transaction import Transaction
from ..extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, or_
class MerchantGetTransactionsResource(Resource):
    @auth_required
    def get(self):
        """Get all transactions for the merchant with filters"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        # Get query parameters
        status = request.args.get('status', '').strip()
        payment_status = request.args.get('payment_status', '').strip()
        search = request.args.get('search', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        limit = request.args.get('limit', 50, type=int)
        page = request.args.get('page', 1, type=int)
        
        # Base query - merchants see all transactions where they are the merchant
        # For instalment plans, they see the FULL transaction (one per instalment plan)
        # For individual payments, they see each payment (but we group by plan)
        
        # Get all instalment plans for this merchant
        instalment_plans = InstalmentPlan.query.filter_by(merchant_id=current_merchant.id).all()
        
        # For each instalment plan, create a "virtual" transaction showing the full amount
        result = []
        for plan in instalment_plans:
            result.append({
                "id": plan.id,
                "transaction_id": plan.plan_id,
                "customer_name": plan.customer_name or plan.customer.full_name,
                "customer_phone": plan.customer_phone or plan.customer.phone,
                "amount": plan.total_amount,
                "product_name": plan.plan_name,
                "product_description": plan.description,
                "quantity": 1,
                "payment_plan": f"{plan.number_of_installments} Months",
                "payment_status": plan.payment_status,
                "status": plan.status,
                "paid_amount": plan.total_amount - plan.remaining_amount,
                "remaining_amount": plan.remaining_amount,
                "transaction_date": plan.start_date.isoformat() if plan.start_date else "",
                "is_instalment": True
            })
        
        # Also get regular one-time transactions
        regular_transactions = Transaction.query.filter_by(
            merchant_id=current_merchant.id
        ).all()
        
        for t in regular_transactions:
            result.append({
                "id": t.id,
                "transaction_id": t.transaction_id,
                "customer_name": t.customer.full_name or t.customer.business_name,
                "customer_phone": t.customer.phone,
                "amount": t.amount,
                "product_name": t.product_name,
                "product_description": t.product_description,
                "quantity": t.quantity,
                "payment_plan": t.payment_plan,
                "payment_status": t.payment_status,
                "status": t.status,
                "transaction_date": t.transaction_date.isoformat() if t.transaction_date else "",
                "is_instalment": False
            })
        
        # Sort by date
        result.sort(key=lambda x: x['transaction_date'], reverse=True)
        
        # Apply filters
        if status:
            result = [r for r in result if r['status'] == status]
        if search:
            search_lower = search.lower()
            result = [r for r in result if 
                     search_lower in r['transaction_id'].lower() or 
                     search_lower in r['product_name'].lower() or
                     search_lower in r['customer_name'].lower()]
        
        total = len(result)
        
        # Paginate
        start = (page - 1) * limit
        end = start + limit
        paginated_result = result[start:end]
        
        return {
            "transactions": paginated_result,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }, 200