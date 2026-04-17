import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import date

# =====================================================
# CONFIG PAGE
# =====================================================
st.set_page_config(
    page_title="Agri Weather Platform",
    page_icon="🍇",
    layout="wide"
)

st.title("🍇 Agri Weather Platform")
st.caption("Pilotage météo viticole • Prévisions • Analyse • Décision")

# =====================================================
# ICONES
# =====================================================
def icon_weather(description, temp=None, wind=None):

    txt = str(description).lower()

    if "heavy snow" in txt:
        return "🌨️"
    if "snow" in txt or "sleet" in txt:
        return "❄️"
    if "thunder" in txt or "storm" in txt:
        return "⛈️"
    if "shower" in txt:
        return "🌧️"
    if "rain" in txt or "drizzle" in txt:
        return "🌦️"
    if "mist" in txt or "fog" in txt or "haze" in txt:
        return "🌫️"

    if wind is not None and wind >= 50:
        return "💨"

    if temp is not None and temp >= 32:
        return "🌡️"

    if temp is not None and temp <= 0:
        return "🥶"

    if "few clouds" in txt:
        return "🌤️"
    if "scattered clouds" in txt:
        return "⛅"
    if "broken clouds" in txt or "overcast" in txt:
        return "☁️"
    if "clear" in txt:
        return "☀️"

    return "🌤️"

# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data
def load_data():

    conn = psycopg2.connect(
        host="localhost",
        database="weather_db",
        user="airflow",
        password="airflow"
    )

    query = """
    SELECT city,
           temperature,
           feels_like,
           humidity,
           wind_speed,
           pressure,
           rain,
           clouds,
           pop,
           description,
           timestamp
    FROM weather_decisions
    ORDER BY timestamp ASC
    """

    df = pd.read_sql(query, conn)
    conn.close()
    return df

df = load_data()

# =====================================================
# CLEAN
# =====================================================
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.drop_duplicates(subset=["city", "timestamp"], keep="last")
df = df.sort_values(["city", "timestamp"])

df["icon"] = df.apply(
    lambda r: icon_weather(
        r["description"],
        r["temperature"],
        r["wind_speed"]
    ),
    axis=1
)

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.header("⚙️ Filtres")

cities = sorted(df["city"].unique())

selected_cities = st.sidebar.multiselect(
    "🏙️ Villes",
    cities,
    default=cities
)

selected_graphs = st.sidebar.multiselect(
    "📊 Graphiques",
    [
        "Température",
        "Température ressentie",
        "Précipitations",
        "Vent",
        "Humidité",
        "Pression",
        "Nuages"
    ],
    default=[
        "Température",
        "Précipitations",
        "Vent",
        "Humidité"
    ]
)

# =====================================================
# DATE
# =====================================================
today = date.today()

min_day = df["timestamp"].min().date()
max_day = df["timestamp"].max().date()

default_day = min(max(today, min_day), max_day)

date_range = st.sidebar.date_input(
    "📅 Jour ou période",
    value=(default_day, default_day),
    min_value=min_day,
    max_value=max_day
)

# 1 seule date sélectionnée
if not isinstance(date_range, tuple):
    start_date = date_range
    end_date = date_range

# tuple de 1 élément
elif len(date_range) == 1:
    start_date = date_range[0]
    end_date = date_range[0]

# vraie période
else:
    start_date = date_range[0]
    end_date = date_range[1]

# =====================================================
# FILTER
# =====================================================
filtered_df = df[
    (df["city"].isin(selected_cities)) &
    (df["timestamp"].dt.date >= start_date) &
    (df["timestamp"].dt.date <= end_date)
].copy()

filtered_df = filtered_df.sort_values(["timestamp", "city"])

if filtered_df.empty:
    st.warning("Aucune donnée disponible.")
    st.stop()



# =====================================================
# TABS
# =====================================================
tab1, tab2 = st.tabs(["📈 Dashboard", "🚨 Alertes"])

# =====================================================
# OUTIL GRAPHE
# =====================================================
def graph_line(title, ycol, ylabel):

    st.subheader(title)

    fig = px.line(
        filtered_df,
        x="timestamp",
        y=ycol,
        color="city",
        markers=True
    )

    fig.update_layout(
        height=430,
        hovermode="x unified",
        xaxis_title="Date / Heure",
        yaxis_title=ylabel
    )

    fig.update_xaxes(
        rangeslider_visible=False,
        tickformat="%d/%m %H:%M"
    )

    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# DASHBOARD
# =====================================================
with tab1:

    # -------------------------------------------------
    # TEMPERATURE
    # -------------------------------------------------
    if "Température" in selected_graphs:

        st.subheader("🌡️ Température")

        fig = px.line(
            filtered_df,
            x="timestamp",
            y="temperature",
            color="city",
            markers=True
        )

        # transformer chaque trace
        positions = [
            "top center",
            "bottom center",
            "middle left"
        ]

        for i, trace in enumerate(fig.data):

            city_name = trace.name

            city_df = filtered_df[
                filtered_df["city"] == city_name
            ].sort_values("timestamp")

            labels = [
                f"{icon} {feel:.1f}°"
                for icon, feel in zip(
                    city_df["icon"],
                    city_df["temperature"]
                )
            ]

            trace.mode = "lines+markers+text"
            trace.text = labels
            trace.textposition = positions[i % len(positions)]
            trace.textfont = dict(size=11)

        fig.update_layout(
            height=520,
            hovermode="x unified",
            xaxis_title="Date / Heure",
            yaxis_title="°C"
        )

        fig.update_xaxes(
            rangeslider_visible=False,
            tickformat="%d/%m %H:%M"
        )

        st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------
    # AUTRES
    # -------------------------------------------------
    if "Température ressentie" in selected_graphs:
        graph_line("🥵 Température ressentie", "feels_like", "°C")

    if "Précipitations" in selected_graphs:

        st.subheader("🌧️ Précipitations")

        rain_df = filtered_df.copy()
        rain_df["pop_txt"] = (
            (rain_df["pop"] * 100)
            .round(0)
            .astype(int)
            .astype(str) + "%"
        )

        fig = px.bar(
            rain_df,
            x="timestamp",
            y="rain",
            color="city",
            barmode="group",
            text="pop_txt"
        )

        fig.update_traces(textposition="outside")

        fig.update_layout(
            height=430,
            hovermode="x unified",
            xaxis_title="Date / Heure",
            yaxis_title="mm / 3h"
        )

        fig.update_xaxes(
            rangeslider_visible=False,
            tickformat="%d/%m %H:%M"
        )

        st.plotly_chart(fig, use_container_width=True)

    if "Vent" in selected_graphs:
        graph_line("💨 Vent", "wind_speed", "km/h")

    if "Humidité" in selected_graphs:
        graph_line("💧 Humidité", "humidity", "%")

    if "Pression" in selected_graphs:
        graph_line("🌪️ Pression", "pressure", "hPa")

    if "Nuages" in selected_graphs:
        graph_line("☁️ Nuages", "clouds", "%")

# =====================================================
# ALERTES
# =====================================================
with tab2:

    st.subheader("🚨 Alertes météo")

    frost = filtered_df[filtered_df["temperature"] < 2]

    irrigation = filtered_df[
        (filtered_df["temperature"] > 25) &
        (filtered_df["humidity"] < 40) &
        (filtered_df["rain"] < 1)
    ]

    rain_alert = filtered_df[filtered_df["rain"] > 10]

    wind_alert = filtered_df[filtered_df["wind_speed"] > 60]

    # -----------------------------------------
    # GEL
    # -----------------------------------------
    for _, row in frost.iterrows():
        st.error(
            f"❄️ Gel possible à {row['city']} le "
            f"{row['timestamp'].strftime('%d/%m %H:%M')} | "
            f"Température : {row['temperature']}°C\n\n"
            f"Règle : température < 2°C"
        )

    # -----------------------------------------
    # IRRIGATION
    # -----------------------------------------
    for _, row in irrigation.iterrows():
        st.warning(
            f"🚿 Irrigation recommandée à {row['city']} le "
            f"{row['timestamp'].strftime('%d/%m %H:%M')} | "
            f"Température : {row['temperature']}°C | "
            f"Humidité : {row['humidity']}% | "
            f"Pluie : {row['rain']} mm\n\n"
            f"Règle : température > 25°C ET humidité < 40% ET pluie < 1 mm"
        )

    # -----------------------------------------
    # FORTE PLUIE
    # -----------------------------------------
    for _, row in rain_alert.iterrows():
        st.info(
            f"🌧️ Forte pluie à {row['city']} le "
            f"{row['timestamp'].strftime('%d/%m %H:%M')} | "
            f"Pluie : {row['rain']} mm\n\n"
            f"Règle : pluie > 10 mm / 3h"
        )

    # -----------------------------------------
    # VENT FORT
    # -----------------------------------------
    for _, row in wind_alert.iterrows():
        st.warning(
            f"💨 Vent fort à {row['city']} le "
            f"{row['timestamp'].strftime('%d/%m %H:%M')} | "
            f"Vent : {row['wind_speed']} km/h\n\n"
            f"Règle : vent > 60 km/h"
        )

    # -----------------------------------------
    # AUCUNE ALERTE
    # -----------------------------------------
    if frost.empty and irrigation.empty and rain_alert.empty and wind_alert.empty:
        st.success("✅ Aucune alerte sur la période.")