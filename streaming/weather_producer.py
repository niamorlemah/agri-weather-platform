from kafka import KafkaProducer
import json
import time
from ingestion.weather_api_collector import get_weather_data

# Configuration Kafka
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

TOPIC = "weather_data"

# Récupération des données
weather_data = get_weather_data()

# Envoi dans Kafka
for record in weather_data:
    producer.send(TOPIC, value=record)
    print(f"Envoyé : {record}")

    time.sleep(0.3)  # simulation temps réel

producer.flush()