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

# =====================================================
# CSS MOBILE
# =====================================================
st.markdown("""
<style>
.block-container{
    padding-top:1rem;
    padding-bottom:1rem;
}
@media (max-width:768px){
    .block-container{
        padding-left:0.6rem;
        padding-right:0.6rem;
    }
}
</style>
""", unsafe_allow_html=True)

st.title("🌿 Agri Weather Platform")
st.caption("Plateforme météo agricole • V3 Complete")

# =====================================================
# ICONES
# =====================================================
def meteo_icon(txt):
    txt = str(txt).lower()

    if "rain" in txt or "drizzle" in txt:
        return "🌧️"
    if "cloud" in txt:
        return "☁️"
    if "clear" in txt:
        return "☀️"
    if "storm" in txt or "thunder" in txt:
        return "⛈️"
    if "snow" in txt:
        return "❄️"

    return "🌤️"

# =====================================================
# LOAD DATA
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

df["forecast_time"] = pd.to_datetime(df["forecast_time"], errors="coerce")
df = df.dropna(subset=["forecast_time"])

if df.empty:
    st.warning("Aucune donnée datée disponible.")
    st.stop()

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

sections = st.sidebar.multiselect(
    "📱 Modules visibles",
    [
        "Conditions actuelles",
        "Prévisions",
        "Alertes"
    ],
    default=[
        "Conditions actuelles",
        "Prévisions"
    ]
)

graphs = st.sidebar.multiselect(
    "📈 Graphiques",
    [
        "Température",
        "Ressenti",
        "Vent",
        "Humidité",
        "Pression",
        "Précipitations",
        "Nuages",
        "Probabilité pluie"
    ],
    default=[
        "Température",
        "Précipitations",
        "Vent"
    ]
)

today = date.today()

min_day = df["forecast_time"].min().date()
max_day = df["forecast_time"].max().date()

default_day = today
if default_day < min_day:
    default_day = min_day
if default_day > max_day:
    default_day = max_day

date_range = st.sidebar.date_input(
    "📅 Jour / période",
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
# FILTER DATA
# =====================================================
filtered_df = df[
    (df["city"].isin(selected_cities)) &
    (df["forecast_time"].dt.date >= start_date) &
    (df["forecast_time"].dt.date <= end_date)
].copy()

if filtered_df.empty:
    st.warning("Aucune donnée sur cette période.")
    st.stop()

latest_ts = filtered_df["forecast_time"].max()

latest_df = filtered_df[
    filtered_df["forecast_time"] == latest_ts
].copy()

latest_df["icon"] = latest_df["description"].apply(meteo_icon)

# =====================================================
# COMMON GRAPH CONFIG
# =====================================================
plotly_config = {
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": False
}

# =====================================================
# CONDITIONS ACTUELLES
# =====================================================
if "Conditions actuelles" in sections:

    st.subheader("🌍 Conditions actuelles")

    cols = st.columns(len(latest_df))

    for i, (_, row) in enumerate(latest_df.iterrows()):

        with cols[i]:
            st.markdown(
                f"""
                **{row['city']}**

                # {row['icon']} {row['temperature']:.1f}°

                Ressenti {row['feels_like']:.1f}°  
                💨 {row['wind_speed']:.0f} km/h  
                💧 {row['humidity']:.0f}%
                """
            )

# =====================================================
# PREVISIONS
# =====================================================
if "Prévisions" in sections:

    st.subheader("📅 Prévisions")

    timeline_df = filtered_df.copy()
    timeline_df["icon"] = timeline_df["description"].apply(meteo_icon)

    for city in selected_cities:

        city_df = timeline_df[
            timeline_df["city"] == city
        ].sort_values("forecast_time")

        if city_df.empty:
            continue

        st.markdown(f"### {city}")

        for day in city_df["forecast_time"].dt.date.unique():

            day_df = city_df[
                city_df["forecast_time"].dt.date == day
            ]

            st.markdown(
                f"**📆 {pd.to_datetime(day).strftime('%A %d/%m')}**"
            )

            cols = st.columns(len(day_df))

            for i, (_, row) in enumerate(day_df.iterrows()):

                with cols[i]:
                    st.markdown(
                        f"""
                        {row['forecast_time'].strftime('%Hh')}  
                        {row['icon']}  
                        **{row['temperature']:.0f}°**
                        """
                    )

# =====================================================
# GRAPH FUNCTION
# =====================================================
def draw_line_graph(title, column, unit):

    st.subheader(title)

    fig = px.line(
        filtered_df,
        x="forecast_time",
        y=column,
        color="city",
        markers=True
    )

    fig.update_layout(
        height=520,
        dragmode=False,
        legend=dict(
            orientation="h",
            y=-0.25
        ),
        margin=dict(l=10, r=10, t=20, b=80),
        yaxis_title=unit
    )

    fig.update_xaxes(
        nticks=6,
        tickformat="%d/%m %H:%M"
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config=plotly_config
    )

# =====================================================
# GRAPHES
# =====================================================
if "Température" in graphs:
    draw_line_graph("🌡️ Température", "temperature", "°C")

if "Ressenti" in graphs:
    draw_line_graph("🥵 Ressenti", "feels_like", "°C")

if "Vent" in graphs:
    draw_line_graph("💨 Vent", "wind_speed", "km/h")

if "Humidité" in graphs:
    draw_line_graph("💧 Humidité", "humidity", "%")

if "Pression" in graphs:
    draw_line_graph("🧭 Pression", "pressure", "hPa")

if "Nuages" in graphs:
    draw_line_graph("☁️ Nuages", "clouds", "%")

if "Probabilité pluie" in graphs:
    draw_line_graph("🎯 Probabilité pluie", "pop", "%")

if "Précipitations" in graphs:

    st.subheader("🌧️ Précipitations")

    fig = px.bar(
        filtered_df,
        x="forecast_time",
        y="rain",
        color="city",
        barmode="group"
    )

    fig.update_layout(
        height=520,
        dragmode=False,
        legend=dict(
            orientation="h",
            y=-0.25
        ),
        margin=dict(l=10, r=10, t=20, b=80),
        yaxis_title="mm"
    )

    fig.update_xaxes(
        nticks=6,
        tickformat="%d/%m %H:%M"
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config=plotly_config
    )

# =====================================================
# ALERTES
# =====================================================
if "Alertes" in sections:

    st.subheader("🚨 Alertes météo")

    alerts = 0

    for _, row in filtered_df.iterrows():

        if row["risk_frost"]:
            alerts += 1
            st.error(
                f"❄️ {row['city']} • "
                f"{row['forecast_time'].strftime('%d/%m %H:%M')} "
                f"(Température < 2°C)"
            )

        if row["irrigation_needed"]:
            alerts += 1
            st.warning(
                f"🚿 {row['city']} • "
                f"{row['forecast_time'].strftime('%d/%m %H:%M')} "
                f"(Irrigation recommandée)"
            )

        if row["rain"] > 10:
            alerts += 1
            st.info(
                f"🌧️ {row['city']} • "
                f"{row['forecast_time'].strftime('%d/%m %H:%M')} "
                f"(Pluie > 10 mm)"
            )

        if row["wind_speed"] > 60:
            alerts += 1
            st.warning(
                f"💨 {row['city']} • "
                f"{row['forecast_time'].strftime('%d/%m %H:%M')} "
                f"(Vent > 60 km/h)"
            )

    if alerts == 0:
        st.success("✅ Aucune alerte détectée.")

# =====================================================
# FOOTER
# =====================================================
st.divider()

st.caption(
    f"Dernière mise à jour : {latest_ts.strftime('%d/%m/%Y %H:%M')}"
)