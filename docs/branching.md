# Branching model and promotion ritual

ZedApply uses a **two-branch promotion gate** so production (`master`) only receives changes that have already shipped to staging (`develop`).

## Branches

| Branch | Role | Deploys to |
| --- | --- | --- |
| `master` | Production. Locked. | `zedapply.com`, `api.zedapply.com` |
| `develop` | Staging integration branch. Default for new PRs. | `preview.zedapply.com`, `staging-api.zedapply.com` |
| `feature/*`, `fix/*`, `chore/*` | Short-lived work branches | Vercel preview URL per PR (ephemeral) |

### Rules

1. All feature work branches from **`develop`**, not `master`.
2. Open PRs against **`develop`** first. CI must pass; Vercel preview deploys for visual review.
3. Production promotion is **`develop` → `master`** only (PR #2, owner review).
4. Do not force-push or delete `master` or `develop`.

## GitHub setup (one-time)

Run from a machine with `gh` authenticated as a repo admin:

```bash
# 1. Create develop from master (if it does not exist yet)
git checkout master && git pull
git checkout -b develop && git push -u origin develop

# 2. Default branch → develop (new PRs target staging)
gh api repos/KaluMuso/zed-cv -X PATCH -f default_branch=develop

# 3. Protect master — PRs only, CI required, no direct pushes
gh api repos/KaluMuso/zed-cv/branches/master/protection -X PUT \
  -f required_status_checks='{"strict":true,"contexts":["enforce-promotion-from-develop","backend-test","openapi-ts-guard","frontend-build","guards"]}' \
  -F enforce_admins=true \
  -F required_pull_request_reviews='{"required_approving_review_count":1}' \
  -F restrictions='{"users":[],"teams":[],"apps":[],"enforce_admins":false}' \
  -F allow_force_pushes=false \
  -F allow_deletions=false

# 4. Require the promotion guard on master (see "How the promotion guard works" below)
#    Add check name: enforce-promotion-from-develop

# 5. Protect develop — PR + CI, squash merge only
gh api repos/KaluMuso/zed-cv/branches/develop/protection -X PUT \
  -f required_status_checks='{"strict":true,"contexts":["backend-test","openapi-ts-guard","frontend-build","guards"]}' \
  -F enforce_admins=false \
  -F required_pull_request_reviews='{"required_approving_review_count":0}' \
  -F allow_force_pushes=false \
  -F allow_deletions=false
```

In the GitHub UI, also enable for **`develop`**: **Allow squash merging** only (disable merge commits and rebase merge if you want a linear staging history).

> **Note:** Exact required status check names must match what appears on a green PR after CI runs once. Adjust the `contexts` array if job names differ (e.g. `drift-guards` workflow job is named `guards`).

## How the promotion guard works

GitHub Rulesets that restrict merge sources (e.g. “only `develop` may target `master`”) require **GitHub Team** on private repositories. As a free-tier workaround, we enforce the promotion ritual with [`.github/workflows/promotion-guard.yml`](../.github/workflows/promotion-guard.yml).

On every pull request targeting `master`, the `enforce-promotion-from-develop` job runs. If the PR head branch is not `develop`, the job fails and blocks merge. If the head branch is `develop`, the job passes.

Combined with **Require status checks to pass before merging** on `master` (classic branch protection), this prevents direct feature → `master` merges without paying for Team. After the workflow has run once on a PR, add **`enforce-promotion-from-develop`** to the required checks list for `master` (Settings → Branches → Branch protection rules → `master` → edit → Status checks).

## Promotion ritual

### Stage 1 — feature → develop

1. Branch from `develop`: `git checkout develop && git pull && git checkout -b feature/my-change`
2. Implement, push, open PR **into `develop`**.
3. Wait for CI (`.github/workflows/ci.yml`, `schema_guard.yml`, `frontend_tests.yml` when applicable).
4. Merge (squash on `develop` if that is the team convention).
5. Verify automatic deploy to **`preview.zedapply.com`** (Vercel **Preview** env scoped to `develop`).
6. Smoke-test on staging API: `curl -sS https://staging-api.zedapply.com/api/v1/health | jq`

### Stage 2 — develop → master (production)

1. Open PR **`develop` → `master`** (Kaluba approval required).
2. Complete [promotion_checklist.md](./promotion_checklist.md).
3. Ensure migrations were applied on **staging Supabase** before merging.
4. Merge PR; Vercel production + OCI production deploy from `master`.
5. Post-deploy: `curl -sS https://api.zedapply.com/api/v1/health | jq`
6. Run `python scripts/production_audit.py --env production` from the OCI host or CI secrets context.

### Emergency hotfix

If production is broken and staging is far ahead:

1. Branch `fix/hotfix-…` from **`master`**, fix, PR into **`master`** (requires admin bypass or temporary rule change — use sparingly).
2. Cherry-pick or merge the hotfix back into **`develop`** immediately so branches do not diverge.

## Related docs

- [staging.md](./staging.md) — URLs, keys, Vercel/Supabase/OCI setup
- [promotion_checklist.md](./promotion_checklist.md) — pre-merge checklist template
- [runbook.md](./runbook.md) — staging stack recovery
