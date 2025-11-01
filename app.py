import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import os

# =============================
# CONFIGURACIÓN GENERAL
# =============================

st.set_page_config(
    page_title="Dashboard de Sensores IMU",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Dashboard de Sensores IMU")
st.markdown("Visualización comparativa de datos provenientes de **InfluxDB** para ambos sensores.")

# =============================
# CONFIGURACIÓN DE INFLUXDB
# =============================

INFLUX_URL = os.getenv("INFLUX_URL", "https://us-east-1-1.aws.cloud2.influxdata.com")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "TU_TOKEN_AQUI")  # ⚠️ Reemplaza por tu token válido
INFLUX_ORG = os.getenv("INFLUX_ORG", "0925ccf91ab36478")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "data")

# =============================
# FUNCIÓN PARA CARGAR DATOS
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

        result = query_api.query_data_frame(query)

        if isinstance(result, list) and len(result) > 0:
            df = pd.concat(result)
        elif isinstance(result, pd.DataFrame):
            df = result
        else:
            return pd.DataFrame()

        if df.empty or "_time" not in df.columns:
            return pd.DataFrame()

        df["_time"] = pd.to_datetime(df["_time"])
        df = df.sort_values("_time")
        df["sensor"] = sensor

        return df

    except Exception as e:
        st.error(f"Error conectando con InfluxDB ({sensor}): {e}")
        return pd.DataFrame()

# =============================
# PARÁMETROS DE DASHBOARD
# =============================

rango_dias = 3  # fijo, puedes cambiarlo a 7 o 30

# Cargar ambos sensores
df1 = cargar_datos("Sensor_1", rango_dias)
df2 = cargar_datos("Sensor_2", rango_dias)

# Combinar datos
df = pd.concat([df1, df2], ignore_index=True)

if df.empty:
    st.warning("⚠️ No se encontraron datos en el rango seleccionado para ninguno de los sensores.")
    st.stop()

# =============================
# VISUALIZACIÓN DE DATOS
# =============================

st.subheader("📈 Evolución temporal comparativa")

for eje in ["accel_x", "accel_y", "accel_z"]:
    st.markdown(f"### {eje.upper()}")

    # Pivotar para mostrar ambos sensores en una misma gráfica
    df_eje = df[df["_field"] == eje].pivot(index="_time", columns="sensor", values="_value")

    if df_eje.empty:
        st.warning(f"No hay datos disponibles para {eje}")
        continue

    st.line_chart(df_eje)

# =============================
# ÚLTIMOS VALORES REGISTRADOS
# =============================

st.subheader("📄 Últimos valores registrados")

últimos = df.sort_values("_time", ascending=False).groupby(["sensor", "_field"]).head(1)
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Sensor_1")
    for _, fila in últimos[últimos["sensor"] == "Sensor_1"].iterrows():
        st.metric(fila["_field"], f"{fila['_value']:.2f}")

with col2:
    st.markdown("#### Sensor_2")
    for _, fila in últimos[últimos["sensor"] == "Sensor_2"].iterrows():
        st.metric(fila["_field"], f"{fila['_value']:.2f}")

# =============================
# TABLA FINAL
# =============================

st.subheader("📋 Últimos datos combinados")
st.dataframe(df[["_time", "sensor", "_field", "_value"]].tail(100))
