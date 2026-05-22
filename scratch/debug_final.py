import pandas as pd

CSV_PATH = 'data/Base_uni.csv'
# Reading with latin-1 to handle accents correctly
df_raw = pd.read_csv(CSV_PATH, sep=';', encoding='latin-1', low_memory=False)
df_raw['FECHA_APERTURA'] = pd.to_datetime(df_raw['FECHA_APERTURA'], dayfirst=True, errors='coerce')
df_raw['ANIO_CALENDAR'] = df_raw['FECHA_APERTURA'].dt.year

def get_stats(prov_name, year, event_names):
    mask = (df_raw['ANIO_CALENDAR'] == year) & \
           (df_raw['EVENTO'].isin(event_names)) & \
           (df_raw['PROV_RESI_CARGA'] == prov_name)
    return len(df_raw[mask])

sifilis_simple = ['Sífilis']
sifilis_all = ['Sífilis', 'Sífilis en personas gestantes']

print(f"--- DISCREPANCY DEBUG (YEAR 2024) ---")

print(f"SALTA:")
print(f"  Only 'Sífilis': {get_stats('Salta', 2024, sifilis_simple)}")
print(f"  Both 'Sífilis': {get_stats('Salta', 2024, sifilis_all)}")

print(f"JUJUY:")
print(f"  Only 'Sífilis': {get_stats('Jujuy', 2024, sifilis_simple)}")
print(f"  Both 'Sífilis': {get_stats('Jujuy', 2024, sifilis_all)}")

# Check for cases without province name but with ID?
# Salta ID is 66, Jujuy is 38
def get_stats_by_id(id_prov, year, event_names):
    mask = (df_raw['ANIO_CALENDAR'] == year) & \
           (df_raw['EVENTO'].isin(event_names)) & \
           (df_raw['ID_PROV_RESI_CARGA'] == id_prov)
    return len(df_raw[mask])

print(f"\n--- COUNTS BY ID ---")
print(f"SALTA (ID 66):")
print(f"  Only 'Sífilis': {get_stats_by_id(66, 2024, sifilis_simple)}")
print(f"  Both 'Sífilis': {get_stats_by_id(66, 2024, sifilis_all)}")

print(f"JUJUY (ID 38):")
print(f"  Only 'Sífilis': {get_stats_by_id(38, 2024, sifilis_simple)}")
print(f"  Both 'Sífilis': {get_stats_by_id(38, 2024, sifilis_all)}")
