# resources/merchant_orders.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.purchase_order import PurchaseOrder
from ..models.transaction import Transaction
from ..extensions import db
from datetime import datetime

def safe_str(v): return v if v is not None else ""
def safe_float(v): return v if v is not None else 0.0

class MerchantGetOrdersResource(Resource):
    @auth_required
    def get(self):
        """Get orders for merchant"""
        current_merchant = current_user()
        
        if current_merchant.role != 'merchant':
            return {"error": "Unauthorized"}, 403
        
        status = request.args.get('status', '')
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        
        query = PurchaseOrder.query.filter_by(merchant_id=current_merchant.id)
        
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
                "product_name": o.product_name,
                "product_price": o.product_price,
                "quantity": o.quantity,
                "total_payable": o.total_payable,
                "down_payment_amount": o.down_payment_amount,
                "installment_amount": o.installment_amount,
                "number_of_installments": o.number_of_installments,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else "",
                "delivery_address": o.delivery_address,
                "delivery_status": o.delivery_status
            } for o in orders],
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }


class MerchantUpdateDeliveryStatusResource(Resource):
    @auth_required
    def put(self, order_id):
        """Merchant updates delivery status of approved order"""
        current_merchant = current_user()
        
        if current_merchant.role != 'merchant':
            return {"error": "Unauthorized"}, 403
        
        order = PurchaseOrder.query.filter_by(id=order_id, merchant_id=current_merchant.id).first()
        
        if not order:
            return {"error": "Order not found"}, 404
        
        if order.status != 'approved':
            return {"error": "Only approved orders can be updated"}, 400
        
        data = request.get_json()
        delivery_status = data.get('delivery_status')
        
        if delivery_status:
            order.delivery_status = delivery_status
            
            if delivery_status == 'delivered':
                order.status = 'completed'
                order.completed_at = datetime.now()
                
                # Update transaction status
                transaction = Transaction.query.filter_by(
                    customer_id=order.customer_id,
                    merchant_id=order.merchant_id,
                    product_name=order.product_name
                ).first()
                
                if transaction:
                    transaction.status = 'completed'
                    transaction.payment_status = 'completed'
                    transaction.completion_date = datetime.now()
        
        db.session.commit()
        
        return {"message": f"Delivery status updated to {delivery_status}"}, 200