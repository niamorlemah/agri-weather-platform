import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Alertes météo", layout="wide")

st.title("🚨 Centre d'alertes météo")

# -----------------------------------
# CONNEXION DB
# -----------------------------------
conn = psycopg2.connect(
    host="localhost",
    database="weather_db",
    user="airflow",
    password="airflow"
)

query = """
SELECT city, temperature, humidity, timestamp
FROM weather_decisions
ORDER BY timestamp ASC
"""

df = pd.read_sql(query, conn)
conn.close()

df["timestamp"] = pd.to_datetime(df["timestamp"])

# -----------------------------------
# 5 JOURS A VENIR
# -----------------------------------
now = pd.Timestamp.now()
limit_date = now + timedelta(days=5)

df = df[
    (df["timestamp"] >= now) &
    (df["timestamp"] <= limit_date)
].copy()

# -----------------------------------
# CREATION ALERTES
# -----------------------------------
alerts = []

for _, row in df.iterrows():

    # Gel
    if row["temperature"] < 2:
        alerts.append({
            "type": "Gel",
            "city": row["city"],
            "timestamp": row["timestamp"],
            "message": f"❄️ Risque de gel (température < 2°C)"
        })

    # Irrigation
    if row["temperature"] > 25 and row["humidity"] < 40:
        alerts.append({
            "type": "Irrigation",
            "city": row["city"],
            "timestamp": row["timestamp"],
            "message": f"🚿 Irrigation recommandée (temp > 25°C et humidité < 40%)"
        })

alerts_df = pd.DataFrame(alerts)

# -----------------------------------
# SI RIEN
# -----------------------------------
if alerts_df.empty:
    st.success("✅ Aucune alerte prévue sur les 5 prochains jours.")
    st.stop()

# -----------------------------------
# FILTRES
# -----------------------------------
st.sidebar.header("⚙️ Filtres")

cities = sorted(alerts_df["city"].unique())

selected_cities = st.sidebar.multiselect(
    "🏙️ Villes",
    cities,
    default=cities
)

selected_types = st.sidebar.multiselect(
    "🚨 Types",
    ["Gel", "Irrigation"],
    default=["Gel", "Irrigation"]
)

# -----------------------------------
# FILTRAGE
# -----------------------------------
alerts_df = alerts_df[
    (alerts_df["city"].isin(selected_cities)) &
    (alerts_df["type"].isin(selected_types))
]

alerts_df = alerts_df.sort_values("timestamp")

# -----------------------------------
# KPI
# -----------------------------------
col1, col2 = st.columns(2)

with col1:
    st.metric("🚨 Total alertes", len(alerts_df))

with col2:
    st.metric(
        "📅 Première alerte",
        alerts_df["timestamp"].min().strftime("%d/%m %H:%M")
    )

# -----------------------------------
# AFFICHAGE
# -----------------------------------
for _, row in alerts_df.iterrows():

    txt = (
        f"{row['city']} — "
        f"{row['timestamp'].strftime('%d/%m/%Y à %H:%M')} — "
        f"{row['message']}"
    )

    if row["type"] == "Gel":
        st.error(txt)
    else:
        st.warning(txt)

# -----------------------------------
# TABLE DETAILLEE
# -----------------------------------
st.subheader("📋 Tableau des alertes")

st.dataframe(
    alerts_df,
    use_container_width=True
)