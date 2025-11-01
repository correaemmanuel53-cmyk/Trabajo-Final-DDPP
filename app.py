import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv
import os

# =========================
# CONFIGURACIÓN GENERAL
# =========================
st.set_page_config(page_title="Dashboard Sensorial InfluxDB", layout="wide")
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
def get_measurements():
    """Obtiene lista de measurements disponibles."""
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()
        query = f'''
        import "influxdata/influxdb/schema"
        schema.measurements(bucket: "{INFLUXDB_BUCKET}")
        '''
        result = query_api.query_data_frame(org=INFLUXDB_ORG, query=query)
        if isinstance(result, list):
            result = pd.concat(result, ignore_index=True)
        return result["_value"].tolist()
    except Exception as e:
        st.error(f"Error consultando measurements: {e}")
        return []

@st.cache_data(ttl=300)
def get_fields(measurement):
    """Obtiene lista de fields disponibles para un measurement."""
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()
        query = f'''
        import "influxdata/influxdb/schema"
        schema.measurementFieldKeys(bucket: "{INFLUXDB_BUCKET}", measurement: "{measurement}")
        '''
        result = query_api.query_data_frame(org=INFLUXDB_ORG, query=query)
        if isinstance(result, list):
            result = pd.concat(result, ignore_index=True)
        return result["_value"].tolist()
    except Exception as e:
        st.error(f"Error consultando fields: {e}")
        return []

@st.cache_data(ttl=300)
def get_data(measurement, fields, days):
    """Obtiene datos de los últimos N días desde InfluxDB."""
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()

        start_time = datetime.utcnow() - timedelta(days=days)
        fields_filter = " or ".join([f'r["_field"] == "{f}"' for f in fields])

        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {start_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "{measurement}")
          |> filter(fn: (r) => {fields_filter})
        '''

        result = query_api.query_data_frame(org=INFLUXDB_ORG, query=query)
        if isinstance(result, list):
            df = pd.concat(result, ignore_index=True)
        else:
            df = result

        if df is None or df.empty:
            return pd.DataFrame()

        df["_time"] = pd.to_datetime(df["_time"])
        return df

    except Exception as e:
        st.error(f"Error conectando con InfluxDB: {e}")
        return pd.DataFrame()

# =========================
# ESTILO VISUAL
# =========================
st.markdown("""
<style>
    body, .stApp { background-color: #ffffff; color: #000000; }
    h1, h2, h3, .stMarkdown, .stSubheader { color: #000000 !important; }
    .stMetric { background-color: #f8fff8; border: 1px solid #00aa55; border-radius: 10px; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR DE CONFIGURACIÓN
# =========================
st.sidebar.header("⚙️ Configuración")

measurements = get_measurements()
if not measurements:
    st.error("No se encontraron measurements disponibles. Verifica el bucket.")
    st.stop()

measurement_sel = st.sidebar.selectbox("📈 Measurement:", measurements)

fields = get_fields(measurement_sel)
if not fields:
    st.error("No se encontraron fields para este measurement.")
    st.stop()

fields_sel = st.sidebar.multiselect("Variables a graficar:", fields, default=fields[:3])
rango_dias = st.sidebar.slider("Rango de tiempo (días):", 1, 90, 7)

# =========================
# OBTENER DATOS
# =========================
df = get_data(measurement_sel, fields_sel, rango_dias)

if df.empty:
    st.warning("⚠️ No se encontraron datos en el rango seleccionado.")
    st.stop()

# =========================
# TARJETAS DE ÚLTIMOS VALORES
# =========================
st.subheader("📊 Últimos Valores Registrados")

df_latest = df.sort_values("_time").groupby("_field").tail(1)

cols = st.columns(len(fields_sel))
for i, field in enumerate(fields_sel):
    if field in df_latest["_field"].values:
        val = df_latest[df_latest["_field"] == field]["_value"].values[0]
        cambio = 0
        df_field = df[df["_field"] == field].sort_values("_time")
        if len(df_field) > 1:
            cambio = df_field["_value"].iloc[-1] - df_field["_value"].iloc[-2]
        cols[i].metric(field.capitalize(), f"{val:.2f}", f"{cambio:+.2f}")

st.markdown("---")

# =========================
# GRÁFICOS Y TABLA
# =========================
st.subheader("📈 Evolución temporal")

tabs = st.tabs(fields_sel + ["Tabla de datos"])

for i, field in enumerate(fields_sel):
    with tabs[i]:
        st.line_chart(
            df[df["_field"] == field].set_index("_time")["_value"],
            key=f"chart_{field}"
        )

with tabs[-1]:
    st.dataframe(df[["_time", "_field", "_value"]], use_container_width=True, key="tabla_final")

st.success("✅ Dashboard actualizado correctamente")
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv
import os

# =========================
# CONFIGURACIÓN GENERAL
# =========================
st.set_page_config(page_title="Dashboard Sensorial InfluxDB", layout="wide")
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
def get_measurements():
    """Obtiene lista de measurements disponibles."""
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()
        query = f'''
        import "influxdata/influxdb/schema"
        schema.measurements(bucket: "{INFLUXDB_BUCKET}")
        '''
        result = query_api.query_data_frame(org=INFLUXDB_ORG, query=query)
        if isinstance(result, list):
            result = pd.concat(result, ignore_index=True)
        return result["_value"].tolist()
    except Exception as e:
        st.error(f"Error consultando measurements: {e}")
        return []

@st.cache_data(ttl=300)
def get_fields(measurement):
    """Obtiene lista de fields disponibles para un measurement."""
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()
        query = f'''
        import "influxdata/influxdb/schema"
        schema.measurementFieldKeys(bucket: "{INFLUXDB_BUCKET}", measurement: "{measurement}")
        '''
        result = query_api.query_data_frame(org=INFLUXDB_ORG, query=query)
        if isinstance(result, list):
            result = pd.concat(result, ignore_index=True)
        return result["_value"].tolist()
    except Exception as e:
        st.error(f"Error consultando fields: {e}")
        return []

@st.cache_data(ttl=300)
def get_data(measurement, fields, days):
    """Obtiene datos de los últimos N días desde InfluxDB."""
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()

        start_time = datetime.utcnow() - timedelta(days=days)
        fields_filter = " or ".join([f'r["_field"] == "{f}"' for f in fields])

        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {start_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "{measurement}")
          |> filter(fn: (r) => {fields_filter})
        '''

        result = query_api.query_data_frame(org=INFLUXDB_ORG, query=query)
        if isinstance(result, list):
            df = pd.concat(result, ignore_index=True)
        else:
            df = result

        if df is None or df.empty:
            return pd.DataFrame()

        df["_time"] = pd.to_datetime(df["_time"])
        return df

    except Exception as e:
        st.error(f"Error conectando con InfluxDB: {e}")
        return pd.DataFrame()

# =========================
# ESTILO VISUAL
# =========================
st.markdown("""
<style>
    body, .stApp { background-color: #ffffff; color: #000000; }
    h1, h2, h3, .stMarkdown, .stSubheader { color: #000000 !important; }
    .stMetric { background-color: #f8fff8; border: 1px solid #00aa55; border-radius: 10px; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR DE CONFIGURACIÓN
# =========================
st.sidebar.header("⚙️ Configuración")

measurements = get_measurements()
if not measurements:
    st.error("No se encontraron measurements disponibles. Verifica el bucket.")
    st.stop()

measurement_sel = st.sidebar.selectbox("📈 Measurement:", measurements)

fields = get_fields(measurement_sel)
if not fields:
    st.error("No se encontraron fields para este measurement.")
    st.stop()

fields_sel = st.sidebar.multiselect("Variables a graficar:", fields, default=fields[:3])
rango_dias = st.sidebar.slider("Rango de tiempo (días):", 1, 90, 7)

# =========================
# OBTENER DATOS
# =========================
df = get_data(measurement_sel, fields_sel, rango_dias)

if df.empty:
    st.warning("⚠️ No se encontraron datos en el rango seleccionado.")
    st.stop()

# =========================
# TARJETAS DE ÚLTIMOS VALORES
# =========================
st.subheader("📊 Últimos Valores Registrados")

df_latest = df.sort_values("_time").groupby("_field").tail(1)

cols = st.columns(len(fields_sel))
for i, field in enumerate(fields_sel):
    if field in df_latest["_field"].values:
        val = df_latest[df_latest["_field"] == field]["_value"].values[0]
        cambio = 0
        df_field = df[df["_field"] == field].sort_values("_time")
        if len(df_field) > 1:
            cambio = df_field["_value"].iloc[-1] - df_field["_value"].iloc[-2]
        cols[i].metric(field.capitalize(), f"{val:.2f}", f"{cambio:+.2f}")

st.markdown("---")

# =========================
# GRÁFICOS Y TABLA
# =========================
st.subheader("📈 Evolución temporal")

tabs = st.tabs(fields_sel + ["Tabla de datos"])

for i, field in enumerate(fields_sel):
    with tabs[i]:
        st.line_chart(
            df[df["_field"] == field].set_index("_time")["_value"],
            key=f"chart_{field}"
        )

with tabs[-1]:
    st.dataframe(df[["_time", "_field", "_value"]], use_container_width=True, key="tabla_final")

st.success("✅ Dashboard actualizado correctamente")
