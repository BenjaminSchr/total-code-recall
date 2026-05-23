**Task:** TASK_W8-T4 — Verify no remaining code-* references
**Status:** TODO

**File:** (no file to create — verification only, writes Execution Log to this task file)
**Branch:** task/W8-T4-verify-rename-complete
**Worker type:** Claude Code

**What changes:**
Runs a comprehensive grep across the entire repo to confirm zero remaining `code-onboard`, `code-update`, `code-search`, `code-overview`, or `code-explain` references in skills/, plugin.json, and README.md. If any are found, lists them and sets Status FAILED. No code is written.

**Ben noob section:**
Ein finaler Audit: Alles nach alten `code-*` Referenzen durchsuchen. Wenn nichts gefunden wird ist Wave 8 fertig. Wenn doch was gefunden wird muss man zurück und es fixen.

**Pattern:**

Run this grep — it must return exit code 1 (no matches = grep returns 1):
```bash
grep -rn "code-onboard\|code-update\|code-search\|code-overview\|code-explain" \
  skills/ plugin.json README.md
```

If grep finds matches → output the matches, set Status FAILED, list every file and line.
If grep finds no matches (exits 1) → PASS.

Also verify the new tcr-* directories all exist:
```bash
test -d skills/tcr-onboard && \
test -d skills/tcr-update && \
test -d skills/tcr-search && \
test -d skills/tcr-overview && \
test -d skills/tcr-explain && \
echo "ALL TCR DIRS EXIST"
```

And verify plugin.json has 5 tcr-* entries:
```bash
grep -c "tcr-" plugin.json
```
Must return >= 10 (5 names + 5 paths).

**Input/Output Contract:**
Depends on: TASK_W8-T1, TASK_W8-T2, TASK_W8-T3 (all rename tasks done)
Produces: Confirmation that Wave 8 rename is complete, or list of failures

**Verify:**
```bash
grep -rn "code-onboard\|code-update\|code-search\|code-overview\|code-explain" skills/ plugin.json README.md && echo "FAIL" || echo "PASS"
```
Must print PASS.

**Done when:**
Zero `code-*` command references found across skills/, plugin.json, README.md. All five `tcr-*` directories exist. Status: DONE.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W8-T4.md`. Run the three verification checks. If all pass, write Execution Log with DONE, rename to `DONE_TASK_W8-T4.md`, commit: `test: TASK_W8-T4 — verify Wave 8 rename complete, zero code-* refs remain`. If any check fails, set Status FAILED and list every failing file/line in the Execution Log.
