**Task:** TASK_W2-T2 — Create code-update SKILL.md
**Status:** TODO

**File:** skills/code-update/SKILL.md
**Branch:** task/W2-T2-skill-update
**Worker type:** Claude Code

**What changes:**
Creates the update skill — instructs Claude how to: check git gate, read last indexed commit, find changed/deleted files, delete old chunks, re-index changed files, update _index_meta.

**Pattern:**
The SKILL.md must contain these sections in order:
1. Frontmatter (name, description)
2. Step 1: Git Gate
3. Step 2: Check Index Exists — query _index_meta, check embedding model match
4. Step 3: Find Changes — `git diff --name-status {last_hash}..HEAD`, categorize M/A/D/R
5. Step 4: Remove Stale Data — DELETE chunks for modified/deleted/renamed files
6. Step 5: Re-Index Changed Files — same chunk+summary+embed pipeline as onboard
7. Step 6: Update _index_meta
8. Step 7: Report — commits processed, files updated/deleted, chunk count

Full content is specified in CONCEPT.md under "Pipeline > Update".

**Input/Output Contract:**
Depends on: TASK_W2-T1 (onboard skill — update references same pipeline pattern)

**Verify:**
`test -f skills/code-update/SKILL.md && grep -c "Step" skills/code-update/SKILL.md` — file exists, has 7+ Step references.

**Done when:**
skills/code-update/SKILL.md exists with all 7 steps. Handles M/A/D/R file statuses. References same pipeline as onboard for re-indexing.

**Ben noob section:**
Das ist die Anleitung für `/code-update` — Claude schaut welche Commits neu sind und aktualisiert nur die geänderten Dateien.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read the task file `.paul/tasks/TASK_W2-T2.md`. Read `.paul/CONCEPT.md` for pipeline details. Read `skills/code-onboard/SKILL.md` for the pipeline pattern to reference. Write skills/code-update/SKILL.md. Verify, write Execution Log, commit.
