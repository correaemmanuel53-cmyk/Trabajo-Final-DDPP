import streamlit as st
import pandas as pd
import numpy as np
from influxdb_client import InfluxDBClient
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
import os
from dotenv import load_dotenv

# ========================
# CARGAR VARIABLES DE ENTORNO
# ========================
load_dotenv()

INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

# Validación básica
if not all([INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
    st.error("Faltan variables de entorno. Verifica tu archivo `.env`.")
    st.stop()

# ========================
# CONFIGURACIÓN DE STREAMLIT
# ========================
st.set_page_config(page_title="Extreme Manufacturing", layout="wide")
st.title("Extreme Manufacturing - Monitoreo de Celda de Secado")
st.markdown("**Digitalización de Planta Productiva** | Sensores: DHT22 + MPU6050")

# ========================
# CLIENTE INFLUXDB
# ========================
@st.cache_resource
def get_influx_client():
    return InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

client = get_influx_client()
query_api = client.query_api()

# ========================
# FUNCIÓN PARA OBTENER DATOS
# ========================
@st.cache_data(ttl=60)  # Cache por 60 segundos
def get_data(range_hours=24):
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -{range_hours}h)
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> keep(columns: ["_time", "temperature", "humidity", "vibration"])
    '''
    try:
        tables = query_api.query(org=INFLUXDB_ORG, query=query)
        if not tables or len(tables) == 0 or len(tables[0].records) == 0:
            st.warning("No hay datos disponibles en el rango seleccionado.")
            return pd.DataFrame()

        df = tables[0].to_pandas()
        df['_time'] = pd.to_datetime(df['_time'])
        df = df.set_index('_time').sort_index()
        return df
    except Exception as e:
        st.error(f"Error de conexión con InfluxDB: {str(e)}")
        return pd.DataFrame()

# ========================
# SIDEBAR - CONTROLES
# ========================
with st.sidebar:
    st.header("Controles")
    range_hours = st.slider("Rango de tiempo (horas)", 1, 168, 24, help="Datos históricos en horas")
    if st.button("Actualizar datos"):
        st.cache_data.clear()
        st.success("Datos actualizados")

    st.markdown("---")
    st.markdown("### Variables Monitorizadas")
    st.markdown("- **Temperatura (°C)**: DHT22")
    st.markdown("- **Humedad (%)**: DHT22")
    st.markdown("- **Vibración (g)**: MPU6050 (RMS)")

# ========================
# CARGAR DATOS
# ========================
with st.spinner("Consultando InfluxDB..."):
    df = get_data(range_hours)

if df.empty:
    st.info("No hay datos para mostrar. Intenta con otro rango.")
    st.stop()

# ========================
# MÉTRICAS EN VIVO
# ========================
latest = df.iloc[-1]
prev_temp = df['temperature'].iloc[-2] if len(df) > 1 else latest['temperature']
prev_hum = df['humidity'].iloc[-2] if len(df) > 1 else latest['humidity']

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        "Temperatura",
        f"{latest['temperature']:.2f} °C",
        delta=f"{latest['temperature'] - prev_temp:+.2f} °C"
    )
with col2:
    st.metric(
        "Humedad",
        f"{latest['humidity']:.1f} %",
        delta=f"{latest['humidity'] - prev_hum:+.1f} %"
    )

# ========================
# GRÁFICAS
# ========================
st.markdown("## Evolución Temporal")

df_resampled = df.resample('1min').mean()

# Temperatura + Humedad
fig_dual = go.Figure()
fig_dual.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled['temperature'],
                              name="Temperatura", line=dict(color="red")))
fig_dual.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled['humidity'],
                              name="Humedad", yaxis="y2", line=dict(color="blue")))
fig_dual.update_layout(
    title="Temperatura y Humedad",
    xaxis_title="Tiempo",
    yaxis=dict(title="°C", side="left"),
    yaxis2=dict(title="%", side="right", overlaying="y"),
    legend=dict(x=0, y=1.1),
    hovermode="x unified"
)
st.plotly_chart(fig_dual, use_container_width=True)

# Vibración
fig_vib = px.line(df_resampled, y='vibration', title="Vibración del Motor",
                  labels={"vibration": "Aceleración (g)"})
fig_vib.update_traces(line_color="purple")
st.plotly_chart(fig_vib, use_container_width=True)

# ========================
# ANÁLISIS PREDICTIVO
# ========================
st.markdown("## Análisis Predictivo: Promedio Móvil + Anomalías")

if len(df_resampled) > 20:
    window_min = st.slider("Ventana de promedio móvil (min)", 5, 60, 15, step=5)
    window = f"{window_min}T"

    df_ma = df_resampled.rolling(window=window).mean()
    df_std = df_resampled.rolling(window=window).std()

    # Anomalías: fuera de ±2.5σ
    anomalies_temp = df_resampled[
        (df_resampled['temperature'] > df_ma['temperature'] + 2.5 * df_std['temperature']) |
        (df_resampled['temperature'] < df_ma['temperature'] - 2.5 * df_std['temperature'])
    ]
    anomalies_vib = df_resampled[
        (df_resampled['vibration'] > df_ma['vibration'] + 2.5 * df_std['vibration'])
    ]

    col1, col2 = st.columns(2)
    with col1:
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled['temperature'], name="Real"))
        fig_temp.add_trace(go.Scatter(x=df_ma.index, y=df_ma['temperature'], name="Promedio Móvil", line=dict(dash='dash')))
        if not anomalies_temp.empty:
            fig_temp.add_trace(go.Scatter(x=anomalies_temp.index, y=anomalies_temp['temperature'],
                                          mode='markers', name='Anomalía', marker=dict(color='red', size=8)))
        fig_temp.update_layout(title=f"Temperatura - Ventana {window_min} min")
        st.plotly_chart(fig_temp, use_container_width=True)

    with col2:
        fig_vib_pred = go.Figure()
        fig_vib_pred.add_trace(go.Scatter(x=df_resampled.index, y=df_resampled['vibration'], name="Real"))
        fig_vib_pred.add_trace(go.Scatter(x=df_ma.index, y=df_ma['vibration'], name="Promedio Móvil", line=dict(dash='dash')))
        if not anomalies_vib.empty:
            fig_vib_pred.add_trace(go.Scatter(x=anomalies_vib.index, y=anomalies_vib['vibration'],
                                              mode='markers', name='Anomalía', marker=dict(color='red', size=8)))
        fig_vib_pred.update_layout(title=f"Vibración - Ventana {window_min} min")
        st.plotly_chart(fig_vib_pred, use_container_width=True)

    total_anomalies = len(anomalies_temp) + len(anomalies_vib)
    st.warning(f"**Detectadas {total_anomalies} anomalías** en el período seleccionado.")

else:
    st.info("Datos insuficientes para análisis predictivo.")

# ========================
# ESTADÍSTICAS
# ========================
st.markdown("## Resumen Estadístico")
stats = df[['temperature', 'humidity', 'vibration']].describe().round(2)
st.dataframe(stats.T, use_container_width=True)

# ========================
# FOOTER
# ========================
st.markdown("---")
st.caption("Proyecto Final | Digitalización de Plantas Productivas — Universidad EAFIT")
