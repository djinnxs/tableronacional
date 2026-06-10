import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import json
import numpy as np
import datetime
from streamlit_autorefresh import st_autorefresh
from utils import get_epi_week_data, format_df_spanish

# --- CONFIGURATION ---
st.set_page_config(page_title="Presentación", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

# --- Ocultar sidebar y reducir padding superior ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    .stMainBlockContainer { padding-top: 1rem !important; }
    .stMetric { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #e5e7eb; }
    .premium-header { color: #1e3a8a; font-size: 2.2rem; font-weight: 800; margin-bottom: 0px; margin-top: 0px; }
    iframe[title="streamlit_autorefresh.st_autorefresh"] { height: 0 !important; min-height: 0 !important; overflow: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- COORDENADAS ---
PROVINCIA_COORDENADAS = {
    "CABA": {"lat": -34.6037, "lon": -58.439, "zoom": 10.5},
    "Buenos Aires": {"lat": -36.6, "lon": -60.3, "zoom": 5.4},
    "Catamarca": {"lat": -28.5, "lon": -66.8, "zoom": 6.0},
    "Chaco": {"lat": -27.0, "lon": -60.7, "zoom": 5.9},
    "Chubut": {"lat": -43.0, "lon": -68.0, "zoom": 5.2},
    "Córdoba": {"lat": -32.4, "lon": -64.2, "zoom": 6.0},
    "Corrientes": {"lat": -28.6, "lon": -57.5, "zoom": 6.2},
    "Entre Ríos": {"lat": -32.0, "lon": -59.3, "zoom": 6.7},
    "Formosa": {"lat": -24.5, "lon": -59.9, "zoom": 5.9},
    "Jujuy": {"lat": -23.3, "lon": -65.7, "zoom": 6.5},
    "La Pampa": {"lat": -36.5, "lon": -65.8, "zoom": 6.0},
    "La Rioja": {"lat": -29.5, "lon": -67.3, "zoom": 6.4},
    "Mendoza": {"lat": -34.4, "lon": -68.6, "zoom": 6.1},
    "Misiones": {"lat": -26.7, "lon": -54.8, "zoom": 7.0},
    "Neuquén": {"lat": -38.5, "lon": -70.1, "zoom": 6.2},
    "Río Negro": {"lat": -39.8, "lon": -67.2, "zoom": 5.0},
    "Salta": {"lat": -23.8, "lon": -65.4, "zoom": 5.6},
    "San Juan": {"lat": -30.5, "lon": -68.5, "zoom": 6.5},
    "San Luis": {"lat": -33.9, "lon": -66.3, "zoom": 6.8},
    "Santa Cruz": {"lat": -49.0, "lon": -69.5, "zoom": 5.3},
    "Santa Fe": {"lat": -31.1, "lon": -60.7, "zoom": 6.1},
    "Santiago del Estero": {"lat": -27.8, "lon": -63.4, "zoom": 6.5},
    "Tierra del Fuego": {"lat": -53.8, "lon": -66.7, "zoom": 6.0},
    "Tucumán": {"lat": -26.8, "lon": -65.3, "zoom": 7.5},
}

# --- DATABASE CONNECTION ---
if 'con' not in st.session_state:
    st.session_state.con = duckdb.connect()
con = st.session_state.con

@st.cache_data
def load_geojson(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# --- Valores implícitos: año actual, todas las semanas, Nacional ---
ANIO_ACTUAL = datetime.date.today().year

@st.cache_data
def get_raw_data(anio):
    """Carga datos crudos del año actual, nivel Nacional, todas las semanas."""
    sql_base = f"""
        SELECT id_provincia as id_geo, Provincia as Nombre, CANTIDAD, Evento
        FROM 'data/base_nacional.parquet'
        WHERE ANIO = {anio}
    """
    sql_pop = f"""
        SELECT LPAD(juri::VARCHAR, 2, '0') as id_geo, SUM(poblacion) as Poblacion
        FROM 'data/poblacionxprovinciaindec.parquet'
        WHERE ano = {anio} AND sexo_nombre = 'Ambos sexos'
        GROUP BY 1
    """
    df_b = con.execute(sql_base).df()
    df_p = con.execute(sql_pop).df()

    if df_b.empty:
        return pd.DataFrame(), pd.DataFrame()

    df_b['id_geo'] = df_b['id_geo'].astype(str).str.strip().str.zfill(2)
    df_p['id_geo'] = df_p['id_geo'].astype(str).str.strip().str.zfill(2)
    return df_b, df_p


def build_dashboard(df_b, df_p, event_name):
    """Filtra por evento, agrupa y calcula tasas."""
    df_evt = df_b[df_b['Evento'] == event_name].copy()
    if df_evt.empty:
        return pd.DataFrame()
    df_m = df_evt.groupby(['id_geo', 'Nombre'])['CANTIDAD'].sum().reset_index().rename(columns={'CANTIDAD': 'Casos'})
    df_m = pd.merge(df_m, df_p, on='id_geo', how='left')
    df_m['Poblacion'] = df_m['Poblacion'].fillna(0)
    df_m['Tasa'] = (df_m['Casos'] / df_m['Poblacion'] * 100000).replace([np.inf, -np.inf], 0).fillna(0)
    return df_m


# --- Auto-refresh desde el navegador cada N milisegundos ---
REFRESH_SECONDS = 4  # Ajustar según se desee
tick = st_autorefresh(interval=REFRESH_SECONDS * 1000, limit=None, key="presentacion_refresh")

# tick se incrementa en cada refresh; lo usamos como índice de evento

# --- Cargar datos ---
df_raw, df_pop = get_raw_data(ANIO_ACTUAL)

if df_raw.empty:
    st.warning("No se encontraron datos para el año actual.")
    st.stop()

unique_events = sorted(df_raw['Evento'].unique())
current_event = unique_events[tick % len(unique_events)]

df_dash = build_dashboard(df_raw, df_pop, current_event)

# --- Header con botón Salir ---
sem_hoy, anio_hoy = get_epi_week_data(datetime.date.today())

col_header, col_exit = st.columns([0.9, 0.1])
with col_header:
    st.markdown(f"""
        <div style='display: flex; align-items: baseline; gap: 15px; margin:0; padding:0;'>
            <h1 class='premium-header'>Situación Nacional — {ANIO_ACTUAL}</h1>
            <h3 style='color: #666; margin:0;'>SE <span style='color: #e11d48;'>{sem_hoy}</span>/{anio_hoy}</h3>
            <span style='color: #999; font-size: 0.9rem;'>▸ {current_event} ({(tick % len(unique_events)) + 1}/{len(unique_events)})</span>
        </div>
        """, unsafe_allow_html=True)
with col_exit:
    if st.button("🚪 Salir", key="exit_btn"):
        st.switch_page("home.py")

if not df_dash.empty:
    c1, c2, c3 = st.columns(3)
    casos_t = df_dash['Casos'].sum()
    pop_t = df_dash['Poblacion'].sum()
    tasa_t = (casos_t / pop_t * 100000) if pop_t > 0 else 0
    c1.metric("Casos Totales", f"{int(casos_t):,}".replace(",", "."))
    c2.metric("Población Estimada", f"{int(pop_t):,}".replace(",", "."))
    c3.metric("Tasa General", f"{tasa_t:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # Mapa coroplético
    geojson = load_geojson('data/provincia.json')
    fig = px.choropleth_mapbox(
        df_dash, geojson=geojson, locations='id_geo', featureidkey="properties.in1",
        color='Tasa', hover_name='Nombre', mapbox_style="white-bg",
        opacity=0.7, color_continuous_scale="Reds"
    )

    fig.update_layout(
        mapbox_layers=[{
            "below": 'traces',
            "sourcetype": "raster",
            "sourceattribution": "IGN Argenmap",
            "source": ["https://wms.ign.gob.ar/geoserver/gwc/service/tms/1.0.0/capabaseargenmap@EPSG%3A3857@png/{z}/{x}/{-y}.png"]
        }]
    )

    fig.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        height=500,
        mapbox={"center": {"lat": -40.0, "lon": -63.0}, "zoom": 2.7}
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabla
    df_table = df_dash[['Nombre', 'Casos', 'Poblacion', 'Tasa']].sort_values('Tasa', ascending=False).copy()
    styler = format_df_spanish(df_table).background_gradient(cmap="Reds", subset=['Tasa'])
    st.dataframe(styler, use_container_width=True, hide_index=True, column_config={
        "Nombre": st.column_config.TextColumn("Jurisdicción"),
        "Casos": st.column_config.NumberColumn("Casos"),
        "Poblacion": st.column_config.NumberColumn("Población"),
        "Tasa": st.column_config.NumberColumn("Tasa")
    })
else:
    st.warning("No hay datos para el evento seleccionado.")
