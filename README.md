## orderflow-recorder

Ein schlanker, erweiterbarer Python-Service, der öffentliche Binance USDT‑M Futures Marktdaten (Orderbuch + Trades) per WebSocket empfängt und 24/7 in eine Postgres-Datenbank schreibt. Fokus zunächst auf `BTCUSDT` und `ETHUSDT`. Keine Private-Endpunkte, keine API Keys (keyless).

### Features

- Öffentliche Binance-Futures via WebSocket: `depth5@100ms` und `aggTrade`
- Normalisierte Events (Trades, Orderbuch-Updates)
- Trennung von Ingest (WS) und Persistenz (Sinks/DB)
- Postgres-Persistenz via SQLAlchemy 2.x
- Robuste WS-Reconnect-Logik (exponentieller Backoff)
- Docker/Compose bereit

### Tech-Stack

- Python 3.11
- Poetry (Dependency-Management)
- websockets (WS-Client)
- pydantic v2 + pydantic-settings (Config)
- SQLAlchemy 2.x (Postgres, Treiber: `psycopg2-binary`)
- loguru (Logging)

### Projektstruktur (Auszug)

```
src/orderflow_recorder/
  __main__.py                    # einfacher Startpunkt (Skeleton)
  config/settings.py             # Pydantic Settings + get_settings()
  binance/ws_client.py           # FuturesWSClient, Parser, RecorderCallbacks
  ingest/runner.py               # zentraler Ingest-Runner (Entry-Point)
  storage/
    db.py                        # Engine/Session, init-db CLI
    models.py                    # SQLAlchemy-Modelle
    sinks.py                     # Sink-Interfaces (Protocols)
    postgres_sinks.py            # konkrete Postgres-Sinks
  utils/logging.py               # Loguru-Setup
tests/
```

### Installation (lokal)

Voraussetzungen: Python 3.11 und Poetry installiert.

```bash
poetry install
```

### Konfiguration

Settings basieren auf Pydantic v2 (pydantic-settings). ENV-Variablen können via `.env` gesetzt werden (siehe `.env.example`):

- `DB_URL` (Default Dev): `postgresql+psycopg2://postgres:postgres@localhost:5432/orderflow_recorder`
- `LOG_LEVEL` (Default: `INFO`)
- Optional:
  - `BINANCE_WS_FUTURES_BASE_URL` (Default: `wss://fstream.binance.com/stream`)
  - `SYMBOLS_FUTURES` (Default: `["btcusdt","ethusdt"]`)
  - `FUTURES_STREAMS_DEPTH` (Default: `depth5@100ms`)
  - `FUTURES_STREAMS_TRADES` (Default: `aggTrade`)

### Datenbank initialisieren

```bash
# Postgres muss laufen (lokal oder via Docker)
poetry run python -m orderflow_recorder.storage.db init-db
```

### Start (lokal)

Empfohlener Entry-Point ist der Ingest-Runner:

```bash
poetry run orderflow-recorder
```

Optionales Logging-Level:

```bash
LOG_LEVEL=DEBUG poetry run orderflow-recorder
```

### Docker / Docker Compose

Schnellstart über Compose (startet Postgres + Recorder):

```bash
docker compose up --build
```

Compose setzt im `recorder`-Service automatisch:

```
DB_URL=postgresql+psycopg2://postgres:postgres@db:5432/orderflow_recorder
```

Nur DB starten:

```bash
docker compose up -d db
docker compose exec db pg_isready -U postgres
```

### Tests

```bash
poetry run pytest -q
```

Optionaler Ingest-Smoke-Test (Integration, benötigt Internet & laufende DB):

```bash
RUN_INGEST_SMOKE=1 poetry run pytest -q tests/test_ingest_smoke.py
```

### Hinweise

- Zentrales Logging: `src/orderflow_recorder/utils/logging.py`
- WS-Client: `src/orderflow_recorder/binance/ws_client.py`
- Sinks-Interfaces: `src/orderflow_recorder/storage/sinks.py`
- Postgres-Sinks: `src/orderflow_recorder/storage/postgres_sinks.py`
- Entry-Point (Console Script): `orderflow-recorder` → `orderflow_recorder.ingest.runner:main`
