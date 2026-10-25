# Git workflow

1. Make an issue / acceptance criteria.
2. `git switch -c feat/small-feature` from a known clean base.
3. Implement one component and corresponding tests.
4. Run lint, format check, unit tests, `git diff --check`.
5. Inspect `git status` and stage explicit source files.
6. Commit with a conventional message.
7. Review evidence and update the relevant milestone.

## Where changes go (decided 2026-10-25)

- **Straight to `main`:** docs, config and tiny fixes. Run `./scripts/check`, commit, push. CI runs on every push to `main`, but cannot block it (branch protection is unavailable on this plan), so check the result.
- **Branch plus pull request:** anything that changes algorithms, evidence, data handling or safety logic, and anything wanting independent review.

Never `git add .` before reviewing untracked ML artifacts and local paths.

For concepts, recovery and practice exercises see [[development/git_guide]].
