# Documento Técnico: Migración a Tablero Epidemiológico Nacional (Argentina)

Este documento detalla las instrucciones y lógica técnica para replicar y expandir las funcionalidades del proyecto **dashPBA** a un nuevo entorno de alcance **Nacional**.

## 1. Objetivo del Nuevo Proyecto
Desarrollar un tablero interactivo en Streamlit que permita visualizar la vigilancia epidemiológica de toda Argentina, integrando datos de todas las provincias y sus respectivos departamentos.

---

## 2. Preparación y Estructura de Datos

### 2.1 Archivos Base a Copiar
Deberás copiar los siguientes archivos/carpetas desde el proyecto actual a una nueva carpeta `data/` en el proyecto nacional:
- **Mapas:** `provincia.json` y `departamento.json` (Asegúrate de reemplazarlos por versiones que incluyan TODA la Argentina, no solo PBA).
- **Población:** `poblacionxprovinciaindec.csv` y `proyecciones_depto_indec.csv` (Versión nacional del INDEC).
- **Maestros:** Cualquier CSV de referencia como `RSPBA.csv` (nota: deberá ser adaptado a Regiones Sanitarias nacionales si aplica).

### 2.2 Proceso ETL (Conversión a Parquet)
Es mandatorio convertir los nuevos archivos de datos (CSV) y la nueva base de datos a formato **Parquet** para garantizar velocidad.
- **Acción:** Ejecutar un script similar a `etl_semanal.py`.
- **Lógica:**
    - Leer los nuevos CSV nacionales.
    - Cambiar tipos de datos: `ANIO` (int16), `SEMANA` (int8), `CANTIDAD` (int32).
    - Convertir columnas de texto repetitivas (Provincia, Evento, Grupo) a tipo `category`.
    - Guardar en `data/base_nacional.parquet` usando `pyarrow`.

---

## 3. Especificaciones de Funcionalidad

### 3.1 Filtros Dinámicos (Selectores)
El tablero debe contar con los siguientes selectores en la barra lateral o superior:
1.  **Año:** Selector único basado en los años disponibles en la base.
2.  **Semana Epidemiológica (SE):** Selector de 1 a 52/53. Si no se elige, debe sumarizar el año completo o el rango actual.
3.  **Evento (Patología):** 
    - Si se selecciona un evento específico: Mostrar mapa y tablas solo para ese evento.
    - Si no se selecciona nada (o se elige "Todos"): Sumarizar la totalidad de los eventos (misma lógica que el proyecto actual).
4.  **Provincia / Departamento:**
    - Filtro de Provincia: Al seleccionar una, el mapa debe hacer zoom o filtrar los departamentos de dicha provincia.
5.  **Métrica:** Selector entre **"Casos"** (Cantidad absoluta) y **"Tasas"** (Casos / Población * 100,000).

### 3.2 Visualización Geográfica (Mapping)
Basado en `pages/4_Mapas.py`, el mapa debe:
- Utilizar `plotly.express.choropleth_mapbox`.
- **Nivel Nacional:** Mostrar mapa de provincias coloreado por la métrica seleccionada.
- **Nivel Departamental:** Al filtrar por provincia, mostrar el desglose por departamentos.
- **Estética:** Usar escalas de colores como `Reds` para casos y `Blues` para tasas. Estilo de mapa `carto-positron`.

### 3.3 Tablas de Respaldo
Debajo de cada mapa, generar un `st.dataframe` con:
- Nombre de la Jurisdicción (Provincia o Departamento).
- Cantidad de Casos.
- Población (proyección INDEC).
- Valor de la Métrica (Calculado dinámicamente).
- Ordenar de mayor a menor valor.

---

## 4. Implementación Técnica Sugerida

### 4.1 Uso de DuckDB
Para las consultas sobre el archivo Parquet de gran tamaño, utiliza la lógica de `utils/common.py`:
```python
import duckdb
def query_data(sql_query, parquet_path):
    with duckdb.connect() as con:
        return con.execute(sql_query.replace('{parquet}', f"'{parquet_path}'")).df()
```

### 4.2 Lógica de Tasas
Asegúrate de que el cruce (merge) entre la base epidemiológica y la población se haga siempre por:
- **Año**
- **Código de Jurisdicción** (Asegura que los códigos INDEC tengan el mismo formato, ej: zfill de 2 para provincias y 5 para departamentos).

---

## 5. Instrucciones de Despliegue
- Mantener el archivo `requirements.txt` actualizado con: `streamlit`, `pandas`, `pyarrow`, `geopandas`, `plotly`, `duckdb`.
- Usar `st.cache_data` para la carga de los GeoJSON (que son pesados) para que la navegación sea fluida.

---

> [!IMPORTANT]
> Recuerda que en este contexto, **"Patología"** siempre se referencia como **"Evento"** en el código y en la interfaz. Sin embargo, en la documentación técnica se pueden usar indistintamente para claridad del desarrollador.
