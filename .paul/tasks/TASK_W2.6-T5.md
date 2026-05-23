**Task:** TASK_W2.6-T5 — Fix shell injection in commit message
**Status:** TODO

**File:** skills/code-onboard/SKILL.md, skills/code-update/SKILL.md
**Branch:** task/W2.6-T5-shell-injection-fix
**Worker type:** Claude Code

**What changes:**
Commit messages with `"`, `$`, backticks break the shell env var `TCR_HEAD_MESSAGE`. Fix: pass commit message via the JSON data file instead of shell env var.

**Pattern:**
1. When writing tcr_chunks.json, change structure to include meta:
```python
json.dump({"meta": {"head_message": HEAD_MESSAGE}, "chunks": chunks}, f)
```
2. In tcr_index.py, read from JSON instead of env:
```python
data = json.load(f)
HEAD_MESSAGE = data["meta"]["head_message"]
chunks = data["chunks"]
```
3. Remove `TCR_HEAD_MESSAGE` from the bash invocation line.

Apply to both onboard and update skills.

**Verify:**
`grep -n "TCR_HEAD_MESSAGE" skills/code-onboard/SKILL.md skills/code-update/SKILL.md` — should return no matches (removed from env vars).

**Done when:**
Commit messages are passed via JSON data file, not shell env var. No shell injection possible.

**Ben noob section:**
Commit-Messages mit Sonderzeichen (`"`, `$`) haben die Scripts crashen lassen. Jetzt werden sie sicher über eine JSON-Datei übergeben.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W2.6-T5.md`. Edit both SKILL.md files — change the chunk JSON structure to include meta.head_message, update tcr_index.py to read from JSON, remove TCR_HEAD_MESSAGE from bash invocations. Verify, write Execution Log, rename task, commit.
