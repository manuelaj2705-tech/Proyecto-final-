"""
Proyecto IoT – Dashboard Streamlit
Ubicación: Ciudad del Río, Medellín, Colombia
Sensor: ESP32 + DHT22 → InfluxDB → Streamlit
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from influxdb_client import InfluxDBClient
from scipy import stats
from datetime import datetime, timedelta

st.set_page_config(
    page_title="IOT Proyecto Final – Ciudad del Río",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background: #1B2138; }
    [data-testid="stSidebar"] * { color: #E8EAF0 !important; }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        text-align: center;
    }
    .metric-label { font-size: 13px; color: #6B7280; font-weight: 500; margin-bottom: 4px; }
    .metric-value { font-size: 32px; font-weight: 700; }
    .metric-delta { font-size: 12px; color: #9CA3AF; margin-top: 4px; }
    .alert-box {
        background: #FEF3C7; border: 1px solid #F59E0B;
        border-radius: 8px; padding: 0.8rem 1rem; margin: 0.5rem 0;
        font-size: 14px; color: #92400E;
    }
    .good-box {
        background: #D1FAE5; border: 1px solid #10B981;
        border-radius: 8px; padding: 0.8rem 1rem; margin: 0.5rem 0;
        font-size: 14px; color: #065F46;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🌡️ Monitor IOT")
    st.markdown("**Ciudad del Río, Medellín**  \nLat: 6.2208 | Lon: -75.5735")
    st.divider()
    fuente = st.radio("Fuente de datos", ["☁️ InfluxDB Cloud", "📊 Datos de ejemplo"])
    rango_dias = st.slider("Rango (días)", 1, 30, 7)
    st.divider()
    st.markdown("**Umbrales de alerta**")
    temp_max = st.number_input("Temp. máxima (°C)", value=30.0, step=0.5)
    hum_min  = st.number_input("Humedad mínima (%)", value=50.0, step=1.0)
    hum_max  = st.number_input("Humedad máxima (%)", value=90.0, step=1.0)

@st.cache_data(ttl=60)
def cargar_influxdb(dias):
    try:
        client = InfluxDBClient(
            url="https://us-east-1-1.aws.cloud2.influxdata.com",
            token="FDW06wY2lrd3AgCJk5tMv8dXu_avdbB887ELIQW1vLvttcsm-Mc5WfEkXPk75ThTRNHopkXdyoAWsGOgbiSrAA==",
            org="32d3e70a444551c9"
        )
        qa = client.query_api()
        query = f'''
        from(bucket: "final")
          |> range(start: -{dias}d)
          |> filter(fn: (r) => r._measurement == "ambiente")
          |> filter(fn: (r) => r._field == "temperature" or r._field == "humidity")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        df = qa.query_data_frame(query)
        if df.empty:
            return None, "Sin datos"
        df = df[['_time', 'temperature', 'humidity']].rename(columns={'_time': 'tiempo'})
        df['tiempo'] = pd.to_datetime(df['tiempo']).dt.tz_localize(None)
        df['hora']    = df['tiempo'].dt.hour
        df['fecha']   = df['tiempo'].dt.date
        return df, None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=60)
def generar_datos_ejemplo(dias):
    n = dias * 144
    idx = pd.date_range(end=datetime.now(), periods=n, freq='10min')
    t = np.linspace(0, dias * 2 * np.pi, n)
    np.random.seed(42)
    temp = 25 + 4 * np.sin(t) + np.random.normal(0, 0.4, n)
    hum  = 72 - 8 * np.sin(t) + np.random.normal(0, 0.8, n)
    df = pd.DataFrame({
        'tiempo': idx,
        'temperature': np.round(temp, 2),
        'humidity':    np.round(np.clip(hum, 30, 100), 2),
    })
    df['hora']  = df['tiempo'].dt.hour
    df['fecha'] = df['tiempo'].dt.date
    return df

if fuente == "☁️ InfluxDB Cloud":
    with st.spinner("Conectando a InfluxDB..."):
        df, err = cargar_influxdb(rango_dias)
    if err or df is None:
        st.warning(f"Sin datos en InfluxDB ({err}). Mostrando datos de ejemplo.")
        df = generar_datos_ejemplo(rango_dias)
else:
    df = generar_datos_ejemplo(rango_dias)

st.markdown("# 🌡️ Proyecto Final — Ciudad del Río, Medellín")
st.markdown("**Sensor:** ESP32 + DHT22 &nbsp;|&nbsp; **Base de datos:** InfluxDB &nbsp;|&nbsp; **Ubicación:** 6.2208°N, -75.5735°O")
st.divider()

ultimo   = df.iloc[-1]
anterior = df.iloc[-2]

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">🌡️ Temperatura actual</div>
        <div class="metric-value" style="color:#E8593C;">{ultimo['temperature']:.1f}°C</div>
        <div class="metric-delta">{abs(ultimo['temperature'] - anterior['temperature']):.2f}°C vs anterior</div>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">💧 Humedad actual</div>
        <div class="metric-value" style="color:#3B8BD4;">{ultimo['humidity']:.1f}%</div>
        <div class="metric-delta">{abs(ultimo['humidity'] - anterior['humidity']):.2f}% vs anterior</div>
    </div>""", unsafe_allow_html=True)
with col3:
    hi = ultimo['temperature'] + 0.05 * (ultimo['humidity'] - 40) * (ultimo['temperature'] - 14.5) / 100
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">🔥 Sensación térmica</div>
        <div class="metric-value" style="color:#F59E0B;">{hi:.1f}°C</div>
        <div class="metric-delta">Heat index calculado</div>
    </div>""", unsafe_allow_html=True)
with col4:
    n_anom = int((np.abs(stats.zscore(df['temperature'].dropna())) > 2.5).sum()) if len(df) > 3 else 0
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">⚠️ Anomalías detectadas</div>
        <div class="metric-value" style="color:{'#EF4444' if n_anom > 0 else '#10B981'};">{n_anom}</div>
        <div class="metric-delta">últimos {rango_dias} días</div>
    </div>""", unsafe_allow_html=True)

st.markdown("### Estado del sistema")
acol1, acol2 = st.columns(2)
with acol1:
    if ultimo['temperature'] > temp_max:
        st.markdown(f'<div class="alert-box">⚠️ Temperatura ({ultimo["temperature"]:.1f}°C) supera el umbral de {temp_max}°C</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="good-box">✅ Temperatura normal ({ultimo["temperature"]:.1f}°C)</div>', unsafe_allow_html=True)
with acol2:
    if not (hum_min <= ultimo['humidity'] <= hum_max):
        st.markdown(f'<div class="alert-box">⚠️ Humedad ({ultimo["humidity"]:.1f}%) fuera del rango [{hum_min:.0f}%–{hum_max:.0f}%]</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="good-box">✅ Humedad en rango ({ultimo["humidity"]:.1f}%)</div>', unsafe_allow_html=True)

st.markdown("### Serie de tiempo")
df_melt = df.melt(id_vars='tiempo', value_vars=['temperature', 'humidity'], var_name='variable', value_name='valor')
df_melt['variable'] = df_melt['variable'].map({'temperature': 'Temperatura (°C)', 'humidity': 'Humedad (%)'})
fig1 = px.line(df_melt, x='tiempo', y='valor', color='variable',
               color_discrete_map={'Temperatura (°C)': '#E8593C', 'Humedad (%)': '#3B8BD4'},
               template='plotly_white', height=380)
fig1.update_layout(legend=dict(orientation='h', y=1.02, x=1, xanchor='right'), xaxis_title='', yaxis_title='Valor', margin=dict(t=10,b=10,l=10,r=10))
st.plotly_chart(fig1, use_container_width=True)

st.markdown("### Patrón horario promedio")
hourly = df.groupby('hora').agg(temp_mean=('temperature','mean'), hum_mean=('humidity','mean')).reset_index()
fig2 = make_subplots(rows=1, cols=2, subplot_titles=('Temperatura por hora', 'Humedad por hora'))
fig2.add_trace(go.Scatter(x=hourly['hora'], y=hourly['temp_mean'], mode='lines+markers', name='Temperatura', line=dict(color='#E8593C', width=2)), row=1, col=1)
fig2.add_trace(go.Scatter(x=hourly['hora'], y=hourly['hum_mean'], mode='lines+markers', name='Humedad', line=dict(color='#3B8BD4', width=2)), row=1, col=2)
fig2.update_layout(template='plotly_white', height=350, margin=dict(t=30,b=10,l=10,r=10), showlegend=False)
st.plotly_chart(fig2, use_container_width=True)

st.markdown("### Correlación temperatura vs humedad")
fig3 = px.scatter(df.sample(min(500, len(df))), x='temperature', y='humidity',
                  labels={'temperature':'Temperatura (°C)', 'humidity':'Humedad (%)'},
                  template='plotly_white', height=350, opacity=0.5, color_discrete_sequence=['#7F77DD'])
fig3.update_layout(margin=dict(t=10,b=10,l=10,r=10))
st.plotly_chart(fig3, use_container_width=True)

st.markdown("### 📍 Ubicación del sensor")
map_df = pd.DataFrame({'lat': [6.2208], 'lon': [-75.5735], 'lugar': ['Ciudad del Río, Medellín']})
fig_map = px.scatter_mapbox(map_df, lat='lat', lon='lon', hover_name='lugar', zoom=14, height=350,
                            mapbox_style='open-street-map', color_discrete_sequence=['#E8593C'])
fig_map.update_traces(marker_size=16)
fig_map.update_layout(margin=dict(t=0,b=0,l=0,r=0))
st.plotly_chart(fig_map, use_container_width=True)

st.markdown("### Datos recientes")
st.dataframe(df[['tiempo','temperature','humidity']].tail(20)
             .rename(columns={'tiempo':'Tiempo','temperature':'Temp (°C)','humidity':'Humedad (%)'}),
             use_container_width=True, height=300)

csv = df[['tiempo','temperature','humidity']].to_csv(index=False)
st.download_button("⬇️ Descargar CSV", csv, "datos_ciudad_del_rio.csv", "text/csv")
st.divider()
st.caption("🌍 Proyecto IoT – Ciudad del Río, Medellín | ESP32 + DHT22 → InfluxDB → Grafana → Streamlit")
