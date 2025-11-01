import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv
import os

# =========================
# CONFIGURACIÓN GENERAL
# =========================
st.set_page_config(page_title="Dashboard Sensorial", layout="wide")
load_dotenv()

# Variables desde .env
INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

# =========================
# CONEXIÓN CON INFLUXDB
# =========================
@st.cache_data(ttl=300)
def get_data(days: int):
    """Obtiene datos de los últimos N días desde InfluxDB."""
    try:
        client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        query_api = client.query_api()

        start_time = datetime.utcnow() - timedelta(days=days)
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {start_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "sensor_data")
          |> filter(fn: (r) => r["_field"] == "temperatura" or r["_field"] == "humedad" or r["_field"] == "sensacion")
        '''
        result = query_api.query_data_frame(org=INFLUXDB_ORG, query=query)

        # ✅ Maneja lista o único DataFrame correctamente
        if isinstance(result, list):
            df = pd.concat(result, ignore_index=True)
        else:
            df = result

        # Validación de datos
        if df is None or df.empty:
            return pd.DataFrame()

        df["_time"] = pd.to_datetime(df["_time"])
        return df

    except Exception as e:
        st.error(f"Error conectando con InfluxDB: {e}")
        return pd.DataFrame()

# =========================
# SIDEBAR DE CONTROL
# =========================
st.sidebar.header("Configuración de rango de tiempo")
rango_dias = st.sidebar.slider(
    "Selecciona rango de tiempo (días):", 1, 30, 3, key="slider_rango_dias"
)

# =========================
# LECTURA DE DATOS
# =========================
df = get_data(rango_dias)

if df.empty:
    st.warning("⚠️ No se encontraron datos en el rango seleccionado.")
    st.stop()

# =========================
# ÚLTIMOS VALORES
# =========================
df_latest = df.sort_values("_time").groupby("_field").tail(1)

ultima_temp = df_latest[df_latest["_field"] == "temperatura"]["_value"].values[0]
ultima_hum = df_latest[df_latest["_field"] == "humedad"]["_value"].values[0]
ultima_sens = df_latest[df_latest["_field"] == "sensacion"]["_value"].values[0]

# Cambios respecto al valor anterior (último menos penúltimo)
df_sorted = df.sort_values("_time")

def cambio_campo(campo):
    vals = df_sorted[df_sorted["_field"] == campo]["_value"].tail(2).values
    return vals[-1] - vals[-2] if len(vals) == 2 else 0

cambio_temp = cambio_campo("temperatura")
cambio_hum = cambio_campo("humedad")
cambio_sens = cambio_campo("sensacion")

# =========================
# ESTILO VISUAL
# =========================
st.markdown("""
<style>
    body, .stApp {
        background-color: #ffffff;
        color: #000000;
    }
    .stMetric {
        background-color: #f5fff5;
        border: 1px solid #00aa55;
        border-radius: 10px;
        padding: 10px;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.1);
    }
    h1, h2, h3, .stMarkdown, .stSubheader {
        color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# TARJETAS DE INDICADORES
# =========================
st.subheader("📊 Estado Actual de Variables Ambientales")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Temperatura", f"{ultima_temp:.1f} °C", f"{cambio_temp:+.1f}")
with col2:
    st.metric("Humedad", f"{ultima_hum:.1f} %", f"{cambio_hum:+.1f}")
with col3:
    st.metric("Sensación", f"{ultima_sens:.1f} °C", f"{cambio_sens:+.1f}")

st.markdown("---")

# =========================
# GRÁFICOS Y TABLA
# =========================
st.subheader("📈 Evolución temporal")

tabs = st.tabs(["Temperatura", "Humedad", "Sensación", "Tabla de datos"])

with tabs[0]:
    st.line_chart(
        df[df["_field"] == "temperatura"].set_index("_time")["_value"],
        key="chart_temp"
    )
with tabs[1]:
    st.line_chart(
        df[df["_field"] == "humedad"].set_index("_time")["_value"],
        key="chart_hum"
    )
with tabs[2]:
    st.line_chart(
        df[df["_field"] == "sensacion"].set_index("_time")["_value"],
        key="chart_sens"
    )
with tabs[3]:
    st.dataframe(
        df[["_time", "_field", "_value"]],
        use_container_width=True,
        key="tabla_final"
    )

st.success("✅ Dashboard actualizado correctamente")
