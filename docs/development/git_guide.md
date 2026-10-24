# Git guide for PRL

A learning and practice guide. The short project rules live in [[development/git_workflow]]; this page explains the *why* and gives exercises. Commands here were used on this repository unless marked "practice".

## 1. The mental model

- **Working tree**: the files you see and edit.
- **Staging area (index)**: the files you have chosen for the next commit. `git add <file>` puts a file here.
- **Commit**: a permanent snapshot with a message, an author and a parent. Commits form a chain (history).
- **Branch**: a movable label pointing at one commit. Making a branch is free; use one per change.
- **Remote**: another copy of the repository. Ours is `origin` on GitHub. `git push` sends commits to it; `git fetch` / `git pull` bring them back.
- **Stash**: a shelf for uncommitted work. `git stash list` shows it. PRL keeps one old stash, `stash@{0}`; do not drop it without a decision.

```
working tree --git add--> staging --git commit--> local branch --git push--> origin (GitHub)
```

## 2. Daily loop

```bash
git status                      # always first: where am I, what changed?
git switch main                 # start from a known base
git switch -c feat/small-thing  # one focused change per branch
# ... edit files ...
uv run pytest -q && uv run ruff check . && uv run ruff format --check . && git diff --check
git status
git add path/to/file1 path/to/file2   # explicit files; never `git add .`
git commit -m "feat(io): add a small thing"
git push -u origin feat/small-thing   # first push of a branch
```

Commit message format (Conventional Commits): `type(scope): summary`, with types `feat fix test docs chore refactor build`. Keep the summary short and in the imperative ("add", not "added").

## 3. Branches used in PRL

| Branch | Purpose | State |
|---|---|---|
| `main` | Accepted work only | On `origin` |
| `feat/prl-006-real-data-playback` | PRL-006, awaiting independent review | On `origin`, not merged |
| `feat/prl-004-data-source-resolver` | PRL-004, already merged into `main` | Local only; keep until you decide to delete |
| `chore/agents-md-canonical`, `docs/git-guide` | Small follow-ups | Local until pushed |

## 4. How the GitHub remote was set up

Done once; recorded here so you can repeat it for another project.

```bash
gh auth status                                      # confirm you are logged in
gh repo create ammarajmal/plant-robotics-lab --private --description "..."
git remote add origin https://github.com/ammarajmal/plant-robotics-lab.git
git push -u origin main feat/prl-006-real-data-playback
```

- `--private` matters: history refers to NORMAN, whose licence is unverified (task PRL-005).
- `-u` links the local branch to the remote one, so later `git push` and `git pull` need no arguments.
- Before the first push of any repository, scan for secrets (tracked `.env` files, tokens, keys). Anything pushed may be copied or cached even if you delete it later.
- Verify: `git remote -v`, `git branch -vv`, `git ls-remote --heads origin`.

Only the branches you name are pushed. Local branches and the stash are not.

## 5. Everyday recovery

| Situation | Safe command |
|---|---|
| Undo staging of a file | `git restore --staged <file>` |
| Inspect before committing | `git diff` (unstaged), `git diff --staged` |
| Fix the last commit message (not pushed) | `git commit --amend` |
| Undo a pushed commit safely | `git revert <sha>` (adds a new commit) |
| Find a "lost" commit | `git reflog`, then `git switch -c rescue <sha>` |
| Compare branches | `git log --oneline main..feat/x` |
| See who changed a line | `git blame <file>` |

## 6. Commands that need explicit approval in this project

These can destroy work or rewrite shared history: `git reset --hard`, `git push --force`, `git rebase` on pushed branches, `git clean -fd`, `git stash drop`, `git branch -D`, deleting remote branches. Look at the target first (`git status`, `git log`, `git stash show`), and ask before running them.

## 7. Backup and recovery

- `origin` is the off-machine copy. After meaningful work, `git push` the branch.
- Unpushed local branches and stashes exist only on this disk.
- New machine: `gh auth login`, `git clone https://github.com/ammarajmal/plant-robotics-lab.git`, `uv sync --extra dev`, then run the quality gate in [[development/environment]]. Data and weights are not in Git; see [[development/data_sources]].

## 8. Practice exercises (use a throwaway repo, not PRL)

```bash
mkdir -p /tmp/git-practice && cd /tmp/git-practice && git init -b main
```

1. **First commit.** Create `a.txt`, `git add a.txt`, `git commit -m "chore: add a"`. Run `git log --oneline`.
2. **Branch and merge.** `git switch -c feat/x`, edit `a.txt`, commit, `git switch main`, `git merge feat/x`.
3. **Conflict.** On two branches change the same line differently, merge, open the conflict markers, resolve, `git add`, `git commit`.
4. **Undo.** Make a bad commit, then `git revert HEAD`. Compare with `git reset --soft HEAD~1` (practice only) and see what changes.
5. **Reflog rescue.** Run `git reset --hard HEAD~1` (practice only), then recover with `git reflog` and `git reset --hard <sha>`.
6. **Stash.** Edit a file, `git stash`, `git switch` away and back, `git stash pop`.
7. **Remote.** `gh repo create practice-git --private`, add it as `origin`, push, change a file on GitHub's web UI, then `git pull`. Delete the practice repo afterwards.

Finish when you can explain, without notes, the difference between `reset`, `revert` and `restore`.

## 9. What to learn now vs later

- **Now:** status, add, commit, switch, diff, log, push, pull, revert.
- **Soon:** merge conflicts, stash, reflog, pull requests.
- **Later:** rebase, bisect, worktrees, signing commits, GitHub Actions (see the deferred CI task).
