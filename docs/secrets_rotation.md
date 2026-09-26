# Secrets rotation (go-live review item 4)

Scanned on 2026-09-27: every commit on every branch of this repo, all files except `*.db`, images and
migrations, for Paystack keys, database URLs with passwords, mail passwords, app/JWT secrets, API
keys/tokens and AWS keys. Values were never printed during the scan.

## What was exposed

| Where | What | Commits |
|---|---|---|
| `app/config.py` | **Database URLs with real passwords** for three Render PostgreSQL databases: hosts starting `dpg-d7t11rjbc2fs73d814q0-a`, `dpg-d888ooek1jcs73eeo6fg-a` and `dpg-d8aki10jo6nc73eqap4g-a` (all `oregon-postgres.render.com`) | f5e7203, 667c9fa (removed in 656a730, Phase 0) |
| `.env.example` | A placeholder URL (`user:password@HOST/DBNAME`) — not a secret | — |

Nothing else matched: no Paystack secret keys, mail passwords, JWT/Flask secret keys or other API
keys were ever committed. The current code reads every secret from environment variables.

## What to do (Render dashboard, account owner)

1. For **each** of the three databases above:
   - If it's still in use: Render → the database → **Info → Reset password** (or create a new user),
     then update the `DATABASE_URL` environment variable of the web service and redeploy.
   - If it isn't used any more: **delete it** (after taking a backup if it might hold real data).
2. Check the database logs / connections for access you don't recognise since the first commit.
3. Treat any data in those databases as possibly seen by anyone who could read the repo. If real
   customer data was ever stored there, that's a Data Protection Commission question (see item 5,
   waiting for the founder).
4. Generate a fresh `SECRET_KEY` for production (`python -c "import secrets; print(secrets.token_urlsafe(64))"`)
   and set it in Render. Changing it signs everyone out once; do it before go-live.
5. Paystack, Smile ID and mNotify keys were never committed, but only put **live** keys into Render
   environment variables, never into files.

Rotating makes the old passwords useless even though they stay in the git history. Removing them
from history (rewriting it) is part of item 5 and needs the founder's decision.
