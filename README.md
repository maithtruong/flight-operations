# ✈️ Flight Operations Pipeline (v2)

A data engineering pipeline that tracks real-time global flight data using **Apache Airflow 2.9**, Docker, and a medallion architecture (Bronze → Silver → Gold).

> **Note:** This is the stable, working version of the project using Airflow 2.9.
> For the Airflow 3.x experimental version, see [flight-operations-ver3](../flight-operations-ver3).

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

### Services

| Service | Role |
|---------|------|
| `airflow-postgres` | Metadata database |
| `airflow-init` | One-shot DB migration + admin user creation |
| `airflow-webserver` | UI at `localhost:8080` |
| `airflow-scheduler` | Schedules and executes tasks |

---

## 📁 Project Structure

```
flight-operations-ver2/
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
- Python 3.x (for generating the Fernet key)

### 1. Clone the repo

```bash
git clone https://github.com/your-username/flight-operations-ver2.git
cd flight-operations-ver2
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Then fill in your `.env`:

```env
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow
FERNET_KEY=        # optional, but recommended for persistent connections
SECRET_KEY=        # optional, but recommended to avoid session resets
```

To generate a Fernet key (optional but recommended):
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Create directories and fix permissions

```bash
mkdir -p logs/scheduler dags scripts plugins data/bronze data/silver data/gold
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

## 🔧 Troubleshooting

**`PermissionError` on logs or data folders**
```bash
sudo chown -R 50000:0 logs/ data/
sudo chmod -R 775 logs/ data/
```

**`ModuleNotFoundError` for `reverse_geocode` or `pandas`**

Make sure you're using the custom image, not the base one:
```yaml
# docker-compose.yml — should say build: . not image: apache/airflow:2.9.0
airflow-webserver:
  build: .
```
Then rebuild:
```bash
docker compose build --no-cache
docker compose up -d
```

**DAG not showing in UI**

Check the scheduler logs:
```bash
docker logs airflow-scheduler 2>&1 | grep -i "error\|import" | tail -20
```

**Scripts folder being parsed as DAGs**

Make sure `scripts/` is at the project root, **not** inside `dags/`. Airflow scans everything inside `dags/` for DAG files.

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | Fetch data from OpenSky API |
| `pandas` | Data transformation |
| `reverse_geocode` | Convert lat/lon to country & city |