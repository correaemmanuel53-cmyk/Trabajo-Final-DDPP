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
        bac
