**Task:** TASK_W3-T1 — Write README.md
**Status:** TODO

**File:** README.md
**Branch:** task/W3-T1-readme
**Worker type:** Claude Code

**What changes:**
Replaces the auto-generated GitHub README with a proper plugin README: what it does, prerequisites, setup, usage of all 3 skills, configuration, architecture.

**Pattern:**
README must include:
1. Title + tagline
2. What it does (problem → solution)
3. Quick Start (prerequisites, Docker option, plugin install)
4. Usage section for each skill (/code-onboard, /code-update, /code-search)
5. Configuration table (.env vars with defaults)
6. Architecture overview (pipeline diagram)
7. Requirements
8. License (MIT)

**Input/Output Contract:**
Depends on: All W1 and W2 tasks (documents actual skill behavior)

**Verify:**
`test -f README.md && head -1 README.md` shows the title line.

**Done when:**
README.md exists with all 8 sections. Describes all 3 skills. Shows configuration options. Has architecture overview.

**Ben noob section:**
Das ist die Seite die Leute auf GitHub als erstes sehen — entscheidet ob jemand es installiert oder weiterscrollt.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read the task file `.paul/tasks/TASK_W3-T1.md`. Read `.paul/CONCEPT.md`, all three SKILL.md files, and .env.example for reference. Write the full README.md. Verify, write Execution Log, commit.
