# Branching & Promotion

## Branch model

Two long-lived branches:

- **`develop`** — default branch. Staging/integration. All feature work merges here. Auto-deploys to `preview.zedapply.com`.
- **`master`** — production. Only receives merges from `develop`. Auto-deploys to `zedapply.com`.

Feature branches (`feat/...`, `fix/...`, `chore/...`) branch off `develop` and PR back into `develop`.

```
feature/X ──► develop ──► master
              (staging)   (production)
```

## Why this layout

- A single-branch flow (push to master) gave us no place to stage integration changes before production. Staging was simulated on feature branches, which didn't catch cross-feature interaction bugs.
- Two branches give us a real staging environment (`preview.zedapply.com`) populated by the same code path production will use, but one merge behind.
- Promotion to production becomes an explicit, reviewable PR (`develop → master`) rather than an implicit consequence of every merge.

## Rules

### Feature → develop
- Open a PR from your feature branch into `develop`.
- CI must pass (backend tests, frontend tests, drift guards).
- At least one review (self-review acceptable while team size = 1, but the PR template must be filled out).
- **Squash-merge only** (keeps `develop` history linear and `develop → master` diffs reviewable).

### develop → master (promotion)
- Open a PR with title `release: YYYY-MM-DD` (or similar).
- Complete the [promotion checklist](./promotion_checklist.md) in the PR body.
- CI must pass.
- Use a **merge commit** (not squash) so individual feature commits remain visible in `master` history.

### Forbidden
- Direct pushes to `master`. (See enforcement below.)
- Force-push or branch deletion on `master` or `develop`.
- PRs to `master` from any branch other than `develop`.

## Enforcement

GitHub native branch protection requires GitHub Pro or a public repo; this repo is private on the free plan. Instead we enforce via CI:

- **`.github/workflows/enforce-master-from-develop.yml`** fails any PR to `master` whose head is not `develop`, and fails any push to `master` whose HEAD is not reachable from `develop` (i.e. not a fast-forward, squash, or merge-from-develop).
- This is *after-the-fact* for pushes — it surfaces violations loudly but cannot reject the push at the server. If a direct push to `master` slips through, revert it and re-promote via `develop → master` PR.
- Force-push and deletion are not enforced — protect via convention and habit until the repo moves to Pro or public.

If/when the repo moves to GitHub Pro or becomes public, replace this CI gate with a real Ruleset:
- `master`: require PR, require status checks, block force-push, block deletion, restrict pushes.
- `develop`: require PR, require status checks, allowed merge methods = squash.

## Promotion ritual

```
feature/X ──► develop   (PR #1, reviewed, CI passes, auto-deploys to preview.zedapply.com)
develop  ──► master     (PR #2, reviewed, CI passes, auto-deploys to zedapply.com)
```

See [`docs/promotion_checklist.md`](./promotion_checklist.md) for the full pre-promotion checklist.

## FAQ

**Why not trunk-based with feature flags?**
We're not there yet — payment flows (Lenco, DPO), WAHA WhatsApp delivery, and Supabase migrations all have real external state. Staging on `develop` gives us a smoke-test window before that state hits production.

**Can I hotfix master directly?**
No. Branch off `develop`, fix, PR into `develop`, then promote `develop → master`. If `develop` has unshippable changes that block the hotfix, that's a sign `develop` shouldn't have been in that state — fix the broken thing on `develop` first.

**What if `develop` is broken and we need an emergency rollback on `master`?**
Revert the offending commit on `master` via a `revert: ...` PR from a branch off `master` itself. This is the one exception to "all changes flow through develop" — and the CI gate will fail on this PR. Override by adding the label `emergency-rollback` and merging anyway (you have admin override). Then cherry-pick the revert back to `develop` so the two branches reconverge.
