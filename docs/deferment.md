# Instalment deferment (CLAUDE.md §4, interim rule §13 #8)

A customer can pay a fee to push an upcoming instalment back. It protects their credit record: a
deferred instalment is never a late payment.

## Rules (settings; defaults pending founder confirmation)

| Setting | Default | Meaning |
|---|---|---|
| `deferment_enabled` | true | Switch the feature on or off |
| `deferment_fee_percentage` | 10 | Fee as % of the deferred instalment (§4) |
| `deferment_max_per_plan` | 1 | Deferments allowed per plan (§13 #8) |
| `deferment_months` | 1 | How far the instalment moves (§13 #8) |
| risk rule `deferred_plans_count_as_clean` | false | Whether a plan with a deferment earns limit growth |

- The deferred instalment **and every unpaid instalment after it** move by the same number of
  months, so the customer never has two payments in one month. The plan's end date moves too.
- Allowed only for an **upcoming** instalment (not Payment 1), **on or before its due date**, with
  no late fee on it. The plan must be active, not paused by a dispute, and have nothing overdue.
- Before agreeing, the customer sees the fee, the old and new date of every instalment that moves,
  and the plan's total payable before and after.
- The fee is paid **up front through Paystack**. Dates only move once Paystack confirms the payment
  (verify page or signed webhook, both re-checked with Paystack's API).

## Money

- Ledger: `deferment_fee` (+fee) and `payment_received` (−fee) on the customer account, so what's
  still owed doesn't change. The fee counts as money received.
- The late-fee cap (25%) is still based on the original total payable.
- If a late fee was charged while the fee payment was going through, it's reversed (`late_fee_waived`).
- If the deferment can no longer be applied when the money arrives (for example the instalment was
  paid in the meantime, or the deferment allowance was already used), nothing moves. The deferment is
  saved as `refund_required` and listed at `GET /admin/deferments?status=refund_required`. The refund
  is done by hand, like dispute refunds.

## Credit

A deferment never lowers the limit or tier. Treated like a cured late payment: a plan with a
deferment doesn't earn +0.1× limit growth, low-tier promotion or extended-plan streak credit,
unless `deferred_plans_count_as_clean` is switched on.

## Reminders and autopay

Reminders run again for the new due date. Autopay uses the new due date automatically.

## Endpoints

- `GET /customer/plans/<plan_id>/deferment[?payment_id=]`: the quote (allowed or not, reasons, fee,
  schedule, totals, deferments left, history)
- `POST /customer/plans/<plan_id>/deferment {payment_id, agree: true}`: starts the Paystack payment
- `GET /admin/deferments[?status=applied|refund_required]`
