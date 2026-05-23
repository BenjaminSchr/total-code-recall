**Task:** TASK_W8-T1 — Rename skill directories code-* → tcr-*, update plugin.json paths
**Status:** TODO

**File:** skills/ (directory renames), plugin.json
**Branch:** task/W8-T1-rename-skill-dirs
**Worker type:** Claude Code

**What changes:**
Renames all five `code-*` skill directories to `tcr-*` using `mv`, then updates plugin.json to point at the new paths. These two actions must happen together — partial rename breaks all skills.

**Ben noob section:**
Das ist wie ein Firma-Rebranding: alle Ordner und Verweise von `code-*` auf `tcr-*` umbenennen. Nach diesem Task gibt es keine `code-*` Ordner mehr.

**Pattern:**

Step 1 — Rename directories (run all five atomically):
```bash
mv skills/code-onboard  skills/tcr-onboard
mv skills/code-update   skills/tcr-update
mv skills/code-search   skills/tcr-search
mv skills/code-overview skills/tcr-overview
mv skills/code-explain  skills/tcr-explain
```

Step 2 — Edit plugin.json, update all 5 path fields:
```json
{
  "skills": [
    { "name": "code-onboard", "path": "skills/tcr-onboard/SKILL.md", ... },
    { "name": "code-update",  "path": "skills/tcr-update/SKILL.md",  ... },
    { "name": "code-search",  "path": "skills/tcr-search/SKILL.md",  ... },
    { "name": "code-overview","path": "skills/tcr-overview/SKILL.md",...},
    { "name": "code-explain", "path": "skills/tcr-explain/SKILL.md", ... }
  ]
}
```
Note: `name` fields stay as `code-*` for now — W8-T2 updates the SKILL.md frontmatter names. Only `path` values change here.

**Input/Output Contract:**
Depends on: none (first task in Wave 8)
Produces: tcr-* directories exist, plugin.json paths updated

**Verify:**
```bash
test -d skills/tcr-onboard && test -d skills/tcr-update && test -d skills/tcr-search && test -d skills/tcr-overview && test -d skills/tcr-explain && ! test -d skills/code-onboard && grep "tcr-onboard/SKILL.md" plugin.json
```

**Done when:**
All five `tcr-*` directories exist, no `code-*` directories remain, and plugin.json paths all reference `tcr-*/SKILL.md`.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W8-T1.md`. Run the five `mv` commands to rename the skill directories. Then read and edit `plugin.json` — update only the five `path` fields (leave `name` fields unchanged for now). Run the verify command to confirm. Write Execution Log, rename task file to `DONE_TASK_W8-T1.md`, commit: `feat: TASK_W8-T1 — rename skill dirs code-* to tcr-*, update plugin.json paths`.
