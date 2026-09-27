# Identity and fraud checks (Phase 6, CLAUDE.md §9)

## Identity: Smile ID Biometric KYC (§9A)

1. The customer adds their full name (as on the Ghana Card), date of birth and Ghana Card number
   (`GHA-XXXXXXXXX-X`), then opens **Verify identity** in the app and agrees to the check.
2. `POST /customer/identity/start {consent: true}` mints a 15-minute Smile ID token **bound to the
   details we hold** (Ghana Card number, names, phone, consent, callback URL).
3. The browser captures a selfie and liveness images with Smile ID's web components and uploads
   them **straight to Smile ID**. Images never pass through our servers, and we never store them.
4. The browser reports Smile ID's `job_id`: `POST /customer/identity/<check_id>/submitted`.
5. Smile ID posts the result to `POST /webhooks/smileid`. We check the `Response-Signature` (HMAC-SHA256
   of timestamp + partner ID + `sid_request`), reject timestamps older than 10 minutes, and re-check
   the job's status with Smile ID before acting on it.

| Smile ID result | Our checks | Outcome |
|---|---|---|
| `clear` | Name **and** date of birth from the ID authority match the profile | **Verified**; tier and limit are set |
| `clear` | Name or date of birth doesn't match | **Review** by an admin |
| `attention` | – | **Review** by an admin |
| `block` | – | **Blocked**; KYC rejected |
| `error` | – | Customer can try again |
| any | Ghana Card already verified on another account | **Blocked** + a fraud flag |

- Customers get 3 attempts (`identity_max_attempts`), after which they must contact support.
- Admins decide reviews in **Identity review** (`/admin/identity-checks`), always with a note.
- Once a customer is verified, they can't change their name or Ghana Card number themselves.
- **While Smile ID is configured, documents alone can't verify a customer.** The old manual
  approval only works while `SMILEID_PARTNER_ID`/`SMILEID_API_KEY` aren't set (local development),
  and it records a `manual` identity check. The `kyc_require_biometric` setting can turn this off.

### Setup

Put these in `tabital/.env` (local) or the Render environment. **Never commit them.**

```
SMILEID_PARTNER_ID=...
SMILEID_API_KEY=...
SMILEID_BASE_URL=https://testapi.smileidentity.com     # production: https://api.smileidentity.com
SMILEID_CALLBACK_URL=https://<api host>/webhooks/smileid
PRIVACY_POLICY_URL=https://tabitalpay.com/<privacy page>
```

Before go-live:
- **Ask Smile ID to enable Ghana** on the account. Their docs say Ghana is available on request.
- Confirm the Ghana Card `id_type` with `GET /v3/services/supported_id_types?country=GH`, and set
  `smileid_ghana_id_type` if it isn't `GHANA_CARD`.
- SIM registration validation (§9A) isn't covered yet. Ask Smile ID whether their phone number
  verification covers Ghanaian networks.

## Employment verification (§9B)

A credit purchase (Pay in 2/3/4) needs employment verified when it's the customer's **first plan**,
or the order is **GHS 10,000 or more** (`high_ticket_threshold`, D6). An admin records it with
`PUT /admin/customers/<id>/employment-verification {verified, method, note}`. The method is one of
`employer_call`, `employer_letter`, `payslip` or `ssnit`. Paying in full doesn't need it.

## Fraud signals (§9D, §9E)

| Code | When | Severity |
|---|---|---|
| `duplicate_ghana_card` | Same Ghana Card on two customer accounts | block (both) |
| `self_dealing` | Customer buys from a merchant sharing their phone or payout number | block (merchant); order refused |
| `shared_device` | More than `fraud_max_customer_accounts_per_device` (2) customers on one device | review |
| `merchant_customer_same_device` | A merchant and a customer used the same device | review |
| `automated_browser` | Browser reports automation (webdriver) or an emulator | review |
| `shared_momo` | Two customers with the same MoMo number | review |
| `merchant_customer_shared_account` | A customer's MoMo is a merchant's payout or contact number | review |
| `shared_payout_account` | Two merchants with the same payout account | review |
| `repeat_orders_same_customer` | 3+ orders from one merchant to one customer in 30 days | review |
| `quick_dispute` | Dispute within 3 days of delivery (possible fake sale) | review |

- **block** stops the customer's new purchases, order approval, and the merchant's payouts
  (settlement batches go `on_hold`), until an admin clears it in **Fraud review**.
- **review** shows in the queue and on the admin orders list, but doesn't stop anything.
- Admins clear or confirm each signal with a note (`PUT /admin/fraud-signals/<id>`), and the
  history is kept on the signal.

Devices: the web app sends a random install ID (`X-Device-Id`) and simple flags (`X-Device-Flags`)
on every request. That's a device identifier, not full device fingerprinting. Smile ID's own device
signals can be added later.
