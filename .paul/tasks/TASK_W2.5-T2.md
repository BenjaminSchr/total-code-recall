**Task:** TASK_W2.5-T2 — Add .env loading to all skill temp scripts
**Status:** TODO

**File:** skills/code-onboard/SKILL.md, skills/code-update/SKILL.md, skills/code-search/SKILL.md
**Branch:** task/W2.5-T2-env-loading
**Worker type:** Claude Code

**What changes:**
All temp Python scripts in the skills use `os.getenv()` but never load the `.env` file. This means users must manually export every variable. Fix: add a plain Python `.env` loader at the top of every temp script (no dependency on python-dotenv).

Add this block at the top of every temp Python script (before any `os.getenv` call):

```python
# Load .env file if present
import os
_env_path = os.path.join(os.getcwd(), ".env")
if not os.path.exists(_env_path):
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
```

This reads `.env` from the current working directory (where the user runs the skill) without any pip dependency.

Do NOT change:
- Code logic, SQL, Ollama calls
- Skill structure

**Verify:**
`grep -c "Load .env" skills/code-onboard/SKILL.md skills/code-update/SKILL.md skills/code-search/SKILL.md` — each file should show at least 1 match.

**Done when:**
Every temp Python script in all 3 skills loads `.env` before calling `os.getenv()`. No external dependency needed.

**Ben noob section:**
Ohne diesen Fix muss der User jede Config-Variable manuell exportieren. Mit dem Fix liest der Skill die .env automatisch.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read the task file `.paul/tasks/TASK_W2.5-T2.md`. Read all three SKILL.md files. Find every temp Python script block. Add the .env loader from the Pattern at the top of each script (before any os.getenv call). Verify, write Execution Log, commit.
