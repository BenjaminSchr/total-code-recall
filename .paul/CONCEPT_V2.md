# CONCEPT V2 — Provider Switch + Config + Rename

## Ben Noob Section
**Was passiert hier?** Drei Dinge:
1. Alle Commands werden von `code-*` zu `tcr-*` umbenannt
2. Neuer Command `/tcr-config` — einmalig Provider + API Key konfigurieren
3. Neuer Command `/tcr-info` — zeigt Status und Hilfe
4. OpenRouter als LLM-Provider — Onboard in 2 Min statt 40
5. Parallele Summary-Generierung über OpenRouter

---

## Objective

Provider-Switch einbauen damit Onboarding schnell läuft (OpenRouter parallel statt Ollama sequenziell). Globale Config damit der User nur einmal API Key eingibt. Alle Commands zu `tcr-*` umbenennen für kurze, eindeutige Slash-Commands.

---

## Acceptance Criteria

### AC-1: Rename
**Given** das Plugin mit 5 bestehenden `code-*` Commands
**When** der User nach dem Update die Commands nutzt
**Then** heißen alle Commands `tcr-*` (tcr-config, tcr-onboard, tcr-update, tcr-search, tcr-overview, tcr-explain, tcr-info)

### AC-2: Config
**Given** ein User der total-code-recall zum ersten Mal nutzt
**When** er `/tcr-config` aufruft (oder `/tcr-onboard` ohne Config)
**Then** wird er durch 3 Toggles geführt:
  - LLM Summaries: Local (Ollama) / Cloud (OpenRouter)
  - Embeddings: Local (Ollama) / Cloud (OpenRouter)
  - Database: Local (pgvector) / Cloud (Supabase)
**And** bei Cloud-Auswahl wird nach API Key + Model gefragt
**And** die Config wird global gespeichert in `~/.config/total-code-recall/config.json`
**And** er wird nie wieder nach dem Key gefragt

### AC-3: Config ändern
**Given** ein User mit bestehender Config
**When** er `/tcr-config` aufruft
**Then** sieht er die aktuelle Config und kann einzelne Werte ändern (Provider, Key, Model, DB)

### AC-4: Provider Switch
**Given** `LLM_PROVIDER=openrouter` in der Config
**When** `/tcr-onboard` läuft
**Then** werden Summaries über OpenRouter generiert statt lokales Ollama
**And** das OpenRouter API Format (OpenAI-kompatibel) wird korrekt verwendet

### AC-5: Parallel Onboard
**Given** OpenRouter als Provider
**When** `/tcr-onboard` auf einem Projekt mit 500+ Chunks läuft
**Then** werden Summaries parallel generiert (ThreadPoolExecutor, 10 concurrent)
**And** Rate-Limit 429 wird mit Retry gehandelt
**And** Onboard dauert <5 Min statt 40 Min

### AC-6: Model-Liste
**Given** der User wählt OpenRouter als Provider
**When** er nach dem Model gefragt wird
**Then** wird die aktuelle Model-Liste live von der OpenRouter API geholt
**And** gefiltert auf relevante Modelle (Anthropic, Google, OpenAI, Qwen, Kimi)

### AC-7: Info
**Given** ein User mit indexierten Projekten
**When** er `/tcr-info` aufruft
**Then** sieht er: aktuelle Config, alle indexierten Projekte mit Stats, Command-Übersicht

### AC-8: Embedding bleibt lokal
**Given** jede Provider-Konfiguration
**When** Embeddings generiert werden
**Then** werden sie immer über lokales Ollama generiert (nomic-embed-text)
**And** nie über OpenRouter

---

## Technical Decisions

| Entscheidung | Wert | Begründung |
|---|---|---|
| Command-Prefix | `tcr-*` | Kurz, eindeutig, kein Collision |
| Config-Speicherort | `~/.config/total-code-recall/config.json` | XDG-Standard, global, nicht pro Projekt |
| Projekt-Override | `.env` im Projekt-Root | Kann globale Config überschreiben |
| Lookup-Reihenfolge | 1. Projekt .env → 2. Global config.json → 3. System env vars | Spezifisch überschreibt global |
| OpenRouter API Format | OpenAI-kompatibel (`/v1/chat/completions`) | Standard, kein Custom-Format |
| Parallel Workers | 10 concurrent (ThreadPoolExecutor) | Balance Speed vs Rate-Limit |
| Rate-Limit Handling | Exponential Backoff bei 429 | Standard-Pattern |
| Model-Liste | Live von `GET https://openrouter.ai/api/v1/models` | Immer aktuell |
| Model-Filter | Nur: anthropic/*, google/*, openai/*, qwen/*, kimi/* | Relevante Anbieter |
| Embedding | Immer lokal (Ollama) | Schnell genug, keine Cloud nötig |

---

## Global Config Format

`~/.config/total-code-recall/config.json`:
```json
{
  "llm_provider": "openrouter",
  "openrouter_api_key": "sk-or-...",
  "openrouter_model": "google/gemini-flash-2.0",
  "ollama_url": "http://localhost:11434",
  "ollama_summary_model": "devstral:24b",
  "embedding_model": "nomic-embed-text",
  "database_url": "postgresql://code_index_user:code_index_pass@localhost:5434/code_index_db",
  "chunk_size": 50,
  "chunk_overlap": 15,
  "parallel_workers": 10
}
```

---

## Command-Rename Mapping

| Alt | Neu | Skill-Datei |
|-----|-----|-------------|
| `/code-onboard` | `/tcr-onboard` | `skills/tcr-onboard/SKILL.md` |
| `/code-update` | `/tcr-update` | `skills/tcr-update/SKILL.md` |
| `/code-search` | `/tcr-search` | `skills/tcr-search/SKILL.md` |
| `/code-overview` | `/tcr-overview` | `skills/tcr-overview/SKILL.md` |
| `/code-explain` | `/tcr-explain` | `skills/tcr-explain/SKILL.md` |
| — (neu) | `/tcr-config` | `skills/tcr-config/SKILL.md` |
| — (neu) | `/tcr-info` | `skills/tcr-info/SKILL.md` |

---

## Provider Switch — API Mapping

### Ollama (lokal)
```python
response = requests.post(f"{OLLAMA_URL}/api/generate", json={
    "model": SUMMARY_MODEL,
    "prompt": prompt,
    "stream": False
})
summary = response.json()["response"]
```

### OpenRouter (cloud)
```python
response = requests.post("https://openrouter.ai/api/v1/chat/completions", 
    headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200
    }
)
summary = response.json()["choices"][0]["message"]["content"]
```

### Parallel (nur OpenRouter)
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def generate_summary(chunk):
    # OpenRouter call
    ...
    return chunk_id, summary

with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
    futures = {executor.submit(generate_summary, c): c for c in chunks}
    for future in as_completed(futures):
        chunk_id, summary = future.result()
        results[chunk_id] = summary
```

---

## Milestones & Waves

### Wave 8 — Rename (4 Tasks)
- W8-T1: Rename skill directories `code-*` → `tcr-*`, update plugin.json
- W8-T2: Update all SKILL.md frontmatter names + internal cross-references
- W8-T3: Update README.md command references
- W8-T4: Verify — alle alten `code-*` Referenzen weg

### Wave 9 — Config + Info (3 Tasks)
- W9-T1: Create `skills/tcr-config/SKILL.md` — Setup-Wizard + Config-Ändern + Reset
- W9-T2: Create `skills/tcr-info/SKILL.md` — Status + Hilfe
- W9-T3: Update plugin.json — 7 Skills registrieren

### Wave 10 — Provider Switch (3 Tasks)
- W10-T1: Add config loader to all temp scripts (global config.json + .env + env vars)
- W10-T2: Add OpenRouter provider in tcr-onboard (if/else in tcr_index.py + tcr_build_summaries.py)
- W10-T3: Add OpenRouter provider in tcr-update (same pattern)

### Wave 11 — Parallel + Model List (2 Tasks)
- W11-T1: ThreadPoolExecutor für OpenRouter Calls in tcr-onboard + tcr-update
- W11-T2: Live Model-Liste von OpenRouter API in tcr-config

---

### Wave 12 — Embedding Provider (2 Tasks)
- W12-T1: `EMBEDDING_PROVIDER=ollama|openrouter` in Config + tcr-config Wizard
- W12-T2: OpenRouter Embedding-Calls in tcr-onboard, tcr-update, tcr-search, tcr-explain

### Wave 13 — Supabase Integration (3 Tasks)
- W13-T1: `DB_PROVIDER=local|supabase` in Config + tcr-config Wizard
- W13-T2: Supabase Connection-String Handling (SSL, pooler URL, API key auth)
- W13-T3: Update README + tcr-info für den "zero infra" Use Case (OpenRouter + Supabase = nichts lokal außer Claude Code)

---

## Boundaries — NOT in Scope

- ❌ Streaming Responses
- ❌ Cost Tracking / Token-Zähler
- ❌ Multi-User / Auth

---

## Open Questions — RESOLVED

| Frage | Antwort |
|---|---|
| Command-Prefix? | `tcr-*` |
| Config wo? | `~/.config/total-code-recall/config.json` (global) |
| Wie oft Key eingeben? | Einmal, global gespeichert |
| Model-Liste? | Live von OpenRouter API, gefiltert |
| Parallel? | ThreadPoolExecutor, 10 workers, nur bei OpenRouter |
| Embedding Provider? | Immer lokal (Phase 4 der Roadmap — nicht jetzt) |
