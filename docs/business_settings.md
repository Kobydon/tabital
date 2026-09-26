# Business settings

Admin page: **Business Settings** (`/admin/system-settings`, also linked as "Rates & Rules").
It replaces the old System Settings page, which called an address that didn't exist, and the old
Charges page, which saved any value with no checks.

## How it works

- `app/services/business_settings.py` is the list of editable settings. For each one it holds:
  - label and help text;
  - type (%, GHS, days, hours, on/off, text, list of days);
  - allowed range and default;
  - what a change affects, and the CLAUDE.md reference.
- `GET /admin/business-settings` returns the groups with current values, defaults, and who changed
  each one last.
- `PUT /admin/business-settings {changes: {key: value}, reason}`:
  - **every** value is checked (known key, type, range, at most 2 decimal places, and the late-fee
    cap can't be below the first late fee);
  - a reason of at least 5 characters is required;
  - if anything fails, **nothing** is saved;
  - otherwise everything is saved in one go, with a row per change in `setting_changes`.
- `GET /admin/business-settings/history`: who changed what, from what, to what, and why.
- A test checks that each default on the page equals the default the code really uses.

## What a change affects

| Group | Effect |
|---|---|
| Plans and pricing (down payment, delivery fee, service fee, MDR) | New orders only. Approved plans keep their stored schedule (§5.4). |
| Late fees, deferment, collections, payouts, identity and fraud | From now on, including on existing plans. |
| Margin model | Reporting only (Unit Economics). |

## Not editable here (on purpose)

- **Risk rules** (`risk_rules`): the tiers, limits and growth rules. They have their own versioned
  defaults in `services/risk.py`.
- **Reminder templates and schedule**.
- **The legacy instalment options**: the plans on offer are fixed as Full and Pay in 2/3/4 (§4, D12).
- **`late_fee_grace_period_days`**: D5 says there's no grace period, and the late-fee code doesn't
  read it.

The old write endpoints `PUT /admin/settings/charges` and `PUT /admin/settings/installments`
now return 410.
