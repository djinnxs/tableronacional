# -*- coding: utf-8 -*-
"""
12_🚨_Anomalías_Complejas.py
=============================
Módulo de Detección de Anomalías Complejas y Silencios Epidemiológicos.

Separa el 'ruido' (artefactos de notificación) de la 'señal' (cambios reales
en la incidencia). Implementa Farrington modificado, STL manual, IDET y
panel de alertas activas.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy.stats import norm, poisson
import datetime
from utils import get_epi_week_data

st.set_page_config(page_title="Anomalías Complejas SNVS", page_icon="🚨", layout="wide")

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
.alert-orange{background:linear-gradient(135deg,#1a0e00,#2a1600);border:1px solid #f9731644;
  border-left:4px solid #f97316;border-radius:6px;padding:14px;color:#fed7aa;
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
div.stButton>button{background:linear-gradient(90deg,#7c2d12,#9a3412);color:#fff;
  border:1px solid #f97316;border-radius:4px;font-family:'Share Tech Mono',monospace;
  padding:10px 24px;letter-spacing:.06em;transition:all .2s}
div.stButton>button:hover{box-shadow:0 0 16px #f9731644;transform:translateY(-1px)}
</style>""", unsafe_allow_html=True)

# ─── HEADER ────────────────────────────────────────────────────────────────────
sem_hoy, anio_hoy = get_epi_week_data(datetime.date.today())
st.markdown(f"""
<div style="border-bottom:2px solid #ef444422;padding-bottom:16px;margin-bottom:20px">
  <h1 style="margin:0;font-size:1.9rem;letter-spacing:.06em">🚨 DETECCIÓN DE ANOMALÍAS COMPLEJAS — SNVS</h1>
  <p style="color:#4a8ab5;font-family:'Share Tech Mono',monospace;font-size:.78rem;margin:4px 0 0">
    SE: <span style="color:#ef4444;font-weight:700">{sem_hoy}</span>/{anio_hoy} &nbsp;·&nbsp;
    Separando ruido epidemiológico de señal real · Farrington · STL · IDET
  </p>
</div>""", unsafe_allow_html=True)

st.markdown("""<div class="info-box">
🎯 <strong>Objetivo:</strong> Separar el "ruido" (artefactos del sistema de notificación SNVS) de la
"señal" (cambios reales en la incidencia). Una anomalía solo es clínicamente relevante si sobrevive
a la descomposición estacional y no coincide con cambios conocidos en el sistema de vigilancia.
<br><strong>Métodos:</strong> Algoritmo de Farrington Modificado · Descomposición STL (manual) · 
Índice de Dispersión Espacio-Temporal (IDET) · Panel de Alertas Activas.
</div>""", unsafe_allow_html=True)

# ─── CARGA ─────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    return pd.read_parquet('data/base_nacional.parquet')

df_full = load_data()
eventos_list = sorted(df_full['Evento'].dropna().unique().tolist())
provincias_list = sorted([p for p in df_full['Provincia'].unique() if p != 'Sin Datos'])

# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("### 🚨 Configuración de Detección")
evento_sel = st.sidebar.selectbox("Evento a analizar", eventos_list, key="q12_ev")
nivel_geo = st.sidebar.selectbox("Geografía", ["Nacional"] + provincias_list, key="q12_geo")
anio_min, anio_max = int(df_full['ANIO'].min()), int(df_full['ANIO'].max())
rango_anios = st.sidebar.slider("Período histórico", anio_min, anio_max,
                                 (anio_min, anio_max), key="q12_anios")
n_anios_hist = st.sidebar.slider("Años de baseline Farrington", 2, 6, 5, key="q12_hist")
percentil_alerta1 = st.sidebar.slider("Umbral Alerta Nivel 1 (percentil)", 80, 98, 95, key="q12_p1")
percentil_alerta2 = st.sidebar.slider("Umbral Alerta Nivel 2 (percentil)", 95, 99, 99, key="q12_p2")

# ─── FUNCIONES ─────────────────────────────────────────────────────────────────
@st.cache_data
def build_series(evento, geo, anios_range):
    df = df_full[
        (df_full['Evento'] == evento) &
        (df_full['ANIO'] >= anios_range[0]) &
        (df_full['ANIO'] <= anios_range[1])
    ]
    if geo != "Nacional":
        df = df[df['Provincia'] == geo]
    serie = df.groupby(['ANIO', 'SEMANA'])['CANTIDAD'].sum().reset_index()
    serie = serie.sort_values(['ANIO', 'SEMANA']).reset_index(drop=True)
    serie['Idx'] = range(len(serie))
    serie['Label'] = serie['ANIO'].astype(str) + '-SE' + serie['SEMANA'].astype(str).str.zfill(2)
    return serie


def farrington_thresholds(serie, n_years_hist, pct1, pct2):
    """
    Farrington Modificado simplificado:
    Para cada semana del año de análisis, el baseline es esa misma semana
    (±2 semanas) en los n_years_hist años previos.
    Retorna la serie con columnas: Umbral1, Umbral2, Alerta1, Alerta2.
    """
    s = serie.copy()
    s['Umbral1'] = np.nan
    s['Umbral2'] = np.nan

    anios_unicos = sorted(s['ANIO'].unique())
    if len(anios_unicos) <= n_years_hist:
        n_years_hist = max(1, len(anios_unicos) - 1)

    for idx, row in s.iterrows():
        anio_actual = row['ANIO']
        sem_actual = row['SEMANA']
        anios_hist = [a for a in anios_unicos if a < anio_actual][-n_years_hist:]
        if not anios_hist:
            continue

        mask_hist = (
            s['ANIO'].isin(anios_hist) &
            s['SEMANA'].between(max(1, sem_actual - 2), min(53, sem_actual + 2))
        )
        baseline_vals = s.loc[mask_hist, 'CANTIDAD'].values
        if len(baseline_vals) < 3:
            continue

        s.at[idx, 'Umbral1'] = np.percentile(baseline_vals, pct1)
        s.at[idx, 'Umbral2'] = np.percentile(baseline_vals, pct2)

    s['Alerta1'] = (s['CANTIDAD'] > s['Umbral1']) & s['Umbral1'].notna()
    s['Alerta2'] = (s['CANTIDAD'] > s['Umbral2']) & s['Umbral2'].notna()
    return s


def stl_manual(serie_vals, period=52):
    """
    Descomposición STL manual: Tendencia (MM) + Estacionalidad + Residuo.
    No requiere statsmodels.
    """
    n = len(serie_vals)
    y = np.array(serie_vals, dtype=float)

    # Tendencia: media móvil de period semanas
    half = period // 2
    trend = np.full(n, np.nan)
    for i in range(half, n - half):
        trend[i] = np.mean(y[i - half:i + half + 1])

    # Rellenar extremos con interpolación lineal
    valid_idx = np.where(~np.isnan(trend))[0]
    if len(valid_idx) > 1:
        trend = np.interp(np.arange(n), valid_idx, trend[valid_idx])

    # Estacionalidad: promedio de cada posición en el ciclo
    detrended = y - trend
    seasonal = np.zeros(n)
    for k in range(period):
        idxs = list(range(k, n, period))
        if idxs:
            seasonal[idxs] = np.nanmean(detrended[idxs])

    residual = y - trend - seasonal
    return trend, seasonal, residual


def calc_idet(df_all, evento, anios_range):
    """
    Índice de Dispersión Espacio-Temporal (IDET):
    Número de departamentos/provincias con al menos un caso en cada semana.
    Un IDET creciente → expansión geográfica (epidemia generalizada).
    IDET decreciente → concentración focal (brote puntual).
    """
    d = df_all[
        (df_all['Evento'] == evento) &
        (df_all['ANIO'] >= anios_range[0]) &
        (df_all['ANIO'] <= anios_range[1]) &
        (df_all['Provincia'] != 'Sin Datos') &
        (df_all['CANTIDAD'] > 0)
    ]
    idet = d.groupby(['ANIO', 'SEMANA'])['Provincia'].nunique().reset_index()
    idet.columns = ['ANIO', 'SEMANA', 'IDET']
    idet = idet.sort_values(['ANIO', 'SEMANA']).reset_index(drop=True)
    idet['Idx'] = range(len(idet))
    idet['Label'] = idet['ANIO'].astype(str) + '-SE' + idet['SEMANA'].astype(str).str.zfill(2)
    return idet


# ─── CONSTRUIR SERIE ───────────────────────────────────────────────────────────
serie = build_series(evento_sel, nivel_geo, rango_anios)
serie_far = farrington_thresholds(serie, n_anios_hist, percentil_alerta1, percentil_alerta2)

# ─── MÉTRICAS ──────────────────────────────────────────────────────────────────
total_alertas1 = int(serie_far['Alerta1'].sum())
total_alertas2 = int(serie_far['Alerta2'].sum())
total_casos = int(serie['CANTIDAD'].sum())
pct_silencio = (serie['CANTIDAD'] == 0).mean() * 100

c1, c2, c3, c4 = st.columns(4)
for col, val, lbl, color in [
    (c1, f"{total_casos:,}".replace(",", "."), "CASOS TOTALES", "#00e5ff"),
    (c2, str(total_alertas1), f"ALERTAS NV1 (p{percentil_alerta1})", "#f59e0b"),
    (c3, str(total_alertas2), f"ALERTAS NV2 (p{percentil_alerta2})", "#ef4444"),
    (c4, f"{pct_silencio:.1f}%", "SEMANAS SIN CASOS", "#4a8ab5"),
]:
    col.markdown(
        f'<div class="m-card"><div class="m-num" style="color:{color}">{val}</div>'
        f'<div class="m-lbl">{lbl}</div></div>',
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# ─── TABS ──────────────────────────────────────────────────────────────────────
tab_farr, tab_stl, tab_sil, tab_idet, tab_panel = st.tabs([
    "🎯 FARRINGTON", "📉 STL RESIDUOS", "🔇 SILENCIOS INESPERADOS",
    "🌐 IDET ESPACIAL", "📋 PANEL DE ALERTAS"
])

# ══════════════════════════════════════════════════
# TAB 1: FARRINGTON MODIFICADO
# ══════════════════════════════════════════════════
with tab_farr:
    st.subheader(f"🎯 Farrington Modificado — {evento_sel} · {nivel_geo}")
    st.markdown(f"""<div class="info-box">
    Para cada semana, el umbral se calcula con los <strong>{n_anios_hist} años previos</strong>
    (misma semana ±2 semanas). <br>
    🟡 <strong>Alerta Nivel 1</strong>: supera el percentil {percentil_alerta1} del baseline histórico.<br>
    🔴 <strong>Alerta Nivel 2</strong>: supera el percentil {percentil_alerta2} del baseline histórico.
    <br>Estas alertas son <em>señales candidatas</em> — deben validarse contra calidad del dato SNVS.
    </div>""", unsafe_allow_html=True)

    if serie_far['Umbral1'].isna().all():
        st.warning("Datos históricos insuficientes para calcular baseline Farrington. "
                   "Ampliá el rango de años o reducí los años de baseline.")
    else:
        fig_f = go.Figure()
        # Banda de fondo (zona segura)
        fig_f.add_trace(go.Scatter(
            x=serie_far['Idx'], y=serie_far['Umbral2'],
            fill=None, mode='lines', line=dict(color='rgba(239,68,68,0)'), showlegend=False, hoverinfo='skip'
        ))
        # Alerta 2 (zona roja)
        fig_f.add_trace(go.Scatter(
            x=serie_far['Idx'], y=serie_far['Umbral2'],
            fill='tozeroy', mode='lines',
            fillcolor='rgba(239,68,68,0.06)', line=dict(color='#ef4444', width=1.5, dash='dash'),
            name=f'Umbral Nv2 (p{percentil_alerta2})',
            hovertemplate='Umbral Nv2: %{y:.1f}<extra></extra>'
        ))
        # Alerta 1 (zona naranja)
        fig_f.add_trace(go.Scatter(
            x=serie_far['Idx'], y=serie_far['Umbral1'],
            fill='tozeroy', mode='lines',
            fillcolor='rgba(249,115,22,0.08)', line=dict(color='#f97316', width=1.5, dash='dot'),
            name=f'Umbral Nv1 (p{percentil_alerta1})',
            hovertemplate='Umbral Nv1: %{y:.1f}<extra></extra>'
        ))
        # Serie de casos
        fig_f.add_trace(go.Scatter(
            x=serie_far['Idx'], y=serie_far['CANTIDAD'],
            mode='lines+markers', name='Casos observados',
            line=dict(color='#00e5ff', width=2),
            marker=dict(
                color=['#ef4444' if a2 else '#f97316' if a1 else '#00e5ff'
                       for a1, a2 in zip(serie_far['Alerta1'], serie_far['Alerta2'])],
                size=[10 if a2 else 7 if a1 else 4
                      for a1, a2 in zip(serie_far['Alerta1'], serie_far['Alerta2'])],
            ),
            hovertext=serie_far['Label'],
            hovertemplate='%{hovertext}<br>Casos: %{y}<extra></extra>'
        ))

        # Sombrear alertas nivel 2
        alertas_nv2 = serie_far[serie_far['Alerta2']]
        for _, row in alertas_nv2.iterrows():
            fig_f.add_vline(x=row['Idx'], line_color='rgba(239,68,68,0.25)', line_width=2)

        fig_f.update_layout(
            paper_bgcolor='#060a12', plot_bgcolor='#060a12',
            font=dict(color='#c8d8e8', family='Share Tech Mono'), height=450,
            legend=dict(bgcolor='rgba(6,10,18,0.85)', font=dict(color='#c8d8e8')),
            xaxis=dict(title='Índice temporal (semanas)', tickfont=dict(color='#c8d8e8'),
                       gridcolor='#1a3a5c'),
            yaxis=dict(title='Casos por semana', tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c'),
            title=dict(text=f"Farrington — {evento_sel} · {nivel_geo}", font=dict(color='#00e5ff'))
        )
        st.plotly_chart(fig_f, use_container_width=True)

        if total_alertas2 > 0:
            alertas_tab = serie_far[serie_far['Alerta2']][
                ['Label', 'ANIO', 'SEMANA', 'CANTIDAD', 'Umbral1', 'Umbral2']
            ].rename(columns={'Label': 'Período', 'CANTIDAD': 'Casos obs.',
                               'Umbral1': f'Umbral Nv1 (p{percentil_alerta1})',
                               'Umbral2': f'Umbral Nv2 (p{percentil_alerta2})'})
            st.markdown(f'<div class="alert-red">🚨 <strong>{total_alertas2} semanas en Alerta Nivel 2</strong> — supera el percentil {percentil_alerta2} histórico.</div>',
                        unsafe_allow_html=True)
            st.dataframe(alertas_tab.round(1), use_container_width=True, hide_index=True)
            st.download_button("📥 Exportar alertas Farrington",
                               data=alertas_tab.to_csv(index=False).encode('utf-8'),
                               file_name=f"farrington_{evento_sel.replace(' ','_')}_{nivel_geo}.csv",
                               mime='text/csv')
        elif total_alertas1 > 0:
            st.markdown(f'<div class="alert-yellow">⚠️ {total_alertas1} semanas en Alerta Nivel 1 (p{percentil_alerta1}). Sin alertas críticas Nv2.</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-green">✅ Sin alertas Farrington en el período analizado.</div>',
                        unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# TAB 2: DESCOMPOSICIÓN STL
# ══════════════════════════════════════════════════
with tab_stl:
    st.subheader("📉 Descomposición STL: Separar Señal de Estacionalidad y Ruido")
    st.markdown("""<div class="info-box">
    La descomposición STL separa la serie en:<br>
    📈 <strong>Tendencia</strong>: dirección de largo plazo.<br>
    🔄 <strong>Estacionalidad</strong>: patrón que se repite anualmente (semanas con pico).<br>
    💥 <strong>Residuo</strong>: lo que queda — donde viven las anomalías verdaderas.<br>
    Los residuos con <strong>|Z| &gt; 2.5</strong> son anomalías no explicadas por tendencia ni estacionalidad.
    </div>""", unsafe_allow_html=True)

    if len(serie) < 52:
        st.warning("Se necesitan al menos 52 semanas de datos para la descomposición STL.")
    else:
        trend, seasonal, residual = stl_manual(serie['CANTIDAD'].values, period=52)
        serie_stl = serie.copy()
        serie_stl['Tendencia'] = trend
        serie_stl['Estacional'] = seasonal
        serie_stl['Residuo'] = residual
        residuo_mean = np.nanmean(residual)
        residuo_std = np.nanstd(residual)
        serie_stl['Z_Residuo'] = ((residual - residuo_mean) / (residuo_std + 1e-10))
        serie_stl['Anomalia_STL'] = serie_stl['Z_Residuo'].abs() > 2.5

        # Plot 4 paneles
        fig_stl = go.Figure()
        colors = ['#00e5ff', '#4ade80', '#f59e0b', '#ef4444']
        components = ['CANTIDAD', 'Tendencia', 'Estacional', 'Residuo']
        labels = ['Observado', 'Tendencia', 'Estacionalidad', 'Residuo']

        for i, (comp, lbl, color) in enumerate(zip(components, labels, colors)):
            visible = True if i == 0 else 'legendonly'
            fig_stl.add_trace(go.Scatter(
                x=serie_stl['Idx'], y=serie_stl[comp], name=lbl,
                line=dict(color=color, width=2), visible=visible,
                hovertext=serie_stl['Label'],
                hovertemplate=f'{lbl}: %{{y:.1f}}<br>%{{hovertext}}<extra></extra>'
            ))

        # Marcar anomalías STL
        anom = serie_stl[serie_stl['Anomalia_STL']]
        fig_stl.add_trace(go.Scatter(
            x=anom['Idx'], y=anom['CANTIDAD'], mode='markers',
            name='Anomalía STL (|Z|>2.5)',
            marker=dict(color='#ef4444', size=12, symbol='x-thin',
                        line=dict(color='#ef4444', width=2)),
            hovertext=anom['Label'],
            hovertemplate='🚨 ANOMALÍA<br>%{hovertext}<br>Casos: %{y}<extra></extra>'
        ))
        fig_stl.add_hline(y=0, line_color='rgba(255,255,255,0.13)', line_width=1)
        fig_stl.update_layout(
            paper_bgcolor='#060a12', plot_bgcolor='#060a12',
            font=dict(color='#c8d8e8', family='Share Tech Mono'), height=440,
            legend=dict(bgcolor='rgba(6,10,18,0.85)', font=dict(color='#c8d8e8')),
            xaxis=dict(title='Índice semanal', tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c'),
            yaxis=dict(title='Valor', tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c'),
            title=dict(text=f"STL — {evento_sel} · {nivel_geo} (activar/desactivar capas en leyenda)",
                       font=dict(color='#00e5ff'))
        )
        st.plotly_chart(fig_stl, use_container_width=True)

        n_anom = int(serie_stl['Anomalia_STL'].sum())
        if n_anom > 0:
            st.markdown(f'<div class="alert-red">🚨 <strong>{n_anom} anomalías verdaderas (|Z|&gt;2.5)</strong> — no explicadas por tendencia ni estacionalidad. Estas son candidatas a ser señales epidemiológicas reales.</div>',
                        unsafe_allow_html=True)
            anom_tab = serie_stl[serie_stl['Anomalia_STL']][
                ['Label', 'CANTIDAD', 'Tendencia', 'Estacional', 'Residuo', 'Z_Residuo']
            ].rename(columns={'Label': 'Período', 'CANTIDAD': 'Casos obs.',
                               'Z_Residuo': 'Z (residuo)'}).round(2)
            st.dataframe(anom_tab, use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="alert-green">✅ Sin anomalías STL significativas (|Z|&gt;2.5). Los picos observados se explican por tendencia y estacionalidad habitual.</div>',
                        unsafe_allow_html=True)

        # Estacionalidad: semanas pico
        st.markdown("#### 📅 Calendario de Estacionalidad — Semanas de Mayor Riesgo")
        estac_sem = pd.DataFrame({
            'Semana': range(1, 53),
            'Componente Estacional': [np.nanmean(residual[i::52]) for i in range(52)]
        })
        fig_est = go.Figure(go.Bar(
            x=estac_sem['Semana'], y=estac_sem['Componente Estacional'],
            marker=dict(color=estac_sem['Componente Estacional'],
                        colorscale='RdYlGn', showscale=False),
            hovertemplate='SE %{x}<br>Componente: %{y:.1f}<extra></extra>'
        ))
        fig_est.add_hline(y=0, line_color='rgba(255,255,255,0.27)')
        fig_est.update_layout(
            paper_bgcolor='#060a12', plot_bgcolor='#060a12',
            font=dict(color='#c8d8e8', family='Share Tech Mono'), height=270,
            xaxis=dict(title='Semana epidemiológica', tickfont=dict(color='#c8d8e8'),
                       gridcolor='#1a3a5c', dtick=4),
            yaxis=dict(title='Exceso estacional', tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c'),
            title=dict(text="Componente estacional por SE (verde = bajo, rojo = alto)",
                       font=dict(color='#00e5ff', size=13))
        )
        st.plotly_chart(fig_est, use_container_width=True)

# ══════════════════════════════════════════════════
# TAB 3: SILENCIOS INESPERADOS
# ══════════════════════════════════════════════════
with tab_sil:
    st.subheader("🔇 Detector de Silencios Inesperados — Ausencias no Esperadas")
    st.markdown("""<div class="info-box">
    Un silencio es "inesperado" cuando el modelo predictivo espera casos pero se notifican cero.
    Se clasifica en tres categorías:<br>
    🔴 <strong>Probable sub-notificación</strong>: el histórico predice &gt;5 casos y hay 0.<br>
    🟡 <strong>Posible cambio de definición</strong>: baja súbita por debajo del percentil 10.<br>
    🟢 <strong>Ausencia posiblemente real</strong>: intervención documentada o baja endémica esperada.
    </div>""", unsafe_allow_html=True)

    thresh_esperar = st.slider("Umbral 'casos esperados' para alerta de silencio", 1, 20, 5, key="q12_sil_thresh")

    # Para cada semana, predecir con baseline histórico
    serie_sil = serie_far.copy()
    baseline_hist = []
    for _, row in serie_sil.iterrows():
        anio_act, sem_act = row['ANIO'], row['SEMANA']
        hist_vals = df_full[
            (df_full['Evento'] == evento_sel) &
            (df_full['Provincia'] == nivel_geo if nivel_geo != "Nacional" else True) &
            (df_full['ANIO'] < anio_act) &
            (df_full['SEMANA'].between(max(1, sem_act - 2), min(53, sem_act + 2)))
        ]['CANTIDAD'].sum() if nivel_geo != "Nacional" else df_full[
            (df_full['Evento'] == evento_sel) &
            (df_full['ANIO'] < anio_act) &
            (df_full['SEMANA'].between(max(1, sem_act - 2), min(53, sem_act + 2)))
        ]['CANTIDAD'].mean()
        baseline_hist.append(hist_vals if not np.isnan(hist_vals) else 0)

    serie_sil['Baseline_hist'] = baseline_hist
    serie_sil['Silencio_inesperado'] = (serie_sil['CANTIDAD'] == 0) & (serie_sil['Baseline_hist'] >= thresh_esperar)
    serie_sil['Baja_abrupta'] = (
        serie_sil['CANTIDAD'] < serie_sil['Umbral1'].fillna(np.inf) * 0.1
    ) & (serie_sil['CANTIDAD'] > 0) & (serie_sil['Baseline_hist'] >= thresh_esperar)

    fig_sil = go.Figure()
    # Baseline esperado
    fig_sil.add_trace(go.Scatter(
        x=serie_sil['Idx'], y=serie_sil['Baseline_hist'],
        name='Baseline histórico (esperado)', line=dict(color='#4a8ab5', width=1.5, dash='dot'),
        opacity=0.7, hovertemplate='Esperado: %{y:.1f}<extra></extra>'
    ))
    # Observado
    fig_sil.add_trace(go.Scatter(
        x=serie_sil['Idx'], y=serie_sil['CANTIDAD'], name='Observado',
        line=dict(color='#00e5ff', width=2), fill='tozeroy',
        fillcolor='rgba(0,229,255,0.07)',
        marker=dict(
            color=['#ef4444' if s else '#f59e0b' if b else '#00e5ff'
                   for s, b in zip(serie_sil['Silencio_inesperado'], serie_sil['Baja_abrupta'])],
            size=[12 if s else 9 if b else 4
                  for s, b in zip(serie_sil['Silencio_inesperado'], serie_sil['Baja_abrupta'])],
        ),
        hovertext=serie_sil['Label'],
        hovertemplate='%{hovertext}<br>Obs: %{y}<extra></extra>'
    ))
    fig_sil.update_layout(
        paper_bgcolor='#060a12', plot_bgcolor='#060a12',
        font=dict(color='#c8d8e8', family='Share Tech Mono'), height=420,
        legend=dict(bgcolor='rgba(6,10,18,0.85)', font=dict(color='#c8d8e8')),
        xaxis=dict(title='Semanas', tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c'),
        yaxis=dict(title='Casos', tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c'),
        title=dict(text="Silencios Inesperados (rojo = silencio donde se esperaban casos)",
                   font=dict(color='#00e5ff'))
    )
    st.plotly_chart(fig_sil, use_container_width=True)

    n_sil = int(serie_sil['Silencio_inesperado'].sum())
    n_baja = int(serie_sil['Baja_abrupta'].sum())

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if n_sil > 0:
            st.markdown(f"""<div class="alert-red">
            🔴 <strong>{n_sil} silencios inesperados</strong> — cero notificaciones donde el histórico predecía
            ≥ {thresh_esperar} casos. Hipótesis prioritaria: ruptura de la cadena de notificación.
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-green">✅ Sin silencios inesperados detectados.</div>',
                        unsafe_allow_html=True)
    with col_s2:
        if n_baja > 0:
            st.markdown(f"""<div class="alert-yellow">
            🟡 <strong>{n_baja} semanas de baja abrupta</strong> — caída súbita &lt;10% de lo esperado.
            Investigar si coincide con cambio en criterio de caso o migración de plataforma.
            </div>""", unsafe_allow_html=True)

    if n_sil > 0:
        sil_tab = serie_sil[serie_sil['Silencio_inesperado']][
            ['Label', 'ANIO', 'SEMANA', 'CANTIDAD', 'Baseline_hist']
        ].rename(columns={'Label': 'Período', 'CANTIDAD': 'Casos obs.', 'Baseline_hist': 'Esperado (media hist.)'})
        st.dataframe(sil_tab.round(1), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════
# TAB 4: IDET ESPACIAL
# ══════════════════════════════════════════════════
with tab_idet:
    st.subheader("🌐 Índice de Dispersión Espacio-Temporal (IDET)")
    st.markdown("""<div class="info-box">
    El IDET cuenta <strong>cuántas provincias reportan al menos un caso por semana</strong>.<br>
    📈 <strong>IDET creciente</strong>: expansión geográfica → epidemia generalizada.<br>
    📉 <strong>IDET decreciente o bajo</strong>: concentración focal → brote localizado (mejor para contención).<br>
    Un IDET que sube bruscamente es una señal de alarma temprana de expansión.
    </div>""", unsafe_allow_html=True)

    idet_df = calc_idet(df_full, evento_sel, rango_anios)

    if idet_df.empty:
        st.warning("Sin datos suficientes para calcular IDET.")
    else:
        # Media móvil 4 semanas
        idet_df['IDET_MM4'] = idet_df['IDET'].rolling(4, center=True, min_periods=1).mean()

        # Detectar cambios bruscos de IDET
        idet_df['IDET_delta'] = idet_df['IDET'].diff()
        umbral_delta_idet = idet_df['IDET_delta'].std() * 2
        idet_df['Expansion_brusca'] = idet_df['IDET_delta'] > umbral_delta_idet

        fig_idet = go.Figure()
        fig_idet.add_trace(go.Bar(
            x=idet_df['Idx'], y=idet_df['IDET'],
            marker=dict(color=idet_df['IDET'], colorscale='YlOrRd',
                        showscale=True, colorbar=dict(title='Provs.', tickfont=dict(color='#c8d8e8'))),
            name='IDET (bruto)', opacity=0.5, hoverinfo='skip'
        ))
        fig_idet.add_trace(go.Scatter(
            x=idet_df['Idx'], y=idet_df['IDET_MM4'], name='IDET (MM4)',
            line=dict(color='#00e5ff', width=2.5),
            hovertext=idet_df['Label'],
            hovertemplate='%{hovertext}<br>IDET: %{y:.1f} provincias<extra></extra>'
        ))
        # Marcar expansiones bruscas
        exp = idet_df[idet_df['Expansion_brusca']]
        fig_idet.add_trace(go.Scatter(
            x=exp['Idx'], y=exp['IDET'], mode='markers',
            name='Expansión brusca', marker=dict(color='#ef4444', size=12, symbol='triangle-up'),
            hovertext=exp['Label'],
            hovertemplate='🚨 EXPANSIÓN<br>%{hovertext}<br>IDET: %{y}<extra></extra>'
        ))
        fig_idet.update_layout(
            paper_bgcolor='#060a12', plot_bgcolor='#060a12',
            font=dict(color='#c8d8e8', family='Share Tech Mono'), height=420,
            legend=dict(bgcolor='rgba(6,10,18,0.85)', font=dict(color='#c8d8e8')),
            xaxis=dict(title='Semanas', tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c'),
            yaxis=dict(title='Nº de provincias con casos', tickfont=dict(color='#c8d8e8'),
                       gridcolor='#1a3a5c'),
            title=dict(text=f"IDET — {evento_sel}: ¿Focal o Expandido?", font=dict(color='#00e5ff'))
        )
        st.plotly_chart(fig_idet, use_container_width=True)

        max_idet = int(idet_df['IDET'].max())
        n_prov_total = len(provincias_list)
        if max_idet >= n_prov_total * 0.7:
            st.markdown(f'<div class="alert-red">🚨 IDET máximo = <strong>{max_idet} provincias ({max_idet/n_prov_total*100:.0f}%)</strong>. Patrón de epidemia generalizada. Respuesta requiere nivel federal.</div>',
                        unsafe_allow_html=True)
        elif max_idet >= n_prov_total * 0.3:
            st.markdown(f'<div class="alert-yellow">⚠️ IDET máximo = <strong>{max_idet} provincias</strong>. Patrón regional. Monitorear difusión hacia provincias contiguas.</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="alert-green">✅ IDET máximo = <strong>{max_idet} provincias</strong>. Patrón focal. Brote localizado — priorizar contención en zona de origen.</div>',
                        unsafe_allow_html=True)

        # IDET por año (comparación)
        idet_anual = idet_df.groupby('ANIO')['IDET'].agg(['mean', 'max']).reset_index()
        idet_anual.columns = ['Año', 'IDET medio', 'IDET máximo']
        fig_ian = px.line(idet_anual.melt(id_vars='Año', var_name='Métrica', value_name='Valor'),
                          x='Año', y='Valor', color='Métrica',
                          title='IDET anual (medio y máximo)',
                          color_discrete_map={'IDET medio': '#4a8ab5', 'IDET máximo': '#ef4444'})
        fig_ian.update_layout(paper_bgcolor='#060a12', plot_bgcolor='#060a12',
                               font=dict(color='#c8d8e8'), height=280,
                               xaxis=dict(gridcolor='#1a3a5c'),
                               yaxis=dict(gridcolor='#1a3a5c'),
                               legend=dict(bgcolor='rgba(6,10,18,0.85)'))
        st.plotly_chart(fig_ian, use_container_width=True)

# ══════════════════════════════════════════════════
# TAB 5: PANEL DE ALERTAS ACTIVAS
# ══════════════════════════════════════════════════
with tab_panel:
    st.subheader("📋 Panel de Alertas Activas — Todos los Eventos")
    st.markdown("""<div class="info-box">
    Resumen ejecutivo de todos los eventos/provincias en situación de alerta.
    Ordenado por severidad. Exportable como CSV para reporte.
    Baseline: <strong>últimas 4 semanas vs. mismo período en años previos</strong>.
    </div>""", unsafe_allow_html=True)

    anio_ref = st.number_input("Año de referencia (actual)", min_value=anio_min,
                                max_value=anio_max, value=anio_max, key="q12_anio_ref")
    sem_ref = st.slider("Semana de referencia", 1, 52, int(min(sem_hoy - 2, 52)), key="q12_sem_ref")
    ventana_alertas = st.slider("Ventana de análisis (últimas N semanas)", 1, 8, 4, key="q12_ventana")

    @st.cache_data
    def compute_panel(anio_ref, sem_ref, ventana, n_hist):
        alertas_panel = []
        sems_ref = list(range(max(1, sem_ref - ventana + 1), sem_ref + 1))

        for ev in eventos_list:
            df_ev = df_full[df_full['Evento'] == ev]
            # Casos actuales
            actual = df_ev[(df_ev['ANIO'] == anio_ref) &
                            (df_ev['SEMANA'].isin(sems_ref))]['CANTIDAD'].sum()
            # Baseline: mismo período, años previos
            anios_prev = [a for a in range(anio_ref - n_hist, anio_ref) if a >= anio_min]
            hist_vals = df_ev[(df_ev['ANIO'].isin(anios_prev)) &
                               (df_ev['SEMANA'].isin(sems_ref))].groupby('ANIO')['CANTIDAD'].sum()
            if len(hist_vals) < 2:
                continue
            hist_mean = hist_vals.mean()
            hist_std = hist_vals.std()
            if hist_mean == 0:
                continue
            ratio = actual / hist_mean
            z = (actual - hist_mean) / (hist_std + 1e-10)
            nivel = ('🚨 CRÍTICO' if z > 2.5 or ratio > 2.5 else
                     '⚠️ ALERTA' if z > 1.96 or ratio > 1.5 else
                     '🔶 AVISO' if z > 1.28 or ratio > 1.2 else '✅ Normal')
            if nivel != '✅ Normal':
                alertas_panel.append({
                    'Evento': ev, 'Casos actuales': int(actual),
                    'Media histórica': round(hist_mean, 1),
                    'Ratio (act/hist)': round(ratio, 2),
                    'Z-score': round(z, 2),
                    'Nivel': nivel
                })
        return pd.DataFrame(alertas_panel).sort_values('Z-score', ascending=False) if alertas_panel else pd.DataFrame()

    df_panel = compute_panel(anio_ref, sem_ref, ventana_alertas, n_anios_hist)

    if not df_panel.empty:
        criticos = df_panel[df_panel['Nivel'] == '🚨 CRÍTICO']
        alertas = df_panel[df_panel['Nivel'] == '⚠️ ALERTA']
        avisos = df_panel[df_panel['Nivel'] == '🔶 AVISO']

        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.markdown(f'<div class="m-card"><div class="m-num" style="color:#ef4444">{len(criticos)}</div><div class="m-lbl">CRÍTICOS</div></div>', unsafe_allow_html=True)
        c_m2.markdown(f'<div class="m-card"><div class="m-num" style="color:#f59e0b">{len(alertas)}</div><div class="m-lbl">ALERTAS</div></div>', unsafe_allow_html=True)
        c_m3.markdown(f'<div class="m-card"><div class="m-num" style="color:#f97316">{len(avisos)}</div><div class="m-lbl">AVISOS</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        if not criticos.empty:
            st.markdown(f'<div class="alert-red">🚨 <strong>EVENTOS CRÍTICOS (Z&gt;2.5):</strong> {", ".join(criticos["Evento"].tolist())}</div>',
                        unsafe_allow_html=True)

        st.dataframe(df_panel, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Exportar Panel de Alertas",
            data=df_panel.to_csv(index=False).encode('utf-8'),
            file_name=f"panel_alertas_SE{sem_ref}_{anio_ref}.csv",
            mime='text/csv',
            type="primary"
        )
    else:
        st.success("✅ Sin alertas activas para la semana y ventana seleccionadas.")
