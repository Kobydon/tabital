# resources/customer_instalment_payment.py (Updated)
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.instalment import InstalmentPlan
from ..models.instalment_payment import InstalmentPayment
from ..models.transaction import Transaction
from ..models.notifications import Notifications
from ..extensions import db
from datetime import datetime
import json

class CustomerMakeInstalmentPaymentResource(Resource):
    @auth_required
    def post(self):
        """Customer makes a payment for an installment"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        plan_id = data.get('plan_id')
        installment_number = data.get('installment_number')
        amount = data.get('amount')
        payment_method = data.get('payment_method')
        payment_reference = data.get('payment_reference', '')
        
        if not plan_id or not installment_number or not amount:
            return {"error": "Plan ID, installment number and amount are required"}, 400
        
        # Get the instalment plan
        plan = InstalmentPlan.query.filter_by(id=plan_id, customer_id=current_customer.id).first()
        if not plan:
            return {"error": "Instalment plan not found"}, 404
        
        # Get the specific installment payment
        instalment_payment = InstalmentPayment.query.filter_by(
            plan_id=plan.id,
            installment_number=installment_number
        ).first()
        
        if not instalment_payment:
            return {"error": "Installment payment not found"}, 404
        
        if instalment_payment.status == 'paid':
            return {"error": "This installment has already been paid"}, 400
        
        # Update the installment payment
        instalment_payment.status = 'paid'
        instalment_payment.paid_date = datetime.now()
        instalment_payment.payment_method = payment_method
        instalment_payment.payment_reference = payment_reference
        instalment_payment.paid_amount = amount
        
        # Update the instalment plan
        plan.paid_installments += 1
        plan.remaining_amount -= amount
        
        if plan.paid_installments == plan.number_of_installments:
            plan.status = 'completed'
            plan.payment_status = 'completed'
            plan.completed_at = datetime.now()
        
        # Create a transaction record for this payment (customer sees this)
        transaction = Transaction(
            transaction_id=Transaction.generate_transaction_id(Transaction),
            customer_id=current_customer.id,
            merchant_id=plan.merchant_id,
            amount=amount,
            product_name=plan.plan_name,
            product_description=f"Installment {installment_number} of {plan.number_of_installments} for {plan.plan_name}",
            quantity=1,
            payment_method=payment_method,
            payment_status='completed',
            payment_reference=payment_reference,
            status='completed',
            delivery_status='completed',
            payment_plan=f"{plan.number_of_installments} Months",
            notes=f"Installment payment {installment_number}/{plan.number_of_installments}"
        )
        
        db.session.add(transaction)
        
        # Create notification for customer
        Notifications.create_notification(
            user_id=current_customer.id,
            user_role='customer',
            title='Payment Successful',
            message=f'Your payment of {amount:.2f} GHS for {plan.plan_name} has been received successfully.',
            type='payment',
            link=f'/customer/instalments/{plan.id}',
            action_text='View Details',
            extra_data={
                'plan_id': plan.id,
                'installment_number': installment_number,
                'amount': amount,
                'remaining_balance': plan.remaining_amount
            }
        )
        
        # Create notification for merchant
        Notifications.create_notification(
            user_id=plan.merchant_id,
            user_role='merchant',
            title='Payment Received',
            message=f'Customer {current_customer.full_name or current_customer.business_name} made a payment of {amount:.2f} GHS for {plan.plan_name}.',
            type='payment',
            link=f'/merchant/transactions',
            action_text='View Transaction',
            extra_data={
                'customer_id': current_customer.id,
                'plan_id': plan.id,
                'amount': amount
            }
        )
        
        # Check if plan is completed and create completion notification
        if plan.paid_installments == plan.number_of_installments:
            Notifications.create_notification(
                user_id=current_customer.id,
                user_role='customer',
                title='Instalment Plan Completed! 🎉',
                message=f'Congratulations! You have successfully completed your instalment plan for {plan.plan_name}.',
                type='system',
                link=f'/customer/instalments/{plan.id}',
                action_text='View Plan',
                extra_data={'plan_id': plan.id}
            )
            
            Notifications.create_notification(
                user_id=plan.merchant_id,
                user_role='merchant',
                title='Instalment Plan Completed',
                message=f'Customer {current_customer.full_name or current_customer.business_name} has completed their instalment plan for {plan.plan_name}.',
                type='system',
                link=f'/merchant/transactions',
                action_text='View Details',
                extra_data={'plan_id': plan.id}
            )
        
        db.session.commit()
        
        return {
            "message": "Payment successful",
            "payment_reference": transaction.transaction_id,
            "remaining_balance": plan.remaining_amount,
            "paid_installments": plan.paid_installments,
            "total_installments": plan.number_of_installments
        }, 200