## orderflow-recorder

Ein schlanker, produktionsreifer Python‑Dienst, der öffentliche Binance USDT‑M Futures‑Daten (Orderbuch‑Depth + Trades) per WebSocket bezieht, robust streamt und in Google Cloud Storage (GCS) als CSV ablegt. Darauf aufbauend stellt eine optionale FastAPI‑Schicht aggregierte Candle‑Daten (1s/1m) zur Verfügung. Fokus zunächst auf `BTCUSDT` und `ETHUSDT`.

### Features

- Öffentliche Binance‑Futures Streams: `depth5@100ms` und `aggTrade`
- Klare Normalisierung der Events (Trades, Orderbuch‑Updates)
- Robuste Reconnect‑Logik mit exponentiellem Backoff
- Persistenz in GCS als CSV‑Batches (konfigurierbares Buffering)
- Täglicher Aggregations‑Job erzeugt OHLC + Orderflow‑Kennzahlen (1s/1m)
- Optionale REST‑API (FastAPI) für Candles inklusive API‑Key‑Schutz
- Docker‑Image zum direkten Betrieb (Default‑CMD startet den Recorder)

### Architektur (Überblick)

- Ingest: `FuturesWSClient` verbindet kombinierte Binance‑Streams und ruft `RecorderCallbacks` auf.
- Sink: `GcsCsvSink` puffert normalisierte Datensätze pro Symbol und lädt periodisch CSV‑Chunks nach GCS hoch:
  - `raw/{SYMBOL}/{YYYY-MM-DD}/{HH-MM-SS}_trades.csv`
  - `raw/{SYMBOL}/{YYYY-MM-DD}/{HH-MM-SS}_depth.csv`
- Processing: Ein täglicher Job aggregiert Trades zu Candles (1s/1m) und lädt sie nach:
  - `aggregated/{SYMBOL}/{YYYY-MM-DD}_1s.csv`
  - `aggregated/{SYMBOL}/{YYYY-MM-DD}_1m.csv`
    Die Roh‑Chunks werden zusätzlich gezippt archiviert und anschließend gelöscht.
- API: FastAPI liefert über `/api/v1/candles` Candle‑Daten aus den aggregierten CSVs.

### Tech‑Stack

- Python 3.11, Poetry
- websockets (Binance WS‑Client)
- pydantic v2 + pydantic‑settings (Config)
- google‑cloud‑storage (GCS Zugriff)
- pandas, pyarrow (Aggregation/Parsing)
- FastAPI + Uvicorn (optionale API)
- aiohttp (Health‑Endpoint für Cloud Run), loguru (Logging)

### Projektstruktur (Auszug)

```
src/
  orderflow_recorder/
    __main__.py                 # optionaler Einstieg
    config/settings.py          # Settings + get_settings()
    binance/ws_client.py        # WS‑Client, Parser, RecorderCallbacks
    ingest/runner.py            # Ingest‑Runner (Console Script)
    process/daily_job.py        # tägliche Aggregation & Archivierung
    storage/
      sinks.py                  # Sink‑Interfaces (Protocols)
      gcs_sinks.py              # GCS‑CSV‑Sink (Trades/Depth)
    utils/logging.py            # Loguru‑Setup
  orderflow_api/
    main.py                     # FastAPI App (+ API‑Key Header)
    service.py                  # CSV‑Laden aus GCS für Candles
tests/
```

### Installation (lokal)

Voraussetzungen: Python 3.11 und Poetry installiert.

```bash
poetry install
```

### Konfiguration

Alle Einstellungen kommen aus ENV‑Variablen (optional `.env`). Wichtige Schlüssel:

- `BINANCE_WS_FUTURES_BASE_URL` (Default: `wss://fstream.binance.com/stream`)
- `SYMBOLS_FUTURES` (Default: `btcusdt,ethusdt`; kommasepariert oder Liste)
- `FUTURES_STREAMS_DEPTH` (Default: `depth5@100ms`)
- `FUTURES_STREAMS_TRADES` (Default: `aggTrade`)
- `GCS_BUCKET_NAME` (Default: `orderflow-data-lake`)
- `BUFFER_SECONDS` (Default: `60`; Upload‑Intervall der CSV‑Chunks)
- `LOG_LEVEL` (Default: `INFO`)
- `API_KEY` (für die FastAPI‑Schicht, Pflicht für API‑Zugriffe)
- `PORT` (nur Health‑Endpoint im Recorder, Default `8080`)
- `GOOGLE_APPLICATION_CREDENTIALS` (Pfad zu GCP Service Account JSON)

Hinweis: Lokal wird eine Datei `gcp-key.json` im Projektwurzelverzeichnis automatisch erkannt und gesetzt, falls `GOOGLE_APPLICATION_CREDENTIALS` nicht gesetzt ist.

### Start (lokal)

- Recorder (Ingest → GCS):

```bash
poetry run orderflow-recorder
```

Optional mit Debug‑Logging:

```bash
LOG_LEVEL=DEBUG poetry run orderflow-recorder
```

- API (aggregierte Candles bereitstellen):

```bash
poetry run uvicorn orderflow_api.main:app --reload
```

Abrufbeispiel (1m Candles, mit API‑Key):

```bash
curl -H "X-API-Key: $API_KEY" \
  "http://127.0.0.1:8000/api/v1/candles?symbol=btcusdt&date=2025-12-11&resolution=1m"
```

Beispiel‑Client zur Visualisierung (lokal): `client_script.py`

```bash
python client_script.py
```

### Datenfluss & Speicherlayout (GCS)

- Rohdaten (CSV‑Chunks, inkl. Header):
  - Trades: `raw/{SYMBOL}/{YYYY-MM-DD}/{HH-MM-SS}_trades.csv`
  - Depth: `raw/{SYMBOL}/{YYYY-MM-DD}/{HH-MM-SS}_depth.csv` (bids/asks als JSON‑Strings)
- Aggregationen:
  - `aggregated/{SYMBOL}/{YYYY-MM-DD}_1s.csv`
  - `aggregated/{SYMBOL}/{YYYY-MM-DD}_1m.csv`
- Archiv:
  - `archive/{SYMBOL}/{YYYY-MM-DD}_raw.zip`

### Aggregations‑Job

Der tägliche Job `src/orderflow_recorder/process/daily_job.py`:

- lädt alle Trade‑Chunks eines Tages je Symbol,
- berechnet OHLC, Volumen (buy/sell/total), Delta, Trade‑Count in 1s,
- resampled zu 1m,
- lädt `1s`/`1m`‑CSV nach `aggregated/`,
- archiviert die Roh‑Chunks als ZIP und löscht sie anschließend.

Ausführung lokal (Beispiel):

```bash
poetry run python -m orderflow_recorder.process.daily_job
```

Optional Datum überschreiben:

```bash
FORCE_DATE=2025-12-11 poetry run python -m orderflow_recorder.process.daily_job
```

### Docker

Ein fertiges Image wird via `Dockerfile` gebaut; der Default‑CMD startet den Recorder.

```bash
docker build -t orderflow-recorder:local .
docker run --rm \
  -e GCS_BUCKET_NAME=orderflow-data-lake \
  -e SYMBOLS_FUTURES=btcusdt,ethusdt \
  -e API_KEY=orderflow123go \
  -e LOG_LEVEL=INFO \
  -p 8080:8080 \
  -v $PWD/gcp-key.json:/app/gcp-key.json:ro \
  orderflow-recorder:local
```

Hinweis: Die mitgelieferte `docker-compose.yml` stammt aus einer früheren Postgres‑Phase und ist aktuell nicht maßgeblich.

### Deployment (GCP)

Ein mögliches Ziel ist Cloud Run (Recorder + API getrennt deployen). Details, Variablen und Hinweise siehe `deployment_gcp.md`. Wichtige Punkte:

- Service Account mit GCS‑Zugriff (Bucket lesen/schreiben)
- Sichere Bereitstellung des Service‑Account‑Keys bzw. Workload Identity
- API mit `API_KEY` absichern

### Tests

```bash
poetry run pytest -q
```

Aktuelle Tests decken Parser/Logging ab. Ältere DB‑basierte Integrations‑Tests sind veraltet und standardmäßig deaktiviert.

### Hinweise

- Zentraler Logger: `src/orderflow_recorder/utils/logging.py`
- WebSocket‑Client & Parser: `src/orderflow_recorder/binance/ws_client.py`
- Sink‑Interfaces: `src/orderflow_recorder/storage/sinks.py`
- GCS‑Sink: `src/orderflow_recorder/storage/gcs_sinks.py`
- Ingest Entry‑Point (Console Script): `orderflow-recorder` → `orderflow_recorder.ingest.runner:main`
