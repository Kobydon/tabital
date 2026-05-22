# resources/customer_purchase.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.purchase_order import PurchaseOrder
from ..models.product import Product
from ..models.user import User
from ..models.system_settings import SystemSetting
from ..extensions import db
from datetime import datetime
import json

def safe_str(v): return v if v is not None else ""

class CustomerPurchaseResource(Resource):
    @auth_required
    def post(self):
        """Customer creates a purchase order"""
        current_customer = current_user()
        
        if current_customer.role != 'customer':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        
        product_id = data.get('product_id')
        product_name = data.get('product_name')
        product_price = data.get('product_price')
        merchant_id = data.get('merchant_id')
        number_of_installments = data.get('number_of_installments', 4)
        delivery_address = data.get('delivery_address')
        payment_schedule = data.get('payment_schedule', [])
        down_payment_amount = data.get('down_payment_amount', 0)
        installment_amount = data.get('installment_amount', 0)
        total_payable = data.get('total_payable', product_price)
        
        # Get merchant
        merchant = User.query.get(merchant_id)
        if not merchant or merchant.role != 'merchant':
            return {"error": "Merchant not found"}, 404
        
        # Get product if product_id provided
        product = None
        product_image = None
        product_description = ""
        
        if product_id:
            product = Product.query.get(product_id)
            if product:
                product_image = product.main_image
                product_description = product.description
        
        # Create purchase order
        order = PurchaseOrder(
            order_id=PurchaseOrder.generate_order_id(PurchaseOrder),
            customer_id=current_customer.id,
            merchant_id=merchant_id,
            product_id=product_id,
            product_name=product_name,
            product_description=product_description,
            product_price=product_price,
            product_image=product_image,
            quantity=data.get('quantity', 1),
            number_of_installments=number_of_installments,
            down_payment_amount=down_payment_amount,
            installment_amount=installment_amount,
            total_payable=total_payable,
       
            payment_schedule=json.dumps(payment_schedule),
            status='pending',
            delivery_address=delivery_address
        )
        
        db.session.add(order)
        db.session.commit()
        
        return {
            "message": "Order submitted for approval",
            "order_id": order.order_id,
            "status": "pending"
        }, 201


class CustomerGetOrdersResource(Resource):
    @auth_required
    def get(self):
        """Customer gets their orders"""
        current_customer = current_user()
        
        if current_customer.role != 'customer':
            return {"error": "Unauthorized"}, 403
        
        orders = PurchaseOrder.query.filter_by(customer_id=current_customer.id).order_by(PurchaseOrder.created_at.desc()).all()
        
        return [{
            "id": o.id,
            "order_id": o.order_id,
            "merchant_name": safe_str(o.merchant.business_name or o.merchant.full_name),
            "product_name": o.product_name,
            "product_price": o.product_price,
            "product_image": o.product_image,
            "quantity": o.quantity,
            "total_payable": o.total_payable,
            "down_payment_amount": o.down_payment_amount,
            "installment_amount": o.installment_amount,
            "number_of_installments": o.number_of_installments,
            # "remaining_balance": o.remaining_balance,
            "status": o.status,
            "payment_schedule": json.loads(o.payment_schedule) if o.payment_schedule else [],
            "delivery_address": o.delivery_address,
            "delivery_status": o.delivery_status,
            "created_at": o.created_at.isoformat() if o.created_at else "",
            "approved_at": o.approved_at.isoformat() if o.approved_at else "",
            "admin_notes": o.admin_notes
        } for o in orders]