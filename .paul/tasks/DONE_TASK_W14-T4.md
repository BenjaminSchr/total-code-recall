**Task:** TASK_W14-T4 — Create tests/test_e2e.py — fixture project onboard → search → verify results
**Status:** DONE

**File:** tests/test_e2e.py (create)
**Branch:** task/W14-T4-test-e2e-onboard-search
**Worker type:** Claude Code

**What changes:**
Creates `tests/test_e2e.py` with an end-to-end test that creates a fixture project directory, runs the tcr-onboard embedded Python logic against it (extracted as functions), then runs tcr-search logic and verifies results come back. Requires running Ollama (or skips if unavailable). Uses a unique project name to avoid collision with real data.

**Ben noob section:**
Der komplette Ablauf als Test: Fixture-Projekt erstellen → indexieren → suchen → prüfen ob Ergebnisse kommen. Wenn Ollama nicht läuft wird der Test übersprungen statt zu crashen.

**Pattern:**

```python
# tests/test_e2e.py
import pytest
import os
import psycopg2
import requests
import uuid

# Skip if prerequisites not available
DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")

def _ollama_available():
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False

def _db_available():
    if not DATABASE_URL:
        return False
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        return True
    except Exception:
        return False

pytestmark = pytest.mark.skipif(
    not (_ollama_available() and _db_available()),
    reason="Ollama or database not available — skipping E2E tests"
)

E2E_PROJECT = f"e2e_{uuid.uuid4().hex[:8]}"

# --- Minimal reimplementation of onboard/search logic for testing ---

def embed(text):
    resp = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
        "model": EMBEDDING_MODEL,
        "prompt": text
    }, timeout=60)
    resp.raise_for_status()
    return resp.json()["embedding"]

def index_file(conn, project, file_path, content):
    """Index a single file into the project tables."""
    chunk_id = f"{project}_{uuid.uuid4().hex[:8]}"
    emb = embed(content)
    with conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {project}_index (id, file_path, line_start, line_end, content, summary, embedding, summary_embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s::vector)
            ON CONFLICT (id) DO NOTHING
        """, (chunk_id, file_path, 1, content.count("\n"), content, "Test summary.", emb, emb))
    conn.commit()

def search(conn, project, query, top_k=3):
    """Semantic search over project index."""
    q_emb = embed(query)
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT file_path, content, 1 - (embedding <=> %s::vector) AS score
            FROM {project}_index
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (q_emb, q_emb, top_k))
        return cur.fetchall()

@pytest.fixture(scope="module")
def e2e_db(tmp_path_factory):
    """Setup: create tables and index fixture files. Teardown: drop tables."""
    conn = psycopg2.connect(DATABASE_URL)

    # Create index table
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {E2E_PROJECT}_index (
                id TEXT PRIMARY KEY,
                file_path TEXT,
                line_start INT,
                line_end INT,
                content TEXT,
                summary TEXT,
                embedding vector(768),
                summary_embedding vector(768)
            )
        """)
    conn.commit()

    # Index two fixture files
    index_file(conn, E2E_PROJECT, "app/main.py",
               "def authenticate_user(username, password):\n    '''Validates user credentials.'''\n    return check_db(username, password)\n")
    index_file(conn, E2E_PROJECT, "app/utils.py",
               "def format_currency(amount, currency='EUR'):\n    '''Formats a number as currency string.'''\n    return f'{amount:.2f} {currency}'\n")

    yield conn

    # Cleanup
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {E2E_PROJECT}_index CASCADE")
    conn.commit()
    conn.close()

def test_e2e_onboard_creates_rows(e2e_db):
    """After indexing, the index table has rows."""
    with e2e_db.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {E2E_PROJECT}_index")
        count = cur.fetchone()[0]
    assert count >= 2

def test_e2e_search_returns_results(e2e_db):
    """Search returns at least 1 result."""
    results = search(e2e_db, E2E_PROJECT, "user authentication", top_k=3)
    assert len(results) >= 1

def test_e2e_search_top_result_is_relevant(e2e_db):
    """Semantic search: auth query returns auth file as top result."""
    results = search(e2e_db, E2E_PROJECT, "user authentication login", top_k=3)
    assert len(results) >= 1
    top_file = results[0][0]
    assert top_file == "app/main.py", f"Expected auth file, got: {top_file}"

def test_e2e_search_currency_query(e2e_db):
    """Semantic search: currency query returns utils file."""
    results = search(e2e_db, E2E_PROJECT, "format money currency EUR", top_k=3)
    assert len(results) >= 1
    top_file = results[0][0]
    assert top_file == "app/utils.py", f"Expected utils file, got: {top_file}"

def test_e2e_search_scores_in_range(e2e_db):
    """All search scores must be between 0 and 1."""
    results = search(e2e_db, E2E_PROJECT, "any query", top_k=5)
    for _, _, score in results:
        assert 0.0 <= float(score) <= 1.0, f"Score out of range: {score}"
```

**Input/Output Contract:**
Depends on: TASK_W14-T1 (tests/ dir and conftest.py exist), TASK_W14-T3 (DB patterns established)
Produces: `tests/test_e2e.py` with 5 end-to-end tests

**Verify:**
```bash
cd /home/bengpu/Schreibtisch/Workspace/projekte/Toolproject/total-code-recall && python3 -m pytest tests/test_e2e.py -v 2>&1 | tail -20
```
All tests must PASS or SKIP cleanly (no errors).

**Done when:**
`tests/test_e2e.py` exists. Tests either pass (with real Ollama + DB) or skip cleanly. No import errors. Running the full suite `python3 -m pytest tests/ -v` collects all 4 test files without errors.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W14-T4.md`. Write `tests/test_e2e.py` with the 5 E2E tests. Run `python3 -m pytest tests/ -v` — all must PASS or SKIP, no errors. Write Execution Log, rename to `DONE_TASK_W14-T4.md`, commit: `test: TASK_W14-T4 — E2E test: fixture project onboard → semantic search → verify results`.

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Created tests/test_e2e.py with 5 E2E tests. Tests skip cleanly when Ollama or DB not available (pytestmark.skipif on module level). Full test suite result: 16 passed, 13 skipped, 0 errors — all 4 test files collected and run cleanly.
- Files Changed: tests/test_e2e.py (created)
- Issues: none
- Status: DONE
