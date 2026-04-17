import sys
sys.path.append('/opt/airflow')

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

from kafka_utils.consumer import consume_weather_batch

dag = DAG(
    dag_id="kafka_consumer_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule="@hourly",
    catchup=False
)

task_consume = PythonOperator(
    task_id="consume_kafka",
    python_callable=consume_weather_batch,
    dag=dag
)