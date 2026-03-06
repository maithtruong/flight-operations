import requests
from datetime import timedelta
from pathlib import Path
import json

URL = "https://opensky-network.org/api/states/all"

def run_bronze_ingestion(context):

    '''
    Get info of all flights within the day.
    '''

    logical_date = context["logical_date"].strftime("%Y%m%d_%H%M%S")

    print("Fetching raw data from API...")
    raw_response = requests.get(URL)
    data = raw_response.json()

    path = Path(f"/opt/airflow/data/bronze/flights_{logical_date}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    
    print("Dumping the raw JSON file...")
    with open(path, "w") as f:
        json.dump(data, f)
    
    # Push location of Bronze file
    context["ti"].xcom_push(key="bronze_file_path", value=str(path))