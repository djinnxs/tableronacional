import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime
import re
import json
import plotly.express as px
import numpy as np

# Configuración de la página
st.set_page_config(page_title="SNEI - Vigilancia de Epirumores", page_icon="🦠", layout="wide")

st.markdown(
    '<center><h3 style="font-weight:bold; padding:5px; border-radius:6px; width:100%;">🦠 Portal de Epirumores (Búsqueda RSS Global con Mapa Interactivo)</h3></center>',
    unsafe_allow_html=True,
)
st.write("Vigilancia Basada en Eventos (EBS) mediante rastreo automático y geoespacial en tiempo real de Google News Argentina.")
st.markdown("---")

# Coordenadas geográficas oficiales de las provincias para el centrado dinámico del mapa
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

# Mapa de códigos INDEC (in1 en provincia.json) para relacionar datos con el GeoJSON del mapa
MAPA_PROVINCIAS_IDS = {
    "CABA": "02", "Buenos Aires": "06", "Catamarca": "10", "Chaco": "22", "Chubut": "26",
    "Córdoba": "14", "Corrientes": "18", "Entre Ríos": "30", "Formosa": "34", "Jujuy": "38",
    "La Pampa": "42", "La Rioja": "46", "Mendoza": "50", "Misiones": "54", "Neuquén": "58",
    "Río Negro": "62", "Salta": "66", "San Juan": "70", "San Luis": "74", "Santa Cruz": "78",
    "Santa Fe": "82", "Santiago del Estero": "86", "Tierra del Fuego": "94", "Tucumán": "90"
}

# Mapeo de términos de búsqueda expandidos para maximizar la recolección de fuentes locales por provincia
BUSQUEDA_PROVINCIAS_EXPANDIDA = {
    "CABA": '("CABA" OR "Capital Federal" OR "Buenos Aires" OR "Palermo" OR "Flores" OR "Constitucion")',
    "Buenos Aires": '("Buenos Aires" OR "PBA" OR "La Plata" OR "Mar del Plata" OR "Bahia Blanca" OR "Tandil" OR "Pergamino" OR "Olavarria")',
    "Catamarca": '("Catamarca" OR "San Fernando del Valle")',
    "Chaco": '("Chaco" OR "Resistencia" OR "Saenz Peña" OR "Sáenz Peña")',
    "Chubut": '("Chubut" OR "Rawson" OR "Trelew" OR "Comodoro Rivadavia" OR "Puerto Madryn")',
    "Córdoba": '("Córdoba" OR "Cordoba" OR "Villa Maria" OR "Rio Cuarto" OR "Carlos Paz")',
    "Corrientes": '("Corrientes" OR "Goya" OR "Paso de los Libres")',
    "Entre Ríos": '("Entre Rios" OR "Entre Ríos" OR "Parana" OR "Paraná" OR "Concordia" OR "Gualeguaychu" OR "Gualeguaychú")',
    "Formosa": '("Formosa" OR "Clorinda")',
    "Jujuy": '("Jujuy" OR "San Salvador" OR "Humahuaca")',
    "La Pampa": '("La Pampa" OR "Santa Rosa" OR "General Pico")',
    "La Rioja": '("La Rioja" OR "Chilecito")',
    "Mendoza": '("Mendoza" OR "San Rafael" OR "Godoy Cruz" OR "Lujan de Cuyo")',
    "Misiones": '("Misiones" OR "Posadas" OR "Obera" OR "Oberá" OR "Iguazu" OR "Iguazú")',
    "Neuquén": '("Neuquen" OR "Neuquén" OR "San Martin de los Andes" OR "Zapala")',
    "Río Negro": '("Rio Negro" OR "Río Negro" OR "Bariloche" OR "Viedma" OR "Cipolletti" OR "General Roca")',
    "Salta": '("Salta" OR "Oran" OR "Cafayate" OR "Tartagal")',
    "San Juan": '("San Juan" OR "Caucete")',
    "San Luis": '("San Luis" OR "Villa Mercedes")',
    "Santa Cruz": '("Santa Cruz" OR "Rio Gallegos" OR "Río Gallegos" OR "Calafate" OR "Caleta Olivia")',
    "Santa Fe": '("Santa Fe" OR "Rosario" OR "Rafaela" OR "Reconquista" OR "Venado Tuerto")',
    "Santiago del Estero": '("Santiago del Estero" OR "La Banda")',
    "Tierra del Fuego": '("Tierra del Fuego" OR "Ushuaia" OR "Rio Grande" OR "Río Grande")',
    "Tucumán": '("Tucuman" OR "Tucumán" OR "San Miguel de Tucuman" OR "Tafi del Valle")'
}

# Lista masiva implícita de Vigilancia Epidemiológica de la SNEI
KEYWORDS_IMPLICITAS = [
    'epidemia', 'enfermedad', 'virus', 'vacuna', 'Rabia', 'Lepidópteros', 'Lonomía', 'Alacranismo', 'Amebiasis', 
    'Araneísmo', 'Latrodectismo', 'Loxoscelismo', 'Foneutrismo', 'Aspergilosis', 'Bartonelosis', 'Botulismo', 
    'Bronquiolitis', 'Brucelosis', 'Candidemias', 'Candidiasis', 'Carbunco', 'Miositis', 'Celiaquía', 'Chagas', 
    'Cisticercosis', 'Citomegalovirus', 'Clamidiasis', 'Coccidioidomicosis', 'Cólera', 'Coqueluche', 
    'Coriomeningitis', 'COVID-19', 'Influenza', 'Cromoblastomicosis', 'Biotinidasa', 'Dengue', 'Dermatofitosis', 
    'Diabetes', 'Diarrea', 'Difteria', 'Encefalitis de San Luis', 'Encefalitis equina del Oeste', 
    'Encefalopatía espongiforme', 'Enfermedad Febril Exantemática-EFE', 'Sarampión', 'Rubéola', 'Virus del Zika', 
    'Esporotricosis', 'Fenilcetonuria', 'Feohifomicosis', 'Fibrosis Quística', 'Fiebre Amarilla', 'Chikungunya', 
    'Oropouche', 'Fiebre del Nilo Occidental', 'Fiebre Hemorrágica Argentina', 'Fiebre Q', 'Borreliosis', 
    'Fiebre tifoidea', 'Filariosis', 'Galactosemia', 'Gonorrea', 'Hantavirosis', 'paratifoidea', 'Hepatitis', 
    'Hialohifomicosis', 'Hidatidosis', 'Hidroarsenicismo', 'Hiperplasia Suprarrenal Congénita', 
    'Hipotiroidismo congénito', 'Histoplasmosis', 'HTLV', 'Infección respiratoria aguda bacteriana', 
    'Infecciones genitales', 'Infecciones por Candida auris', 'Cryptococcus', 'hongos miceliales', 
    'Influenza Aviar', 'Intoxicación medicamentosa', 'Intoxicación por Moluscos', 'Intoxicación por ARSÉNICO', 
    'Intoxicación por Cromo', 'Intoxicación por hidrocarburos', 'Intoxicación por Mercurio', 
    'Intoxicación por plaguicidas', 'Intoxicación por Plomo', 'Intoxicación por Monóxido de Carbono', 
    'Legionelosis', 'Leishmaniasis', 'Lepra', 'Leptospirosis', 'Linfogranuloma Venéreo', 'Listeriosis', 
    'Meningoencefalitis', 'Metahemoglobinemia del lactante', 'Micetomas actinomicóticos', 'Mucormicosis', 
    'Neumonía', 'Ofidismo', 'infecciones bacterianas', 'Paludismo', 'Pandrogo resistencia', 
    'Paracoccidioidomicosis', 'Parotiditis', 'Poliomielitis', 'Psitacosis', 'Rickettsiosis', 'Sífilis', 
    'brote de ETA', 'virus emergente', 'Streptococcus agalactiae', 'Sindrome Urémico Hemolítico', 'Tétanos', 
    'Toxocariasis', 'Toxoplasmosis', 'Triquinelosis', 'Tuberculosis', 'Triquinosis', 'VIH', 'Viruela', 'Antrax',
    'brote', 'alerta sanitaria'
]

# 1. Inicializar estado por defecto si no existe
if "provincia_seleccionada" not in st.session_state:
    st.session_state.provincia_seleccionada = "Toda Argentina"

# 2. SINCRONIZACIÓN PRE-WIDGET: Captura el clic del mapa ANTES de instanciar el selectbox
if "mapa_epirumores_interactivo" in st.session_state and st.session_state["mapa_epirumores_interactivo"]:
    puntos_seleccionados = st.session_state["mapa_epirumores_interactivo"].get("selection", {}).get("points", [])
    if puntos_seleccionados:
        id_geo_clicado = puntos_seleccionados[0].get("location")
        if id_geo_clicado:
            # Obtener nombre de provincia a partir del código geográfico
            id_inv = {v: k for k, v in MAPA_PROVINCIAS_IDS.items()}
            provincia_clicada = id_inv.get(id_geo_clicado)
            if provincia_clicada and provincia_clicada != st.session_state.provincia_seleccionada:
                # Modificamos el valor de manera limpia antes de que selectbox se renderice en este rerun
                st.session_state.provincia_seleccionada = provincia_clicada

# Configuración del panel lateral
with st.sidebar:
    st.header("⚙️ Filtros de Búsqueda")
    
    # Selector territorial inicial utilizando la variable sincronizada sin generar conflictos
    provincia_filtro = st.selectbox(
        "Filtro de búsqueda territorial:", 
        ["Toda Argentina"] + sorted(list(PROVINCIA_COORDENADAS.keys())),
        key="provincia_seleccionada"
    )
    
    tiempo_filtro = st.selectbox(
        "Antigüedad de las publicaciones:",
        ["Últimas 48 horas", "Última semana", "Último mes"]
    )
    
    st.markdown("---")
    st.info("ℹ️ **Búsqueda Inteligente Activa:** El motor rastrea implícitamente más de 120 eventos bajo vigilancia, incluyendo patologías respiratorias, vectoriales e intoxicaciones (como Monóxido de Carbono).")

@st.cache_data
def load_geojson_local():
    """Carga de forma segura el archivo de límites provinciales oficial."""
    try:
        with open('data/provincia.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error al cargar el GeoJSON del mapa: {e}")
        return None

def limpiar_titulo_y_medio(titulo_completo):
    """Separa el titular real de la noticia del nombre del diario."""
    if " - " in titulo_completo:
        partes = titulo_completo.rsplit(" - ", 1)
        return partes[0].strip(), partes[1].strip()
    return titulo_completo, "Medio Local"

def formatear_fecha_rss(fecha_raw):
    """Normaliza fechas del feed RSS."""
    try:
        fecha_clean = re.sub(r'\s+[A-Z]{3,4}$', '', fecha_raw.strip())
        dt = datetime.strptime(fecha_clean, "%a, %d %b %Y %H:%M:%S")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return datetime.now().strftime("%d/%m/%Y")

def clasificas_provincia_noticia(titulo, enlace, region_seleccionada):
    """
    Analiza semánticamente el título y enlace de la noticia para identificar 
    a qué provincia de Argentina pertenece el reporte real de salud.
    """
    titulo_normalizado = titulo.lower()
    enlace_normalizado = enlace.lower()
    
    prov_keywords = {
        "CABA": ["caba", "buenos aires capital", "palermo", "recoleta", "flores", "constitucion", "san telmo", "belgrano"],
        "Buenos Aires": ["buenos aires", "provincia de buenos", "pba", "la plata", "bahia blanca", "mar del plata", "quilmes", "lanus", "tigre", "san isidro", "olavarria", "pergamino"],
        "Catamarca": ["catamarca", "san fernando del valle"],
        "Chaco": ["chaco", "resistencia", "saenz peña"],
        "Chubut": ["chubut", "rawson", "trelew", "comodoro", "madryn"],
        "Córdoba": ["cordoba", "villa maria", "rio cuarto", "carlos paz"],
        "Corrientes": ["corrientes", "paso de los libres", "goya"],
        "Entre Ríos": ["entre rios", "parana", "concordia", "gualeguaychu"],
        "Formosa": ["formosa", "clorinda"],
        "Jujuy": ["jujuy", "san salvador"],
        "La Pampa": ["la pampa", "santa rosa", "general pico"],
        "La Rioja": ["la rioja"],
        "Mendoza": ["mendoza", "san rafael", "godoy cruz"],
        "Misiones": ["misiones", "posadas", "obera", "iguazu"],
        "Neuquén": ["neuquen", "san martin de los andes", "zapala"],
        "Río Negro": ["rio negro", "bariloche", "viedma", "cipolletti", "roca"],
        "Salta": ["salta", "oran", "tartanagol"],
        "San Juan": ["san juan"],
        "San Luis": ["san luis", "villa mercedes"],
        "Santa Cruz": ["santa cruz", "rio gallegos", "calafate"],
        "Santa Fe": ["santa fe", "rosario", "rafaela", "reconquista", "venado tuerto"],
        "Santiago del Estero": ["santiago del estero", "la banda"],
        "Tierra del Fuego": ["tierra del fuego", "ushuaia", "rio grande"],
        "Tucumán": ["tucuman", "san miguel de tucuman"]
    }
    
    for prov, matches in prov_keywords.items():
        if any(m in titulo_normalizado or m in enlace_normalizado for m in matches):
            return prov
            
    if region_seleccionada in MAPA_PROVINCIAS_IDS:
        return region_seleccionada
        
    return "Nacional"

@st.cache_data(ttl=900)
def ejecutar_rastreo_rss(keywords, region, rango_tiempo):
    """
    Rastrea de forma global en Google News RSS usando expresiones booleanas precisas.
    Usa la query de búsqueda expandida para evitar escasez de fuentes.
    """
    if not keywords:
        return pd.DataFrame(), "No se han configurado palabras clave de rastreo."
        
    time_map = {
        "Últimas 48 horas": "when:2d",
        "Última semana": "when:7d",
        "Último mes": "when:30d"
    }
    time_query = time_map.get(rango_tiempo, "when:7d")
    
    if region == "Toda Argentina":
        region_query = "Argentina"
    else:
        region_query = BUSQUEDA_PROVINCIAS_EXPANDIDA.get(region, f'"{region}"')
    
    keywords_query = " OR ".join([f'"{kw}"' for kw in keywords[:45]])
    query_final = f"({keywords_query}) AND {region_query} {time_query}"
    
    url = f"https://news.google.com/rss/search?q={quote(query_final)}&hl=es-419&gl=AR&ceid=AR:es-419"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        noticias_extraidas = []
        
        for item in root.findall('.//item'):
            titulo_raw = item.find('title').text if item.find('title') is not None else ""
            enlace = item.find('link').text if item.find('link') is not None else ""
            fecha_raw = item.find('pubDate').text if item.find('pubDate') is not None else ""
            
            titulo_limpio, medio = limpiar_titulo_y_medio(titulo_raw)
            fecha_local = formatear_fecha_rss(fecha_raw)
            
            if any(term.lower() in titulo_limpio.lower() for term in keywords):
                provincia_detectada = clasificas_provincia_noticia(titulo_limpio, enlace, region)
                
                noticias_extraidas.append({
                    "fecha": fecha_local,
                    "provincia": provincia_detectada,
                    "medio": medio,
                    "titulo": titulo_limpio,
                    "enlace": enlace
                })
            
        df = pd.DataFrame(noticias_extraidas)
        if not df.empty:
            df = df.drop_duplicates(subset=['titulo']).reset_index(drop=True)
            
        return df, None
        
    except Exception as e:
        return pd.DataFrame(), f"Error al recuperar las noticias de Google News: {str(e)}"

# --- INTERFAZ PRINCIPAL ---
col1, col2 = st.columns([1, 4])

with col1:
    ejecutar = st.button("🚀 Iniciar Rastreo Global", use_container_width=True)

if ejecutar:
    st.cache_data.clear()

# Control de estado de ejecución
if ejecutar or st.session_state.get('rss_corriendo', False):
    st.session_state.rss_corriendo = True
    
    with st.spinner(f"Escaneando Google News en busca de eventos de salud para {provincia_filtro}..."):
        df_noticias, error = ejecutar_rastreo_rss(KEYWORDS_IMPLICITAS, provincia_filtro, tiempo_filtro)
        
        if error:
            st.error(error)
        elif not df_noticias.empty:
            st.success(f"📍 Rastreo completado. Se localizaron {len(df_noticias)} noticias reales sobre eventos sanitarios. Use la rueda del mouse para ver todas las noticias de la tabla")
            
            # --- CONSTRUCCIÓN DEL MAPA INTERACTIVO DE ARGENTINA (CHOROPLETH MAPBOX) ---
            geojson = load_geojson_local()
            
            if geojson:
                df_conteo = df_noticias.groupby('provincia').size().reset_index(name='Noticias')
                
                df_mapa_completo = pd.DataFrame([
                    {"provincia": name, "id_geo": code, "Noticias": 0} 
                    for name, code in MAPA_PROVINCIAS_IDS.items()
                ])
                
                df_mapa_completo = pd.merge(df_mapa_completo.drop(columns=['Noticias']), df_conteo, on='provincia', how='left').fillna(0)
                df_mapa_completo['Noticias'] = df_mapa_completo['Noticias'].astype(int)
                
                st.markdown("#### 🗺️ Distribución de Alertas por Jurisdicción (Haz clic en una provincia para filtrar la tabla)")
                
                fig = px.choropleth_mapbox(
                    df_mapa_completo,
                    geojson=geojson,
                    locations='id_geo',
                    featureidkey="properties.in1",
                    color='Noticias',
                    hover_name='provincia',
                    mapbox_style="white-bg",
                    color_continuous_scale="Reds",
                    opacity=0.7,
                    labels={'Noticias': 'Alertas Detectadas'}
                )
                
                if provincia_filtro == "Toda Argentina":
                    center_coords = {"lat": -38.4161, "lon": -63.6167}
                    zoom_level = 2.7
                else:
                    coords = PROVINCIA_COORDENADAS.get(provincia_filtro, {"lat": -38.4161, "lon": -63.6167, "zoom": 3.4})
                    center_coords = {"lat": coords["lat"], "lon": coords["lon"]}
                    zoom_level = coords["zoom"]
                
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
                    ],
                    margin={"r":0,"t":0,"l":0,"b":0},
                    height=450,
                    mapbox={"center": center_coords, "zoom": zoom_level}
                )
                
                # Renderizador del gráfico interactivo con detección de eventos on_select
                seleccion_mapa = st.plotly_chart(
                    fig, 
                    use_container_width=True, 
                    on_select="rerun", 
                    key="mapa_epirumores_interactivo"
                )
                
                # NOTA: El procesamiento del clic ya se maneja de manera segura al inicio de este script 
                # para evitar violar el ciclo de vida de los widgets de Streamlit.
            
            # --- TABLA Y CONTROLES DE DESCARGA ---
            st.markdown("#### 📰 Reporte Consolidado de Alertas Detectadas")
            
            if not df_noticias.empty:
                csv = df_noticias.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 Descargar Reporte en CSV ({len(df_noticias)} registros)",
                    data=csv,
                    file_name=f'epirumores_{provincia_filtro.lower().replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.csv',
                    mime='text/csv',
                )
                
                st.dataframe(
                    df_noticias,
                    column_config={
                        "enlace": st.column_config.LinkColumn("Leer Noticia Completa", help="Clic para dirigirse al diario oficial emisor"),
                        "titulo": st.column_config.TextColumn("Titular de la Alerta", width="large"),
                        "medio": st.column_config.TextColumn("Diario Emisor"),
                        "fecha": st.column_config.TextColumn("Fecha"),
                        "provincia": st.column_config.TextColumn("Jurisdicción Detectada")
                    },
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.warning("No se registraron noticias asociadas a los criterios en este rango de tiempo.")
        else:
            st.info(f"El motor RSS finalizó el escaneo en Google News pero no encontró publicaciones sobre brotes para la región '{provincia_filtro}' con los filtros de tiempo seleccionados.")