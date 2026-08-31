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

st.markdown("---")
st.subheader("📋 Tabla de Datos Comparativa")

import io
from utils import format_df_spanish

tab1, tab2 = st.tabs(["📅 Matriz Comparativa (Semanas vs Años)", "📄 Datos Detallados"])

with tab1:
    if not df_comp.empty:
        # Matriz Semanas x Años
        df_pivot = df_comp.pivot(index='SEMANA', columns='ANIO', values='CANTIDAD').fillna(0).astype(int)
        
        # Asegurar semanas 1 a 52/53
        max_s = int(df_comp['SEMANA'].max()) if not df_comp.empty else 52
        all_s = pd.Index(range(1, max(53, max_s + 1)), name='SEMANA')
        df_pivot = df_pivot.reindex(all_s, fill_value=0)
        
        # Reordenar columnas según el orden de años seleccionado
        cols_ordered = [str(a) for a in selected_anios if str(a) in df_pivot.columns]
        df_pivot = df_pivot[cols_ordered]
        
        df_pivot_display = df_pivot.reset_index().rename(columns={'SEMANA': 'Semana Epidemiológica'})
        styler_pivot = format_df_spanish(df_pivot_display)
        st.dataframe(styler_pivot, use_container_width=True, hide_index=True)

        col_d1, col_d2, _ = st.columns([0.2, 0.2, 0.6])
        csv_p = df_pivot_display.to_csv(index=False).encode('utf-8')
        col_d1.download_button("📄 Descargar CSV (Matriz)", data=csv_p, file_name=f'comparativa_matriz_{selected_evento}.csv', mime='text/csv')

        buffer_p = io.BytesIO()
        with pd.ExcelWriter(buffer_p, engine='xlsxwriter') as writer:
            df_pivot_display.to_excel(writer, index=False, sheet_name='Matriz_Comparativa')
        col_d2.download_button("🟢 Descargar Excel (Matriz)", data=buffer_p.getvalue(), file_name=f'comparativa_matriz_{selected_evento}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    else:
        st.warning("No hay datos disponibles para los filtros seleccionados.")

with tab2:
    if not df_comp.empty:
        df_detail = df_comp[['ANIO', 'SEMANA', 'Semana_Continua', 'CANTIDAD']].copy().rename(columns={
            'ANIO': 'Año',
            'SEMANA': 'Semana Epidemiológica',
            'Semana_Continua': 'Semana Continua',
            'CANTIDAD': 'Casos'
        })
        styler_detail = format_df_spanish(df_detail)
        st.dataframe(styler_detail, use_container_width=True, hide_index=True)

        col_d1, col_d2, _ = st.columns([0.2, 0.2, 0.6])
        csv_d = df_detail.to_csv(index=False).encode('utf-8')
        col_d1.download_button("📄 Descargar CSV (Detalle)", data=csv_d, file_name=f'comparativa_detalle_{selected_evento}.csv', mime='text/csv')

        buffer_d = io.BytesIO()
        with pd.ExcelWriter(buffer_d, engine='xlsxwriter') as writer:
            df_detail.to_excel(writer, index=False, sheet_name='Detalle')
        col_d2.download_button("🟢 Descargar Excel (Detalle)", data=buffer_d.getvalue(), file_name=f'comparativa_detalle_{selected_evento}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

