# Git push checklist (go-live review item 6)

This is for pushing both repos to GitHub (`Kobydon/tabital` and `Kobydon/tabital_front`) from this
computer, with your own GitHub login. Do the sections in order. Every command is PowerShell.

Open PowerShell and make Git available first (every new window):

```powershell
$env:Path = "C:\Program Files\Git\cmd;" + $env:Path
$root = "C:\Users\LENOVO\Desktop\Tabital APP  Review by Claude Code"
```

## Where things stand (checked 2026-09-27)

Both repos have the same shape: local `main` is the same commit as GitHub `main`, and nine phase
branches are stacked on top of it, each one containing the one before. Nothing is pushed yet.

| | `tabital` (API) | `tabital_front` (web app) |
|---|---|---|
| `main` = `origin/main` | `b25c78c` (2026-06-09) | `bc298cd` (2026-06-09) |
| Current branch | `phase7-unit-economics` (`0b7d26b`) | `phase7-unit-economics` (`82b5909`) |
| Commits to push (`main..phase7-unit-economics`) | **42** | **29** |
| Uncommitted changes / stashes | none | none |
| Merge commits in the new work | none | none |

New commits on each branch (compared with the branch before it):

| Branch | `tabital` | `tabital_front` |
|---|---|---|
| `phase0-security` | 3 | 2 |
| `phase1-ledger` | 2 | 1 |
| `phase2-paystack` | 2 | 2 |
| `phase3-underwriting` | 7 | 1 |
| `phase4-servicing` | 3 | 1 |
| `phase5-settlements` | 2 | 1 |
| `phase6-identity-fraud` | 2 | 1 |
| `phase6b-deferment` | 1 | 1 |
| `phase7-unit-economics` | 20 | 19 |

- Every branch is a descendant of the one before it, and of `main`. None is behind.
- So `main` **can be fast-forwarded** to `phase7-unit-economics`: no merge is needed, and every
  commit keeps its hash.
- One caveat: "`main` = `origin/main`" is what this computer last saw from GitHub, when the repos
  were cloned on 2026-09-25. Section c checks GitHub again before you push.

## a. Stop first: rotate the database passwords

Two Render database passwords are readable on GitHub `main` **today**, in the current
`app/config.py`: the databases whose host starts `dpg-d7t11…` and `dpg-d8aki…`. A third
(`dpg-d888…`) is in the history only. `docs/secrets_rotation.md` has the details.

1. Reset those passwords in the Render dashboard now (Render → the database → Info → Reset password,
   or delete databases you no longer use). Then update `DATABASE_URL` on the web service.
2. Do this **before** pushing. It's the only step that makes the old passwords useless.

Pushing and merging takes the passwords out of `main`'s **current** files. It does **not** take them
out of the **history**: anyone can still open an old commit on GitHub and read them. That's why
rotating comes first, whatever you decide in section b.

## b. The history decision (go-live review item 5, your call)

The old commits on GitHub `main` hold three things that shouldn't be there:

| What | Where in the history |
|---|---|
| Database URLs with passwords (3 Render databases) | `app/config.py`, from 2026-05-05 until the Phase 0 commit `656a730` |
| `instance/app.db`, a SQLite database file | added 2026-05-05, changed up to 2026-05-24, removed in `656a730`. Nobody has checked what's in it; it may hold accounts or personal data |
| `.env` | added 2026-05-05, removed in `656a730`; it was empty both times |

`tabital_front` has none of these.

You have two options.

### Option 1: push as it is

- Simple. Nothing changes for anyone.
- The passwords and `app.db` stay readable in old commits for as long as the repo exists.
- That's acceptable **only** once the passwords are rotated (section a), and only if `app.db` holds
  nothing personal. If it does, or if the exposed databases held real customer data, that's a Data
  Protection Commission question.

### Option 2: rewrite the history first, with `git filter-repo`

`git filter-repo` rebuilds every commit without the removed files and with the passwords replaced
by a marker. What that involves:

- **Every commit hash changes** from the first bad commit (2026-05-05) onward. That's almost all of
  `main`'s history and all 42 new commits.
- **GitHub `main` has to be force-pushed**, and branch protection (if any) must allow it. Render
  deploys from `main`, so the force-push can start a deploy (see section e).
- **Everyone who has a copy has to re-clone.** Old clones can't be pulled into the new history.
- **The bundles in `handoff/` stop matching.** They need `b25c78c` / `bc298cd`, which no longer
  exist after the rewrite. They'd have to be made again.
- Commit hashes quoted in the docs (for example in `secrets_rotation.md`) no longer match.
- It doesn't remove copies that already exist: other people's clones, forks, and pages GitHub has
  cached. GitHub Support can be asked to purge cached views. **Rotating is still what protects you.**

**If you choose option 2, do it before pushing anything, and before opening any pull request.**
Once the phase branches are pushed, the old commits exist in ten branches on GitHub, and every pull
request creates a reference (`refs/pull/…`) that GitHub keeps and you can't delete yourself. A
rewrite after that means force-pushing every branch and redoing the pull requests, and the old
commits stay reachable through those references.

Don't run it until you've decided. If you do choose it, ask the engineer to run it with you. For
the record, it looks like this (on a copy, never on the only copy):

```powershell
python -m pip install git-filter-repo          # a separate tool, not part of Git
git clone --mirror "$root\tabital" "$root\tabital-rewrite.git"
Set-Location "$root\tabital-rewrite.git"
# replacements.txt: one line per old password, written like  <old password>==>REMOVED
# Keep it OUTSIDE every repo, and delete it afterwards.
git filter-repo --invert-paths --path instance/app.db --path .env --replace-text "$root\..\replacements.txt"
```

Then check the result, force-push `main` and push the branches from the rewritten copy, and make
new bundles.

## c. Pre-push checks

Run these in **each** repo. Stop and ask if any check fails.

### 1. The working tree is clean, and GitHub hasn't moved

```powershell
Set-Location "$root\tabital"          # later: "$root\tabital_front"
git status --short                     # must print nothing
git stash list                         # must print nothing
git branch --show-current              # phase7-unit-economics
git fetch origin                       # asks for your GitHub login if needed
git rev-list --left-right --count origin/main...main
```

The last command must print `0	0`. If the first number isn't 0, someone pushed to GitHub `main`
after 2026-09-25: stop and ask the engineer, because a fast-forward is then no longer possible.

### 2. The branches are still stacked

```powershell
$branches = "main","phase0-security","phase1-ledger","phase2-paystack","phase3-underwriting",
            "phase4-servicing","phase5-settlements","phase6-identity-fraud","phase6b-deferment",
            "phase7-unit-economics"
for ($i = 1; $i -lt $branches.Count; $i++) {
    git merge-base --is-ancestor $branches[$i-1] $branches[$i]
    $ok = if ($LASTEXITCODE -eq 0) { "OK" } else { "NOT STACKED" }
    "{0} -> {1}: {2}" -f $branches[$i-1], $branches[$i], $ok
}
git rev-list --count origin/main..phase7-unit-economics      # tabital 42, tabital_front 29
```

Every line must say `OK`.

### 3. Backend tests pass (`tabital` only)

```powershell
Set-Location "$root\tabital"
& .venv\Scripts\python.exe -m pytest -q
```

The last line must say `passed`, with no `failed` or `error`.

### 4. The production build is clean (`tabital_front` only)

```powershell
Set-Location "$root\tabital_front"
$env:Path = "C:\Program Files\nodejs;" + $env:Path
npm ci --legacy-peer-deps              # only if node_modules is missing or out of date
npm run build                          # runs `ng build`; production is the default
```

It must finish without an `Error:` line. The output goes to `dist/tabital-app`, which git ignores.

### 5. No secret files are tracked

```powershell
git ls-files | Select-String -Pattern '(^|/)\.env$', '\.db$', '\.sqlite3?$', '^instance/'
```

Must print nothing. (`.env.example` is allowed; it only has placeholders.) Then check that
`.gitignore` covers them:

```powershell
git check-ignore -v .env instance/app.db app.db     # tabital: each line names the .gitignore rule
```

In `tabital` this prints the rules for `.env`, `instance/` and `*.db`. `tabital_front` has no
`.env` or database files; its `.gitignore` covers `/dist` and `/node_modules`.

### 6. Scan for secret-looking strings (file names only, never values)

```powershell
$pat = '(postgres(ql)?://[^:@/ ]+:[^@/ ]+@)|(sk_live_[0-9A-Za-z]{10,})|(pk_live_[0-9A-Za-z]{10,})|(sk_test_[0-9A-Za-z]{20,})|(AKIA[0-9A-Z]{16})|(BEGIN [A-Z ]*PRIVATE KEY)|((PASSWORD|SECRET|API_KEY|TOKEN)[A-Z_]*\s*=\s*[''"][^''"]{8,}[''"])'
# Files at the tip of the branch you'll push
git grep -l -I -i -E $pat phase7-unit-economics
# Commits being pushed whose changes touch such a string (hash and file name only)
git log -i -G $pat --format="commit %h" --name-only origin/main..phase7-unit-economics
```

`-l` and `--name-only` print only names. Don't drop them: without them git prints the matching
lines, secrets included.

What you should see (checked 2026-09-27):

- `tabital`, first command: only `phase7-unit-economics:.env.example`. That's the placeholder
  database URL, not a real one.
- `tabital`, second command: only `commit 656a730` with `.env.example` and `app/config.py`. That's
  the Phase 0 commit that **removed** the passwords from `app/config.py`.
- `tabital_front`: nothing from either command.

Anything else: stop, and don't push until someone has looked at that file.

## d. How to push

Only you can push: nobody else has credentials for `Kobydon`. The first push opens a GitHub sign-in
window (Git Credential Manager). Sign in there; never paste a password or token into a file.

**Recommended:** push all nine phase branches (so each phase can be reviewed on its own), open
**one** pull request `phase7-unit-economics` → `main` to look at, and only put it on `main` once the
deploy checklist is ready (section e). Pushing the phase branches doesn't change `main`, so it
doesn't deploy anything.

For each repo:

```powershell
Set-Location "$root\tabital"          # then again with "$root\tabital_front"
git push origin phase0-security phase1-ledger phase2-paystack phase3-underwriting phase4-servicing phase5-settlements phase6-identity-fraud phase6b-deferment phase7-unit-economics
```

Don't push `main` here. Then open the pull request in the browser:

- https://github.com/Kobydon/tabital/compare/main...phase7-unit-economics
- https://github.com/Kobydon/tabital_front/compare/main...phase7-unit-economics

It should list 42 commits (`tabital`) and 29 commits (`tabital_front`).

Opening a pull request per phase (each against the branch before it) also works, but it's nine pull
requests per repo that must be merged in order. One pull request is simpler.

### Putting the work on `main` (only when section e says so)

A fast-forward is possible (section "Where things stand"). Two ways:

- **Fast-forward from the terminal (keeps every hash, matches the bundles):**
  ```powershell
  git push origin phase7-unit-economics:main
  git fetch origin main:main            # moves your local main to the same commit
  ```
  GitHub then marks the pull request as merged by itself.
- **GitHub's "Create a merge commit" button:** keeps every commit, adds one merge commit on top.

Don't use **Squash and merge** (it throws away the phase history) or **Rebase and merge** (it
changes every hash, so the bundles stop matching).

### Pushing from another computer, with the bundles

`handoff\` holds one bundle per repo and phase (`<repo>-phaseN-*.bundle`, each = `main..<branch>`).
All of them check out as valid. **But the two `phase7-unit-economics` bundles are one commit behind
the branch:**

| Bundle | Bundle tip | Branch tip | Missing commit |
|---|---|---|---|
| `tabital-phase7-unit-economics.bundle` | `ee4e2cc` | `0b7d26b` | Deferment fee is 10% of what's still owed |
| `tabital_front-phase7-unit-economics.bundle` | `da07d9f` | `82b5909` | Deferment wording |

The phase 0–6b bundles match their branches. Remake the phase 7 bundles on **this** computer
before using them anywhere else:

```powershell
Set-Location "$root\tabital"
git bundle create "$root\handoff\tabital-phase7-unit-economics.bundle" main..phase7-unit-economics
Set-Location "$root\tabital_front"
git bundle create "$root\handoff\tabital_front-phase7-unit-economics.bundle" main..phase7-unit-economics
git bundle list-heads "$root\handoff\tabital_front-phase7-unit-economics.bundle"   # 82b5909…
```

On the other computer (copy the `handoff` folder there first):

```powershell
git clone https://github.com/Kobydon/tabital.git
Set-Location tabital
$h = "D:\handoff"                      # wherever you copied it
git bundle verify "$h\tabital-phase7-unit-economics.bundle"      # must say "is okay"
foreach ($b in "phase0-security","phase1-ledger","phase2-paystack","phase3-underwriting",
               "phase4-servicing","phase5-settlements","phase6-identity-fraud","phase6b-deferment",
               "phase7-unit-economics") {
    git fetch "$h\tabital-$b.bundle" "${b}:${b}"
}
git log --oneline -1 phase7-unit-economics                         # 0b7d26b
```

Same for `tabital_front` (clone `Kobydon/tabital_front`, bundles `tabital_front-*.bundle`, tip
`82b5909`). Then run section c and push as above.

`git bundle verify` fails with "requires this ref" if GitHub `main` no longer contains `b25c78c`
(`tabital`) or `bc298cd` (`tabital_front`), for example after a history rewrite.

## e. After the push

1. **Check GitHub has exactly what you have.** For each repo:
   ```powershell
   git ls-remote --heads origin
   git rev-parse phase7-unit-economics
   ```
   GitHub's `phase7-unit-economics` must be the same hash (`0b7d26b…` for `tabital`, `82b5909…` for
   `tabital_front`). The branches page on GitHub shows all nine phase branches.
2. **Warning: Render deploys from `main`, and may do it by itself.** If the Render services have
   Auto-Deploy on (the Render default), the moment `main` changes, Render builds the new code. The new
   API **won't start on the old database** (it needs `flask db upgrade`), and it needs the new
   environment variables. So before `main` changes:
   - finish the "Before anything else" and "Environment variables" parts of `docs/deploy_checklist.md`;
   - turn Auto-Deploy off (Render → service → Settings → Auto-Deploy) until you're ready, or plan the
     merge for a quiet time with the deploy steps ready to run straight away.
3. **After `main` is updated,** check that GitHub `main` no longer has the passwords or the old files
   in its current version:
   ```powershell
   git fetch origin
   git grep -l -I -i -E "postgres(ql)?://[^:@/ ]+:[^@/ ]+@" origin/main       # must print nothing
   git ls-tree -r --name-only origin/main | Select-String '^instance/', '^\.env$'   # must print nothing
   ```
   (Unless you chose option 2, they're still in the history. That's expected.)
4. Then follow `docs/deploy_checklist.md` from "Database".
