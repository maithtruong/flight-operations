'''
import sys
from pathlib import Path

AIRFLOW_HOME = Path("/opt/airflow")

if str(AIRFLOW_HOME) not in sys.path:
    sys.path.insert(0, str(AIRFLOW_HOME))

from scripts.bronze_ingest import run_bronze_ingestion
from scripts.silver_transform import run_silver_transform
from scripts.gold_aggregate import run_gold_aggregate
import requests
import pandas as pd
import reverse_geocode as rg

from datetime import datetime
from airflow.decorators import dag, task
from airflow.sdk import get_current_context

@dag(
    start_date=datetime(2025, 3, 3),
    schedule="*/5 * * * *",
    catchup=False
)
def fetch_bronze_and_silver():

    @task(task_id="bronze_ingest")
    def bronze():
        context = get_current_context()
        run_bronze_ingestion(context)

    @task(task_id="silver_transform")
    def silver():
        context = get_current_context()
        run_silver_transform(context)

    bronze_task = bronze()
    silver_task = silver()

    bronze_task >> silver_task

@dag(
    start_date=datetime(2025, 3, 8),
    schedule="59 23 * * 0",
    catchup=False
)
def gen_gold_weekly_report():

    @task(task_id="gold_aggregate")
    def gold():
        context = get_current_context()
        run_gold_aggregate(context)

    gold()

fetch_bronze_and_silver()
gen_gold_weekly_report()
'''

from datetime import datetime, timezone
from pathlib import Path
import json
import requests
import pandas as pd
import reverse_geocode as rg

from airflow.decorators import dag, task


URL = "https://opensky-network.org/api/states/all"


# -------------------------
# BRONZE
# -------------------------

def run_bronze_ingestion(**context):

    logical_date = context["logical_date"].strftime("%Y%m%d_%H%M%S")

    raw_response = requests.get(URL)
    data = raw_response.json()

    path = Path(f"/opt/airflow/data/bronze/flights_{logical_date}.json")
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(data, f)

    context["ti"].xcom_push(key="bronze_file_path", value=str(path))


# -------------------------
# SILVER
# -------------------------

def run_silver_transform(**context):

    bronze_file_path = context["ti"].xcom_pull(
        key="bronze_file_path",
        task_ids="bronze_ingest"
    )

    if not bronze_file_path:
        raise ValueError("Bronze file path not found in XCom")

    with open(bronze_file_path, "r") as f:
        data = json.load(f)

    timestamp = data["time"]
    states_vector = data["states"]

    states_df = pd.DataFrame(states_vector)

    states_df = states_df[[0, 2, 3, 5, 6, 9]]

    states_df.columns = [
        "icao24",
        "origin_country",
        "time_position",
        "longitude",
        "latitude",
        "velocity",
    ]

    states_df = states_df.rename(columns={"time_position": "pos_time"})

    states_df["pos_time"] = pd.to_datetime(
        states_df["pos_time"],
        unit="s",
        utc=True,
    )

    states_df["retrieved_time"] = datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    )

    states_df["pos_date"] = states_df["pos_time"].dt.date

    def reverse_pos_from_ll(longitude, latitude):
        if pd.isna(longitude) or pd.isna(latitude):
            return None, None
        pos_vector = rg.get((latitude, longitude))
        return pos_vector["country_code"], pos_vector["city"]

    states_df[["pos_country", "pos_city"]] = states_df.apply(
        lambda row: reverse_pos_from_ll(row["longitude"], row["latitude"]),
        axis=1,
        result_type="expand",
    )

    silver_path = Path("/opt/airflow/data/silver")
    silver_path.mkdir(parents=True, exist_ok=True)

    logical_date = context["logical_date"].strftime("%Y%m%d_%H%M%S")
    silver_file_path = silver_path / f"flights_{logical_date}.csv"

    states_df.to_csv(silver_file_path, index=False)

    context["ti"].xcom_push(key="silver_file_path", value=str(silver_file_path))


# -------------------------
# GOLD
# -------------------------

def run_gold_aggregate(**context):

    logical_date = context["logical_date"]

    silver_path = Path("/opt/airflow/data/silver")
    silver_files = list(silver_path.glob("flights_*.csv"))

    if not silver_files:
        raise ValueError("No silver files found")

    dfs = [pd.read_csv(f) for f in silver_files]
    states_df = pd.concat(dfs, ignore_index=True)

    states_df["retrieved_time"] = pd.to_datetime(
        states_df["retrieved_time"],
        utc=True,
    )

    gold_df = pd.DataFrame([{
        "total_aircraft": states_df["icao24"].nunique(),
        "total_flights": states_df["icao24"].count(),
        "min_velocity": states_df["velocity"].min(),
        "max_velocity": states_df["velocity"].max(),
        "mean_velocity": states_df["velocity"].mean(),
        "mode_country": states_df["pos_country"].mode().iloc[0] if not states_df["pos_country"].mode().empty else None,
        "mode_city": states_df["pos_city"].mode().iloc[0] if not states_df["pos_city"].mode().empty else None,
    }])

    gold_path = Path("/opt/airflow/data/gold")
    gold_path.mkdir(parents=True, exist_ok=True)

    week_number = logical_date.isocalendar().week
    gold_file_path = gold_path / f"weekly_{week_number}.csv"

    gold_df.to_csv(gold_file_path, index=False)

    context["ti"].xcom_push(key="gold_file_path", value=str(gold_file_path))


# =========================
# DAG DEFINITIONS
# =========================

@dag(
    dag_id="fetch_bronze_and_silver",
    start_date=datetime(2025, 3, 3),
    schedule="*/5 * * * *",
    catchup=False,
)
def fetch_bronze_and_silver():

    @task(task_id="bronze_ingest")
    def bronze(**context):
        run_bronze_ingestion(**context)

    @task(task_id="silver_transform")
    def silver(**context):
        run_silver_transform(**context)

    bronze() >> silver()


@dag(
    dag_id="gen_gold_weekly_report",
    start_date=datetime(2025, 3, 8),
    schedule="59 23 * * 0",
    catchup=False,
)
def gen_gold_weekly_report():

    @task(task_id="gold_aggregate")
    def gold(**context):
        run_gold_aggregate(**context)

    gold()


fetch_bronze_and_silver()
gen_gold_weekly_report()