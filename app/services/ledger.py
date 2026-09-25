"""Write money events to the ledger and read balances from it.

Callers add entries inside their own database transaction; this module never commits,
so the ledger row and the change it records are saved together or not at all.
"""
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func

from ..extensions import db
from ..models.ledger import LedgerEntry

CENT = Decimal("0.01")


def to_pesewas(amount) -> int:
    return int((Decimal(str(amount)).quantize(CENT, ROUND_HALF_UP) * 100).to_integral_value())


def to_cedis(pesewas) -> Decimal:
    return (Decimal(int(pesewas or 0)) / 100).quantize(CENT)


def record(plan, entry_type, amount, *, account=LedgerEntry.CUSTOMER, payment=None,
           reference=None, note=None, user=None):
    """Append one entry. `amount` is in GHS and carries its sign (see LedgerEntry)."""
    if plan.id is None:
        db.session.flush()
    entry = LedgerEntry(
        plan_id=plan.id,
        payment_id=payment.id if payment is not None else None,
        account=account,
        entry_type=entry_type,
        amount_pesewas=to_pesewas(amount),
        reference=reference,
        note=note,
        created_by=user.id if user is not None else None,
    )
    db.session.add(entry)
    return entry


def open_plan(plan, total_payable, merchant_fee, merchant_payable, user=None):
    """Record a new contract: what the customer owes and what the merchant is owed."""
    record(plan, LedgerEntry.PLAN_OPENED, total_payable, note="Contract total payable", user=user)
    record(plan, LedgerEntry.MERCHANT_FEE, merchant_fee, account=LedgerEntry.MERCHANT,
           note="Merchant discount (MDR)", user=user)
    record(plan, LedgerEntry.MERCHANT_PAYABLE, merchant_payable, account=LedgerEntry.MERCHANT,
           note="Settlement owed to merchant", user=user)


def payment_received(plan, payment, amount, reference, user=None):
    return record(plan, LedgerEntry.PAYMENT_RECEIVED, -Decimal(str(amount)), payment=payment,
                  reference=reference, note=f"Payment {payment.installment_number}", user=user)


def late_fee_charged(plan, payment, fee, user=None):
    return record(plan, LedgerEntry.LATE_FEE_CHARGED, fee, payment=payment,
                  note=f"Late fee on payment {payment.installment_number}", user=user)


def late_fee_waived(plan, payment, fee, reason=None, user=None):
    return record(plan, LedgerEntry.LATE_FEE_WAIVED, -Decimal(str(fee)), payment=payment,
                  note=(reason or "Late fee waived")[:255], user=user)


def customer_balance(plan) -> Decimal:
    """What the customer still owes on this plan, in GHS, including unpaid late fees."""
    total = db.session.query(func.coalesce(func.sum(LedgerEntry.amount_pesewas), 0)).filter(
        LedgerEntry.plan_id == plan.id, LedgerEntry.account == LedgerEntry.CUSTOMER
    ).scalar()
    return to_cedis(total)


def has_entries(plan) -> bool:
    return db.session.query(LedgerEntry.id).filter(LedgerEntry.plan_id == plan.id).first() is not None
