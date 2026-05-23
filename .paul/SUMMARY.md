# SUMMARY — total-code-recall Relational Layer

## Final UNIFY — feature/relational-layer

### Waves Completed

| Wave | Tasks | Purpose | Opus Review | Bugs Fixed |
|------|-------|---------|-------------|------------|
| W5 | T1-T4 | AST Layer (entities, relations, tree-sitter, code-overview) | FAIL→FIX | 3 (full DELETE, name collision, CTE filter) |
| W6 | T1-T3 | Hierarchical Summaries (file, module, repo) | PASS | 0 (+1 idempotency guard) |
| W7 | T1-T2 | Hybrid Query (code-explain, README update) | FAIL→FIX | 3 (re-ranking, README count, summary claim) |

### New Files

| File | Lines | Purpose |
|------|-------|---------|
| `skills/code-overview/SKILL.md` | ~444 | Structural overview via entity/relation graph |
| `skills/code-explain/SKILL.md` | ~526 | Hybrid search: vector + graph + summaries |

### Modified Files

| File | Changes |
|------|---------|
| `skills/code-onboard/SKILL.md` | +entity/relation tables, +AST parsing step, +summaries table, +file/module/repo summary generation |
| `skills/code-update/SKILL.md` | +entity DELETE cascade, +AST re-parse, +summary rebuild |
| `scripts/setup_db.sql` | +entity, relation, summaries table templates |
| `plugin.json` | 3→5 skills (added code-overview, code-explain) |
| `README.md` | +code-overview/code-explain docs, +tree-sitter prereq, +architecture update |

### New DB Tables (per project)

| Table | Purpose |
|-------|---------|
| `{project}_entities` | Code elements: files, classes, functions, methods, imports |
| `{project}_relations` | Relationships: calls, imports, extends, references, contains |
| `{project}_summaries` | Hierarchical summaries: file, module, repo level |

### Bugs Found & Fixed

| Bug | Severity | Fix |
|-----|----------|-----|
| Update AST full DELETE wiped unchanged entities | CRITICAL | Removed — Step 4 handles selective deletion |
| name_to_id collision on duplicate names | HIGH | Qualified keys: file_path::name |
| CTE traversed all relation types | MEDIUM | Filtered to `r.type = 'calls'` |
| Summaries not idempotent on re-run | MEDIUM | Added DELETE before regeneration |
| code-explain no re-ranking | HIGH | Added weighted score: 0.6*vector + 0.2*graph + 0.2*summary |
| README "Three commands" | MEDIUM | Changed to "Five commands" |
| README claims module/repo in explain | MEDIUM | Corrected to "file summary context" |

### Architecture (final)

```
code-onboard pipeline:
  File Discovery → Chunk (50/15) → Summary (devstral) → Embed (nomic)
    → 2 rows/chunk in pgvector
    → AST parse (tree-sitter) → entities + relations
    → File → Module → Repo summaries

code-update pipeline:
  git diff → DELETE stale (chunks + entities + summaries)
    → Re-chunk → Re-embed → Re-parse AST → Rebuild summaries

code-search:    vector similarity → top 10
code-overview:  recursive CTE on entity graph (pure SQL)
code-explain:   vector + graph expansion + file summary → weighted re-rank → top 10
```

### Plugin Skills (5 total)
1. `/code-onboard` — First-time project indexing
2. `/code-update` — Incremental update after commits
3. `/code-search` — Semantic vector search
4. `/code-overview` — Structural overview (entities/relations)
5. `/code-explain` — Hybrid search (vector + graph + summaries)
