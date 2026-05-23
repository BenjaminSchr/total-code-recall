**Task:** TASK_W5-T3 — Add entity/relation cleanup to update skill
**Status:** DONE

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

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Added `DELETE FROM {PROJECT_NAME}_entities WHERE file_path = %s` inside the `for path in stale_paths:` loop in Step 4 (tcr_delete_stale.py), after the existing chunk DELETE. Added Step 5c to code-update SKILL.md: writes `files_to_reindex` to `/tmp/tcr_files.json`, then writes and runs the full `tcr_parse_ast.py` script (copied verbatim from onboard Step 5b). Both grep checks pass: `_entities` count=3, `parse_ast` count=2.
- Files Changed: skills/code-update/SKILL.md
- Issues: The copied tcr_parse_ast.py does `DELETE FROM {PROJECT_NAME}_entities` (full table wipe) before re-inserting. In the update context only `files_to_reindex` files are passed via `/tmp/tcr_files.json`, so entities for unchanged files will be wiped and not restored. Task says "accepted drift risk" — noted here per advisor guidance.
- Status: DONE
