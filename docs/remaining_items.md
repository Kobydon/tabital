# Remaining items before and after go-live

Checked against CLAUDE.md §13 / §13.1, the other files in `docs/` and the code on
`phase7-unit-economics` (2026-09-27).

Each item is marked:
- **Blocks go-live**: don't launch without it.
- **Soon after**: launch is possible, but do it in the first weeks.
- **Later**: planned, not urgent.

## a. From the founder

Decisions and actions only you can take.

### Security and code

| # | What's needed | Why it matters | When |
|---|---|---|---|
| F1 | **Rotate the database passwords** for `dpg-d7t11…` and `dpg-d8aki…` (live on GitHub `main` today), and `dpg-d888…` (in the history). Delete databases you don't use (`secrets_rotation.md`) | Anyone who can read the repo can read the two live ones now | **Blocks go-live. Do it today** |
| F2 | Check the exposed databases' logs for access you don't recognise. If real customer data was ever in them, decide whether to tell the Data Protection Commission | Data protection (§10) | **Blocks go-live** |
| F3 | Set a new `SECRET_KEY` in Render | Signs all tokens; the old deployment's key can't be trusted | **Blocks go-live** |
| F4 | **History decision (item 5):** push as is, or rewrite the history with `git filter-repo` first (`git_push_checklist.md` section b) | The passwords and `instance/app.db` stay in old commits unless the history is rewritten. A rewrite must happen **before** pushing | **Blocks the push** (decide first) |
| F5 | **Push both repos (item 6)** with your GitHub login (`git_push_checklist.md`) | None of the work since Phase 0 is on GitHub, and nobody else can push | **Blocks go-live** |
| F6 | Sign in to the admin app so the browser click-through of masking, reveal and Team and access can be done (item 13) | Those controls are only tested by automated tests so far, not in a real browser | **Blocks go-live** |

### Render, vendors and accounts

| # | What's needed | Why it matters | When |
|---|---|---|---|
| F7 | **Render setup:** environment variables, the daily cron job, Auto-Deploy off during the first deploy, the web app's rewrite rule (`deploy_checklist.md`) | Without the cron job no late fees, reminders, autopay or settlements run. Without `SMS_PROVIDER=mnotify`, no SMS is sent | **Blocks go-live** |
| F8 | **Live Paystack keys** in Render, the live webhook URL, transfers enabled, a funded GHS balance, OTP off for API transfers | Down payments, instalments, refunds and merchant payouts all go through Paystack (D11) | **Blocks go-live** |
| F9 | **Smile ID:** production keys, ask them to **enable Ghana**, confirm the Ghana Card `id_type` (setting `smileid_ghana_id_type`) | Identity checks are mandatory (§9A). Customers can't buy until verified | **Blocks go-live** |
| F10 | **SIM registration validation (§9A):** ask Smile ID whether they verify Ghanaian phone numbers. Or decide to launch without it | §9A lists it as mandatory; nothing checks it today | **Blocks go-live as §9A is written**, unless you accept launching without it |
| F11 | **mNotify:** API key, and the sender ID (`TabitalPay` or another) registered and approved | Unapproved sender IDs are rejected, so reminders wouldn't arrive | **Blocks go-live** |
| F12 | A mailbox for password-reset emails (`MAIL_USERNAME` / `MAIL_PASSWORD`) | Customers can't reset their password without it | **Blocks go-live** |
| F13 | **First manager account** (`flask create-admin … --management`), then check every existing admin on Team and access | Existing admins were all given Management Access by the migration | **Blocks go-live** |
| F14 | Before the first daily run, a manager clears the "Payments customers say they made" queue (`deploy_checklist.md`, data migration) | The first run can charge late fees on customers who really did pay | **Blocks go-live** |

### Website and legal

| # | What's needed | Why it matters | When |
|---|---|---|---|
| F15 | **Publish the Privacy Policy** at tabitalpay.com/privacy-policy/ (the page has no text) | The app links to it at sign-up, checkout and the Smile ID consent. Data protection (§10) | **Blocks go-live** |
| F16 | Fix the **Terms page** contact: support@tabital.com / www.tabital.com → **info@tabitalpay.com / tabitalpay.com**. Then change `TERMS_VERSION` in Render | Customers accept these Terms on every order | **Blocks go-live** |
| F17 | Update the website's **"no late fees"** copy (§13 #15) | Late fees are on from day one (D5). The website says the opposite | **Blocks go-live** |
| F18 | Mention the **down payment** on the website ("up to 4 interest-free installments" never says so, §13 #16) | Clear consumer disclosure (§10) | **Blocks go-live** |
| F19 | Decide whether a separate **Credit Agreement** is needed. Today each order records the Terms version it accepted, nothing more | Digital credit compliance (§10) | Your call; check before launch |

### Rules still waiting for your confirmation

These are built and will be live on day one. A yes, or the change you want, is enough.

| # | What to confirm | Where it's described | When |
|---|---|---|---|
| F20 | **Phase 6 defaults:** Smile ID auto-verifies only on `clear` plus a name and date-of-birth match; documents alone can't verify; 3 attempts; employment check for the first credit plan and orders of GHS 10,000+; which fraud signals block and which only flag; more than 2 customer accounts on one device is flagged | CLAUDE.md §13.1, `identity_fraud.md` | **Blocks go-live** (confirm or change) |
| F21 | **Deferment defaults:** 10% fee paid up front, 1 per plan, moves that instalment and all later ones by 1 month, only on or before the due date, no limit growth for the plan, a fee that can't be applied is refunded by hand | CLAUDE.md §13.1, `deferment.md` | **Blocks go-live** (or switch `deferment_enabled` off) |
| F22 | **Go-live interim rules:** part payments go to the instalment first, then its late fees, overpaying refused; "I've paid" claims don't change the instalment until staff confirm; merchant fee tiers 8% / 10% / 12%, picked by Management, fixed at approval; accounts are never deleted, can't be suspended while money is owed, and restricted accounts can pay but not buy | CLAUDE.md §13.1 "Go-live review" | **Blocks go-live** (confirm or change) |
| F23 | **Admin data and collections controls:** masked personal data with an audited 60-second reveal; collections can't move due dates; manual reminders by SMS or in-app only | CLAUDE.md §13.1 | **Blocks go-live** (confirm or change) |

### Open business decisions

| # | What's needed | Why it matters | When |
|---|---|---|---|
| F24 | Whether **MDR applies to the delivery fee**, and whether the merchant receives the whole delivery fee | Today the merchant is paid `P × (1 − MDR)` on the product price only; the delivery fee isn't passed on. Merchants who deliver will ask | **Blocks go-live** if merchants deliver; otherwise soon after |
| F25 | Whether **MDR or pricing changes with the 3 / 7 / 30-day billing period** (D4) | Today the MDR is the same for every period | Soon after |
| F26 | **Fraud loss reserve** and **cost of capital** rates (`fraud_loss_reserve_percentage`, `cost_of_capital_annual_percentage`, §13 #14) | Both are 0% until set, so Unit Economics shows a margin that's too high. Reporting only | Soon after |
| F27 | **Down payment for the 6- and 12-month plans**, and the **12-month plan's fee** (§13 #12, D12) | Both plans are switched off ("coming soon") until these are set | Later |
| F28 | What **"3 consecutive transactions"** means for extended-plan eligibility (D7): 3 completed plans, or 3 instalments paid on time | Needed only when the extended plans open | Later |
| F29 | **Hardship / payment arrangement policy** for customers in collections | On hold at your request (2026-09-27). Nothing is built | Later (on hold) |
| F30 | An **AML screening** provider, or a decision that onboarding checks are enough for now (see E9) | AML is a compliance requirement (§10); nothing screens customers or merchants today | Check before launch |

## b. From the engineering agent (code work not done yet)

Found in CLAUDE.md, `docs/` and the code. A search for `TODO` / `FIXME` found none in either repo.

| # | What's missing | What we found | When |
|---|---|---|---|
| E1 | **Browser click-through (item 13)** of masking, reveal and Team and access | Waiting for you to sign in (F6) | **Blocks go-live** |
| E2 | **The session isn't cut when an account is suspended** | `flask_praetorian` checks the account status (`User.is_valid`) only at sign-in and token refresh, not on each request. A suspended or rejected user keeps working until their token expires, up to `JWT_ACCESS_MINUTES` (60). The note in `app/models/user.py` says "every request", which isn't true. Admin access levels are re-checked on every request, so demoting an admin works at once | Soon after |
| E3 | **Customers can't pay part of an instalment** in the app | Part payments exist only for Management in Collections (money received outside Paystack). The customer Make Payment page always charges the full amount due | Soon after |
| E4 | **CSV exports aren't logged** | Exports are Management-only, but only personal-data reveals are written to the access log (`pii_access`). Exports hold unmasked data | Soon after |
| E5 | **The merchant's payout account isn't on the admin merchant detail** | The detail shows only the older `momo_name` / `momo_number` fields. The Paystack payout account (MoMo or bank) is visible only inside a settlement batch | Soon after |
| E6 | **`.env.example` is incomplete** | It lists 19 variables. Missing: `FRONTEND_URL`, `TRUSTED_PROXY_COUNT`, `SMILEID_*`, `TERMS_URL`, `TERMS_VERSION`, `PRIVACY_POLICY_URL` and the guessing limits. `deploy_checklist.md` has the full list | Soon after |
| E7 | **No screen for the message log** | Sent and failed SMS are only visible through `GET /admin/messages` | Soon after |
| E8 | **No real automated frontend tests** | The 57 `*.spec.ts` files are the Angular CLI's generated "should create" checks and aren't part of any check. Only the backend has tests | Soon after |
| E9 | **AML screening** | `users.aml_screening` defaults to `pending` and no code ever sets it; the admin merchant view shows it. Needs a provider (F30) | Soon after (once F30 is decided) |
| E10 | **SIM registration validation (§9A)** | Not built. Waits for Smile ID's answer (F10) | Depends on F10 |
| E11 | **Development build size budgets** | `angular.json` gives the development build the same 100 kB per-component stylesheet limit as production. The customer Shop (27 KB of source) and merchant Dashboard (27 KB) stylesheets, the two largest, are the ones reported over it in the development build. The production build is what's deployed. Not re-run for this document | Soon after |
| E12 | **Risk filters on admin Customers and Merchants** | Removed in batch 5 because the server never filtered by risk level. Putting them back needs server support first | Later |
| E13 | **WhatsApp reminders** | Not connected. Reminders and manual reminders go by SMS (mNotify) or in-app only | Later |
| E14 | **Credit bureau reporting (§8.5 step 4)** | The daily job sets the collections stage to `bureau_reporting`, but nothing is sent to a bureau | Later |
| E15 | **Customer refunds by hand** | Refunds after a dispute the customer won, deferment fees that couldn't be applied, and failed Paystack refunds (`refund_failed`) are all done by hand, as decided in Phase 4 | Later |
| E16 | **Device intelligence (§9D)** | The web app sends a random install ID and simple flags, not full device fingerprinting. Smile ID's device signals could be added (`identity_fraud.md`) | Later |
| E17 | **Screens not yet on the Vault design still use emoji** | Your UI decision says no emoji. A scan finds emoji or symbol characters in about 55 files, mostly older customer, merchant and admin screens (for example merchant reports and disputes, customer notifications, admin transactions) | Later |
| E18 | **Stale placeholder code** | `app/resources/admin_merchants.py` (`AdminMerchantStatsResource`) returns made-up figures (average payout time 1.2 days, growth 14.2%). The current Merchants page doesn't show them, but the code should go | Later |
| E19 | **A stale note in `docs/unit_economics.md`** | "Known issue in older reports" says the Reports revenue chart is a flat 10% estimate. The code now takes revenue from the ledger (`economics.revenue_between`). The note needs updating | Later |
| E20 | **The Flutter mobile app** (D10) | Not started. Android first, after the web app is stable | Later |

Also noticed, harmless: both repos track an empty file called `ng` in their root folder (added to
`main` in June). It can be deleted in a later commit.
