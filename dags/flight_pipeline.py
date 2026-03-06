from datetime import datetime
from airflow.decorators import dag, task
from scripts.bronze_ingest import run_bronze_ingestion
from scripts.silver_transform import run_silver_transform
from scripts.gold_aggregate import run_gold_aggregate


@dag(
    start_date=datetime(2025, 3, 3),
    schedule_interval="*/5 * * * *",
    catchup=False
)
def fetch_bronze_and_silver():

    @task(task_id="bronze_ingest")
    def bronze(**context):
        run_bronze_ingestion(context)

    @task(task_id="silver_transform")
    def silver(**context):
        run_silver_transform(context)

    bronze_task = bronze()
    silver_task = silver()
    bronze_task >> silver_task


@dag(
    start_date=datetime(2025, 3, 8),
    schedule_interval="59 23 * * 0",
    catchup=False
)
def gen_gold_weekly_report():

    @task(task_id="gold_aggregate")
    def gold(**context):
        run_gold_aggregate(context)

    gold()


fetch_bronze_and_silver()
gen_gold_weekly_report()