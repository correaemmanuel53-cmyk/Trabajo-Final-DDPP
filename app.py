import streamlit as st
import pandas as pd
import numpy as np
from influxdb_client import InfluxDBClient
import plotly.graph_objects as go
from datetime import datetime
import time
import os
from dotenv import load_dotenv

# -------------------------------------------------
# CARGAR .env
# -------------------------------------------------
load_dotenv()

INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

if not all([INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
    st.error("Faltan credenciales en el archivo .env")
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
# CSS
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
      |> filter(fn: (r) => 
          r._measurement == "studio-dht22" or 
          r._measurement == "mpu6050"
      )
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> keep(columns: [
          "_time",
          "temperatura", "humedad", "sensacion_termica",
          "accel_x", "accel_y", "accel_z",
          "gyro_x", "gyro_y", "gyro_z"
      ])
    '''
    try:
        result = query_api.query(org=INFLUXDB_ORG, query=query)
        rows = []
        for table in result:
            for rec in table.records:
                row = {"_time": rec.get_time()}
                for field in ["temperatura", "humedad", "sensacion_termica",
                              "accel_x", "accel_y", "accel_z",
                              "gyro_x", "gyro_y", "gyro_z"]:
                    row[field] = rec.values.get(field)
                rows.append(row)
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        df["_time"] = pd.to_datetime(df["_time"])
        df = df.set_index("_time").sort_index()
        
        for c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        
        df = df.dropna(how="all")
        return df
    except Exception as e:
        st.error(f"Error al consultar InfluxDB: {e}")
        return pd.DataFrame()

# -------------------------------------------------
# TÍTULO
# -------------------------------------------------
st.markdown('<h1 class="main-header">Factory Extreme Manufacturing – Celda de Secado</h1>', unsafe_allow_html=True)

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
with st.sidebar:
    st.title("Controles")
    range_hours = st.slider("Rango de datos (horas)", 1, 168, 24, key="range_slider")
    auto_refresh = st.checkbox("Auto-refresh cada 30s", value=True)
    if st.button("Recargar datos"):
        st.cache_data.clear()
        st.success("Datos recargados")

# -------------------------------------------------
# CARGAR DATOS
# -------------------------------------------------
with st.spinner("Cargando datos desde InfluxDB..."):
    df = get_data(range_hours)

if df.empty:
    st.warning("No se encontraron datos en el rango seleccionado.")
    st.stop()

df_resampled = df.resample("1min").mean()

# -------------------------------------------------
# MÉTRICAS EN VIVO (CORREGIDO: RMS robusto)
# -------------------------------------------------
st.markdown("## Métricas en Tiempo Real")
latest = df.iloc[-1]
cols = st.columns(4)

metrics = [
    ("Temperatura", "temperatura", "°C", (20, 40), (15, 45)),
    ("Humedad", "humedad", "%", (30, 70), (20, 80)),
    ("Sensación Térmica", "sensacion_termica", "°C", (20, 45), (15, 50)),
    ("Vibración RMS", None, "g", (0, 1.0), (0, 1.5))
]

for i, (lbl, field, unit, good, warn) in enumerate(metrics):
    with cols[i]:
        if field and field in latest.index:
            val = latest[field]
            if pd.isna(val):
                val = 0.0
        elif field:
            val = 0.0
        else:
            # RMS de aceleración (CORREGIDO)
            accel_cols = ["accel_x", "accel_y", "accel_z"]
            values = []
            for col in accel_cols:
                if col in latest.index:
                    v = latest[col]
                    if pd.notna(v):
                        values.append(v**2)
            if values:
                val = np.sqrt(sum(values))
            else:
                val = 0.0
        
        val = round(float(val), 2)

        # Estado
        if good[0] <= val <= good[1]:
            st_class, status = "status-good", "Normal"
        elif warn[0] <= val <= warn[1]:
            st_class, status = "status-warning", "Advertencia"
        else:
            st_class, status = "status-critical", "Crítico"
        
        st.metric(lbl, f"{val} {unit}")
        st.markdown(f'<div class="{st_class}">{status}</div>', unsafe_allow_html=True)

# -------------------------------------------------
# GRÁFICO DHT22
# -------------------------------------------------
st.markdown("## DHT22 – Condiciones Ambientales")
fig_dht = go.Figure()

if "temperatura" in df_resampled.columns:
    fig_dht.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled["temperatura"],
                                 name="Temperatura", line=dict(color="red")))
if "humedad" in df_resampled.columns:
    fig_dht.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled["humedad"],
                                 name="Humedad", yaxis="y2", line=dict(color="blue")))
if "sensacion_termica" in df_resampled.columns:
    fig_dht.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled["sensacion_termica"],
                                 name="Sensación Térmica", line=dict(color="orange", dash="dot")))

fig_dht.update_layout(
    title="DHT22: Temperatura, Humedad y Sensación Térmica",
    yaxis=dict(title="Temperatura (°C)"),
    yaxis2=dict(title="Humedad (%)", overlaying="y", side="right"),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig_dht, use_container_width=True)

# -------------------------------------------------
# GRÁFICO ACELERACIÓN
# -------------------------------------------------
st.markdown("## MPU6050 – Aceleración")
fig_acc = go.Figure()
colors_acc = {"accel_x": "red", "accel_y": "green", "accel_z": "blue"}
labels = {"accel_x": "X", "accel_y": "Y", "accel_z": "Z"}  # Definido aquí

for col in ["accel_x", "accel_y", "accel_z"]:
    if col in df_resampled.columns:
        fig_acc.add_trace(go.Scatter(
            x=df_resampled.index, y=df_resampled[col],
            name=f"Aceleración {labels[col]}",
            line=dict(color=colors_acc[col])
        ))

fig_acc.update_layout(title="Aceleración (g)", hovermode="x unified")
st.plotly_chart(fig_acc, use_container_width=True)

# -------------------------------------------------
# GRÁFICO GIROSCOPIO (CORREGIDO)
# -------------------------------------------------
st.markdown("## MPU6050 – Giroscopio")
fig_gyr = go.Figure()
colors_gyr = {"gyro_x": "purple", "gyro_y": "orange", "gyro_z": "cyan"}
labels = {"gyro_x": "X", "gyro_y": "Y", "gyro_z": "Z"}  # Re-definido aquí

for col in ["gyro_x", "gyro_y", "gyro_z"]:
    if col in df_resampled.columns:
        fig_gyr.add_trace(go.Scatter(
            x=df_resampled.index, y=df_resampled[col],
            name=f"Giro {labels[col]}",  # Ahora labels existe
            line=dict(color=colors_gyr[col])
        ))

fig_gyr.update_layout(title="Giro (°/s)", hovermode="x unified")
st.plotly_chart(fig_gyr, use_container_width=True)

# -------------------------------------------------
# ANÁLISIS PREDICTIVO
# -------------------------------------------------
st.markdown("## Análisis Predictivo")
window = st.slider("Ventana promedio móvil (min)", 5, 60, 15, key="predict_window")
df_ma = df_resampled.rolling(f"{window}T").mean()
df_std = df_resampled.rolling(f"{window}T").std()

# Temperatura
mask_temp = pd.Series([False] * len(df_resampled), index=df_resampled.index)
if "temperatura" in df_resampled.columns:
    upper = df_ma["temperatura"] + 2.5 * df_std["temperatura"]
    lower = df_ma["temperatura"] - 2.5 * df_std["temperatura"]
    mask_temp = (df_resampled["temperatura"] > upper) | (df_resampled["temperatura"] < lower)

# Vibración RMS
accel_cols = [c for c in ["accel_x", "accel_y", "accel_z"] if c in df_resampled.columns]
vib_rms = pd.Series(0.0, index=df_resampled.index)
if accel_cols:
    vib_rms = np.sqrt((df_resampled[accel_cols]**2).sum(axis=1))

ma_vib = vib_rms.rolling(f"{window}T").mean()
std_vib = vib_rms.rolling(f"{window}T").std()
mask_vib = (vib_rms > ma_vib + 2.5*std_vib) | (vib_rms < ma_vib - 2.5*std_vib)

col1, col2 = st.columns(2)
with col1:
    fig_temp = go.Figure()
    if "temperatura" in df_resampled.columns:
        fig_temp.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled["temperatura"], name="Real"))
        fig_temp.add_trace(go.Scatter(x=df_ma.index, y=df_ma["temperatura"], name="Promedio", line=dict(dash="dash")))
        if mask_temp.any():
            fig_temp.add_trace(go.Scatter(x=df_resampled[mask_temp].index, y=df_resampled[mask_temp]["temperatura"],
                                          mode="markers", name="Anomalía", marker=dict(color="red", size=8)))
    fig_temp.update_layout(title=f"Temperatura – Ventana {window} min")
    st.plotly_chart(fig_temp, use_container_width=True)

with col2:
    fig_vib = go.Figure()
    fig_vib.add_trace(go.Scatter(x=vib_rms.index, y=vib_rms, name="RMS Real"))
    fig_vib.add_trace(go.Scatter(x=ma_vib.index, y=ma_vib, name="Promedio", line=dict(dash="dash")))
    if mask_vib.any():
        fig_vib.add_trace(go.Scatter(x=vib_rms[mask_vib].index, y=vib_rms[mask_vib],
                                      mode="markers", name="Anomalía", marker=dict(color="red", size=8)))
    fig_vib.update_layout(title=f"Vibración RMS – Ventana {window} min")
    st.plotly_chart(fig_vib, use_container_width=True)

st.warning(f"Anomalías detectadas: {int(mask_temp.sum() + mask_vib.sum())}")

# -------------------------------------------------
# RESUMEN ESTADÍSTICO
# -------------------------------------------------
st.markdown("## Resumen Estadístico")
stats = df.describe().round(2).T
units = {
    "temperatura": "°C", "humedad": "%", "sensacion_termica": "°C",
    "accel_x": "g", "accel_y": "g", "accel_z": "g",
    "gyro_x": "°/s", "gyro_y": "°/s", "gyro_z": "°/s"
}
stats["unidad"] = stats.index.map(units)
st.dataframe(stats[["mean", "std", "min", "max", "unidad"]], use_container_width=True)

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
    st.markdown(f"**Última actualización:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
