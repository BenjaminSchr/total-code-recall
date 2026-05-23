# LOG — total-code-recall

## 2026-05-23

### Session Start
- Project: total-code-recall (Claude Code Plugin für semantische Code-Suche)
- Repo: github.com/BenjaminSchr/total-code-recall (public, MIT)
- Working dir: /home/bengpu/Schreibtisch/Workspace/projekte/Toolproject/total-code-recall

### PLAN Phase
- Concept discussion with Ben: Architecture, DB schema, chunking, embedding, skills
- Key decisions:
  - 100% local (Ollama, no cloud LLMs)
  - devstral:24b for summaries, one embedding model for both summary+code
  - pgvector DB, one table per project, table name = sanitized git repo name
  - Two rows per chunk (summary + code), each with own embedding
  - Fixed-size chunks (50 lines, 15 overlap), language-agnostic
  - Delete + Re-Insert on update (always current state)
  - Git gate: no git repo = no indexing
  - Plugin format (publishable on GitHub)
- CONCEPT.md written and approved
- Advisor consulted twice for plan challenges

### APPLY Phase — Task Creation
- Created 7 tasks across 3 waves:
  - W1: T1-T4 (Plugin scaffold + DB setup)
  - W2: T1-T3 (Three skills: onboard, update, search)
  - W3: T1 (README)
- STATE.md and LOG.md created

### Activation Code
- Ben provided activation code AlphaBravoZulu1984 for docker-compose.yaml (W1-T4)
- W1-T4 unblocked and executed

### APPLY Phase — Wave 1 Execution (Quality mode, ohne GLM)
- W1-T1: plugin.json — DONE (a1 CODE + a2 REVIEW PASS)
- W1-T2: .env.example + .gitignore — DONE (a1 CODE + a2 REVIEW PASS)
- W1-T3: setup_db.sql — DONE (a1 CODE)
- W1-T4: docker-compose.yaml — DONE (a1 CODE)
- Wave Review: PASS (1 doku-issue fixed in Wave Fix)
- All task branches merged into wave/W1-scaffold

### APPLY Phase — Wave 2 Execution
- W2-T1: code-onboard SKILL.md — DONE (543 lines, a1+a2 PASS)
- W2-T2: code-update SKILL.md — DONE (581 lines, a1 CODE)
- W2-T3: code-search SKILL.md — DONE (346 lines, a1 CODE)
- Wave Review: FAIL — 2 HIGH bugs in update skill + 1 setup_db.sql permissions
- Wave Fix: modified in files_to_delete + chunk_id collision + superuser docs
- After Fix: PASS
- Merged to dev, tagged W2_done

### Zwischen-UNIFY W1+W2
- SUMMARY.md updated
- STATE.md updated
- 3 open issues documented: German output, .env loading, tcr_index duplication

### APPLY Phase — Wave 2.6 (Critical Bugfixes)
- W2.6-T1 to T5: All 5 bugs fixed (path mismatch, vector type, requirements, rerun dedup, shell injection)
- Wave Review: PASS
- Merged to dev, tagged W2.6_done

### APPLY Phase — Wave 3 (README)
- W3-T1: README.md with FAQ — DONE (270 lines)
- Merged to dev, tagged W3_done
- V1 COMPLETE, pushed to GitHub

### APPLY Phase — Relational Layer (feature/relational-layer)
- W5 (AST Layer): 4 tasks DONE, Opus Review found 3 bugs → fixed
- W6 (Hierarchical Summaries): 3 tasks DONE, Opus Review PASS (+1 idempotency fix)
- W7 (Hybrid Query): 2 tasks DONE, Opus Review found 3 bugs → fixed
- Final parallel Opus Code Review (3 agents): found 10 more bugs (4 HIGH, 6 MEDIUM) → all fixed
- Merged to dev, tagged relational-layer_done

### Final State
- 5 Skills: code-onboard, code-update, code-search, code-overview, code-explain
- 5 DB Tables/project: chunks, entities, relations, summaries, _index_meta
- Total: 24 tasks across 7 waves, all DONE
- Pushed to GitHub: dev branch

### Wave 8 — Rename (2026-05-23)
- W8-T2: SKILL.md frontmatter + plugin.json names code-* → tcr-* — DONE
- W8-T3: README.md command references code-* → tcr-* — DONE
- W8-T4: Verification — all 3 checks PASS — DONE
- Wave Review: FAIL (2 issues: STATE.md outdated + stale task files)
- Wave Fix: Fixed STATE.md + removed stale TASK_W8-T*.md files
- Merged wave/W8-rename → dev, tagged W8_done
