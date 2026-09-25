"""Paystack checkout for instalments (CLAUDE.md §13.1 D11).

Flow: customer asks to pay -> server fixes the amount and starts a Paystack transaction ->
customer pays on Paystack's page -> Paystack redirects back and also sends a signed webhook ->
the server verifies the transaction with Paystack's API and only then marks the instalment paid.
"""
import json
import uuid

from flask import current_app, request
from flask_praetorian import auth_required, current_user
from flask_restful import Resource

from ..extensions import db
from ..models.instalment import InstalmentPlan
from ..models.payment_intent import PaymentIntent
from ..services import paystack
from ..services.ledger import to_pesewas
from ..services.payments import apply_verified_transaction, next_payable_instalment


def _customer_email(user):
    # Paystack requires an email; customers without one get an internal placeholder
    return user.business_email or user.email or f"{user.phone}@customers.tabitalpay.com"


def _new_reference(plan, payment):
    return f"TBP-{plan.id}-{payment.installment_number}-{uuid.uuid4().hex[:12]}"


def _intent_view(intent, outcome=None):
    return {
        "reference": intent.reference,
        "purpose": intent.purpose,
        "status": intent.status,
        "outcome": outcome,
        "amount": intent.amount_pesewas / 100,
        "currency": intent.currency,
        "channel": intent.channel,
        "plan_id": intent.plan_id,
        "order_id": intent.order.order_id if intent.order else None,
        "order_status": intent.order.status if intent.order else None,
        "installment_number": intent.payment.installment_number if intent.payment else 1,
    }


class CustomerPaymentConfigResource(Resource):
    @auth_required
    def get(self):
        return {"paystack_enabled": paystack.is_configured()}, 200


class CustomerPaystackInitializeResource(Resource):
    @auth_required
    def post(self):
        customer = current_user()
        if customer.role != 'customer':
            return {"error": "Unauthorized"}, 403
        if not paystack.is_configured():
            return {"error": "Online payment isn't available right now. Please try again later."}, 503

        data = request.get_json() or {}
        plan = InstalmentPlan.query.filter_by(id=data.get('plan_id'), customer_id=customer.id).first()
        if not plan:
            return {"error": "Instalment plan not found"}, 404

        payment = next_payable_instalment(plan)
        if not payment:
            return {"error": "No payments due on this plan"}, 400

        # The server decides the amount: the instalment plus any unpaid late fee
        amount_pesewas = to_pesewas(payment.get_total_due())
        intent = PaymentIntent(
            reference=_new_reference(plan, payment),
            purpose=PaymentIntent.INSTALMENT,
            plan_id=plan.id,
            payment_id=payment.id,
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
                metadata={
                    "plan_id": plan.id,
                    "installment_number": payment.installment_number,
                    "customer_id": customer.id,
                },
            )
        except paystack.PaystackError as e:
            db.session.rollback()
            current_app.logger.warning("Paystack initialize failed: %s", e)
            return {"error": "Could not start the payment. Please try again."}, 502

        db.session.commit()
        return {
            "reference": intent.reference,
            "authorization_url": result.get("authorization_url"),
            "access_code": result.get("access_code"),
            "amount": amount_pesewas / 100,
            "currency": "GHS",
            "installment_number": payment.installment_number,
        }, 201


class CustomerPaystackVerifyResource(Resource):
    @auth_required
    def get(self, reference):
        """Called by the payment-callback page after Paystack redirects the customer back."""
        customer = current_user()
        intent = PaymentIntent.query.filter_by(reference=reference).with_for_update().first()
        if not intent or (customer.role != 'admin' and intent.customer_id != customer.id):
            return {"error": "Payment not found"}, 404

        if intent.status == PaymentIntent.SUCCESS:
            return _intent_view(intent, 'already_applied'), 200

        try:
            data = paystack.verify_transaction(reference)
        except paystack.PaystackError as e:
            db.session.rollback()
            current_app.logger.warning("Paystack verify failed for %s: %s", reference, e)
            return {"error": "Could not confirm the payment yet. We'll update it automatically."}, 502

        outcome = apply_verified_transaction(intent, data)
        db.session.commit()
        return _intent_view(intent, outcome), 200


class PaystackWebhookResource(Resource):
    def post(self):
        """Paystack server-to-server notifications. Public, but every call must be signed."""
        raw = request.get_data()
        if not paystack.valid_webhook_signature(raw, request.headers.get('x-paystack-signature', '')):
            return {"error": "Invalid signature"}, 401

        try:
            event = json.loads(raw or b'{}')
        except ValueError:
            return {"error": "Invalid body"}, 400

        if event.get('event') != 'charge.success':
            return {"status": "ignored"}, 200

        reference = (event.get('data') or {}).get('reference')
        intent = PaymentIntent.query.filter_by(reference=reference).with_for_update().first() if reference else None
        if not intent:
            # Not one of ours (or not yet committed); acknowledge so Paystack stops retrying
            current_app.logger.warning("Paystack webhook for unknown reference %s", reference)
            return {"status": "unknown_reference"}, 200

        # Don't trust the webhook body alone: confirm with Paystack's API
        try:
            data = paystack.verify_transaction(reference)
        except paystack.PaystackError as e:
            db.session.rollback()
            current_app.logger.warning("Paystack verify (webhook) failed for %s: %s", reference, e)
            return {"error": "verify failed"}, 502   # non-2xx makes Paystack retry later

        outcome = apply_verified_transaction(intent, data)
        db.session.commit()
        return {"status": outcome}, 200
