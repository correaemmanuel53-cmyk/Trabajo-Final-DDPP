import streamlit as st
import pandas as pd
import numpy as np
from influxdb_client import InfluxDBClient
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import os
from dotenv import load_dotenv

# -------------------------------------------------
# CREDENCIALES (Streamlit Secrets o .env)
# -------------------------------------------------
if "INFLUXDB_URL" in st.secrets:
    INFLUXDB_URL = st.secrets["INFLUXDB_URL"]
    INFLUXDB_TOKEN = st.secrets["INFLUXDB_TOKEN"]
    INFLUXDB_ORG = st.secrets["INFLUXDB_ORG"]
    INFLUXDB_BUCKET = st.secrets["INFLUXDB_BUCKET"]
else:
    load_dotenv()
    INFLUXDB_URL = os.getenv("INFLUXDB_URL")
    INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
    INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
    INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

if not all([INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
    st.error("Faltan credenciales de InfluxDB.")
    st.stop()

# -------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# -------------------------------------------------
st.set_page_config(
    page_title="Extreme Manufacturing – Celda de Secado",
    page_icon="Factory",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# CSS (solo lo esencial)
# -------------------------------------------------
st.markdown("""
<style>
    .main-header{font-size:2.8rem;font-weight:bold;color:#1f77b4;text-align:center;margin-bottom:2rem;}
    .status-good{background:linear-gradient(135deg,#11998e 0%,#38ef7d 100%);color:white;padding:.5rem;border-radius:5px;text-align:center;font-weight:bold;}
    .status-warning{background:linear-gradient(135deg,#f093fb 0%,#f5576c 100%);color:white;padding:.5rem;border-radius:5px;text-align:center;font-weight:bold;}
    .status-critical{background:linear-gradient(135deg,#ff9a9e 0%,#fecfef 100%);color:white;padding:.5rem;border-radius:5px;text-align:center;font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# CLIENTE INFLUXDB
# -------------------------------------------------
@st.cache_resource
def get_client():
    return InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

client = get_client()
query_api = client.query_api()

# -------------------------------------------------
# OBTENER DATOS
# -------------------------------------------------
@st.cache_data(ttl=60)
def get_data(range_hours=24):
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -{range_hours}h)
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> keep(columns: ["_time","temperature","humidity","heat_index",
                       "accel_x","accel_y","accel_z","gyro_x","gyro_y","gyro_z"])
    '''
    try:
        result = query_api.query(org=INFLUXDB_ORG, query=query)
        rows = []
        for table in result:
            for rec in table.records:
                rows.append({
                    "_time": rec.get_time(),
                    "temperature": rec.values.get("temperature"),
                    "humidity": rec.values.get("humidity"),
                    "heat_index": rec.values.get("heat_index"),
                    "accel_x": rec.values.get("accel_x"),
                    "accel_y": rec.values.get("accel_y"),
                    "accel_z": rec.values.get("accel_z"),
                    "gyro_x": rec.values.get("gyro_x"),
                    "gyro_y": rec.values.get("gyro_y"),
                    "gyro_z": rec.values.get("gyro_z")
                })
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df["_time"] = pd.to_datetime(df["_time"])
        df = df.set_index("_time").sort_index()

        # Numérico + limpiar filas vacías
        for c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(how="all", subset=df.columns)
        return df
    except Exception as e:
        st.error(f"Error InfluxDB: {e}")
        return pd.DataFrame()

# -------------------------------------------------
# TÍTULO
# -------------------------------------------------
st.markdown('<h1 class="main-header">Factory Extreme Manufacturing – Celda de Secado</h1>', unsafe_allow_html=True)

# -------------------------------------------------
# SIDEBAR (solo controles)
# -------------------------------------------------
with st.sidebar:
    st.title("Controls")
    range_hours = st.slider("Rango (horas)", 1, 168, 24)
    auto_refresh = st.checkbox("Auto-refresh (30 s)")

    if st.button("Recargar"):
        st.cache_data.clear()

# -------------------------------------------------
# CARGAR DATOS
# -------------------------------------------------
with st.spinner("Cargando datos…"):
    df = get_data(range_hours)

if df.empty:
    st.warning("No hay datos en el rango seleccionado.")
    st.stop()

df_resampled = df.resample("1min").mean()

# -------------------------------------------------
# MÉTRICAS EN VIVO
# -------------------------------------------------
st.markdown("## Real-Time Métricas")
latest = df.iloc[-1]
cols = st.columns(4)

metrics = [
    ("Temperatura", "temperature", "°C", (20, 40), (15, 45)),
    ("Humedad", "humidity", "%", (30, 70), (20, 80)),
    ("Sensación Térmica", "heat_index", "°C", (20, 45), (15, 50)),
    ("Vibración RMS", None, "g", (0, 1.0), (0, 1.5))
]

for i, (lbl, field, unit, good, warn) in enumerate(metrics):
    with cols[i]:
        if field:
            val = latest.get(field)
            val = val if pd.notna(val) else 0.0
        else:
            # RMS de aceleración
            val = np.sqrt((df[["accel_x","accel_y","accel_z"]].iloc[-1]**2).sum())

        # Estado
        if good[0] <= val <= good[1]:
            st_class = "status-good"
            status = "Normal"
        elif warn[0] <= val <= warn[1]:
            st_class = "status-warning"
            status = "Advertencia"
        else:
            st_class = "status-critical"
            status = "Crítico"

        st.metric(lbl, f"{val:.2f} {unit}")
        st.markdown(f'<div class="{st_class}">{status}</div>', unsafe_allow_html=True)

# -------------------------------------------------
# GRÁFICOS DHT22
# -------------------------------------------------
st.markdown("## DHT22 – Condiciones Ambientales")
fig_dht = go.Figure()
fig_dht.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled["temperature"],
                             name="Temperatura", line=dict(color="red")))
fig_dht.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled["humidity"],
                             name="Humedad", yaxis="y2", line=dict(color="blue")))
fig_dht.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled["heat_index"],
                             name="Sensación Térmica", line=dict(color="orange", dash="dot")))
fig_dht.update_layout(
    title="DHT22",
    yaxis=dict(title="°C"),
    yaxis2=dict(title="%", overlaying="y", side="right"),
    hovermode="x unified"
)
st.plotly_chart(fig_dht, use_container_width=True)

# -------------------------------------------------
# GRÁFICOS MPU6050 – ACELERACIÓN
# -------------------------------------------------
st.markdown("## MPU6050 – Aceleración")
fig_acc = go.Figure()
for ax, col in zip(["X","Y","Z"], ["red","green","blue"]):
    fig_acc.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled[f"accel_{ax.lower()}"],
                                 name=f"Aceleración {ax}", line=dict(color=col)))
fig_acc.update_layout(title="Aceleración (g)", hovermode="x unified")
st.plotly_chart(fig_acc, use_container_width=True)

# -------------------------------------------------
# GRÁFICOS MPU6050 – GIROSCOPIO
# -------------------------------------------------
st.markdown("## MPU6050 – Giroscopio")
fig_gyr = go.Figure()
for ax, col in zip(["X","Y","Z"], ["purple","orange","cyan"]):
    fig_gyr.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled[f"gyro_{ax.lower()}"],
                                 name=f"Giro {ax}", line=dict(color=col)))
fig_gyr.update_layout(title="Giro (°/s)", hovermode="x unified")
st.plotly_chart(fig_gyr, use_container_width=True)

# -------------------------------------------------
# ANÁLISIS PREDICTIVO (Promedio móvil + anomalías)
# -------------------------------------------------
st.markdown("## Predictive Análisis Predictivo")
window = st.slider("Ventana promedio móvil (min)", 5, 60, 15)
df_ma  = df_resampled.rolling(f"{window}T").mean()
df_std = df_resampled.rolling(f"{window}T").std()

# Anomalías en temperatura
mask_temp = (df_resampled["temperature"] > df_ma["temperature"] + 2.5*df_std["temperature"]) | \
            (df_resampled["temperature"] < df_ma["temperature"] - 2.5*df_std["temperature"])

# RMS vibración
vib_rms = (df_resampled[["accel_x","accel_y","accel_z"]]**2).sum(axis=1).apply(np.sqrt)
ma_vib  = vib_rms.rolling(f"{window}T").mean()
std_vib = vib_rms.rolling(f"{window}T").std()
mask_vib = (vib_rms > ma_vib + 2.5*std_vib) | (vib_rms < ma_vib - 2.5*std_vib)

col1, col2 = st.columns(2)
with col1:
    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled["temperature"], name="Real"))
    fig_temp.add_trace(go.Scatter(x=df_ma.index, y=df_ma["temperature"], name="Promedio", line=dict(dash="dash")))
    if mask_temp.any():
        fig_temp.add_trace(go.Scatter(x=df_resampled[mask_temp].index,
                                      y=df_resampled[mask_temp]["temperature"],
                                      mode="markers", name="Anomalía", marker=dict(color="red", size=8)))
    fig_temp.update_layout(title=f"Temperatura – {window} min")
    st.plotly_chart(fig_temp, use_container_width=True)

with col2:
    fig_vib = go.Figure()
    fig_vib.add_trace(go.Scatter(x=vib_rms.index, y=vib_rms, name="RMS"))
    fig_vib.add_trace(go.Scatter(x=ma_vib.index, y=ma_vib, name="Promedio", line=dict(dash="dash")))
    if mask_vib.any():
        fig_vib.add_trace(go.Scatter(x=vib_rms[mask_vib].index,
                                     y=vib_rms[mask_vib],
                                     mode="markers", name="Anomalía", marker=dict(color="red", size=8)))
    fig_vib.update_layout(title=f"Vibración RMS – {window} min")
    st.plotly_chart(fig_vib, use_container_width=True)

st.warning(f"Anomalías detectadas: {mask_temp.sum() + mask_vib.sum()}")

# -------------------------------------------------
# RESUMEN ESTADÍSTICO
# -------------------------------------------------
st.markdown("## Summary Resumen")
stats = df.describe().round(2).T
units = ["°C","%","°C","g","g","g","°/s","°/s","°/s"]
stats["unidad"] = units
st.dataframe(stats[["mean","std","min","max","unidad"]], use_container_width=True)

# -------------------------------------------------
# AUTO-REFRESH
# -------------------------------------------------
if auto_refresh:
    time.sleep(30)
    st.rerun()

# -------------------------------------------------
# FOOTER
# -------------------------------------------------
st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Proyecto Final – Digitalización de Plantas**")
with c2:
    st.markdown(f"**Última actualización:** {datetime.now().strftime('%H:%M:%S')}")
