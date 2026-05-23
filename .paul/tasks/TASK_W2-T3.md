**Task:** TASK_W2-T3 — Create code-search SKILL.md
**Status:** TODO

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
