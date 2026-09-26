# Unit economics and portfolio reporting (Phase 7)

Admin page: **Unit Economics** (`/admin/unit-economics`). Every figure comes from the ledger and the
stored instalment schedule. The cost rates are settings.

## Margin model (CLAUDE.md §7, full model)

Per plan:

```
Merchant fee revenue   MDR x P                       (ledger merchant_fee)
- Gateway cost         gateway_fee_percentage x P            (default 2%, §6.1)
- Expected credit loss expected_credit_loss_percentage x FB  (default 5%)
- Fraud loss reserve   fraud_loss_reserve_percentage x FB    (default 0%, not set yet, §13 #14)
- Collections cost     collections_cost_percentage x FB      (default 3%)
- Cost of capital      cost_of_capital_annual_percentage x FB x term/12 / 2   (default 0%, not set yet)
= Modelled net
```

`P` = product price (merchant fee + merchant payable in the ledger). `FB` = the sum of instalments
2..N. The cost of capital uses half the financed balance because it's repaid in equal monthly
instalments. With the defaults, the §7 worked example (GHS 4,000, Pay in 4, 10% MDR) gives
**GHS 128 (3.2%)**. The fraud reserve and cost of capital are 0 until the founder sets them, and the
page and CSV say so.

**Net with actuals** swaps the expected-loss line for losses actually booked (the balance still owed
on plans charged off in the period), and adds late fees (net of waivers) and deferment fees.

## Portfolio and liquidity

- Outstanding book by §8.4 bucket; charged-off plans count as 90+.
- PAR 30 / 60 / 90: share of the outstanding book on plans more than 30 / 60 / 90 days late.
- Liquidity (§12, the biggest risk):
  - Owed to merchants: payable minus settled minus clawed back.
  - Customer payments due in the next 30 days, and overdue customer payments.
  - Funding gap: cash to find from reserves in the next 30 days.

## Cohorts (Year-1 mission, §12)

Plans grouped by the month they were opened: instalments due so far, share paid on time, share of
plans ever more than 30 days late, defaults, and the **loss rate** (outstanding on defaulted plans ÷
financed) against the expected-credit-loss assumption.

## What-if calculator

Price, plan, down payment %, MDR % and any cost rate can be changed to test a scenario. Nothing is saved.

## Endpoints (admin only)

`/admin/economics/summary?from&to`, `/admin/economics/export?from&to` (CSV),
`/admin/economics/portfolio`, `/admin/economics/cohorts`, `/admin/economics/scenario?price&n&...`

## Known issue in older reports

The older **Reports** revenue chart (`/admin/reports/revenue`) still estimates revenue as a flat 10% of
transaction amounts, using floating-point numbers. It ignores the actual MDR, costs and losses. Use
Unit Economics for decisions. The old report should be moved onto the ledger or retired.
