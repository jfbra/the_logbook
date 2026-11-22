# Protect `master` with a ruleset

One-off GitHub settings steps (issue #23). They need repository admin rights, so a person does them in the browser. Repository: `jfbra/the_logbook`.

**Prerequisite:** the CI workflow must have run at least once on a pull request, or its checks can't be picked as required. The checks are:

- `Lint, types and tests`
- `Production image builds`

## 1. Replace the classic rule with a ruleset

- [ ] Settings → Branches → delete the classic branch protection rule on `master`.
- [ ] Settings → Rules → Rulesets → New ruleset → New branch ruleset.
- [ ] Name: `Protect master`. Enforcement status: **Active**.
- [ ] Target branches → Add target → Include default branch.

## 2. Rules

- [ ] **Restrict deletions**: on.
- [ ] **Block force pushes**: on.
- [ ] **Require a pull request before merging**: on, **Required approvals: 0**.
- [ ] **Require status checks to pass**: on. Add `Lint, types and tests` and `Production image builds`. If a check isn't offered, it hasn't run yet. Open a PR first.

## 3. Owner bypass

- [ ] Bypass list → Add bypass → Repository admin (or yourself) → set mode to **For pull requests only**. Never "Always allow": that would permit direct pushes.
- [ ] Create the ruleset.

## 4. Auto-delete merged branches

- [ ] Settings → General → Pull Requests → tick **Automatically delete head branches**.

## 5. Verify

Use a throwaway branch and PR. Don't skip this: a ruleset that looks right can still not apply.

- [ ] A PR with a red required check cannot be merged (without bypassing).
- [ ] A PR with all checks green can be merged.
- [ ] `git push origin master` from a local commit is rejected.
- [ ] `git push --force origin master` is rejected.
- [ ] After merging a PR, its branch is gone from the remote.

## Verification record

Run on 2026-11-22 against ruleset "Protect master" (PR #36 was the throwaway PR):

- Red required check: merge blocked (`mergeStateStatus: BLOCKED`).
- All checks green: merge allowed.
- Direct push to `master`: rejected.
- Force push to `master`: rejected.
- Merged PR branch auto-deleted.

## Notes

- The checks are matched by name. If the ruleset UI shows them as `CI / Lint, types and tests`, pick that form. The research in `docs/research/ci-cd.md` couldn't confirm which one applies.
- The ruleset UI offers rulesets on this repo's plan, per the same research. If it doesn't, stop and report back.
