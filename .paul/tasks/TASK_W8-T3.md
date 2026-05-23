**Task:** TASK_W8-T3 — Update README.md — all /code-* references → /tcr-*
**Status:** TODO

**File:** README.md
**Branch:** task/W8-T3-update-readme-references
**Worker type:** Claude Code

**What changes:**
Replaces every occurrence of `/code-onboard`, `/code-update`, `/code-search`, `/code-overview`, `/code-explain` in README.md with their `tcr-*` equivalents. Also updates any `code-onboard`, `code-update` etc. references in prose and code blocks.

**Ben noob section:**
Die README ist die Anleitung für User. Überall wo bisher `/code-onboard` steht muss jetzt `/tcr-onboard` stehen, sonst wundert sich jeder neue User warum der Command nicht existiert.

**Pattern:**

Find and replace these exact strings throughout README.md:
| Old | New |
|-----|-----|
| `/code-onboard` | `/tcr-onboard` |
| `/code-update` | `/tcr-update` |
| `/code-search` | `/tcr-search` |
| `/code-overview` | `/tcr-overview` |
| `/code-explain` | `/tcr-explain` |
| `code-onboard` (bare, in prose) | `tcr-onboard` |
| `code-update` (bare, in prose) | `tcr-update` |
| `code-search` (bare, in prose) | `tcr-search` |
| `code-overview` (bare, in prose) | `tcr-overview` |
| `code-explain` (bare, in prose) | `tcr-explain` |

Do NOT change any Python code, SQL, environment variable names, or path strings that are not command references.

**Input/Output Contract:**
Depends on: TASK_W8-T1, TASK_W8-T2 (renames and skill names done)
Produces: README.md with all tcr-* command references

**Verify:**
```bash
grep -n "code-onboard\|code-update\|code-search\|code-overview\|code-explain" README.md && echo "FAIL — old refs remain" || echo "PASS"
```
Must print PASS (exit 0 with no matches).

**Done when:**
No `code-*` command references remain in README.md.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W8-T3.md`. Read `README.md`. Replace all `/code-*` and bare `code-*` command references with `tcr-*` equivalents. Run the verify grep — it must print PASS with zero matches. Write Execution Log, rename task file to `DONE_TASK_W8-T3.md`, commit: `feat: TASK_W8-T3 — update README.md command references to tcr-*`.
