import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(
    page_title="Alertes météo",
    page_icon="🚨",
    layout="wide"
)

st.title("🚨 Centre d'alertes météo")

@st.cache_data(ttl=300)
def load_data():

    conn = psycopg2.connect(
        host=st.secrets["DB_HOST"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        port=st.secrets["DB_PORT"],
        sslmode="require"
    )

    query = """
    SELECT
        city,
        temperature,
        humidity,
        wind_speed,
        rain,
        risk_frost,
        irrigation_needed,
        "timestamp" AS forecast_time
    FROM weather_decisions
    ORDER BY forecast_time ASC
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df

df = load_data()

if df.empty:
    st.warning("Aucune donnée.")
    st.stop()

df["forecast_time"] = pd.to_datetime(df["forecast_time"], errors="coerce")
df = df.dropna(subset=["forecast_time"])

# =====================================================
# FILTRE ALERTES : maintenant -> +5 jours
# =====================================================

now = pd.Timestamp.now()
limit_date = now + pd.Timedelta(days=5)

df = df[
    (df["forecast_time"] >= now) &
    (df["forecast_time"] <= limit_date)
].copy()

cities = sorted(df["city"].unique())

selected = st.sidebar.multiselect(
    "🏙️ Villes",
    cities,
    default=cities
)

df = df[df["city"].isin(selected)]

alerts = 0

for _, row in df.iterrows():

    if row["risk_frost"]:
        alerts += 1
        st.error(
            f"❄️ {row['city']} • "
            f"{row['forecast_time'].strftime('%d/%m %H:%M')} "
            f"Gel possible"
        )

    if row["irrigation_needed"]:
        alerts += 1
        st.warning(
            f"🚿 {row['city']} • "
            f"{row['forecast_time'].strftime('%d/%m %H:%M')} "
            f"Irrigation recommandée"
        )

    if row["rain"] > 10:
        alerts += 1
        st.info(
            f"🌧️ {row['city']} • "
            f"{row['forecast_time'].strftime('%d/%m %H:%M')} "
            f"Forte pluie"
        )

    if row["wind_speed"] > 60:
        alerts += 1
        st.warning(
            f"💨 {row['city']} • "
            f"{row['forecast_time'].strftime('%d/%m %H:%M')} "
            f"Vent fort"
        )

if alerts == 0:
    st.success("✅ Aucune alerte.")