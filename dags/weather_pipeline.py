import sys
sys.path.append('/opt/airflow')

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

from ingestion.weather_api_collector import get_weather_data, save_data
from kafka_utils.producer import send_to_kafka
from kafka_utils.consumer import consume_weather_batch


# ---------------------------------------------------
# TASK 1 : INGESTION
# ---------------------------------------------------
def run_ingestion():

    data = get_weather_data()

    if data:
        save_data(data)
        send_to_kafka(data)


# ---------------------------------------------------
# DAG
# ---------------------------------------------------
with DAG(
    dag_id="weather_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule="0 */3 * * *",   # toutes les 3h
    catchup=False,
    tags=["meteo", "portfolio"]
) as dag:

    task_ingestion = PythonOperator(
        task_id="ingestion_task",
        python_callable=run_ingestion
    )

    task_consume = PythonOperator(
        task_id="consume_kafka_task",
        python_callable=consume_weather_batch
    )

    # ordre strict
    task_ingestion >> task_consume