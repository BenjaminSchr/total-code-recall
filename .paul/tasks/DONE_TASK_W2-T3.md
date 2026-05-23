**Task:** TASK_W2-T3 — Create code-search SKILL.md
**Status:** DONE

**File:** skills/code-search/SKILL.md
**Branch:** task/W2-T3-skill-search
**Worker type:** Claude Code

**What changes:**
Creates the search skill — instructs Claude how to: embed user query via Ollama, run vector similarity search with dedup, format top 10 results.

**Pattern:**
The SKILL.md must contain these sections in order:
1. Frontmatter (name, description)
2. Usage line: `/code-search <query>`
3. Step 1: Git Gate
4. Step 2: Check Index Exists — query _index_meta for chunk_count
5. Step 3: Embed Query — Ollama embed API
6. Step 4: Search — vector similarity with DISTINCT ON (chunk_id) dedup, ORDER BY similarity DESC, LIMIT 10
7. Step 5: Format Results — file, lines, type, score, content per match

Full content is specified in CONCEPT.md under "Pipeline > Search".

**Input/Output Contract:**
Depends on: TASK_W2-T1 (onboard must have been run — data must exist)

**Verify:**
`test -f skills/code-search/SKILL.md && grep -c "Step" skills/code-search/SKILL.md` — file exists, has 5+ Step references.

**Done when:**
skills/code-search/SKILL.md exists with all 5 steps. Dedup SQL uses DISTINCT ON (chunk_id). Output format shows file, lines, type, score, content.

**Ben noob section:**
Das ist die Suche — du tippst `/code-search "Datumsfilter"` und bekommst die 10 relevantesten Code-Stellen.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read the task file `.paul/tasks/TASK_W2-T3.md`. Read `.paul/CONCEPT.md` for search pipeline and SQL. Write skills/code-search/SKILL.md. Verify, write Execution Log, commit.

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Created skills/code-search/SKILL.md with all 5 steps: Git Gate, Check Index Exists (with embedding model mismatch check matching update skill), Embed Query (Ollama /api/embed), Search (DISTINCT ON chunk_id dedup SQL as specified), Format Results (file, lines, type, score, full content). Config section stripped to only DATABASE_URL/OLLAMA_URL/EMBEDDING_MODEL (no summary/chunk config — search doesn't need it). Vector passed as formatted string for %s::vector cast. Params tuple passes vec_str twice as required by the subquery SQL.
- Files Changed: skills/code-search/SKILL.md
- Issues: none
- Status: DONE
