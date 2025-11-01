import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import os

# =============================
# CONFIGURACIÓN GENERAL
# =============================

st.set_page_config(
    page_title="Dashboard de Sensores",
    page_icon="📊",
    layout="wide",
)

# =============================
# VARIABLES DE CONEXIÓN
# =============================

INFLUX_URL = os.getenv("INFLUX_URL", "https://us-east-1-1.aws.cloud2.influxdata.com")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "TU_TOKEN_AQUI")
INFLUX_ORG = os.getenv("INFLUX_ORG", "0925ccf91ab36478")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "data")

# =============================
# FUNCIÓN DE CONEXIÓN Y CONSULTA
# =============================

def cargar_datos(sensor: str, rango_dias: int = 3) -> pd.DataFrame:
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        query_api = client.query_api()

        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -{rango_dias}d)
          |> filter(fn: (r) => r["sensor"] == "{sensor}")
          |> filter(fn: (r) => r["_measurement"] == "imu")
          |> filter(fn: (r) => r["_field"] =~ /accel_.+/)
          |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
          |> yield(name: "mean")
        '''

        tables = query_api.query_data_frame(query)

        if isinstance(tables, list) and len(tables) > 0:
            df = pd.concat(tables)
        elif isinstance(tables, pd.DataFrame):
            df = tables
        else:
            return pd.DataFrame()

        if df.empty or "_time" not in df.columns:
            return pd.DataFrame()

        df["_time"] = pd.to_datetime(df["_time"])
        df = df.sort_values("_time")

        return df

    except Exception as e:
        st.error(f"Error conectando con InfluxDB: {e}")
        return pd.DataFrame()

# =============================
# INTERFAZ PRINCIPAL
# =============================

st.title("📊 Dashboard de Sensores IMU")
st.markdown("Visualización de datos provenientes de InfluxDB.")

# Selección de sensor y rango de tiempo
col1, col2 = st.columns(2)
with col1:
    sensor = st.selectbox("Selecciona un sensor:", ["Sensor_1", "Sensor_2"])
with col2:
    rango_dias = st.slider("Selecciona rango de tiempo (días):", 1, 30, 3)

# =============================
# CARGA DE DATOS
# =============================

df = cargar_datos(sensor, rango_dias)

if df.empty:
    st.warning("⚠️ No se encontraron datos en el rango seleccionado.")
    st.stop()

# =============================
# VISUALIZACIÓN DE DATOS
# =============================

st.subheader("📈 Evolución temporal")
fields = df["_field"].unique()

for field in fields:
    serie = df[df["_field"] == field].set_index("_time")["_value"]

    if serie.empty:
        continue

    st.markdown(f"**{field}**")
    st.line_chart(serie)

# =============================
# ÚLTIMOS VALORES
# =============================

st.subheader("📄 Últimos valores registrados")

últimos = df.sort_values("_time", ascending=False).groupby("_field").head(1)
for _, fila in últimos.iterrows():
    st.metric(
        label=fila["_field"],
        value=f"{fila['_value']:.2f}",
        delta=None,
    )

# =============================
# TABLA FINAL
# =============================

st.subheader("📋 Tabla de datos")
st.dataframe(df[["_time", "_field", "_value", "sensor"]].tail(100))

