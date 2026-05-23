**Task:** TASK_W14-T1 — Create tests/conftest.py + tests/test_sanitize.py
**Status:** TODO

**File:** tests/conftest.py (create), tests/test_sanitize.py (create)
**Branch:** task/W14-T1-test-scaffold-sanitize
**Worker type:** Claude Code

**What changes:**
Creates the `tests/` directory from scratch (it does not exist yet). Writes `conftest.py` with shared fixtures and `test_sanitize.py` testing path sanitization, digit-prefix stripping, and chunk boundary logic extracted or reimplemented from the tcr-onboard embedded Python.

**Ben noob section:**
Bisher gibt es keine Tests. Dieser Task erstellt die Test-Infrastruktur und die ersten Tests für die häufigsten Bugs: Pfade die komische Zeichen enthalten, Dateinamen die mit Zahlen anfangen, und ob Chunks die richtige Größe haben.

**Pattern:**

**tests/conftest.py:**
```python
import pytest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Shared constants
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://code_index_user:code_index_pass@localhost:5434/code_index_db"
)

@pytest.fixture
def sample_project_path(tmp_path):
    """Create a minimal fake project for testing."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("def hello():\n    return 'world'\n")
    (tmp_path / "app" / "utils.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / ".git").mkdir()
    return tmp_path

@pytest.fixture
def sample_chunks():
    """Sample chunk data for testing."""
    return [
        {"id": "chunk_1", "file_path": "app/main.py", "line_start": 1, "line_end": 50, "content": "def hello():\n    return 'world'\n"},
        {"id": "chunk_2", "file_path": "app/utils.py", "line_start": 1, "line_end": 30, "content": "def add(a, b):\n    return a + b\n"},
    ]
```

**tests/test_sanitize.py:**
```python
import pytest
import re

# --- Path sanitization logic (copied from SKILL.md embedded scripts) ---

def sanitize_project_name(path):
    """Convert project path to a valid PostgreSQL table name prefix."""
    name = os.path.basename(path.rstrip("/"))
    name = re.sub(r"[^a-z0-9_]", "_", name.lower())
    # Strip leading digits (table names can't start with a digit)
    name = re.sub(r"^[0-9]+", "", name)
    if not name:
        name = "project"
    return name

import os

# --- Tests ---

def test_sanitize_simple_name():
    assert sanitize_project_name("/home/user/myproject") == "myproject"

def test_sanitize_strips_trailing_slash():
    assert sanitize_project_name("/home/user/myproject/") == "myproject"

def test_sanitize_hyphens_to_underscores():
    assert sanitize_project_name("/home/user/my-project") == "my_project"

def test_sanitize_spaces_to_underscores():
    assert sanitize_project_name("/home/user/my project") == "my_project"

def test_sanitize_digit_prefix_stripped():
    result = sanitize_project_name("/home/user/123project")
    assert not result[0].isdigit(), f"Name starts with digit: {result}"

def test_sanitize_uppercase_lowercased():
    assert sanitize_project_name("/home/user/MyProject") == "myproject"

def test_sanitize_empty_after_strip_falls_back():
    # All digits → stripped → empty → fallback to "project"
    result = sanitize_project_name("/home/user/123")
    assert result == "project"

def test_chunk_size_respects_config():
    """Chunks must not exceed CHUNK_SIZE lines."""
    CHUNK_SIZE = 50
    CHUNK_OVERLAP = 15
    lines = list(range(1, 201))  # 200 lines

    chunks = []
    start = 0
    while start < len(lines):
        end = min(start + CHUNK_SIZE, len(lines))
        chunks.append(lines[start:end])
        start += CHUNK_SIZE - CHUNK_OVERLAP

    for chunk in chunks:
        assert len(chunk) <= CHUNK_SIZE, f"Chunk too large: {len(chunk)} > {CHUNK_SIZE}"

def test_chunk_overlap_produces_continuity():
    """Adjacent chunks must overlap by CHUNK_OVERLAP lines."""
    CHUNK_SIZE = 50
    CHUNK_OVERLAP = 15
    lines = list(range(1, 201))

    chunks = []
    start = 0
    while start < len(lines):
        end = min(start + CHUNK_SIZE, len(lines))
        chunks.append(lines[start:end])
        start += CHUNK_SIZE - CHUNK_OVERLAP

    for i in range(len(chunks) - 1):
        overlap = set(chunks[i]) & set(chunks[i+1])
        assert len(overlap) >= CHUNK_OVERLAP - 1, f"Overlap too small: {len(overlap)}"
```

**Input/Output Contract:**
Depends on: nothing (creates test infrastructure from scratch)
Produces: `tests/` directory, `tests/conftest.py`, `tests/test_sanitize.py`

**Verify:**
```bash
cd /home/bengpu/Schreibtisch/Workspace/projekte/Toolproject/total-code-recall && python3 -m pytest tests/test_sanitize.py -v 2>&1 | tail -20
```
All tests must pass.

**Done when:**
`tests/conftest.py` and `tests/test_sanitize.py` exist. All 9 tests in test_sanitize.py pass with `python3 -m pytest tests/test_sanitize.py -v`.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W14-T1.md`. Create the `tests/` directory. Write `tests/conftest.py` with the shared fixtures. Write `tests/test_sanitize.py` with all 9 tests. Run `python3 -m pytest tests/test_sanitize.py -v` — all must pass. Write Execution Log, rename to `DONE_TASK_W14-T1.md`, commit: `test: TASK_W14-T1 — create test scaffold + sanitize/chunking tests`.
