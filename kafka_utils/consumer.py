def consume_weather_batch():

    import json
    import psycopg2
    from kafka import KafkaConsumer

    # ---------------------------
    # Connexion PostgreSQL
    # ---------------------------
    conn = psycopg2.connect(
        host="postgres",
        database="weather_db",
        user="airflow",
        password="airflow"
    )
    cursor = conn.cursor()

    # ---------------------------
    # Consumer Kafka
    # ---------------------------
    consumer = KafkaConsumer(
        'weather_data',
        bootstrap_servers='kafka:9092',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        group_id=None
    )

    print("📥 Lecture batch Kafka...")

    # ---------------------------
    # Récupération messages (batch)
    # ---------------------------
    messages = consumer.poll(timeout_ms=5000)

    count = 0

    for tp, msgs in messages.items():
        for message in msgs:

            data = message.value

            # 🔥 sécurité JSON
            if isinstance(data, str):
                data = json.loads(data)

            # ---------------------------
            # Extraction données
            # ---------------------------
            temperature = data.get("temperature")
            humidity = data.get("humidity")
            wind_speed = data.get("wind_speed")
            city = data.get("city")
            feels_like = data.get("feels_like")
            pressure = data.get("pressure")
            description = data.get("description")
            timestamp = data.get("datetime")
            rain = data.get("rain")
            clouds = data.get("clouds")
            pop = data.get("pop")

            # ---------------------------
            # Logique métier
            # ---------------------------
            risk_frost = temperature is not None and temperature < 2
            irrigation_needed = (
                temperature is not None and humidity is not None
                and temperature > 25 and humidity < 40
            )

            # ---------------------------
            # INSERT PostgreSQL
            # ---------------------------
            cursor.execute(
                """
                INSERT INTO weather_decisions 
                (city, temperature, feels_like, pressure, description,
                humidity, wind_speed, risk_frost, irrigation_needed, timestamp, rain, clouds, pop)

                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)

                ON CONFLICT (city, timestamp)
                DO UPDATE SET
                    temperature = EXCLUDED.temperature,
                    feels_like = EXCLUDED.feels_like,
                    pressure = EXCLUDED.pressure,
                    description = EXCLUDED.description,
                    humidity = EXCLUDED.humidity,
                    wind_speed = EXCLUDED.wind_speed,
                    risk_frost = EXCLUDED.risk_frost,
                    irrigation_needed = EXCLUDED.irrigation_needed,
                    rain = EXCLUDED.rain,
                    clouds = EXCLUDED.clouds,
                    pop = EXCLUDED.pop;
                """,
                (
                    city,
                    temperature,
                    feels_like,
                    pressure,
                    description,
                    humidity,
                    wind_speed,
                    risk_frost,
                    irrigation_needed,
                    timestamp,
                    rain,
                    clouds,
                    pop
                )
            )

            count += 1

    # ---------------------------
    # Commit + fermeture
    # ---------------------------
    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ {count} messages insérés")

    if count == 0:
        print("ℹ️ Aucun nouveau message")