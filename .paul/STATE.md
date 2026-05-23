# STATE — total-code-recall

## Current Phase: V1 COMPLETE

## V1 Tasks — All DONE

### Wave 1 — Plugin Scaffold
| W1-T1 | plugin.json | DONE |
| W1-T2 | .env.example + .gitignore | DONE |
| W1-T3 | setup_db.sql | DONE |
| W1-T4 | docker-compose.yaml | DONE |

### Wave 2 — Core Skills
| W2-T1 | code-onboard SKILL.md | DONE |
| W2-T2 | code-update SKILL.md | DONE |
| W2-T3 | code-search SKILL.md | DONE |

### Wave 2.5 — Polish
| W2.5-T1 | German → English | DONE |
| W2.5-T2 | .env loading | DONE |

### Wave 2.6 — Critical Bugfixes
| W2.6-T1 | Path format mismatch | DONE |
| W2.6-T2 | Vector type error | DONE |
| W2.6-T3 | requirements.txt | DONE |
| W2.6-T4 | Onboard re-run fix | DONE |
| W2.6-T5 | Shell injection fix | DONE |

### Wave 3 — README
| W3-T1 | README.md + FAQ | DONE |

## Accepted Risks
- tcr_index.py duplicated in onboard + update (drift risk)

## Relational Layer (feature/relational-layer)

### Wave 5 — Phase 1: AST Layer
| W5-T1 | Entity + relation tables in onboard | DONE |
| W5-T2 | AST parsing step in onboard | DONE |
| W5-T3 | Entity/relation cleanup in update | DONE |
| W5-T4 | code-overview skill | DONE |

### Wave 6 — Phase 2: Hierarchical Summaries
| W6-T1 | Summaries table in onboard | DONE |
| W6-T2 | File-level summaries | DONE |
| W6-T3 | Module + repo summaries | DONE |

### Wave 7 — Phase 3: Hybrid Query
| W7-T1 | code-explain skill | DONE |
| W7-T2 | Update consolidation + README | DONE |

---

## V2 Tasks — Provider Switch + Config + Rename

### Wave 8 — Rename ✓ DONE
| W8-T1 | Rename skill dirs code-* → tcr-*, update plugin.json paths | DONE |
| W8-T2 | Update SKILL.md frontmatter names + plugin.json name fields | DONE |
| W8-T3 | Update README.md command references | DONE |
| W8-T4 | Verify — zero code-* references remain | DONE |

### Wave 9 — Config + Info ✓ DONE
| W9-T1 | Create skills/tcr-config/SKILL.md (wizard + change + reset) | DONE |
| W9-T2 | Create skills/tcr-info/SKILL.md (config + projects + commands) | DONE |
| W9-T3 | Update plugin.json — register tcr-config + tcr-info (7 skills) | DONE |

### Wave 10 — Provider Switch ✓ DONE
| W10-T1 | Add 3-layer config loader to all 5 SKILL.md embedded scripts | DONE |
| W10-T2 | Add OpenRouter LLM provider in tcr-onboard SKILL.md | DONE |
| W10-T3 | Add OpenRouter LLM provider in tcr-update SKILL.md | DONE |

### Wave 11 — Parallel + Model List ✓ DONE
| W11-T1 | ThreadPoolExecutor parallel OpenRouter calls in tcr-onboard + tcr-update | DONE |
| W11-T2 | Live model list from OpenRouter API in tcr-config | DONE |

### Wave 12 — Embedding Provider ✓ DONE
| W12-T1 | EMBEDDING_PROVIDER toggle in tcr-config + config.json | DONE |
| W12-T2 | OpenRouter embedding calls in onboard/update/search/explain | DONE |

### Wave 13 — Supabase
| W13-T1 | DB_PROVIDER toggle in tcr-config + Supabase connection handling | TODO |
| W13-T2 | Audit + fix SQL for Supabase pooler in tcr-onboard + tcr-update | TODO |
| W13-T3 | Supabase docs in README + tcr-info (cloud setup section) | TODO |

### Wave 14 — Test Suite
| W14-T1 | Create tests/conftest.py + tests/test_sanitize.py (9 tests) | TODO |
| W14-T2 | Create tests/test_config.py — config loader priority (7 tests) | TODO |
| W14-T3 | Create tests/test_db.py — schema/entity/vector/summary (9 tests) | TODO |
| W14-T4 | Create tests/test_e2e.py — onboard → search → verify (5 tests) | TODO |
