# ✈️ Flight Operations Pipeline (v3)

A data engineering pipeline that tracks real-time global flight data using **Apache Airflow 3.x**, Docker, and a medallion architecture (Bronze → Silver → Gold).

> ⚠️ **This version is experimental.** Airflow 3.x introduced significant breaking changes (standalone DAG processor, new execution API, task supervisor model) that make local Docker deployment more complex. This repo documents the attempt and known issues.
>
> For the stable, fully working version, see [flight-operations-ver2](../flight-operations-ver2) (Airflow 2.9).

---

## 📐 Architecture

```
OpenSky Network API
        │
        ▼
┌──────────────┐
│    Bronze    │  Raw JSON snapshots every 5 minutes
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    Silver    │  Cleaned, typed, reverse-geocoded CSV
└──────┬───────┘
       │
       ▼
┌──────────────┐
│     Gold     │  Weekly aggregated report (velocity, top countries/cities)
└──────────────┘
```

### DAGs

| DAG | Schedule | Description |
|-----|----------|-------------|
| `fetch_bronze_and_silver` | Every 5 minutes | Fetches live flight data → cleans and transforms it |
| `gen_gold_weekly_report` | Sunday 23:59 | Aggregates all silver data into a weekly summary |

### Services (Airflow 3.x requires 4 services)

| Service | Role |
|---------|------|
| `airflow-postgres` | Metadata database |
| `airflow-webserver` | UI + execution API at `localhost:8080` |
| `airflow-scheduler` | Schedules and executes tasks |
| `airflow-dag-processor` | **New in Airflow 3.x** — dedicated process for parsing DAG files |

---

## 📁 Project Structure

```
flight-operations-ver3/
├── dags/
│   └── flight_pipeline.py       # DAG definitions
├── scripts/
│   ├── __init__.py
│   ├── bronze_ingest.py         # Fetch raw API data
│   ├── silver_transform.py      # Clean + reverse geocode
│   └── gold_aggregate.py        # Weekly aggregation
├── data/
│   ├── bronze/                  # Raw JSON files
│   ├── silver/                  # Cleaned CSV files
│   └── gold/                    # Weekly reports
├── logs/                        # Airflow task logs
├── plugins/                     # Airflow plugins (empty)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

---

## 🚀 Setup & Installation

### Prerequisites

- Docker & Docker Compose
- Python 3.x

### 1. Clone the repo

```bash
git clone https://github.com/your-username/flight-operations-ver3.git
cd flight-operations-ver3
```

### 2. Create your `.env` file

```env
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow
```

### 3. Create directories and fix permissions

```bash
mkdir -p logs/scheduler logs/dag_processor dags scripts plugins data/bronze data/silver data/gold
sudo chown -R 50000:0 logs/ dags/ scripts/ plugins/ data/
sudo chmod -R 775 logs/ dags/ scripts/ plugins/ data/
```

### 4. Build and start

```bash
docker compose build
docker compose up -d
```

### 5. Access the UI

Open [http://localhost:8080](http://localhost:8080) and log in with:
- **Username:** `admin`
- **Password:** `admin`

---

## ⚠️ Known Issues & Airflow 3.x Breaking Changes

Airflow 3.x is a major architectural overhaul. Here's what's different and what caused issues:

**Standalone DAG Processor required**

Airflow 3.x no longer parses DAGs inside the scheduler. A dedicated `airflow dag-processor` service is required. Without it, DAGs never appear in the UI.

**Execution API on the webserver**

The scheduler no longer runs tasks directly. It calls the webserver's execution API (`/execution/`) to start each task. This requires the env var:
```yaml
AIRFLOW__EXECUTION_API__EXECUTION_API_SERVER_URL: "http://airflow-webserver:8080/execution/"
```
Without this, all tasks fail with `Connection refused` and show a state mismatch error in the UI.

**Task subprocess SIGKILL / fork() deadlock**

The `LocalExecutor` forks subprocesses to run tasks, but the multi-threaded scheduler process causes fork deadlocks in Python 3.12. This leads to tasks being killed with `SIGKILL` before they can register with the execution API. The fix is:
```yaml
AIRFLOW__CORE__EXECUTE_TASKS_NEW_PYTHON_INTERPRETER: "True"
```

**`airflow webserver` renamed to `airflow api-server`**

The webserver command changed in Airflow 3.x:
```bash
# Airflow 2.x
command: webserver

# Airflow 3.x
command: api-server
```

**Permissions on mounted volumes**

All mounted folders must be owned by UID `50000` (the airflow user inside the container):
```bash
sudo chown -R 50000:0 logs/ dags/ scripts/ plugins/ data/
```

---

## 🔧 General Troubleshooting

**DAG not appearing in UI**
```bash
docker logs airflow-dag-processor 2>&1 | grep -i "error\|import" | tail -20
```

**Tasks failing with state mismatch / no logs**
```bash
docker logs airflow-scheduler 2>&1 | grep -i "error\|refused" | tail -20
```

**Test a task manually**
```bash
docker exec -it airflow-scheduler bash
airflow tasks test fetch_bronze_and_silver bronze_ingest 2025-03-06
```

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | Fetch data from OpenSky API |
| `pandas` | Data transformation |
| `reverse_geocode` | Convert lat/lon to country & city |