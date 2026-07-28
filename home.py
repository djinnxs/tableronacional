import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import json
import io
import numpy as np
import datetime
from utils import get_epi_week_data, format_df_spanish

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tablero Epidemiológico Nacional", page_icon="🇦🇷", layout="wide")

# --- ESTILOS ---
st.markdown("""
    <style>
    .stMetric { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #e5e7eb; }
    .premium-header { color: #1e3a8a; font-size: 2.2rem; font-weight: 800; margin-bottom: 10px; }
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

if 'con' not in st.session_state:
    st.session_state.con = duckdb.connect()
con = st.session_state.con

@st.cache_data
def load_geojson(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

@st.cache_data
def get_filter_options():
    anios = con.execute("SELECT DISTINCT ANIO FROM 'data/base_nacional.parquet' ORDER BY 1 DESC").df()['ANIO'].astype(str).tolist()
    eventos_raw = con.execute("SELECT DISTINCT CAST(ID_SNVS_EVENTO AS VARCHAR) as ID_SNVS_EVENTO, Evento FROM 'data/base_nacional.parquet' ORDER BY Evento").df()
    # Filtramos 'Sin Datos' de la lista de provincias para que la UI sea limpia
    provincias = con.execute("SELECT DISTINCT Provincia FROM 'data/base_nacional.parquet' WHERE Provincia != 'Sin Datos' ORDER BY 1").df()['Provincia'].tolist()
    semanas = sorted(con.execute("SELECT DISTINCT SEMANA FROM 'data/base_nacional.parquet'").df()['SEMANA'].tolist())
    return anios, dict(zip(eventos_raw['ID_SNVS_EVENTO'], eventos_raw['Evento'])), provincias, ["Todas"] + [str(s) for s in semanas]

# --- SIDEBAR ---
anios_list, eventos_dict, provincias_list, semanas_list = get_filter_options()
selected_anios = st.sidebar.multiselect("Año", anios_list, default=[anios_list[0]] if anios_list else [])
if not selected_anios and anios_list:
    selected_anios = [anios_list[0]]
selected_semanas = st.sidebar.multiselect("Semanas", semanas_list, default=["Todas"])
selected_event_ids = st.sidebar.multiselect("Eventos", list(eventos_dict.keys()), format_func=lambda x: f"{x} - {eventos_dict[x]}")
if "pending_jurisdiccion" in st.session_state:
    st.session_state.jurisdiccion = st.session_state.pop("pending_jurisdiccion")
if "jurisdiccion" not in st.session_state:
    st.session_state.jurisdiccion = "Nacional"
selected_provincia_ui = st.sidebar.selectbox("Jurisdicción", ["Nacional"] + provincias_list, key="jurisdiccion")
metric_option = st.sidebar.radio("Métrica Visual", ["Casos", "Tasas (cada 100k hab.)"])

@st.cache_data
def get_dashboard_data(anios, semanas, event_ids, prov_filter):
    anios_str = ", ".join([str(a) for a in anios])
    max_anio = max([int(a) for a in anios]) if anios else 2024
    where = [f"ANIO IN ({anios_str})"]
    if semanas and "Todas" not in semanas:
        where.append(f"SEMANA IN ({', '.join(semanas)})")
    if event_ids:
        event_ids_str = ", ".join([f"'{str(eid)}'" for eid in event_ids])
        where.append(f"ID_SNVS_EVENTO IN ({event_ids_str})")
    
    where_str = " AND ".join(where)

    if prov_filter == "Nacional":
        sql_base = f"SELECT id_provincia as id_geo, Provincia as Nombre, CANTIDAD, Evento FROM 'data/base_nacional.parquet' WHERE {where_str}"
        sql_pop = f"SELECT LPAD(juri::VARCHAR, 2, '0') as id_geo, SUM(poblacion) as Poblacion FROM 'data/poblacionxprovinciaindec.parquet' WHERE ano = {max_anio} AND sexo_nombre = 'Ambos sexos' GROUP BY 1"
        id_len = 2
    else:
        sql_base = f"SELECT id_departamento as id_geo, Departamento as Nombre, CANTIDAD, Evento FROM 'data/base_nacional.parquet' WHERE {where_str} AND Provincia = '{prov_filter}'"
        
        # Obtener el ID de la provincia seleccionada para filtrar la población
        res_id = con.execute(f"SELECT DISTINCT id_provincia FROM 'data/base_nacional.parquet' WHERE Provincia = '{prov_filter}'").fetchone()
        id_p = str(res_id[0]).zfill(2) if res_id else "00"
        
        sql_pop = f"""
            SELECT (LPAD(juri_codigo::VARCHAR, 2, '0') || LPAD(departamento_codigo::VARCHAR, 3, '0')) as id_geo, SUM(poblacion) as Poblacion 
            FROM 'data/proyecciones_depto_indec.parquet' 
            WHERE ano = {max_anio} AND LPAD(juri_codigo::VARCHAR, 2, '0') = '{id_p}' AND sexo_nombre = 'Ambos sexos'
            GROUP BY 1
        """
        id_len = 5

    df_b = con.execute(sql_base).df()
    df_p = con.execute(sql_pop).df()

    if df_b.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Normalización forzada de IDs
    df_b['id_geo'] = df_b['id_geo'].astype(str).str.strip().str.zfill(id_len)
    df_p['id_geo'] = df_p['id_geo'].astype(str).str.strip().str.zfill(id_len)

    # Agrupación para el mapa
    df_m = df_b.groupby(['id_geo', 'Nombre'])['CANTIDAD'].sum().reset_index().rename(columns={'CANTIDAD': 'Casos'})
    df_m = pd.merge(df_m, df_p, on='id_geo', how='left')
    df_m['Poblacion'] = df_m['Poblacion'].fillna(0)
    df_m['Tasa'] = (df_m['Casos'] / df_m['Poblacion'] * 100000).replace([np.inf, -np.inf], 0).fillna(0)

    return df_m, df_b

df_dash, df_full = get_dashboard_data(selected_anios, selected_semanas, selected_event_ids, selected_provincia_ui)

# --- SE ACTUAL ---
sem_hoy, anio_hoy = get_epi_week_data(datetime.date.today())

# --- UI ---
col_head, col_back = st.columns([0.75, 0.25])
with col_head:
    st.markdown(f"""
        <div style='display: flex; align-items: baseline; gap: 20px;'>
            <h1 class='premium-header'>Situación: {selected_provincia_ui}</h1>
            <h3 style='color: #666;'>Semana Epi actual: <span style='color: #e11d48;'>{sem_hoy}</span> del {anio_hoy}</h3>
        </div>
        """, unsafe_allow_html=True)

with col_back:
    if selected_provincia_ui != "Nacional":
        st.write("") # Espaciado vertical para alinear con el título
        if st.button("🇦🇷 Volver a Vista Nacional", use_container_width=True):
            st.session_state.pending_jurisdiccion = "Nacional"
            st.rerun()

if not df_dash.empty:
    c1, c2, c3 = st.columns(3)
    casos_t = df_dash['Casos'].sum()
    pop_t = df_dash['Poblacion'].sum()
    tasa_t = (casos_t / pop_t * 100000) if pop_t > 0 else 0
    
    c1.metric("Casos Totales", f"{int(casos_t):,}".replace(",", "."))
    c2.metric("Población Estimada", f"{int(pop_t):,}".replace(",", "."))
    c3.metric("Tasa General", f"{tasa_t:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    mostrar_grafico = st.checkbox("Mostrar gráfico", value=False)
    
    if mostrar_grafico:
        col_map, col_pie = st.columns([1.2, 0.8])
    else:
        col_map = st.container()
        col_pie = None
    
    with col_map:
        geojson = load_geojson('data/provincia.json' if selected_provincia_ui == "Nacional" else 'data/departamento.json')
        color_v = 'Casos' if metric_option == "Casos" else 'Tasa'
        
        fig = px.choropleth_mapbox(
    df_dash, geojson=geojson, locations='id_geo', featureidkey="properties.in1",
    color=color_v, hover_name='Nombre', mapbox_style="white-bg",
    opacity=0.7, color_continuous_scale="Blues" if metric_option == "Casos" else "Reds"
)
        
        fig.update_layout(
            mapbox_layers=[
                {
                    "below": 'traces',
                    "sourcetype": "raster",
                    "sourceattribution": "IGN Argenmap",
                    "source": [
                        "https://wms.ign.gob.ar/geoserver/gwc/service/tms/1.0.0/capabaseargenmap@EPSG%3A3857@png/{z}/{x}/{-y}.png"
                    ]
                }
            ]
        )
        
        if selected_provincia_ui == "Nacional":
            center, zoom = {"lat": -40.0, "lon": -63.0}, 2.7
        else:
            c = PROVINCIA_COORDENADAS.get(selected_provincia_ui, {"lat": -38.0, "lon": -63.0, "zoom": 5.0})
            center, zoom = {"lat": c["lat"], "lon": c["lon"]}, c["zoom"]
            
        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=500, mapbox={"center": center, "zoom": zoom})
        sel = st.plotly_chart(fig, width='stretch', on_select="rerun", selection_mode="points", key=f"main_map_{selected_provincia_ui}")
        
        # Lógica de drill-down: si estamos en Nacional y hacemos clic en una provincia, navegamos a ella
        pts = sel.get("selection", {}).get("points", [])
        if pts and selected_provincia_ui == "Nacional":
            clicked_id = pts[0].get("location")
            if clicked_id:
                matched = df_dash[df_dash['id_geo'] == clicked_id]
                if not matched.empty:
                    clicked_name = matched.iloc[0]['Nombre']
                    if clicked_name in provincias_list:
                        st.session_state.pending_jurisdiccion = clicked_name
                        st.rerun()

    if mostrar_grafico and col_pie is not None:
        with col_pie:
            st.subheader("Eventos detectados")
            pts = sel.get("selection", {}).get("points", [])
            if pts:
                name = pts[0].get("hovertext")
                st.info(f"Filtro: {name}")
                df_p = df_full[df_full['Nombre'] == name].groupby('Evento')['CANTIDAD'].sum().reset_index()
            else:
                df_p = df_full.groupby('Evento')['CANTIDAD'].sum().reset_index()
            
            # Mostrar solo los 10 con más cantidad
            df_p = df_p.sort_values('CANTIDAD', ascending=False).head(10)
            
            fig_p = px.pie(df_p, values='CANTIDAD', names='Evento', hole=0.4)
            st.plotly_chart(fig_p, width='stretch')

    st.markdown("---")
    # Preparar datos de la tabla, siempre ordenada por Tasa para detectar anomalías
    df_table = df_dash[['Nombre', 'Casos', 'Poblacion', 'Tasa']].sort_values('Tasa', ascending=False).copy()

    # Aplicar formato español (decimales con coma, miles con punto)
    # Primero aplicamos el degradado y luego el formato de números
    styler_final = format_df_spanish(df_table)
    if metric_option == "Casos":
        styler_final = styler_final.background_gradient(cmap="Blues", subset=['Tasa'])
    else:
        styler_final = styler_final.background_gradient(cmap="Reds", subset=['Tasa'])

    # Mostrar la tabla. Omitimos column_config.format para que prevalezca el estilo
    st.dataframe(styler_final, use_container_width=True, hide_index=True, column_config={
        "Nombre": st.column_config.TextColumn("Jurisdicción"),
        "Casos": st.column_config.NumberColumn("Casos"),
        "Poblacion": st.column_config.NumberColumn("Población"),
        "Tasa": st.column_config.NumberColumn("Tasa")
    })

    # --- BOTONES DE DESCARGA ---
    col_d1, col_d2, _ = st.columns([0.2, 0.2, 0.6])
    
    # CSV
    csv = df_table.to_csv(index=False).encode('utf-8')
    col_d1.download_button("📄 Descargar CSV", data=csv, file_name='datos_epidemiologicos.csv', mime='text/csv')

    # Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_table.to_excel(writer, index=False, sheet_name='Datos')
    col_d2.download_button("🟢 Descargar Excel", data=buffer.getvalue(), file_name='datos_epidemiologicos.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
else:
    st.warning("No se encontraron datos para la selección actual. Verifique los filtros o el archivo 'base_nacional.parquet'.")