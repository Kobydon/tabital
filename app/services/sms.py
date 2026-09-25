"""SMS/WhatsApp providers behind one interface.

The provider is chosen with SMS_PROVIDER. Until a Ghana provider is chosen (Hubtel, Arkesel,
mNotify, ...; §13.1 D11), the default 'log' provider only writes the message to the server
log, so reminders can be tested end to end without sending anything. To add a real provider,
implement `send(to, body) -> SendResult` and register it in PROVIDERS.
"""
from dataclasses import dataclass
from typing import Optional

from flask import current_app


@dataclass
class SendResult:
    ok: bool
    provider: str
    message_id: Optional[str] = None
    error: Optional[str] = None


def to_e164(phone: str) -> Optional[str]:
    """Ghana numbers: 0241234567 -> +233241234567. Returns None if it doesn't look valid."""
    digits = ''.join(ch for ch in (phone or '') if ch.isdigit())
    if digits.startswith('233') and len(digits) == 12:
        return '+' + digits
    if digits.startswith('0') and len(digits) == 10:
        return '+233' + digits[1:]
    return None


class LogProvider:
    name = 'log'

    def send(self, to, body):
        current_app.logger.info("SMS (log only) to %s: %s", to, body)
        return SendResult(ok=True, provider=self.name, message_id=None)


PROVIDERS = {
    'log': LogProvider,
}


def provider():
    name = (current_app.config.get('SMS_PROVIDER') or 'log').lower()
    cls = PROVIDERS.get(name)
    if cls is None:
        raise RuntimeError(f"Unknown SMS_PROVIDER '{name}'. Available: {', '.join(PROVIDERS)}")
    return cls()
