# resources/admin_orders.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.purchase_order import PurchaseOrder
from ..models.user import User
from ..models.transaction import Transaction
from ..extensions import db
from datetime import datetime
import json

def safe_str(v): return v if v is not None else ""
def safe_float(v): return v if v is not None else 0.0

class AdminGetOrdersResource(Resource):
    @auth_required
    def get(self):
        """Get all purchase orders for admin"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        status = request.args.get('status', '')
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        
        query = PurchaseOrder.query
        
        if status:
            query = query.filter(PurchaseOrder.status == status)
        
        total = query.count()
        orders = query.order_by(PurchaseOrder.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        
        return {
            "orders": [{
                "id": o.id,
                "order_id": o.order_id,
                "customer_name": safe_str(o.customer.full_name or o.customer.business_name),
                "customer_phone": safe_str(o.customer.phone),
                "merchant_name": safe_str(o.merchant.business_name or o.merchant.full_name),
                "product_name": o.product_name,
                "product_price": o.product_price,
                "quantity": o.quantity,
                "total_payable": o.total_payable,
                "down_payment_amount": o.down_payment_amount,
                "installment_amount": o.installment_amount,
                "number_of_installments": o.number_of_installments,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else "",
                "delivery_address": o.delivery_address
            } for o in orders],
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }


# class AdminApproveOrderResource(Resource):
#     @auth_required
#     def put(self, order_id):
#         """Admin approves an order"""
#         current_admin = current_user()
        
#         if current_admin.role != 'admin':
#             return {"error": "Unauthorized"}, 403
        
#         order = PurchaseOrder.query.get(order_id)
#         if not order:
#             return {"error": "Order not found"}, 404
        
#         if order.status != 'pending':
#             return {"error": f"Order already {order.status}"}, 400
        
#         data = request.get_json()
        
#         order.status = 'approved'
#         order.approved_at = datetime.now()
#         order.admin_notes = data.get('admin_notes', '')
        
#         # Create transaction for the merchant (full payment to merchant)
#         transaction = Transaction(
#             transaction_id=Transaction.generate_transaction_id(Transaction),
#             customer_id=order.customer_id,
#             merchant_id=order.merchant_id,
#             amount=order.total_payable,
#             product_name=order.product_name,
#             product_description=order.product_description,
#             quantity=order.quantity,
#             payment_plan=f"{order.number_of_installments} Months",
#             status='completed',
#             payment_status='processing',
#             delivery_address=order.delivery_address
#         )
        
#         db.session.add(transaction)
#         db.session.commit()
        
#         return {
#             "message": "Order approved successfully",
#             "transaction_id": transaction.transaction_id
#         }, 200


class AdminRejectOrderResource(Resource):
    @auth_required
    def put(self, order_id):
        """Admin rejects an order"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        order = PurchaseOrder.query.get(order_id)
        if not order:
            return {"error": "Order not found"}, 404
        
        if order.status != 'pending':
            return {"error": f"Order already {order.status}"}, 400
        
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        order.status = 'rejected'
        order.rejected_at = datetime.now()
        order.admin_notes = reason
        
        db.session.commit()
        
        return {"message": f"Order rejected: {reason}"}, 200