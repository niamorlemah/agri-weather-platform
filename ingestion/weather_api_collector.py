import requests
import json
import os
import logging
from datetime import datetime
from kafka_utils.producer import send_to_kafka

#clé de l'API fournie
API_KEY = "41273deefe5d44baf2ccc13a67fadebc"
#Liste des villes à recupérer.
CITIES = ["Aix-en-Provence","Fuveau","Peynier"]

# Setup logging
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/ingestion.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
# fonction get_weather_data qui recupere les données météo de l'API puis les mets dans un dictionnaire de donnée
def get_weather_data():
    weather_data = []
    #boucle sur toutes les villes de la liste CITIES
    for city in CITIES:
        try:
            url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"
            response = requests.get(url, timeout=10)
            #Si erreur http erreur et sortie du code
            if response.status_code != 200:
                logging.error(f"Erreur API {city}: {response.status_code}")
                continue

            data = response.json()
            #ajout des données au dico
            for entry in data["list"]:
                record = {
                    "city": city,
                    "datetime": entry["dt_txt"],
                    "temperature": entry["main"]["temp"],
                    "feels_like": entry["main"]["feels_like"],
                    "pressure": entry["main"]["pressure"],
                    "humidity": entry["main"]["humidity"],
                    "wind_speed": round(entry["wind"]["speed"] * 3.6, 1),
                    "description": entry["weather"][0]["description"],

                    "rain": entry.get("rain", {}).get("3h", 0),
                    "clouds": entry["clouds"]["all"],
                    "pop": entry.get("pop", 0)
                }
                weather_data.append(record)
            
        #si erreur afficher le message sur la ville
        except Exception as e:
            logging.error(f"Erreur sur {city}: {str(e)}")
    #si ok affiche les recorsq collectés
    weather_data = sorted(
        weather_data,
        key=lambda x: (x["city"], x["datetime"])
    )
    logging.info(f"{len(weather_data)} records collectés")
    return weather_data

#fontion de sauvegarde dans le fichier
def save_data(data):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # RAW
    raw_path = f"data/raw/weather_raw_{timestamp}.json"
    os.makedirs("data/raw", exist_ok=True)

    with open(raw_path, "w") as f:
        json.dump(data, f)

    # PROCESSED
    processed_path = f"data/processed/weather_processed_{timestamp}.json"
    os.makedirs("data/processed", exist_ok=True)

    with open(processed_path, "w") as f:
        json.dump(data, f, indent=2)

    logging.info(f"Données sauvegardées : {timestamp}")

#utilisation des fonctions 
if __name__ == "__main__":
    logging.info("Début ingestion")

    data = get_weather_data()

    if data:
        save_data(data)
        send_to_kafka(data)
    else:
        logging.warning("Aucune donnée récupérée")

    logging.info("Fin ingestion")