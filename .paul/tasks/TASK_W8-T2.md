**Task:** TASK_W8-T2 — Update all SKILL.md frontmatter names code-* → tcr-*
**Status:** TODO

**File:** skills/tcr-onboard/SKILL.md, skills/tcr-update/SKILL.md, skills/tcr-search/SKILL.md, skills/tcr-overview/SKILL.md, skills/tcr-explain/SKILL.md
**Branch:** task/W8-T2-update-skillmd-names
**Worker type:** Claude Code

**What changes:**
Updates the `name:` field in each SKILL.md frontmatter block and all internal `/code-*` command references in the heading and usage lines to their `tcr-*` equivalents.

**Ben noob section:**
Jede SKILL.md hat oben einen Header mit `name: code-onboard`. Der wird jetzt auf `name: tcr-onboard` geändert. Außerdem alle Stellen im Text wo `/code-onboard` steht.

**Pattern:**

For each of the five files, change:

**skills/tcr-onboard/SKILL.md:**
```
# BEFORE:
name: code-onboard
# After:
name: tcr-onboard

# BEFORE in body text:
# /code-onboard — Skill Instructions
You are executing the **code-onboard** skill.
Usage: `/code-onboard <path>`
# After:
# /tcr-onboard — Skill Instructions
You are executing the **tcr-onboard** skill.
Usage: `/tcr-onboard <path>`
```

Apply same pattern for each file:
- `code-update` → `tcr-update`
- `code-search` → `tcr-search`
- `code-overview` → `tcr-overview`
- `code-explain` → `tcr-explain`

Also update plugin.json `name` fields (the ones left as `code-*` in W8-T1):
```json
{ "name": "tcr-onboard", "path": "skills/tcr-onboard/SKILL.md" }
{ "name": "tcr-update",  "path": "skills/tcr-update/SKILL.md" }
{ "name": "tcr-search",  "path": "skills/tcr-search/SKILL.md" }
{ "name": "tcr-overview","path": "skills/tcr-overview/SKILL.md" }
{ "name": "tcr-explain", "path": "skills/tcr-explain/SKILL.md" }
```

Do NOT change any Python code blocks, SQL, or configuration variable names — only the skill name references and usage examples.

**Input/Output Contract:**
Depends on: TASK_W8-T1 (directories renamed, so files exist at tcr-* paths)
Produces: All SKILL.md frontmatter names are tcr-*, plugin.json name fields are tcr-*

**Verify:**
```bash
grep -r "^name: code-" skills/ && echo "FAIL — old names remain" || echo "PASS"
grep "\"code-onboard\"\|\"code-update\"\|\"code-search\"\|\"code-overview\"\|\"code-explain\"" plugin.json && echo "FAIL — old names in plugin.json" || echo "PASS"
```
Both must print PASS.

**Done when:**
No `name: code-*` in any SKILL.md frontmatter. No `"code-*"` name entries in plugin.json. All five plugin.json name fields read `tcr-*`.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W8-T2.md`. Read each of the five SKILL.md files. Update the `name:` frontmatter and all internal `/code-*` usage references to `tcr-*`. Also update the five `name` fields in `plugin.json`. Run verify. Write Execution Log, rename task file to `DONE_TASK_W8-T2.md`, commit: `feat: TASK_W8-T2 — update SKILL.md frontmatter names and plugin.json name fields to tcr-*`.
