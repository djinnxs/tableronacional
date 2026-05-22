import pandas as pd
import numpy as np
import os
import unicodedata

def clean_text(v):
    if pd.isna(v): return "Sin Datos"
    v = str(v).replace('\xad', '')
    return unicodedata.normalize('NFC', v).strip()

def run_etl():
    input_path = os.path.join('data', 'Base_uni.csv')
    prov_path = os.path.join('data', 'Provincias.csv')
    depto_path = os.path.join('data', 'Departamentos.csv')
    output_path = os.path.join('data', 'base_nacional.parquet')
    
    print("Leyendo Base_uni.csv...")
    df = pd.read_csv(input_path, sep=';', encoding='utf-8', low_memory=False)
    df.columns = df.columns.str.strip()

    # --- PROCESAMIENTO DE FECHAS ---
    # ANIO_SEPI_AP: YYYYWW (ej: 202401)
    df['ANIO_SEPI_AP'] = pd.to_numeric(df['ANIO_SEPI_AP'], errors='coerce').fillna(0).astype(int).astype(str)
    
    # Extraer año (primeros 4) y semana (últimos 2)
    # Si viene vacío o 0, usamos valores por defecto
    df['ANIO'] = df['ANIO_SEPI_AP'].apply(lambda x: int(x[:4]) if len(x) >= 4 and x[:4] != '0' else 2024)
    df['SEMANA'] = df['ANIO_SEPI_AP'].apply(lambda x: int(x[4:]) if len(x) > 4 else 1)
    df.loc[df['SEMANA'] == 0, 'SEMANA'] = 1

    # --- NORMALIZACIÓN DE IDs (Base Principal) ---
    # Pasamos por numeric para limpiar cualquier punto decimal o espacio
    df['ID_PROVINCIA'] = pd.to_numeric(df['ID_PROVINCIA'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(2)
    df['ID_DEPARTAMENTO'] = pd.to_numeric(df['ID_DEPARTAMENTO'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(5)
    df.loc[df['ID_DEPARTAMENTO'] == '02000', 'ID_DEPARTAMENTO'] = '02001'

    # --- CARGA DE MAESTROS ---
    print("Cruzando con maestros...")
    
    # PROVINCIAS
    df_prov = pd.read_csv(prov_path, sep=';', encoding='utf-8-sig')
    df_prov = df_prov.iloc[:, [0, 1]] 
    df_prov.columns = ['PROVINCIA_NAME', 'ID_PROV_MASTER'] # Nombres temporales
    # Asegurar que el ID sea string "06", "02", etc.
    df_prov['ID_PROV_MASTER'] = pd.to_numeric(df_prov['ID_PROV_MASTER'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(2)

    # DEPARTAMENTOS
    df_depto = pd.read_csv(depto_path, sep=';', encoding='utf-8-sig')
    df_depto = df_depto.iloc[:, [0, 1]]
    df_depto.columns = ['DEPARTAMENTO_NAME', 'ID_DEP_MASTER']
    df_depto['ID_DEP_MASTER'] = pd.to_numeric(df_depto['ID_DEP_MASTER'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(5)

    # --- LIMPIEZA DE COLUMNAS PREVIAS ---
    cols_to_drop = ['PROVINCIA', 'DEPARTAMENTO', 'Provincia', 'Departamento']
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    # --- CRUCE (MERGE) ---
    # Cruzamos ID de base con ID de maestro
    df = df.merge(df_prov, left_on='ID_PROVINCIA', right_on='ID_PROV_MASTER', how='left')
    df = df.merge(df_depto, left_on='ID_DEPARTAMENTO', right_on='ID_DEP_MASTER', how='left')

    # --- ASIGNACIÓN Y LIMPIEZA DE TEXTO ---
    # Forzamos astype(str) para que PyArrow no falle
    df['Provincia'] = df['PROVINCIA_NAME'].apply(clean_text).astype(str)
    df['Departamento'] = df['DEPARTAMENTO_NAME'].apply(clean_text).astype(str)
    df['Evento'] = df['EVENTO'].apply(clean_text).astype(str)
    df['CANTIDAD'] = pd.to_numeric(df['CONFIRMADOS'], errors='coerce').fillna(0).astype(int)

    # --- AGRUPACIÓN ---
    group_cols = [
        'ANIO', 'SEMANA', 'ID_SNVS_EVENTO', 'Evento', 
        'Provincia', 'Departamento', 'ID_PROVINCIA', 'ID_DEPARTAMENTO'
    ]
    df_agg = df.groupby(group_cols, as_index=False)['CANTIDAD'].sum()

    # Renombrar para el Dashboard
    df_agg = df_agg.rename(columns={'ID_PROVINCIA': 'id_provincia', 'ID_DEPARTAMENTO': 'id_departamento'})

    # --- REPORTE Y GUARDADO ---
    errores = len(df_agg[df_agg['Provincia'] == 'Sin Datos'])
    print(f"--- REPORTE ETL ---")
    print(f"Filas totales agrupadas: {len(df_agg)}")
    print(f"Filas sin provincia asignada: {errores}")
    
    # EL PASO MÁS IMPORTANTE PARA EL ERROR DE PYARROW:
    # Asegurar que los IDs de eventos también sean strings
    df_agg['ID_SNVS_EVENTO'] = df_agg['ID_SNVS_EVENTO'].astype(str)

    df_agg.to_parquet(output_path, engine='pyarrow', index=False)
    print(f"Éxito: Archivo guardado en {output_path}")

if __name__ == "__main__":
    run_etl()