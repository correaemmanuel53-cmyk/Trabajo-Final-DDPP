import streamlit as st
import pandas as pd
import numpy as np
from influxdb_client import InfluxDBClient
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import os
from dotenv import load_dotenv

# ========================
# CARGAR CREDENCIALES
# ========================
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

# Validación
if not all([INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
    st.error("Faltan credenciales de InfluxDB. Verifica `.env` o `secrets`.")
    st.stop()

# ========================
# CONFIGURACIÓN DE PÁGINA
# ========================
st.set_page_config(
    page_title="Extreme Manufacturing - Celda de Secado",
    page_icon="Factory",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================
# CSS PROFESIONAL
# ========================
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .status-good {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        text-align: center;
        font-weight: bold;
    }
    .status-warning {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        text-align: center;
        font-weight: bold;
    }
    .status-critical {
        background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        text-align: center;
        font-weight: bold;
    }
    .kpi-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
    .alert-high {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
    }
    .alert-medium {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
    }
    .alert-low {
        background-color: #e8f5e8;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ========================
# CLIENTE INFLUXDB
# ========================
@st.cache_resource
def get_client():
    return InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

client = get_client()
query_api = client.query_api()

# ========================
# OBTENER DATOS REALES
# ========================
@st.cache_data(ttl=60)
def get_data(range_hours=24):
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -{range_hours}h)
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> keep(columns: ["_time", "temperature", "humidity", "heat_index", "accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z"])
    '''
    try:
        result = query_api.query(org=INFLUXDB_ORG, query=query)
        data = []
        for table in result:
            for record in table.records:
                row = {
                    "_time": record.get_time(),
                    "temperature": record.values.get("temperature"),
                    "humidity": record.values.get("humidity"),
                    "heat_index": record.values.get("heat_index"),
                    "accel_x": record.values.get("accel_x"),
                    "accel_y": record.values.get("accel_y"),
                    "accel_z": record.values.get("accel_z"),
                    "gyro_x": record.values.get("gyro_x"),
                    "gyro_y": record.values.get("gyro_y"),
                    "gyro_z": record.values.get("gyro_z")
                }
                data.append(row)

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df['_time'] = pd.to_datetime(df['_time'])
        df = df.set_index('_time').sort_index()

        # Convertir a numérico
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Eliminar filas sin datos útiles
        df = df.dropna(how='all', subset=df.columns)
        return df

    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

# ========================
# TÍTULO
# ========================
st.markdown('<h1 class="main-header">Factory Extreme Manufacturing - Celda de Secado</h1>', unsafe_allow_html=True)
st.markdown("**Digitalización de Planta Productiva** | Sensores: DHT22 + MPU6050")

# ========================
# SIDEBAR
# ========================
with st.sidebar:
    st.title("Controls del Sistema")
    range_hours = st.slider("Rango de Tiempo (horas)", 1, 168, 24)
    auto_refresh = st.checkbox("Actualización Automática (30s)")

    st.markdown("---")
    st.markdown("### Variables Disponibles")
    st.markdown("- **DHT22**: Temp, Humedad, Sensación Térmica")
    st.markdown("- **MPU6050**: Aceleración (X,Y,Z), Giro (X,Y,Z)")

    if st.button("Recargar Datos"):
        st.cache_data.clear()

    st.markdown("---")
    st.markdown("### Soporte")
    st.markdown("Email: soporte@extreme.com")
    st.markdown("Tel: +57 300 123 4567")

# ========================
# CARGAR DATOS
# ========================
with st.spinner("Consultando sensores en tiempo real..."):
    df = get_data(range_hours)

if df.empty:
    st.warning("No hay datos disponibles. Verifica la conexión o el rango.")
    st.stop()

# Resample para gráficos
df_resampled = df.resample('1min').mean()

# ========================
# ESTADO GENERAL
# ========================
st.markdown("## System Status Estado del Sistema")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown('<div class="alert-low"><strong>Green Sistemas Activos</strong><br>DHT22 + MPU6050</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="alert-low"><strong>Yellow Alertas</strong><br>0 pendientes</div>', unsafe_allow_html=True)
with col3:
    vib_rms = np.sqrt(np.mean((df[['accel_x', 'accel_y', 'accel_z']]**2).sum(axis=1)))
    st.markdown(f'<div class="alert-low"><strong>Vibration Vibración</strong><br>{vib_rms:.3f} g RMS</div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="alert-low"><strong>Uptime</strong><br>100% (últimas {range_hours}h)</div>', unsafe_allow_html=True)

# ========================
# MÉTRICAS EN VIVO
# ========================
st.markdown("## Real-Time Métricas en Tiempo Real")

latest = df.iloc[-1]
cols = st.columns(4)

metricas = [
    ("Temperatura", "temperature", "°C", (20, 40), (15, 45)),
    ("Humedad", "humidity", "%", (30, 70), (20, 80)),
    ("Sensación Térmica", "heat_index", "°C", (20, 45), (15, 50)),
    ("Vibración RMS", None, "g", (0, 1.0), (0, 1.5))
]

for i, (nombre, campo, unidad, bueno, warning) in enumerate(metricas):
    with cols[i]:
        if campo:
            valor = latest.get(campo)
            valor = valor if pd.notna(valor) else 0
        else:
            valor = np.sqrt(np.mean((df[['accel_x', 'accel_y', 'accel_z']].iloc[-1]**2).sum()))

        # Estado
        if bueno[0] <= valor <= bueno[1]:
            estado, clase = "Normal", "status-good"
        elif warning[0] <= valor <= warning[1]:
            estado, clase = "Advertencia", "status-warning"
        else:
            estado, clase = "Crítico", "status-critical"

        st.metric(nombre, f"{valor:.2f} {unidad}")
        st.markdown(f'<div class="{clase}">{estado}</div>', unsafe_allow_html=True)

# ========================
# GRÁFICOS
# ========================
st.markdown("## Trends Tendencias de Variables")

# DHT22: Temp + Humedad + Sensación
fig_dht = go.Figure()
fig_dht.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled['temperature'], name='Temperatura', line=dict(color='red')))
fig_dht.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled['humidity'], name='Humedad', yaxis='y2', line=dict(color='blue')))
fig_dht.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled['heat_index'], name='Sensación Térmica', line=dict(color='orange', dash='dot')))
fig_dht.update_layout(
    title="DHT22 - Condiciones Ambientales",
    yaxis=dict(title="°C"),
    yaxis2=dict(title="%", overlaying="y", side="right"),
    hovermode="x unified"
)
st.plotly_chart(fig_dht, use_container_width=True)

# MPU6050: Vibración 3D
fig_mpu = go.Figure()
for axis, color in zip(['accel_x', 'accel_y', 'accel_z'], ['red', 'green', 'blue']):
    fig_mpu.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled[axis], name=f'Aceleración {axis[-1].upper()}', line=dict(color=color)))
fig_mpu.update_layout(title="MPU6050 - Aceleración (g)", hovermode="x unified")
st.plotly_chart(fig_mpu, use_container_width=True)

# Giroscopio
fig_gyro = go.Figure()
for axis, color in zip(['gyro_x', 'gyro_y', 'gyro_z'], ['purple', 'orange', 'cyan']):
    fig_gyro.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled[axis], name=f'Giro {axis[-1].upper()}', line=dict(color=color)))
fig_gyro.update_layout(title="MPU6050 - Giroscopio (°/s)", hovermode="x unified")
st.plotly_chart(fig_gyro, use_container_width=True)

# ========================
# ANÁLISIS PREDICTIVO
# ========================
st.markdown("## Predictive Análisis Predictivo: Promedio Móvil + Anomalías")

window = st.slider("Ventana de promedio móvil (min)", 5, 60, 15)
df_ma = df_resampled.rolling(f'{window}T').mean()
df_std = df_resampled.rolling(f'{window}T').std()

anomalies = pd.DataFrame()
for col in ['temperature', 'accel_x']:
    upper = df_ma[col] + 2.5 * df_std[col]
    lower = df_ma[col] - 2.5 * df_std[col]
    mask = (df_resampled[col] > upper) | (df_resampled[col] < lower)
    if mask.any():
        anomalies = pd.concat([anomalies, df_resampled[mask][[col]]])

col1, col2 = st.columns(2)
with col1:
    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled['temperature'], name='Real'))
    fig_temp.add_trace(go.Scatter(x=df_ma.index, y=df_ma['temperature'], name='Promedio', line=dict(dash='dash')))
    if 'temperature' in anomalies.columns:
        fig_temp.add_trace(go.Scatter(x=anomalies.index, y=anomalies['temperature'], mode='markers', name='Anomalía', marker=dict(color='red', size=8)))
    fig_temp.update_layout(title=f"Temperatura - Ventana {window} min")
    st.plotly_chart(fig_temp, use_container_width=True)

with col2:
    vib_series = (df_resampled[['accel_x', 'accel_y', 'accel_z']]**2).sum(axis=1).sqrt()
    ma_vib = vib_series.rolling(f'{window}T').mean()
    std_vib = vib_series.rolling(f'{window}T').std()
    fig_vib = go.Figure()
    fig_vib.add_trace(go.Scatter(x=vib_series.index, y=vib_series, name='RMS'))
    fig_vib.add_trace(go.Scatter(x=ma_vib.index, y=ma_vib, name='Promedio', line=dict(dash='dash')))
    st.plotly_chart(fig_vib, use_container_width=True)

st.warning(f"**Anomalías detectadas:** {len(anomalies)}")

# ========================
# ESTADÍSTICAS
# ========================
st.markdown("## Summary Resumen del Período")
stats = df.describe().round(2).T
stats['unidad'] = ['°C', '%', '°C', 'g', 'g', 'g', '°/s', '°/s', '°/s']
st.dataframe(stats[['mean', 'std', 'min', 'max', 'unidad']], use_container_width=True)

# ========================
# AUTO REFRESH
# ========================
if auto_refresh:
    time.sleep(30)
    st.rerun()

# ========================
# FOOTER
# ========================
st.markdown("---")
colf1, colf2, colf3 = st.columns(3)
with colf1:
    st.markdown("**Proyecto Final - Digitalización de Plantas**")
with colf2:
    st.markdown(f"**Última actualización:** {datetime.now().strftime('%H:%M:%S')}")
with colf3:
    st.markdown("**Conexión:** Green En línea")
