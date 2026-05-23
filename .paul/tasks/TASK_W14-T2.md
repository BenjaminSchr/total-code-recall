**Task:** TASK_W14-T2 — Create tests/test_config.py — config loader priority order
**Status:** TODO

**File:** tests/test_config.py (create)
**Branch:** task/W14-T2-test-config-loader
**Worker type:** Claude Code

**What changes:**
Creates `tests/test_config.py` that tests the 3-layer config loader logic: env var overrides global config.json, which overrides the hardcoded default. Uses temp files and monkeypatching — no real `~/.config/` directory touched.

**Ben noob section:**
Testet dass die Config-Priorität korrekt ist: `.env` schlägt `config.json` schlägt Default. Das ist wichtig weil wenn die Reihenfolge falsch ist, nutzt jemand plötzlich den falschen API Key.

**Pattern:**

```python
# tests/test_config.py
import pytest
import json
import os
import tempfile

# --- Reimplemented config loader (mirrors the pattern in SKILL.md scripts) ---

def make_cfg_loader(config_path, env_overrides=None):
    """Factory that returns a _cfg() function using the given config.json path and env."""
    global_config = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            global_config = json.load(f)

    env = env_overrides or {}

    def _cfg(env_key, config_key, default):
        return env.get(env_key) or global_config.get(config_key) or default

    return _cfg

# --- Tests ---

def test_env_var_wins_over_config_json(tmp_path):
    """Env var takes priority over config.json value."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"database_url": "postgres://from-config"}))
    cfg = make_cfg_loader(str(config_file), env_overrides={"DATABASE_URL": "postgres://from-env"})
    assert cfg("DATABASE_URL", "database_url", "postgres://default") == "postgres://from-env"

def test_config_json_wins_over_default(tmp_path):
    """config.json takes priority over hardcoded default."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"database_url": "postgres://from-config"}))
    cfg = make_cfg_loader(str(config_file), env_overrides={})
    assert cfg("DATABASE_URL", "database_url", "postgres://default") == "postgres://from-config"

def test_default_used_when_nothing_set(tmp_path):
    """Default is used when env var and config.json are both absent."""
    config_file = tmp_path / "nonexistent.json"  # doesn't exist
    cfg = make_cfg_loader(str(config_file), env_overrides={})
    assert cfg("DATABASE_URL", "database_url", "postgres://default") == "postgres://default"

def test_missing_config_file_does_not_crash(tmp_path):
    """Missing config.json is silently ignored, no exception raised."""
    config_file = tmp_path / "missing.json"
    # Should not raise
    cfg = make_cfg_loader(str(config_file), env_overrides={})
    result = cfg("OLLAMA_URL", "ollama_url", "http://localhost:11434")
    assert result == "http://localhost:11434"

def test_env_var_empty_string_falls_through_to_config(tmp_path):
    """Empty string env var does not override config.json (falsy check)."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"ollama_url": "http://from-config:11434"}))
    cfg = make_cfg_loader(str(config_file), env_overrides={"OLLAMA_URL": ""})
    result = cfg("OLLAMA_URL", "ollama_url", "http://localhost:11434")
    assert result == "http://from-config:11434"

def test_config_json_invalid_key_returns_default(tmp_path):
    """Config.json missing key falls back to default."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"other_key": "value"}))
    cfg = make_cfg_loader(str(config_file), env_overrides={})
    result = cfg("EMBEDDING_MODEL", "embedding_model", "nomic-embed-text")
    assert result == "nomic-embed-text"

def test_config_json_all_providers_loaded(tmp_path):
    """Config.json with all keys returns all values correctly."""
    config_data = {
        "llm_provider": "openrouter",
        "openrouter_model": "google/gemini-flash-2.0",
        "embedding_provider": "ollama",
        "db_provider": "local",
        "parallel_workers": 10
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))
    cfg = make_cfg_loader(str(config_file), env_overrides={})
    assert cfg("LLM_PROVIDER", "llm_provider", "ollama") == "openrouter"
    assert cfg("EMBEDDING_PROVIDER", "embedding_provider", "ollama") == "ollama"
    assert cfg("DB_PROVIDER", "db_provider", "local") == "local"
```

**Input/Output Contract:**
Depends on: TASK_W14-T1 (tests/ directory and conftest.py exist)
Produces: `tests/test_config.py` with 7 config loader tests

**Verify:**
```bash
cd /home/bengpu/Schreibtisch/Workspace/projekte/Toolproject/total-code-recall && python3 -m pytest tests/test_config.py -v 2>&1 | tail -20
```
All 7 tests must pass.

**Done when:**
`tests/test_config.py` exists. All 7 tests pass with `python3 -m pytest tests/test_config.py -v`. No real `~/.config/` directory is read — only `tmp_path` fixtures.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W14-T2.md`. Write `tests/test_config.py` with the `make_cfg_loader()` factory and all 7 tests. Run `python3 -m pytest tests/test_config.py -v` — all must pass. Write Execution Log, rename to `DONE_TASK_W14-T2.md`, commit: `test: TASK_W14-T2 — config loader priority tests (env > config.json > default)`.
