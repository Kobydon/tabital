# Deploy checklist (Render)

Do these in order for the first go-live deploy, and check the ones marked (every deploy) each time.
Push the code first with `docs/git_push_checklist.md`. **Read its section e before `main` changes:**
Render deploys `main`, and may do it by itself as soon as `main` moves.

Commands below run from the `tabital` folder (on Render: the service's **Shell** tab). They name the
app explicitly, the same way as `docs/servicing.md`:

```
flask --app "app:create_app" <command>
```

## Before anything else
1. **Rotate the database passwords** listed in `docs/secrets_rotation.md`. Two are readable on
   GitHub `main` today (hosts starting `dpg-d7t11…` and `dpg-d8aki…`).
2. Generate a new `SECRET_KEY` (`python -c "import secrets; print(secrets.token_urlsafe(64))"`).
   Changing it signs everyone out once.
3. Turn **Auto-Deploy off** on the Render web service and cron job until steps 4–12 are ready
   (Render → service → Settings). Turn it back on after the smoke test.
4. **Back up the production database** before the first migration (Render → the database → backups,
   or `pg_dump`). The migrations change data as well as tables (see "Data migration" below).

## Render services
| Service | Setting |
|---|---|
| Web service (API) | Build: `pip install -r requirements.txt`. Start: `gunicorn "app:create_app()"`. Branch: `main`. Set `PYTHON_VERSION` to `3.12.10`, the version the tests run on |
| Cron job (daily servicing) | Same repo, branch, build and **the same environment variables** as the web service. Command: `flask --app "app:create_app" run-daily`. Schedule: `0 6 * * *` (Render uses UTC; that's 06:00 in Accra) |
| Web app (`tabital_front`) | Build: `npm ci --legacy-peer-deps && npm run build`. Publish directory: **`dist/tabital-app`**. Add a rewrite rule `/*` → `/index.html` (the app uses real paths such as `/customer/payment-callback`; without the rule, Paystack's return page is a 404) |

## Environment variables (Render → web service → Environment)
Every variable the API reads is in `app/config.py`. Defaults in brackets.

**Must be set:**

| Variable | Value / note |
|---|---|
| `DATABASE_URL` | the (rotated) PostgreSQL URL. `postgres://` is accepted and converted |
| `SECRET_KEY` | the new key. The API refuses to start without it |
| `CORS_ORIGINS` | the web app's address(es), comma separated [`http://localhost:4200,https://app.tabitalpay.com`]. Remove `localhost` in production |
| `FRONTEND_URL` | the web app's address, e.g. `https://app.tabitalpay.com` [`http://localhost:4200`]. Used in merchant payment links and QR codes |
| `TRUSTED_PROXY_COUNT` | **1** on Render [1]. The sign-in limits read the client address from the last `X-Forwarded-For` hop Render adds. Check once: sign in, then look at `login_attempts.ip`: it must be your own public address, not a Render or Cloudflare one. If Cloudflare is ever put in front, set **2**. If nothing is in front, **0** |
| `PAYSTACK_SECRET_KEY` | `sk_live_…` here only, never in files. Without it, online payment is switched off |
| `PAYSTACK_PUBLIC_KEY` | `pk_live_…` (not used by the server yet) |
| `PAYSTACK_CALLBACK_URL` | `https://<web app>/customer/payment-callback` [`http://localhost:4200/customer/payment-callback`] |
| `SMS_PROVIDER` | **`mnotify`**. The default `log` only writes messages to the server log: no customer gets an SMS |
| `MNOTIFY_API_KEY` | from the mNotify dashboard |
| `MNOTIFY_SENDER_ID` | [`TabitalPay`]. 11 characters or fewer, and **registered and approved** in mNotify first |
| `SMILEID_PARTNER_ID`, `SMILEID_API_KEY` | from Smile ID (production keys) |
| `SMILEID_BASE_URL` | `https://api.smileidentity.com` [`https://testapi.smileidentity.com`, the sandbox] |
| `SMILEID_CALLBACK_URL` | `https://<api>/webhooks/smileid` [not set] |
| `MAIL_USERNAME`, `MAIL_PASSWORD` | the mailbox that sends password-reset emails |

**Check the default is right:**

| Variable | Default | Note |
|---|---|---|
| `FLASK_DEBUG` | `0` | Leave unset. Never `1` in production |
| `MAIL_SERVER` | `smtp.gmail.com` | |
| `MAIL_PORT` | `587` | |
| `MAIL_USE_TLS` | `True` | Written exactly `True` or `False` (capital T/F). `true` counts as off |
| `MAIL_USE_SSL` | `False` | Same spelling rule |
| `MAIL_DEFAULT_SENDER` | `MAIL_USERNAME` | e.g. `info@tabitalpay.com` |
| `TERMS_URL` | `https://tabitalpay.com/elementor-page-3332/` | |
| `TERMS_VERSION` | `2026-09-26` | Each order records it. Change it whenever the Terms page changes (for example after the support email fix) |
| `PRIVACY_POLICY_URL` | `https://tabitalpay.com/privacy-policy/` | The page has no text yet (see `docs/remaining_items.md`) |
| `JWT_ACCESS_MINUTES` | `60` | How long a sign-in lasts |
| `JWT_REFRESH_DAYS` | `7` | |
| `PAYSTACK_BASE_URL` | `https://api.paystack.co` | |
| `MNOTIFY_BASE_URL` | `https://api.mnotify.com/api` | |

**Guessing limits (optional):** `LOGIN_MAX_FAILURES` (5), `LOGIN_MAX_ACCOUNTS_PER_IP` (20),
`LOGIN_WINDOW_MINUTES` (15), `OTP_MAX_FAILURES_PER_DAY` (10), `OTP_MAX_ACCOUNTS_PER_IP` (10),
`SIGNUP_MAX_FAILURES_PER_IP` (10), `RESET_REQUESTS_PER_IP_PER_HOUR` (10),
`RESET_CODES_PER_ACCOUNT_PER_DAY` (10).

`HOST` and `PORT` are only read by `python run.py` (local development). Gunicorn on Render doesn't
use them.

## Database (every deploy)
5. `flask --app "app:create_app" db upgrade`. The API won't start on an old schema (it crashes on a
   missing column). Run it as soon as the new code is on Render; expect errors until it has run.
6. `flask --app "app:create_app" db current` must print `f8a5d2e3c7aa (head)`.
7. First deploy only: `flask --app "app:create_app" ledger-backfill --dry-run`, read the output (it
   lists plans with no stored merchant payout), then `flask --app "app:create_app" ledger-backfill`.

## Data migration: "I've paid" claims (first deploy)
Migration `f8a5d2e3c7aa` finds instalments that customers marked "pending verification" under the old
"I've paid" button (Payment 1 excluded). It turns each one into a **payment claim** for staff to
check, and puts the instalment back to `pending`, or `overdue` if its due date has passed.

The daily job doesn't look at claims. So the **first `run-daily` after this migration can charge late
fees** on those instalments (10% the day after the due date, another 10% at 31+ days, within the 25%
cap), move them into collections, and mark plans more than 90 days past due as `defaulted`.

8. **Before the first daily run**, a manager clears the claims queue: Admin → **Collections** →
   "Payments customers say they made". For each one, check the MoMo or bank statement, then
   **Money arrived** (records it, part or full) or **Not found**. Only Management Access can do this.
9. Until the queue is clear, keep the cron job paused, and nobody presses "Run daily servicing now"
   (Admin → Disputes).

## People
10. `flask --app "app:create_app" create-admin --phone <phone> --name "<name>" --management` for the
    first manager. It asks for the password twice (never type it on the command line). Other admins
    start as Operations; managers change access on Settings → Team and access. From the server:
    `flask --app "app:create_app" set-admin-access --phone <phone> --level management` (or
    `operations`).
11. **Check every admin on Settings → Team and access.** Migration `a3b0e6f7d2bb` gave every existing
    admin account Management Access. The old sign-up (before Phase 0) could create admin accounts, so
    the production database may have admins nobody created on purpose. Set anyone you don't know to
    Operations or suspend them.

## Jobs and webhooks
12. Turn on the cron job (see "Render services"): `flask --app "app:create_app" run-daily` at `0 6 * * *`
    (late fees, days past due, collections stage, reminders, autopay, settlement batches). Only after
    step 8.
13. Paystack dashboard (live mode) → Settings → API Keys & Webhooks: webhook URL
    `https://<api>/webhooks/paystack`. Leave the callback URL blank (the app sends it). Enable
    transfers, keep a funded GHS balance, and turn off OTP for API transfers (`docs/settlements.md`).
    The webhook handles `charge.success`, `transfer.success`, `transfer.failed` and `transfer.reversed`.
14. Smile ID dashboard: callback URL `https://<api>/webhooks/smileid`. Ask Smile ID to enable Ghana,
    and confirm the Ghana Card `id_type` (setting `smileid_ghana_id_type`, default `GHANA_CARD`;
    `docs/identity_fraud.md`).

## Frontend (every deploy)
15. `npm run build` (runs `ng build`; production is the default configuration). Deploy
    **`dist/tabital-app`**. The production build uses `src/environments/environment.prod.ts`, whose
    `apiUrl` is `https://tabital.onrender.com`. If the API has another address, change that file,
    commit and push it, then build.

## Smoke test (after the deploy)
16. `flask --app "app:create_app" db current` prints `f8a5d2e3c7aa (head)`.
17. Open the web app and sign in as the manager. The dashboard loads with no errors (a CORS mistake
    shows up here as empty pages).
18. Sign in as an Operations admin. Check they can't approve, reveal personal data or export. They get
    "This needs Management Access".
19. Refresh the browser on a deep page such as `/customer/dashboard`. It must load the app, not a 404
    (the rewrite rule).
20. One real Smile ID check with a staff member's Ghana Card, on a staff test customer account: the
    result arrives through the callback. Customers can't buy until this passes.
21. Live money, small amounts: with that test customer, place two test orders with a live card or
    MoMo. Approve one; reject the other and check the refund in Paystack. Both should show as paid
    before approval (Paystack verified the down payment).
22. As a merchant, create a payment link. The link must start with your `FRONTEND_URL`, not `localhost`.
23. Ask for a password reset on a staff account. The email arrives.
24. After the first daily run, check Render's cron log (it prints a summary). Due reminders must
    reach a staff test customer's phone by SMS. If they don't, the message log is at
    `GET /admin/messages` (there's no screen for it yet): SMS must show provider `mnotify`, not `log`.
25. Turn Auto-Deploy back on if you want it.
