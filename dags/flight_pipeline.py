'''
import sys
from pathlib import Path

AIRFLOW_HOME = Path("/opt/airflow")

if str(AIRFLOW_HOME) not in sys.path:
    sys.path.insert(0, str(AIRFLOW_HOME))
'''

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