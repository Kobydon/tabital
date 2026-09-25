# Paystack setup

Tabital collects the down payment and instalments through Paystack (card and mobile money, GHS).

## Checkout: the down payment is paid first

1. The customer places an order in the Shop.
2. `POST /customer/purchase` prices it on the server and saves it as `awaiting_payment`. It then starts a Paystack transaction for **Payment 1** (down payment + delivery fee) and returns Paystack's `authorization_url`.
3. Once Paystack confirms the charge (callback verify or webhook), the order becomes `pending`. That means it's paid and waiting for admin approval.
4. The admin can't approve an order until its down payment is paid. On approval, the plan starts with Payment 1 already paid, and the ledger records it.
5. If the admin rejects a paid order, the down payment is refunded through Paystack (`POST /refund`). If the refund call fails, the order shows `refund_failed` and someone has to refund it by hand.
6. If the first attempt fails, the customer can pay again from **My Orders** (`POST /customer/orders/<id>/pay`).

Some cases are flagged rather than handled automatically:

| Case | What happens |
|---|---|
| Customer pays twice for the same order | The second payment is flagged for refund |
| Money arrives after the order was rejected | The order shows `refund_required` |

Without Paystack configured, orders go straight to `pending`, and the admin records the down-payment reference by hand when approving.

## Instalments after approval

1. The customer opens **Make Payment** and clicks **Pay with Card or MoMo**.
2. `POST /customer/payments/paystack/initialize` works out the amount due on the server (the next unpaid instalment plus any unpaid late fee), creates a `payment_intents` row, and starts a Paystack transaction.
3. The customer pays on Paystack's checkout page.
4. Paystack does two things:
   - redirects the customer to `PAYSTACK_CALLBACK_URL` (`/customer/payment-callback`). That page calls `GET /customer/payments/paystack/verify/<reference>`.
   - sends a signed `charge.success` webhook to `POST /webhooks/paystack`.
5. Either way, the server **verifies the transaction with Paystack's API** and only then marks the instalment paid and writes a `payment_received` ledger entry. Repeated webhooks don't change anything.

Paystack's report is never applied automatically when it's wrong. These cases are left for an admin to review:

| Case | `payment_intents.status` |
|---|---|
| Underpaid, or not in GHS | `amount_mismatch` |
| Instalment was already paid another way | `success`, with a `DUPLICATE` note (refund review) |

## Configuration (environment variables)

| Variable | Value |
|---|---|
| `PAYSTACK_SECRET_KEY` | `sk_test_...` while testing, `sk_live_...` at go-live |
| `PAYSTACK_PUBLIC_KEY` | `pk_test_...` / `pk_live_...` (not used by the server yet) |
| `PAYSTACK_CALLBACK_URL` | Frontend URL of the callback page, e.g. `https://app.tabitalpay.com/customer/payment-callback` |

Locally, put these in `tabital/.env`, which is ignored by git. On Render, add them as environment variables. **Never commit keys.**

If `PAYSTACK_SECRET_KEY` is missing, online payment is switched off. The Make Payment page then shows only the manual "enter your transfer reference" form, and an admin confirms those payments.

## Paystack dashboard

In Paystack Dashboard > Settings > API Keys & Webhooks:

- **Webhook URL:** `https://<api-host>/webhooks/paystack` (for example `https://tabital.onrender.com/webhooks/paystack`)
- **Callback URL:** leave blank. The app sends it with each transaction.

Paystack can't reach `localhost`, so local testing relies on the callback page's verify call. To test webhooks locally, use a tunnel such as ngrok.

## Test cards and MoMo

Use Paystack's published test card and mobile money details in test mode. See Paystack's "Test Payments" documentation. No real money moves with `sk_test_` keys.
