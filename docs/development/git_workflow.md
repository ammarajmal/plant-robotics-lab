# Git workflow

1. Make an issue / acceptance criteria.
2. `git switch -c feat/small-feature` from a known clean base.
3. Implement one component and corresponding tests.
4. Run lint, format check, unit tests, `git diff --check`.
5. Inspect `git status` and stage explicit source files.
6. Commit with a conventional message.
7. Review evidence and update the relevant milestone.

Never `git add .` before reviewing untracked ML artifacts and local paths.
