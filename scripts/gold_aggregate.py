import pandas as pd
from pathlib import Path
from datetime import datetime

def run_gold_aggregate(**context):

    logical_date = context['logical_date']

    silver_path = Path("/opt/airflow/data/silver")

    # Read all silver CSV files
    silver_files = list(silver_path.glob("flights_*.csv"))

    if not silver_files:
        raise ValueError("No silver files found")

    dfs = [pd.read_csv(f) for f in silver_files]
    states_df = pd.concat(dfs, ignore_index=True)

    # Exract ISO week
    states_df["retrieved_time"] = pd.to_datetime(
        states_df["retrieved_time"],
        utc=True
    )

    # Aggregration
    gold_df = pd.DataFrame([{
        "total_aircraft": states_df["icao24"].nunique(),
        "total_flights":  states_df["icao24"].count(),
        "min_velocity":   states_df["velocity"].min(),
        "max_velocity":   states_df["velocity"].max(),
        "mean_velocity":  states_df["velocity"].mean(),
        "mode_country":   states_df["pos_country"].mode().iloc[0] if not states_df["pos_country"].mode().empty else None,
        "mode_city":      states_df["pos_city"].mode().iloc[0]    if not states_df["pos_city"].mode().empty    else None,
    }])

    # Write gold layer
    gold_path = Path("/opt/airflow/data/gold")
    gold_path.mkdir(parents=True, exist_ok=True)

    week_number = logical_date.isocalendar().week
    gold_file_path = gold_path / f"weekly_{week_number}.csv"

    gold_df.to_csv(gold_file_path, index=False)

    context["ti"].xcom_push(
        key="gold_file_path",
        value=str(gold_file_path)
    )