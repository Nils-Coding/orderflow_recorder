Voraussetzungen: GCP-Projekt, gcloud CLI, Artifact Registry, Cloud SQL (Postgres), Cloud Storage (optional).
Schritte:
Cloud SQL Instanz mit Postgres anlegen, DB orderflow_recorder anlegen.
Docker-Image in Artifact Registry pushen (gcloud builds submit).
Cloud Run Service orderflow-recorder erzeugen mit:
Image aus Artifact Registry
min-instances=1
CPU always allocated
Verbindung zu Cloud SQL (Connection Name, DB_URL über Unix-Socket oder Connector)
ENV-Variablen für DB_URL, LOG_LEVEL, SYMBOLS_FUTURES setzen.
Hinweise zu Logging (Cloud Logging) und Monitoring.
