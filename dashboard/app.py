import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import date

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Agri Weather Platform",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 Agri Weather Platform")
st.caption("Prévisions météo • Aide à la décision agricole")

# =====================================================
# ICONES METEO
# =====================================================
def weather_icon(desc):
    txt = str(desc).lower()

    if "thunder" in txt:
        return "⛈️"
    if "snow" in txt:
        return "❄️"
    if "rain" in txt or "drizzle" in txt:
        return "🌧️"
    if "mist" in txt or "fog" in txt:
        return "🌫️"
    if "clear" in txt:
        return "☀️"
    if "cloud" in txt:
        return "☁️"

    return "🌤️"

# =====================================================
# LOAD DATA CLOUD
# =====================================================
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
        feels_like,
        pressure,
        description,
        humidity,
        wind_speed,
        risk_frost,
        irrigation_needed,
        rain,
        clouds,
        pop,
        "timestamp" AS forecast_time
    FROM weather_decisions
    ORDER BY forecast_time ASC
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df

# =====================================================
# DATA
# =====================================================
df = load_data()

if df.empty:
    st.warning("Aucune donnée disponible.")
    st.stop()

# datetime clean
df["forecast_time"] = pd.to_datetime(
    df["forecast_time"],
    errors="coerce"
)

df = df.dropna(subset=["forecast_time"])

if df.empty:
    st.warning("Aucune donnée datée disponible.")
    st.stop()

df["icon"] = df["description"].apply(weather_icon)

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.header("⚙️ Filtres")

cities = sorted(df["city"].dropna().unique())

selected_cities = st.sidebar.multiselect(
    "🏙️ Villes",
    cities,
    default=cities
)

# dates
today = date.today()

min_day = df["forecast_time"].min().date()
max_day = df["forecast_time"].max().date()

default_day = today

if default_day < min_day:
    default_day = min_day

if default_day > max_day:
    default_day = max_day

date_range = st.sidebar.date_input(
    "📅 Jour ou période",
    value=(default_day, default_day),
    min_value=min_day,
    max_value=max_day
)

if not isinstance(date_range, tuple):
    start_date = date_range
    end_date = date_range

elif len(date_range) == 1:
    start_date = date_range[0]
    end_date = date_range[0]

else:
    start_date = date_range[0]
    end_date = date_range[1]

# =====================================================
# FILTER
# =====================================================
filtered_df = df[
    (df["city"].isin(selected_cities)) &
    (df["forecast_time"].dt.date >= start_date) &
    (df["forecast_time"].dt.date <= end_date)
].copy()

if filtered_df.empty:
    st.warning("Aucune donnée sur cette période.")
    st.stop()

# =====================================================
# KPI
# =====================================================
latest_ts = filtered_df["forecast_time"].max()

latest_df = filtered_df[
    filtered_df["forecast_time"] == latest_ts
]

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "🌡️ Température",
        f"{latest_df['temperature'].mean():.1f} °C"
    )

with c2:
    st.metric(
        "🥵 Ressenti",
        f"{latest_df['feels_like'].mean():.1f} °C"
    )

with c3:
    st.metric(
        "💨 Vent",
        f"{latest_df['wind_speed'].mean():.1f} km/h"
    )

with c4:
    st.metric(
        "💧 Humidité",
        f"{latest_df['humidity'].mean():.0f} %"
    )

st.caption(
    f"Dernière mise à jour : {latest_ts.strftime('%d/%m/%Y %H:%M')}"
)

st.divider()

# =====================================================
# TABS
# =====================================================
tab1, tab2 = st.tabs(["📈 Dashboard", "🚨 Alertes"])

# =====================================================
# TAB DASHBOARD
# =====================================================
with tab1:

    # -----------------------------------------------
    # TEMPERATURE
    # -----------------------------------------------
    st.subheader("🌡️ Température")

    fig = px.line(
        filtered_df,
        x="forecast_time",
        y="temperature",
        color="city",
        markers=True
    )

    positions = [
        "top center",
        "bottom center",
        "middle left"
    ]

    for i, trace in enumerate(fig.data):

        city = trace.name

        city_df = filtered_df[
            filtered_df["city"] == city
        ].sort_values("forecast_time")

        labels = [
            f"{icon} {feel:.1f}°"
            for icon, feel in zip(
                city_df["icon"],
                city_df["feels_like"]
            )
        ]

        trace.mode = "lines+markers+text"
        trace.text = labels
        trace.textposition = positions[i % len(positions)]
        trace.textfont = dict(size=11)

    fig.update_layout(
        height=500,
        hovermode="x unified",
        xaxis_title="Date / Heure",
        yaxis_title="°C"
    )

    fig.update_xaxes(
        tickformat="%d/%m %H:%M",
        rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------
    # PLUIE
    # -----------------------------------------------
    st.subheader("🌧️ Précipitations")

    rain_df = filtered_df.copy()
    rain_df["prob_txt"] = (
        (rain_df["pop"] * 100)
        .round(0)
        .astype(int)
        .astype(str) + "%"
    )

    fig2 = px.bar(
        rain_df,
        x="forecast_time",
        y="rain",
        color="city",
        barmode="group",
        text="prob_txt"
    )

    fig2.update_traces(textposition="outside")

    fig2.update_layout(
        height=430,
        hovermode="x unified",
        xaxis_title="Date / Heure",
        yaxis_title="mm / 3h"
    )

    fig2.update_xaxes(
        tickformat="%d/%m %H:%M",
        rangeslider_visible=False
    )

    st.plotly_chart(fig2, use_container_width=True)

# =====================================================
# TAB ALERTES
# =====================================================
with tab2:

    st.subheader("🚨 Alertes météo")

    alerts = 0

    frost = filtered_df[filtered_df["risk_frost"] == True]

    for _, row in frost.iterrows():
        alerts += 1
        st.error(
            f"❄️ Gel possible à {row['city']} le "
            f"{row['forecast_time'].strftime('%d/%m %H:%M')} | "
            f"Règle : température < 2°C"
        )

    irrig = filtered_df[
        filtered_df["irrigation_needed"] == True
    ]

    for _, row in irrig.iterrows():
        alerts += 1
        st.warning(
            f"🚿 Irrigation recommandée à {row['city']} le "
            f"{row['forecast_time'].strftime('%d/%m %H:%M')} | "
            f"Règle : chaud + sec + peu de pluie"
        )

    heavy_rain = filtered_df[filtered_df["rain"] > 10]

    for _, row in heavy_rain.iterrows():
        alerts += 1
        st.info(
            f"🌧️ Forte pluie à {row['city']} le "
            f"{row['forecast_time'].strftime('%d/%m %H:%M')} | "
            f"Règle : pluie > 10 mm / 3h"
        )

    strong_wind = filtered_df[
        filtered_df["wind_speed"] > 60
    ]

    for _, row in strong_wind.iterrows():
        alerts += 1
        st.warning(
            f"💨 Vent fort à {row['city']} le "
            f"{row['forecast_time'].strftime('%d/%m %H:%M')} | "
            f"Règle : vent > 60 km/h"
        )

    if alerts == 0:
        st.success("✅ Aucune alerte sur la période.")