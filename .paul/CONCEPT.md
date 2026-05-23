# CONCEPT — total-code-recall

## Ben Noob Section
**Was ist das?** Ein Claude Code Plugin das deinen Code durchsuchbar macht — ohne dass ein Agent jedes Mal alle Files lesen muss. Einmal indexieren, danach per Suchbegriff sofort die richtige Stelle finden. Spart Token, spart Zeit, Agent hat mehr Context Window frei zum Denken.

**Drei Skills:**
- `/code-onboard` — Projekt zum ersten Mal indexieren
- `/code-update` — Neue Commits nachindexieren
- `/code-search` — Code semantisch durchsuchen

**Alles lokal.** Kein Cloud-LLM, kein API-Key nötig. Ollama + PostgreSQL + pgvector.

---

## Objective

Ein publishbares Claude Code Plugin (`BenjaminSchr/total-code-recall`) das jedes Git-Projekt lokal indexiert und per semantischer Suche durchsuchbar macht. Ziel: Agenten kommen schneller und günstiger in ein Projekt rein ohne Full-Grab auf alle Files.

---

## Acceptance Criteria

### AC-1: Onboard
**Given** ein Projekt mit Git-Repo und Code-Dateien
**When** der User `/code-onboard` aufruft
**Then** werden alle relevanten Dateien in Chunks aufgeteilt, summarized, embedded und in der DB gespeichert. Letzter Commit-Hash wird in `_index_meta` vermerkt.

### AC-2: Onboard ohne Git
**Given** ein Verzeichnis ohne Git-Repo
**When** der User `/code-onboard` aufruft
**Then** bekommt er die Meldung: "Kein Git-Repo gefunden. Bitte erst `git init` ausführen."

### AC-3: Update
**Given** ein bereits indexiertes Projekt mit neuen Commits seit letztem Index
**When** der User `/code-update` aufruft
**Then** werden nur die geänderten Dateien neu indexiert (Delete + Re-Insert). `_index_meta` wird aktualisiert.

### AC-4: Search
**Given** ein indexiertes Projekt
**When** der User `/code-search "Datumsfilter"` aufruft
**Then** bekommt er Top 10 Ergebnisse mit: Dateiname, Zeilennummern, Typ (summary/code), Similarity Score und vollem Chunk-Inhalt.

### AC-5: Search Dedup
**Given** ein Chunk der sowohl über Summary als auch über Code matcht
**When** die Search-Results zusammengestellt werden
**Then** erscheint der Chunk nur einmal (höchster Score gewinnt): `GROUP BY chunk_id, ORDER BY MAX(similarity)`.

### AC-6: Portabilität
**Given** ein externer User der das Plugin installiert
**When** er die README folgt
**Then** kann er mit eigenem Ollama + pgvector-Container alles lokal betreiben. Kein Cloud-LLM nötig.

### AC-7: Git Gate
**Given** jeder Skill-Aufruf
**When** kein Git-Repo im aktuellen Verzeichnis
**Then** wird der Skill abgebrochen mit Hinweis auf `git init`.

### AC-8: Modellwechsel
**Given** ein User der ein anderes Embedding-Modell konfiguriert
**When** er `/code-onboard` erneut aufruft
**Then** erkennt der Skill den Modellwechsel (via `embedding_model` Spalte) und re-indexiert automatisch.

---

## Technical Decisions

| Entscheidung | Wert | Begründung |
|---|---|---|
| Summary LLM | devstral:24b (lokal, Ollama) | Code-optimiert, gratis, offline |
| Embedding LLM | Ein Modell für beides (Default: nomic-embed-text) | Simplicity, ein Call pro Suche |
| Chunk-Size | 50 Zeilen, 15 Overlap | Balance Kontext vs. Embedding-Qualität |
| Chunking-Strategie | Fixed-Size, sprachagnostisch | Universell, kein Parser nötig |
| Min. File-Size | Unter 3 Zeilen → skip | Leere __init__.py etc. bringen keinen Mehrwert |
| DB-Schema | Eine Tabelle pro Projekt | Risikominimierung, einfaches Löschen/Neubauen |
| Tabellenname | Git Repo-Name, sanitized (lowercase, `-`→`_`) | Eindeutig, automatisch |
| Embedding-Storage | Zwei Zeilen pro Chunk (summary + code) | Redundanz als Sicherheitsnetz, jeder Typ optimal embedded |
| Update-Logik | Delete + Re-Insert pro geänderter Datei | Immer aktueller Stand, kein Zombie-Daten |
| Search-Ergebnis | Top 10, voller Chunk | Agent bekommt genug Kontext |
| Search-Dedup | GROUP BY chunk_id, MAX(similarity) | Chunk erscheint nur einmal |
| Vector-Index | HNSW (nicht IVFFlat) | 2026 Best Practice, besserer Recall, schnellere Queries |
| DB-Zugriff | psycopg2 via DATABASE_URL | Portabel, kein docker exec für Bulk |
| DB-Isolation | Eigene DB (code_index_db) + eigener User (code_index_user) | Agenten können andere Tabellen nicht sehen |
| File-Allowlist | .py .html .sql .js .css .yaml .json .toml .md .sh | Code-relevant, kein Ballast |
| Git-Gate | Kein Repo = kein Indexing | Safeguard + Commit-Tracking braucht Git |

---

## DB Schema

### Projekt-Tabelle (eine pro Projekt, z.B. `tokenwatch`)

```sql
CREATE TABLE {project_name} (
    id SERIAL PRIMARY KEY,
    chunk_id INT NOT NULL,
    type VARCHAR(10) NOT NULL CHECK (type IN ('summary', 'code')),
    file_path TEXT NOT NULL,
    line_start INT NOT NULL,
    line_end INT NOT NULL,
    content TEXT NOT NULL,
    commit_hash VARCHAR(40) NOT NULL,
    commit_message TEXT,
    embedding_model VARCHAR(100) NOT NULL,
    embedding vector(768),
    indexed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON {project_name} USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON {project_name} (chunk_id);
CREATE INDEX ON {project_name} (file_path);
```

### Meta-Tabelle (eine für alle Projekte)

```sql
CREATE TABLE _index_meta (
    project VARCHAR(100) PRIMARY KEY,
    last_commit_hash VARCHAR(40),
    last_indexed_at TIMESTAMP,
    chunk_count INT DEFAULT 0,
    embedding_model VARCHAR(100)
);
```

---

## Pipeline

### Onboard
```
git rev-parse --is-inside-work-tree → Fail? → "Mach erstmal git init"
                                    → OK ↓
Repo-Name extrahieren → sanitize → Tabellenname
Embedding-Modell booten (ollama pull falls nötig)
Summary-Modell booten (ollama pull falls nötig)
                    ↓
Alle Files filtern (Allowlist + min 3 Zeilen)
                    ↓
Für jede Datei:
    → Fixed-Size Chunks (50 Zeilen, 15 Overlap)
    → Für jeden Chunk:
        → devstral:24b → Summary generieren
        → Embedding-Modell → Summary embedden → Row 1
        → Embedding-Modell → Code embedden → Row 2
        → Batch INSERT in DB
                    ↓
HEAD Commit-Hash → _index_meta speichern
```

### Update
```
_index_meta.last_commit_hash lesen
git log {last_hash}..HEAD → geänderte Dateien
                    ↓
Für jede geänderte Datei:
    → DELETE FROM {project} WHERE file_path = %s
    → Neu chunken → summarizen → embedden → INSERT
                    ↓
Neuen HEAD Commit-Hash → _index_meta updaten

Gelöschte Dateien:
    → git diff --name-status → Status 'D'
    → DELETE FROM {project} WHERE file_path = %s
```

### Search
```
User-Query empfangen
    → Embedding-Modell → Query embedden
    → SELECT *, 1 - (embedding <=> %s) AS similarity
      FROM {project}
      GROUP BY chunk_id  -- Dedup
      ORDER BY MAX(similarity) DESC
      LIMIT 10
    → Ergebnis formatieren:
      File, Lines, Type, Score, Content
```

---

## File Exclusions

### Allowlist (wird indexiert)
`.py`, `.html`, `.sql`, `.js`, `.css`, `.yaml`, `.json`, `.toml`, `.md`, `.sh`

### Blocklist (wird immer ignoriert)
`venv/`, `__pycache__/`, `.git/`, `node_modules/`, `data/`, `.env`, `*.min.css`, `*.min.js`, `*.pyc`, `*.png`, `*.jpg`, `*.pdf`, `*.woff`, `*.ttf`, `*.ico`

### Min. File-Size
Dateien unter 3 Zeilen werden übersprungen.

---

## Plugin Structure

```
total-code-recall/
├── plugin.json                  ← Manifest
├── README.md                    ← Setup, Use Cases, Screenshots
├── LICENSE                      ← MIT (bereits vorhanden)
├── docker-compose.yaml          ← pgvector Container für externe User
├── .env.example                 ← DATABASE_URL, EMBEDDING_MODEL, SUMMARY_MODEL
├── skills/
│   ├── code-onboard/
│   │   └── SKILL.md             ← Onboard-Skill Instruktionen
│   ├── code-update/
│   │   └── SKILL.md             ← Update-Skill Instruktionen
│   └── code-search/
│       └── SKILL.md             ← Search-Skill Instruktionen
└── scripts/
    └── setup_db.sql             ← CREATE EXTENSION + Template-Tabellen
```

---

## Milestones & Waves

### M0 — Plugin Scaffold + DB Setup
**Wave 0:** Prerequisites Check
**Wave 1:** Plugin-Grundstruktur
- plugin.json, .env.example, .gitignore
- docker-compose.yaml (pgvector Container) ← Aktivierungscode nötig
- scripts/setup_db.sql (Extension + _index_meta Tabelle)

### M1 — /code-onboard Skill
**Wave 0:** Prerequisites (Ollama Modelle verfügbar, DB erreichbar)
**Wave 1:** SKILL.md für code-onboard
- Git-Gate Check
- File Discovery (Allowlist/Blocklist)
- Chunking-Logik (50 Zeilen, 15 Overlap)
- Summary-Generierung (devstral via Ollama)
- Embedding (nomic-embed-text via Ollama)
- Bulk Insert in DB
- _index_meta Update

### M2 — /code-update Skill
**Wave 0:** Prerequisites (M1 done, Projekt bereits indexiert)
**Wave 1:** SKILL.md für code-update
- Commit-Diff seit letztem Index
- Delete + Re-Insert für geänderte Dateien
- Gelöschte Dateien erkennen und aus DB entfernen
- _index_meta Update

### M3 — /code-search Skill
**Wave 0:** Prerequisites (M1 done, Daten in DB)
**Wave 1:** SKILL.md für code-search
- Query embedden
- Vector Similarity Search
- Dedup (GROUP BY chunk_id)
- Top 10 Ergebnis-Formatierung

### M4 — Polish & Publish
**Wave 1:** README.md (Setup-Anleitung, Use Cases, Screenshots)
**Wave 2:** Testen mit echtem Projekt (z.B. Tokenwatch)
**Wave 3:** Git push, GitHub Repo finalisieren

---

## Boundaries — NOT in Scope

- ❌ Cloud LLMs / API-Keys
- ❌ AST-basiertes Chunking (kommt ggf. später als Optimierung)
- ❌ Cross-Projekt-Suche (eine Tabelle = ein Projekt)
- ❌ Web-UI / Dashboard
- ❌ Automatische Hooks (kein post-commit auto-update)
- ❌ Multi-User / Auth
- ❌ Streaming / Real-Time Updates

---

## Open Questions — RESOLVED

| Frage | Antwort |
|---|---|
| Was embedden? | Beides: Summary + Code, zwei Zeilen pro Chunk |
| Welches Embedding-Modell? | Ein Modell für beides, Default nomic-embed-text, konfigurierbar |
| Welches Summary-Modell? | devstral:24b lokal |
| Chunk-Size? | 50 Zeilen, 15 Overlap, fixed-size |
| Update-Logik? | Delete + Re-Insert, kein Append |
| DB-Zugriff? | psycopg2 via DATABASE_URL |
| Tabellenname? | Git Repo-Name, sanitized |
| Git erforderlich? | Ja, kein Git = kein Index |
| File-Filter? | Allowlist + Blocklist + Min 3 Zeilen |
| Search-Results? | Top 10, voller Chunk, dedupliziert |
| Cloud oder lokal? | 100% lokal |
| Skill oder Plugin? | Plugin (publishable) |

---

## Blocked

- None — Aktivierungscode AlphaBravoZulu1984 wurde erteilt
