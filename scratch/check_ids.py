import pandas as pd

CSV_PATH = 'data/Base_uni.csv'
df_raw = pd.read_csv(CSV_PATH, sep=';', encoding='utf-8', low_memory=False)
df_raw['FECHA_APERTURA'] = pd.to_datetime(df_raw['FECHA_APERTURA'], dayfirst=True, errors='coerce')
df_raw['ANIO_CALENDAR'] = df_raw['FECHA_APERTURA'].dt.year

sifilis_name = 'Sfilis' # From previous run

print("--- SALTA 2024 SIFILIS DETAILED ---")
salta_2024 = df_raw[(df_raw['ANIO_CALENDAR'] == 2024) & (df_raw['EVENTO'] == sifilis_name) & ((df_raw['PROV_RESI_CARGA'] == 'Salta') | (df_raw['ID_PROV_RESI_CARGA'] == 66))] # 66 is Salta? No, 66 is Salta? 
# Let's find Salta ID
salta_id = df_raw[df_raw['PROV_RESI_CARGA'] == 'Salta']['ID_PROV_RESI_CARGA'].unique()
print(f"Salta ID(s): {salta_id}")

# Count by name
print(f"Count by Name 'Salta': {len(df_raw[(df_raw['ANIO_CALENDAR'] == 2024) & (df_raw['EVENTO'] == sifilis_name) & (df_raw['PROV_RESI_CARGA'] == 'Salta')])}")
# Count by ID
print(f"Count by ID {salta_id}: {len(df_raw[(df_raw['ANIO_CALENDAR'] == 2024) & (df_raw['EVENTO'] == sifilis_name) & (df_raw['ID_PROV_RESI_CARGA'].isin(salta_id))])}")

print("\n--- JUJUY 2024 SIFILIS DETAILED ---")
jujuy_id = df_raw[df_raw['PROV_RESI_CARGA'] == 'Jujuy']['ID_PROV_RESI_CARGA'].unique()
print(f"Jujuy ID(s): {jujuy_id}")
print(f"Count by Name 'Jujuy': {len(df_raw[(df_raw['ANIO_CALENDAR'] == 2024) & (df_raw['EVENTO'] == sifilis_name) & (df_raw['PROV_RESI_CARGA'] == 'Jujuy')])}")
print(f"Count by ID {jujuy_id}: {len(df_raw[(df_raw['ANIO_CALENDAR'] == 2024) & (df_raw['EVENTO'] == sifilis_name) & (df_raw['ID_PROV_RESI_CARGA'].isin(jujuy_id))])}")
