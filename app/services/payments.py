"""Applying confirmed money to instalments. Shared by admin confirmation and Paystack."""
from datetime import datetime

from ..models.instalment import InstalmentPlan
from . import ledger

# Instalments a customer can still pay
PAYABLE_STATUSES = ('pending', 'overdue', 'pending_verification')


def next_payable_instalment(plan):
    from ..models.instalment_payment import InstalmentPayment
    return InstalmentPayment.query.filter(
        InstalmentPayment.plan_id == plan.id,
        InstalmentPayment.status.in_(PAYABLE_STATUSES)
    ).order_by(InstalmentPayment.installment_number).first()


def mark_instalment_paid(payment, payment_method, payment_reference, amount_received=None, user=None):
    """Record a confirmed payment, write it to the ledger, and update the plan.

    Doesn't commit: the caller commits so everything is saved together.
    remaining_amount tracks the financed balance, which excludes Payment 1
    (down payment + delivery fee), so only instalments 2..N reduce it.
    """
    total_due = payment.get_total_due()
    payment.status = 'paid'
    payment.paid_date = datetime.now()
    payment.paid_amount = amount_received if amount_received else total_due
    payment.payment_method = payment_method
    payment.payment_reference = payment_reference
    # A late fee charged after the customer started paying stays owed (and in the ledger)
    if payment.late_fee and payment.paid_amount + 0.005 >= total_due:
        payment.late_fee_paid = True

    plan = InstalmentPlan.query.get(payment.plan_id)
    if plan:
        ledger.payment_received(plan, payment, payment.paid_amount, payment_reference, user=user)
        plan.paid_installments = (plan.paid_installments or 0) + 1
        if payment.installment_number > 1:
            plan.remaining_amount = round((plan.remaining_amount or 0) - payment.amount, 2)
        plan.payment_status = 'partial'
        if plan.paid_installments >= plan.number_of_installments:
            plan.status = 'completed'
            plan.payment_status = 'completed'
            plan.completed_at = datetime.now()


def apply_verified_transaction(intent, data):
    """Apply a Paystack transaction that was verified with Paystack's API.

    Idempotent: calling it again for the same successful intent does nothing.
    Returns a short outcome string. Doesn't commit.
    """
    from ..models.payment_intent import PaymentIntent

    if intent.status == PaymentIntent.SUCCESS:
        return 'already_applied'

    intent.channel = data.get('channel') or intent.channel
    intent.gateway_response = (data.get('gateway_response') or '')[:255] or intent.gateway_response
    status = data.get('status')

    if status != 'success':
        if status in ('failed', 'reversed'):
            intent.status = PaymentIntent.FAILED
        elif status == 'abandoned':
            intent.status = PaymentIntent.ABANDONED
        return status or 'unknown'

    if data.get('reference') and data['reference'] != intent.reference:
        intent.status = PaymentIntent.AMOUNT_MISMATCH
        return 'reference_mismatch'

    amount = int(data.get('amount') or 0)
    intent.paid_amount_pesewas = amount
    if data.get('currency') != intent.currency or amount < intent.amount_pesewas:
        # Money arrived but not what we asked for: never mark paid automatically
        intent.status = PaymentIntent.AMOUNT_MISMATCH
        return 'amount_mismatch'

    payment = intent.payment
    intent.paid_at = datetime.utcnow()
    if payment.status == 'paid':
        # Already settled another way (admin or another attempt): flag for refund review
        intent.status = PaymentIntent.SUCCESS
        intent.gateway_response = 'DUPLICATE: instalment was already paid; review for refund'
        return 'duplicate_payment'

    mark_instalment_paid(payment, f"paystack_{intent.channel or 'unknown'}", intent.reference,
                         amount_received=amount / 100)
    intent.status = PaymentIntent.SUCCESS
    return 'applied'
