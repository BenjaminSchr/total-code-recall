**Task:** TASK_W2.6-T3 — Create requirements.txt
**Status:** TODO

**File:** requirements.txt
**Branch:** task/W2.6-T3-requirements-txt
**Worker type:** Claude Code

**What changes:**
Creates requirements.txt listing all Python dependencies needed by the plugin's temp scripts.

**Pattern:**
```
psycopg2-binary
requests
```

**Verify:**
`test -f requirements.txt && cat requirements.txt`

**Done when:**
requirements.txt exists with psycopg2-binary and requests.

**Ben noob section:**
Ohne requirements.txt wissen externe User nicht welche Python-Pakete sie installieren müssen.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W2.6-T3.md`. Create requirements.txt at project root. Verify, write Execution Log, rename task, commit.
