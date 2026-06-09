# etl_semanal_genomica.py
"""
ETL Semanal - Base de Vigilancia Genómica SARS-CoV-2
Procesa el archivo VM_SNVS_GENOMICA.csv y genera un Parquet optimizado.
Versión completa con todas las funcionalidades.
"""

import pandas as pd
import numpy as np
import os
import unicodedata
import re
from datetime import datetime

def clean_text(v):
    """Limpia y normaliza texto: elimina caracteres especiales, normaliza Unicode."""
    if pd.isna(v):
        return "Sin Datos"
    v = str(v).replace('\xad', '')  # eliminar guion blando
    v = re.sub(r'\s+', ' ', v)       # múltiples espacios a uno
    return unicodedata.normalize('NFC', v).strip()

def parse_fecha_apertura(fecha_str):
    """
    Convierte fecha de FECHA_APERTURA que viene como "14-04-2025 00:00"
    Retorna solo la parte de fecha (YYYY-MM-DD)
    """
    if pd.isna(fecha_str) or str(fecha_str).strip() == '':
        return pd.NaT
    try:
        # Si viene con hora "14-04-2025 00:00"
        fecha_limpia = str(fecha_str).split(' ')[0]  # toma solo "14-04-2025"
        return pd.to_datetime(fecha_limpia, format='%d-%m-%Y', errors='coerce')
    except:
        try:
            return pd.to_datetime(str(fecha_str), format='%d-%m-%Y', errors='coerce')
        except:
            try:
                return pd.to_datetime(str(fecha_str), format='%d/%m/%Y', errors='coerce')
            except:
                return pd.NaT

def extraer_id_geografico(id_localidad, tipo):
    """
    Extrae ID geográfico de ID_LOCALIDAD_MUESTRA (formato: 14 dígitos)
    tipo: 'provincia' -> primeros 2 dígitos
          'departamento' -> primeros 5 dígitos
    Retorna string con ceros a la izquierda
    """
    if pd.isna(id_localidad) or str(id_localidad).strip() == '':
        return "00" if tipo == 'provincia' else "00000"
    
    # Limpiar: convertir a string, eliminar decimales
    id_str = str(id_localidad).strip()
    if '.' in id_str:
        id_str = id_str.split('.')[0]
    
    if tipo == 'provincia':
        if len(id_str) >= 2:
            return id_str[:2].zfill(2)
        else:
            return id_str.zfill(2)
    else:  # departamento
        if len(id_str) >= 5:
            return id_str[:5].zfill(5)
        else:
            return id_str.zfill(5)

def clasificar_variante_manual(clasificacion):
    """
    Clasifica la variante según CLASIFICACION_MANUAL
    Valores comunes: "Variante Ómicron confirmada por secuenciación", 
                     "En estudio", "No fue posible obtener secuencia"
    """
    if pd.isna(clasificacion):
        return "Sin clasificar"
    
    texto = str(clasificacion).lower()
    
    if "ómicron" in texto or "omicron" in texto:
        if "confirmada" in texto:
            return "Ómicron confirmada"
        else:
            return "Ómicron"
    elif "delta" in texto:
        return "Delta"
    elif "gamma" in texto:
        return "Gamma"
    elif "alfa" in texto or "alpha" in texto:
        return "Alpha"
    elif "beta" in texto:
        return "Beta"
    elif "no fue posible" in texto:
        return "Fallo secuenciación"
    elif "en estudio" in texto:
        return "En estudio"
    else:
        return clean_text(clasificacion)

def extraer_linaje_desde_resultado(resultado):
    """
    Extrae linaje desde RESULTADO (ej: "Omicron KP.3.1.1 (VUM)")
    """
    if pd.isna(resultado) or str(resultado).strip() == '':
        return "Sin linaje"
    
    texto = str(resultado)
    
    # Limpiar y extraer
    texto_limpio = texto.replace('"', '').strip()
    
    # Eliminar contenido entre paréntesis para el linaje principal
    sin_parentesis = re.sub(r'\s*\([^)]*\)', '', texto_limpio)
    
    # Si está vacío después de limpiar, devolver texto original
    if not sin_parentesis.strip():
        return texto_limpio[:50]
    
    return sin_parentesis.strip()[:50]

def run_etl():
    # ==================== CONFIGURACIÓN DE RUTAS ====================
    input_path = os.path.join('data', 'VM_SNVS_GENOMICA.csv')
    prov_path = os.path.join('data', 'Provincias.csv')
    depto_path = os.path.join('data', 'Departamentos.csv')
    output_path = os.path.join('data', 'base_genomica.parquet')
    
    # Verificar que el archivo existe
    if not os.path.exists(input_path):
        print(f"❌ ERROR: No se encuentra el archivo {input_path}")
        print("Verificar el nombre del archivo en 'data/'")
        return
    
    # ==================== LECTURA ====================
    print(f"📂 Leyendo {input_path} con encoding=latin-1...")
    df = pd.read_csv(input_path, sep=';', encoding='latin-1', low_memory=False)
    df.columns = df.columns.str.strip()
    print(f"✅ Filas originales: {len(df):,}")
    print(f"📋 Columnas disponibles: {list(df.columns)[:20]}...")
    
    # ==================== LIMPIEZA INICIAL ====================
    # Reemplazar valores vacíos (sin usar case parameter que causa error)
    df = df.replace(r'^\s*$', pd.NA, regex=True)
    df = df.replace(r'^\*sin dato\*$', pd.NA, regex=True)
    df = df.replace(r'^\*SIN DATO\*$', pd.NA, regex=True)
    
    # ==================== PROCESAMIENTO DE FECHA (FECHA_APERTURA) ====================
    print("📅 Procesando fecha desde FECHA_APERTURA...")
    
    if 'FECHA_APERTURA' in df.columns:
        df['fecha_apertura'] = df['FECHA_APERTURA'].apply(parse_fecha_apertura)
        
        # Extraer componentes de fecha
        df['anio'] = df['fecha_apertura'].dt.year
        df['mes'] = df['fecha_apertura'].dt.month
        df['dia'] = df['fecha_apertura'].dt.day
        df['trimestre'] = df['fecha_apertura'].dt.quarter
        
        # Calcular semana epidemiológica
        df['semana_epi'] = df['fecha_apertura'].dt.isocalendar().week
        df['anio_epi'] = df['fecha_apertura'].dt.isocalendar().year
        df['anio_semana'] = df['anio_epi'].astype(str) + df['semana_epi'].astype(str).str.zfill(2)
        
        print(f"   Rango de fechas: {df['fecha_apertura'].min()} a {df['fecha_apertura'].max()}")
        
        # Calcular retrasos si hay otras fechas
        if 'FECHA_CONSULTA' in df.columns:
            df['fecha_consulta'] = df['FECHA_CONSULTA'].apply(parse_fecha_apertura)
            df['retraso_apertura_consulta'] = (df['fecha_consulta'] - df['fecha_apertura']).dt.days
        
        if 'FECHA_MUESTRA' in df.columns:
            df['fecha_muestra'] = df['FECHA_MUESTRA'].apply(parse_fecha_apertura)
            df['retraso_apertura_muestra'] = (df['fecha_muestra'] - df['fecha_apertura']).dt.days
        
        if 'FECHA_ESTUDIO' in df.columns:
            df['fecha_estudio'] = df['FECHA_ESTUDIO'].apply(parse_fecha_apertura)
            df['retraso_apertura_estudio'] = (df['fecha_estudio'] - df['fecha_apertura']).dt.days
            df['retraso_muestra_estudio'] = (df['fecha_estudio'] - df['fecha_muestra']).dt.days if 'fecha_muestra' in df.columns else pd.NA
    else:
        print("⚠️ No se encontró columna FECHA_APERTURA")
        df['fecha_apertura'] = pd.NaT
    
    # ==================== GENERACIÓN DE PROVINCIA Y DEPARTAMENTO ====================
    print("🗺️ Generando provincia y departamento...")
    
    # Buscar columna de localidad
    col_id_geografico = None
    for col in ['ID_LOCALIDAD_MUESTRA', 'ID_LOCALIDAD_RESIDENCIA', 'ID_LOC_INDEC_MUESTRA', 'ID_LOC_INDEC_RESIDENCIA']:
        if col in df.columns:
            col_id_geografico = col
            print(f"   Usando {col_id_geografico} como fuente principal")
            break
    
    if col_id_geografico:
        # Extraer provincia (primeros 2 dígitos)
        df['id_provincia_raw'] = df[col_id_geografico].apply(lambda x: extraer_id_geografico(x, 'provincia'))
        # Extraer departamento (primeros 5 dígitos)
        df['id_departamento_raw'] = df[col_id_geografico].apply(lambda x: extraer_id_geografico(x, 'departamento'))
        
        print(f"   Ejemplo IDs: provincia={df['id_provincia_raw'].iloc[0] if len(df)>0 else 'N/A'}, "
              f"departamento={df['id_departamento_raw'].iloc[0] if len(df)>0 else 'N/A'}")
    else:
        print("⚠️ No se encontró columna de localidad para georreferenciación")
        df['id_provincia_raw'] = '00'
        df['id_departamento_raw'] = '00000'
    
    # ==================== CARGA DE MAESTROS ====================
    print("📚 Cargando maestros de geografía...")
    
    # PROVINCIAS - formato ID de 2 dígitos
    if os.path.exists(prov_path):
        df_prov = pd.read_csv(prov_path, sep=';', encoding='utf-8-sig')
        df_prov = df_prov.iloc[:, [0, 1]]
        df_prov.columns = ['provincia_name', 'id_prov_master']
        df_prov['id_prov_master'] = df_prov['id_prov_master'].astype(str).str.zfill(2)
        print(f"   Provincias cargadas: {len(df_prov)}")
    else:
        print(f"⚠️ No se encuentra {prov_path}, creando maestros básicos")
        provincias_default = {
            '02': 'CABA', '06': 'Buenos Aires', '10': 'Catamarca', '14': 'Córdoba',
            '18': 'Corrientes', '22': 'Chaco', '26': 'Chubut', '30': 'Entre Ríos',
            '34': 'Formosa', '38': 'Jujuy', '42': 'La Pampa', '46': 'La Rioja',
            '50': 'Mendoza', '54': 'Misiones', '58': 'Neuquén', '62': 'Río Negro',
            '66': 'Salta', '70': 'San Juan', '74': 'San Luis', '78': 'Santa Cruz',
            '82': 'Santa Fe', '86': 'Santiago del Estero', '90': 'Tucumán', '94': 'Tierra del Fuego'
        }
        df_prov = pd.DataFrame([
            {'id_prov_master': k, 'provincia_name': v} for k, v in provincias_default.items()
        ])
    
    # DEPARTAMENTOS - formato ID de 5 dígitos
    if os.path.exists(depto_path):
        df_depto = pd.read_csv(depto_path, sep=';', encoding='utf-8-sig')
        df_depto = df_depto.iloc[:, [0, 1]]
        df_depto.columns = ['departamento_name', 'id_depto_master']
        df_depto['id_depto_master'] = df_depto['id_depto_master'].astype(str).str.zfill(5)
        print(f"   Departamentos cargados: {len(df_depto)}")
    else:
        print(f"⚠️ No se encuentra {depto_path}, los departamentos quedarán como IDs")
        df_depto = pd.DataFrame(columns=['id_depto_master', 'departamento_name'])
    
    # ==================== CRUCE CON MAESTROS ====================
    print("🔗 Cruzando con maestros geográficos...")
    
    # Cruce para provincia
    df = df.merge(df_prov, left_on='id_provincia_raw', right_on='id_prov_master', how='left')
    
    # Cruce para departamento
    df = df.merge(df_depto, left_on='id_departamento_raw', right_on='id_depto_master', how='left')
    
    # Asignar nombres finales
    df['provincia'] = df['provincia_name'].apply(clean_text).astype(str)
    df['departamento'] = df['departamento_name'].apply(clean_text).astype(str)
    
    # IDs finales para mapas
    df['id_provincia'] = df['id_provincia_raw']
    df['id_departamento'] = df['id_departamento_raw']
    
    # Corrección de IDs problemáticos
    df.loc[df['id_departamento'] == '02000', 'id_departamento'] = '02001'
    df.loc[df['id_provincia'] == '00', 'provincia'] = 'Sin Datos'
    df.loc[df['id_departamento'] == '00000', 'departamento'] = 'Sin Datos'
    
    # ==================== PROCESAMIENTO DE CLASIFICACION_MANUAL ====================
    print("🏷️ Procesando CLASIFICACION_MANUAL...")
    
    if 'CLASIFICACION_MANUAL' in df.columns:
        df['clasificacion_manual'] = df['CLASIFICACION_MANUAL'].apply(clasificar_variante_manual)
        df['clasificacion_manual_original'] = df['CLASIFICACION_MANUAL'].apply(clean_text)
        
        # Estadísticas de clasificación
        print("\n   Distribución de CLASIFICACION_MANUAL:")
        for valor, count in df['clasificacion_manual'].value_counts().head(10).items():
            print(f"      {valor}: {count}")
    else:
        print("⚠️ No se encontró columna CLASIFICACION_MANUAL")
        df['clasificacion_manual'] = 'Sin dato'
        df['clasificacion_manual_original'] = 'Sin dato'
    
    # ==================== PROCESAMIENTO DE LINAJES DESDE RESULTADO ====================
    print("🧬 Procesando linajes desde RESULTADO...")
    
    if 'RESULTADO' in df.columns:
        df['resultado_original'] = df['RESULTADO'].apply(clean_text)
        df['linaje'] = df['RESULTADO'].apply(extraer_linaje_desde_resultado)
        
        # Si RESULTADO tiene "No fue posible obtener secuencia", marcarlo
        df['exito_secuenciacion'] = ~df['resultado_original'].str.contains('no fue posible|No fue posible', na=False)
        
        # Extraer sublinaje si existe (ej: KP.3.1.1)
        def extraer_sublinaje(texto):
            match = re.search(r'([A-Z]+\.[0-9]+(?:\.[0-9]+)?(?:\.[0-9]+)?)', str(texto))
            return match.group(1) if match else ''
        
        df['sublinaje'] = df['RESULTADO'].apply(extraer_sublinaje)
        
        print(f"   Linajes únicos: {df['linaje'].nunique()}")
        print("   Top 10 linajes:")
        for linaje, count in df['linaje'].value_counts().head(10).items():
            print(f"      {linaje}: {count}")
    else:
        print("⚠️ No se encontró columna RESULTADO")
        df['linaje'] = 'Sin linaje'
        df['resultado_original'] = 'Sin dato'
        df['exito_secuenciacion'] = False
        df['sublinaje'] = ''
    
    # ==================== PROCESAMIENTO DEMOGRÁFICO ====================
    print("👥 Procesando datos demográficos...")
    
    # Sexo
    if 'SEXO' in df.columns:
        df['sexo'] = df['SEXO'].apply(lambda x: clean_text(x)[0] if clean_text(x) != 'Sin Datos' else 'S/D')
    else:
        df['sexo'] = 'S/D'
    
    # Edad - priorizar EDAD_ACTUAL, luego EDAD_DIAGNOSTICO
    if 'EDAD_ACTUAL' in df.columns:
        df['edad'] = pd.to_numeric(df['EDAD_ACTUAL'], errors='coerce').fillna(0).astype(int)
    elif 'EDAD_DIAGNOSTICO' in df.columns:
        df['edad'] = pd.to_numeric(df['EDAD_DIAGNOSTICO'], errors='coerce').fillna(0).astype(int)
    else:
        df['edad'] = 0
    
    # Grupo etario - priorizar GRUPO_ETARIO_DX, luego calcular por edad
    if 'GRUPO_ETARIO_DX' in df.columns:
        df['grupo_etario'] = df['GRUPO_ETARIO_DX'].apply(clean_text)
    else:
        bins = [-1, 0, 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59, 64, 69, 74, 79, 200]
        labels = ['<1', '1-4', '5-9', '10-14', '15-19', '20-24', '25-29', '30-34',
                  '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69',
                  '70-74', '75-79', '80+']
        df['grupo_etario'] = pd.cut(df['edad'], bins=bins, labels=labels, right=True).astype(str)
        df.loc[df['edad'] == 0, 'grupo_etario'] = 'Sin dato'
    
    # Grupo etario detallado (para análisis más fino)
    if 'EDAD_ACTUAL' in df.columns or 'EDAD_DIAGNOSTICO' in df.columns:
        bins_detalle = [-1, 0, 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59, 64, 69, 74, 79, 200]
        labels_detalle = ['<1', '1-4', '5-9', '10-14', '15-19', '20-24', '25-29', '30-34',
                          '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69',
                          '70-74', '75-79', '80+']
        df['grupo_etario_detalle'] = pd.cut(df['edad'], bins=bins_detalle, labels=labels_detalle, right=True).astype(str)
        df.loc[df['edad'] == 0, 'grupo_etario_detalle'] = 'Sin dato'
    
    # ==================== PROCESAMIENTO CLÍNICO ====================
    print("🏥 Procesando datos clínicos...")
    
    # Variables binarias de gravedad
    clinicas = {
        'internado': 'INTERNADO',
        'cuidado_intensivo': 'CUIDADO_INTENSIVO',
        'asistencia_respiratoria': 'ASIST_RESP_MECANICA_COVID',
        'fallecido': 'FALLECIDO'
    }
    
    for col_nueva, col_orig in clinicas.items():
        if col_orig in df.columns:
            df[col_nueva] = df[col_orig].apply(lambda x: clean_text(x) == 'SI' if pd.notna(x) else False)
        else:
            df[col_nueva] = False
    
    # Indicador de gravedad compuesto
    df['grave'] = (df['internado'] | df['cuidado_intensivo'] | df['asistencia_respiratoria']).astype(bool)
    df['muy_grave'] = (df['cuidado_intensivo'] | df['asistencia_respiratoria']).astype(bool)
    
    # Fecha de fallecimiento
    if 'FECHA_FALLECIMIENTO' in df.columns:
        df['fecha_fallecimiento'] = df['FECHA_FALLECIMIENTO'].apply(parse_fecha_apertura)
    else:
        df['fecha_fallecimiento'] = pd.NaT
    
    # ==================== PROCESAMIENTO DE VACUNACIÓN ====================
    print("💉 Procesando datos de vacunación...")
    
    if 'VACUNA' in df.columns:
        df['vacuna_tipo'] = df['VACUNA'].apply(clean_text)
    elif 'VACUNA_NOMIVAC' in df.columns:
        df['vacuna_tipo'] = df['VACUNA_NOMIVAC'].apply(clean_text)
    else:
        df['vacuna_tipo'] = 'Sin dato'
    
    if 'DOSIS' in df.columns:
        df['vacuna_dosis'] = pd.to_numeric(df['DOSIS'], errors='coerce').fillna(0).astype(int)
    else:
        df['vacuna_dosis'] = 0
    
    df['vacuna_esquema_completo'] = df['vacuna_dosis'] >= 2
    
    # Tiempo desde última dosis (meses)
    if 'FECHA_APLICACION' in df.columns:
        df['fecha_aplicacion'] = df['FECHA_APLICACION'].apply(parse_fecha_apertura)
        if 'fecha_apertura' in df.columns:
            df['meses_desde_ultima_dosis'] = (df['fecha_apertura'] - df['fecha_aplicacion']).dt.days / 30
    else:
        df['fecha_aplicacion'] = pd.NaT
        df['meses_desde_ultima_dosis'] = pd.NA
    
    # ==================== VIAJES Y ANTECEDENTES ====================
    print("✈️ Procesando antecedentes de viaje...")
    
    if 'PAIS_VIAJE' in df.columns:
        df['pais_viaje'] = df['PAIS_VIAJE'].apply(clean_text)
    else:
        df['pais_viaje'] = 'Sin dato'
    
    if 'ANTECEDENTE_EPIDEMIOLOGICO' in df.columns:
        df['antecedente_epidemiologico'] = df['ANTECEDENTE_EPIDEMIOLOGICO'].apply(clean_text)
    else:
        df['antecedente_epidemiologico'] = 'Sin dato'
    
    if 'NEXO_EPIDEMIOLOGICO' in df.columns:
        df['nexo_epidemiologico'] = df['NEXO_EPIDEMIOLOGICO'].apply(clean_text)
    else:
        df['nexo_epidemiologico'] = 'Sin dato'
    
    # ==================== CONTROL DE CALIDAD ====================
    print("🔍 Procesando control de calidad...")
    
    if 'ES_CENTINELA' in df.columns:
        df['es_centinela'] = df['ES_CENTINELA'].apply(lambda x: clean_text(x) == 'SI' if pd.notna(x) else False)
    else:
        df['es_centinela'] = False
    
    if 'ID_USUARIO_REGISTRO' in df.columns:
        df['id_usuario_registro'] = df['ID_USUARIO_REGISTRO'].apply(clean_text)
    else:
        df['id_usuario_registro'] = 'Sin dato'
    
    # ==================== SELECCIÓN DE COLUMNAS FINALES ====================
    print("📋 Seleccionando columnas para el dataset final...")
    
    columnas_finales = [
        # Fechas y tiempo
        'fecha_apertura', 'anio', 'mes', 'dia', 'trimestre',
        'semana_epi', 'anio_epi', 'anio_semana',
        'fecha_consulta', 'fecha_muestra', 'fecha_estudio', 'fecha_fallecimiento',
        'retraso_apertura_consulta', 'retraso_apertura_muestra', 
        'retraso_apertura_estudio', 'retraso_muestra_estudio',
        
        # Geografía
        'id_provincia', 'provincia', 'id_departamento', 'departamento',
        
        # Genómica
        'linaje', 'sublinaje', 'resultado_original', 
        'clasificacion_manual', 'clasificacion_manual_original',
        'exito_secuenciacion',
        
        # Demografía
        'sexo', 'edad', 'grupo_etario', 'grupo_etario_detalle',
        
        # Clínica
        'internado', 'cuidado_intensivo', 'asistencia_respiratoria',
        'grave', 'muy_grave', 'fallecido',
        
        # Vacunación
        'vacuna_tipo', 'vacuna_dosis', 'vacuna_esquema_completo',
        'fecha_aplicacion', 'meses_desde_ultima_dosis',
        
        # Epidemiología
        'pais_viaje', 'antecedente_epidemiologico', 'nexo_epidemiologico',
        
        # Control de calidad
        'es_centinela', 'id_usuario_registro'
    ]
    
    # Verificar qué columnas existen realmente en el DataFrame
    columnas_existentes = [col for col in columnas_finales if col in df.columns]
    columnas_faltantes = [col for col in columnas_finales if col not in df.columns]
    
    if columnas_faltantes:
        print(f"⚠️ Columnas no encontradas (se crearán con valor por defecto): {columnas_faltantes}")
        for col in columnas_faltantes:
            if col in ['grave', 'muy_grave', 'fallecido', 'exito_secuenciacion', 
                       'internado', 'cuidado_intensivo', 'asistencia_respiratoria', 'es_centinela']:
                df[col] = False
            elif col in ['anio', 'mes', 'dia', 'trimestre', 'semana_epi', 'anio_epi', 'edad', 'vacuna_dosis']:
                df[col] = 0
            elif col in ['fecha_apertura', 'fecha_consulta', 'fecha_muestra', 'fecha_estudio', 
                        'fecha_fallecimiento', 'fecha_aplicacion']:
                df[col] = pd.NaT
            elif col in ['retraso_apertura_consulta', 'retraso_apertura_muestra', 
                        'retraso_apertura_estudio', 'retraso_muestra_estudio', 'meses_desde_ultima_dosis']:
                df[col] = pd.NA
            else:
                df[col] = 'Sin dato'
    
    df_final = df[columnas_finales].copy()
    
    # ==================== LIMPIEZA FINAL ====================
    print("🧹 Limpieza final...")
    
    for col in df_final.columns:
        if df_final[col].dtype == 'object':
            df_final[col] = df_final[col].fillna('Sin dato')
        elif df_final[col].dtype == 'bool':
            df_final[col] = df_final[col].fillna(False)
        elif df_final[col].dtype in ['int64', 'float64']:
            df_final[col] = df_final[col].fillna(0)
    
    # ==================== REPORTE Y GUARDADO ====================
    print("\n" + "="*50)
    print("📊 REPORTE ETL GENÓMICA")
    print("="*50)
    print(f"📥 Filas originales: {len(df):,}")
    print(f"📤 Filas finales: {len(df_final):,}")
    print(f"📋 Columnas finales: {len(df_final.columns)}")
    print(f"🧬 Linajes únicos: {df_final['linaje'].nunique()}")
    print(f"🏷️ Clasificaciones únicas: {df_final['clasificacion_manual'].nunique()}")
    print(f"🌍 Provincias únicas: {df_final['provincia'].nunique()}")
    print(f"🏘️ Departamentos únicos: {df_final['departamento'].nunique()}")
    print(f"✅ Éxito secuenciación: {df_final['exito_secuenciacion'].mean()*100:.1f}%")
    
    errores_prov = len(df_final[df_final['provincia'] == 'Sin Datos'])
    print(f"🗺️ Filas sin provincia: {errores_prov} ({errores_prov/len(df_final)*100:.1f}%)")
    
    # Mostrar distribución de clasificaciones
    print("\n📊 Distribución de CLASIFICACION_MANUAL:")
    for valor, count in df_final['clasificacion_manual'].value_counts().head(10).items():
        print(f"   {valor}: {count} ({count/len(df_final)*100:.1f}%)")
    
    # Mostrar top linajes
    print("\n📊 Top 10 linajes:")
    for linaje, count in df_final['linaje'].value_counts().head(10).items():
        print(f"   {linaje}: {count} ({count/len(df_final)*100:.1f}%)")
    
    # Mostrar distribución por provincia
    print("\n📊 Top 10 provincias:")
    for prov, count in df_final['provincia'].value_counts().head(10).items():
        print(f"   {prov}: {count} ({count/len(df_final)*100:.1f}%)")
    
    # Guardar como Parquet
    df_final.to_parquet(output_path, engine='pyarrow', index=False, compression='snappy')
    print(f"\n💾 Archivo guardado en: {output_path}")
    print(f"📦 Tamaño: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")
    
    return df_final

if __name__ == "__main__":
    df_resultado = run_etl()