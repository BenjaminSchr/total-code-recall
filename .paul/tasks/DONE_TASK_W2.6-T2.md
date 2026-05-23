**Task:** TASK_W2.6-T2 — Fix vector type error in INSERT scripts
**Status:** DONE

**File:** skills/code-onboard/SKILL.md, skills/code-update/SKILL.md
**Branch:** task/W2.6-T2-vector-type-fix
**Worker type:** Claude Code

**What changes:**
INSERT scripts pass Python lists for the vector(768) column. Must convert to string format + use `%s::vector` cast, matching how code-search already does it in tcr_search.py.

**Pattern:**
In both `tcr_index.py` scripts (onboard Step 6, update Step 5b), after getting embedding vectors:
```python
# Convert list to pgvector string format
summary_vec_str = "[" + ",".join(str(x) for x in summary_vec) + "]"
code_vec_str = "[" + ",".join(str(x) for x in code_vec) + "]"
```
And change INSERT SQL from `%s` to `%s::vector` for the embedding parameter.

**Verify:**
`grep -n "::vector" skills/code-onboard/SKILL.md skills/code-update/SKILL.md` — both files should show `%s::vector` in INSERT SQL.

**Done when:**
Both onboard and update tcr_index.py scripts convert embedding lists to strings and use `%s::vector` cast in INSERT SQL.

**Ben noob section:**
Ohne diesen Fix crasht das Einfügen der Vektoren in die Datenbank — die Daten werden im falschen Format gesendet.

---

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Added `summary_vec_str`/`code_vec_str` conversion after embedding calls and changed `%s` to `%s::vector` in INSERT_SQL in both tcr_index.py scripts. Pattern matches code-search/SKILL.md vec_str exactly.
- Files Changed: skills/code-onboard/SKILL.md, skills/code-update/SKILL.md
- Issues: none
- Status: DONE

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W2.6-T2.md`. Read `skills/code-search/SKILL.md` to see how tcr_search.py correctly handles vector conversion (look for `vec_str`). Apply the same pattern to the INSERT scripts in both `skills/code-onboard/SKILL.md` and `skills/code-update/SKILL.md`. Verify, write Execution Log, rename task, commit.
