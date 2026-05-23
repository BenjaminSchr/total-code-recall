**Task:** TASK_W6-T2 — Add file-level summary generation to onboard
**Status:** DONE

**File:** skills/code-onboard/SKILL.md
**Branch:** task/W6-T2-file-summaries
**Worker type:** Claude Code

**What changes:**
Adds a new step after embedding (before _index_meta update). Writes `/tmp/tcr_build_summaries.py` which aggregates chunk-level summaries per file, generates a file-level summary via devstral, embeds it, and INSERTs into _summaries.

**Pattern:**

New step in SKILL.md:

```
## Step 8: Generate Hierarchical Summaries
```

The script `/tmp/tcr_build_summaries.py` must:
1. Load .env (same inline loader pattern)
2. Connect to DB
3. Query all distinct file_paths from the chunks table
4. For each file_path:
   - `SELECT content FROM {project} WHERE file_path = %s AND type = 'summary' ORDER BY line_start`
   - Concatenate all chunk summaries for this file
   - Call devstral via `POST {OLLAMA_URL}/api/generate`:
     ```
     prompt: "Summarize this file's purpose and key components in 2-3 sentences:\n\n{concatenated_summaries}"
     model: {SUMMARY_MODEL}
     ```
   - Embed the file summary via `POST {OLLAMA_URL}/api/embed`
   - Convert embedding to pgvector string format
   - `INSERT INTO {project}_summaries (level, scope, content, embedding) VALUES ('file', %s, %s, %s::vector)`
5. Output: `SUMMARIES_OK: {count} file summaries generated`

Env vars: DATABASE_URL, OLLAMA_URL, SUMMARY_MODEL, EMBEDDING_MODEL, TCR_PROJECT

**Input/Output Contract:**
Depends on: TASK_W6-T1 (summaries table exists), chunk summaries from Step 6 must exist

**Verify:**
`grep -c "build_summaries" skills/code-onboard/SKILL.md` — should be >0.

**Done when:**
New step exists in onboard SKILL.md. For each indexed file, a file-level summary is generated (devstral), embedded, and stored in _summaries with level='file'.

**Ben noob section:**
Nach dem Indexieren fasst dieser Step jede Datei in 2-3 Sätzen zusammen. So kann ein Agent schnell verstehen was eine Datei tut, ohne sie zu lesen.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W6-T2.md`. Read `skills/code-onboard/SKILL.md` to understand the current step numbering. Add a new step after the embedding step. Use the existing Ollama API call patterns from Step 6 (tcr_index.py) as reference for the devstral generate + nomic embed calls. Verify, write Execution Log, rename task, commit.

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Inserted new Step 7 (Generate Hierarchical Summaries) into skills/code-onboard/SKILL.md. The step writes /tmp/tcr_build_summaries.py which: loads .env inline, connects to DB, queries distinct file_paths from chunk summaries, concatenates chunk summaries per file, calls devstral via /api/generate, embeds via /api/embed, converts to pgvector string format, INSERTs into {project}_summaries with level='file'. Old Step 7 (Update _index_meta) renumbered to Step 8, old Step 8 (Report) renumbered to Step 9. Intro updated from "8 steps" to "9 steps".
- Files Changed: skills/code-onboard/SKILL.md
- Issues: none
- Status: DONE
