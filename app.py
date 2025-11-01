import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv
import os

# =========================
# CONFIGURACIÓN GENERAL
# =========================
st.set_page_config(page_title="Dashboard IMU", layout="wide")
load_dotenv()

# Variables del entorno
INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

# =========================
# FUNCIÓN DE CONEXIÓN Y LECTURA
# =========================
@st.cache_data(ttl=300)
def obtener_datos():
    """Obtiene los últimos datos de InfluxDB"""
    try:
        client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        query_api = client.query_api()

        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -1d)
          |> filter(fn: (r) => r["_measurement"] == "imu")
          |> last()
        '''
        df = query_api.query_data_frame(org=INFLUXDB_ORG, query=query)

        if isinstance(df, list):
            df = pd.concat(df, ignore_index=True)

        if df.empty:
            return pd.DataFrame()

        df["_time"] = pd.to_datetime(df["_time"])
        return df

    except Exception as e:
        st.error(f"Error conectando con InfluxDB: {e}")
        return pd.DataFrame()

# =========================
# LECTURA DE DATOS
# =========================
df = obtener_datos()

if df.empty:
    st.warning("⚠️ No se encontraron datos recientes en InfluxDB.")
    st.stop()

# =========================
# PROCESAMIENTO DE ÚLTIMOS DATOS
# =========================
ultimo_registro = df.sort_values("_time").groupby("_field").tail(1)

# =========================
# INTERFAZ VISUAL
# =========================
st.title("📊 Dashboard IMU")
st.caption("Visualización simple de los últimos datos registrados desde InfluxDB")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🧭 Sensor 1 - Últimos valores")
    for field in ["accel_x", "accel_y", "accel_z"]:
        try:
            valor = ultimo_registro[ultimo_registro["_field"] == field]["_value"].values[0]
            st.metric(label=field.upper(), value=f"{valor:.2f}")
        except:
            st.write(f"{field}: sin datos")

with col2:
    st.subheader("🧭 Sensor 2 - Últimos valores")
    for field in ["gyro_x", "gyro_y", "gyro_z"]:
        try:
            valor = ultimo_registro[ultimo_registro["_field"] == field]["_value"].values[0]
            st.metric(label=field.upper(), value=f"{valor:.2f}")
        except:
            st.write(f"{field}: sin datos")

st.success("✅ Dashboard cargado correctamente")
