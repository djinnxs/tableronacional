import pandas as pd
import duckdb

CSV_PATH = 'data/Base_uni.csv'
PARQUET_PATH = 'data/base_nacional.parquet'

print("--- Analysis of Discrepancies ---")

# Load raw CSV
df_raw = pd.read_csv(CSV_PATH, sep=';', encoding='utf-8', low_memory=False)

# Convert dates to get year
df_raw['FECHA_APERTURA'] = pd.to_datetime(df_raw['FECHA_APERTURA'], dayfirst=True, errors='coerce')
df_raw['ANIO_RAW'] = df_raw['FECHA_APERTURA'].dt.year

# Filter for Sífilis and 2024
# The user said 'sifilis', let's find the exact string
eventos = df_raw['EVENTO'].unique()
sifilis_name = [e for e in eventos if 'Sifilis' in str(e) or 'Sífilis' in str(e)][0]
print(f"Detected event name: {sifilis_name}")

# Raw counts by province
raw_salta = df_raw[(df_raw['ANIO_RAW'] == 2024) & (df_raw['EVENTO'] == sifilis_name) & (df_raw['PROV_RESI_CARGA'] == 'Salta')]
raw_jujuy = df_raw[(df_raw['ANIO_RAW'] == 2024) & (df_raw['EVENTO'] == sifilis_name) & (df_raw['PROV_RESI_CARGA'] == 'Jujuy')]

print(f"Raw CSV Salta 2024: {len(raw_salta)}")
print(f"Raw CSV Jujuy 2024: {len(raw_jujuy)}")

# Check Parquet counts
with duckdb.connect() as con:
    pq_salta = con.execute(f"SELECT SUM(CANTIDAD) FROM '{PARQUET_PATH}' WHERE ANIO = 2024 AND Evento = '{sifilis_name}' AND Provincia = 'Salta'").fetchone()[0]
    pq_jujuy = con.execute(f"SELECT SUM(CANTIDAD) FROM '{PARQUET_PATH}' WHERE ANIO = 2024 AND Evento = '{sifilis_name}' AND Provincia = 'Jujuy'").fetchone()[0]
    print(f"Parquet Salta 2024: {pq_salta}")
    print(f"Parquet Jujuy 2024: {pq_jujuy}")

# Check for "Sin información" in CSV that might belong to these provinces but missing IDs?
# Or check if ANIO in parquet is different from ANIO_RAW
print("\n--- Date/Year check ---")
raw_2024_total = len(df_raw[(df_raw['ANIO_RAW'] == 2024) & (df_raw['Evento'] == sifilis_name)])
with duckdb.connect() as con:
    pq_2024_total = con.execute(f"SELECT SUM(CANTIDAD) FROM '{PARQUET_PATH}' WHERE ANIO = 2024 AND Evento = '{sifilis_name}'").fetchone()[0]
print(f"Total 2024 Sífilis Raw: {raw_2024_total}")
print(f"Total 2024 Sífilis Parquet: {pq_2024_total}")
