Extreme Manufacturing – Celda de Secado
---------------------------------------

Proyecto Final – Digitalización de Plantas Industriales

Esta aplicación permite monitorear en tiempo real las condiciones ambientales y mecánicas dentro de una celda de secado industrial. Utiliza Streamlit para la visualización interactiva de datos provenientes de sensores DHT22 y MPU6050 almacenados en InfluxDB.

Características principales:
- Conexión segura a InfluxDB mediante variables de entorno (.env).
- Dashboard con métricas en tiempo real.
- Indicadores visuales de estado (Normal, Advertencia, Crítico).
- Gráficos interactivos con Plotly (temperatura, humedad, aceleración, giroscopio).
- Cálculo de vibración RMS.
- Análisis predictivo mediante ventanas móviles.
- Detección automática de anomalías.
- Resumen estadístico detallado.
- Auto-refresh configurable cada 30 segundos.

Requisitos:
- streamlit
- pandas
- numpy
- influxdb-client
- plotly
- python-dotenv

Archivo .env requerido:
INFLUXDB_URL=...
INFLUXDB_TOKEN=...
INFLUXDB_ORG=...
INFLUXDB_BUCKET=...

Cómo ejecutar:
1. Instalar dependencias.
2. Ejecutar:
   streamlit run app.py
3. Abrir en navegador:
   http://localhost:8501

Estructura recomendada del proyecto:
- app.py
- .env
- requirements.txt
- README.txt
- assets/

Descripción técnica:
La app consulta las mediciones de InfluxDB, procesa los datos con Pandas, y genera gráficos dinámicos con Plotly. La caché de Streamlit optimiza rendimiento usando `@st.cache_data` y `@st.cache_resource`.

Sensor DHT22:
- Temperatura
- Humedad
- Sensación térmica

Sensor MPU6050:
- Aceleración XYZ
- Giroscopio XYZ
- Vibración RMS (calculada)

Análisis predictivo:
- Promedio móvil configurable (5–60 min)
- Detección de anomalías por variaciones superiores a 2.5 desviaciones estándar

Fin del documento.
