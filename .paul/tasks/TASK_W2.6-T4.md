**Task:** TASK_W2.6-T4 — Fix onboard re-run duplication
**Status:** TODO

**File:** skills/code-onboard/SKILL.md
**Branch:** task/W2.6-T4-onboard-rerun-fix
**Worker type:** Claude Code

**What changes:**
Re-running /code-onboard doubles all data because there's no DELETE before INSERT. Fix: add DELETE FROM {project_name} at the start of tcr_index.py before the chunk loop.

**Pattern:**
In `tcr_index.py` (Step 6), after connecting to DB and before processing chunks:
```python
# Clear existing data for idempotent re-onboard
cur.execute(f"DELETE FROM {PROJECT_NAME}")
conn.commit()
print(f"CLEARED: Removed existing data from {PROJECT_NAME}")
```

**Verify:**
`grep -n "DELETE FROM" skills/code-onboard/SKILL.md` — should show the new DELETE in tcr_index.py.

**Done when:**
Re-running /code-onboard clears existing data before inserting new chunks. No duplicates.

**Ben noob section:**
Ohne diesen Fix verdoppeln sich alle Daten wenn man /code-onboard ein zweites Mal ausführt.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W2.6-T4.md`. Edit `skills/code-onboard/SKILL.md` — find the tcr_index.py script in Step 6 and add a DELETE statement at the top (after DB connect, before chunk loop). Verify, write Execution Log, rename task, commit.
