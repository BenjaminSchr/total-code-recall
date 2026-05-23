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
        {
            "id": "chunk_1",
            "file_path": "app/main.py",
            "line_start": 1,
            "line_end": 50,
            "content": "def hello():\n    return 'world'\n",
        },
        {
            "id": "chunk_2",
            "file_path": "app/utils.py",
            "line_start": 1,
            "line_end": 30,
            "content": "def add(a, b):\n    return a + b\n",
        },
    ]
