**Task:** TASK_W7-T2 — Consolidate update skill and update README
**Status:** TODO

**File:** skills/code-update/SKILL.md, README.md
**Branch:** task/W7-T2-update-consolidation-readme
**Worker type:** Claude Code

**What changes:**
Final consolidation: verify update skill mirrors all onboard additions (entities, summaries). Update README with new commands, tree-sitter prerequisite, updated architecture.

**Pattern:**

1. Review `skills/code-update/SKILL.md` — confirm it has:
   - Entity DELETE in Step 4 (from W5-T3)
   - AST re-parse after chunk re-indexing (from W5-T3)
   - Summary rebuild for affected files/modules/repo (from W6-T3)
   - Fix any gaps or inconsistencies

2. Update README.md:
   - Add `tree-sitter` and `tree-sitter-languages` to Prerequisites
   - Add `pip install -r requirements.txt` in setup
   - Add `/code-overview` usage section with examples
   - Add `/code-explain` usage section with examples
   - Update architecture diagram to show entity/relation/summary layer
   - Add FAQ entries:
     - "What is the relational layer?" → Explains entity/relation extraction
     - "Do I need tree-sitter?" → Optional, degrades gracefully

**Verify:**
`grep -c "code-overview" README.md` — should be >0.
`grep -c "code-explain" README.md` — should be >0.
`grep -c "tree-sitter" README.md` — should be >0.

**Done when:**
Update skill is fully consistent with onboard (all relational layer steps present). README documents all 5 skills, tree-sitter prerequisite, and updated architecture.

**Ben noob section:**
Der letzte Schliff: alles konsistent machen und die README aktualisieren damit externe User die neuen Features verstehen.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W7-T2.md`. Read `skills/code-update/SKILL.md` and `skills/code-onboard/SKILL.md` side by side — verify update has all steps from onboard (entities, summaries). Fix gaps. Then read `README.md` and add documentation for code-overview and code-explain. Verify, write Execution Log, rename task, commit.
