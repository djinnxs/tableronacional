# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import streamlit.components.v1 as stc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time, re, json
from datetime import datetime
from osint_engine import (
    detectar_tipo_query, generar_variaciones_username,
    buscar_inaturalist, buscar_gbif, buscar_wayback,
    construir_timeline, analizar_paises_visitados,
    analizar_velocidad_desplazamiento, generar_enlaces_osint,
    ejecutar_analisis_completo
)
from utils import format_df_spanish

st.set_page_config(page_title="Epi-Seek - Motor de Inteligencia Epidemiológica", page_icon="🧬", layout="wide")

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');
html,body,[class*="css"]{font-family:'Rajdhani',sans-serif}
.stApp{background:#060a12;color:#c8d8e8}
h1,h2,h3{font-family:'Share Tech Mono',monospace!important;color:#00e5ff!important}
.hero-box{background:linear-gradient(135deg,#0a1628 0%,#0d2040 50%,#0a1628 100%);border:1px solid #00e5ff22;border-left:4px solid #00e5ff;border-radius:6px;padding:18px 22px;margin:10px 0;font-family:'Share Tech Mono',monospace;font-size:.82rem;color:#8ecae6}
.alert-box{background:linear-gradient(135deg,#1a0a0a,#2a0a0a);border:1px solid #ef444444;border-left:4px solid #ef4444;border-radius:6px;padding:14px 18px;margin:8px 0;color:#fca5a5;font-family:'Share Tech Mono',monospace;font-size:.8rem}
.stat-card{background:linear-gradient(135deg,#0d1b2a,#112233);border:1px solid #1a3a5c;border-radius:8px;padding:16px;text-align:center;transition:all .3s}
.stat-card:hover{border-color:#00e5ff;transform:translateY(-2px);box-shadow:0 4px 20px #00e5ff22}
.stat-num{font-size:2.2rem;font-weight:700;color:#00e5ff;font-family:'Share Tech Mono',monospace;line-height:1}
.stat-label{font-size:.72rem;color:#4a8ab5;font-family:'Share Tech Mono',monospace;letter-spacing:.08em;margin-top:4px}
.link-row{display:flex;align-items:center;gap:10px;padding:8px 12px;border-bottom:1px solid #1a2a3c;transition:background .2s}
.link-row:hover{background:#0d2040}
.link-cat{font-size:.68rem;padding:2px 8px;border-radius:3px;font-family:'Share Tech Mono',monospace;font-weight:700;letter-spacing:.06em;white-space:nowrap}
a.olink{color:#00e5ff;text-decoration:none;font-size:.85rem}
a.olink:hover{text-decoration:underline;color:#38bdf8}
div.stButton>button{background:linear-gradient(90deg,#023e8a,#0077b6);color:#fff;border:1px solid #00b4d8;border-radius:4px;font-family:'Share Tech Mono',monospace;font-size:1rem;padding:12px 32px;letter-spacing:.08em;transition:all .2s}
div.stButton>button:hover{background:linear-gradient(90deg,#0077b6,#00b4d8);box-shadow:0 0 16px #00e5ff44;transform:translateY(-1px)}
div[data-baseweb="input"] input{background:#0d1b2a!important;border:1px solid #1a3a5c!important;color:#c8d8e8!important;font-family:'Share Tech Mono',monospace!important;font-size:.95rem!important;border-radius:4px!important}
div[data-baseweb="input"] input:focus{border-color:#00e5ff!important;box-shadow:0 0 8px #00e5ff33!important}
.stProgress>div>div>div>div{background:linear-gradient(90deg,#00e5ff,#0077b6)}
[data-testid="metric-container"]{background:#0d1b2a;border:1px solid #1a3a5c;border-radius:6px;padding:12px}
.stTabs [data-baseweb="tab"]{background:#0d1b2a;border-radius:4px;padding:8px 16px;font-family:'Share Tech Mono',monospace}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#023e8a,#0077b6);color:#00e5ff}
hr{border-color:#1a3a5c!important}
</style>""", unsafe_allow_html=True)

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown("""<div style="border-bottom:2px solid #00e5ff22;padding-bottom:16px;margin-bottom:20px">
<h1 style="margin:0;font-size:1.9rem;letter-spacing:.06em">🧬 EPI-SEEK - MOTOR DE INTELIGENCIA EPIDEMIOLÓGICA</h1>
<p style="color:#4a8ab5;font-family:'Share Tech Mono',monospace;font-size:.78rem;margin:4px 0 0">
Extracción activa de datos · Geolocalización GPS real · Trayectoria de desplazamiento · Cruce multifuente · Detección de Caso 0
</p></div>""", unsafe_allow_html=True)

st.markdown("""<div class="hero-box">
⚠️ <strong>HERRAMIENTA DE INVESTIGACIÓN EPIDEMIOLÓGICA - USO AUTORIZADO</strong><br>
• Extrae datos <strong>reales</strong> de APIs públicas (iNaturalist, GBIF, Wayback Machine)<br>
• Construye <strong>trayectorias GPS</strong> con fechas para rastrear movimientos del sujeto<br>
• Analiza <strong>velocidad de desplazamiento</strong> para detectar viajes internacionales<br>
• Los resultados pueden compartirse con ministerios de salud de otros países para <strong>contención de brotes</strong>
</div>""", unsafe_allow_html=True)

st.markdown("---")

# ─── INPUT ────────────────────────────────────────────────────────────────────
col_in, col_btn = st.columns([4, 1])
with col_in:
    query = st.text_input("Dato a investigar", placeholder="Nombre, usuario, DNI, email, IP, teléfono...", label_visibility="collapsed", key="osint_q")
with col_btn:
    buscar = st.button("🧬 EJECUTAR ANÁLISIS PROFUNDO", use_container_width=True)

if query and query.strip():
    tipo = detectar_tipo_query(query.strip())
    iconos = {'documento':'🆔','cuit':'🏢','email':'✉️','ip':'🌐','telefono':'📞','usuario':'👤','url':'🔗'}
    st.info(f"📌 Tipo detectado: {iconos.get(tipo,'🔍')} **{tipo.upper()}** - Se usarán {len(generar_variaciones_username(query.strip()))} variaciones de búsqueda")

st.markdown("---")

# ─── EJECUCIÓN ────────────────────────────────────────────────────────────────
if buscar and query and query.strip():
    q = query.strip()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(pct, msg):
        progress_bar.progress(pct)
        status_text.text(f"⏳ {msg}")
    
    with st.spinner("Ejecutando análisis profundo..."):
        resultados = ejecutar_analisis_completo(q, progress_callback=update_progress)
    
    progress_bar.empty()
    status_text.empty()
    
    stats = resultados['stats']
    df_inat = resultados['inaturalist']
    df_gbif = resultados['gbif']
    timeline = resultados['timeline']
    desplaz = resultados['desplazamientos']
    paises = resultados['paises']
    wayback = resultados['wayback']
    enlaces = resultados['enlaces']
    
    cuit_data = resultados.get('cuitonline', [])

    # ─── ESTADÍSTICAS RESUMEN ─────────────────────────────────────────────
    if stats['tiene_datos_reales']:
        st.markdown("""<div class="alert-box">
        🚨 <strong>¡DATOS REALES ENCONTRADOS!</strong> - Se extrajeron observaciones con coordenadas GPS y datos de identidad.
        Estos datos permiten reconstruir la trayectoria geográfica e identidad del sujeto investigado.
        </div>""", unsafe_allow_html=True)
    
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    cards = [
        (c1, str(stats['total_observaciones']), "OBSERVACIONES"),
        (c2, str(stats['total_geolocalizadas']), "CON GPS"),
        (c3, str(stats['total_paises']), "PAÍSES"),
        (c4, str(stats['total_identidades']), "IDENTIDADES"),
        (c5, str(len(df_inat)), "iNATURALIST"),
        (c6, str(len(df_gbif)), "GBIF"),
        (c7, str(stats['total_wayback']), "WAYBACK"),
    ]
    for col, num_val, label in cards:
        try:
            val = int(num_val)
            formatted_num = f"{val:,}".replace(",", ".")
        except:
            formatted_num = num_val
            
        with col:
            st.markdown(f'<div class="stat-card"><div class="stat-num">{formatted_num}</div><div class="stat-label">{label}</div></div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ─── TABS PRINCIPALES ─────────────────────────────────────────────────
    tab_map, tab_timeline, tab_desp, tab_ident, tab_inat, tab_gbif, tab_links, tab_wb, tab_report = st.tabs([
        "🗺️ MAPA TRAYECTORIA", "📅 TIMELINE", "✈️ DESPLAZAMIENTOS", "🆔 IDENTIDAD",
        "🌿 iNATURALIST", "🧬 GBIF", "🔗 ENLACES OSINT",
        "🗄️ WAYBACK", "📋 INFORME"
    ])
    
    # ═══ TAB: MAPA DE TRAYECTORIA ═══════════════════════════════════════
    with tab_map:
        if not timeline.empty:
            st.subheader(f"🗺️ Trayectoria geográfica - {len(timeline)} puntos GPS")
            
            fig = go.Figure()
            
            tl_sorted = timeline.dropna(subset=['lat','lon']).sort_values('Fecha')
            if len(tl_sorted) > 1:
                fig.add_trace(go.Scattermapbox(
                    lat=tl_sorted['lat'], lon=tl_sorted['lon'],
                    mode='lines', name='Trayectoria',
                    line=dict(width=2, color='#ff6b6b'),
                    hoverinfo='skip'
                ))
            
            hover_text = []
            for _, r in tl_sorted.iterrows():
                fecha_str = r['Fecha'].strftime('%Y-%m-%d') if pd.notna(r['Fecha']) else 'Sin fecha'
                hover_text.append(f"📍 {r.get('Lugar','')}<br>📅 {fecha_str}<br>🌿 {r.get('Especie','')}<br>📡 {r.get('Plataforma','')}")
            
            fig.add_trace(go.Scattermapbox(
                lat=tl_sorted['lat'], lon=tl_sorted['lon'],
                mode='markers', name='Observaciones',
                marker=dict(size=10, color='#00e5ff', opacity=0.9),
                text=hover_text, hoverinfo='text'
            ))
            
            if len(tl_sorted) >= 2:
                first = tl_sorted.iloc[0]
                last = tl_sorted.iloc[-1]
                fig.add_trace(go.Scattermapbox(
                    lat=[first['lat']], lon=[first['lon']],
                    mode='markers', name='PRIMER registro',
                    marker=dict(size=16, color='#4ade80', symbol='circle'),
                    text=[f"🟢 PRIMER registro<br>{first.get('Lugar','')}"], hoverinfo='text'
                ))
                fig.add_trace(go.Scattermapbox(
                    lat=[last['lat']], lon=[last['lon']],
                    mode='markers', name='ÚLTIMO registro',
                    marker=dict(size=16, color='#ef4444', symbol='circle'),
                    text=[f"🔴 ÚLTIMO registro<br>{last.get('Lugar','')}"], hoverinfo='text'
                ))
            
            fig.update_layout(
                mapbox_style="carto-darkmatter",
                mapbox=dict(
                    zoom=2,
                    center=dict(lat=tl_sorted['lat'].mean(), lon=tl_sorted['lon'].mean())
                ),
                margin=dict(r=0, t=0, l=0, b=0), 
                height=600,
                legend=dict(x=0, y=1, bgcolor='rgba(10,20,30,0.8)', font=dict(color='#c8d8e8'))
            )
            st.plotly_chart(fig, use_container_width=True)
            
            if paises:
                st.subheader("🌍 Países / Regiones detectadas")
                pais_data = []
                for p, info in paises.items():
                    pais_data.append({
                        'País/Región': p,
                        'Registros': info['registros'],
                        'Primera vez': info['primera_vez'],
                        'Última vez': info['ultima_vez'],
                    })
                st.dataframe(format_df_spanish(pd.DataFrame(pais_data).sort_values('Registros', ascending=False)),
                           use_container_width=True, hide_index=True)
        else:
            st.warning("No se encontraron datos de geolocalización para este sujeto. Revisá los enlaces OSINT para buscar manualmente.")
    
    # ═══ TAB: TIMELINE ═══════════════════════════════════════════════════
    with tab_timeline:
        if not timeline.empty:
            st.subheader("📅 Línea temporal de actividad")
            
            tl_chart = timeline.dropna(subset=['Fecha']).copy()
            if not tl_chart.empty:
                tl_chart['Fecha_str'] = tl_chart['Fecha'].dt.strftime('%Y-%m-%d')
                
                fig_tl = px.scatter(
                    tl_chart, x='Fecha', y='Plataforma',
                    color='Plataforma', hover_data=['Lugar', 'Especie'],
                    title='Actividad en el tiempo',
                    color_discrete_map={'iNaturalist': '#a3e635', 'GBIF': '#38bdf8'}
                )
                fig_tl.update_layout(
                    plot_bgcolor='#0a0e1a', paper_bgcolor='#0a0e1a',
                    font_color='#c8d8e8', height=350
                )
                st.plotly_chart(fig_tl, use_container_width=True)
                
                tl_chart['Mes'] = tl_chart['Fecha'].dt.to_period('M').astype(str)
                monthly = tl_chart.groupby('Mes').size().reset_index(name='Registros')
                fig_bar = px.bar(monthly, x='Mes', y='Registros', title='Actividad por mes',
                               color='Registros', color_continuous_scale='viridis')
                fig_bar.update_layout(plot_bgcolor='#0a0e1a', paper_bgcolor='#0a0e1a',
                                     font_color='#c8d8e8', height=300)
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # Timeline con enlaces en nueva pestaña
            timeline_display = timeline[['Fecha','Lugar','Especie','Plataforma','URL']].sort_values('Fecha', ascending=False).copy()
            if 'URL' in timeline_display.columns:
                timeline_display['URL'] = timeline_display['URL'].apply(
                    lambda x: f'<a href="{x}" target="_blank" rel="noopener noreferrer">🔗 Ver</a>' if pd.notna(x) else ''
                )
            st.markdown(timeline_display.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info("Sin datos de timeline.")
    
    # ═══ TAB: DESPLAZAMIENTOS ═════════════════════════════════════════════
    with tab_desp:
        if not desplaz.empty:
            st.subheader("✈️ Análisis de desplazamientos")
            
            sosp = desplaz[desplaz['Sospechoso'] == True]
            if not sosp.empty:
                st.markdown(f"""<div class="alert-box">
                🚨 <strong>{len(sosp)} desplazamientos de alta velocidad detectados</strong> - 
                Posibles vuelos internacionales/nacionales que indican viajes del sujeto.
                </div>""", unsafe_allow_html=True)
            
            st.dataframe(format_df_spanish(desplaz), use_container_width=True, hide_index=True,
                        column_config={
                            "Distancia_km": st.column_config.NumberColumn("📏 Dist (km)", format="%.1f"),
                            "Velocidad_kmh": st.column_config.NumberColumn("⚡ Vel (km/h)", format="%.1f"),
                            "Sospechoso": st.column_config.CheckboxColumn("🚨 Vuelo?"),
                        })
        else:
            st.info("Datos insuficientes para análisis de desplazamiento (se necesitan al menos 2 observaciones geolocalizadas).")
    
    # ═══ TAB: IDENTIDAD (CuitOnline) ═════════════════════════════════════
    with tab_ident:
        if cuit_data:
            st.subheader(f"🆔 Identidades encontradas - {len(cuit_data)} registros")
            for res in cuit_data:
                with st.container():
                    st.markdown(f"### {res['Nombre']}")
                    ic1, ic2, ic3 = st.columns(3)
                    ic1.write(f"**CUIT/DNI:** {res['CUIT']}")
                    ic2.write(f"**Tipo:** {res['Tipo']}")
                    # Perfil en nueva pestaña
                    ic3.markdown(f'**Página:** <a href="{res["URL"]}" target="_blank" rel="noopener noreferrer">🔗 Ver Perfil</a>', unsafe_allow_html=True)
                    
                    if res.get('Detalles'):
                        det = res['Detalles']
                        with st.expander("Ver detalles de domicilio y ubicación", expanded=True):
                            st.write(f"**Dirección:** {det.get('Direccion', 'No disponible')}")
                            st.write(f"**Localidad/Provincia:** {det.get('Localidad', '---')} ({det.get('Provincia', '')})")
                            st.write(f"**Género:** {det.get('Genero', '---')}")
                            st.write(f"**Nacionalidad:** {det.get('Nacionalidad', '---')}")
                    st.divider()
        else:
            st.info("No se encontraron registros de identidad detallados. Probá buscando por CUIT o DNI exacto.")
 
    # ═══ TAB: iNATURALIST (con enlaces en nueva pestaña) ═════════════════════════════
    with tab_inat:
        if not df_inat.empty:
            st.subheader(f"🌿 iNaturalist - {len(df_inat)} observaciones encontradas")
            
            cols_show = [c for c in ['Fecha','Lugar','Especie','Calidad','Usuario','URL'] if c in df_inat.columns]
            df_inat_display = df_inat[cols_show].copy()
            if 'URL' in df_inat_display.columns:
                df_inat_display['URL'] = df_inat_display['URL'].apply(
                    lambda x: f'<a href="{x}" target="_blank" rel="noopener noreferrer">🔗 Ver observación</a>' if pd.notna(x) else ''
                )
            st.markdown(df_inat_display.to_html(escape=False, index=False), unsafe_allow_html=True)
            
            if 'Especie' in df_inat.columns:
                esp = df_inat['Especie'].value_counts().head(15).reset_index()
                esp.columns = ['Especie', 'Cantidad']
                fig_esp = px.bar(esp, x='Cantidad', y='Especie', orientation='h',
                               title='Top 15 especies observadas', color='Cantidad',
                               color_continuous_scale='greens')
                fig_esp.update_layout(plot_bgcolor='#0a0e1a', paper_bgcolor='#0a0e1a',
                                     font_color='#c8d8e8', height=400)
                st.plotly_chart(fig_esp, use_container_width=True)
        else:
            st.info("No se encontraron observaciones en iNaturalist.")
    
    # ═══ TAB: GBIF (con enlaces en nueva pestaña) ═══════════════════════════════════
    with tab_gbif:
        if not df_gbif.empty:
            st.subheader(f"🧬 GBIF - {len(df_gbif)} registros de biodiversidad")
            
            cols_show = [c for c in ['Fecha','Lugar','Pais','Especie','Institucion','URL'] if c in df_gbif.columns]
            df_gbif_display = df_gbif[cols_show].copy()
            if 'URL' in df_gbif_display.columns:
                df_gbif_display['URL'] = df_gbif_display['URL'].apply(
                    lambda x: f'<a href="{x}" target="_blank" rel="noopener noreferrer">🔗 Ver registro</a>' if pd.notna(x) else ''
                )
            st.markdown(df_gbif_display.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info("No se encontraron registros en GBIF.")
    
    # ═══ TAB: ENLACES OSINT (CORREGIDO - TODOS ABREN EN NUEVA PESTAÑA) ═══════════════
    with tab_links:
        st.subheader(f"🔗 {len(enlaces)} enlaces de investigación generados")
        
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #1a3a5c 0%, #00e5ff 100%); padding: 10px; border-radius: 8px; margin-bottom: 20px; text-align: center; border: 1px solid #00e5ff55;">
            <span style="color: white; font-weight: 800; letter-spacing: 1px;">🚀 MOTOR DE BÚSQUEDA POTENCIADO x1.000.000 - MODO ELITE ACTIVADO</span>
        </div>
        """, unsafe_allow_html=True)

        for e in enlaces:
            if "github.com/mgaitan/cuitonline" in e['url']:
                st.info("💡 **RECOMENDACIÓN PRO:** Se ha incluido el motor de **CuitOnline** (mgaitan/cuitonline) para búsquedas profundas de personas y CUITs en Argentina.")

        cats = sorted(set(e['cat'] for e in enlaces))
        for cat in cats:
            with st.expander(f"{cat} - {sum(1 for e in enlaces if e['cat']==cat)} fuentes", expanded=True):
                for e in sorted([x for x in enlaces if x['cat']==cat], key=lambda x: x['prioridad']):
                    prio_color = "#00e5ff" if e['prioridad'] == 1 else "#4a8ab5"
                    st.markdown(
                        f'<div style="display:flex; align-items:center; gap:12px; padding:8px 12px; border-bottom:1px solid #1a2a3c;">'
                        f'<span style="color:{prio_color}; font-size:.9rem; min-width:180px; font-weight:600">{e["nombre"]}</span>'
                        f'<a href="{e["url"]}" target="_blank" rel="noopener noreferrer" style="color:#4ade80; text-decoration:none;">🔗 Abrir en nueva pestaña →</a>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
    
    # ═══ TAB: WAYBACK (con enlaces en nueva pestaña) ════════════════════════════════
    with tab_wb:
        if wayback:
            st.subheader(f"🗄️ {len(wayback)} perfiles encontrados en Wayback Machine")
            wb_df = pd.DataFrame(wayback)
            wb_display = wb_df.copy()
            if 'URL_Archivo' in wb_display.columns:
                wb_display['URL_Archivo'] = wb_display['URL_Archivo'].apply(
                    lambda x: f'<a href="{x}" target="_blank" rel="noopener noreferrer">📦 Ver captura</a>' if pd.notna(x) else ''
                )
            st.markdown(wb_display[['URL_Original', 'URL_Archivo', 'Fecha_Captura']].to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info("No se encontraron capturas archivadas de perfiles.")
    
    # ═══ TAB: INFORME ═════════════════════════════════════════════════════
    with tab_report:
        st.subheader("📋 Informe de Inteligencia Epidemiológica")
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        report = f"""# INFORME DE INTELIGENCIA EPIDEMIOLÓGICA
## Generado: {now}
## Sujeto: {q} (Tipo: {resultados['tipo']})

### RESUMEN EJECUTIVO
- Observaciones totales extraídas: {stats['total_observaciones']}
- Puntos con GPS exacto: {stats['total_geolocalizadas']}
- Países/Regiones detectadas: {stats['total_paises']}
- Perfiles archivados (Wayback): {stats['total_wayback']}
- Identidades detectadas (CuitOnline): {stats['total_identidades']}
- Variaciones de usuario probadas: {len(resultados['variaciones'])}

### IDENTIDAD Y LOCALIZACIÓN (CuitOnline)
"""
        if cuit_data:
            for res in cuit_data:
                report += f"- **{res['Nombre']}** (CUIT: {res['CUIT']})\n"
                if res.get('Detalles'):
                    det = res['Detalles']
                    report += f"  - Domicilio: {det.get('Direccion','')}, {det.get('Localidad','')} ({det.get('Provincia','')})\n"
        else:
            report += "- No se encontraron datos de identidad detallados.\n"

        report += "\n### PAÍSES/REGIONES VISITADOS\n"
        if paises:
            for p, info in sorted(paises.items(), key=lambda x: -x[1]['registros']):
                report += f"- **{p}**: {info['registros']} registros\n"
        else:
            report += "- Sin datos geográficos\n"
        
        report += "\n### DESPLAZAMIENTOS SOSPECHOSOS (posibles vuelos)\n"
        if not desplaz.empty:
            for _, d in desplaz[desplaz.get('Sospechoso', False) == True].iterrows():
                report += f"- {d.get('Desde','')} → {d.get('Hasta','')}: {d.get('Distancia_km',0)} km en {d.get('Horas',0)} hrs\n"
        else:
            report += "- Sin datos suficientes\n"
        
        report += f"\n### VARIACIONES DE USUARIO PROBADAS\n"
        for v in resultados['variaciones'][:10]:
            report += f"- `{v}`\n"
        
        st.markdown(report)
        
        st.download_button("📥 DESCARGAR INFORME (.md)", data=report,
                          file_name=f"informe_epi_{re.sub(r'[^a-z0-9]','_',q.lower())}_{now.replace(':','').replace(' ','_')}.md",
                          mime="text/markdown", use_container_width=True)
        
        if not timeline.empty:
            csv = timeline.to_csv(index=False).encode('utf-8')
            st.download_button("📥 DESCARGAR DATOS GPS (.csv)", data=csv,
                              file_name=f"gps_{re.sub(r'[^a-z0-9]','_',q.lower())}.csv",
                              mime="text/csv", use_container_width=True)

elif buscar:
    st.warning("⚠️ Ingresá un dato de búsqueda.")

# ─── GUÍA ─────────────────────────────────────────────────────────────────────
with st.expander("📖 GUÍA DE USO PARA INVESTIGACIÓN EPIDEMIOLÓGICA"):
    st.markdown("""
### 🎯 Estrategia para detección de Caso 0

**1. Identificar al sujeto** - Ingresá nombre, usuario, DNI o email.

**2. Analizar trayectoria GPS** - El mapa muestra puntos reales extraídos de iNaturalist y GBIF.
La línea roja conecta los puntos cronológicamente mostrando el recorrido.

**3. Detectar viajes** - La pestaña "Desplazamientos" detecta saltos geográficos >900 km/h
que indican vuelos internacionales.

**4. Cruzar con brotes conocidos** - Comparar fechas y ubicaciones del sujeto con zonas de brote.

**5. Compartir con otros ministerios** - Exportar informe y datos GPS para coordinación internacional.

### 🔑 Fuentes con datos GPS reales
| Fuente | Datos | Cobertura |
|--------|-------|-----------|
| iNaturalist | Observaciones de naturaleza con coordenadas exactas | Global |
| GBIF | Registros de biodiversidad de museos y field work | Global |
| eBird | Listas de observación de aves con GPS | Global |
| Strava/Wikiloc | Rutas GPS de actividad física | Global |

### ⚡ Tips de búsqueda
- Probá con **nombre completo** y con **username** por separado
- La herramienta genera automáticamente variaciones (john.smith, jsmith, john_smith, etc.)
- Para personas con actividad en naturaleza (ornitólogos, biólogos) los resultados son más ricos
""")

if __name__ == "__main__":
    pass