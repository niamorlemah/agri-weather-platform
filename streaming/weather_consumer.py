from kafka import KafkaConsumer
import json
import psycopg2

# Connexion PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    database="agri_weather",
    user="data",
    password="data"
)

cursor = conn.cursor()

# Création table (si pas existe)
cursor.execute("""
CREATE TABLE IF NOT EXISTS weather_data (
    id SERIAL PRIMARY KEY,
    city TEXT,
    datetime TIMESTAMP,
    temperature FLOAT,
    humidity INT,
    wind_speed FLOAT
)
""")
conn.commit()

# Kafka Consumer
consumer = KafkaConsumer(
    "weather_data",
    bootstrap_servers="localhost:9092",
    value_deserializer=lambda m: json.loads(m.decode("utf-8"))
)

print("Consumer lancé...")

# Lecture des messages
for message in consumer:
    data = message.value

    print(f"Reçu : {data}")

    cursor.execute("""
        INSERT INTO weather_data (city, datetime, temperature, humidity, wind_speed)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        data["city"],
        data["datetime"],
        data["temperature"],
        data["humidity"],
        data["wind_speed"]
    ))

    conn.commit()