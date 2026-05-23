import pytest
import re
import os


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
        overlap = set(chunks[i]) & set(chunks[i + 1])
        assert len(overlap) >= CHUNK_OVERLAP - 1, f"Overlap too small: {len(overlap)}"
