**Task:** TASK_W2.5-T1 — Translate all skill outputs from German to English
**Status:** TODO

**File:** skills/code-onboard/SKILL.md, skills/code-update/SKILL.md, skills/code-search/SKILL.md
**Branch:** task/W2.5-T1-english-output
**Worker type:** Claude Code

**What changes:**
All user-facing text in the three SKILL.md files must be in English. The plugin is published publicly — German output is wrong. Change all print statements, report strings, and error messages from German to English.

Examples of what to change:
- "Kein Git-Repo gefunden" → "No git repository found"
- "Projekt nicht indexiert" → "Project not indexed"  
- "Bereits aktuell" → "Already up to date"
- All Step report strings
- All error messages

Do NOT change:
- Code logic, SQL queries, variable names
- SKILL.md structure or step order
- Any technical content

**Verify:**
`grep -r "ä\|ö\|ü\|ß" skills/` — should return no German characters in output strings.

**Done when:**
All user-facing text in all 3 SKILL.md files is in English. No German strings remain in print/report/error messages.

**Ben noob section:**
Das Plugin wird public — alle Texte die der User sieht müssen Englisch sein.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read the task file `.paul/tasks/TASK_W2.5-T1.md`. Read all three SKILL.md files in skills/. Find every German string in print statements, report messages, and error messages. Replace with English equivalents. Do not change code logic. Verify, write Execution Log, commit.
