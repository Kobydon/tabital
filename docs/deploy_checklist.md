# Deploy checklist (Render)

Do these in order for the first go-live deploy, and check the ones marked (every deploy) each time.

## Before anything else
1. **Rotate the database passwords** listed in `docs/secrets_rotation.md`. Two are readable on
   GitHub `main` today.
2. Generate a new `SECRET_KEY` (`python -c "import secrets; print(secrets.token_urlsafe(64))"`).

## Environment variables (Render → web service → Environment)
| Variable | Value / note |
|---|---|
| `DATABASE_URL` | the (rotated) PostgreSQL URL |
| `SECRET_KEY` | the new key |
| `CORS_ORIGINS` | the web app's address(es), comma separated |
| `TRUSTED_PROXY_COUNT` | **1** on Render. The sign-in limits read the client address from the last `X-Forwarded-For` hop Render adds. Check once: sign in, then look at `login_attempts.ip`: it must be your own public address, not a Render or Cloudflare one. If Cloudflare is ever put in front, set **2**. If nothing is in front, **0** |
| `PAYSTACK_SECRET_KEY`, `PAYSTACK_PUBLIC_KEY` | live keys only here, never in files |
| `SMILEID_PARTNER_ID`, `SMILEID_API_KEY` | from Smile ID |
| `MNOTIFY_API_KEY` | SMS |
| Mail settings | for password-reset emails |
| Optional limits | `LOGIN_MAX_FAILURES` (5), `LOGIN_MAX_ACCOUNTS_PER_IP` (20), `LOGIN_WINDOW_MINUTES` (15), `OTP_MAX_FAILURES_PER_DAY` (10), `OTP_MAX_ACCOUNTS_PER_IP` (10), `SIGNUP_MAX_FAILURES_PER_IP` (10), `RESET_REQUESTS_PER_IP_PER_HOUR` (10) |

## Database (every deploy)
3. `flask db upgrade`: the app won't start on an old schema (it crashes on a missing column).
4. First deploy only: `flask ledger-backfill --dry-run`, read the output (it lists plans with no stored
   merchant payout), then `flask ledger-backfill`.

## People
5. `flask create-admin --phone <phone> --name "<name>" --management` for the first manager. Other
   admins start as Operations; managers change access on Settings → Team and access.

## Jobs and webhooks
6. A daily Render cron job: `flask run-daily` at 06:00 Africa/Accra (late fees, days past due,
   reminders, autopay).
7. Paystack dashboard: webhook URL `https://<api>/webhooks/paystack` (live mode).
8. Smile ID dashboard: callback URL `https://<api>/webhooks/smileid`.

## Frontend (every deploy)
9. `ng build` (production configuration, the default) and deploy `dist/`. `environment.prod.ts` points
   at the API address.

## After the deploy
10. Sign in as a manager and as an Operations admin; check the Operations admin can't approve, reveal
    personal data or export.
11. Place a GHS 1 test order with a live card, approve, reject, and check the refund in Paystack.
