# -*- coding: utf-8 -*-
"""
11_🕸️_Sindémica.py
===================
Módulo de Análisis Sindémico y Co-ocurrencia Temporal-Espacial.

Analiza cómo múltiples eventos (TBC, Sífilis, Alacranismo, etc.) interactúan
en tiempo y espacio. No busca correlaciones espurias: busca señales con
coherencia biológica, social y espacial.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy.stats import pearsonr
import datetime
from utils import get_epi_week_data

st.set_page_config(page_title="Análisis Sindémico SNVS", page_icon="🕸️", layout="wide")

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
.signal-weak{background:linear-gradient(135deg,#0a1a0a,#0f2a0f);border:1px solid #4ade8044;
  border-left:4px solid #4ade80;border-radius:6px;padding:14px;color:#bbf7d0;
  font-family:'Share Tech Mono',monospace;font-size:.82rem;margin:8px 0}
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
</style>""", unsafe_allow_html=True)

# ─── HEADER ────────────────────────────────────────────────────────────────────
sem_hoy, anio_hoy = get_epi_week_data(datetime.date.today())
st.markdown(f"""
<div style="border-bottom:2px solid #00e5ff22;padding-bottom:16px;margin-bottom:20px">
  <h1 style="margin:0;font-size:1.9rem;letter-spacing:.06em">🕸️ ANÁLISIS SINDÉMICO — CO-OCURRENCIA & SEÑALES DÉBILES</h1>
  <p style="color:#4a8ab5;font-family:'Share Tech Mono',monospace;font-size:.78rem;margin:4px 0 0">
    SE: <span style="color:#ef4444;font-weight:700">{sem_hoy}</span>/{anio_hoy} &nbsp;·&nbsp;
    Dinámica de interacción multi-evento en tiempo y espacio
  </p>
</div>""", unsafe_allow_html=True)

st.markdown("""<div class="info-box">
🔬 Una <strong>sindemia</strong> no es la co-ocurrencia casual de dos enfermedades — es una interacción
bidireccional donde cada una amplifica biológica o socialmente a la otra. TBC + VIH, Sífilis + VIH,
Alacranismo + acceso precario a salud. Este módulo busca esas interacciones en los datos del SNVS.
<br><strong>Advertencia metodológica:</strong> correlación ≠ sinergia sindémica.
Toda señal alta requiere plausibilidad biológica y contexto social antes de ser interpretada.
</div>""", unsafe_allow_html=True)

# ─── CARGA ─────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    return pd.read_parquet('data/base_nacional.parquet')

df_full = load_data()
eventos_list = sorted(df_full['Evento'].dropna().unique().tolist())
provincias_list = sorted([p for p in df_full['Provincia'].unique() if p != 'Sin Datos'])

# Sugerencias pre-cargadas de tríadas sindémicas conocidas
TRIADAS_SUGERIDAS = {
    "TBC + Sífilis (co-morbilidad por vulnerabilidad social)": ["Tuberculosis", "Sífilis"],
    "TBC + VIH/SIDA (sindemia clásica)": ["Tuberculosis", "VIH/SIDA"],
    "Alacranismo + Dengue (vector + fauna en zonas áridas)": ["Alacranismo", "Dengue"],
    "Sífilis + Gonorrea (ITS de transmisión común)": ["Sífilis", "Gonorrea"],
}

# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("### 🕸️ Configuración Sindémica")
preset = st.sidebar.selectbox("Tríadas conocidas (opcional)",
                              ["— Selección manual —"] + list(TRIADAS_SUGERIDAS.keys()),
                              key="s11_preset")

if preset != "— Selección manual —":
    sugeridos = [e for e in TRIADAS_SUGERIDAS[preset] if e in eventos_list]
    default_ev = sugeridos if sugeridos else eventos_list[:2]
else:
    default_ev = eventos_list[:2]

eventos_sel = st.sidebar.multiselect(
    "Eventos a analizar (2–4)", eventos_list, default=default_ev, key="s11_eventos"
)
anio_min, anio_max = int(df_full['ANIO'].min()), int(df_full['ANIO'].max())
rango_anios = st.sidebar.slider("Rango años", anio_min, anio_max, (anio_min, anio_max), key="s11_anios")
nivel_geo = st.sidebar.radio("Nivel geográfico", ["Nacional", "Por Provincia"], key="s11_geo")
max_lag = st.sidebar.slider("Lags CCF (semanas)", 4, 16, 8, key="s11_lag")

if len(eventos_sel) < 2:
    st.warning("⚠️ Seleccioná al menos **2 eventos** para analizar la dinámica sindémica.")
    st.stop()

# ─── FUNCIONES ─────────────────────────────────────────────────────────────────
@st.cache_data
def build_weekly_matrix(eventos, anios_range, nivel):
    """Construye matriz semanal: índice=período, columnas=eventos"""
    df = df_full[
        (df_full['Evento'].isin(eventos)) &
        (df_full['ANIO'] >= anios_range[0]) &
        (df_full['ANIO'] <= anios_range[1])
    ].copy()

    if nivel == "Nacional":
        agg = df.groupby(['ANIO', 'SEMANA', 'Evento'])['CANTIDAD'].sum().reset_index()
    else:
        agg = df.groupby(['ANIO', 'SEMANA', 'Evento', 'Provincia'])['CANTIDAD'].sum().reset_index()

    return agg


def ccf_pairwise(series_a, series_b, max_lag=8):
    """Cross-Correlation Function entre dos series con lags -max_lag a +max_lag."""
    n = len(series_a)
    a = np.array(series_a, dtype=float)
    b = np.array(series_b, dtype=float)
    a = (a - a.mean()) / (a.std() + 1e-10)
    b = (b - b.mean()) / (b.std() + 1e-10)

    lags, corrs = [], []
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            slice_a, slice_b = a[:lag], b[-lag:]
        elif lag > 0:
            slice_a, slice_b = a[lag:], b[:-lag]
        else:
            slice_a, slice_b = a, b

        if len(slice_a) > 5:
            corr, pval = pearsonr(slice_a, slice_b)
            corrs.append(corr if not np.isnan(corr) else 0.0)
        else:
            corrs.append(0.0)
        lags.append(lag)
    return pd.DataFrame({'lag': lags, 'ccf': corrs})


def zscore_normalize(series):
    mu, sigma = series.mean(), series.std()
    return (series - mu) / (sigma + 1e-10) if sigma > 0 else series - mu


# ─── PREPARAR DATOS ────────────────────────────────────────────────────────────
agg_data = build_weekly_matrix(eventos_sel, rango_anios, nivel_geo)

# Pivot nacional
pivot_nac = agg_data.groupby(['ANIO', 'SEMANA', 'Evento'])['CANTIDAD'].sum().reset_index()
pivot_nac = pivot_nac.pivot_table(index=['ANIO', 'SEMANA'], columns='Evento',
                                   values='CANTIDAD', aggfunc='sum').fillna(0)
pivot_nac = pivot_nac.sort_index().reset_index()
pivot_nac['Idx'] = range(len(pivot_nac))
pivot_nac['Label'] = pivot_nac['ANIO'].astype(str) + '-SE' + pivot_nac['SEMANA'].astype(str).str.zfill(2)

# ─── MÉTRICAS ──────────────────────────────────────────────────────────────────
st.markdown("### 📊 Resumen de eventos seleccionados")
cols_metrics = st.columns(len(eventos_sel))
for i, ev in enumerate(eventos_sel):
    if ev in pivot_nac.columns:
        total = int(pivot_nac[ev].sum())
        media = pivot_nac[ev].mean()
        cols_metrics[i].markdown(
            f'<div class="m-card">'
            f'<div class="m-num">{total:,}'.replace(",", ".") +
            f'</div><div class="m-lbl">{ev[:22]}</div>'
            f'<div style="font-size:.7rem;color:#4a8ab5">{media:.1f} casos/sem</div></div>',
            unsafe_allow_html=True
        )
st.markdown("<br>", unsafe_allow_html=True)

# ─── TABS ──────────────────────────────────────────────────────────────────────
tab_trend, tab_ccf, tab_cooc, tab_heat, tab_senal = st.tabs([
    "📈 TENDENCIAS PARALELAS", "🔄 CCF CRUZADA", "🗺️ CO-OCURRENCIA ESPACIAL",
    "🌡️ HEATMAP DOBLE", "🔍 SEÑALES DÉBILES"
])

# ══════════════════════════════════════════════════
# TAB 1: TENDENCIAS PARALELAS NORMALIZADAS
# ══════════════════════════════════════════════════
with tab_trend:
    st.subheader("📈 Tendencias Paralelas Normalizadas (Z-score)")
    st.markdown("""<div class="info-box">
    Normalización Z-score permite comparar eventos de distinta magnitud en el mismo eje.
    Si dos curvas se mueven en paralelo → co-dinámica. Si una <strong>precede</strong> a la otra
    → posible relación causal o de amplificación que investiga la CCF.
    </div>""", unsafe_allow_html=True)

    fig_trend = go.Figure()
    palette = ['#00e5ff', '#ef4444', '#4ade80', '#f59e0b', '#a78bfa', '#f472b6']
    for i, ev in enumerate(eventos_sel):
        if ev in pivot_nac.columns:
            z = zscore_normalize(pivot_nac[ev])
            # Media móvil 4 semanas
            z_smooth = z.rolling(4, center=True, min_periods=1).mean()
            fig_trend.add_trace(go.Scatter(
                x=pivot_nac['Idx'], y=z, name=f"{ev} (raw)",
                line=dict(color=palette[i % len(palette)], width=1),
                opacity=0.3, showlegend=False, hoverinfo='skip'
            ))
            fig_trend.add_trace(go.Scatter(
                x=pivot_nac['Idx'], y=z_smooth, name=ev,
                line=dict(color=palette[i % len(palette)], width=2.5),
                hovertext=pivot_nac['Label'],
                hovertemplate=f'{ev}<br>Z: %{{y:.2f}}<br>%{{hovertext}}<extra></extra>'
            ))

    # Marcadores de años
    for anio in range(rango_anios[0], rango_anios[1] + 1):
        idx_anio = pivot_nac[pivot_nac['ANIO'] == anio]['Idx'].min()
        if not pd.isna(idx_anio):
            fig_trend.add_vline(x=idx_anio, line_dash="dot", line_color="rgba(255,255,255,0.13)",
                                annotation_text=str(anio), annotation_font_color="#4a8ab5",
                                annotation_font_size=9)

    fig_trend.add_hline(y=0, line_color="rgba(255,255,255,0.2)", line_width=1)
    fig_trend.update_layout(
        paper_bgcolor='#060a12', plot_bgcolor='#060a12',
        font=dict(color='#c8d8e8', family='Share Tech Mono'), height=440,
        legend=dict(bgcolor='rgba(6,10,18,0.85)', font=dict(color='#c8d8e8')),
        xaxis=dict(title='Índice semanal', tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c'),
        yaxis=dict(title='Z-score (4-sem suavizado)', tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c'),
        title=dict(text="Co-dinámica temporal de eventos (MM4 suavizada)", font=dict(color='#00e5ff'))
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # Correlación simple entre pares
    st.markdown("#### 🔗 Correlación de Pearson entre pares (toda la serie)")
    pares = []
    ev_cols = [e for e in eventos_sel if e in pivot_nac.columns]
    for i in range(len(ev_cols)):
        for j in range(i + 1, len(ev_cols)):
            a, b = pivot_nac[ev_cols[i]], pivot_nac[ev_cols[j]]
            if a.std() > 0 and b.std() > 0:
                r, p = pearsonr(a, b)
                pares.append({
                    'Par': f"{ev_cols[i]} ↔ {ev_cols[j]}",
                    'r de Pearson': round(r, 3),
                    'p-valor': f"{p:.4f}",
                    'Significativo (p<0.05)': '✅' if p < 0.05 else '❌',
                    'Interpretación': (
                        '🔴 Correlación inversa fuerte' if r < -0.5 else
                        '🔶 Correlación inversa débil' if r < 0 else
                        '⚠️ Sin correlación clara' if r < 0.3 else
                        '🟡 Correlación positiva débil' if r < 0.5 else
                        '🟢 Correlación positiva moderada' if r < 0.7 else
                        '🔵 Correlación positiva fuerte'
                    )
                })
    if pares:
        st.dataframe(pd.DataFrame(pares), use_container_width=True, hide_index=True)
        st.markdown("""<div class="alert-yellow">
        ⚠️ <strong>Advertencia metodológica:</strong> Una correlación alta en series temporales puede ser
        espuria por confusión con tendencias comunes (efectos de período, estacionalidad compartida).
        Usá la CCF para evaluar si existe estructura temporal, y considerá co-variables (temperatura,
        acceso a salud, condiciones socioeconómicas) antes de inferir causalidad.
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# TAB 2: CCF CRUZADA
# ══════════════════════════════════════════════════
with tab_ccf:
    st.subheader("🔄 Función de Correlación Cruzada (CCF) con Lags")
    st.markdown(f"""<div class="info-box">
    La CCF mide si el evento A en la semana t <strong>predice</strong> al evento B en la semana t+k (lag positivo).
    Un pico de correlación en lag=+4 significa que A anticipa a B por 4 semanas.
    Lags de <strong>−{max_lag} a +{max_lag}</strong> semanas analizados.
    <strong>Umbral de significancia:</strong> |r| &gt; 2/√n ≈ {2/np.sqrt(max(len(pivot_nac),1)):.3f}
    </div>""", unsafe_allow_html=True)

    ev_cols = [e for e in eventos_sel if e in pivot_nac.columns]
    if len(ev_cols) < 2:
        st.warning("Se necesitan al menos 2 eventos con datos para la CCF.")
    else:
        # Selector de par
        par_options = [f"{ev_cols[i]} → {ev_cols[j]}"
                       for i in range(len(ev_cols)) for j in range(len(ev_cols)) if i != j]
        par_sel = st.selectbox("Par de eventos (A → B)", par_options, key="s11_par_ccf")
        ev_a_name, ev_b_name = par_sel.split(" → ")

        ccf_df = ccf_pairwise(pivot_nac[ev_a_name], pivot_nac[ev_b_name], max_lag)
        sig_threshold = 2 / np.sqrt(len(pivot_nac))

        # Colores por significancia
        colors_ccf = ['#ef4444' if abs(r) > sig_threshold else '#1a3a5c' for r in ccf_df['ccf']]

        fig_ccf = go.Figure()
        # Barras CCF
        fig_ccf.add_trace(go.Bar(
            x=ccf_df['lag'], y=ccf_df['ccf'],
            marker_color=colors_ccf, name='CCF',
            hovertemplate='Lag: %{x} sem<br>r: %{y:.3f}<extra></extra>'
        ))
        fig_ccf.add_hline(y=sig_threshold, line_dash="dash", line_color="#f59e0b",
                          annotation_text=f"+sig ({sig_threshold:.3f})", annotation_font_color="#f59e0b")
        fig_ccf.add_hline(y=-sig_threshold, line_dash="dash", line_color="#f59e0b",
                          annotation_text=f"-sig ({-sig_threshold:.3f})", annotation_font_color="#f59e0b")
        fig_ccf.add_vline(x=0, line_color="rgba(255,255,255,0.27)", line_width=1)
        fig_ccf.update_layout(
            paper_bgcolor='#060a12', plot_bgcolor='#060a12',
            font=dict(color='#c8d8e8', family='Share Tech Mono'), height=380,
            xaxis=dict(title=f'Lag (semanas) — negativo: A sigue a B / positivo: A precede a B',
                       tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c', dtick=1),
            yaxis=dict(title='Correlación cruzada (r)', tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c'),
            title=dict(text=f"CCF: {ev_a_name} → {ev_b_name}", font=dict(color='#00e5ff'))
        )
        st.plotly_chart(fig_ccf, use_container_width=True)

        # Interpretación automática
        best_lag = ccf_df.loc[ccf_df['ccf'].abs().idxmax()]
        if abs(best_lag['ccf']) > sig_threshold:
            lag_v, r_v = int(best_lag['lag']), float(best_lag['ccf'])
            direccion = (f"**{ev_a_name}** anticipa a **{ev_b_name}** en {lag_v} semana(s)"
                         if lag_v > 0 else
                         f"**{ev_b_name}** anticipa a **{ev_a_name}** en {abs(lag_v)} semana(s)"
                         if lag_v < 0 else
                         "ambos eventos se mueven de forma sincrónica (lag = 0)")
            tipo_box = "signal-weak" if abs(r_v) > 0.5 else "alert-yellow"
            st.markdown(f"""<div class="{tipo_box}">
            🔍 <strong>Señal más fuerte en lag={lag_v} (r={r_v:.3f}):</strong><br>
            {direccion}.<br>
            {"Hipótesis a explorar: ¿comparten el mismo determinante social con desfase temporal? ¿Existe un efecto amplificador biológico directo? ¿O es un artefacto de notificación desfasada?" if abs(r_v) > 0.5 else "Señal débil — requerís más datos o un enfoque estratificado por provincia."}
            </div>""", unsafe_allow_html=True)
        else:
            st.info("No se detecta correlación cruzada significativa en este par para la serie completa. "
                    "Probá estratificar por provincia o por período.")

        # CCF por provincia (resumen)
        if nivel_geo == "Por Provincia" or True:
            st.markdown("#### 🗺️ Lag óptimo por Provincia")
            ccf_provs = []
            for prov in provincias_list:
                df_p = agg_data[agg_data.get('Provincia', pd.Series([None])) == prov] if 'Provincia' in agg_data.columns else agg_data
                if 'Provincia' in agg_data.columns:
                    df_p = agg_data[agg_data['Provincia'] == prov]
                    piv_p = df_p.pivot_table(index=['ANIO', 'SEMANA'], columns='Evento',
                                              values='CANTIDAD', aggfunc='sum').fillna(0).sort_index().reset_index()
                    if ev_a_name in piv_p.columns and ev_b_name in piv_p.columns and len(piv_p) > max_lag * 2:
                        ccf_p = ccf_pairwise(piv_p[ev_a_name], piv_p[ev_b_name], max_lag)
                        best = ccf_p.loc[ccf_p['ccf'].abs().idxmax()]
                        if abs(best['ccf']) > sig_threshold:
                            ccf_provs.append({
                                'Provincia': prov,
                                'Lag óptimo (sem)': int(best['lag']),
                                'r máx': round(float(best['ccf']), 3),
                                'Significativo': '✅' if abs(best['ccf']) > sig_threshold else '❌'
                            })
            if ccf_provs:
                df_ccf_prov = pd.DataFrame(ccf_provs).sort_values('r máx', ascending=False, key=abs)
                st.dataframe(df_ccf_prov, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════
# TAB 3: CO-OCURRENCIA ESPACIAL
# ══════════════════════════════════════════════════
with tab_cooc:
    st.subheader("🗺️ Score Sindémico Espacial por Provincia")
    st.markdown("""<div class="info-box">
    Para cada provincia, calcula en cuántos años <strong>ambos eventos superan simultáneamente
    su mediana histórica</strong>. Un score alto indica co-ocurrencia persistente en esa jurisdicción
    — zona de potencial interacción sindémica o de vulnerabilidad social compartida.
    </div>""", unsafe_allow_html=True)

    ev_a_cooc = st.selectbox("Evento A", [e for e in eventos_sel if e in eventos_list],
                              key="s11_cooc_a")
    ev_b_cooc = st.selectbox("Evento B", [e for e in eventos_sel if e in eventos_list and e != ev_a_cooc],
                              key="s11_cooc_b")

    score_rows = []
    for prov in provincias_list:
        df_pv = df_full[(df_full['Provincia'] == prov)].copy()
        anual_a = df_pv[df_pv['Evento'] == ev_a_cooc].groupby('ANIO')['CANTIDAD'].sum()
        anual_b = df_pv[df_pv['Evento'] == ev_b_cooc].groupby('ANIO')['CANTIDAD'].sum()

        anios_comunes = anual_a.index.intersection(anual_b.index)
        if len(anios_comunes) < 2:
            continue

        med_a = anual_a[anios_comunes].median()
        med_b = anual_b[anios_comunes].median()
        cooc_score = int(((anual_a[anios_comunes] > med_a) & (anual_b[anios_comunes] > med_b)).sum())
        total_anios = len(anios_comunes)
        pct = cooc_score / total_anios * 100 if total_anios > 0 else 0
        score_rows.append({
            'Provincia': prov, 'Score sindémico': cooc_score,
            'Años evaluados': total_anios, '% Co-ocurrencia': round(pct, 1),
            f'Total {ev_a_cooc}': int(anual_a[anios_comunes].sum()),
            f'Total {ev_b_cooc}': int(anual_b[anios_comunes].sum()),
        })

    if score_rows:
        df_score = pd.DataFrame(score_rows).sort_values('Score sindémico', ascending=False)

        fig_score = go.Figure(go.Bar(
            x=df_score['Provincia'], y=df_score['Score sindémico'],
            marker=dict(color=df_score['Score sindémico'], colorscale='YlOrRd',
                        showscale=True, colorbar=dict(title='Score', tickfont=dict(color='#c8d8e8'))),
            text=df_score['% Co-ocurrencia'].apply(lambda x: f"{x:.0f}%"),
            textposition='outside',
            hovertemplate='%{x}<br>Score: %{y} años<br>%{text} de co-ocurrencia<extra></extra>'
        ))
        fig_score.update_layout(
            paper_bgcolor='#060a12', plot_bgcolor='#060a12',
            font=dict(color='#c8d8e8', family='Share Tech Mono'), height=380,
            xaxis=dict(tickangle=-45, tickfont=dict(color='#c8d8e8', size=10), gridcolor='#1a3a5c'),
            yaxis=dict(title='Años con co-ocurrencia simultánea', tickfont=dict(color='#c8d8e8'), gridcolor='#1a3a5c'),
            title=dict(text=f"Score Sindémico: {ev_a_cooc} ∩ {ev_b_cooc}", font=dict(color='#00e5ff'))
        )
        st.plotly_chart(fig_score, use_container_width=True)

        alta_cooc = df_score[df_score['% Co-ocurrencia'] >= 60]
        if not alta_cooc.empty:
            st.markdown(f"""<div class="signal-weak">
            🔍 <strong>Señal de co-ocurrencia persistente (≥60% de los años) en:</strong>
            {', '.join(alta_cooc['Provincia'].tolist())}<br>
            Estas provincias muestran co-elevación sostenida de ambos eventos.
            Hipótesis prioritaria: determinantes sociales compartidos (hacinamiento, vulnerabilidad NBI,
            acceso limitado a salud). Requiere análisis de co-variables socioeconómicas (INDEC).
            </div>""", unsafe_allow_html=True)
        st.dataframe(df_score, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════
# TAB 4: HEATMAP DOBLE SINCRONIZADO
# ══════════════════════════════════════════════════
with tab_heat:
    st.subheader("🌡️ Heatmaps Sincronizados por Provincia × Año")
    st.markdown("""<div class="info-box">
    Dos heatmaps sincronizados: las celdas que están "encendidas" en ambos simultáneamente
    son zonas de <strong>co-ocurrencia espacio-temporal</strong>.
    </div>""", unsafe_allow_html=True)

    ev_h1 = st.selectbox("Heatmap 1 — Evento", eventos_sel, key="s11_h1")
    ev_h2 = st.selectbox("Heatmap 2 — Evento", [e for e in eventos_sel if e != ev_h1], key="s11_h2")

    def make_prov_year_pivot(ev):
        d = df_full[(df_full['Evento'] == ev) &
                    (df_full['ANIO'] >= rango_anios[0]) &
                    (df_full['ANIO'] <= rango_anios[1]) &
                    (df_full['Provincia'] != 'Sin Datos')].groupby(
            ['Provincia', 'ANIO'])['CANTIDAD'].sum().reset_index()
        return d.pivot(index='Provincia', columns='ANIO', values='CANTIDAD').fillna(0)

    piv1 = make_prov_year_pivot(ev_h1)
    piv2 = make_prov_year_pivot(ev_h2)

    col_h1, col_h2 = st.columns(2)
    for col, piv, title in [(col_h1, piv1, ev_h1), (col_h2, piv2, ev_h2)]:
        with col:
            fig_hh = go.Figure(go.Heatmap(
                z=piv.values, x=[str(c) for c in piv.columns], y=piv.index.tolist(),
                colorscale='Inferno',
                colorbar=dict(title='Casos', tickfont=dict(color='#c8d8e8'), len=0.9),
                hovertemplate='%{y}<br>Año: %{x}<br>Casos: %{z:,.0f}<extra></extra>'
            ))
            fig_hh.update_layout(
                paper_bgcolor='#060a12', plot_bgcolor='#060a12',
                font=dict(color='#c8d8e8', family='Share Tech Mono'),
                height=520, margin=dict(l=110, r=30, t=40, b=40),
                title=dict(text=title[:35], font=dict(color='#00e5ff', size=13)),
                xaxis=dict(tickfont=dict(color='#c8d8e8', size=9)),
                yaxis=dict(tickfont=dict(color='#c8d8e8', size=9))
            )
            st.plotly_chart(fig_hh, use_container_width=True)

# ══════════════════════════════════════════════════
# TAB 5: SEÑALES DÉBILES
# ══════════════════════════════════════════════════
with tab_senal:
    st.subheader("🔍 Detector de Señales Débiles y Emergentes")
    st.markdown("""<div class="info-box">
    Identifica pares evento×provincia donde la correlación temporal es alta (|r| &gt; 0.5)
    pero ocurre en zonas o combinaciones que típicamente no se monitorean juntas.
    Estas son las <strong>"señales débiles"</strong> que los sistemas reactivos ignoran.
    </div>""", unsafe_allow_html=True)

    umbral_r = st.slider("Umbral mínimo |r| para señal", 0.3, 0.9, 0.5, 0.05, key="s11_umbral_r")
    threshold_sig = 2 / np.sqrt(max(len(pivot_nac), 10))

    señales = []
    ev_cols = [e for e in eventos_sel if e in eventos_list]

    for prov in provincias_list:
        piv_p_rows = {}
        for ev in ev_cols:
            d_p = df_full[(df_full['Provincia'] == prov) & (df_full['Evento'] == ev) &
                          (df_full['ANIO'] >= rango_anios[0]) & (df_full['ANIO'] <= rango_anios[1])]
            weekly = d_p.groupby(['ANIO', 'SEMANA'])['CANTIDAD'].sum()
            piv_p_rows[ev] = weekly

        # Crear DataFrame alineado
        if len(piv_p_rows) >= 2:
            df_p_aligned = pd.DataFrame(piv_p_rows).fillna(0)
            if len(df_p_aligned) < 10:
                continue

            for i in range(len(ev_cols)):
                for j in range(i + 1, len(ev_cols)):
                    ea, eb = ev_cols[i], ev_cols[j]
                    if ea in df_p_aligned.columns and eb in df_p_aligned.columns:
                        sa, sb = df_p_aligned[ea], df_p_aligned[eb]
                        if sa.std() > 0 and sb.std() > 0 and sa.sum() > 0 and sb.sum() > 0:
                            r, p = pearsonr(sa, sb)
                            if abs(r) >= umbral_r and p < 0.05:
                                señales.append({
                                    'Provincia': prov,
                                    'Par sindémico': f"{ea} ↔ {eb}",
                                    'r': round(r, 3),
                                    'p-valor': round(p, 4),
                                    'Tipo': '🔴 Inversa' if r < -0.4 else '🟢 Directa',
                                    'Prioridad': '⭐⭐⭐ ALTA' if abs(r) > 0.7 else '⭐⭐ MEDIA'
                                })

    if señales:
        df_señ = pd.DataFrame(señales).sort_values('r', ascending=False, key=abs)
        n_high = len(df_señ[df_señ['Prioridad'] == '⭐⭐⭐ ALTA'])
        st.markdown(f"""<div class="signal-weak">
        🔍 <strong>{len(df_señ)} señales detectadas ({n_high} de alta prioridad)</strong><br>
        Estos pares evento×provincia muestran co-variación temporal estadísticamente significativa
        y no trivial. Revisalos con el equipo de epidemiología local para descartar artefactos.
        </div>""", unsafe_allow_html=True)
        st.dataframe(df_señ, use_container_width=True, hide_index=True)
        st.download_button("📥 Descargar señales débiles",
                           data=df_señ.to_csv(index=False).encode('utf-8'),
                           file_name="senales_debiles_sindemia.csv", mime='text/csv')
    else:
        st.info(f"No se detectaron señales con |r| ≥ {umbral_r} y p < 0.05. "
                f"Reducí el umbral o ampliá el rango de años.")
