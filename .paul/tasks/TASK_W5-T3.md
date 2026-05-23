**Task:** TASK_W5-T3 — Add entity/relation cleanup to update skill
**Status:** TODO

**File:** skills/code-update/SKILL.md
**Branch:** task/W5-T3-update-entity-cleanup
**Worker type:** Claude Code

**What changes:**
Extends the update skill to handle entity/relation invalidation and rebuild for changed files. Step 4 (delete stale data) gets entity cleanup. Step 5 gets the AST re-parse for changed files.

**Pattern:**

1. In Step 4 (tcr_delete_stale.py), after the existing `DELETE FROM {PROJECT_NAME} WHERE file_path = %s`, add:
```python
cur.execute(f"DELETE FROM {PROJECT_NAME}_entities WHERE file_path = %s", (path,))
# Relations auto-cascade via ON DELETE CASCADE on from_id/to_id FKs
```

2. After Step 5 (re-index chunks), add Step 5c: write and execute `/tmp/tcr_parse_ast.py` for the files in `files_to_reindex`. Same script as onboard Step 5b (inline duplicate, accepted drift risk).

**Input/Output Contract:**
Depends on: TASK_W5-T1 (tables exist), TASK_W5-T2 (parse_ast script pattern to copy)

**Verify:**
`grep -c "_entities" skills/code-update/SKILL.md` — should be >0.
`grep -c "parse_ast" skills/code-update/SKILL.md` — should be >0.

**Done when:**
Update skill deletes entities for stale files in Step 4 (relations cascade automatically). Update skill re-parses AST for changed files after chunk re-indexing. Same tcr_parse_ast.py inline script as onboard.

**Ben noob section:**
Wenn du Code änderst und `/code-update` ausführst, werden nicht nur die Text-Chunks aktualisiert sondern auch die Struktur-Infos (Funktionen, Klassen, Aufrufe).

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W5-T3.md`. Read `skills/code-update/SKILL.md` for Step 4 (tcr_delete_stale.py). Read `skills/code-onboard/SKILL.md` for Step 5b (tcr_parse_ast.py) to copy the pattern. Add entity DELETE in Step 4. Add AST re-parse step after chunk re-indexing. Verify, write Execution Log, rename task, commit.
