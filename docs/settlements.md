# Merchant settlements, statements and payment links (Phase 5)

## How a merchant gets paid

1. **Delivery confirmed** (`PUT /merchant/orders/<id>/delivery`, status `delivered`) creates one
   `sale` settlement line for the plan: gross = product price, fee = MDR, net = `P × (1 − MDR)`
   (§5.2). The merchant is owed money from delivery, not from approval.
2. **Batching**: `flask run-daily` calls `settlements.generate_batches`. Each merchant's unbatched
   lines are swept into a `Settlement` once their billing cycle has passed (3, 7 or 30 days, D4,
   default 7). A batch is made only when the net is above zero; a negative net (clawbacks larger
   than new sales) carries forward.
3. **Approval**: every batch waits for an admin (`POST /admin/settlement-batches/<id>/approve`).
   Approval creates the Paystack transfer recipient if needed (MoMo or GhIPSS bank) and starts a
   transfer. Outcome: `paid`, `processing` (finished by the `transfer.success` webhook), or
   `failed` (can be approved again).
4. **Ledger**: when paid, each line posts `merchant_settled` (−net) so the merchant account nets
   to zero. A `transfer.reversed` event after payment reverses those entries and marks the batch
   `failed`.

## Clawbacks

When an admin resolves a dispute as `customer_won`, `settlements.clawback_plan` runs:

- Sale not yet paid out: the line is removed, so the merchant is never paid for it.
- Sale already paid or in progress: a negative `clawback` line comes off the next settlement,
  and a `merchant_clawback` ledger entry records the debt.
- Not delivered yet: the plan is flagged, so a later delivery adds no line.

The customer refund itself is still done by hand (Phase 4 decision).

## Payout account security

Merchants set their payout account with `PUT /merchant/payout-account`: `payout_method`
(`mobile_money` | `bank`), `payout_bank_code` (from `GET /merchant/payout-banks?method=`), the
account number and name, and `settlement_period_days`. When a merchant changes payout details
(through this or any older settings endpoint):

- the saved Paystack recipient is cleared, and
- payouts are held for `payout_hold_hours` (SystemSetting, default 48), and the merchant
  gets an in-app notice.

Batches created or approved during the hold stay `on_hold`. Changes made by an admin don't start
a hold.

## Statements

- `GET /merchant/statement?from=YYYY-MM-DD&to=YYYY-MM-DD` returns sales, fees, clawbacks and payouts
  with totals.
- Add `&format=csv` for a CSV download.
- `GET /merchant/settlement-batches[/<id>]` lists batches and their lines.

## Payment links / QR (in-store and WhatsApp sales)

- `POST /merchant/payment-links` `{product_id, quantity?, note?, expires_in_hours? (1–168, default 24)}`
  returns `url` (`{FRONTEND_URL}/customer/pay-link/<token>`) and `qr_svg`.
- `GET /merchant/payment-links` lists links. `DELETE /merchant/payment-links/<id>` cancels one.
- Customers call `GET /customer/payment-links/<token>`, then
  `POST /customer/purchase {payment_link, number_of_installments}`. The product and quantity come
  from the link, and the address defaults to "Collected in store". Each link works once; a used,
  expired or cancelled link returns 410.
- All normal checks still apply (KYC, eligibility, limit, down payment at checkout).

Set `FRONTEND_URL` in the environment (e.g. `https://app.tabitalpay.com`).

## Paystack setup

Transfers need a funded Paystack GHS balance and transfers enabled on the account. With
OTP-on-transfer turned on in the Paystack dashboard, a transfer returns `otp` and stays
`processing`. Turn OTP off for API payouts, or finalise the transfer in the dashboard. Add the
webhook events `transfer.success`, `transfer.failed` and `transfer.reversed` (same URL as charges).
