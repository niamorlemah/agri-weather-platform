from kafka import KafkaProducer
import json


def send_to_kafka(data):

    producer = KafkaProducer(
        bootstrap_servers='kafka:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    for item in data:
        producer.send('weather_data', value=item)

    producer.flush()

    print("✅ Data envoyée à Kafka")
