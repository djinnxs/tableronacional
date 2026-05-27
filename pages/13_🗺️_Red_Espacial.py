# -*- coding: utf-8 -*-
"""
13_🗺️_Red_Espacial.py
======================
Módulo de Análisis de Redes de Transmisión Espacial.

Trata a provincias/departamentos como NODOS de una red de transmisión.
Un brote en el nodo A tiene probabilidad de impactar al nodo B según su
correlación histórica y contigüidad geográfica.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import json
from scipy.stats import pearsonr
import datetime

try:
    import networkx as nx
    NETWORKX_OK = True
except ImportError:
    NETWORKX_OK = False

try:
    import geopandas as gpd
    from shapely.geometry import shape
    GEOPANDAS_OK = True
except ImportError:
    GEOPANDAS_OK = False

from utils import get_epi_week_data


st.set_page_config(page_title="Red Espacial SNVS", page_icon="🗺️", layout="wide")

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');
html,body,[class*="css"]{font-family:'Rajdhani',sans-serif}
.stApp{background:#060a12;color:#c8d8e8}
h1,h2,h3{font-family:'Share Tech Mono',monospace!important;color:#00e5ff!important}
.m-card{background:linear-gradient(135deg,#0d1b2a,#112233);border:1px solid #1a3a5c;border-radius:8px;
  padding:16px;text-align:center;transition:all .3s}
.m-card:hover{border-color:#00e5ff;box-shadow:0 4px 20px #00e5ff22;transform:translateY(-2px)}
.m-num{font-size:2rem;font-weight:700;color:#00e5ff;font-family:'Share Tech Mono',monospace}
.m-lbl{font-size:.72rem;color:#4a8ab5;font-family:'Share Tech Mono',monospace;letter-spacing:.08em;margin-top:4px}
.info-box{background:linear-gradient(135deg,#0a1628,#0d2040);border:1px solid #00e5ff22;
  border-left:4px solid #00e5ff;border-radius:6px;padding:14px;color:#8ecae6;
  font-family:'Share Tech Mono',monospace;font-size:.8rem;margin:8px 0}
.alert-red{background:linear-gradient(135deg,#1a0a0a,#2a0a0a);border:1px solid #ef444444;
  border-left:4px solid #ef4444;border-radius:6px;padding:14px;color:#fca5a5;
  font-family:'Share Tech Mono',monospace;font-size:.82rem;margin:8px 0}
.alert-yellow{background:linear-gradient(135deg,#1a1200,#2a1c00);border:1px solid #f59e0b44;
  border-left:4px solid #f59e0b;border-radius:6px;padding:14px;color:#fde68a;
  font-family:'Share Tech Mono',monospace;font-size:.82rem;margin:8px 0}
.alert-green{background:linear-gradient(135deg,#0a1a0a,#0f2a0f);border:1px solid #4ade8044;
  border-left:4px solid #4ade80;border-radius:6px;padding:14px;color:#bbf7d0;
  font-family:'Share Tech Mono',monospace;font-size:.82rem;margin:8px 0}
.stTabs [data-baseweb="tab"]{background:#0d1b2a;border-radius:4px;padding:8px 16px;
  font-family:'Share Tech Mono',monospace;color:#8ecae6}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#023e8a,#0077b6)!important;color:#00e5ff!important}
hr{border-color:#1a3a5c!important}
</style>""", unsafe_allow_html=True)

# ─── HEADER ────────────────────────────────────────────────────────────────────
sem_hoy, anio_hoy = get_epi_week_data(datetime.date.today())
st.markdown(f"""
<div style="border-bottom:2px solid #00e5ff22;padding-bottom:16px;margin-bottom:20px">
  <h1 style="margin:0;font-size:1.9rem;letter-spacing:.06em">🗺️ RED ESPACIAL DE TRANSMISIÓN — SNVS</h1>
  <p style="color:#4a8ab5;font-family:'Share Tech Mono',monospace;font-size:.78rem;margin:4px 0 0">
    SE: <span style="color:#ef4444;font-weight:700">{sem_hoy}</span>/{anio_hoy} &nbsp;·&nbsp;
    Provincias como nodos · Correlación espacial · Moran's I · Difusión en red
  </p>
</div>""", unsafe_allow_html=True)

if not NETWORKX_OK:
    st.error("❌ `networkx` no está instalado. Ejecutá: `pip install networkx` en el entorno.")
    st.stop()

st.markdown("""<div class="info-box">
🌐 Este módulo trata a cada provincia como un <strong>nodo</strong> de una red de transmisión.
Las <strong>aristas</strong> representan correlaciones temporales históricas entre pares de provincias.
Un brote en el nodo A impacta al nodo B según el peso de su arista.<br>
<strong>Metodologías:</strong> Grafo de contigüidad · Correlación con lag espacial ·
Índice de Moran (autocorrelación espacial) · Centralidad de Betweenness · Simulación de difusión.
</div>""", unsafe_allow_html=True)

# ─── CARGA ─────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    return pd.read_parquet('data/base_nacional.parquet')

@st.cache_data
def load_geojson_prov():
    with open('data/provincia.json', 'r', encoding='utf-8') as f:
        return json.load(f)

df_full = load_data()
geojson = load_geojson_prov()
eventos_list = sorted(df_full['Evento'].dropna().unique().tolist())
provincias_list = sorted([p for p in df_full['Provincia'].unique() if p != 'Sin Datos'])

# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("### 🗺️ Configuración de Red")
evento_sel = st.sidebar.selectbox("Evento", eventos_list, key="q13_ev")
anio_min, anio_max = int(df_full['ANIO'].min()), int(df_full['ANIO'].max())
rango_anios = st.sidebar.slider("Período", anio_min, anio_max, (anio_min, anio_max), key="q13_anios")
umbral_correlacion = st.sidebar.slider("Umbral mínimo |r| para arista", 0.2, 0.9, 0.4, 0.05, key="q13_r")
max_lag_spatial = st.sidebar.slider("Lag espacial máximo (semanas)", 1, 8, 4, key="q13_lag")

# ─── COORDENADAS DE PROVINCIAS (para posicionamiento del grafo) ─────────────────
PROV_COORDS = {
    "Buenos Aires": (-36.6, -60.3), "CABA": (-34.6, -58.4),
    "Catamarca": (-28.5, -66.8), "Chaco": (-27.0, -60.7),
    "Chubut": (-43.0, -68.0), "Córdoba": (-32.4, -64.2),
    "Corrientes": (-28.6, -57.5), "Entre Ríos": (-32.0, -59.3),
    "Formosa": (-24.5, -59.9), "Jujuy": (-23.3, -65.7),
    "La Pampa": (-36.5, -65.8), "La Rioja": (-29.5, -67.3),
    "Mendoza": (-34.4, -68.6), "Misiones": (-26.7, -54.8),
    "Neuquén": (-38.5, -70.1), "Río Negro": (-39.8, -67.2),
    "Salta": (-23.8, -65.4), "San Juan": (-30.5, -68.5),
    "San Luis": (-33.9, -66.3), "Santa Cruz": (-49.0, -69.5),
    "Santa Fe": (-31.1, -60.7), "Santiago del Estero": (-27.8, -63.4),
    "Tierra del Fuego": (-53.8, -66.7), "Tucumán": (-26.8, -65.3),
}

# ─── FUNCIONES ─────────────────────────────────────────────────────────────────
@st.cache_data
def build_province_series(evento, anios_range):
    """Construye una serie semanal por provincia."""
    df = df_full[
        (df_full['Evento'] == evento) &
        (df_full['ANIO'] >= anios_range[0]) &
        (df_full['ANIO'] <= anios_range[1]) &
        (df_full['Provincia'] != 'Sin Datos')
    ]
    pivot = df.groupby(['Provincia', 'ANIO', 'SEMANA'])['CANTIDAD'].sum().reset_index()
    return pivot


def build_correlation_matrix(pivot, lag=0):
    """Construye matriz de correlación entre provincias, con lag opcional."""
    provs = sorted(pivot['Provincia'].unique().tolist())
    # Crear series semanales por provincia
    series_dict = {}
    for prov in provs:
        s = pivot[pivot['Provincia'] == prov].sort_values(['ANIO', 'SEMANA'])['CANTIDAD'].values
        series_dict[prov] = s

    corr_matrix = pd.DataFrame(np.nan, index=provs, columns=provs)
    for i, p1 in enumerate(provs):
        for j, p2 in enumerate(provs):
            if i >= j:
                continue
            s1 = series_dict[p1]
            s2 = series_dict[p2]
            n = min(len(s1), len(s2))
            if n < 20:
                continue
            if lag == 0:
                a, b = s1[:n], s2[:n]
            elif lag > 0:
                a, b = s1[:n-lag], s2[lag:n]
            else:
                a, b = s1[-lag:n], s2[:n+lag]
            if np.std(a) > 0 and np.std(b) > 0:
                r, p = pearsonr(a, b)
                if not np.isnan(r):
                    corr_matrix.at[p1, p2] = r
                    corr_matrix.at[p2, p1] = r
    return corr_matrix


def moran_global(values_dict, corr_matrix):
    """Calcula el Índice de Moran Global (I)."""
    provs = list(values_dict.keys())
    n = len(provs)
    if n < 3:
        return None, None

    y = np.array([values_dict.get(p, 0) for p in provs], dtype=float)
    y_mean = y.mean()
    z = y - y_mean

    # Matriz de pesos (correlaciones positivas significativas)
    W = np.zeros((n, n))
    for i, p1 in enumerate(provs):
        for j, p2 in enumerate(provs):
            if i != j:
                r = corr_matrix.at[p1, p2] if p1 in corr_matrix.index and p2 in corr_matrix.columns else np.nan
                if not np.isnan(r) and r > 0.3:
                    W[i, j] = r

    # Normalizar filas
    row_sums = W.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    W = W / row_sums

    S0 = W.sum()
    if S0 == 0:
        return 0.0, 1.0

    I = (n / S0) * (z @ W @ z) / (z @ z + 1e-10)
    E_I = -1 / (n - 1)  # Valor esperado bajo H0

    return float(I), float(E_I)


def lisa_scores(values_dict, corr_matrix):
    """Calcula LISA (Local Indicator of Spatial Association) por provincia."""
    provs = list(values_dict.keys())
    n = len(provs)
    y = np.array([values_dict.get(p, 0) for p in provs], dtype=float)
    y_std = (y - y.mean()) / (y.std() + 1e-10)

    lisa = {}
    for i, p1 in enumerate(provs):
        z_i = y_std[i]
        wz_sum = 0.0
        w_sum = 0.0
        for j, p2 in enumerate(provs):
            if i == j:
                continue
            r = corr_matrix.at[p1, p2] if p1 in corr_matrix.index and p2 in corr_matrix.columns else np.nan
            if not np.isnan(r) and r > 0.1:
                wz_sum += r * y_std[j]
                w_sum += r
        lag_zi = wz_sum / (w_sum + 1e-10)
        li = z_i * lag_zi

        tipo = (
            "HH" if z_i > 0 and lag_zi > 0 else  # Alto rodeado de alto
            "LL" if z_i < 0 and lag_zi < 0 else  # Bajo rodeado de bajo
            "HL" if z_i > 0 and lag_zi < 0 else  # Alto rodeado de bajo (outlier)
            "LH"  # Bajo rodeado de alto (outlier)
        )
        lisa[p1] = {'LISA': li, 'Tipo': tipo, 'z_i': z_i, 'lag_z': lag_zi}
    return lisa


# ─── CONSTRUIR DATOS ───────────────────────────────────────────────────────────
pivot_data = build_province_series(evento_sel, rango_anios)

# ─── MÉTRICAS ──────────────────────────────────────────────────────────────────
total_casos = int(pivot_data['CANTIDAD'].sum())
provs_activas = pivot_data[pivot_data['CANTIDAD'] > 0]['Provincia'].nunique()
años_datos = pivot_data['ANIO'].nunique()

c1, c2, c3 = st.columns(3)
for col, val, lbl in [
    (c1, f"{total_casos:,}".replace(",", "."), "CASOS TOTALES"),
    (c2, str(provs_activas), "PROVINCIAS ACTIVAS"),
    (c3, str(años_datos), "AÑOS DE DATOS"),
]:
    col.markdown(f'<div class="m-card"><div class="m-num">{val}</div><div class="m-lbl">{lbl}</div></div>',
                 unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── TABS ──────────────────────────────────────────────────────────────────────
tab_red, tab_lag, tab_moran, tab_central, tab_difusion = st.tabs([
    "🕸️ GRAFO DE RED", "⏱️ LAG ESPACIAL", "📐 MORAN & LISA",
    "🎯 CENTRALIDAD", "🌊 DIFUSIÓN"
])

# ══════════════════════════════════════════════════
# TAB 1: GRAFO INTERACTIVO
# ══════════════════════════════════════════════════
with tab_red:
    st.subheader("🕸️ Grafo de Red de Correlación Interprovincial")
    st.markdown(f"""<div class="info-box">
    Cada <strong>nodo</strong> = provincia. Cada <strong>arista</strong> = correlación temporal |r| &gt; {umbral_correlacion}
    entre las series semanales de casos.<br>
    Grosor de arista = fuerza de correlación. Color del nodo = total de casos (rojo = más casos).
    Nodos sin conexiones: su dinámica es independiente de las demás jurisdicciones.
    </div>""", unsafe_allow_html=True)

    lag_red = st.select_slider("Lag para correlación del grafo (semanas)",
                                options=list(range(0, max_lag_spatial + 1)),
                                value=0, key="q13_lag_red")

    with st.spinner("Calculando matriz de correlación..."):
        corr_mat = build_correlation_matrix(pivot_data, lag=lag_red)

    # Construir grafo networkx
    G = nx.Graph()
    casos_por_prov = pivot_data.groupby('Provincia')['CANTIDAD'].sum().to_dict()

    for prov in provincias_list:
        if prov in PROV_COORDS:
            G.add_node(prov, casos=casos_por_prov.get(prov, 0))

    aristas_add = []
    for p1 in provincias_list:
        for p2 in provincias_list:
            if p1 >= p2:
                continue
            if p1 in corr_mat.index and p2 in corr_mat.columns:
                r = corr_mat.at[p1, p2]
                if not np.isnan(r) and abs(r) >= umbral_correlacion:
                    G.add_edge(p1, p2, weight=abs(r), r=r)
                    aristas_add.append((p1, p2, r))

    # Plotly graph
    node_x, node_y, node_color, node_size, node_text = [], [], [], [], []
    for node in G.nodes():
        lat, lon = PROV_COORDS.get(node, (-38, -65))
        node_x.append(lon)
        node_y.append(lat)
        node_color.append(G.nodes[node].get('casos', 0))
        node_size.append(max(8, min(30, G.nodes[node].get('casos', 0) ** 0.3 * 3)))
        deg = G.degree(node)
        node_text.append(f"<b>{node}</b><br>Casos: {G.nodes[node].get('casos',0):,}<br>Conexiones: {deg}".replace(",", "."))

    # Aristas
    edge_traces = []
    for p1, p2, r in aristas_add:
        lat1, lon1 = PROV_COORDS.get(p1, (-38, -65))
        lat2, lon2 = PROV_COORDS.get(p2, (-38, -65))
        color_edge = f'rgba(0,229,255,{min(0.9, abs(r)):.2f})' if r > 0 else f'rgba(239,68,68,{min(0.9, abs(r)):.2f})'
        edge_traces.append(go.Scatter(
            x=[lon1, lon2, None], y=[lat1, lat2, None],
            mode='lines',
            line=dict(width=max(0.5, abs(r) * 4), color=color_edge),
            hoverinfo='none', showlegend=False
        ))

    fig_g = go.Figure(edge_traces)
    fig_g.add_trace(go.Scatter(
        x=node_x, y=node_y, mode='markers+text',
        marker=dict(size=node_size, color=node_color, colorscale='YlOrRd',
                    showscale=True, colorbar=dict(title='Casos', tickfont=dict(color='#c8d8e8')),
                    line=dict(color='#00e5ff', width=1)),
        text=[n.replace("Santiago del Estero", "Stgo.E.").replace("Buenos Aires", "Bs.As.")
              .replace("Tierra del Fuego", "TDF").replace("Entre Ríos", "E.Ríos") for n in G.nodes()],
        textposition='top center', textfont=dict(color='#c8d8e8', size=9),
        hovertext=node_text, hoverinfo='text', name='Provincias'
    ))
    fig_g.update_layout(
        paper_bgcolor='#060a12', plot_bgcolor='#060a12',
        font=dict(color='#c8d8e8', family='Share Tech Mono'), height=560,
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-75, -52]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-57, -20]),
        title=dict(text=f"Red de transmisión — {evento_sel} (lag={lag_red} sem, |r|≥{umbral_correlacion})",
                   font=dict(color='#00e5ff')),
        margin=dict(l=10, r=10, t=50, b=10)
    )
    st.plotly_chart(fig_g, use_container_width=True)

    n_aristas = G.number_of_edges()
    n_nodos = G.number_of_nodes()
    densidad = nx.density(G) if n_nodos > 1 else 0
    st.markdown(f"""<div class="info-box">
    📊 <strong>Estadísticas del grafo:</strong> {n_nodos} nodos · {n_aristas} aristas ·
    Densidad: {densidad:.3f} (0=sin conexiones, 1=todos conectados).<br>
    {"Alta densidad → el evento se mueve en red generalizada. Difícil contener con intervención puntual." if densidad > 0.3 else "Baja densidad → dinámicas provinciales en gran parte independientes. Posible intervención focal efectiva."}
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# TAB 2: LAG ESPACIAL
# ══════════════════════════════════════════════════
with tab_lag:
    st.subheader("⏱️ Correlación Espacial con Lag — ¿Quién precede a quién?")
    st.markdown("""<div class="info-box">
    Para cada par de provincias, calcula la correlación con diferentes lags temporales.
    El lag óptimo indica cuántas semanas después de un pico en la <strong>Provincia A</strong>
    se espera un pico en la <strong>Provincia B</strong>.
    Esta es una aproximación a la <strong>velocidad de difusión espacial</strong> del evento.
    </div>""", unsafe_allow_html=True)

    prov_origen = st.selectbox("Provincia origen (A)", provincias_list, key="q13_origen")
    prov_destino = st.selectbox("Provincia destino (B)",
                                 [p for p in provincias_list if p != prov_origen],
                                 key="q13_destino")

    s_a = pivot_data[pivot_data['Provincia'] == prov_origen].sort_values(
        ['ANIO', 'SEMANA'])['CANTIDAD'].values
    s_b = pivot_data[pivot_data['Provincia'] == prov_destino].sort_values(
        ['ANIO', 'SEMANA'])['CANTIDAD'].values
    n = min(len(s_a), len(s_b))

    if n >= 20:
        lags_range = range(-max_lag_spatial, max_lag_spatial + 1)
        ccf_vals = []
        sig_thresh = 2 / np.sqrt(n)
        for lag in lags_range:
            if lag < 0:
                a_s, b_s = s_a[:lag], s_b[-lag:]
            elif lag > 0:
                a_s, b_s = s_a[lag:], s_b[:-lag]
            else:
                a_s, b_s = s_a[:n], s_b[:n]
            if len(a_s) > 5 and np.std(a_s) > 0 and np.std(b_s) > 0:
                r, _ = pearsonr(a_s[:min(len(a_s), len(b_s))], b_s[:min(len(a_s), len(b_s))])
                ccf_vals.append(r if not np.isnan(r) else 0)
            else:
                ccf_vals.append(0)

        ccf_df = pd.DataFrame({'lag': list(lags_range), 'ccf': ccf_vals})
        best = ccf_df.loc[ccf_df['ccf'].abs().idxmax()]
        colors_bar = ['#ef4444' if abs(r) > sig_thresh else '#1a3a5c' for r in ccf_vals]

        fig_lag = go.Figure(go.Bar(
            x=ccf_df['lag'], y=ccf_df['ccf'], marker_color=colors_bar,
            hovertemplate='Lag: %{x} sem<br>r: %{y:.3f}<extra></extra>'
        ))
        fig_lag.add_hline(y=sig_thresh, line_dash="dash", line_color="#f59e0b",
                           annotation_text=f"+sig ({sig_thresh:.3f})", annotation_font_color="#f59e0b")
        fig_lag.add_hline(y=-sig_thresh, line_dash="dash", line_color="#f59e0b",
                           annotation_text=f"-sig", annotation_font_color="#f59e0b")
        fig_lag.add_vline(x=0, line_color="rgba(255,255,255,0.27)")
        fig_lag.update_layout(
            paper_bgcolor='#060a12', plot_bgcolor='#060a12',
            font=dict(color='#c8d8e8', family='Share Tech Mono'), height=380,
            xaxis=dict(title=f'Lag (sem) — positivo: {prov_origen} precede a {prov_destino}',
                       tickfont=dict(color='#c8d8e8'), dtick=1, gridcolor='#1a3a5c'),
            yaxis=dict(title='r de correlación', tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c'),
            title=dict(text=f"CCF Espacial: {prov_origen} → {prov_destino}", font=dict(color='#00e5ff'))
        )
        st.plotly_chart(fig_lag, use_container_width=True)

        lag_v, r_v = int(best['lag']), float(best['ccf'])
        if abs(r_v) > sig_thresh:
            if lag_v > 0:
                interp = f"**{prov_origen}** anticipa a **{prov_destino}** en {lag_v} semana(s) (r={r_v:.3f})"
                recom = f"Si detectás un brote en {prov_origen}, activá vigilancia activa en {prov_destino} con anticipación de {lag_v} semanas."
            elif lag_v < 0:
                interp = f"**{prov_destino}** anticipa a **{prov_origen}** en {abs(lag_v)} semana(s) (r={r_v:.3f})"
                recom = f"Si detectás un brote en {prov_destino}, activá alerta en {prov_origen} con {abs(lag_v)} semanas de ventana."
            else:
                interp = f"Movimiento sincrónico (lag=0, r={r_v:.3f}) — misma dinámica temporal."
                recom = "Ambas provincias responden simultáneamente. Posible factor común (ej. vector compartido, evento climático regional)."
            st.markdown(f'<div class="alert-yellow">🔍 <strong>{interp}</strong><br>💡 Implicación operativa: {recom}</div>',
                        unsafe_allow_html=True)

        # Resumen de todos los lags óptimos desde el origen
        st.markdown(f"#### 🗺️ Lags óptimos desde {prov_origen} hacia todas las provincias")
        lag_summary = []
        for prov_b in provincias_list:
            if prov_b == prov_origen:
                continue
            s_b2 = pivot_data[pivot_data['Provincia'] == prov_b].sort_values(
                ['ANIO', 'SEMANA'])['CANTIDAD'].values
            n2 = min(len(s_a), len(s_b2))
            if n2 < 20:
                continue
            best_r, best_lag_v = 0, 0
            for lag in range(-max_lag_spatial, max_lag_spatial + 1):
                if lag < 0:
                    ax, bx = s_a[:lag], s_b2[-lag:]
                elif lag > 0:
                    ax, bx = s_a[lag:], s_b2[:-lag]
                else:
                    ax, bx = s_a[:n2], s_b2[:n2]
                mn = min(len(ax), len(bx))
                if mn > 5 and np.std(ax[:mn]) > 0 and np.std(bx[:mn]) > 0:
                    r, _ = pearsonr(ax[:mn], bx[:mn])
                    if not np.isnan(r) and abs(r) > abs(best_r):
                        best_r, best_lag_v = r, lag
            if abs(best_r) > sig_thresh:
                lag_summary.append({
                    'Provincia destino': prov_b,
                    'Lag óptimo (sem)': best_lag_v,
                    'r': round(best_r, 3),
                    'Dirección': f'{prov_origen} → {prov_b}' if best_lag_v > 0 else f'{prov_b} → {prov_origen}' if best_lag_v < 0 else 'Sincrónico',
                    'Significativo': '✅' if abs(best_r) > sig_thresh else '❌'
                })
        if lag_summary:
            df_lag_sum = pd.DataFrame(lag_summary).sort_values('r', key=abs, ascending=False)
            st.dataframe(df_lag_sum, use_container_width=True, hide_index=True)
    else:
        st.warning("Datos insuficientes para el análisis de lag espacial (mínimo 20 semanas por provincia).")

# ══════════════════════════════════════════════════
# TAB 3: MORAN & LISA
# ══════════════════════════════════════════════════
with tab_moran:
    st.subheader("📐 Índice de Moran Global y LISA por Provincia")
    st.markdown("""<div class="info-box">
    <strong>Moran's I Global:</strong> detecta si hay autocorrelación espacial general (las provincias
    con muchos casos tienden a estar cerca de otras con muchos casos).<br>
    <strong>LISA (Local):</strong> clasifica cada provincia en:<br>
    🔴 <strong>HH</strong>: Alto rodeado de alto (cluster de alta incidencia).<br>
    🟢 <strong>LL</strong>: Bajo rodeado de bajo (cluster de baja incidencia).<br>
    🟡 <strong>HL</strong>: Alto rodeado de bajo (outlier — brote aislado).<br>
    🔵 <strong>LH</strong>: Bajo rodeado de alto (zona sana en entorno de riesgo).
    </div>""", unsafe_allow_html=True)

    anio_moran = st.selectbox("Año para análisis Moran",
                               sorted(pivot_data['ANIO'].unique(), reverse=True), key="q13_moran_anio")

    with st.spinner("Calculando correlaciones y Moran..."):
        corr_mat_moran = build_correlation_matrix(pivot_data, lag=0)

    casos_anio = pivot_data[pivot_data['ANIO'] == anio_moran].groupby('Provincia')['CANTIDAD'].sum()
    casos_dict = casos_anio.to_dict()

    I_global, E_I = moran_global(casos_dict, corr_mat_moran)

    if I_global is not None:
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.markdown(f'<div class="m-card"><div class="m-num">{I_global:.3f}</div><div class="m-lbl">Moran\'s I Global</div></div>', unsafe_allow_html=True)
        col_m2.markdown(f'<div class="m-card"><div class="m-num">{E_I:.3f}</div><div class="m-lbl">I Esperado (H₀)</div></div>', unsafe_allow_html=True)
        interpretacion = "Clustering positivo" if I_global > E_I + 0.1 else "Dispersión" if I_global < E_I - 0.1 else "Sin patrón espacial"
        col_m3.markdown(f'<div class="m-card"><div class="m-num" style="font-size:1.2rem">{interpretacion}</div><div class="m-lbl">INTERPRETACIÓN</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        if I_global > E_I + 0.1:
            st.markdown(f"""<div class="alert-red">
            🔴 <strong>Autocorrelación espacial positiva (I={I_global:.3f}):</strong>
            Las provincias con alta incidencia tienden a estar rodeadas por otras de alta incidencia.
            Patrón de <strong>clustering geográfico</strong> — la enfermedad no se distribuye aleatoriamente en el territorio.
            Hipótesis: gradiente de riesgo ambiental o social compartido (pobreza, vector, temperatura).
            </div>""", unsafe_allow_html=True)
        elif I_global < E_I - 0.1:
            st.markdown(f"""<div class="alert-yellow">
            🟡 <strong>Dispersión espacial (I={I_global:.3f}):</strong>
            Las provincias con alta incidencia tienden a estar rodeadas por provincias de baja incidencia.
            Patrón de <strong>dispersión anti-clustering</strong>.
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="alert-green">✅ Sin patrón espacial significativo (I≈E[I]) — distribución aleatoria en el territorio para {anio_moran}.</div>', unsafe_allow_html=True)

        # LISA
        lisa_dict = lisa_scores(casos_dict, corr_mat_moran)
        lisa_rows = []
        for prov, vals in lisa_dict.items():
            tipo_color = {
                'HH': '#ef4444', 'LL': '#4ade80',
                'HL': '#f59e0b', 'LH': '#3b82f6'
            }
            lisa_rows.append({
                'Provincia': prov,
                'LISA': round(vals['LISA'], 3),
                'Tipo': vals['Tipo'],
                'Z local': round(vals['z_i'], 3),
                'Lag espacial Z': round(vals['lag_z'], 3),
                'Clasificación': {
                    'HH': '🔴 Alto-Alto (cluster riesgo)',
                    'LL': '🟢 Bajo-Bajo (cluster seguro)',
                    'HL': '🟡 Outlier: alto-bajo',
                    'LH': '🔵 Outlier: bajo-alto'
                }.get(vals['Tipo'], '—')
            })
        df_lisa = pd.DataFrame(lisa_rows).sort_values('LISA', ascending=False, key=abs)

        # Mapa LISA
        tipo_colores = {'HH': '#ef4444', 'LL': '#4ade80', 'HL': '#f59e0b', 'LH': '#3b82f6'}
        lisa_plot = df_lisa.copy()
        lisa_plot['lat'] = lisa_plot['Provincia'].map(lambda p: PROV_COORDS.get(p, (-38, -65))[0])
        lisa_plot['lon'] = lisa_plot['Provincia'].map(lambda p: PROV_COORDS.get(p, (-38, -65))[1])
        lisa_plot['Color'] = lisa_plot['Tipo'].map(tipo_colores)
        lisa_plot['size'] = lisa_plot['LISA'].abs().clip(0.01, 5) * 8

        fig_lisa = go.Figure()
        for tipo, color in tipo_colores.items():
            sub = lisa_plot[lisa_plot['Tipo'] == tipo]
            if sub.empty:
                continue
            fig_lisa.add_trace(go.Scatter(
                x=sub['lon'], y=sub['lat'], mode='markers+text',
                marker=dict(size=sub['size'].clip(8, 28), color=color,
                            line=dict(color='rgba(255,255,255,0.33)', width=1)),
                text=sub['Provincia'].str[:8],
                textposition='top center', textfont=dict(color='#c8d8e8', size=8),
                hovertext=[f"{r['Provincia']}<br>Tipo: {r['Tipo']}<br>LISA: {r['LISA']:.3f}"
                           for _, r in sub.iterrows()],
                hoverinfo='text', name=f"{tipo}: {{'HH':'Alto-Alto','LL':'Bajo-Bajo','HL':'Alto-Bajo','LH':'Bajo-Alto'}}.get(tipo,tipo)"
            ))
        fig_lisa.update_layout(
            paper_bgcolor='#060a12', plot_bgcolor='#060a12',
            font=dict(color='#c8d8e8', family='Share Tech Mono'), height=500,
            showlegend=True,
            legend=dict(bgcolor='rgba(6,10,18,0.85)', font=dict(color='#c8d8e8')),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-75, -52]),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-57, -20]),
            title=dict(text=f"Mapa LISA — {evento_sel} ({anio_moran}) · 🔴HH 🟢LL 🟡HL 🔵LH",
                       font=dict(color='#00e5ff'))
        )
        st.plotly_chart(fig_lisa, use_container_width=True)
        st.dataframe(df_lisa, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════
# TAB 4: CENTRALIDAD
# ══════════════════════════════════════════════════
with tab_central:
    st.subheader("🎯 Centralidad de Red — Nodos Críticos de Transmisión")
    st.markdown("""<div class="info-box">
    La <strong>centralidad de betweenness</strong> identifica las provincias que actúan como
    "puentes" de transmisión: si se intervienen, se maximiza el corte de la cadena epidémica.
    Son los nodos de mayor eficiencia para la contención.<br>
    La <strong>centralidad de grado</strong> indica cuántas provincias están directamente correlacionadas.
    </div>""", unsafe_allow_html=True)

    with st.spinner("Calculando métricas de centralidad..."):
        corr_mat_c = build_correlation_matrix(pivot_data, lag=0)
        G_c = nx.Graph()
        for prov in provincias_list:
            if prov in PROV_COORDS:
                G_c.add_node(prov, casos=casos_por_prov.get(prov, 0))
        for p1 in provincias_list:
            for p2 in provincias_list:
                if p1 >= p2:
                    continue
                if p1 in corr_mat_c.index and p2 in corr_mat_c.columns:
                    r = corr_mat_c.at[p1, p2]
                    if not np.isnan(r) and abs(r) >= umbral_correlacion:
                        G_c.add_edge(p1, p2, weight=abs(r))

        if G_c.number_of_edges() > 0:
            betweenness = nx.betweenness_centrality(G_c, weight='weight', normalized=True)
            degree_c = dict(G_c.degree())
            closeness = nx.closeness_centrality(G_c)
        else:
            betweenness = {p: 0 for p in G_c.nodes()}
            degree_c = {p: 0 for p in G_c.nodes()}
            closeness = {p: 0 for p in G_c.nodes()}

    central_df = pd.DataFrame({
        'Provincia': list(G_c.nodes()),
        'Betweenness (puente)': [betweenness.get(p, 0) for p in G_c.nodes()],
        'Grado (conexiones)': [degree_c.get(p, 0) for p in G_c.nodes()],
        'Closeness (cercanía)': [closeness.get(p, 0) for p in G_c.nodes()],
        'Casos totales': [G_c.nodes[p].get('casos', 0) for p in G_c.nodes()],
    }).sort_values('Betweenness (puente)', ascending=False).reset_index(drop=True)
    central_df['Rol en la red'] = central_df.apply(
        lambda r: '🔴 Puente crítico' if r['Betweenness (puente)'] > 0.3 else
                  '🟡 Conector importante' if r['Betweenness (puente)'] > 0.1 else
                  '🟢 Nodo periférico', axis=1
    )

    fig_cent = go.Figure()
    fig_cent.add_trace(go.Bar(
        x=central_df['Provincia'], y=central_df['Betweenness (puente)'],
        marker=dict(color=central_df['Betweenness (puente)'], colorscale='YlOrRd',
                    showscale=True, colorbar=dict(title='Betweenness', tickfont=dict(color='#c8d8e8'))),
        text=[f"{v:.3f}" for v in central_df['Betweenness (puente)']],
        textposition='outside',
        hovertemplate='%{x}<br>Betweenness: %{y:.3f}<extra></extra>'
    ))
    fig_cent.update_layout(
        paper_bgcolor='#060a12', plot_bgcolor='#060a12',
        font=dict(color='#c8d8e8', family='Share Tech Mono'), height=380,
        xaxis=dict(tickangle=-45, tickfont=dict(color='#c8d8e8', size=9), gridcolor='#1a3a5c'),
        yaxis=dict(title='Betweenness Centrality', tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c'),
        title=dict(text="Centralidad de Betweenness — Provincias 'puente' de transmisión",
                   font=dict(color='#00e5ff'))
    )
    st.plotly_chart(fig_cent, use_container_width=True)

    puentes = central_df[central_df['Betweenness (puente)'] > 0.1]
    if not puentes.empty:
        st.markdown(f"""<div class="alert-red">
        🎯 <strong>Nodos puente críticos para contención:</strong>
        {', '.join(puentes['Provincia'].tolist())}<br>
        Intervenir en estas provincias maximiza la ruptura de la cadena de transmisión en la red.
        Priorizarlas en recursos de vigilancia activa y respuesta rápida.
        </div>""", unsafe_allow_html=True)

    st.dataframe(central_df.round(3), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════
# TAB 5: SIMULACIÓN DE DIFUSIÓN
# ══════════════════════════════════════════════════
with tab_difusion:
    st.subheader("🌊 Simulación de Difusión en Red")
    st.markdown("""<div class="info-box">
    Dado un brote inicial en una provincia, simula la propagación hacia las demás
    usando los <strong>pesos de correlación histórica</strong> como proxy de probabilidad de difusión.<br>
    Modelo determinístico simplificado: en cada paso temporal (semana), el brote se propaga
    a provincias vecinas con fuerza proporcional al peso de la arista.<br>
    <strong>Advertencia:</strong> Esta es una aproximación exploratoria, NO un modelo SIR calibrado.
    Su valor es orientativo para priorizar vigilancia.
    </div>""", unsafe_allow_html=True)

    prov_brote = st.selectbox("Provincia origen del brote", provincias_list, key="q13_brote")
    casos_iniciales = st.number_input("Casos iniciales en el foco", 10, 10000, 100, step=10, key="q13_casos_ini")
    pasos_sim = st.slider("Semanas de simulación", 2, 24, 8, key="q13_pasos")
    tasa_difusion = st.slider("Tasa de difusión base (0-1)", 0.05, 0.5, 0.15, 0.05, key="q13_tasa")

    if st.button("▶️ EJECUTAR SIMULACIÓN", key="q13_sim_btn"):
        with st.spinner("Simulando difusión..."):
            # Construir grafo con pesos para simulación
            corr_sim = build_correlation_matrix(pivot_data, lag=0)
            G_sim = nx.Graph()
            for p in provincias_list:
                G_sim.add_node(p)
            for p1 in provincias_list:
                for p2 in provincias_list:
                    if p1 >= p2:
                        continue
                    if p1 in corr_sim.index and p2 in corr_sim.columns:
                        r = corr_sim.at[p1, p2]
                        if not np.isnan(r) and r > 0.2:
                            G_sim.add_edge(p1, p2, weight=r)

            # Estado inicial
            estado = {p: 0.0 for p in provincias_list}
            estado[prov_brote] = float(casos_iniciales)
            historia = [estado.copy()]

            for paso in range(pasos_sim):
                nuevo_estado = estado.copy()
                for p1 in G_sim.nodes():
                    if estado[p1] <= 0:
                        continue
                    for p2 in G_sim.neighbors(p1):
                        w = G_sim[p1][p2]['weight']
                        difusion = estado[p1] * w * tasa_difusion
                        nuevo_estado[p2] += difusion
                        nuevo_estado[p1] = max(0, nuevo_estado[p1] - difusion * 0.3)
                estado = nuevo_estado.copy()
                historia.append(estado.copy())

        # Visualizar evolución
        df_hist = pd.DataFrame(historia)
        df_hist.index.name = 'Semana'
        df_hist_melt = df_hist.reset_index().melt(id_vars='Semana', var_name='Provincia', value_name='Casos')

        # Seleccionar top provincias afectadas
        top_provs = df_hist.iloc[-1].sort_values(ascending=False).head(8).index.tolist()
        df_plot_sim = df_hist_melt[df_hist_melt['Provincia'].isin(top_provs)]

        palette_sim = ['#00e5ff', '#ef4444', '#4ade80', '#f59e0b', '#a78bfa', '#f472b6', '#38bdf8', '#fb923c']
        fig_sim = go.Figure()
        for i, prov in enumerate(top_provs):
            d = df_plot_sim[df_plot_sim['Provincia'] == prov]
            linestyle = dict(color=palette_sim[i % len(palette_sim)], width=3 if prov == prov_brote else 1.5,
                             dash='solid' if prov == prov_brote else 'dot')
            fig_sim.add_trace(go.Scatter(
                x=d['Semana'], y=d['Casos'], name=prov,
                line=linestyle,
                hovertemplate=f'{prov}: %{{y:.0f}} casos · Sem %{{x}}<extra></extra>'
            ))
        fig_sim.update_layout(
            paper_bgcolor='#060a12', plot_bgcolor='#060a12',
            font=dict(color='#c8d8e8', family='Share Tech Mono'), height=430,
            legend=dict(bgcolor='rgba(6,10,18,0.85)', font=dict(color='#c8d8e8')),
            xaxis=dict(title='Semana desde inicio del brote', tickfont=dict(color='#c8d8e8'),
                       gridcolor='#1a3a5c'),
            yaxis=dict(title='Casos estimados (proxy)', tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c'),
            title=dict(text=f"Difusión simulada desde {prov_brote} (tasa={tasa_difusion}, {pasos_sim} sem)",
                       font=dict(color='#00e5ff'))
        )
        st.plotly_chart(fig_sim, use_container_width=True)

        # Estado final
        final_estado = pd.DataFrame(list(estado.items()), columns=['Provincia', 'Casos estimados']).sort_values(
            'Casos estimados', ascending=False)
        final_estado['Casos estimados'] = final_estado['Casos estimados'].round(1)
        afectadas = final_estado[final_estado['Casos estimados'] > 1]

        st.markdown(f"""<div class="alert-yellow">
        🌊 <strong>Proyección a {pasos_sim} semanas:</strong> {len(afectadas)} provincias recibirían
        casos estimados &gt;1. Provincias prioritarias para vigilancia activa preventiva:<br>
        <strong>{', '.join(afectadas.head(5)['Provincia'].tolist())}</strong><br>
        ⚠️ Modelo determinístico exploratorio. Debe complementarse con modelado SIR calibrado con R₀ real.
        </div>""", unsafe_allow_html=True)
        st.dataframe(afectadas, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Exportar proyección de difusión",
            data=afectadas.to_csv(index=False).encode('utf-8'),
            file_name=f"difusion_{prov_brote.replace(' ','_')}_{evento_sel.replace(' ','_')}.csv",
            mime='text/csv'
        )
    else:
        st.info("👆 Configurá los parámetros y ejecutá la simulación.")
