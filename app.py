import streamlit as st
import pandas as pd
from influxdb_client import InfluxDBClient
import plotly.express as px

# -----------------------------------
# CONFIGURACIÓN GENERAL
# -----------------------------------
st.set_page_config(page_title="Dashboard Planta Productiva", layout="wide")

# Estilos CSS personalizados
st.markdown("""
    <style>
    body {
        background-color: #ffffff;
        color: #000000;
    }
    .title {
        color: #000000;
        text-align: center;
        font-size: 32px;
        font-weight: bold;
        margin-bottom: 15px;
    }
    .card {
        background-color: #ffffff;
        border: 2px solid #007B3E;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 25px;
    }
    h3 {
        color: #007B3E;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------
# CONEXIÓN CON INFLUXDB
# -----------------------------------
try:
    INFLUXDB_URL = st.secrets["INFLUXDB_URL"]
    INFLUXDB_TOKEN = st.secrets["INFLUXDB_TOKEN"]
    INFLUXDB_ORG = st.secrets["INFLUXDB_ORG"]
    INFLUXDB_BUCKET = st.secrets["INFLUXDB_BUCKET"]
except:
    st.error("⚠️ No se encontraron las credenciales. Configúralas en *Secrets* de Streamlit Cloud.")
    st.stop()

client = InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)
query_api = client.query_api()

# -----------------------------------
# TÍTULO
# -----------------------------------
st.markdown('<div class="title">📊 Dashboard — Planta Productiva</div>', unsafe_allow_html=True)
st.markdown("Visualización de datos en tiempo real desde sensores **DHT22** y **MPU6050**.")

# -----------------------------------
# CONTROLES
# -----------------------------------
rango = st.slider("Selecciona rango de tiempo (días):", 1, 30, 3)

# -----------------------------------
# CONSULTAS
# -----------------------------------
def consultar_datos(sensor):
    try:
        if sensor == "DHT22":
            query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
                |> range(start: -{rango}d)
                |> filter(fn: (r) => r._measurement == "studio-dht22")
                |> filter(fn: (r) => r._field == "temperatura" or r._field == "humedad" or r._field == "sensacion_termica")
            '''
        else:
            query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
                |> range(start: -{rango}d)
                |> filter(fn: (r) => r._measurement == "mpu6050")
                |> filter(fn: (r) =>
                    r._field == "accel_x" or r._field == "accel_y" or r._field == "accel_z" or
                    r._field == "gyro_x" or r._field == "gyro_y" or r._field == "gyro_z" or
                    r._field == "temperature")
            '''
        df = query_api.query_data_frame(org=INFLUXDB_ORG, query=query)
        if isinstance(df, list):
            df = pd.concat(df)
        df = df[["_time", "_field", "_value"]]
        df.rename(columns={"_time": "Tiempo", "_field": "Variable", "_value": "Valor"}, inplace=True)
        df["Tiempo"] = pd.to_datetime(df["Tiempo"])
        return df
    except Exception as e:
        st.error(f"Error al consultar {sensor}: {e}")
        return pd.DataFrame()

# -----------------------------------
# CARGA DE DATOS
# -----------------------------------
df_dht = consultar_datos("DHT22")
df_mpu = consultar_datos("MPU6050")

# -----------------------------------
# VISUALIZACIÓN
# -----------------------------------
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="card"><h3>🌡️ Sensor DHT22</h3>', unsafe_allow_html=True)
    if df_dht.empty:
        st.warning("Sin datos de DHT22.")
    else:
        for var in df_dht["Variable"].unique():
            sub_df = df_dht[df_dht["Variable"] == var]
            fig = px.line(sub_df, x="Tiempo", y="Valor", title=var, template="plotly_white")
            fig.update_layout(title_font_color="black", title_font_size=16, paper_bgcolor="white", plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card"><h3>⚙️ Sensor MPU6050</h3>', unsafe_allow_html=True)
    if df_mpu.empty:
        st.warning("Sin datos de MPU6050.")
    else:
        for var in df_mpu["Variable"].unique():
            sub_df = df_mpu[df_mpu["Variable"] == var]
            fig = px.line(sub_df, x="Tiempo", y="Valor", title=var, template="plotly_white")
            fig.update_layout(title_font_color="black", title_font_size=16, paper_bgcolor="white", plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
import streamlit as st
import pandas as pd
from influxdb_client import InfluxDBClient
import plotly.express as px

# -----------------------------------
# CONFIGURACIÓN GENERAL
# -----------------------------------
st.set_page_config(page_title="Dashboard Planta Productiva", layout="wide")

# Estilos CSS personalizados
st.markdown("""
    <style>
    body {
        background-color: #ffffff;
        color: #000000;
    }
    .title {
        color: #000000;
        text-align: center;
        font-size: 32px;
        font-weight: bold;
        margin-bottom: 15px;
    }
    .card {
        background-color: #ffffff;
        border: 2px solid #007B3E;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 25px;
    }
    h3 {
        color: #007B3E;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------
# CONEXIÓN CON INFLUXDB
# -----------------------------------
try:
    INFLUXDB_URL = st.secrets["INFLUXDB_URL"]
    INFLUXDB_TOKEN = st.secrets["INFLUXDB_TOKEN"]
    INFLUXDB_ORG = st.secrets["INFLUXDB_ORG"]
    INFLUXDB_BUCKET = st.secrets["INFLUXDB_BUCKET"]
except:
    st.error("⚠️ No se encontraron las credenciales. Configúralas en *Secrets* de Streamlit Cloud.")
    st.stop()

client = InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)
query_api = client.query_api()

# -----------------------------------
# TÍTULO
# -----------------------------------
st.markdown('<div class="title">📊 Dashboard — Planta Productiva</div>', unsafe_allow_html=True)
st.markdown("Visualización de datos en tiempo real desde sensores **DHT22** y **MPU6050**.")

# -----------------------------------
# CONTROLES
# -----------------------------------
rango = st.slider("Selecciona rango de tiempo (días):", 1, 30, 3)

# -----------------------------------
# CONSULTAS
# -----------------------------------
def consultar_datos(sensor):
    try:
        if sensor == "DHT22":
            query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
                |> range(start: -{rango}d)
                |> filter(fn: (r) => r._measurement == "studio-dht22")
                |> filter(fn: (r) => r._field == "temperatura" or r._field == "humedad" or r._field == "sensacion_termica")
            '''
        else:
            query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
                |> range(start: -{rango}d)
                |> filter(fn: (r) => r._measurement == "mpu6050")
                |> filter(fn: (r) =>
                    r._field == "accel_x" or r._field == "accel_y" or r._field == "accel_z" or
                    r._field == "gyro_x" or r._field == "gyro_y" or r._field == "gyro_z" or
                    r._field == "temperature")
            '''
        df = query_api.query_data_frame(org=INFLUXDB_ORG, query=query)
        if isinstance(df, list):
            df = pd.concat(df)
        df = df[["_time", "_field", "_value"]]
        df.rename(columns={"_time": "Tiempo", "_field": "Variable", "_value": "Valor"}, inplace=True)
        df["Tiempo"] = pd.to_datetime(df["Tiempo"])
        return df
    except Exception as e:
        st.error(f"Error al consultar {sensor}: {e}")
        return pd.DataFrame()

# -----------------------------------
# CARGA DE DATOS
# -----------------------------------
df_dht = consultar_datos("DHT22")
df_mpu = consultar_datos("MPU6050")

# -----------------------------------
# VISUALIZACIÓN
# -----------------------------------
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="card"><h3>🌡️ Sensor DHT22</h3>', unsafe_allow_html=True)
    if df_dht.empty:
        st.warning("Sin datos de DHT22.")
    else:
        for var in df_dht["Variable"].unique():
            sub_df = df_dht[df_dht["Variable"] == var]
            fig = px.line(sub_df, x="Tiempo", y="Valor", title=var, template="plotly_white")
            fig.update_layout(title_font_color="black", title_font_size=16, paper_bgcolor="white", plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card"><h3>⚙️ Sensor MPU6050</h3>', unsafe_allow_html=True)
    if df_mpu.empty:
        st.warning("Sin datos de MPU6050.")
    else:
        for var in df_mpu["Variable"].unique():
            sub_df = df_mpu[df_mpu["Variable"] == var]
            fig = px.line(sub_df, x="Tiempo", y="Valor", title=var, template="plotly_white")
            fig.update_layout(title_font_color="black", title_font_size=16, paper_bgcolor="white", plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
