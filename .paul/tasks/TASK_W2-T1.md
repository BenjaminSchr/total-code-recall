**Task:** TASK_W2-T1 — Create code-onboard SKILL.md
**Status:** TODO

**File:** skills/code-onboard/SKILL.md
**Branch:** task/W2-T1-skill-onboard
**Worker type:** Claude Code

**What changes:**
Creates the onboard skill — instructs Claude how to: check git gate, discover files, chunk them, generate summaries via Ollama, generate embeddings, bulk insert into pgvector, update _index_meta.

**Pattern:**
The SKILL.md must contain these sections in order:
1. Frontmatter (name, description)
2. Step 1: Git Gate — `git rev-parse --is-inside-work-tree`, extract+sanitize repo name
3. Step 2: Check Prerequisites — Ollama running, models available, DB reachable
4. Step 3: Create Project Table — dynamic CREATE TABLE with schema from CONCEPT.md
5. Step 4: Discover Files — allowlist (.py .html .sql .js .css .yaml .json .toml .md .sh), blocklist (venv/ __pycache__/ .git/ etc.), min 3 lines
6. Step 5: Chunk Files — 50 lines, 15 overlap, sequential chunk_id
7. Step 6: Generate Summaries + Embeddings — Ollama generate for summary, Ollama embed for both summary+code vectors, batch INSERT
8. Step 7: Update _index_meta — HEAD commit hash, chunk count, embedding model
9. Step 8: Report — files indexed, chunks created, table name
10. Config section — all 6 env vars with defaults
11. Error Handling section

Full content is specified in CONCEPT.md under "Pipeline > Onboard".

**Input/Output Contract:**
Depends on: TASK_W1-T3 (setup_db.sql — _index_meta table schema as reference)

**Verify:**
`test -f skills/code-onboard/SKILL.md && grep -c "Step" skills/code-onboard/SKILL.md` — file exists, has 8+ Step references.

**Done when:**
skills/code-onboard/SKILL.md exists with all 8 steps, config section, error handling. Covers full pipeline from git check to DB insert.

**Ben noob section:**
Das ist die Anleitung die Claude liest wenn du `/code-onboard` tippst. Claude folgt den Schritten und indexiert dein Projekt automatisch.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read the task file `.paul/tasks/TASK_W2-T1.md`. Read `.paul/CONCEPT.md` for the full pipeline details and DB schema. Write the complete SKILL.md at skills/code-onboard/SKILL.md. Verify, write Execution Log, commit.
