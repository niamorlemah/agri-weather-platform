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
st.caption("Prévisions météo agricoles • Dashboard mobile premium")

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
# DB
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
    "📱 Affichage",
    [
        "Conditions actuelles",
        "Prévisions",
        "Température",
        "Précipitations",
        "Alertes"
    ],
    default=[
        "Conditions actuelles",
        "Prévisions",
        "Température"
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

        unique_days = city_df["forecast_time"].dt.date.unique()

        for day in unique_days:

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

            st.markdown("---")

# =====================================================
# TEMPERATURE
# =====================================================
if "Température" in sections:

    st.subheader("🌡️ Température")

    fig = px.line(
        filtered_df,
        x="forecast_time",
        y="temperature",
        color="city",
        markers=True,
        custom_data=[
            "feels_like",
            "humidity",
            "wind_speed"
        ]
    )

    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=8),
        hovertemplate=
        "<b>%{fullData.name}</b><br>" +
        "%{x}<br>" +
        "Temp : %{y:.1f}°C<br>" +
        "Ressenti : %{customdata[0]:.1f}°C<br>" +
        "Humidité : %{customdata[1]:.0f}%<br>" +
        "Vent : %{customdata[2]:.0f} km/h<br>" +
        "<extra></extra>"
    )

    fig.update_layout(
        height=620,
        legend=dict(
            orientation="h",
            y=-0.25
        ),
        margin=dict(l=10, r=10, t=20, b=80)
    )

    fig.update_xaxes(
        nticks=6,
        tickformat="%d/%m %H:%M"
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False,
            "scrollZoom": False,
            "doubleClick": False
        }
    )

# =====================================================
# PRECIPITATIONS
# =====================================================
if "Précipitations" in sections:

    st.subheader("🌧️ Précipitations")

    fig2 = px.bar(
        filtered_df,
        x="forecast_time",
        y="rain",
        color="city",
        barmode="group",
        custom_data=["pop"]
    )

    fig2.update_traces(
        hovertemplate=
        "<b>%{fullData.name}</b><br>" +
        "%{x}<br>" +
        "Pluie : %{y:.1f} mm<br>" +
        "Probabilité : %{customdata[0]:.0%}<br>" +
        "<extra></extra>"
    )

    fig2.update_layout(
        height=520,
        legend=dict(
            orientation="h",
            y=-0.25
        ),
        margin=dict(l=10, r=10, t=20, b=80)
    )

    fig2.update_xaxes(
        nticks=6,
        tickformat="%d/%m %H:%M"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True,
        config={
            "displayModeBar": False,
            "scrollZoom": False,
            "doubleClick": False
        }
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