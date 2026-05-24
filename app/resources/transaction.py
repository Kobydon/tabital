from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.user import User
from ..models.transaction import Transaction
from ..extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, or_

def safe_str(value):
    return value if value is not None else ""

def safe_float(value):
    return value if value is not None else 0.0

def safe_int(value):
    return value if value is not None else 0


class GetTransactionsResource(Resource):
    @auth_required
    def get(self):
        """Get all transactions with filters"""
        current_user_obj = current_user()
        
        # Get query parameters
        status = request.args.get('status', '').strip()
        payment_status = request.args.get('payment_status', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        search = request.args.get('search', '').strip()
        transaction_type = request.args.get('type', '').strip()  # sent, received, all
        
        # Base query based on user role
        if current_user_obj.role == 'admin':
            query = Transaction.query
        elif current_user_obj.role == 'customer':
            query = Transaction.query.filter_by(customer_id=current_user_obj.id)
            if transaction_type == 'sent':
                query = Transaction.query.filter_by(customer_id=current_user_obj.id)
            elif transaction_type == 'received':
                query = Transaction.query.filter_by(merchant_id=current_user_obj.id)
        elif current_user_obj.role == 'merchant':
            query = Transaction.query.filter_by(merchant_id=current_user_obj.id)
        else:
            return {"error": "Unauthorized"}, 403
        
        # Apply filters
        if status:
            query = query.filter(Transaction.status == status)
        if payment_status:
            query = query.filter(Transaction.payment_status == payment_status)
        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)
        if search:
            query = query.filter(
                db.or_(
                    Transaction.transaction_id.ilike(f'%{search}%'),
                    Transaction.product_name.ilike(f'%{search}%'),
                    Transaction.payment_reference.ilike(f'%{search}%')
                )
            )
        
        transactions = query.order_by(Transaction.created_at.desc()).all()
        
        return [
            {
                "id": t.id,
                "transaction_id": safe_str(t.transaction_id),
                "customer_id": t.customer_id,
                "customer_name": safe_str(t.customer.full_name or t.customer.business_name or t.customer.phone),
                "customer_phone": safe_str(t.customer.phone),
                "merchant_id": t.merchant_id,
                "merchant_name": safe_str(t.merchant.business_name or t.merchant.full_name or t.merchant.phone),
                "merchant_phone": safe_str(t.merchant.phone),
                "amount": safe_float(t.amount),
                "product_name": safe_str(t.product_name),
                "product_description": safe_str(t.product_description),
                "quantity": safe_int(t.quantity),
                "payment_method": safe_str(t.payment_method),
                "payment_status": safe_str(t.payment_status),
                "payment_reference": safe_str(t.payment_reference),
                "status": safe_str(t.status),
                "transaction_date": t.transaction_date.isoformat() if t.transaction_date else "",
                "completion_date": t.completion_date.isoformat() if t.completion_date else "",
                "delivery_address": safe_str(t.delivery_address),
                "delivery_status": safe_str(t.delivery_status),
                "tracking_number": safe_str(t.tracking_number),
                "notes": safe_str(t.notes),
                "created_at": t.created_at.isoformat() if t.created_at else "",
                # Payout information
                "commission_rate": safe_float(getattr(t, 'commission_rate', 10)),
                "commission_amount": safe_float(getattr(t, 'commission_amount', 0)),
                "payout_amount": safe_float(getattr(t, 'payout_amount', 0)),
                "is_instalment": getattr(t, 'payment_plan', None) is not None
            } for t in transactions
        ]


class CreateTransactionResource(Resource):
    @auth_required
    def post(self):
        """Create a new transaction"""
        current_user_obj = current_user()
        
        if current_user_obj.role != "customer":
            return {"error": "Only customers can create transactions"}, 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['merchant_id', 'amount', 'product_name']
        for field in required_fields:
            if field not in data:
                return {"error": f"{field} is required"}, 400
        
        # Check if merchant exists
        merchant = User.query.get(data['merchant_id'])
        if not merchant or merchant.role != 'merchant':
            return {"error": "Merchant not found"}, 404
        
        # Calculate payout amounts (10% commission)
        commission_rate = 10
        commission_amount = data['amount'] * (commission_rate / 100)
        payout_amount = data['amount'] - commission_amount
        
        # Create transaction
        transaction = Transaction(
            customer_id=current_user_obj.id,
            merchant_id=data['merchant_id'],
            amount=data['amount'],
            product_name=data['product_name'],
            product_description=data.get('product_description', ''),
            quantity=data.get('quantity', 1),
            payment_method=data.get('payment_method', ''),
            payment_reference=data.get('payment_reference', ''),
            delivery_address=data.get('delivery_address', ''),
            notes=data.get('notes', ''),
            status='pending',
            payment_status='pending',
            delivery_status='pending',
            commission_rate=commission_rate,
            commission_amount=commission_amount,
            payout_amount=payout_amount
        )
        
        transaction.transaction_id = transaction.generate_transaction_id()
        
        db.session.add(transaction)
        db.session.commit()
        
        return {
            "message": "Transaction created successfully",
            "transaction_id": transaction.transaction_id,
            "id": transaction.id,
            "amount": transaction.amount,
            "commission_rate": commission_rate,
            "commission_amount": commission_amount,
            "payout_amount": payout_amount
        }, 201


class UpdateTransactionStatusResource(Resource):
    @auth_required
    def put(self, transaction_id):
        """Update transaction status"""
        current_user_obj = current_user()
        
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return {"error": "Transaction not found"}, 404
        
        # Check permissions
        if current_user_obj.role == 'admin':
            pass
        elif current_user_obj.role == 'merchant' and transaction.merchant_id != current_user_obj.id:
            return {"error": "Unauthorized"}, 403
        elif current_user_obj.role == 'customer' and transaction.customer_id != current_user_obj.id:
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        
        # Allowed fields to update
        allowed_fields = ['status', 'payment_status', 'delivery_status', 'tracking_number', 'payment_reference', 'notes']
        
        for field in allowed_fields:
            if field in data:
                setattr(transaction, field, data[field])
        
        if data.get('status') == 'completed' and not transaction.completion_date:
            transaction.completion_date = datetime.utcnow()
        
        db.session.commit()
        
        return {
            "message": "Transaction updated successfully",
            "transaction_id": transaction.transaction_id,
            "amount": transaction.amount,
            "commission_rate": getattr(transaction, 'commission_rate', 10),
            "commission_amount": getattr(transaction, 'commission_amount', 0),
            "payout_amount": getattr(transaction, 'payout_amount', 0)
        }, 200


class GetTransactionStatsResource(Resource):
    @auth_required
    def get(self):
        """Get transaction statistics"""
        current_user_obj = current_user()
        
        # Base query based on role
        if current_user_obj.role == 'admin':
            query = Transaction.query
        elif current_user_obj.role == 'customer':
            query = Transaction.query.filter_by(customer_id=current_user_obj.id)
        elif current_user_obj.role == 'merchant':
            query = Transaction.query.filter_by(merchant_id=current_user_obj.id)
        else:
            return {"error": "Unauthorized"}, 403
        
        # Calculate statistics
        total_transactions = query.count()
        total_amount = db.session.query(db.func.sum(Transaction.amount)).filter(Transaction.id.in_([t.id for t in query.all()])).scalar() or 0
        total_payout = db.session.query(db.func.sum(Transaction.payout_amount)).filter(Transaction.id.in_([t.id for t in query.all()])).scalar() or 0
        total_commission = db.session.query(db.func.sum(Transaction.commission_amount)).filter(Transaction.id.in_([t.id for t in query.all()])).scalar() or 0
        
        pending = query.filter_by(status='pending').count()
        completed = query.filter_by(status='completed').count()
        cancelled = query.filter_by(status='cancelled').count()
        
        # Monthly breakdown
        from sqlalchemy import extract
        monthly_stats = db.session.query(
            extract('year', Transaction.transaction_date).label('year'),
            extract('month', Transaction.transaction_date).label('month'),
            db.func.count(Transaction.id).label('count'),
            db.func.sum(Transaction.amount).label('amount'),
            db.func.sum(Transaction.payout_amount).label('payout')
        ).filter(Transaction.id.in_([t.id for t in query.all()])).group_by('year', 'month').order_by('year', 'month').limit(6).all()
        
        return {
            "total_transactions": total_transactions,
            "total_amount": float(total_amount),
            "total_payout": float(total_payout),
            "total_commission": float(total_commission),
            "pending": pending,
            "completed": completed,
            "cancelled": cancelled,
            "monthly_stats": [
                {
                    "month": f"{int(m[1])}/{int(m[0])}",
                    "count": m[2],
                    "amount": float(m[3]),
                    "payout": float(m[4]) if m[4] else 0
                } for m in monthly_stats
            ]
        }, 200


class DeleteTransactionResource(Resource):
    @auth_required
    def delete(self, transaction_id):
        """Delete a transaction (admin only)"""
        current_user_obj = current_user()
        
        if current_user_obj.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return {"error": "Transaction not found"}, 404
        
        db.session.delete(transaction)
        db.session.commit()
        
        return {"message": "Transaction deleted successfully"}, 200


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
        transaction_type = request.args.get('type', '').strip()
        limit = request.args.get('limit', 50, type=int)
        page = request.args.get('page', 1, type=int)
        
        # Base query
        query = Transaction.query.filter_by(merchant_id=current_merchant.id)
        
        # Apply filters
        if status:
            query = query.filter(Transaction.status == status)
        
        if payment_status:
            query = query.filter(Transaction.payment_status == payment_status)
        
        if transaction_type == 'sale':
            query = query.filter(Transaction.payment_plan.is_(None))
        elif transaction_type == 'instalment':
            query = query.filter(Transaction.payment_plan.isnot(None))
        
        if search:
            query = query.filter(
                or_(
                    Transaction.transaction_id.ilike(f'%{search}%'),
                    Transaction.product_name.ilike(f'%{search}%'),
                    Transaction.customer.has(User.full_name.ilike(f'%{search}%')),
                    Transaction.customer.has(User.phone.ilike(f'%{search}%'))
                )
            )
        
        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)
        
        # Pagination
        total = query.count()
        transactions = query.order_by(Transaction.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        
        # Calculate total payout for filtered transactions
        total_payout = sum(getattr(t, 'payout_amount', 0) or 0 for t in transactions)
        total_commission = sum(getattr(t, 'commission_amount', 0) or 0 for t in transactions)
        
        return {
            "transactions": [{
                "id": t.id,
                "transaction_id": safe_str(t.transaction_id),
                "customer_name": safe_str(t.customer.full_name or t.customer.business_name or t.customer.phone),
                "customer_phone": safe_str(t.customer.phone),
                "customer_email": safe_str(t.customer.business_email or t.customer.email),
                "amount": safe_float(t.amount),
                "product_name": safe_str(t.product_name),
                "product_description": safe_str(t.product_description),
                "quantity": safe_int(t.quantity),
                "payment_method": safe_str(t.payment_method),
                "payment_status": safe_str(t.payment_status),
                "payment_reference": safe_str(t.payment_reference),
                "payment_plan": safe_str(t.payment_plan),
                "status": safe_str(t.status),
                "transaction_date": t.transaction_date.isoformat() if t.transaction_date else "",
                "completion_date": t.completion_date.isoformat() if t.completion_date else "",
                "delivery_status": safe_str(t.delivery_status),
                "created_at": t.created_at.isoformat() if t.created_at else "",
                "is_instalment": t.payment_plan is not None and t.payment_plan != '',
                # Payout information for merchants
                "commission_rate": safe_float(getattr(t, 'commission_rate', 10)),
                "commission_amount": safe_float(getattr(t, 'commission_amount', 0)),
                "payout_amount": safe_float(getattr(t, 'payout_amount', 0))
            } for t in transactions],
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
            "total_payout": float(total_payout),
            "total_commission": float(total_commission)
        }
class MerchantGetTransactionStatsResource(Resource):
    @auth_required
    def get(self):
        """Get transaction statistics for the merchant including payout info"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        # Date ranges
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Get all completed transactions for this merchant
        all_completed_transactions = Transaction.query.filter(
            Transaction.merchant_id == current_merchant.id,
            Transaction.status == 'completed'
        ).all()
        
        # Calculate total payout (all time)
        total_payout = sum(getattr(t, 'payout_amount', t.amount * 0.9) for t in all_completed_transactions)
        total_commission = sum(getattr(t, 'commission_amount', t.amount * 0.1) for t in all_completed_transactions)
        
        # Calculate pending payout (completed but not paid)
        pending_transactions = [t for t in all_completed_transactions if getattr(t, 'payment_status', 'pending') == 'pending']
        pending_payout = sum(getattr(t, 'payout_amount', t.amount * 0.9) for t in pending_transactions)
        
        # Calculate paid payout
        paid_transactions = [t for t in all_completed_transactions if getattr(t, 'payment_status', '') == 'paid']
        paid_payout = sum(getattr(t, 'payout_amount', t.amount * 0.9) for t in paid_transactions)
        
        # This month's payout
        this_month_transactions = [t for t in all_completed_transactions if t.completion_date and t.completion_date >= month_ago]
        this_month_payout = sum(getattr(t, 'payout_amount', t.amount * 0.9) for t in this_month_transactions)
        
        # Last month's payout (for growth calculation)
        last_month_start = (month_ago - timedelta(days=30)).replace(day=1)
        last_month_end = month_ago - timedelta(days=1)
        last_month_transactions = [t for t in all_completed_transactions if t.completion_date and last_month_start <= t.completion_date <= last_month_end]
        last_month_payout = sum(getattr(t, 'payout_amount', t.amount * 0.9) for t in last_month_transactions)
        
        # Calculate payout growth
        if last_month_payout > 0:
            payout_growth = ((this_month_payout - last_month_payout) / last_month_payout) * 100
        else:
            payout_growth = 100 if this_month_payout > 0 else 0
        
        # Return the format the frontend expects
        return {
            "total_payout": float(total_payout),
            "total_commission": float(total_commission),
            "pending_payout": float(pending_payout),
            "paid_payout": float(paid_payout),
            "this_month_payout": float(this_month_payout),
            "last_month_payout": float(last_month_payout),
            "payout_growth": float(payout_growth)
        }, 200

class MerchantUpdateTransactionStatusResource(Resource):
    @auth_required
    def put(self, transaction_id):
        """Update transaction status"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        transaction = Transaction.query.get(transaction_id)
        
        if not transaction or transaction.merchant_id != current_merchant.id:
            return {"error": "Transaction not found"}, 404
        
        data = request.get_json()
        
        allowed_fields = ['status', 'payment_status', 'delivery_status', 'tracking_number', 'notes']
        
        for field in allowed_fields:
            if field in data:
                setattr(transaction, field, data[field])
        
        if data.get('status') == 'completed' and not transaction.completion_date:
            transaction.completion_date = datetime.utcnow()
        
        db.session.commit()
        
        return {
            "message": "Transaction updated successfully",
            "transaction_id": transaction.transaction_id,
            "amount": transaction.amount,
            "commission_rate": getattr(transaction, 'commission_rate', 10),
            "commission_amount": getattr(transaction, 'commission_amount', 0),
            "payout_amount": getattr(transaction, 'payout_amount', 0)
        }, 200


class MerchantUpdateTransactionResource(Resource):
    @auth_required
    def put(self, transaction_id):
        """Update transaction details"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        transaction = Transaction.query.get(transaction_id)
        
        if not transaction or transaction.merchant_id != current_merchant.id:
            return {"error": "Transaction not found"}, 404
        
        data = request.get_json()
        
        allowed_fields = ['delivery_address', 'tracking_number', 'notes', 'payment_reference']
        
        for field in allowed_fields:
            if field in data:
                setattr(transaction, field, data[field])
        
        db.session.commit()
        
        return {
            "message": "Transaction updated successfully",
            "transaction_id": transaction.transaction_id,
            "payout_amount": getattr(transaction, 'payout_amount', 0)
        }, 200


class MerchantRefundTransactionResource(Resource):
    @auth_required
    def post(self, transaction_id):
        """Process a refund for a transaction"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        transaction = Transaction.query.get(transaction_id)
        
        if not transaction or transaction.merchant_id != current_merchant.id:
            return {"error": "Transaction not found"}, 404
        
        if transaction.status != 'completed':
            return {"error": "Only completed transactions can be refunded"}, 400
        
        data = request.get_json()
        refund_amount = data.get('refund_amount', transaction.amount)
        reason = data.get('reason', '')
        
        # Calculate refund impact on payout
        refund_payout_impact = refund_amount * (1 - (getattr(transaction, 'commission_rate', 10) / 100))
        
        transaction.status = 'refunded'
        transaction.payment_status = 'refunded'
        transaction.notes = f"Refunded: {reason}" if reason else transaction.notes
        
        db.session.commit()
        
        return {
            "message": f"Refund of {refund_amount} processed successfully",
            "refund_amount": refund_amount,
            "refund_payout_impact": refund_payout_impact,
            "transaction_id": transaction.transaction_id
        }, 200


class MerchantExportTransactionsResource(Resource):
    @auth_required
    def get(self):
        """Export transactions to CSV with payout info"""
        from flask import Response
        import csv
        from io import StringIO
        
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        
        query = Transaction.query.filter_by(merchant_id=current_merchant.id)
        
        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)
        
        transactions = query.order_by(Transaction.created_at.desc()).all()
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers with payout columns
        writer.writerow([
            'Transaction ID', 'Date', 'Customer Name', 'Customer Phone', 
            'Product', 'Quantity', 'Amount', 'Commission Rate (%)', 
            'Commission Amount', 'Payout Amount', 'Status', 'Payment Status',
            'Payment Method', 'Delivery Status'
        ])
        
        # Write data
        for t in transactions:
            writer.writerow([
                t.transaction_id,
                t.transaction_date.strftime('%Y-%m-%d %H:%M') if t.transaction_date else '',
                t.customer.full_name or t.customer.business_name or t.customer.phone,
                t.customer.phone,
                t.product_name,
                t.quantity,
                t.amount,
                getattr(t, 'commission_rate', 10),
                getattr(t, 'commission_amount', 0),
                getattr(t, 'payout_amount', 0),
                t.status,
                t.payment_status,
                t.payment_method,
                t.delivery_status
            ])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=transactions_{datetime.now().strftime("%Y%m%d")}.csv'
            }


    
        )


# Add these to your Flask API resources

class MerchantPayoutStatsResource(Resource):
    @auth_required
    def get(self):
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        # Calculate payout stats
        from ..models.transaction import Transaction
        
        # Total payout (all time)
        total_payout = db.session.query(
            func.sum(Transaction.payout_amount)
        ).filter_by(merchant_id=current_merchant.id, status='completed').scalar() or 0
        
        total_commission = db.session.query(
            func.sum(Transaction.commission_amount)
        ).filter_by(merchant_id=current_merchant.id, status='completed').scalar() or 0
        
        # Pending payout (completed but not paid)
        pending_payout = db.session.query(
            func.sum(Transaction.payout_amount)
        ).filter_by(merchant_id=current_merchant.id, status='completed', payment_status='pending').scalar() or 0
        
        # Paid payout
        paid_payout = db.session.query(
            func.sum(Transaction.payout_amount)
        ).filter_by(merchant_id=current_merchant.id, status='completed', payment_status='paid').scalar() or 0
        
        # This month's payout
        today = datetime.now()
        first_day_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        this_month_payout = db.session.query(
            func.sum(Transaction.payout_amount)
        ).filter(
            Transaction.merchant_id == current_merchant.id,
            Transaction.status == 'completed',
            Transaction.completion_date >= first_day_of_month
        ).scalar() or 0
        
        # Available for withdrawal (minimum payout is 100)
        min_payout = 100
        available_for_withdrawal = pending_payout if pending_payout >= min_payout else 0
        
        # Next payout date (next settlement date)
        next_payout_date = (today + timedelta(days=7)).strftime('%Y-%m-%d')
        
        return {
            "total_payout": float(total_payout),
            "total_commission": float(total_commission),
            "pending_payout": float(pending_payout),
            "paid_payout": float(paid_payout),
            "this_month_payout": float(this_month_payout),
            "last_month_payout": 0,
            "payout_growth": 0,
            "available_for_withdrawal": float(available_for_withdrawal),
            "next_payout_date": next_payout_date,
            "payout_history": []
        }, 200


class MerchantRecentPayoutsResource(Resource):
    @auth_required
    def get(self):
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        limit = request.args.get('limit', 5, type=int)
        
        # Get recent completed transactions
        transactions = Transaction.query.filter_by(
            merchant_id=current_merchant.id,
            status='completed'
        ).order_by(Transaction.completion_date.desc()).limit(limit).all()
        
        result = []
        for t in transactions:
            result.append({
                "id": t.id,
                "payout_id": t.transaction_id,
                "amount": float(t.amount),
                "payout_amount": float(getattr(t, 'payout_amount', t.amount * 0.9)),
                "commission_amount": float(getattr(t, 'commission_amount', t.amount * 0.1)),
                "status": t.payment_status or 'pending',
                "date": t.completion_date.isoformat() if t.completion_date else t.created_at.isoformat(),
                "product_name": t.product_name
            })
        
        return result, 200