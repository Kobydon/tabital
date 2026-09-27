"""Deactivating accounts. Accounts are never deleted (money, KYC, fraud and audit records must stay),
and can't be deactivated while money is still owed either way: a suspended customer can't sign in to
pay, and a suspended merchant's settlements would be stuck."""
from ..extensions import db


def deactivation_blocker(user):
    """Why this account can't be deactivated now, or None."""
    from ..models.instalment import InstalmentPlan
    from . import ledger

    if user.role == 'customer':
        plans = InstalmentPlan.query.filter(InstalmentPlan.customer_id == user.id,
                                            InstalmentPlan.status.in_(('active', 'paused'))).all()
        owed = sum((b["outstanding"] for b in ledger.plan_balances(plans).values()), 0) if plans else 0
        if owed > 0:
            return (f"This customer still owes GHS {float(owed):,.2f} on {len(plans)} plan(s). They must be able "
                    "to sign in and pay, so the account can't be deactivated until that's settled.")
    elif user.role == 'merchant':
        from ..models.settlement import Settlement, SettlementLine
        unbatched = db.session.query(db.func.coalesce(db.func.sum(SettlementLine.net_pesewas), 0)).filter(
            SettlementLine.merchant_id == user.id, SettlementLine.settlement_id.is_(None)).scalar() or 0
        unpaid = Settlement.query.filter(Settlement.merchant_id == user.id, Settlement.status != Settlement.PAID,
                                         Settlement.net_pesewas != 0).count()
        if unbatched != 0 or unpaid:
            return ("This merchant still has settlements to be paid (or clawbacks to be taken). "
                    "Deactivate them once those are settled.")
    return None


def deactivate(user):
    """Suspend the account (no sign-in, no new purchases or sales). Raises ValueError if money is owed."""
    reason = deactivation_blocker(user)
    if reason:
        raise ValueError(reason)
    user.status = 'suspended'
    db.session.commit()
