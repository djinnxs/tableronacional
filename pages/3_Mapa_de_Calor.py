import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from utils import get_epi_week_data

st.set_page_config(page_title="Mapa de Calor", layout="wide")

# --- SE ACTUAL ---
sem_hoy, anio_hoy = get_epi_week_data(datetime.date.today())
st.markdown(f"<h3 style='text-align: center;'>Hoy es Semana Epidemiológica: <span style='color: #e11d48; font-weight:bold;'>{sem_hoy}</span> del {anio_hoy}</h3>", unsafe_allow_html=True)

st.title("🔥 Mapa de Calor Epidemiológico")

@st.cache_data
def get_data():
    df_base = pd.read_parquet('data/base_nacional.parquet')
    df_pop = pd.read_parquet('data/poblacionxprovinciaindec.parquet')
    
    # Procesar población
    df_pop = df_pop[df_pop['sexo_nombre'] == 'Ambos sexos']
    df_pop = df_pop.groupby(['juri', 'ano'])['poblacion'].sum().reset_index()
    df_pop['juri'] = df_pop['juri'].astype(str).str.zfill(2)
    df_pop = df_pop.rename(columns={'juri': 'id_provincia', 'ano': 'ANIO', 'poblacion': 'Poblacion'})
    
    return df_base, df_pop

df_base, df_pop = get_data()

# Filtros
anios = sorted(df_base['ANIO'].unique(), reverse=True)
selected_anio = st.sidebar.selectbox("Seleccionar Año", anios)

eventos = sorted(df_base['Evento'].unique())
selected_evento = st.sidebar.selectbox("Seleccionar Evento", eventos)

# Procesamiento
df_heat = df_base[(df_base['ANIO'] == selected_anio) & (df_base['Evento'] == selected_evento)]
df_heat = df_heat.groupby(['Provincia', 'id_provincia', 'ANIO', 'SEMANA'])['CANTIDAD'].sum().reset_index()

# Unir con población y calcular tasa
df_heat = pd.merge(df_heat, df_pop, on=['id_provincia', 'ANIO'], how='left')
df_heat['Tasa'] = (df_heat['CANTIDAD'] / df_heat['Poblacion'] * 100000).fillna(0)

# Pivotar para el heatmap
df_pivot = df_heat.pivot(index='Provincia', columns='SEMANA', values='Tasa').fillna(0)

# Gráfico
fig = px.imshow(df_pivot, 
                labels=dict(x="Semana Epidemiológica", y="Jurisdicción", color="Tasa"),
                x=df_pivot.columns,
                y=df_pivot.index,
                color_continuous_scale='Reds',
                title=f"Tasa de {selected_evento} cada 100k hab. por Provincia y Semana ({selected_anio})")

fig.update_layout(height=700)
st.plotly_chart(fig, width='stretch')

st.info("El mapa de calor permite visualizar rápidamente la propagación geográfica y temporal de un evento.")
