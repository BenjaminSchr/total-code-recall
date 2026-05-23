**Task:** TASK_W9-T3 — Update plugin.json — register tcr-config and tcr-info (total 7 skills)
**Status:** DONE

**File:** plugin.json
**Branch:** task/W9-T3-register-new-skills-plugin
**Worker type:** Claude Code

**What changes:**
Adds two new skill entries to plugin.json — `tcr-config` and `tcr-info` — bringing the total from 5 to 7 registered skills.

**Ben noob section:**
Claude Code liest plugin.json um zu wissen welche Commands existieren. Ohne Eintrag in plugin.json erkennt Claude Code den neuen Command nicht. Dieser Task registriert die zwei neuen Commands.

**Pattern:**

Add these two entries to the `skills` array in plugin.json:

```json
{
  "name": "tcr-config",
  "path": "skills/tcr-config/SKILL.md",
  "description": "Configure providers: LLM (Ollama/OpenRouter), Embedding (Ollama/OpenRouter), DB (local/Supabase)"
},
{
  "name": "tcr-info",
  "path": "skills/tcr-info/SKILL.md",
  "description": "Show current config, indexed projects, and command reference"
}
```

Final plugin.json `skills` array must contain all 7 entries in this order:
1. tcr-onboard
2. tcr-update
3. tcr-search
4. tcr-overview
5. tcr-explain
6. tcr-config
7. tcr-info

**Input/Output Contract:**
Depends on: TASK_W9-T1 (tcr-config SKILL.md created), TASK_W9-T2 (tcr-info SKILL.md created)
Produces: plugin.json with 7 skill entries

**Verify:**
```bash
python3 -c "import json; d=json.load(open('plugin.json')); assert len(d['skills'])==7, f'Expected 7 skills, got {len(d[\"skills\"])}'; print('PASS')"
```

**Done when:**
plugin.json parses as valid JSON and contains exactly 7 skills entries, including tcr-config and tcr-info.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W9-T3.md`. Read `plugin.json`. Add the two new skill entries (tcr-config, tcr-info) to the skills array. Verify the JSON is valid and has 7 entries. Write Execution Log, rename to `DONE_TASK_W9-T3.md`, commit: `feat: TASK_W9-T3 — register tcr-config and tcr-info in plugin.json (7 skills total)`.

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Added tcr-config and tcr-info entries to plugin.json skills array. Verified 7 skills total (PASS).
- Files Changed: plugin.json
- Issues: none
- Status: DONE
