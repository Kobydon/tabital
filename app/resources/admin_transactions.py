from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.models.instalment import InstalmentPlan
from app.models.instalment_payment import InstalmentPayment
from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, or_, and_

class AdminTransactionStatsResource(Resource):
    @auth_required
    def get(self):
        """Get transaction statistics"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Date calculations
        today = datetime.now().date()
        last_30_days = today - timedelta(days=30)
        
        # Total Transactions
        total_transactions = Transaction.query.count()
        
        # Total Volume
        total_volume = db.session.query(func.sum(Transaction.amount)).scalar() or 0
        
        # Completed Transactions
        completed_transactions = Transaction.query.filter_by(status='completed').count()
        
        # Pending Transactions
        pending_transactions = Transaction.query.filter_by(status='pending').count()
        
        # Failed Transactions
        failed_transactions = Transaction.query.filter_by(status='failed').count()
        
        # Average Transaction Value
        avg_transaction_value = (total_volume / total_transactions) if total_transactions > 0 else 0
        
        # Success Rate
        success_rate = (completed_transactions / total_transactions * 100) if total_transactions > 0 else 0
        
        # Volume growth (last 30 days vs previous)
        volume_last_30 = db.session.query(func.sum(Transaction.amount))\
            .filter(Transaction.created_at >= last_30_days).scalar() or 0
        volume_previous = total_volume - volume_last_30
        volume_growth = ((volume_last_30 - volume_previous) / volume_previous * 100) if volume_previous > 0 else 0
        
        return {
            "total_transactions": total_transactions,
            "total_volume": float(total_volume),
            "total_volume_growth": round(volume_growth, 1),
            "completed_transactions": completed_transactions,
            "pending_transactions": pending_transactions,
            "failed_transactions": failed_transactions,
            "avg_transaction_value": float(avg_transaction_value),
            "success_rate": round(success_rate, 1)
        }, 200


class AdminGetTransactionsResource(Resource):
    @auth_required
    def get(self):
        """Get all transactions with filters and pagination"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str)
        status = request.args.get('status', '', type=str)
        payment_status = request.args.get('payment_status', '', type=str)
        customer_id = request.args.get('customer_id', '', type=int)
        merchant_id = request.args.get('merchant_id', '', type=int)
        date_from = request.args.get('date_from', '', type=str)
        date_to = request.args.get('date_to', '', type=str)
        sort_by = request.args.get('sort_by', 'created_at', type=str)
        sort_order = request.args.get('sort_order', 'desc', type=str)
        
        # Build query
        query = Transaction.query
        
        # Apply search filter
        if search:
            query = query.join(User, Transaction.customer_id == User.id).filter(
                or_(
                    Transaction.transaction_id.ilike(f'%{search}%'),
                    Transaction.product_name.ilike(f'%{search}%'),
                    User.full_name.ilike(f'%{search}%'),
                    User.business_name.ilike(f'%{search}%')
                )
            )
        
        # Apply status filter
        if status:
            query = query.filter(Transaction.status == status)
        
        # Apply payment status filter
        if payment_status:
            query = query.filter(Transaction.payment_status == payment_status)
        
        # Apply customer filter
        if customer_id:
            query = query.filter(Transaction.customer_id == customer_id)
        
        # Apply merchant filter
        if merchant_id:
            query = query.filter(Transaction.merchant_id == merchant_id)
        
        # Apply date range filter
        if date_from:
            query = query.filter(Transaction.created_at >= date_from)
        if date_to:
            query = query.filter(Transaction.created_at <= date_to)
        
        # Apply sorting
        if sort_order == 'desc':
            query = query.order_by(getattr(Transaction, sort_by).desc())
        else:
            query = query.order_by(getattr(Transaction, sort_by).asc())
        
        # Pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        transactions = []
        for transaction in paginated.items:
            # Get customer and merchant info
            customer = User.query.get(transaction.customer_id)
            merchant = User.query.get(transaction.merchant_id)
            
            transactions.append({
                "id": transaction.id,
                "transaction_id": transaction.transaction_id,
                "customer_name": customer.full_name if customer else "N/A",
                "customer_phone": customer.phone if customer else "N/A",
                "merchant_name": merchant.business_name if merchant else "N/A",
                "merchant_phone": merchant.phone if merchant else "N/A",
                "amount": float(transaction.amount),
                "payout_amount": float(transaction.payout_amount) if transaction.payout_amount else float(transaction.amount * 0.9),
                "product_name": transaction.product_name,
                "product_description": transaction.product_description,
                "quantity": transaction.quantity,
                "payment_method": transaction.payment_method or "N/A",
                "payment_status": transaction.payment_status,
                "payment_reference": transaction.payment_reference or "N/A",
                "payment_plan": transaction.payment_plan or "N/A",
                "status": transaction.status,
                "delivery_status": transaction.delivery_status,
                "tracking_number": transaction.tracking_number or "N/A",
                "delivery_address": transaction.delivery_address,
                "notes": transaction.notes,
                "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
                "completion_date": transaction.completion_date.isoformat() if transaction.completion_date else None
            })
        
        return {
            "transactions": transactions,
            "total": paginated.total,
            "page": page,
            "per_page": per_page,
            "total_pages": paginated.pages if paginated.pages > 0 else 1
        }, 200


class AdminGetTransactionDetailResource(Resource):
    @auth_required
    def get(self, transaction_id):
        """Get detailed transaction information"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return {"error": "Transaction not found"}, 404
        
        customer = User.query.get(transaction.customer_id)
        merchant = User.query.get(transaction.merchant_id)
        
        # Get related instalment plan if exists
        instalment_plan = InstalmentPlan.query.filter_by(transaction_id=transaction.id).first()
        
        # Get payment schedule if instalment plan exists
        payment_schedule = []
        if instalment_plan:
            payments = InstalmentPayment.query.filter_by(plan_id=instalment_plan.id).all()
            payment_schedule = [{
                "installment_number": p.installment_number,
                "due_date": p.due_date.isoformat() if p.due_date else None,
                "amount": float(p.amount),
                "status": p.status,
                "paid_date": p.paid_date.isoformat() if p.paid_date else None
            } for p in payments]
        
        return {
            "transaction": {
                "id": transaction.id,
                "transaction_id": transaction.transaction_id,
                "amount": float(transaction.amount),
                "payout_amount": float(transaction.payout_amount) if transaction.payout_amount else float(transaction.amount * 0.9),
                "product_name": transaction.product_name,
                "product_description": transaction.product_description,
                "quantity": transaction.quantity,
                "payment_method": transaction.payment_method,
                "payment_status": transaction.payment_status,
                "payment_reference": transaction.payment_reference,
                "payment_plan": transaction.payment_plan,
                "status": transaction.status,
                "delivery_status": transaction.delivery_status,
                "tracking_number": transaction.tracking_number,
                "delivery_address": transaction.delivery_address,
                "notes": transaction.notes,
                "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
                "completion_date": transaction.completion_date.isoformat() if transaction.completion_date else None
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
                "phone": merchant.phone if merchant else "N/A",
                "email": merchant.business_email or merchant.email if merchant else "N/A"
            },
            "instalment_plan": {
                "plan_id": instalment_plan.plan_id if instalment_plan else None,
                "total_amount": float(instalment_plan.total_amount) if instalment_plan else 0,
                "remaining_amount": float(instalment_plan.remaining_amount) if instalment_plan else 0,
                "number_of_installments": instalment_plan.number_of_installments if instalment_plan else 0,
                "status": instalment_plan.status if instalment_plan else None
            } if instalment_plan else None,
            "payment_schedule": payment_schedule
        }, 200


class AdminUpdateTransactionStatusResource(Resource):
    @auth_required
    def put(self, transaction_id):
        """Update transaction status"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        new_status = data.get('status')
        reason = data.get('reason', '')
        
        if new_status not in ['pending', 'approved', 'completed', 'failed', 'cancelled']:
            return {"error": "Invalid status"}, 400
        
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return {"error": "Transaction not found"}, 404
        
        old_status = transaction.status
        transaction.status = new_status
        
        if new_status == 'completed':
            transaction.completion_date = datetime.now()
        
        db.session.commit()
        
        return {
            "message": f"Transaction status updated from {old_status} to {new_status}",
            "transaction_id": transaction.transaction_id,
            "status": new_status
        }, 200


class AdminUpdateDeliveryStatusResource(Resource):
    @auth_required
    def put(self, transaction_id):
        """Update delivery status and tracking number"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        delivery_status = data.get('delivery_status')
        tracking_number = data.get('tracking_number', '')
        
        if delivery_status not in ['pending', 'processing', 'shipped', 'delivered', 'cancelled']:
            return {"error": "Invalid delivery status"}, 400
        
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return {"error": "Transaction not found"}, 404
        
        transaction.delivery_status = delivery_status
        if tracking_number:
            transaction.tracking_number = tracking_number
        
        db.session.commit()
        
        return {
            "message": f"Delivery status updated to {delivery_status}",
            "transaction_id": transaction.transaction_id,
            "delivery_status": delivery_status,
            "tracking_number": transaction.tracking_number
        }, 200


class AdminRefundTransactionResource(Resource):
    @auth_required
    def post(self, transaction_id):
        """Process refund for transaction"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        refund_amount = data.get('refund_amount')
        reason = data.get('reason', '')
        
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return {"error": "Transaction not found"}, 404
        
        if transaction.status != 'completed':
            return {"error": "Only completed transactions can be refunded"}, 400
        
        if not refund_amount or refund_amount <= 0:
            return {"error": "Invalid refund amount"}, 400
        
        if refund_amount > transaction.amount:
            return {"error": "Refund amount cannot exceed transaction amount"}, 400
        
        # Mark transaction as refunded
        transaction.status = 'refunded'
        
        # Create refund record (you can create a Refund model)
        
        db.session.commit()
        
        return {
            "message": f"Refund of {refund_amount} processed successfully",
            "transaction_id": transaction.transaction_id,
            "refund_amount": refund_amount,
            "status": "refunded"
        }, 200


class AdminExportTransactionsResource(Resource):
    @auth_required
    def get(self):
        """Export transactions to CSV"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Get query parameters
        search = request.args.get('search', '', type=str)
        status = request.args.get('status', '', type=str)
        date_from = request.args.get('date_from', '', type=str)
        date_to = request.args.get('date_to', '', type=str)
        
        # Build query
        query = Transaction.query
        
        if search:
            query = query.join(User, Transaction.customer_id == User.id).filter(
                or_(
                    Transaction.transaction_id.ilike(f'%{search}%'),
                    Transaction.product_name.ilike(f'%{search}%'),
                    User.full_name.ilike(f'%{search}%')
                )
            )
        
        if status:
            query = query.filter(Transaction.status == status)
        
        if date_from:
            query = query.filter(Transaction.created_at >= date_from)
        if date_to:
            query = query.filter(Transaction.created_at <= date_to)
        
        transactions = query.all()
        
        # Create CSV content
        import csv
        from io import StringIO
        from flask import make_response
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Transaction ID', 'Customer', 'Merchant', 'Amount', 'Product',
            'Payment Method', 'Status', 'Delivery Status', 'Created At'
        ])
        
        # Write data
        for transaction in transactions:
            customer = User.query.get(transaction.customer_id)
            merchant = User.query.get(transaction.merchant_id)
            
            writer.writerow([
                transaction.transaction_id,
                customer.full_name if customer else "N/A",
                merchant.business_name if merchant else "N/A",
                transaction.amount,
                transaction.product_name,
                transaction.payment_method or "N/A",
                transaction.status,
                transaction.delivery_status,
                transaction.created_at.strftime("%Y-%m-%d %H:%M:%S") if transaction.created_at else ""
            ])
        
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=transactions_{datetime.now().strftime("%Y%m%d")}.csv'
        return response