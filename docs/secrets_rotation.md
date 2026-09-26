# Secrets rotation (go-live review item 4)

Scanned on 2026-09-27: every commit on every branch of this repo, all files except `*.db`, images and
migrations, for Paystack keys, database URLs with passwords, mail passwords, app/JWT secrets, API
keys/tokens and AWS keys. Values were never printed during the scan.

## What was exposed

`app/config.py` held **database URLs with real passwords** for three Render PostgreSQL databases
(all `*.oregon-postgres.render.com`). They stay readable in the git history until it's rewritten, so
treat each password as exposed from the first commit below, and check access logs from that date.

| Database host | In the code (commits) | Exposed since |
|---|---|---|
| `dpg-d7t11rjbc2fs73d814q0-a` | added f5e7203 (2026-05-05); also in edbd895, 94cb154, 667c9fa, ecfad98, 8af2c91, ce4bfe1; removed 656a730 (2026-09-25, Phase 0) | 2026-05-05 |
| `dpg-d888ooek1jcs73eeo6fg-a` | added 8af2c91 (2026-05-22); also ce4bfe1; removed 8c683ef (2026-05-26) | 2026-05-22 |
| `dpg-d8aki10jo6nc73eqap4g-a` | added 8c683ef (2026-05-26); removed 656a730 (2026-09-25) | 2026-05-26 |

Also checked: `.env.example` only has a placeholder (`user:password@HOST/DBNAME`); a `.env` file was
committed in f5e7203 and removed in 656a730 but was empty both times, and `.env` is now gitignored;
the `tabital_front` history has no secrets.

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
