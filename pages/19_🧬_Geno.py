# dashboard_genomico_completo_adaptado.py
"""
Dashboard COMPLETO de Vigilancia Genómica SARS-CoV-2
BASADO EXACTAMENTE EN TU codigo.txt - Solo adaptado a columnas del ETL
NO SE ELIMINÓ NINGUNA VISUALIZACIÓN
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import json
from scipy.stats import fisher_exact, chi2_contingency, pearsonr
import matplotlib.pyplot as plt
import seaborn as sns

def extraer_numero_mes(valor):
    """Extrae el número del mes desde diferentes formatos: '2025-01', 1, '1', etc."""
    try:
        if isinstance(valor, (int, float)):
            return int(valor)
        valor_str = str(valor)
        if '-' in valor_str:
            return int(valor_str.split('-')[1])
        return int(float(valor_str))
    except:
        return 1

# ==================== CONFIGURACIÓN ====================
st.set_page_config(
    page_title="Vigilancia Genómica SARS-CoV-2",
    page_icon="🧬",
    layout="wide"
)

# ==================== CARGA DE DATOS ====================
@st.cache_data
def load_data():
    df = pd.read_parquet('data/base_genomica.parquet')
    
    # ===== ADAPTACIÓN: Usar fecha_apertura como fecha principal =====
    if 'fecha_apertura' in df.columns:
        df['fecha_apertura'] = pd.to_datetime(df['fecha_apertura'], errors='coerce')
        df['fecha_estudio'] = df['fecha_apertura']
        df['fecha_inicio_sintoma'] = df['fecha_apertura']
        df['fecha_consulta'] = df['fecha_apertura']
    
    # Si no hay fechas reales de retrasos, crear columnas con valores por defecto
    if 'retraso_sintoma_consulta' not in df.columns:
        df['retraso_sintoma_consulta'] = 0
    if 'retraso_consulta_estudio' not in df.columns:
        df['retraso_consulta_estudio'] = 0
    if 'retraso_total' not in df.columns:
        df['retraso_total'] = 0
    if 'retraso_muestra_estudio' not in df.columns:
        df['retraso_muestra_estudio'] = 0
    
    # Agregar columnas de tiempo
    if 'fecha_estudio' in df.columns:
        df['anio'] = df['fecha_estudio'].dt.year
        df['mes'] = df['fecha_estudio'].dt.month
        df['anio_mes'] = df['fecha_estudio'].dt.to_period('M').astype(str)
        df['trimestre'] = df['fecha_estudio'].dt.quarter
        df['dia_semana'] = df['fecha_estudio'].dt.dayofweek
        df['semana_epi'] = df['fecha_estudio'].dt.isocalendar().week
        df['mes_str'] = df['fecha_estudio'].dt.to_period('M').astype(str)
    
    # Detectar comorbilidades por texto (si existe la columna)
    if 'comorbilidad' in df.columns:
        keywords_comorb = {
            'Diabetes': ['diabetes', 'dm', 'glucosa'],
            'Hipertensión': ['hipertensión', 'hta', 'presion alta'],
            'Obesidad': ['obesidad', 'sobrepeso', 'imc'],
            'Cardiopatía': ['cardio', 'corazón', 'infarto', 'insuficiencia cardiaca', 'cardiopatia'],
            'Respiratoria': ['epoc', 'asma', 'bronquitis', 'neumopatía', 'enfermedad pulmonar'],
            'Renal': ['renal', 'diálisis', 'riñón', 'insuficiencia renal'],
            'Inmunosupresión': ['inmuno', 'hiv', 'vih', 'cáncer', 'quimio', 'trasplante', 'inmunosupresor'],
            'Hepática': ['hepatico', 'higado', 'cirrosis', 'hepatitis'],
            'Neurológica': ['neurologico', 'accidente cerebrovascular', 'acv', 'parkinson', 'alzheimer']
        }
        for cond, keywords in keywords_comorb.items():
            df[cond] = df['comorbilidad'].str.lower().apply(
                lambda x: any(kw in str(x) for kw in keywords)
            ).astype(int)
    else:
        # Crear columnas de comorbilidad vacías
        for cond in ['Diabetes', 'Hipertensión', 'Obesidad', 'Cardiopatía', 'Respiratoria', 'Renal', 'Inmunosupresión', 'Hepática', 'Neurológica']:
            df[cond] = 0
    
    # Clasificación de edad en grupos más detallados
    if 'edad' in df.columns:
        bins = [-1, 0, 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59, 64, 69, 74, 79, 200]
        labels = ['<1', '1-4', '5-9', '10-14', '15-19', '20-24', '25-29', '30-34', 
                  '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', 
                  '70-74', '75-79', '80+']
        df['grupo_edad_detallado'] = pd.cut(df['edad'], bins=bins, labels=labels, right=True).astype(str)
        df.loc[df['edad'] == 0, 'grupo_edad_detallado'] = '<1'
    
    # Crear columna num_comorbilidades
    comorb_cols = ['Diabetes', 'Hipertensión', 'Obesidad', 'Cardiopatía', 'Respiratoria', 'Renal', 'Inmunosupresión', 'Hepática', 'Neurológica']
    comorb_existentes = [c for c in comorb_cols if c in df.columns]
    if comorb_existentes:
        df['num_comorbilidades'] = df[comorb_existentes].sum(axis=1)
    else:
        df['num_comorbilidades'] = 0
    
    # Asegurar columnas necesarias
    if 'cuidado_intensivo' not in df.columns:
        df['cuidado_intensivo'] = False
    if 'asistencia_respiratoria' not in df.columns:
        df['asistencia_respiratoria'] = False
    if 'vacuna_esquema_completo' not in df.columns:
        df['vacuna_esquema_completo'] = False
    if 'vacuna_dosis' not in df.columns:
        df['vacuna_dosis'] = 0
    if 'vacuna_tipo' not in df.columns:
        df['vacuna_tipo'] = 'Sin dato'
    if 'meses_desde_ultima_dosis' not in df.columns:
        df['meses_desde_ultima_dosis'] = np.nan
    if 'fallecido' not in df.columns:
        df['fallecido'] = False
    if 'fecha_fallecimiento' not in df.columns:
        df['fecha_fallecimiento'] = pd.NaT
    if 'pais_viaje' not in df.columns:
        df['pais_viaje'] = 'Sin dato'
    if 'exito_secuenciacion' not in df.columns:
        df['exito_secuenciacion'] = False
    if 'grave' not in df.columns:
        df['grave'] = False
    if 'muy_grave' not in df.columns:
        df['muy_grave'] = False
    
    return df

@st.cache_data
def load_geojson():
    try:
        with open('data/provincia.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

@st.cache_data
def load_depto_geojson():
    try:
        with open('data/departamento.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

df = load_data()
geojson = load_geojson()
geojson_depto = load_depto_geojson()

# ==================== SIDEBAR ====================
st.sidebar.header("🔬 Filtros de Análisis")

# Filtro temporal
if 'fecha_estudio' in df.columns and df['fecha_estudio'].notna().any():
    fecha_min = df['fecha_estudio'].min().date()
    fecha_max = df['fecha_estudio'].max().date()
    fecha_range = st.sidebar.date_input("📅 Rango de fechas", value=[fecha_min, fecha_max])
    if isinstance(fecha_range, (list, tuple)) and len(fecha_range) == 2:
        df = df[(df['fecha_estudio'].dt.date >= fecha_range[0]) & 
                (df['fecha_estudio'].dt.date <= fecha_range[1])]

# Filtro geográfico
provincias = ['Todas'] + sorted([str(x) for x in df['provincia'].dropna().unique().tolist() if str(x) != 'Sin Datos'])
provincia_sel = st.sidebar.selectbox("📍 Provincia", provincias)
if provincia_sel != 'Todas':
    df = df[df['provincia'] == provincia_sel]

# Filtro por departamento
if provincia_sel != 'Todas' and 'departamento' in df.columns:
    deptos = ['Todos'] + sorted([str(x) for x in df['departamento'].dropna().unique().tolist() if str(x) != 'Sin Datos'])
    depto_sel = st.sidebar.selectbox("🏘️ Departamento", deptos)
    if depto_sel != 'Todos':
        df = df[df['departamento'] == depto_sel]

# Filtro por linaje
linajes = ['Todos'] + sorted([str(x) for x in df['linaje'].dropna().unique().tolist() if str(x) not in ['Sin linaje', 'Sin dato']])
linaje_sel = st.sidebar.selectbox("🧬 Linaje", linajes)
if linaje_sel != 'Todos':
    df = df[df['linaje'] == linaje_sel]

# Filtro por clasificación manual
if 'clasificacion_manual' in df.columns:
    clasificaciones = ['Todas'] + sorted([str(x) for x in df['clasificacion_manual'].dropna().unique().tolist()])
    clasificacion_sel = st.sidebar.selectbox("🏷️ Clasificación Manual", clasificaciones)
    if clasificacion_sel != 'Todas':
        df = df[df['clasificacion_manual'] == clasificacion_sel]

# Filtro por éxito de secuenciación
if 'exito_secuenciacion' in df.columns:
    exito_filter = st.sidebar.radio("🔬 Éxito secuenciación", ["Todos", "✅ Solo exitosos", "❌ Solo fallidos"])
    if exito_filter == "✅ Solo exitosos":
        df = df[df['exito_secuenciacion'] == True]
    elif exito_filter == "❌ Solo fallidos":
        df = df[df['exito_secuenciacion'] == False]

# Filtro por sexo
if 'sexo' in df.columns:
    sexo_filter = st.sidebar.radio("👤 Sexo", ["Todos", "Femenino", "Masculino"])
    if sexo_filter == "Femenino":
        df = df[df['sexo'] == 'F']
    elif sexo_filter == "Masculino":
        df = df[df['sexo'] == 'M']

# Filtro por grupo etario
if 'grupo_etario' in df.columns:
    grupos = ['Todos'] + sorted([str(x) for x in df['grupo_etario'].dropna().unique().tolist()])
    grupo_sel = st.sidebar.selectbox("📊 Grupo etario", grupos)
    if grupo_sel != 'Todos':
        df = df[df['grupo_etario'] == grupo_sel]

st.sidebar.markdown("---")
st.sidebar.markdown(f"### 📊 Estadísticas del filtro")
st.sidebar.metric("Total registros", f"{len(df):,}")
if 'linaje' in df.columns:
    st.sidebar.metric("Linajes únicos", df['linaje'].nunique())
if 'provincia' in df.columns:
    st.sidebar.metric("Provincias", df['provincia'].nunique())

# ==================== HEADER ====================
st.title("🧬 Vigilancia Genómica SARS-CoV-2")
st.markdown(f"*Análisis epidemiológico y genómico de {len(df):,} casos secuenciados*")
st.markdown(f"*Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}*")
st.markdown("---")

# ==================== KPI CARDS ====================
col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)

with col1:
    st.metric("📊 Total", f"{len(df):,}")
with col2:
    st.metric("🧬 Linajes", df['linaje'].nunique())
with col3:
    tasa_exito = df['exito_secuenciacion'].mean() * 100 if 'exito_secuenciacion' in df.columns else 0
    st.metric("✅ Tasa éxito", f"{tasa_exito:.1f}%")
with col4:
    pct_femenino = (df['sexo'] == 'F').mean() * 100 if 'sexo' in df.columns else 0
    st.metric("👩 % Femenino", f"{pct_femenino:.1f}%")
with col5:
    pct_grave = df['grave'].mean() * 100 if 'grave' in df.columns else 0
    st.metric("🏥 % Graves", f"{pct_grave:.1f}%")
with col6:
    pct_vac = df['vacuna_esquema_completo'].mean() * 100 if 'vacuna_esquema_completo' in df.columns else 0
    st.metric("💉 % Vac. completo", f"{pct_vac:.1f}%")
with col7:
    edad_prom = df['edad'].mean() if 'edad' in df.columns else 0
    st.metric("🎂 Edad promedio", f"{edad_prom:.0f}")
with col8:
    pct_fallecidos = df['fallecido'].mean() * 100 if 'fallecido' in df.columns else 0
    st.metric("⚰️ Letalidad", f"{pct_fallecidos:.1f}%")

st.markdown("---")

# ==================== TABS PRINCIPALES ====================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "📊 Descriptivos",
    "🧬 Linajes", 
    "🏥 Gravedad",
    "💉 Vacunación",
    "🗺️ Geográfico",
    "📈 Temporal",
    "🔄 Correlaciones",
    "🚨 Alertas",
    "📋 Reporte",
    "💾 Exportar"
])

# ==========================================================
# PARTE 1: ANÁLISIS DESCRIPTIVOS BÁSICOS (COMPLETO)
# ==========================================================
with tab1:
    st.header("📊 Análisis Descriptivos Básicos")
    
    # 1.1 Perfil demográfico
    st.subheader("1.1 Perfil Demográfico")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'sexo' in df.columns:
            sexo_counts = df['sexo'].value_counts().reset_index()
            sexo_counts.columns = ['Sexo', 'Cantidad']
            fig_sexo = px.pie(sexo_counts, values='Cantidad', names='Sexo',
                              title='Distribución por Sexo',
                              color_discrete_sequence=['#ff6b6b', '#4ecdc4', '#888888'],
                              hole=0.3)
            fig_sexo.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_sexo, use_container_width=True)
    
    with col2:
        if 'grupo_etario' in df.columns:
            etario_counts = df['grupo_etario'].value_counts().reset_index()
            etario_counts.columns = ['Grupo Etario', 'Cantidad']
            fig_etario = px.bar(etario_counts, x='Grupo Etario', y='Cantidad',
                                title='Distribución por Grupo Etario',
                                color='Cantidad', 
                                color_continuous_scale='Viridis',
                                text='Cantidad')
            fig_etario.update_layout(xaxis_tickangle=-45)
            fig_etario.update_traces(textposition='outside')
            st.plotly_chart(fig_etario, use_container_width=True)
    
    if 'edad' in df.columns and 'sexo' in df.columns:
        fig_edad = px.box(df, x='sexo', y='edad', 
                          title='Distribución de Edad por Sexo',
                          color='sexo', 
                          color_discrete_sequence=['#ff6b6b', '#4ecdc4'],
                          points='all')
        st.plotly_chart(fig_edad, use_container_width=True)
    
    if 'grupo_etario' in df.columns and 'sexo' in df.columns:
        st.subheader("Tabla Resumen Demográfica")
        tabla_resumen = pd.crosstab(df['grupo_etario'], df['sexo'], margins=True)
        mapping = {'F': 'Femenino', 'M': 'Masculino', 'S/D': 'Sin Datos', 'Sin Datos': 'Sin Datos', 'All': 'Total'}
        tabla_resumen = tabla_resumen.rename(columns=mapping)
        st.dataframe(tabla_resumen, use_container_width=True)
    
    # 1.2 Éxito de secuenciación
    st.subheader("1.2 Éxito de Secuenciación")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'exito_secuenciacion' in df.columns:
            exito = df['exito_secuenciacion'].mean() * 100
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=exito,
                title={'text': "Tasa de Éxito (%)", 'font': {'size': 24}},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': "#4ecdc4"},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 50], 'color': '#ff6b6b'},
                        {'range': [50, 80], 'color': '#ffeaa7'},
                        {'range': [80, 100], 'color': '#55efc4'}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig_gauge.update_layout(height=350)
            st.plotly_chart(fig_gauge, use_container_width=True)
    
    with col2:
        exito_prov = df.groupby('provincia')['exito_secuenciacion'].agg(['mean', 'count']).reset_index()
        exito_prov.columns = ['Provincia', 'Tasa_Éxito', 'N_Casos']
        exito_prov['Tasa_Éxito'] = exito_prov['Tasa_Éxito'] * 100
        exito_prov = exito_prov[exito_prov['N_Casos'] >= 5].sort_values('Tasa_Éxito', ascending=False)
        
        if not exito_prov.empty:
            fig_exito_prov = px.bar(exito_prov.head(10), x='Provincia', y='Tasa_Éxito',
                                    title='Top 10 Provincias por Tasa de Éxito',
                                    color='Tasa_Éxito', 
                                    color_continuous_scale='RdYlGn',
                                    text='Tasa_Éxito')
            fig_exito_prov.update_layout(xaxis_tickangle=-45)
            fig_exito_prov.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(fig_exito_prov, use_container_width=True)
    
    # Evolución temporal del éxito
    if 'fecha_estudio' in df.columns:
        df['mes'] = df['fecha_estudio'].dt.to_period('M').astype(str)
        exito_mensual = df.groupby('mes')['exito_secuenciacion'].agg(['mean', 'count']).reset_index()
        exito_mensual.columns = ['Mes', 'Tasa_Exito', 'N_Casos']
        exito_mensual['Tasa_Exito'] = exito_mensual['Tasa_Exito'] * 100
        
        if not exito_mensual.empty:
            fig_exito_temporal = px.line(exito_mensual, x='Mes', y='Tasa_Exito',
                                         title='Evolución Temporal de la Tasa de Éxito',
                                         markers=True, 
                                         line_shape='spline')
            fig_exito_temporal.add_scatter(x=exito_mensual['Mes'], 
                                           y=exito_mensual['Tasa_Exito'].rolling(3, min_periods=1).mean(),
                                           mode='lines', 
                                           name='Media móvil 3 meses', 
                                           line=dict(dash='dash', color='orange'))
            st.plotly_chart(fig_exito_temporal, use_container_width=True)
    
        # 1.3 Retrasos operativos (CON MANEJO DE ERRORES)
    st.subheader("1.3 Retrasos Operativos")
    
    # Verificar si existen las columnas y si son numéricas
    retraso_sintoma_consulta = df['retraso_sintoma_consulta'] if 'retraso_sintoma_consulta' in df.columns else pd.Series([0])
    retraso_consulta_estudio = df['retraso_consulta_estudio'] if 'retraso_consulta_estudio' in df.columns else pd.Series([0])
    retraso_total = df['retraso_total'] if 'retraso_total' in df.columns else pd.Series([0])
    retraso_muestra_estudio = df['retraso_muestra_estudio'] if 'retraso_muestra_estudio' in df.columns else pd.Series([0])
    
    # Función segura para calcular mediana
    def safe_median(series):
        try:
            # Convertir a numérico, errores -> NaN
            numeric = pd.to_numeric(series, errors='coerce')
            # Filtrar solo números válidos
            valid = numeric.dropna()
            if len(valid) > 0:
                return valid.median()
            else:
                return 0
        except:
            return 0
    
    def safe_p95(series):
        try:
            numeric = pd.to_numeric(series, errors='coerce')
            valid = numeric.dropna()
            if len(valid) > 0:
                return valid.quantile(0.95)
            else:
                return 0
        except:
            return 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        med_sintoma = safe_median(retraso_sintoma_consulta)
        p95_sintoma = safe_p95(retraso_sintoma_consulta)
        st.metric("📅 Síntoma → Consulta", f"{med_sintoma:.0f} días", delta=f"P95: {p95_sintoma:.0f}")
    
    with col2:
        med_consulta = safe_median(retraso_consulta_estudio)
        p95_consulta = safe_p95(retraso_consulta_estudio)
        st.metric("🏥 Consulta → Estudio", f"{med_consulta:.0f} días", delta=f"P95: {p95_consulta:.0f}")
    
    with col3:
        med_total = safe_median(retraso_total)
        p95_total = safe_p95(retraso_total)
        st.metric("🔬 Síntoma → Resultado", f"{med_total:.0f} días", delta=f"P95: {p95_total:.0f}")
    
    with col4:
        med_muestra = safe_median(retraso_muestra_estudio)
        st.metric("🧪 Muestra → Estudio", f"{med_muestra:.0f} días")
    
    # Boxplot de retrasos por provincia (solo si hay datos válidos)
    if 'retraso_total' in df.columns:
        # Convertir a numérico
        df_temp = df.copy()
        df_temp['retraso_total_num'] = pd.to_numeric(df_temp['retraso_total'], errors='coerce')
        df_temp = df_temp[df_temp['retraso_total_num'].notna()]
        
        if not df_temp.empty:
            retraso_prov = df_temp.groupby('provincia')['retraso_total_num'].median().reset_index()
            retraso_prov = retraso_prov.sort_values('retraso_total_num', ascending=False).head(15)
            
            if not retraso_prov.empty:
                fig_retraso = px.bar(retraso_prov, x='provincia', y='retraso_total_num',
                                     title='Mediana de Retraso Total por Provincia (días)',
                                     color='retraso_total_num', 
                                     color_continuous_scale='Reds',
                                     text='retraso_total_num')
                fig_retraso.update_layout(xaxis_tickangle=-45)
                fig_retraso.update_traces(texttemplate='%{text:.0f}', textposition='outside')
                st.plotly_chart(fig_retraso, use_container_width=True)
            
            # HEATMAP de retrasos por provincia y mes
            if 'fecha_estudio' in df.columns:
                df_temp['mes_str'] = df_temp['fecha_estudio'].dt.to_period('M').astype(str)
                retraso_pivot = df_temp.groupby(['provincia', 'mes_str'])['retraso_total_num'].median().unstack()
                retraso_pivot = retraso_pivot.dropna(thresh=3)
                
                if not retraso_pivot.empty and len(retraso_pivot) > 1 and len(retraso_pivot.columns) > 1:
                    fig_heatmap_retraso = px.imshow(retraso_pivot.fillna(0),
                                                    labels=dict(x="Mes", y="Provincia", color="Días"),
                                                    title="Mediana de Retraso Total por Provincia y Mes",
                                                    color_continuous_scale='Reds',
                                                    aspect="auto",
                                                    height=max(400, len(retraso_pivot) * 25))
                    fig_heatmap_retraso.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig_heatmap_retraso, use_container_width=True)
        else:
            st.info("No hay datos suficientes para calcular retrasos operativos")
    else:
        st.info("No hay datos suficientes para calcular retrasos operativos")
    # 1.4 Análisis de fallos de secuenciación
    st.subheader("1.4 Análisis de Fallos de Secuenciación")
    
    if 'exito_secuenciacion' in df.columns:
        fallos = df[df['exito_secuenciacion'] == False]
        if len(fallos) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                fallos_prov = fallos['provincia'].value_counts().head(10).reset_index()
                fallos_prov.columns = ['Provincia', 'Fallos']
                fig_fallos = px.bar(fallos_prov, x='Provincia', y='Fallos',
                                    title='Provincias con Mayor Número de Fallos',
                                    color='Fallos', color_continuous_scale='Reds')
                fig_fallos.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_fallos, use_container_width=True)
            
            with col2:
                fallo_tasa = df.groupby('provincia').apply(
                    lambda x: len(x[x['exito_secuenciacion'] == False]) / len(x) * 100
                ).reset_index()
                fallo_tasa.columns = ['Provincia', 'Tasa_Fallo_%']
                fallo_tasa = fallo_tasa.sort_values('Tasa_Fallo_%', ascending=False).head(10)
                
                fig_tasa_fallo = px.bar(fallo_tasa, x='Provincia', y='Tasa_Fallo_%',
                                        title='Provincias con Mayor Tasa de Fallo (%)',
                                        color='Tasa_Fallo_%', color_continuous_scale='Reds')
                fig_tasa_fallo.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_tasa_fallo, use_container_width=True)
        else:
            st.success("✅ No se registraron fallos de secuenciación en el período seleccionado")
    
    # Clasificación manual
    if 'clasificacion_manual' in df.columns:
        st.subheader("1.5 Clasificación de Variantes (Manual)")
        clasif_counts = df['clasificacion_manual'].value_counts().reset_index()
        clasif_counts.columns = ['Clasificación', 'Cantidad']
        fig_clasif = px.bar(clasif_counts, x='Clasificación', y='Cantidad',
                            title='Distribución de Clasificación Manual',
                            color='Cantidad', color_continuous_scale='Viridis',
                            text='Cantidad')
        fig_clasif.update_layout(xaxis_tickangle=-45)
        fig_clasif.update_traces(textposition='outside')
        st.plotly_chart(fig_clasif, use_container_width=True)

# ==========================================================
# PARTE 2: ANÁLISIS DE LINAJES (COMPLETO CON SANKEY)
# ==========================================================
with tab2:
    st.header("🧬 Análisis de Linajes Circulantes")
    
    # 2.1 Gráfico de áreas apiladas
    st.subheader("2.1 Evolución Temporal de Linajes")
    
    if 'semana_epi' in df.columns and 'linaje' in df.columns:
        df_semanal = df.groupby(['semana_epi', 'linaje']).size().reset_index(name='count')
        total_semanal = df_semanal.groupby('semana_epi')['count'].sum().reset_index(name='total')
        df_semanal = df_semanal.merge(total_semanal, on='semana_epi')
        df_semanal['porcentaje'] = df_semanal['count'] / df_semanal['total'] * 100
        
        df_pivot = df_semanal.pivot(index='semana_epi', columns='linaje', values='porcentaje').fillna(0)
        top_linajes = df['linaje'].value_counts().head(8).index.tolist()
        top_linajes = [l for l in top_linajes if l not in ['Sin linaje', 'Sin dato']]
        
        if top_linajes:
            df_pivot_top = df_pivot[top_linajes]
            df_pivot_top['Otros'] = 100 - df_pivot_top.sum(axis=1)
            
            fig_area = px.area(df_pivot_top, 
                               title='Evolución de Linajes Circulantes (% por semana)',
                               labels={'value': 'Porcentaje', 'index': 'Semana Epidemiológica'},
                               color_discrete_sequence=px.colors.qualitative.Set3)
            fig_area.update_layout(height=500, legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
            st.plotly_chart(fig_area, use_container_width=True)
        
        # DIAGRAMA DE SANKEY (transiciones de linaje dominante) - ESTO LO TENÍAS
        st.subheader("Diagrama de Transición de Linajes")
        
        linaje_por_semana = df.groupby('semana_epi')['linaje'].agg(
            lambda x: x.mode()[0] if len(x.mode()) > 0 else 'ND'
        )
        
        transiciones = []
        for i in range(len(linaje_por_semana)-1):
            transiciones.append((linaje_por_semana.iloc[i], linaje_por_semana.iloc[i+1]))
        
        if transiciones:
            nodes = list(set([t[0] for t in transiciones] + [t[1] for t in transiciones]))
            node_indices = {node: i for i, node in enumerate(nodes)}
            links = [{'source': node_indices[s], 'target': node_indices[t], 'value': 1} for s, t in transiciones]
            
            fig_sankey = go.Figure(data=[go.Sankey(
                node=dict(label=nodes, pad=15, thickness=20, color='blue'),
                link=dict(source=[l['source'] for l in links],
                          target=[l['target'] for l in links],
                          value=[l['value'] for l in links],
                          color='rgba(0, 229, 255, 0.4)')
            )])
            fig_sankey.update_layout(title='Transición de Linaje Dominante Semana a Semana', height=500)
            st.plotly_chart(fig_sankey, use_container_width=True)
    
    # 2.2 Mapa de calor de linajes por provincia
    st.subheader("2.2 Distribución de Linajes por Provincia")
    
    if 'provincia' in df.columns and 'linaje' in df.columns:
        matriz = pd.crosstab(df['provincia'], df['linaje'])
        matriz_pct = matriz.div(matriz.sum(axis=1), axis=0) * 100
        
        top_linajes_matriz = df['linaje'].value_counts().head(10).index.tolist()
        top_linajes_matriz = [l for l in top_linajes_matriz if l not in ['Sin linaje', 'Sin dato']]
        
        if top_linajes_matriz:
            matriz_pct_top = matriz_pct[top_linajes_matriz]
            
            fig_heatmap = px.imshow(matriz_pct_top,
                                    labels=dict(x="Linaje", y="Provincia", color="%"),
                                    title="Distribución de Linajes por Provincia (%)",
                                    color_continuous_scale='Viridis',
                                    aspect="auto",
                                    height=max(400, len(matriz_pct_top) * 25))
            fig_heatmap.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # 2.3 Tabla de linaje dominante por provincia
    st.subheader("2.3 Linaje Dominante por Provincia")
    
    linaje_dominante = df.groupby('provincia')['linaje'].agg(
        lambda x: x.mode()[0] if len(x.mode()) > 0 else 'ND'
    ).reset_index()
    linaje_dominante.columns = ['provincia', 'Linaje_Dominante']
    
    freq_linaje = df.groupby(['provincia', 'linaje']).size().reset_index(name='freq')
    max_freq = freq_linaje.loc[freq_linaje.groupby('provincia')['freq'].idxmax()]
    max_freq.columns = ['provincia', 'Linaje_Dominante', 'Frecuencia']
    total_por_prov = df.groupby('provincia').size().reset_index(name='Total')
    
    tabla_dominante = max_freq.merge(total_por_prov, on='provincia')
    tabla_dominante['Porcentaje'] = (tabla_dominante['Frecuencia'] / tabla_dominante['Total'] * 100).round(1)
    tabla_dominante = tabla_dominante.rename(columns={'provincia': 'Provincia'})
    tabla_dominante = tabla_dominante[tabla_dominante['Provincia'] != 'Sin Datos']
    tabla_dominante = tabla_dominante[['Provincia', 'Linaje_Dominante', 'Frecuencia', 'Total', 'Porcentaje']]
    tabla_dominante = tabla_dominante.sort_values('Porcentaje', ascending=False)
    
    st.dataframe(tabla_dominante, use_container_width=True)
    
    # 2.4 Detección de nuevas variantes
    st.subheader("2.4 Nuevas Variantes Detectadas")
    
    if 'fecha_estudio' in df.columns:
        fecha_max = df['fecha_estudio'].max()
        fecha_limite = fecha_max - timedelta(days=14)
        
        linajes_historicos = set(df[df['fecha_estudio'] <= fecha_limite]['linaje'].unique())
        linajes_recientes = set(df[df['fecha_estudio'] > fecha_limite]['linaje'].unique())
        nuevas_variantes = linajes_recientes - linajes_historicos
        nuevas_variantes = {v for v in nuevas_variantes if v not in ['Sin linaje', 'Sin dato']}
        
        if nuevas_variantes:
            st.warning(f"🚨 **{len(nuevas_variantes)} nuevas variantes** detectadas en las últimas 2 semanas")
            for var in nuevas_variantes:
                df_var = df[df['linaje'] == var]
                fecha_primer = df_var['fecha_estudio'].min()
                provincia_primer = df_var.iloc[0]['provincia'] if not df_var.empty else 'Desconocida'
                st.info(f"**🧬 {var}** - Primer caso: {fecha_primer.strftime('%d/%m/%Y')} - Provincia: {provincia_primer} - Total: {len(df_var)}")
        else:
            st.success("✅ No se detectaron nuevas variantes en las últimas 2 semanas")
        
        st.subheader("Primeras Apariciones Históricas de Linajes")
        primeras = df.groupby('linaje')['fecha_estudio'].min().sort_values().reset_index()
        primeras.columns = ['Linaje', 'Primera_Detección']
        primeras['Primera_Detección'] = primeras['Primera_Detección'].dt.strftime('%d/%m/%Y')
        primeras = primeras[primeras['Linaje'].notna()]
        primeras = primeras[primeras['Linaje'] != 'Sin linaje']
        st.dataframe(primeras, use_container_width=True)
    
    # 2.5 Diversidad de linajes por provincia
    st.subheader("2.5 Diversidad de Linajes por Provincia")
    
    from scipy.stats import entropy
    
    def shannon_diversity(group):
        probs = group.value_counts() / len(group)
        return entropy(probs)
    
    diversidad = df.groupby('provincia')['linaje'].apply(shannon_diversity).reset_index()
    diversidad.columns = ['Provincia', 'Diversidad_Shannon']
    diversidad = diversidad.sort_values('Diversidad_Shannon', ascending=False)
    diversidad = diversidad[diversidad['Provincia'] != 'Sin Datos']
    
    if not diversidad.empty:
        fig_diversidad = px.bar(diversidad.head(15), x='Provincia', y='Diversidad_Shannon',
                                title='Diversidad de Linajes por Provincia (Índice de Shannon)',
                                color='Diversidad_Shannon', color_continuous_scale='Viridis')
        fig_diversidad.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_diversidad, use_container_width=True)

# ==========================================================
# PARTE 3: ANÁLISIS DE GRAVEDAD (COMPLETO CON ODDS RATIO)
# ==========================================================
with tab3:
    st.header("🏥 Análisis de Gravedad por Linaje")
    
    if 'grave' in df.columns:
        # 3.1 Tabla de gravedad por linaje
        st.subheader("3.1 Indicadores de Gravedad por Linaje")
        
        gravedad_linaje = df.groupby('linaje').agg({
            'grave': ['mean', 'count'],
            'muy_grave': 'mean',
            'fallecido': 'mean',
            'edad': 'mean',
            'cuidado_intensivo': 'mean',
            'asistencia_respiratoria': 'mean'
        }).round(3)
        
        gravedad_linaje.columns = ['%_Grave', 'N_Casos', '%_Muy_Grave', '%_Letalidad', 
                                   'Edad_Promedio', '%_UCI', '%_ARM']
        gravedad_linaje['%_Grave'] = gravedad_linaje['%_Grave'] * 100
        gravedad_linaje['%_Muy_Grave'] = gravedad_linaje['%_Muy_Grave'] * 100
        gravedad_linaje['%_Letalidad'] = gravedad_linaje['%_Letalidad'] * 100
        gravedad_linaje['%_UCI'] = gravedad_linaje['%_UCI'] * 100
        gravedad_linaje['%_ARM'] = gravedad_linaje['%_ARM'] * 100
        
        gravedad_linaje = gravedad_linaje[gravedad_linaje['N_Casos'] >= 5].sort_values('%_Grave', ascending=False)
        gravedad_linaje = gravedad_linaje[gravedad_linaje.index != 'Sin linaje']
        
        st.dataframe(gravedad_linaje, use_container_width=True)
        
        if not gravedad_linaje.empty:
            fig_gravedad = px.bar(gravedad_linaje.reset_index(), 
                                  x='linaje', 
                                  y=['%_Grave', '%_Muy_Grave', '%_Letalidad'],
                                  title='Indicadores de Gravedad por Linaje (%)',
                                  barmode='group',
                                  labels={'value': 'Porcentaje', 'linaje': 'Linaje', 'variable': 'Indicador'})
            fig_gravedad.update_layout(xaxis_tickangle=-45, height=500)
            st.plotly_chart(fig_gravedad, use_container_width=True)
        
        # 3.2 Odds Ratio de hospitalización (FOREST PLOT)
        st.subheader("3.2 Odds Ratio de Hospitalización")
        
        linaje_ref = df['linaje'].mode()[0] if len(df['linaje'].mode()) > 0 else df['linaje'].iloc[0]
        df['es_referencia'] = (df['linaje'] == linaje_ref).astype(int)
        
        odds_resultados = []
        for linaje in gravedad_linaje.index:
            if linaje != linaje_ref and linaje not in ['Sin linaje', 'Sin dato']:
                tabla = pd.crosstab(df['linaje'] == linaje, df['grave'])
                if tabla.shape == (2, 2) and tabla.values.min() > 0:
                    or_value, p_value = fisher_exact(tabla.values)
                    log_or = np.log(or_value)
                    se = np.sqrt(1/tabla.iloc[0,0] + 1/tabla.iloc[0,1] + 1/tabla.iloc[1,0] + 1/tabla.iloc[1,1])
                    ci_lower = np.exp(log_or - 1.96 * se)
                    ci_upper = np.exp(log_or + 1.96 * se)
                    
                    odds_resultados.append({
                        'Linaje': linaje,
                        'OR_Hospitalizacion': or_value,
                        'IC_95%_lower': ci_lower,
                        'IC_95%_upper': ci_upper,
                        'p_valor': p_value,
                        'Interpretacion': '⬆️ Mayor riesgo' if or_value > 1 else '⬇️ Menor riesgo' if or_value < 1 else '➡️ Igual'
                    })
        
        if odds_resultados:
            df_odds = pd.DataFrame(odds_resultados).sort_values('OR_Hospitalizacion', ascending=False)
            
            fig_odds = go.Figure()
            fig_odds.add_trace(go.Scatter(
                x=df_odds['OR_Hospitalizacion'],
                y=df_odds['Linaje'],
                mode='markers',
                marker=dict(size=10, color='red'),
                error_x=dict(
                    type='data',
                    symmetric=False,
                    arrayminus=df_odds['OR_Hospitalizacion'] - df_odds['IC_95%_lower'],
                    array=df_odds['IC_95%_upper'] - df_odds['OR_Hospitalizacion'],
                    color='gray'
                ),
                name='OR (IC 95%)'
            ))
            fig_odds.add_vline(x=1, line_dash="dash", line_color="gray")
            fig_odds.update_layout(
                title=f'Odds Ratio de Hospitalización (ref: {linaje_ref})',
                xaxis_title='Odds Ratio (escala logarítmica)',
                yaxis_title='Linaje',
                xaxis_type='log',
                height=400
            )
            st.plotly_chart(fig_odds, use_container_width=True)
    
    # 3.3 Gravedad por grupo etario
    st.subheader("3.3 Gravedad por Grupo Etario")
    
    if 'grupo_etario' in df.columns:
        gravedad_etario = df.groupby('grupo_etario').agg({
            'grave': 'mean',
            'muy_grave': 'mean',
            'fallecido': 'mean',
            'cuidado_intensivo': 'mean'
        }).round(3) * 100
        
        gravedad_etario = gravedad_etario.reset_index()
        gravedad_etario.columns = ['Grupo_Etario', 'Graves_%', 'Muy_Graves_%', 'Letalidad_%', 'UCI_%']
        
        fig_etario = go.Figure()
        fig_etario.add_trace(go.Bar(x=gravedad_etario['Grupo_Etario'], y=gravedad_etario['Graves_%'], name='Graves', marker_color='#ff6b6b'))
        fig_etario.add_trace(go.Bar(x=gravedad_etario['Grupo_Etario'], y=gravedad_etario['Muy_Graves_%'], name='Muy Graves', marker_color='#ffaa44'))
        fig_etario.add_trace(go.Bar(x=gravedad_etario['Grupo_Etario'], y=gravedad_etario['Letalidad_%'], name='Letalidad', marker_color='#ff4444'))
        fig_etario.update_layout(
            title='Indicadores de Gravedad por Grupo Etario (%)',
            xaxis_title='Grupo Etario',
            yaxis_title='Porcentaje',
            barmode='group',
            xaxis_tickangle=-45,
            height=500
        )
        st.plotly_chart(fig_etario, use_container_width=True)
    
    # 3.4 Comorbilidades (COMPLETO)
    st.subheader("3.4 Análisis de Comorbilidades")
    
    comorb_cols = ['Diabetes', 'Hipertensión', 'Obesidad', 'Cardiopatía', 'Respiratoria', 'Renal', 'Inmunosupresión', 'Hepática', 'Neurológica']
    comorb_existentes = [c for c in comorb_cols if c in df.columns and df[c].sum() > 0]
    
    if comorb_existentes:
        st.write("**Prevalencia de comorbilidades por linaje (%)**")
        comorb_linaje = df.groupby('linaje')[comorb_existentes].mean().round(3) * 100
        st.dataframe(comorb_linaje, use_container_width=True)
        
        comorb_total = df[comorb_existentes].mean().reset_index()
        comorb_total.columns = ['Comorbilidad', 'Prevalencia_%']
        comorb_total['Prevalencia_%'] = comorb_total['Prevalencia_%'] * 100
        comorb_total = comorb_total.sort_values('Prevalencia_%', ascending=True)
        
        fig_comorb = px.bar(comorb_total, x='Prevalencia_%', y='Comorbilidad',
                            title='Prevalencia de Comorbilidades en la Población',
                            color='Prevalencia_%', color_continuous_scale='Viridis',
                            orientation='h')
        st.plotly_chart(fig_comorb, use_container_width=True)
        
        # Riesgo relativo por comorbilidad
        st.subheader("Riesgo Relativo de Hospitalización por Comorbilidad")
        
        rr_resultados = []
        for comorb in comorb_existentes:
            if df[comorb].sum() > 5:
                rr = (df[df[comorb] == 1]['grave'].mean()) / (df[df[comorb] == 0]['grave'].mean())
                rr_resultados.append({
                    'Comorbilidad': comorb,
                    'Riesgo_Relativo': rr,
                    'Casos_con_comorb': df[comorb].sum()
                })
        
        if rr_resultados:
            df_rr = pd.DataFrame(rr_resultados).sort_values('Riesgo_Relativo', ascending=False)
            
            fig_rr = px.bar(df_rr, x='Comorbilidad', y='Riesgo_Relativo',
                            title='Riesgo Relativo de Hospitalización por Comorbilidad',
                            color='Riesgo_Relativo', color_continuous_scale='Reds',
                            text='Riesgo_Relativo')
            fig_rr.add_hline(y=1, line_dash="dash", line_color="gray")
            fig_rr.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            st.plotly_chart(fig_rr, use_container_width=True)
        
        # Pacientes con múltiples comorbilidades
        st.subheader("Pacientes con Múltiples Comorbilidades")
        df['num_comorbilidades'] = df[comorb_existentes].sum(axis=1)
        
        col1, col2 = st.columns(2)
        with col1:
            mult_comorb = df['num_comorbilidades'].value_counts().sort_index().reset_index()
            mult_comorb.columns = ['N° Comorbilidades', 'Pacientes']
            fig_mult = px.bar(mult_comorb, x='N° Comorbilidades', y='Pacientes',
                              title='Distribución de Número de Comorbilidades por Paciente',
                              color='Pacientes', color_continuous_scale='Viridis')
            st.plotly_chart(fig_mult, use_container_width=True)
        
        with col2:
            grave_por_comorb = df.groupby('num_comorbilidades')['grave'].mean().reset_index()
            grave_por_comorb.columns = ['N° Comorbilidades', 'Tasa_Gravedad']
            grave_por_comorb['Tasa_Gravedad'] = grave_por_comorb['Tasa_Gravedad'] * 100
            
            fig_grave_comorb = px.line(grave_por_comorb, x='N° Comorbilidades', y='Tasa_Gravedad',
                                       title='Tasa de Gravedad según Número de Comorbilidades',
                                       markers=True)
            st.plotly_chart(fig_grave_comorb, use_container_width=True)

# ==========================================================
# PARTE 4: ANÁLISIS DE VACUNACIÓN (COMPLETO)
# ==========================================================
with tab4:
    st.header("💉 Análisis de Vacunación por Linaje")
    
    if 'vacuna_tipo' in df.columns:
        st.subheader("4.1 Cobertura Vacunal por Linaje")
        
        vacunacion_linaje = df.groupby('linaje').agg({
            'vacuna_esquema_completo': 'mean',
            'vacuna_dosis': 'mean'
        }).round(3)
        vacunacion_linaje.columns = ['%_Esquema_Completo', 'Dosis_Promedio']
        vacunacion_linaje['%_Esquema_Completo'] = vacunacion_linaje['%_Esquema_Completo'] * 100
        vacunacion_linaje = vacunacion_linaje[vacunacion_linaje['Dosis_Promedio'] > 0]
        vacunacion_linaje = vacunacion_linaje[vacunacion_linaje.index != 'Sin linaje']
        
        st.dataframe(vacunacion_linaje, use_container_width=True)
        
        st.subheader("4.2 Distribución de Tipos de Vacuna")
        
        col1, col2 = st.columns(2)
        
        with col1:
            vacuna_dist = df['vacuna_tipo'].value_counts().reset_index()
            vacuna_dist.columns = ['Vacuna', 'Cantidad']
            if not vacuna_dist.empty:
                fig_vacuna = px.pie(vacuna_dist, values='Cantidad', names='Vacuna',
                                    title='Distribución de Tipos de Vacuna',
                                    color_discrete_sequence=px.colors.qualitative.Set3,
                                    hole=0.3)
                fig_vacuna.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_vacuna, use_container_width=True)
        
        with col2:
            if not vacunacion_linaje.empty:
                vacuna_linaje = pd.crosstab(df['linaje'], df['vacuna_tipo'], normalize='index') * 100
                top_linajes_vac = df['linaje'].value_counts().head(5).index.tolist()
                top_linajes_vac = [l for l in top_linajes_vac if l not in ['Sin linaje', 'Sin dato']]
                if top_linajes_vac:
                    vacuna_linaje_top = vacuna_linaje.loc[top_linajes_vac]
                    fig_vacuna_linaje = px.bar(vacuna_linaje_top.reset_index().melt(id_vars='linaje'),
                                               x='linaje', y='value', color='vacuna_tipo',
                                               title='Distribución de Vacunas por Linaje (%)',
                                               barmode='stack')
                    fig_vacuna_linaje.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig_vacuna_linaje, use_container_width=True)
        
        # 4.3 Efectividad vacunal
        st.subheader("4.3 Efectividad Vacunal contra Hospitalización")
        
        if 'grave' in df.columns:
            efectividad = []
            for linaje in df['linaje'].unique():
                if linaje in ['Sin linaje', 'Sin dato']:
                    continue
                df_l = df[df['linaje'] == linaje]
                if len(df_l) >= 10:
                    vac = df_l[df_l['vacuna_esquema_completo'] == True]
                    no_vac = df_l[df_l['vacuna_esquema_completo'] == False]
                    
                    if len(no_vac) > 0:
                        tasa_hosp_vac = vac['grave'].mean() if len(vac) > 0 else 0
                        tasa_hosp_no_vac = no_vac['grave'].mean()
                        
                        if tasa_hosp_no_vac > 0:
                            ef = (1 - tasa_hosp_vac / tasa_hosp_no_vac) * 100
                            efectividad.append({
                                'Linaje': linaje,
                                'Efectividad_%': ef,
                                'N_Vacunados': len(vac),
                                'N_No_Vacunados': len(no_vac)
                            })
            
            if efectividad:
                df_efectividad = pd.DataFrame(efectividad).sort_values('Efectividad_%', ascending=False)
                
                fig_ef = px.bar(df_efectividad, x='Linaje', y='Efectividad_%',
                                title='Efectividad Vacunal contra Hospitalización por Linaje (%)',
                                color='Efectividad_%', color_continuous_scale='RdYlGn',
                                text='Efectividad_%')
                fig_ef.add_hline(y=0, line_dash="dash", line_color="gray")
                fig_ef.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_ef.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_ef, use_container_width=True)
        
        # 4.4 Tiempo desde última dosis
        if 'meses_desde_ultima_dosis' in df.columns:
            st.subheader("4.4 Tiempo desde Última Dosis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                df_temp = df[df['linaje'] != 'Sin linaje']
                if not df_temp.empty:
                    fig_tiempo = px.box(df_temp, x='linaje', y='meses_desde_ultima_dosis',
                                        title='Meses desde Última Dosis por Linaje',
                                        color='linaje')
                    fig_tiempo.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig_tiempo, use_container_width=True)
            
            with col2:
                df_vac = df[df['meses_desde_ultima_dosis'].notna()]
                if len(df_vac) > 10:
                    fig_relacion = px.scatter(df_vac, x='meses_desde_ultima_dosis', y='grave',
                                              title='Relación entre Tiempo desde Vacuna y Gravedad',
                                              color='linaje',
                                              opacity=0.6,
                                              trendline='lowess')
                    fig_relacion.update_layout(yaxis_title='Gravedad (0/1)', xaxis_title='Meses desde última dosis')
                    st.plotly_chart(fig_relacion, use_container_width=True)
        
        # 4.5 Esquema completo por grupo etario
        st.subheader("4.5 Cobertura Vacunal por Grupo Etario")
        
        if 'grupo_etario' in df.columns:
            vac_etario = df.groupby('grupo_etario')['vacuna_esquema_completo'].mean().reset_index()
            vac_etario.columns = ['Grupo_Etario', 'Cobertura_Vacunal_%']
            vac_etario['Cobertura_Vacunal_%'] = vac_etario['Cobertura_Vacunal_%'] * 100
            
            fig_vac_etario = px.bar(vac_etario, x='Grupo_Etario', y='Cobertura_Vacunal_%',
                                    title='Cobertura de Esquema Completo por Grupo Etario (%)',
                                    color='Cobertura_Vacunal_%', color_continuous_scale='Viridis')
            fig_vac_etario.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_vac_etario, use_container_width=True)

# ==========================================================
# PARTE 5: ANÁLISIS GEOGRÁFICO (COMPLETO CON MAPA DEPARTAMENTAL)
# ==========================================================
with tab5:
    st.header("🗺️ Análisis Geográfico")
    
    # 5.1 Mapa de casos por provincia
    if geojson:
        st.subheader("5.1 Mapa de Casos por Provincia")
        
        casos_prov = df['provincia'].value_counts().reset_index()
        casos_prov.columns = ['Provincia', 'Casos']
        casos_prov = casos_prov[casos_prov['Provincia'] != 'Sin Datos']
        
        provincias_ids = {
            'CABA': '02', 'Buenos Aires': '06', 'Catamarca': '10', 'Chaco': '22',
            'Chubut': '26', 'Córdoba': '14', 'Corrientes': '18', 'Entre Ríos': '30',
            'Formosa': '34', 'Jujuy': '38', 'La Pampa': '42', 'La Rioja': '46',
            'Mendoza': '50', 'Misiones': '54', 'Neuquén': '58', 'Río Negro': '62',
            'Salta': '66', 'San Juan': '70', 'San Luis': '74', 'Santa Cruz': '78',
            'Santa Fe': '82', 'Santiago del Estero': '86', 'Tierra del Fuego': '94', 'Tucumán': '90'
        }
        
        casos_prov['id'] = casos_prov['Provincia'].map(provincias_ids)
        casos_prov = casos_prov.dropna(subset=['id'])
        
        if not casos_prov.empty:
            fig_map = px.choropleth_mapbox(
                casos_prov, 
                geojson=geojson, 
                locations='id', 
                featureidkey="properties.in1",
                color='Casos', 
                title='Distribución de Casos Secuenciados por Provincia',
                mapbox_style='carto-positron', 
                center={"lat": -38.4161, "lon": -63.6167},
                zoom=3.5, 
                color_continuous_scale='Viridis',
                hover_data={'Casos': ':.0f'}
            )
            fig_map.update_layout(height=600, margin={"r":0,"t":40,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)
    
    # 5.2 Mapa de calor por departamento
    if geojson_depto and 'departamento' in df.columns and len(df['departamento'].unique()) > 5:
        st.subheader("5.2 Mapa de Casos por Departamento")
        casos_depto = df['departamento'].value_counts().head(30).reset_index()
        casos_depto.columns = ['Departamento', 'Casos']
        st.info("Para visualización completa por departamento se requiere un archivo GeoJSON de departamentos")
        fig_depto_map = px.bar(casos_depto, x='Departamento', y='Casos',
                               title='Top 30 Departamentos con más Casos',
                               color='Casos', color_continuous_scale='Viridis')
        fig_depto_map.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_depto_map, use_container_width=True)
    
    # 5.3 Top departamentos
    st.subheader("5.3 Top Departamentos con Mayor Número de Casos")
    
    if 'departamento' in df.columns:
        top_deptos = df['departamento'].value_counts().head(15).reset_index()
        top_deptos.columns = ['Departamento', 'Casos']
        top_deptos = top_deptos[top_deptos['Departamento'] != 'Sin Datos']
        if not top_deptos.empty:
            fig_deptos = px.bar(top_deptos, x='Departamento', y='Casos',
                                title='Top 15 Departamentos con más Casos Secuenciados',
                                color='Casos', color_continuous_scale='Viridis',
                                text='Casos')
            fig_deptos.update_layout(xaxis_tickangle=-45)
            fig_deptos.update_traces(textposition='outside')
            st.plotly_chart(fig_deptos, use_container_width=True)
    
    # 5.4 Importación de variantes por país
    st.subheader("5.4 Importación de Variantes")
    
    if 'pais_viaje' in df.columns:
        viajes = df[df['pais_viaje'] != 'Sin dato']
        
        if not viajes.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                viajes_pais = viajes['pais_viaje'].value_counts().head(10).reset_index()
                viajes_pais.columns = ['País', 'Casos']
                fig_viajes = px.bar(viajes_pais, x='País', y='Casos',
                                    title='Top 10 Países de Origen de Casos Importados',
                                    color='Casos', color_continuous_scale='Oranges',
                                    text='Casos')
                fig_viajes.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_viajes, use_container_width=True)
            
            with col2:
                viajes_linaje = pd.crosstab(viajes['pais_viaje'], viajes['linaje']).head(10)
                fig_viajes_linaje = px.imshow(viajes_linaje,
                                              labels=dict(x="Linaje", y="País", color="Casos"),
                                              title="Importación de Variantes por País de Origen",
                                              color_continuous_scale='Oranges',
                                              aspect="auto")
                fig_viajes_linaje.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_viajes_linaje, use_container_width=True)
            
            if 'fecha_estudio' in df.columns:
                viajes['mes'] = viajes['fecha_estudio'].dt.to_period('M').astype(str)
                viajes_mensual = viajes.groupby(['mes', 'pais_viaje']).size().reset_index(name='casos')
                top_paises = viajes['pais_viaje'].value_counts().head(5).index.tolist()
                viajes_mensual_top = viajes_mensual[viajes_mensual['pais_viaje'].isin(top_paises)]
                
                if not viajes_mensual_top.empty:
                    fig_viajes_temporal = px.line(viajes_mensual_top, x='mes', y='casos', color='pais_viaje',
                                                  title='Evolución de Casos Importados por País de Origen',
                                                  markers=True)
                    st.plotly_chart(fig_viajes_temporal, use_container_width=True)
        else:
            st.info("No se registraron casos con antecedentes de viaje en el período seleccionado")

# ==========================================================
# PARTE 6: ANÁLISIS TEMPORAL AVANZADO (COMPLETO)
# ==========================================================
with tab6:
    st.header("📈 Análisis Temporal Avanzado")
    
    # 6.1 Serie temporal de casos
    st.subheader("6.1 Serie Temporal de Casos Secuenciados")
    
    if 'semana_epi' in df.columns:
        casos_semana = df['semana_epi'].value_counts().sort_index().reset_index()
        casos_semana.columns = ['Semana', 'Casos']
        
        fig_serie = go.Figure()
        fig_serie.add_trace(go.Scatter(
            x=casos_semana['Semana'], 
            y=casos_semana['Casos'],
            mode='lines+markers',
            name='Casos semanales',
            line=dict(color='#00e5ff', width=2),
            marker=dict(size=8, color='#00e5ff')
        ))
        fig_serie.add_trace(go.Scatter(
            x=casos_semana['Semana'], 
            y=casos_semana['Casos'].rolling(3, min_periods=1).mean(),
            mode='lines',
            name='Media móvil 3 semanas',
            line=dict(color='orange', width=2, dash='dash')
        ))
        fig_serie.update_layout(
            title='Casos Secuenciados por Semana Epidemiológica',
            xaxis_title='Semana Epidemiológica',
            yaxis_title='N° de Casos',
            height=450
        )
        st.plotly_chart(fig_serie, use_container_width=True)
    
    # 6.2 Velocidad de reemplazo de variantes
    st.subheader("6.2 Velocidad de Reemplazo de Variantes")
    
    if 'semana_epi' in df.columns and 'linaje' in df.columns:
        dominante_por_semana = df.groupby('semana_epi')['linaje'].agg(
            lambda x: x.mode()[0] if len(x.mode()) > 0 else 'ND'
        ).reset_index()
        dominante_por_semana.columns = ['Semana', 'Linaje_Dominante']
        
        cambios = []
        for i in range(1, len(dominante_por_semana)):
            if dominante_por_semana.iloc[i]['Linaje_Dominante'] != dominante_por_semana.iloc[i-1]['Linaje_Dominante']:
                cambios.append({
                    'Semana': dominante_por_semana.iloc[i]['Semana'],
                    'Linaje_Anterior': dominante_por_semana.iloc[i-1]['Linaje_Dominante'],
                    'Linaje_Nuevo': dominante_por_semana.iloc[i]['Linaje_Dominante']
                })
        
        if cambios:
            st.info(f"🔄 Se detectaron **{len(cambios)} cambios** en el linaje dominante")
            st.dataframe(pd.DataFrame(cambios), use_container_width=True)
        
        # Tiempo para alcanzar 50% de prevalencia
        st.subheader("Tiempo para alcanzar 50% de prevalencia")
        
        df_semanal_prev = df.groupby(['semana_epi', 'linaje']).size().reset_index(name='count')
        total_semanal_prev = df_semanal_prev.groupby('semana_epi')['count'].sum().reset_index(name='total')
        df_semanal_prev = df_semanal_prev.merge(total_semanal_prev, on='semana_epi')
        df_semanal_prev['prevalencia'] = df_semanal_prev['count'] / df_semanal_prev['total'] * 100
        
        tiempo_50 = []
        for linaje in df['linaje'].unique():
            if linaje in ['Sin linaje', 'Sin dato']:
                continue
            df_l = df_semanal_prev[df_semanal_prev['linaje'] == linaje].sort_values('semana_epi')
            if len(df_l) > 0:
                semana_50 = df_l[df_l['prevalencia'] >= 50]['semana_epi'].min()
                if pd.notna(semana_50):
                    primera_semana = df_l['semana_epi'].min()
                    tiempo_50.append({
                        'Linaje': linaje,
                        'Primera_Aparicion': primera_semana,
                        'Semana_50%': semana_50,
                        'Semanas_para_50%': semana_50 - primera_semana
                    })
        
        if tiempo_50:
            df_tiempo_50 = pd.DataFrame(tiempo_50).sort_values('Semanas_para_50%')
            st.dataframe(df_tiempo_50, use_container_width=True)
            
            fig_tiempo_50 = px.bar(df_tiempo_50, x='Linaje', y='Semanas_para_50%',
                                   title='Semanas necesarias para alcanzar 50% de prevalencia',
                                   color='Semanas_para_50%', color_continuous_scale='Viridis')
            fig_tiempo_50.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_tiempo_50, use_container_width=True)
    
        # 6.3 Análisis por estacionalidad
    st.subheader("6.3 Análisis de Estacionalidad")
    
    if 'mes' in df.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            # Crear una copia y limpiar la columna mes
            casos_mes = df.groupby('mes').size().reset_index(name='casos')
            
            # Función segura para extraer el número del mes
            def extraer_numero_mes(valor):
                try:
                    # Si es número, convertir a int
                    if isinstance(valor, (int, float)):
                        return int(valor)
                    # Si es string, intentar convertir
                    valor_str = str(valor)
                    # Si tiene formato '2025-01', extraer la parte después del guion
                    if '-' in valor_str:
                        return int(valor_str.split('-')[1])
                    # Si es solo un número en string
                    return int(float(valor_str))
                except:
                    return 1  # valor por defecto
            
            casos_mes['mes_num'] = casos_mes['mes'].apply(extraer_numero_mes)
            meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
            casos_mes['Mes_Nombre'] = casos_mes['mes_num'].apply(lambda x: meses_nombres[x-1] if 1 <= x <= 12 else str(x))
            
            fig_mes = px.bar(casos_mes, x='Mes_Nombre', y='casos',
                             title='Distribución de Casos por Mes',
                             color='casos', color_continuous_scale='Viridis')
            st.plotly_chart(fig_mes, use_container_width=True)
        
        with col2:
            if 'grave' in df.columns:
                # Crear una copia y limpiar la columna mes para gravedad
                gravedad_mes = df.groupby('mes')['grave'].mean().reset_index()
                gravedad_mes.columns = ['mes', 'tasa_gravedad']
                gravedad_mes['tasa_gravedad'] = gravedad_mes['tasa_gravedad'] * 100
                gravedad_mes['mes_num'] = gravedad_mes['mes'].apply(extraer_numero_mes)
                gravedad_mes['Mes_Nombre'] = gravedad_mes['mes_num'].apply(lambda x: meses_nombres[x-1] if 1 <= x <= 12 else str(x))
                
                fig_grave_mes = px.line(gravedad_mes, x='Mes_Nombre', y='tasa_gravedad',
                                        title='Tasa de Gravedad por Mes (%)',
                                        markers=True)
                st.plotly_chart(fig_grave_mes, use_container_width=True)

# ==========================================================
# PARTE 7: CORRELACIONES (COMPLETO)
# ==========================================================
with tab7:
    st.header("🔄 Análisis de Correlaciones")
    
    # 7.1 Matriz de correlación
    st.subheader("7.1 Matriz de Correlación")
    
    vars_numericas = []
    if 'edad' in df.columns:
        vars_numericas.append('edad')
    if 'vacuna_dosis' in df.columns:
        vars_numericas.append('vacuna_dosis')
    if 'num_comorbilidades' in df.columns and df['num_comorbilidades'].sum() > 0:
        vars_numericas.append('num_comorbilidades')
    
    if len(vars_numericas) >= 2:
        corr_matrix = df[vars_numericas].corr()
        
        fig_corr = px.imshow(corr_matrix,
                             labels=dict(x="Variable", y="Variable", color="Correlación"),
                             title="Matriz de Correlación entre Variables Numéricas",
                             color_continuous_scale='RdBu',
                             zmin=-1, zmax=1)
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("No hay suficientes variables numéricas para calcular correlaciones")
    
    # 7.2 Autocorrelación temporal
    st.subheader("7.2 Correlación Temporal (Autocorrelación)")
    
    if 'semana_epi' in df.columns:
        casos_serie = df['semana_epi'].value_counts().sort_index()
        
        if len(casos_serie) > 5:
            from scipy.signal import correlate
            
            autocorr = np.correlate(casos_serie.values, casos_serie.values, mode='full')
            autocorr = autocorr[autocorr.size // 2:]
            autocorr = autocorr / autocorr[0]
            
            lags = range(len(autocorr))
            
            fig_autocorr = go.Figure()
            fig_autocorr.add_trace(go.Bar(x=list(lags)[:20], y=autocorr[:20], name='Autocorrelación'))
            fig_autocorr.add_hline(y=0.5, line_dash="dash", line_color="red", 
                                  annotation_text="Umbral significativo (0.5)")
            fig_autocorr.update_layout(
                title='Autocorrelación de la Serie de Casos',
                xaxis_title='Lag (semanas)',
                yaxis_title='Autocorrelación',
                height=400
            )
            st.plotly_chart(fig_autocorr, use_container_width=True)

# ==========================================================
# PARTE 8: SISTEMA DE ALERTAS (COMPLETO)
# ==========================================================
with tab8:
    st.header("🚨 Sistema de Alertas Tempranas")
    
    alertas = []
    fecha_actual = datetime.now()
    
    # Alerta 1: Nuevas variantes (últimas 2 semanas)
    if 'fecha_estudio' in df.columns:
        fecha_limite = fecha_actual - timedelta(days=14)
        df_reciente = df[df['fecha_estudio'] > fecha_limite]
        
        linajes_historicos = set(df[df['fecha_estudio'] <= fecha_limite]['linaje'].unique())
        linajes_recientes = set(df_reciente['linaje'].unique())
        nuevas_variantes = linajes_recientes - linajes_historicos
        nuevas_variantes = {v for v in nuevas_variantes if v not in ['Sin linaje', 'Sin dato']}
        
        for var in nuevas_variantes:
            df_var = df_reciente[df_reciente['linaje'] == var]
            alertas.append({
                'Tipo': '🆕 NUEVA VARIANTE',
                'Linaje': var,
                'Detalle': f'Primera detección: {df_var["fecha_estudio"].min().strftime("%d/%m/%Y")}',
                'Severidad': 'ALTA',
                'Recomendacion': 'Notificar a vigilancia epidemiológica. Incrementar secuenciación.'
            })
    
    # Alerta 2: Aumento de gravedad
    if 'grave' in df.columns:
        tasa_global = df['grave'].mean()
        for linaje in df['linaje'].unique():
            if linaje in ['Sin linaje', 'Sin dato']:
                continue
            df_l = df[df['linaje'] == linaje]
            if len(df_l) >= 10:
                tasa_linaje = df_l['grave'].mean()
                if tasa_linaje > tasa_global * 1.5:
                    alertas.append({
                        'Tipo': '⚠️ AUMENTO GRAVEDAD',
                        'Linaje': linaje,
                        'Detalle': f'Tasa hospitalización: {tasa_linaje*100:.1f}% (global: {tasa_global*100:.1f}%)',
                        'Severidad': 'MEDIA',
                        'Recomendacion': 'Evaluar necesidad de refuerzos vacunales.'
                    })
    
    # Alerta 3: Expansión rápida de variante
    if 'semana_epi' in df.columns:
        ultimas_semanas = df['semana_epi'].max()
        semanas_anteriores = ultimas_semanas - 2
        
        for linaje in df['linaje'].unique():
            if linaje in ['Sin linaje', 'Sin dato']:
                continue
            df_l = df[df['linaje'] == linaje]
            casos_recientes = len(df_l[df_l['semana_epi'] > semanas_anteriores])
            casos_anteriores = len(df_l[df_l['semana_epi'] <= semanas_anteriores])
            
            if casos_anteriores > 0 and casos_recientes > casos_anteriores * 2:
                alertas.append({
                    'Tipo': '📈 EXPANSIÓN RÁPIDA',
                    'Linaje': linaje,
                    'Detalle': f'Creció de {casos_anteriores} a {casos_recientes} casos en 2 semanas',
                    'Severidad': 'MEDIA',
                    'Recomendacion': 'Monitorear expansión. Activar vigilancia en zonas con alta circulación.'
                })
    
    # Alerta 4: Baja tasa de secuenciación en provincia
    if 'exito_secuenciacion' in df.columns:
        exito_prov_alerta = df.groupby('provincia')['exito_secuenciacion'].mean().reset_index()
        exito_prov_alerta = exito_prov_alerta[exito_prov_alerta['exito_secuenciacion'] < 0.7]
        for _, row in exito_prov_alerta.iterrows():
            if row['provincia'] != 'Sin Datos':
                alertas.append({
                    'Tipo': '🔬 BAJA TASA SECUENCIACIÓN',
                    'Linaje': row['provincia'],
                    'Detalle': f'Tasa de éxito: {row["exito_secuenciacion"]*100:.1f}%',
                    'Severidad': 'BAJA',
                    'Recomendacion': 'Revisar cadena de frío y calidad de muestras en la provincia.'
                })
    
    # Mostrar alertas
    if alertas:
        st.warning(f"🚨 **{len(alertas)} alertas activas**")
        for alerta in alertas:
            color = "#ff4444" if alerta['Severidad'] == 'ALTA' else ("#ffaa44" if alerta['Severidad'] == 'MEDIA' else "#44ff44")
            st.markdown(f"""
            <div style="border-left: 4px solid {color}; background: #1a1a2e; padding: 15px; margin: 10px 0; border-radius: 8px;">
                <strong style="color: {color};">{alerta['Tipo']}</strong><br>
                <strong>🧬 {alerta['Linaje']}</strong><br>
                <strong>📋 Detalle:</strong> {alerta['Detalle']}<br>
                <strong>⚠️ Severidad:</strong> <span style="color: {color};">{alerta['Severidad']}</span><br>
                <strong>💡 Recomendación:</strong> {alerta['Recomendacion']}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ **No hay alertas activas en este momento**")
        st.balloons()

# ==========================================================
# PARTE 9: REPORTE EJECUTIVO
# ==========================================================
with tab9:
    st.header("📋 Reporte Ejecutivo de Vigilancia Genómica")
    
    min_date = df['fecha_estudio'].min() if 'fecha_estudio' in df.columns else pd.NaT
    max_date = df['fecha_estudio'].max() if 'fecha_estudio' in df.columns else pd.NaT
    
    reporte = f"""# INFORME EJECUTIVO - VIGILANCIA GENÓMICA SARS-CoV-2

## 📅 Período analizado
**Desde:** {min_date.strftime('%d/%m/%Y') if pd.notna(min_date) else 'Sin datos'}
**Hasta:** {max_date.strftime('%d/%m/%Y') if pd.notna(max_date) else 'Sin datos'}

## 📊 Resumen General
| Indicador | Valor |
|-----------|-------|
| Total de casos secuenciados | **{len(df):,}** |
| Provincias con datos | **{df['provincia'].nunique()}** |
| Linajes detectados | **{df['linaje'].nunique()}** |
| Tasa de éxito de secuenciación | **{df['exito_secuenciacion'].mean()*100:.1f}%** |

## 🏥 Indicadores Clínicos
| Indicador | Valor |
|-----------|-------|
| Porcentaje de casos graves | **{df['grave'].mean()*100:.1f}%** |
| Porcentaje de casos muy graves (UCI/ARM) | **{df['muy_grave'].mean()*100:.1f}%** |
| Letalidad | **{df['fallecido'].mean()*100:.1f}%** |
| Edad promedio | **{df['edad'].mean():.0f} años** |

## 💉 Vacunación
| Indicador | Valor |
|-----------|-------|
| Porcentaje con esquema completo | **{df['vacuna_esquema_completo'].mean()*100:.1f}%** |
| Dosis promedio | **{df['vacuna_dosis'].mean():.1f}** |

## 🧬 Linajes Principales
"""
    
    for linaje, count in df['linaje'].value_counts().head(5).items():
        if linaje not in ['Sin linaje', 'Sin dato']:
            reporte += f"- **{linaje}**: {count} casos ({count/len(df)*100:.1f}%)\n"
    
    st.markdown(reporte)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Descargar Reporte (Markdown)",
            data=reporte,
            file_name=f"reporte_genomica_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True
        )

# ==========================================================
# PARTE 10: EXPORTAR DATOS
# ==========================================================
with tab10:
    st.header("💾 Exportar Datos Filtrados")
    
    st.markdown("""
    ### Opciones de exportación
    
    Puedes descargar los datos actualmente filtrados en diferentes formatos para análisis externos.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📄 Descargar como CSV (Excel compatible)",
            data=csv_data,
            file_name=f"datos_genomica_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        try:
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Datos_Genomicos', index=False)
            excel_data = output.getvalue()
            st.download_button(
                label="📊 Descargar como Excel",
                data=excel_data,
                file_name=f"datos_genomica_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except:
            st.info("Para exportar a Excel, instala openpyxl: `pip install openpyxl`")
    
    st.subheader("Vista previa de los datos a exportar")
    st.dataframe(df.head(100), use_container_width=True)
    st.markdown(f"**Total de registros a exportar:** {len(df):,}")
    st.markdown(f"**Columnas incluidas:** {len(df.columns)}")

# ==================== FOOTER ====================
st.markdown("---")
st.markdown(
    "<center><small>🧬 Sistema de Vigilancia Genómica SARS-CoV-2 | Datos actualizados automáticamente</small></center>",
    unsafe_allow_html=True
)