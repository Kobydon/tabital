"""Paystack flow with the Paystack API replaced by a fake (no network, no real keys)."""
import hashlib
import hmac
import json
from decimal import Decimal

import pytest

from app import create_app
from app.extensions import db
from app.models.instalment_payment import InstalmentPayment
from app.models.payment_intent import PaymentIntent
from app.services import ledger, paystack

from tests.test_ledger import approved_plan, token
from app.models.user import User

FAKE_SECRET = "sk_test_fake_key_for_unit_tests"


class FakePaystack:
    """Stands in for the Paystack API. Tests set what verify() will report."""

    def __init__(self):
        self.initialized = []
        self.verify_result = {}

    def initialize(self, **kwargs):
        self.initialized.append(kwargs)
        return {"authorization_url": f"https://checkout.paystack.test/{kwargs['reference']}",
                "access_code": "ac_test", "reference": kwargs["reference"]}

    def verify(self, reference):
        data = {"reference": reference, "currency": "GHS", "channel": "mobile_money",
                "gateway_response": "Approved"}
        data.update(self.verify_result)
        return data


@pytest.fixture()
def env(monkeypatch):
    app = create_app()
    app.config["TESTING"] = True
    app.config["PAYSTACK_SECRET_KEY"] = FAKE_SECRET
    fake = FakePaystack()
    monkeypatch.setattr(paystack, "initialize_transaction", fake.initialize)
    monkeypatch.setattr(paystack, "verify_transaction", fake.verify)
    with app.app_context():
        db.drop_all()
        db.create_all()
        # Approved without a down payment reference: Payment 1 is awaiting payment
        client, admin_headers, plan = approved_plan(app, down_payment_reference="")
        customer = User.query.filter_by(role="customer").one()
        yield {"client": client, "fake": fake, "plan": plan,
               "customer": token(client, customer.phone), "admin": admin_headers}
        db.session.remove()
        db.drop_all()


def signed(body: dict):
    raw = json.dumps(body).encode()
    sig = hmac.new(FAKE_SECRET.encode(), raw, hashlib.sha512).hexdigest()
    return raw, {"x-paystack-signature": sig, "Content-Type": "application/json"}


def start_payment(env):
    res = env["client"].post("/customer/payments/paystack/initialize", headers=env["customer"],
                             json={"plan_id": env["plan"].id, "amount": 1})
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def test_initialize_uses_server_amount(env):
    body = start_payment(env)
    assert body["amount"] == 1650.0                 # down payment + delivery, not the client's 1
    assert body["installment_number"] == 1
    sent = env["fake"].initialized[-1]
    assert sent["amount_pesewas"] == 165000
    assert body["authorization_url"].endswith(body["reference"])
    intent = PaymentIntent.query.filter_by(reference=body["reference"]).one()
    assert intent.status == PaymentIntent.INITIALIZED


def test_webhook_rejects_bad_signature(env):
    body = start_payment(env)
    raw = json.dumps({"event": "charge.success", "data": {"reference": body["reference"]}}).encode()
    res = env["client"].post("/webhooks/paystack", data=raw,
                             headers={"x-paystack-signature": "forged", "Content-Type": "application/json"})
    assert res.status_code == 401
    p1 = InstalmentPayment.query.filter_by(plan_id=env["plan"].id, installment_number=1).one()
    assert p1.status == "pending_verification"


def test_signed_webhook_marks_paid_once(env):
    body = start_payment(env)
    env["fake"].verify_result = {"status": "success", "amount": 165000}
    raw, headers = signed({"event": "charge.success", "data": {"reference": body["reference"]}})

    res = env["client"].post("/webhooks/paystack", data=raw, headers=headers)
    assert res.status_code == 200 and res.get_json()["status"] == "applied"
    p1 = InstalmentPayment.query.filter_by(plan_id=env["plan"].id, installment_number=1).one()
    assert p1.status == "paid" and p1.payment_method == "paystack_mobile_money"
    assert ledger.customer_balance(env["plan"]) == Decimal("2400.00")

    # Paystack retries the same webhook: nothing changes
    res = env["client"].post("/webhooks/paystack", data=raw, headers=headers)
    assert res.get_json()["status"] == "already_applied"
    assert ledger.customer_balance(env["plan"]) == Decimal("2400.00")


def test_callback_verify_marks_paid(env):
    body = start_payment(env)
    env["fake"].verify_result = {"status": "success", "amount": 165000}
    res = env["client"].get(f"/customer/payments/paystack/verify/{body['reference']}", headers=env["customer"])
    assert res.status_code == 200 and res.get_json()["outcome"] == "applied"
    assert ledger.customer_balance(env["plan"]) == Decimal("2400.00")


def test_underpayment_is_not_marked_paid(env):
    body = start_payment(env)
    env["fake"].verify_result = {"status": "success", "amount": 100}   # GHS 1.00
    res = env["client"].get(f"/customer/payments/paystack/verify/{body['reference']}", headers=env["customer"])
    assert res.get_json()["outcome"] == "amount_mismatch"
    p1 = InstalmentPayment.query.filter_by(plan_id=env["plan"].id, installment_number=1).one()
    assert p1.status == "pending_verification"
    assert ledger.customer_balance(env["plan"]) == Decimal("4050.00")


def test_failed_charge_is_not_marked_paid(env):
    body = start_payment(env)
    env["fake"].verify_result = {"status": "failed", "amount": 165000}
    res = env["client"].get(f"/customer/payments/paystack/verify/{body['reference']}", headers=env["customer"])
    assert res.get_json()["status"] == PaymentIntent.FAILED
    assert ledger.customer_balance(env["plan"]) == Decimal("4050.00")


def test_customer_cannot_verify_someone_elses_payment(env):
    body = start_payment(env)
    other = User(phone="0209999999", role="customer", status="approved",
                 password=User.query.filter_by(role="customer").one().password)
    db.session.add(other)
    db.session.commit()
    res = env["client"].get(f"/customer/payments/paystack/verify/{body['reference']}",
                            headers=token(env["client"], other.phone))
    assert res.status_code == 404


def test_next_instalment_after_down_payment(env):
    body = start_payment(env)
    env["fake"].verify_result = {"status": "success", "amount": 165000}
    env["client"].get(f"/customer/payments/paystack/verify/{body['reference']}", headers=env["customer"])
    second = start_payment(env)
    assert second["installment_number"] == 2 and second["amount"] == 800.0


def test_not_configured_returns_503(env):
    from flask import current_app
    current_app.config["PAYSTACK_SECRET_KEY"] = None
    res = env["client"].post("/customer/payments/paystack/initialize", headers=env["customer"],
                             json={"plan_id": env["plan"].id})
    assert res.status_code == 503
    assert env["client"].get("/customer/payments/config", headers=env["customer"]).get_json() == {"paystack_enabled": False}
