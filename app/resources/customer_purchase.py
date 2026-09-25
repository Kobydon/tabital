# resources/customer_purchase.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.purchase_order import PurchaseOrder
from ..models.product import Product
from ..models.user import User
from ..models.system_settings import SystemSetting
from ..extensions import db
from ..services import plan_engine, paystack
from datetime import datetime
import json
import uuid

def safe_str(v): return v if v is not None else ""

class CustomerPurchaseResource(Resource):
    @auth_required
    def post(self):
        """Customer creates a purchase order"""
        current_customer = current_user()
        
        if current_customer.role != 'customer':
            return {"error": "Unauthorized"}, 403
        
        # KYC is enforced here, not only in the UI
        if current_customer.kyc_status != 'verified':
            return {"error": "Complete KYC verification before making a purchase"}, 403

        data = request.get_json() or {}

        # Only the product, plan, quantity and address come from the client.
        # Price, merchant and every amount are taken from the database and the plan engine.
        try:
            product_id = int(data.get('product_id'))
            quantity = int(data.get('quantity', 1))
            number_of_installments = int(data.get('number_of_installments', 4))
        except (TypeError, ValueError):
            return {"error": "product_id, quantity and number_of_installments must be numbers"}, 400
        delivery_address = (data.get('delivery_address') or '').strip()
        if not delivery_address:
            return {"error": "Delivery address is required"}, 400

        product = Product.query.get(product_id)
        if not product or product.status != 'active':
            return {"error": "Product not available"}, 404
        if quantity < 1 or quantity > (product.stock_quantity or 0):
            return {"error": "Requested quantity is not in stock"}, 400

        merchant = User.query.get(product.merchant_id)
        if not merchant or merchant.role != 'merchant' or merchant.status not in ('approved', 'active'):
            return {"error": "Merchant not available"}, 404

        try:
            plan = plan_engine.quote(product.price, quantity, number_of_installments, SystemSetting.get_value)
        except plan_engine.PlanError as e:
            return {"error": str(e)}, 400

        order = PurchaseOrder(
            order_id=PurchaseOrder.generate_order_id(PurchaseOrder),
            customer_id=current_customer.id,
            merchant_id=merchant.id,
            product_id=product.id,
            product_name=product.name,
            product_description=product.description or "",
            product_price=float(plan_engine.money(product.price)),
            product_image=product.main_image,
            quantity=quantity,
            number_of_installments=number_of_installments,
            down_payment_amount=float(plan["down_payment"]),
            installment_amount=float(plan["installment_amount"]),
            total_payable=float(plan["total_payable"]),
            payment_schedule=json.dumps(plan_engine.schedule_to_json(plan["schedule"])),
            # With Paystack, Payment 1 is collected now and the order only reaches the
            # approval queue once it's paid. Without Paystack, it goes straight to approval
            # and the admin records the down payment reference (manual fallback).
            status='awaiting_payment' if paystack.is_configured() else 'pending',
            delivery_address=delivery_address
        )

        db.session.add(order)
        db.session.commit()

        body = {
            "order_id": order.order_id,
            "id": order.id,
            "status": order.status,
            "due_now": float(plan["due_now"]),
            "total_payable": float(plan["total_payable"]),
            "payment_schedule": plan_engine.schedule_to_json(plan["schedule"])
        }

        if order.status != 'awaiting_payment':
            body["message"] = "Order submitted for approval"
            return body, 201

        try:
            checkout = start_down_payment(order, current_customer)
        except paystack.PaystackError:
            # Order is kept; the customer can retry from My Orders
            body["message"] = "Order saved, but we couldn't open the payment page. Pay the down payment from My Orders."
            body["payment_error"] = True
            return body, 201

        body.update(checkout)
        body["message"] = "Pay the down payment to send your order for approval"
        return body, 201


def start_down_payment(order, customer):
    """Start a Paystack payment for Payment 1 (down payment + delivery fee) of an order.

    The amount is taken from the order's stored, server-built schedule. Commits the intent.
    Raises paystack.PaystackError if Paystack can't be reached.
    """
    from flask import current_app
    from ..models.payment_intent import PaymentIntent
    from ..services.ledger import to_pesewas
    from .paystack_payments import _customer_email

    schedule = json.loads(order.payment_schedule)
    amount_pesewas = to_pesewas(schedule[0]["amount"])
    intent = PaymentIntent(
        reference=f"TBO-{order.id}-{uuid.uuid4().hex[:12]}",
        purpose=PaymentIntent.DOWN_PAYMENT,
        order_id=order.id,
        customer_id=customer.id,
        amount_pesewas=amount_pesewas,
        currency='GHS',
    )
    db.session.add(intent)
    db.session.flush()
    try:
        result = paystack.initialize_transaction(
            email=_customer_email(customer),
            amount_pesewas=amount_pesewas,
            reference=intent.reference,
            callback_url=current_app.config.get("PAYSTACK_CALLBACK_URL"),
            metadata={"order_id": order.order_id, "purpose": "down_payment", "customer_id": customer.id},
        )
    except paystack.PaystackError as e:
        db.session.rollback()
        current_app.logger.warning("Paystack initialize (down payment) failed: %s", e)
        raise
    db.session.commit()
    return {
        "reference": intent.reference,
        "authorization_url": result.get("authorization_url"),
        "amount": amount_pesewas / 100,
        "currency": "GHS",
    }


class CustomerPayOrderResource(Resource):
    @auth_required
    def post(self, order_id):
        """Retry paying the down payment for an order that's still awaiting payment."""
        customer = current_user()
        if customer.role != 'customer':
            return {"error": "Unauthorized"}, 403
        order = PurchaseOrder.query.filter_by(id=order_id, customer_id=customer.id).first()
        if not order:
            return {"error": "Order not found"}, 404
        if order.status != 'awaiting_payment' or order.down_payment_status == 'paid':
            return {"error": "This order has no down payment due"}, 400
        if not paystack.is_configured():
            return {"error": "Online payment isn't available right now. Please try again later."}, 503
        try:
            return start_down_payment(order, customer), 201
        except paystack.PaystackError:
            return {"error": "Could not start the payment. Please try again."}, 502


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
            "down_payment_status": o.down_payment_status or 'unpaid',
            "due_now": (json.loads(o.payment_schedule)[0]["amount"] if o.payment_schedule else o.down_payment_amount),
            "refund_status": o.refund_status,
            "payment_schedule": json.loads(o.payment_schedule) if o.payment_schedule else [],
            "delivery_address": o.delivery_address,
            "delivery_status": o.delivery_status,
            "created_at": o.created_at.isoformat() if o.created_at else "",
            "approved_at": o.approved_at.isoformat() if o.approved_at else "",
            "admin_notes": o.admin_notes
        } for o in orders]