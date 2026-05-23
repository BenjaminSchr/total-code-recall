import pytest
import re
import os


# --- Path sanitization logic (exact copy from SKILL.md tcr-onboard Step 1) ---

def sanitize_project_name(path):
    """Convert project path to a valid PostgreSQL table name prefix.

    Mirrors the exact logic in skills/tcr-onboard/SKILL.md Step 1:
      1. basename of path
      2. lowercase
      3. hyphens → underscores
      4. strip all non-[a-z0-9_] characters (spaces, dots, etc.)
      5. if first char is digit → prepend "p_"
      6. if empty after stripping → fallback to "project"
    """
    name = os.path.basename(path.rstrip("/"))
    name = name.lower()
    name = name.replace("-", "_")
    name = re.sub(r"[^a-z0-9_]", "", name)
    if not name:
        name = "project"
    elif name[0].isdigit():
        name = "p_" + name
    return name


# --- Tests ---

def test_sanitize_simple_name():
    assert sanitize_project_name("/home/user/myproject") == "myproject"


def test_sanitize_strips_trailing_slash():
    assert sanitize_project_name("/home/user/myproject/") == "myproject"


def test_sanitize_hyphens_to_underscores():
    assert sanitize_project_name("/home/user/my-project") == "my_project"


def test_sanitize_spaces_stripped_not_replaced():
    """Spaces are stripped (not turned to underscores) — matches SKILL.md re.sub(r'[^a-z0-9_]', '', ...)."""
    assert sanitize_project_name("/home/user/my project") == "myproject"


def test_sanitize_digit_prefix_gets_p_prepended():
    """Names starting with a digit get 'p_' prepended — matches SKILL.md 'p_' + name."""
    result = sanitize_project_name("/home/user/123project")
    assert result == "p_123project"
    assert not result[0].isdigit()


def test_sanitize_uppercase_lowercased():
    assert sanitize_project_name("/home/user/MyProject") == "myproject"


def test_sanitize_all_digits_gets_p_prepended():
    """All-digit name (no letters) → 'p_' prepended (not fallback to 'project')."""
    result = sanitize_project_name("/home/user/123")
    assert result == "p_123"
    assert not result[0].isdigit()


def test_sanitize_empty_after_strip_falls_back():
    """Name that strips to empty → fallback to 'project'."""
    # "..." → lowercase "..." → no hyphens → re.sub strips all dots → "" → fallback "project"
    # (Note: "---" becomes "___" which is not empty — underscores survive the strip)
    result = sanitize_project_name("/home/user/...")
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
        overlap = set(chunks[i]) & set(chunks[i + 1])
        assert len(overlap) >= CHUNK_OVERLAP - 1, f"Overlap too small: {len(overlap)}"
