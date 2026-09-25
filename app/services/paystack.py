"""Thin Paystack API client (https://paystack.com/docs/api/).

Only three things are used: start a transaction, verify it, and check webhook signatures.
Amounts are in the currency subunit (pesewas for GHS).
"""
import hashlib
import hmac

import requests
from flask import current_app

TIMEOUT_SECONDS = 20


class PaystackError(Exception):
    pass


def _secret():
    key = current_app.config.get("PAYSTACK_SECRET_KEY")
    if not key:
        raise PaystackError("Paystack is not configured (PAYSTACK_SECRET_KEY missing)")
    return key


def is_configured() -> bool:
    return bool(current_app.config.get("PAYSTACK_SECRET_KEY"))


def _headers():
    return {"Authorization": f"Bearer {_secret()}", "Content-Type": "application/json"}


def _base():
    return current_app.config.get("PAYSTACK_BASE_URL", "https://api.paystack.co").rstrip("/")


def initialize_transaction(*, email, amount_pesewas, reference, callback_url=None, metadata=None,
                           channels=("card", "mobile_money")):
    """Returns Paystack's `data`: authorization_url, access_code, reference."""
    body = {
        "email": email,
        "amount": int(amount_pesewas),
        "currency": "GHS",
        "reference": reference,
        "channels": list(channels),
        "metadata": metadata or {},
    }
    if callback_url:
        body["callback_url"] = callback_url
    try:
        res = requests.post(f"{_base()}/transaction/initialize", json=body, headers=_headers(),
                            timeout=TIMEOUT_SECONDS)
        payload = res.json()
    except (requests.RequestException, ValueError) as e:
        raise PaystackError(f"Could not reach Paystack: {e}")
    if res.status_code >= 400 or not payload.get("status"):
        raise PaystackError(payload.get("message") or f"Paystack error {res.status_code}")
    return payload["data"]


def verify_transaction(reference):
    """Returns Paystack's `data` for a transaction (status, amount, currency, channel, ...)."""
    try:
        res = requests.get(f"{_base()}/transaction/verify/{reference}", headers=_headers(),
                           timeout=TIMEOUT_SECONDS)
        payload = res.json()
    except (requests.RequestException, ValueError) as e:
        raise PaystackError(f"Could not reach Paystack: {e}")
    if res.status_code >= 400 or not payload.get("status"):
        raise PaystackError(payload.get("message") or f"Paystack error {res.status_code}")
    return payload["data"]


def charge_authorization(*, email, amount_pesewas, authorization_code, reference, metadata=None):
    """Charge a saved reusable authorization (autopay). Returns Paystack's transaction `data`.

    data.status is 'success' when charged immediately; other statuses mean Paystack will
    finish later and notify us by webhook.
    """
    body = {
        "email": email,
        "amount": int(amount_pesewas),
        "currency": "GHS",
        "authorization_code": authorization_code,
        "reference": reference,
        "metadata": metadata or {},
    }
    try:
        res = requests.post(f"{_base()}/transaction/charge_authorization", json=body, headers=_headers(),
                            timeout=TIMEOUT_SECONDS)
        payload = res.json()
    except (requests.RequestException, ValueError) as e:
        raise PaystackError(f"Could not reach Paystack: {e}")
    if res.status_code >= 400 or not payload.get("status"):
        raise PaystackError(payload.get("message") or f"Paystack error {res.status_code}")
    return payload["data"]


def deactivate_authorization(authorization_code):
    """Tell Paystack a saved card should no longer be chargeable (best effort)."""
    try:
        res = requests.post(f"{_base()}/customer/deactivate_authorization",
                            json={"authorization_code": authorization_code}, headers=_headers(),
                            timeout=TIMEOUT_SECONDS)
        return res.status_code < 400
    except requests.RequestException:
        return False


def refund_transaction(reference, amount_pesewas=None, reason=None):
    """Refund a successful transaction (all of it unless amount_pesewas is given).

    Returns Paystack's `data` (status is usually 'pending' or 'processed').
    """
    body = {"transaction": reference}
    if amount_pesewas is not None:
        body["amount"] = int(amount_pesewas)
    if reason:
        body["merchant_note"] = reason[:255]
    try:
        res = requests.post(f"{_base()}/refund", json=body, headers=_headers(), timeout=TIMEOUT_SECONDS)
        payload = res.json()
    except (requests.RequestException, ValueError) as e:
        raise PaystackError(f"Could not reach Paystack: {e}")
    if res.status_code >= 400 or not payload.get("status"):
        raise PaystackError(payload.get("message") or f"Paystack error {res.status_code}")
    return payload["data"]


def valid_webhook_signature(raw_body: bytes, signature: str) -> bool:
    """Paystack signs webhooks with HMAC-SHA512 of the raw body using the secret key."""
    if not signature or not is_configured():
        return False
    expected = hmac.new(_secret().encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)
