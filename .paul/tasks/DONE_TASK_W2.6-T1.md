# TASK_W2.6-T1 — Fix path format mismatch between find and git diff

**Status:** DONE
**Branch:** task/W2.6-T1-path-format-fix
**Worker type:** Claude Code
**Priority:** CRITICAL

---

## Ben Noob Section

When the onboard skill finds files it uses `find .` which gives paths like `./app/main.py`. When the update skill gets changed files from git it gives paths like `app/main.py` (no leading `./`). This means the DELETE step in code-update can never find the right rows to delete — the paths in the DB and the paths being queried don't match. Fix: strip the `./` prefix from find output so both systems always use the same bare-relative path format.

---

## File

- `skills/code-onboard/SKILL.md` (edit)
- `skills/code-update/SKILL.md` (edit)

---

## What Changes

In code-onboard Step 4, strip the leading `./` from every path produced by `find .` before storing it in `files_to_index`. In code-update Step 3, ensure the paths from `git diff --name-status` are already bare-relative (they are — no change needed there, but add a comment confirming this). Both skills now store and query the DB with bare-relative paths like `app/main.py`.

---

## Pattern

In code-onboard Step 4, the file discovery loop currently does:

```python
for path in raw_find_output.splitlines():
    path = path.strip()
    if not path:
        continue
```

Add one line after `path = path.strip()`:

```python
    if path.startswith("./"):
        path = path[2:]
```

This must happen BEFORE `is_blocked(path)` and before `files_to_index.append((path, lines))`.

In code-update Step 3, add a comment after the `git diff` parsing block to document that `git diff --name-status` already produces bare-relative paths (no `./` prefix), so no stripping is needed there. This makes the contract explicit for future maintainers.

---

## What To Do

1. Open `skills/code-onboard/SKILL.md`
2. Find Step 4, the Python block starting with `for path in raw_find_output.splitlines():`
3. After `path = path.strip()` (and before the `if not path: continue` check), add:
   ```python
   if path.startswith("./"):
       path = path[2:]
   ```
4. Open `skills/code-update/SKILL.md`
5. Find Step 3, after the `for line in git_diff_output.splitlines():` block ends (after the categorization into added/modified/deleted/renamed)
6. Add a comment line:
   ```python
   # Note: git diff --name-status paths are already bare-relative (e.g. "app/main.py") — no ./ stripping needed.
   ```
7. Verify the change is logically consistent: onboard stores `app/main.py`, update deletes `app/main.py` — paths now match.

---

## Verify

Read the modified Step 4 block in code-onboard/SKILL.md and confirm:
- The `./` stripping line is present and positioned correctly (after `path.strip()`, before `is_blocked`)
- A file found at `./app/main.py` would be stored as `app/main.py`

Read the modified Step 3 block in code-update/SKILL.md and confirm:
- The comment is present explaining the path format contract

---

## Done When

`find .` output paths are normalized to bare-relative format (no leading `./`) before any processing in code-onboard, and the path format contract is documented in code-update.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W2.6-T1.md` for your full assignment. You are fixing a critical path format mismatch bug in two SKILL.md files.

The bug: `find .` produces `./app/main.py` but the DB stores and queries `app/main.py` (from git diff). DELETE never matches.

Fix in `skills/code-onboard/SKILL.md` Step 4: after `path = path.strip()`, add `if path.startswith("./"): path = path[2:]` — before the blocklist check and before appending to `files_to_index`.

Fix in `skills/code-update/SKILL.md` Step 3: add a comment after the git diff parsing block documenting that git diff paths are already bare-relative.

After editing both files, re-read the changed sections to verify correctness. Then write the Execution Log, update Status to DONE, rename this file to `DONE_TASK_W2.6-T1.md`, and commit: `git add skills/code-onboard/SKILL.md skills/code-update/SKILL.md .paul/tasks/DONE_TASK_W2.6-T1.md && git commit -m "fix: TASK_W2.6-T1 — strip ./ prefix from find output to match git diff path format"`

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Added `./` stripping in code-onboard Step 4 (after `path.strip()`, before blocklist check). Added bare-relative path contract comment in code-update Step 3 (after the git diff categorization block). Both skills now use consistent bare-relative paths — onboard stores `app/main.py`, update deletes by `app/main.py`.
- Files Changed: `skills/code-onboard/SKILL.md`, `skills/code-update/SKILL.md`
- Issues: none
- Status: DONE
