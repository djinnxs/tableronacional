# -*- coding: utf-8 -*-
"""
10_🔬_Calidad_SNVS.py
=====================
Módulo de Auditoría de Calidad y Sesgo del SNVS.

PRINCIPIO RECTOR: Cuestionar SIEMPRE la calidad y el sesgo antes de interpretar.
Un silencio puede ser sub-notificación, no epidemiología favorable.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import datetime
from utils import get_epi_week_data

st.set_page_config(page_title="Auditoría Calidad SNVS", page_icon="🔬", layout="wide")

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
.stTabs [data-baseweb="tab"]{background:#0d1b2a;border-radius:4px;padding:8px 16px;
  font-family:'Share Tech Mono',monospace;color:#8ecae6}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#023e8a,#0077b6)!important;color:#00e5ff!important}
hr{border-color:#1a3a5c!important}
div.stButton>button{background:linear-gradient(90deg,#023e8a,#0077b6);color:#fff;
  border:1px solid #00b4d8;border-radius:4px;font-family:'Share Tech Mono',monospace;
  padding:10px 24px;letter-spacing:.06em;transition:all .2s}
div.stButton>button:hover{box-shadow:0 0 16px #00e5ff44;transform:translateY(-1px)}
[data-testid="metric-container"]{background:#0d1b2a;border:1px solid #1a3a5c;border-radius:6px;padding:12px}
</style>""", unsafe_allow_html=True)

# ─── HEADER ────────────────────────────────────────────────────────────────────
sem_hoy, anio_hoy = get_epi_week_data(datetime.date.today())
st.markdown(f"""
<div style="border-bottom:2px solid #00e5ff22;padding-bottom:16px;margin-bottom:20px">
  <h1 style="margin:0;font-size:1.9rem;letter-spacing:.06em">🔬 AUDITORÍA DE CALIDAD Y SESGO — SNVS</h1>
  <p style="color:#4a8ab5;font-family:'Share Tech Mono',monospace;font-size:.78rem;margin:4px 0 0">
    SE actual: <span style="color:#ef4444;font-weight:700">{sem_hoy}</span> / {anio_hoy} &nbsp;·&nbsp;
    Principio rector: Cuestionar el dato antes de interpretar la epidemia
  </p>
</div>""", unsafe_allow_html=True)

st.markdown("""<div class="info-box">
⚠️ <strong>Este módulo audita el dato antes de usarlo.</strong>
Identifica silencios epidemiológicos, inconsistencias de notificación por jurisdicción,
y quiebres estructurales que pueden confundirse con señales reales.<br>
<strong>Antes de concluir que "bajó la incidencia", verificá si bajó la notificación.</strong>
</div>""", unsafe_allow_html=True)

# ─── CARGA ─────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    return pd.read_parquet('data/base_nacional.parquet')

df_full = load_data()
eventos_list = sorted(df_full['Evento'].dropna().unique().tolist())
provincias_list = sorted([p for p in df_full['Provincia'].unique() if p != 'Sin Datos'])

# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("### 🔬 Filtros de Auditoría")
evento_sel = st.sidebar.selectbox("Evento a auditar", ["(Todos)"] + eventos_list, key="q10_evento")
anio_min, anio_max = int(df_full['ANIO'].min()), int(df_full['ANIO'].max())
rango_anios = st.sidebar.slider("Rango de años", anio_min, anio_max, (anio_min, anio_max), key="q10_anios")
umbral_silencio = st.sidebar.slider("Semanas consecutivas sin notif. (alerta)", 2, 12, 4, key="q10_silencio")

df = df_full.copy()
if evento_sel != "(Todos)":
    df = df[df['Evento'] == evento_sel]
df = df[(df['ANIO'] >= rango_anios[0]) & (df['ANIO'] <= rango_anios[1])]

# ─── MÉTRICAS GLOBALES ─────────────────────────────────────────────────────────
total_reg = len(df)
provs_activas = df[df['Provincia'] != 'Sin Datos']['Provincia'].nunique()
total_sem_pos = (rango_anios[1] - rango_anios[0] + 1) * 52
sem_con_datos = df.groupby(['ANIO', 'SEMANA'])['CANTIDAD'].sum().astype(bool).sum()
cobertura_pct = (sem_con_datos / total_sem_pos * 100) if total_sem_pos > 0 else 0
pct_cero = (df.groupby(['ANIO', 'SEMANA'])['CANTIDAD'].sum() == 0).mean() * 100

c1, c2, c3, c4 = st.columns(4)
for col, val, lbl in [
    (c1, f"{total_reg:,}".replace(",", "."), "REGISTROS TOTALES"),
    (c2, str(provs_activas), "PROVINCIAS ACTIVAS"),
    (c3, f"{cobertura_pct:.1f}%", "COBERTURA TEMPORAL"),
    (c4, f"{pct_cero:.1f}%", "SEMANAS CON CERO"),
]:
    col.markdown(f'<div class="m-card"><div class="m-num">{val}</div><div class="m-lbl">{lbl}</div></div>',
                 unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── TABS ──────────────────────────────────────────────────────────────────────
tab_comp, tab_icn, tab_cusum, tab_subn, tab_sil = st.tabs([
    "📊 COMPLETITUD", "📐 ICN PROVINCIAL", "📉 CUSUM / QUIEBRES",
    "🎯 SUB-NOTIFICACIÓN", "🔇 SILENCIOS"
])

# ══════════════════════════════════════════════════
# TAB 1: COMPLETITUD
# ══════════════════════════════════════════════════
with tab_comp:
    st.subheader("📊 Completitud de Notificación: Heatmap Semana × Año")
    st.markdown("""<div class="info-box">
    Las celdas <strong>oscuras</strong> son semanas sin notificación. Patrones de filas oscuras indican
    "silencios sistemáticos" — posibles artefactos del SNVS (cambios de plataforma, cierres administrativos)
    en lugar de ausencia real de la enfermedad.
    </div>""", unsafe_allow_html=True)

    weekly_agg = df.groupby(['ANIO', 'SEMANA'])['CANTIDAD'].sum().reset_index()
    pivot = weekly_agg.pivot(index='SEMANA', columns='ANIO', values='CANTIDAD').fillna(0)
    pivot = pivot[pivot.index <= 52]

    fig_h = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[str(c) for c in pivot.columns],
        y=[f"SE {r}" for r in pivot.index],
        colorscale='Inferno',
        colorbar=dict(title='Casos', tickfont=dict(color='#c8d8e8')),
        hoverongaps=False,
        hovertemplate='Año: %{x}<br>%{y}<br>Casos: %{z:,.0f}<extra></extra>'
    ))
    fig_h.update_layout(
        paper_bgcolor='#060a12', plot_bgcolor='#060a12',
        font=dict(color='#c8d8e8', family='Share Tech Mono'), height=520,
        margin=dict(l=60, r=20, t=30, b=40),
        xaxis=dict(title='Año', tickfont=dict(color='#c8d8e8')),
        yaxis=dict(title='Semana Epi', tickfont=dict(color='#c8d8e8'), autorange='reversed')
    )
    st.plotly_chart(fig_h, use_container_width=True)

    ceros_anio = (pivot == 0).sum()
    fig_c = px.bar(
        x=ceros_anio.index.astype(str), y=ceros_anio.values,
        labels={'x': 'Año', 'y': 'Semanas con CERO casos'},
        title='Semanas con notificación nula por año',
        color=ceros_anio.values, color_continuous_scale='RdYlGn_r'
    )
    fig_c.update_layout(paper_bgcolor='#060a12', plot_bgcolor='#060a12',
                        font=dict(color='#c8d8e8'), height=280,
                        coloraxis_showscale=False)
    st.plotly_chart(fig_c, use_container_width=True)

    anio_peor = ceros_anio.idxmax()
    st.markdown(f"""<div class="alert-yellow">
    📌 El año con más semanas sin notificación es <strong>{anio_peor}</strong>
    ({ceros_anio[anio_peor]} semanas). Investigar si coincide con cambios en el SNVS,
    COVID-19 (2020), o problemas de carga de datos.
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# TAB 2: ICN PROVINCIAL
# ══════════════════════════════════════════════════
with tab_icn:
    st.subheader("📐 Índice de Consistencia de Notificación (ICN) por Provincia")
    st.markdown("""<div class="info-box">
    El <strong>ICN</strong> es el Coeficiente de Variación (CV) de la notificación semanal por provincia.
    CV &gt; 100% → notificación errática (posible artefacto sistémico, no epidemiología).
    CV &lt; 50% → notificación estable y confiable para análisis de tendencias.
    </div>""", unsafe_allow_html=True)

    wp = df[df['Provincia'] != 'Sin Datos'].groupby(
        ['Provincia', 'ANIO', 'SEMANA'])['CANTIDAD'].sum().reset_index()
    icn_df = wp.groupby('Provincia')['CANTIDAD'].agg(
        Media='mean', DE='std', Total='sum', N_semanas='count'
    ).reset_index()
    icn_df['ICN_CV'] = (icn_df['DE'] / icn_df['Media'].replace(0, np.nan) * 100).fillna(0).round(1)
    icn_df['Clasificación'] = pd.cut(
        icn_df['ICN_CV'], bins=[0, 50, 100, 200, np.inf],
        labels=['✅ Estable (<50)', '⚠️ Variable (50-100)', '🔶 Errática (100-200)', '🚨 Caótica (>200)']
    )
    icn_df = icn_df.sort_values('ICN_CV', ascending=True)

    fig_icn = go.Figure(go.Bar(
        x=icn_df['ICN_CV'], y=icn_df['Provincia'], orientation='h',
        marker=dict(color=icn_df['ICN_CV'], colorscale='RdYlGn_r', showscale=True,
                    colorbar=dict(title='CV%', tickfont=dict(color='#c8d8e8'))),
        text=[f"{v:.0f}%" for v in icn_df['ICN_CV']], textposition='outside',
        hovertemplate='%{y}<br>CV: %{x:.1f}%<extra></extra>'
    ))
    for thresh, color, label in [(50, '#4ade80', 'Estable'), (100, '#f59e0b', 'Errática'), (200, '#ef4444', 'Caótica')]:
        fig_icn.add_vline(x=thresh, line_dash="dash", line_color=color,
                          annotation_text=label, annotation_font_color=color,
                          annotation_position="top right")
    fig_icn.update_layout(
        paper_bgcolor='#060a12', plot_bgcolor='#060a12',
        font=dict(color='#c8d8e8', family='Share Tech Mono'),
        height=max(420, len(icn_df) * 24), margin=dict(l=150, r=90, t=30, b=40),
        xaxis_title='Coeficiente de Variación (%)', yaxis_title=''
    )
    st.plotly_chart(fig_icn, use_container_width=True)

    caoticas = icn_df[icn_df['ICN_CV'] > 150]
    if not caoticas.empty:
        st.markdown(f"""<div class="alert-red">
        🚨 <strong>{len(caoticas)} provincias con notificación caótica (CV &gt; 150%):
        {', '.join(caoticas['Provincia'].tolist())}</strong><br>
        Sus datos requieren análisis de sensibilidad antes de cualquier inferencia causal.
        </div>""", unsafe_allow_html=True)

    st.dataframe(
        icn_df[['Provincia', 'Media', 'DE', 'ICN_CV', 'Clasificación', 'Total']].rename(
            columns={'Media': 'Media sem.', 'DE': 'Desv.Est.', 'ICN_CV': 'CV (%)', 'Total': 'Total casos'}
        ).sort_values('CV (%)', ascending=False),
        use_container_width=True, hide_index=True
    )

# ══════════════════════════════════════════════════
# TAB 3: CUSUM
# ══════════════════════════════════════════════════
with tab_cusum:
    st.subheader("📉 CUSUM: Quiebres Estructurales en la Serie de Notificación")
    st.markdown("""<div class="info-box">
    El <strong>CUSUM</strong> detecta cambios sostenidos en el nivel de notificación.
    Un quiebre puede indicar: cambio de definición de caso, migración de plataforma SNVS,
    pandemia COVID-19, o —recién como última hipótesis— un cambio real en la incidencia.
    </div>""", unsafe_allow_html=True)

    prov_cusum = st.selectbox("Geografía para CUSUM",
                              ["Nacional (total)"] + provincias_list, key="q10_cusum_prov")
    k_param = st.slider("Sensibilidad CUSUM (k — menor = más sensible)", 0.25, 1.5, 0.5, 0.25, key="q10_k")
    h_param = st.slider("Umbral de alarma (h)", 2, 10, 4, key="q10_h")

    if prov_cusum == "Nacional (total)":
        serie = df.groupby(['ANIO', 'SEMANA'])['CANTIDAD'].sum().reset_index()
    else:
        serie = df[df['Provincia'] == prov_cusum].groupby(
            ['ANIO', 'SEMANA'])['CANTIDAD'].sum().reset_index()

    serie = serie.sort_values(['ANIO', 'SEMANA']).reset_index(drop=True)
    serie['Idx'] = range(len(serie))
    serie['Label'] = serie['ANIO'].astype(str) + '-SE' + serie['SEMANA'].astype(str).str.zfill(2)

    if len(serie) > 10:
        mu = serie['CANTIDAD'].mean()
        sigma = serie['CANTIDAD'].std() if serie['CANTIDAD'].std() > 0 else 1.0

        c_pos = np.zeros(len(serie))
        c_neg = np.zeros(len(serie))
        for i in range(1, len(serie)):
            z = (serie['CANTIDAD'].iloc[i] - mu) / sigma
            c_pos[i] = max(0.0, c_pos[i-1] + z - k_param)
            c_neg[i] = max(0.0, c_neg[i-1] - z - k_param)

        serie['C+'] = c_pos
        serie['C-'] = c_neg
        serie['Z'] = (serie['CANTIDAD'] - mu) / sigma

        # Identificar quiebres (primer cruce del umbral en cada racha)
        breaks_pos = serie[serie['C+'] > h_param].index.tolist()
        breaks_neg = serie[serie['C-'] > h_param].index.tolist()

        fig_cs = go.Figure()
        fig_cs.add_trace(go.Scatter(
            x=serie['Idx'], y=serie['Z'], name='Serie (Z-score)',
            line=dict(color='#4a8ab5', width=1), opacity=0.5,
            hovertext=serie['Label'], hovertemplate='%{hovertext}<br>Z: %{y:.2f}<extra></extra>'
        ))
        fig_cs.add_trace(go.Scatter(
            x=serie['Idx'], y=serie['C+'], name='CUSUM+ (alza sostenida)',
            line=dict(color='#ef4444', width=2.5),
            hovertext=serie['Label'], hovertemplate='%{hovertext}<br>C+: %{y:.2f}<extra></extra>'
        ))
        fig_cs.add_trace(go.Scatter(
            x=serie['Idx'], y=serie['C-'], name='CUSUM- (baja sostenida)',
            line=dict(color='#4ade80', width=2.5),
            hovertext=serie['Label'], hovertemplate='%{hovertext}<br>C-: %{y:.2f}<extra></extra>'
        ))
        fig_cs.add_hline(y=h_param, line_dash="dot", line_color="#f59e0b",
                         annotation_text=f"Umbral h={h_param}", annotation_font_color="#f59e0b")

        # Marcar quiebres
        for brk in breaks_pos[:5]:
            fig_cs.add_vline(x=brk, line_color="rgba(239, 68, 68, 0.4)", line_width=1)

        fig_cs.update_layout(
            paper_bgcolor='#060a12', plot_bgcolor='#060a12',
            font=dict(color='#c8d8e8', family='Share Tech Mono'), height=420,
            legend=dict(bgcolor='rgba(6,10,18,0.8)', font=dict(color='#c8d8e8')),
            xaxis=dict(title='Índice temporal (semanas)', tickfont=dict(color='#c8d8e8')),
            yaxis=dict(title='CUSUM / Z-score', tickfont=dict(color='#c8d8e8'))
        )
        st.plotly_chart(fig_cs, use_container_width=True)

        # Hipótesis contextuales para Argentina
        hipotesis = {
            2020: "🦠 <strong>COVID-19 (2020):</strong> Sub-notificación masiva por reorientación del sistema de salud y suspensión de consultas no-urgentes.",
            2021: "🦠 <strong>COVID-19 2ª ola (2021):</strong> Colapso parcial de la vigilancia epidemiológica. Alta posibilidad de sub-notificación.",
            2018: "📋 <strong>~2018:</strong> Posible cambio en la plataforma SNVS o inicio de nueva codificación de eventos. Verificar con el equipo de vigilancia.",
            2019: "📋 <strong>~2019:</strong> Verificar si coincide con cambio de gestión provincial o nacional que afectó los flujos de notificación.",
        }

        if breaks_pos or breaks_neg:
            anios_quiebre = serie.iloc[breaks_pos[:4]]['ANIO'].unique() if breaks_pos else []
            st.markdown("#### 🔍 Hipótesis para los quiebres detectados")
            for anio in anios_quiebre:
                hip = hipotesis.get(int(anio),
                    f"📌 <strong>~{int(anio)}:</strong> Investigar: cambio en criterio de notificación local, "
                    f"reordenamiento administrativo o evento epidemiológico real. "
                    f"Contrastar con datos de otras fuentes (registros hospitalarios, farmacovigilancia).")
                st.markdown(f'<div class="alert-yellow">{hip}</div>', unsafe_allow_html=True)
        else:
            st.success(f"✅ No se detectaron quiebres significativos (CUSUM < h={h_param})")
    else:
        st.warning("Datos insuficientes para análisis CUSUM (mínimo 10 puntos temporales).")

# ══════════════════════════════════════════════════
# TAB 4: SUB-NOTIFICACIÓN
# ══════════════════════════════════════════════════
with tab_subn:
    st.subheader("🎯 Radar de Sub-Notificación Latente")
    st.markdown("""<div class="info-box">
    Compara la tasa de notificación de cada provincia contra el promedio nacional ajustado por población.
    <strong>Ratio &lt; 0.5:</strong> provincia notifica menos del 50% de lo esperado →
    zona de silencio epidemiológico latente. No necesariamente favorece a la provincia — puede reflejar
    brechas diagnósticas, barreras de acceso o colapso de la cadena de vigilancia.
    </div>""", unsafe_allow_html=True)

    try:
        pop_df = pd.read_parquet('data/poblacionxprovinciaindec.parquet')
        pop_df = pop_df[pop_df['sexo_nombre'] == 'Ambos sexos']
        anio_pop = min(rango_anios[1], int(pop_df['ano'].max()))
        pop_anio = pop_df[pop_df['ano'] == anio_pop].groupby('juri')['poblacion'].sum().reset_index()
        pop_anio.columns = ['juri_num', 'Poblacion']

        casos_prov = df[df['Provincia'] != 'Sin Datos'].groupby(
            ['id_provincia', 'Provincia'])['CANTIDAD'].sum().reset_index()
        casos_prov['juri_num'] = pd.to_numeric(
            casos_prov['id_provincia'].astype(str).str.lstrip('0'), errors='coerce').fillna(0).astype(int)

        merged = casos_prov.merge(pop_anio, on='juri_num', how='left')
        merged['Poblacion'] = merged['Poblacion'].fillna(1)
        merged['Tasa_100k'] = (merged['CANTIDAD'] / merged['Poblacion'] * 100000).round(2)
        nac_tasa = merged['CANTIDAD'].sum() / merged['Poblacion'].sum() * 100000
        merged['Ratio_Nac'] = (merged['Tasa_100k'] / nac_tasa).fillna(0).round(3)
        merged['Clasificación'] = pd.cut(
            merged['Ratio_Nac'],
            bins=[0, 0.3, 0.5, 0.8, 1.2, 2.0, np.inf],
            labels=['🚨 Crítico (<30%)', '⚠️ Bajo (30-50%)', '🔶 Reducido (50-80%)',
                    '✅ Normal (80-120%)', '📈 Alto (120-200%)', '🔴 Muy alto (>200%)']
        )
        merged = merged.sort_values('Ratio_Nac')

        fig_ratio = go.Figure(go.Bar(
            x=merged['Ratio_Nac'], y=merged['Provincia'], orientation='h',
            marker=dict(color=merged['Ratio_Nac'], colorscale='RdYlGn',
                        cmin=0, cmax=2, showscale=True,
                        colorbar=dict(title='Ratio', tickfont=dict(color='#c8d8e8'))),
            text=[f"{v:.2f}x" for v in merged['Ratio_Nac']], textposition='outside',
            hovertemplate='%{y}<br>Ratio: %{x:.3f}x<extra></extra>'
        ))
        fig_ratio.add_vline(x=0.5, line_dash="dash", line_color="#ef4444",
                            annotation_text="Sub-notif. latente", annotation_font_color="#ef4444")
        fig_ratio.add_vline(x=1.0, line_dash="dash", line_color="#4a8ab5",
                            annotation_text="Promedio nacional", annotation_font_color="#4a8ab5")
        fig_ratio.update_layout(
            paper_bgcolor='#060a12', plot_bgcolor='#060a12',
            font=dict(color='#c8d8e8', family='Share Tech Mono'),
            height=max(420, len(merged) * 24), margin=dict(l=150, r=90, t=30, b=40),
            xaxis_title='Ratio vs. promedio nacional (1.0 = esperado)'
        )
        st.plotly_chart(fig_ratio, use_container_width=True)

        silencio_lat = merged[merged['Ratio_Nac'] < 0.5]
        if not silencio_lat.empty:
            st.markdown(f"""<div class="alert-red">
            🚨 <strong>Zonas de Silencio Epidemiológico Latente — {len(silencio_lat)} provincias:</strong>
            {', '.join(silencio_lat['Provincia'].tolist())}<br><br>
            Estas provincias notifican menos del 50% de lo esperado. Hipótesis a investigar:
            (1) Sub-notificación real por barreras de acceso diagnóstico,
            (2) Colapso de la cadena de vigilancia local,
            (3) Definición de caso más restrictiva aplicada localmente.
            </div>""", unsafe_allow_html=True)

        st.dataframe(
            merged[['Provincia', 'CANTIDAD', 'Poblacion', 'Tasa_100k', 'Ratio_Nac', 'Clasificación']].rename(
                columns={'CANTIDAD': 'Casos', 'Tasa_100k': 'Tasa/100k', 'Ratio_Nac': 'Ratio vs. Nac.'}
            ).sort_values('Ratio vs. Nac.'),
            use_container_width=True, hide_index=True
        )

    except Exception as e:
        st.error(f"Error en cálculo de sub-notificación: {e}")

# ══════════════════════════════════════════════════
# TAB 5: SILENCIOS
# ══════════════════════════════════════════════════
with tab_sil:
    st.subheader("🔇 Detector de Silencios Epidemiológicos Inesperados")
    st.markdown(f"""<div class="info-box">
    Identifica provincias que históricamente notifican un evento y dejan de hacerlo por
    <strong>≥ {umbral_silencio} semanas consecutivas</strong>. Un silencio inesperado puede ser:
    (A) sub-notificación sistémica, (B) cambio de definición de caso, o (C) ausencia real de transmisión
    (biológicamente improbable sin intervención documentada).
    </div>""", unsafe_allow_html=True)

    col_ev, col_prov = st.columns(2)
    with col_ev:
        evento_sil = st.selectbox("Evento", eventos_list, key="q10_ev_sil")
    with col_prov:
        modo_geo = st.selectbox("Nivel geográfico", ["Provincia", "Nacional"], key="q10_geo_sil")

    df_ev = df_full[df_full['Evento'] == evento_sil].copy()

    silencios = []
    scope = provincias_list if modo_geo == "Provincia" else ["Nacional"]
    for zona in scope:
        if zona == "Nacional":
            df_z = df_ev.groupby(['ANIO', 'SEMANA'])['CANTIDAD'].sum().reset_index()
        else:
            df_z = df_ev[df_ev['Provincia'] == zona].groupby(
                ['ANIO', 'SEMANA'])['CANTIDAD'].sum().reset_index()

        if df_z['CANTIDAD'].sum() == 0:
            continue

        df_z = df_z.sort_values(['ANIO', 'SEMANA']).reset_index(drop=True)
        racha, racha_max, inicio_racha = 0, 0, None
        for _, row in df_z.iterrows():
            if row['CANTIDAD'] == 0:
                racha += 1
                if racha == 1:
                    inicio_racha = f"{int(row['ANIO'])}-SE{int(row['SEMANA'])}"
                racha_max = max(racha_max, racha)
            else:
                racha = 0

        if racha_max >= umbral_silencio:
            media_hist = df_z[df_z['CANTIDAD'] > 0]['CANTIDAD'].mean()
            cls = ('🚨 Crítico' if racha_max >= umbral_silencio * 3
                   else '⚠️ Alerta' if racha_max >= umbral_silencio * 1.5 else '🔶 Aviso')
            silencios.append({
                'Jurisdicción': zona, 'Evento': evento_sil,
                'Racha máx. (sem)': racha_max, 'Inicio silencio': inicio_racha,
                'Media histórica/sem': round(media_hist, 1), 'Clasificación': cls
            })

    if silencios:
        df_sil = pd.DataFrame(silencios).sort_values('Racha máx. (sem)', ascending=False)
        criticos = df_sil[df_sil['Clasificación'] == '🚨 Crítico']
        if not criticos.empty:
            st.markdown(f"""<div class="alert-red">
            🚨 <strong>Silencios Críticos en {len(criticos)} jurisdicción(es):</strong>
            {', '.join(criticos['Jurisdicción'].tolist())}<br>
            Rachas de silencio ≥ {umbral_silencio*3} semanas con historial positivo.
            Alta probabilidad de sub-notificación sistémica o ruptura de la cadena de vigilancia.
            </div>""", unsafe_allow_html=True)
        st.dataframe(df_sil, use_container_width=True, hide_index=True)
        st.download_button("📥 Descargar silencios detectados",
                           data=df_sil.to_csv(index=False).encode('utf-8'),
                           file_name=f"silencios_{evento_sil.replace(' ','_')}.csv",
                           mime='text/csv')
    else:
        st.success(f"✅ Sin silencios ≥ {umbral_silencio} semanas para '{evento_sil}' en el período seleccionado.")

    # Visualización de serie para una provincia
    st.markdown("---")
    st.markdown("#### 📈 Serie temporal con silencios marcados")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        ev_viz = st.selectbox("Evento", eventos_list, key="q10_ev_viz")
    with col_v2:
        prov_viz = st.selectbox("Provincia", provincias_list, key="q10_prov_viz")

    df_viz = df_full[(df_full['Evento'] == ev_viz) & (df_full['Provincia'] == prov_viz)].groupby(
        ['ANIO', 'SEMANA'])['CANTIDAD'].sum().reset_index().sort_values(['ANIO', 'SEMANA'])
    df_viz['Idx'] = range(len(df_viz))
    df_viz['Label'] = df_viz['ANIO'].astype(str) + '-SE' + df_viz['SEMANA'].astype(str).str.zfill(2)

    if not df_viz.empty and df_viz['CANTIDAD'].sum() > 0:
        max_val = df_viz['CANTIDAD'].max()
        media_v = df_viz[df_viz['CANTIDAD'] > 0]['CANTIDAD'].mean()
        silencio_mask = (df_viz['CANTIDAD'] == 0).astype(float) * max_val

        fig_v = go.Figure()
        fig_v.add_trace(go.Bar(
            x=df_viz['Idx'], y=silencio_mask,
            name='Semanas sin notificación', marker_color='rgba(239,68,68,0.15)',
            hoverinfo='skip'
        ))
        fig_v.add_trace(go.Scatter(
            x=df_viz['Idx'], y=df_viz['CANTIDAD'], name='Casos notificados',
            line=dict(color='#00e5ff', width=2), fill='tozeroy',
            fillcolor='rgba(0,229,255,0.08)', hovertext=df_viz['Label'],
            hovertemplate='%{hovertext}<br>Casos: %{y}<extra></extra>'
        ))
        fig_v.add_hline(y=media_v, line_dash="dash", line_color="#f59e0b",
                        annotation_text=f"Media histórica: {media_v:.1f}",
                        annotation_font_color="#f59e0b")
        fig_v.update_layout(
            paper_bgcolor='#060a12', plot_bgcolor='#060a12',
            font=dict(color='#c8d8e8', family='Share Tech Mono'), height=320,
            title=dict(text=f"{ev_viz} — {prov_viz}", font=dict(color='#00e5ff')),
            legend=dict(bgcolor='rgba(6,10,18,0.8)', font=dict(color='#c8d8e8'))
        )
        st.plotly_chart(fig_v, use_container_width=True)
    else:
        st.info("Sin datos para la combinación evento/provincia seleccionada.")
