import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from utils import get_epi_week_data

st.set_page_config(page_title="Comparativa Anual", layout="wide")

# --- SE ACTUAL ---
sem_hoy, anio_hoy = get_epi_week_data(datetime.date.today())
st.markdown(f"<h3 style='text-align: center;'>Hoy es Semana Epidemiológica: <span style='color: #e11d48; font-weight:bold;'>{sem_hoy}</span> del {anio_hoy}</h3>", unsafe_allow_html=True)

st.title("📊 Comparativa Interanual")

@st.cache_data
def get_data():
    df = pd.read_parquet('data/base_nacional.parquet')
    return df

df = get_data()

# Filtros
anios = sorted(df['ANIO'].unique(), reverse=True)
selected_anios = st.sidebar.multiselect("Seleccionar Años", anios, default=anios)

eventos = sorted(df['Evento'].unique())
selected_evento = st.sidebar.selectbox("Seleccionar Evento", eventos)

tipo_grafico = st.sidebar.selectbox("Tipo de Gráfico", ["Líneas", "Apilado", "Área"], index=0)
modo_visualizacion = st.sidebar.selectbox("Modo de Visualización", ["Comparativa (Superpuesta)", "Serie Temporal (Continua)"], index=0)

# Procesamiento
mask = (df['Evento'] == selected_evento) & (df['ANIO'].isin(selected_anios))
df_comp = df[mask].groupby(['ANIO', 'SEMANA'])['CANTIDAD'].sum().reset_index()
df_comp = df_comp.sort_values(['ANIO', 'SEMANA'])
df_comp['ANIO'] = df_comp['ANIO'].astype(str)
df_comp['Semana_Continua'] = df_comp['ANIO'] + "-S" + df_comp['SEMANA'].astype(str).str.zfill(2)

if modo_visualizacion == "Serie Temporal (Continua)":
    x_col = 'Semana_Continua'
    color_col = None
    title_text = f"Serie Temporal de {selected_evento}"
    labels_dict = {'CANTIDAD': 'Casos', 'Semana_Continua': 'Semana Epi Continua'}
else:
    x_col = 'SEMANA'
    color_col = 'ANIO'
    title_text = f"Comparativa de {selected_evento} por Año"
    labels_dict = {'CANTIDAD': 'Casos', 'SEMANA': 'Semana Epi', 'ANIO': 'Año'}

# Gráfico
if tipo_grafico == "Apilado":
    fig = px.bar(df_comp, x=x_col, y='CANTIDAD', color=color_col,
                 title=title_text,
                 labels=labels_dict,
                 barmode='stack' if color_col else 'relative')
elif tipo_grafico == "Área":
    fig = px.area(df_comp, x=x_col, y='CANTIDAD', color=color_col,
                  title=title_text,
                  labels=labels_dict)
else:
    fig = px.line(df_comp, x=x_col, y='CANTIDAD', color=color_col,
                 title=title_text,
                 labels=labels_dict)

if modo_visualizacion == "Comparativa (Superpuesta)":
    fig.update_layout(xaxis=dict(tickmode='linear', tick0=1, dtick=5))
    
st.plotly_chart(fig, width='stretch')

st.info("Utilice este gráfico para comparar la magnitud de los casos actuales contra años históricos para el mismo evento, o visualizar su evolución en una serie temporal continua.")
