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

st.markdown("---")
st.subheader("📋 Tabla de Datos")

import io
from utils import format_df_spanish

if selected_evento != "Todos":
    df_table = df_plot.copy()
    df_table['ANIO'] = selected_anio
    df_table['Evento'] = selected_evento
    df_table['CANTIDAD'] = df_table['CANTIDAD'].astype(int)
    df_table = df_table[['ANIO', 'Evento', 'SEMANA', 'CANTIDAD']].rename(columns={
        'ANIO': 'Año',
        'Evento': 'Evento',
        'SEMANA': 'Semana Epidemiológica',
        'CANTIDAD': 'Casos'
    })
    
    styler = format_df_spanish(df_table)
    st.dataframe(styler, use_container_width=True, hide_index=True)
    
    col_d1, col_d2, _ = st.columns([0.2, 0.2, 0.6])
    csv = df_table.to_csv(index=False).encode('utf-8')
    col_d1.download_button("📄 Descargar CSV", data=csv, file_name=f'curva_epi_{selected_evento}_{selected_anio}.csv', mime='text/csv')

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_table.to_excel(writer, index=False, sheet_name='Datos')
    col_d2.download_button("🟢 Descargar Excel", data=buffer.getvalue(), file_name=f'curva_epi_{selected_evento}_{selected_anio}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

else:
    tab1, tab2 = st.tabs(["📊 Total por Semana", "🔍 Desglose por Evento"])
    
    with tab1:
        df_table_total = df_plot.copy()
        df_table_total['ANIO'] = selected_anio
        df_table_total['CANTIDAD'] = df_table_total['CANTIDAD'].astype(int)
        df_table_total = df_table_total[['ANIO', 'SEMANA', 'CANTIDAD']].rename(columns={
            'ANIO': 'Año',
            'SEMANA': 'Semana Epidemiológica',
            'CANTIDAD': 'Total Casos'
        })
        styler_total = format_df_spanish(df_table_total)
        st.dataframe(styler_total, use_container_width=True, hide_index=True)
        
        col_d1, col_d2, _ = st.columns([0.2, 0.2, 0.6])
        csv = df_table_total.to_csv(index=False).encode('utf-8')
        col_d1.download_button("📄 Descargar CSV (Total)", data=csv, file_name=f'curva_epi_total_{selected_anio}.csv', mime='text/csv')

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_table_total.to_excel(writer, index=False, sheet_name='Total_Semana')
        col_d2.download_button("🟢 Descargar Excel (Total)", data=buffer.getvalue(), file_name=f'curva_epi_total_{selected_anio}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        
    with tab2:
        df_events_group = df[mask].groupby(['Evento', 'SEMANA'])['CANTIDAD'].sum().reset_index()
        if selected_anio == anio_hoy:
            df_events_group = df_events_group[df_events_group['SEMANA'] <= (sem_hoy - 2)]
        
        if not df_events_group.empty:
            df_pivot_events = df_events_group.pivot(index='Evento', columns='SEMANA', values='CANTIDAD').fillna(0).astype(int)
            df_pivot_events['Total'] = df_pivot_events.sum(axis=1)
            df_pivot_events = df_pivot_events.sort_values('Total', ascending=False)
            
            styler_events = format_df_spanish(df_pivot_events.reset_index())
            st.dataframe(styler_events, use_container_width=True, hide_index=True)
            
            col_d1, col_d2, _ = st.columns([0.2, 0.2, 0.6])
            csv_ev = df_pivot_events.reset_index().to_csv(index=False).encode('utf-8')
            col_d1.download_button("📄 Descargar CSV (Desglose)", data=csv_ev, file_name=f'curva_epi_desglose_{selected_anio}.csv', mime='text/csv')

            buffer_ev = io.BytesIO()
            with pd.ExcelWriter(buffer_ev, engine='xlsxwriter') as writer:
                df_pivot_events.reset_index().to_excel(writer, index=False, sheet_name='Desglose_Eventos')
            col_d2.download_button("🟢 Descargar Excel (Desglose)", data=buffer_ev.getvalue(), file_name=f'curva_epi_desglose_{selected_anio}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        else:
            st.warning("No hay datos de eventos para los filtros seleccionados.")
