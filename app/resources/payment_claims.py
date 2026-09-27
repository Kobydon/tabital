"""Payment claims (customers saying they paid outside the app): list, confirm (records the money
through services/payments.record_payment) or reject. Confirming and rejecting need Management Access
(enforced centrally, services/access.py)."""
from datetime import datetime

from flask import request
from flask_praetorian import auth_required, current_user
from flask_restful import Resource

from ..extensions import db
from ..models.payment_claim import PaymentClaim
from ..services import payments


def _admin():
    user = current_user()
    return user if user.role == 'admin' else None


def _notify(claim, title, message):
    try:
        from ..models.notifications import Notifications
        Notifications.create_notification(user_id=claim.customer_id, user_role='customer', title=title,
                                          message=message, type='payment', link='/customer/instalments',
                                          action_text='View plan')
    except Exception:                      # noqa: BLE001 (a failed notification never undoes the decision)
        pass


class AdminPaymentClaimsResource(Resource):
    @auth_required
    def get(self):
        if not _admin():
            return {"error": "Unauthorized"}, 403
        status = request.args.get('status', PaymentClaim.PENDING)
        q = PaymentClaim.query
        if status:
            q = q.filter(PaymentClaim.status == status)
        claims = q.order_by(PaymentClaim.created_at.desc()).limit(200).all()
        return {"claims": [c.to_dict() for c in claims],
                "pending": PaymentClaim.query.filter_by(status=PaymentClaim.PENDING).count()}, 200


class AdminPaymentClaimConfirmResource(Resource):
    @auth_required
    def post(self, claim_id):
        admin = _admin()
        if not admin:
            return {"error": "Unauthorized"}, 403
        claim = PaymentClaim.query.get(claim_id)
        if not claim:
            return {"error": "Claim not found"}, 404
        if claim.status != PaymentClaim.PENDING:
            return {"error": f"This claim is already {claim.status}"}, 400
        data = request.get_json() or {}
        payment = claim.payment
        amount = data.get('amount_received', payment.get_total_due())
        reference = (data.get('payment_reference') or claim.reference or '').strip()
        method = claim.method if claim.method in ('mobile_money', 'bank_transfer', 'card') else 'manual'
        try:
            outcome = payments.record_payment(payment, amount, method, reference, user=admin)
        except payments.PaymentError as e:
            db.session.rollback()
            return {"error": str(e)}, 400
        claim.status = PaymentClaim.CONFIRMED
        claim.reviewed_by, claim.reviewed_at = admin.id, datetime.utcnow()
        claim.review_note = f"Confirmed: {float(amount):.2f} received ({outcome})"[:500]
        db.session.commit()
        still_owed = payment.get_total_due()
        _notify(claim, "Payment received",
                "We've received your payment." if outcome == 'paid'
                else f"We've received part of your payment. GHS {still_owed:,.2f} is still due on this instalment.")
        return {"message": "Payment recorded" if outcome == 'paid'
                else f"Part payment recorded. {still_owed:.2f} is still owed.",
                "outcome": outcome, "still_owed": still_owed, "claim": claim.to_dict()}, 200


class AdminPaymentClaimRejectResource(Resource):
    @auth_required
    def post(self, claim_id):
        admin = _admin()
        if not admin:
            return {"error": "Unauthorized"}, 403
        claim = PaymentClaim.query.get(claim_id)
        if not claim:
            return {"error": "Claim not found"}, 404
        if claim.status != PaymentClaim.PENDING:
            return {"error": f"This claim is already {claim.status}"}, 400
        reason = ((request.get_json() or {}).get('reason') or '').strip()
        if len(reason) < 5:
            return {"error": "Say why (at least 5 characters). The customer sees it."}, 400
        claim.status = PaymentClaim.REJECTED
        claim.reviewed_by, claim.reviewed_at = admin.id, datetime.utcnow()
        claim.review_note = reason[:500]
        db.session.commit()
        _notify(claim, "We couldn't find your payment",
                f"{reason} Your instalment is still due; pay it in the app or contact us.")
        return {"message": "Claim rejected", "claim": claim.to_dict()}, 200
