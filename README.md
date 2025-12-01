## orderflow-recorder

Ein schlanker, aber erweiterbarer Python-Service, der öffentliche Binance USDT‑M Futures Marktdaten (Orderbuch + Trades) per WebSocket empfängt und 24/7 in eine Postgres-Datenbank schreibt. Zunächst fokussiert auf `BTCUSDT` und `ETHUSDT`. Keine Private-Endpunkte, keine API Keys (keyless).

### Tech-Stack

- Python 3.11
- Poetry (Dependency-Management)
- SQLAlchemy 2.x (Postgres, async via `asyncpg`)
- websockets (für WebSockets)
- pydantic (Config / Models)
- loguru (Logging)

### Lokales Setup

Voraussetzungen: Python 3.11 und Poetry installiert.

```bash
poetry install
```

Starten (Skeleton / Smoke-Test):

```bash
poetry run python -m orderflow_recorder
```

Optionales Logging-Level:

```bash
LOG_LEVEL=DEBUG poetry run python -m orderflow_recorder
```

### Projektstruktur

```
src/orderflow_recorder/
  __init__.py
  __main__.py
  config/
  binance/
  storage/
  ingest/
  utils/
tests/
pyproject.toml
README.md
```

In `utils/logger.py` befindet sich das zentrale Logging-Setup (loguru). In den nächsten Schritten folgen: WebSocket-Ingest für Binance-Futures (Orderbuch + Trades) und Persistierung per SQLAlchemy in Postgres.
