import streamlit as st
import pandas as pd
import datetime
from utils import get_epi_week_data, format_df_spanish

# Configuración de página compatible
st.set_page_config(page_title="Velocidad y Alertas", layout="wide")

# --- SE ACTUAL ---
sem_hoy, anio_hoy = get_epi_week_data(datetime.date.today())
st.markdown(f"<h3 style='text-align: center;'>Hoy es Semana Epidemiológica: <span style='color: #e11d48; font-weight:bold;'>{sem_hoy}</span> del {anio_hoy}</h3>", unsafe_allow_html=True)

st.title("🚀 Velocidad de Notificación y Alertas")

st.markdown("""
Esta página analiza la variación de casos entre las semanas más recientes, considerando un retraso de notificación de 2 semanas.
""")

# Semanas de interés
sem_actual = sem_hoy - 2
sem_previa = sem_hoy - 3

st.warning(f"Comparando Semana **{sem_actual}** (Actual - 2) vs Semana **{sem_previa}** (Actual - 3) del año {anio_hoy}")

@st.cache_data
def get_data():
    return pd.read_parquet('data/base_nacional.parquet')

df = get_data()

# Filtrar por año actual
df_alert = df[df['ANIO'] == anio_hoy]

# Agrupar por Evento y Semana
df_stats = df_alert[df_alert['SEMANA'].isin([sem_actual, sem_previa])]
df_stats = df_stats.groupby(['Evento', 'SEMANA'])['CANTIDAD'].sum().unstack(fill_value=0)

# Renombrar columnas
if sem_actual in df_stats.columns and sem_previa in df_stats.columns:
    df_stats = df_stats.rename(columns={sem_actual: 'Casos_Actual', sem_previa: 'Casos_Previo'})
    df_stats['Variación'] = df_stats['Casos_Actual'] - df_stats['Casos_Previo']
    df_stats['Crecimiento (%)'] = (df_stats['Variación'] / df_stats['Casos_Previo'] * 100).fillna(0)
    
    # Formatear para visualización
    df_stats = df_stats.sort_values('Variación', ascending=False)
    
    def color_variacion(val):
        color = 'red' if val > 0 else 'green'
        return f'color: {color}'

    st.subheader("Estado por Evento")
    st.markdown("---")
    
    styler = format_df_spanish(df_stats)
    
    # Corrección del error: se quita width='stretch' y se añade use_container_width=True
    st.dataframe(
        styler.map(color_variacion, subset=['Variación']),
        use_container_width=True
    )
    
    # Alertas de crecimiento significativo
    alertas = df_stats[df_stats['Crecimiento (%)'] > 20].index.tolist()
    if alertas:
        st.error(f"🚨 **ALERTAS DE CRECIMIENTO (>20%):** {', '.join(alertas)}")
    else:
        st.success("✅ No se detectan crecimientos significativos (>20%) en la última semana comparada.")

else:
    st.error("No hay datos suficientes en la base para las semanas calculadas (SE-2 y SE-3).")
    st.info("Verifique que la base nacional esté actualizada con los datos más recientes.")