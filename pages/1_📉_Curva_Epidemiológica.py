import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from utils import get_epi_week_data

st.set_page_config(page_title="Curva Epidemiológica", layout="wide")

# --- SE ACTUAL ---
sem_hoy, anio_hoy = get_epi_week_data(datetime.date.today())
st.markdown(f"<h3 style='text-align: center;'>Hoy es Semana Epidemiológica: <span style='color: #e11d48; font-weight:bold;'>{sem_hoy}</span> del {anio_hoy}</h3>", unsafe_allow_html=True)

st.title("📈 Curva Epidemiológica")

@st.cache_data
def get_time_series_data():
    df = pd.read_parquet('data/base_nacional.parquet')
    return df

df = get_time_series_data()

# Filtros
anios = sorted(df['ANIO'].unique(), reverse=True)
selected_anio = st.sidebar.selectbox("Seleccionar Año", anios)

eventos = sorted(df['Evento'].unique())
selected_evento = st.sidebar.selectbox("Seleccionar Evento", ["Todos"] + eventos)

# Filtrado
mask = (df['ANIO'] == selected_anio)
if selected_evento != "Todos":
    mask &= (df['Evento'] == selected_evento)

df_filtered = df[mask].groupby('SEMANA')['CANTIDAD'].sum().reset_index()

# Asegurar que todas las semanas (1-52/53) estén presentes
all_weeks = pd.DataFrame({'SEMANA': range(1, 54)})
df_plot = pd.merge(all_weeks, df_filtered, on='SEMANA', how='left').fillna(0)

# Limitar semanas para el año actual (SE-2)
if selected_anio == anio_hoy:
    max_sem = sem_hoy - 2
    df_plot = df_plot[df_plot['SEMANA'] <= max_sem]

# Gráfico
fig = px.line(df_plot, x='SEMANA', y='CANTIDAD', 
             title=f"Casos por Semana - {selected_evento} ({selected_anio})",
             labels={'CANTIDAD': 'Número de Casos', 'SEMANA': 'Semana Epidemiológica'},
             markers=True)

fig.update_layout(xaxis=dict(tickmode='linear', tick0=1, dtick=5))
st.plotly_chart(fig, width='stretch')

st.info("Este gráfico muestra la evolución temporal de los casos reportados por semana para el año seleccionado, semana actual -2.")
