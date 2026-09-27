# Putting the finished work on `main` (both repos)

This guide is for you, the founder. You run it yourself in PowerShell on Windows, with your own
GitHub login. It covers `tabital` (the API) first, then `tabital_front` (the web app).

It builds on three other documents. It doesn't repeat them, so keep them open:

- `docs/secrets_rotation.md`: the database passwords that must be reset first.
- `docs/git_push_checklist.md`: the history decision (section b) and the pre-push checks (section c).
- `docs/deploy_checklist.md`: Render, which may deploy as soon as `main` changes.

Every hash and number below was checked on **2026-09-27**. If anything you see is different, stop
and ask the engineer.

> **Numbers as of 2026-09-27.** The backend count is 43 because this guide is itself the last commit. If you commit anything else before merging, re-run the counts in step 0 and use what they print.

## Where things stand (2026-09-27)

| | `tabital` (API) | `tabital_front` (web app) |
|---|---|---|
| GitHub address (`git remote -v`) | `https://github.com/Kobydon/tabital.git` | `https://github.com/Kobydon/tabital_front.git` |
| `main` = `origin/main` | `b25c78c` | `bc298cd` |
| `phase7-unit-economics` (the finished work) | run `git rev-parse --short phase7-unit-economics` | `fa44c71` |
| Commits to add to `main` | **43** | **29** |
| Can `main` simply move forward (fast-forward)? | Yes | Yes |
| Uncommitted changes | none | none |

The work sits on nine stacked branches. Each one contains the one before it:

| Branch | `tabital`: new commits, tip | `tabital_front`: new commits, tip |
|---|---|---|
| `phase0-security` | 3, `d98f3a6` | 2, `3c66c9a` |
| `phase1-ledger` | 2, `203122c` | 1, `4d4cdb9` |
| `phase2-paystack` | 2, `23ae735` | 2, `1abd8e0` |
| `phase3-underwriting` | 7, `5f7d374` | 1, `c30694c` |
| `phase4-servicing` | 3, `b7aef0d` | 1, `7eebfba` |
| `phase5-settlements` | 2, `2e4f689` | 1, `e71a067` |
| `phase6-identity-fraud` | 2, `d777239` | 1, `2d0017f` |
| `phase6b-deferment` | 1, `82921fa` | 1, `43f80a7` |
| `phase7-unit-economics` | 21 | 19, `fa44c71` |

Old files that GitHub `main` still has, and that the new work removes:

- `tabital`: `.env` (empty), `instance/app.db` (an old SQLite database), and 68 `*.pyc` files
  (Python cache files). Also the database passwords inside `app/config.py`.
- `tabital_front`: `dist.zip` (an old build of the web app). No secret files.

### One important warning: don't check out the old `main`

Don't run `git checkout main` in either repo **until `main` has moved forward**. The old `main`
still tracks `.env`, `instance/app.db` and `dist.zip`. Your computer has its own copies of those
files. Git would silently replace them with the old versions, and later delete them. Your local
`instance\app.db` is **not** the same as the one on GitHub (it holds your local test data), so you
would lose it.

This guide avoids that. It moves `main` forward without checking it out. Once `main` equals the
finished work, `git checkout main` is safe.

## Open PowerShell (every new window)

```powershell
$env:Path = "C:\Program Files\Git\cmd;" + $env:Path
$root = "C:\Users\LENOVO\Desktop\Tabital APP  Review by Claude Code"
```

---

## 0. Before you start: stop unless all of these are done

1. **The passwords are rotated.** Both database passwords that are readable on GitHub `main`
   today have been reset in Render. See `docs/secrets_rotation.md`. Merging does not make them
   safe: they stay in the old commits.
2. **The history decision is made** (`git_push_checklist.md` section b). If you chose to rewrite the
   history (option 2), that happens **before** this guide, with the engineer. After a rewrite, every
   hash in this guide is different, so don't use this guide as written.
3. **Render Auto-Deploy is off** on the API web service, the cron job, and the web app (Render →
   service → Settings → Auto-Deploy). Changing `main` can start a deploy by itself, and the new API
   won't start until its database is upgraded. See `docs/deploy_checklist.md`, "Before anything else".
4. **The pre-push checks passed** in both repos (`git_push_checklist.md` section c: clean tree,
   stacked branches, backend tests, frontend build, no secret files, secret scan).
5. **You have a backup.** Do one or both of these.

   A bundle of every branch, per repo (one file each, easy to keep):

   ```powershell
   $backup = "$root\..\tabital-backup-2026-09-27"
   New-Item -ItemType Directory -Force $backup
   Set-Location "$root\tabital";       git bundle create "$backup\tabital-all.bundle" --all
   Set-Location "$root\tabital_front"; git bundle create "$backup\tabital_front-all.bundle" --all
   ```

   A bundle only holds what git tracks. Also copy your local database and settings files, which git
   doesn't track:

   ```powershell
   Copy-Item -Recurse "$root\tabital\instance" "$backup\tabital-instance"
   Copy-Item "$root\tabital\.env" "$backup\tabital.env"
   ```

   Or simply copy the whole project folder somewhere else in File Explorer. That is the safest backup.

---

## 1. Recommended path: a pull request on GitHub

A pull request lets you see every change on GitHub before `main` moves. Do `tabital` first.

### 1.1 Check that GitHub hasn't moved

```powershell
Set-Location "$root\tabital"
git branch --show-current          # must print: phase7-unit-economics
git status --short                 # must print nothing
git fetch origin                   # may open a GitHub sign-in window
git rev-list --left-right --count main...origin/main
```

The last command must print `0	0` (zero, a gap, zero).

If it prints anything else, someone changed GitHub since the repos were copied here. **Stop and ask
for help.** Don't force anything.

### 1.2 Push the nine phase branches

This is one command, on one line:

```powershell
git push origin phase0-security phase1-ledger phase2-paystack phase3-underwriting phase4-servicing phase5-settlements phase6-identity-fraud phase6b-deferment phase7-unit-economics
```

This adds the branches to GitHub. It does **not** change `main`, so nothing deploys.

### 1.3 Open one pull request

Open this address in your browser:

https://github.com/Kobydon/tabital/compare/main...phase7-unit-economics

- "base" must be `main`. "compare" must be `phase7-unit-economics`.
- Click the button to create a pull request. Give it a title such as "Phases 0 to 7".

What you should see on the pull request page:

- **43 commits.**
- About **224 files changed**. In the list of files you should find:
  - `instance/app.db` removed;
  - many `__pycache__/….pyc` files removed (68 of them);
  - `.env` either removed or shown as "renamed" to `app/services/__init__.py`. Both files are
    empty, so GitHub may pair them up. Either way `.env` is gone;
  - `app/config.py` changed: the lines with the database passwords are removed.

GitHub's pages change from time to time. If a button has another name, look for the same idea.

### 1.4 Merge the pull request

**Only when you are ready to deploy** (Auto-Deploy off, `deploy_checklist.md` ready to follow).

At the bottom of the pull request, open the menu next to the merge button and choose:

- **"Create a merge commit"**. This keeps all 43 commits as they are and adds one merge commit.

Don't choose:

- **"Squash and merge"**: it squeezes the 43 commits into one, so the phase-by-phase history is lost.
- **"Rebase and merge"**: GitHub rewrites every commit when it rebases, so all the hashes change and
  no longer match your computer or the `handoff\` bundles.

(If you want `main` to end up with exactly the same hashes as your computer, use section 2 instead.)

### 1.5 Bring your computer up to date

Stay on `phase7-unit-economics`. This moves your local `main` to match GitHub without checking it
out (see the warning at the top):

```powershell
git branch --show-current          # must print: phase7-unit-economics
git fetch origin main:main
git merge-base --is-ancestor phase7-unit-economics main
$LASTEXITCODE
```

The last line must print `0`. That means `main` now contains all the finished work. (`1` means it
doesn't: stop and ask.)

From now on `git checkout main` followed by `git pull` is safe and does what you'd expect.

Now do section 3 (checks on GitHub) for `tabital`.

---

## 2. Alternative path: fast-forward from the command line (no pull request)

Because nothing on GitHub has moved (section 1.1 printed `0	0`), this gives exactly the same
result as a pull request, except that there is no merge commit: `main` becomes the finished tip itself.

Run section 1.1 first. Pushing the phase branches (1.2) is optional here.

```powershell
Set-Location "$root\tabital"
git branch --show-current                    # must print: phase7-unit-economics
git fetch . phase7-unit-economics:main       # move local main forward, without checking it out
git log --oneline -3 main
git push origin main
```

- `git fetch . phase7-unit-economics:main` does the same job as `git checkout main` followed by
  `git merge --ff-only phase7-unit-economics`, but it never checks out the old `main`, so your local
  files are safe. Like `--ff-only`, it **refuses** (with "non-fast-forward") rather than create a
  merge you didn't expect.
- `git log --oneline -3 main` must show the same code as `git rev-parse --short phase7-unit-economics` on the first line.
- `git push origin main` is refused by GitHub if GitHub moved in the meantime. That's the
  protection you want. Never add `--force`.

If you opened a pull request in section 1.3, GitHub marks it as merged by itself.

(`git_push_checklist.md` section d shows another way, `git push origin phase7-unit-economics:main`
then `git fetch origin main:main`. It gives the same result.)

---

## 3. Check GitHub after each repo

1. **The latest commit matches.** On your computer:

   ```powershell
   git rev-parse --short main
   ```

   On GitHub, open the repository's main page with `main` selected. The latest commit shown near the
   top must have the same short code. (Section 2: the tip printed by `git rev-parse --short phase7-unit-economics` for `tabital`, `fa44c71` for
   `tabital_front`. Section 1: the new merge commit.)

2. **`tabital` only: no passwords in `app/config.py`.** On GitHub, open `app/config.py` on `main`.
   Use the browser's search (Ctrl+F) for `postgresql`. You should find only one line, which
   replaces `postgres://` with `postgresql://`. There must be **no** address containing
   `render.com` or an `@`. Don't copy or paste anything from the old version anywhere.

3. **The old files are gone from `main`.** On GitHub's file list for `main`:
   - `tabital`: no `.env` file and no `instance` folder;
   - `tabital_front`: no `dist.zip`.

   From PowerShell, the same check (it prints only names, never values):

   ```powershell
   git fetch origin
   git ls-tree -r --name-only origin/main | Select-String '^instance/', '^\.env$', '\.pyc$', '^dist\.zip$'   # must print nothing
   ```

(The passwords and `app.db` are still in the old commits unless you rewrote the history. That's
expected, and why rotating came first.)

---

## 4. Then the web app repo (`tabital_front`)

Repeat sections 1 (or 2) and 3 in the other folder:

```powershell
Set-Location "$root\tabital_front"
```

What's different:

- Pull request address: https://github.com/Kobydon/tabital_front/compare/main...phase7-unit-economics
- It should show **29 commits** and about **226 files changed**. The file list includes the removal
  of `dist.zip`, and many old screen files (a big clean-up). There are no `.env`, database or
  `.pyc` files in this repo.
- The finished tip is `fa44c71`. The old `main` is `bc298cd`.
- In section 3, skip the `app/config.py` check.
- If the web app is also deployed from `main` on Render, the same Auto-Deploy warning applies.

---

## 5. Afterwards

- The phase branches on GitHub can stay, or be deleted later from GitHub's Branches page. It's
  optional; `main` already contains everything.
- The bundles in `handoff\` are no longer needed once both `main` branches are on GitHub. Keep your
  own backup from step 0 for a while.
- Now follow `docs/deploy_checklist.md` from "Database", and turn Auto-Deploy back on only after the
  smoke test.

---

## 6. If something goes wrong

**"rejected … (non-fast-forward)" or "fetch first"**
GitHub has commits your computer doesn't. Stop. Don't use `--force` and don't "pull and try
again". Ask for help.

**Sign-in problems ("Authentication failed", "403", "Permission denied")**
- Git for Windows includes Git Credential Manager: the first push opens a GitHub sign-in window in
  the browser. Sign in with the account that owns `Kobydon`.
- If it keeps failing, create a **personal access token** on GitHub (your profile → Settings →
  Developer settings → Personal access tokens), with access to the two repos, and use it as the
  password when asked. Never save it in a file, and never paste it into a chat.
- Or install **GitHub Desktop**, sign in there, and push from it.
- "Permission denied" can also mean you're signed in as a different GitHub user than `Kobydon`.

**Your local `main` moved to the wrong thing, and you have NOT pushed it yet**
Nothing on GitHub has changed, so this is safe to fix. Make sure you're not on `main`, then point
`main` back at GitHub's copy:

```powershell
git checkout phase7-unit-economics
git branch -f main origin/main
git rev-list --left-right --count main...origin/main     # must print 0	0 again
```

If you are already on `main`, the classic command is `git reset --hard origin/main`. Be careful: it
throws away every uncommitted change, and it puts the old `.env` and `instance/app.db` back over
your local copies. Back up the `instance` folder and `.env` first (step 0), and only ever use it
**before** pushing.

**`main` was already pushed and something is wrong**
Never rewrite `main` on GitHub (no `reset` plus `--force`). Undo it with a new change instead:
- if you merged with a pull request, its page has a **Revert** button that opens a new pull request
  undoing it; merge that;
- otherwise ask the engineer to prepare a revert on a branch and open a pull request.

Render deploys whatever is on `main`, so if a bad deploy started, use Render's "Rollback" to the
previous deploy while the revert is prepared.

---

## 7. Checklist

Before you start
- [ ] Both exposed database passwords reset in Render (`secrets_rotation.md`)
- [ ] History decision made; any rewrite done first (`git_push_checklist.md` b)
- [ ] Render Auto-Deploy off (API, cron job, web app)
- [ ] Pre-push checks passed in both repos (`git_push_checklist.md` c)
- [ ] Backup made: bundles and/or a copy of the folder, plus `tabital\instance` and `.env`
- [ ] I will not run `git checkout main` until `main` has moved forward

`tabital` (old `main` `b25c78c`, finished work = the tip printed by `git rev-parse --short phase7-unit-economics`, 43 commits)
- [ ] `git fetch origin`, then `main...origin/main` prints `0	0`
- [ ] Nine phase branches pushed (one command)
- [ ] Pull request `main` ← `phase7-unit-economics` shows 43 commits, `instance/app.db`, `.env` and the `.pyc` files removed
- [ ] Merged with "Create a merge commit" (never Squash, never Rebase) — or fast-forwarded (section 2)
- [ ] `git fetch origin main:main`, then `is-ancestor` prints `0`
- [ ] GitHub's latest commit matches `git rev-parse --short main`
- [ ] `app/config.py` on GitHub: no password URL; no `.env`, no `instance/` on `main`

`tabital_front` (old `main` `bc298cd`, finished work `fa44c71`, 29 commits)
- [ ] `git fetch origin`, then `main...origin/main` prints `0	0`
- [ ] Nine phase branches pushed
- [ ] Pull request shows 29 commits and `dist.zip` removed
- [ ] Merged with "Create a merge commit" — or fast-forwarded (section 2)
- [ ] `git fetch origin main:main`, then `is-ancestor` prints `0`
- [ ] GitHub's latest commit matches `git rev-parse --short main`; no `dist.zip` on `main`

Afterwards
- [ ] Follow `deploy_checklist.md` from "Database"
- [ ] Auto-Deploy back on after the smoke test (if wanted)
- [ ] Phase branches on GitHub: keep or delete later (optional)
