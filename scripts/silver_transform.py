from datetime import datetime, timezone
from pathlib import Path
import json
import pandas as pd
import reverse_geocode as rg

def run_silver_transform(context):

    '''
    Tranform the bronze dataset into a suitable schema.
    '''

    # Read bronze data
    bronze_file_path = context["ti"].xcom_pull(
        key="bronze_file_path",
        task_ids="bronze_ingest"
    )

    if not bronze_file_path:
        raise ValueError("Bronze file path not found in XCom")
    
    with open(bronze_file_path, "r") as f:
        data = json.load(f)

    # Flatten bronze data
    timestamp = data["time"]
    states_vector = data["states"]

    states_df = pd.DataFrame(states_vector)

    # Extract necessary columns
    states_df = states_df[[
        0, #'icao24',
        2, #'origin_country',
        3, #'time_position',
        5, #'longitude',
        6, #'latitude,'
        9 #'velocity'
    ]]
    
    states_df.columns = [
        'icao24',
        'origin_country',
        'time_position',
        'longitude',
        'latitude',
        'velocity'
    ]

    # Rename columns
    states_df = states_df.rename(
        columns={'time_position': 'pos_time'}
    )

    states_df['pos_time'] = pd.to_datetime(
        states_df['pos_time'],
        unit='s',
        utc=True
    )

    # Infer new columns
    states_df['retrieved_time'] = datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc
    )
    states_df['pos_date'] = states_df['pos_time'].dt.date

    def reverse_pos_from_ll(longitude, latitude):
        if pd.isna(longitude) or pd.isna(latitude):
            return None, None
        pos_vector = rg.get((latitude, longitude))
        return pos_vector['country_code'], pos_vector['city']
    
    states_df[["pos_country", "pos_city"]] = states_df.apply(
        lambda row: reverse_pos_from_ll(row["longitude"], row["latitude"]),
        axis=1,
        result_type="expand"
    )

    # Write silver data
    silver_path = Path("/opt/airflow/data/silver")
    silver_path.mkdir(parents=True, exist_ok=True)

    logical_date = context["logical_date"].strftime("%Y%m%d_%H%M%S")
    silver_file_path = silver_path / f"flights_{logical_date}.csv"

    states_df.to_csv(silver_file_path, index=False)
    
    # Push location of Bronze file
    context["ti"].xcom_push(key="silver_file_path", value=str(silver_file_path))