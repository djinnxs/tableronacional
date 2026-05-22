import pandas as pd

CSV_PATH = 'data/Base_uni.csv'
df_raw = pd.read_csv(CSV_PATH, sep=';', encoding='utf-8', low_memory=False)
df_raw['FECHA_APERTURA'] = pd.to_datetime(df_raw['FECHA_APERTURA'], dayfirst=True, errors='coerce')
df_raw['ANIO_CALENDAR'] = df_raw['FECHA_APERTURA'].dt.year

# Filter for anything like Sifilis
mask_sifilis = df_raw['EVENTO'].str.contains('ifilis', case=False, na=False)
sifilis_rows = df_raw[mask_sifilis]

print(f"Events found: {sifilis_rows['EVENTO'].unique()}")

# Select the most likely one
event_target = sifilis_rows['EVENTO'].unique()[0]
print(f"Targeting: {event_target}")

# Detailed counts for 2024
df_2024 = df_raw[(df_raw['ANIO_CALENDAR'] == 2024) & (df_raw['EVENTO'] == event_target)]

salta_stats = df_2024[df_2024['PROV_RESI_CARGA'] == 'Salta']
jujuy_stats = df_2024[df_2024['PROV_RESI_CARGA'] == 'Jujuy']

print(f"\n--- SALTA 2024 ---")
print(f"Total Rows: {len(salta_stats)}")
print(f"Unique IDs: {salta_stats['ID_PROV_RESI_CARGA'].unique()}")

print(f"\n--- JUJUY 2024 ---")
print(f"Total Rows: {len(jujuy_stats)}")
print(f"Unique IDs: {jujuy_stats['ID_PROV_RESI_CARGA'].unique()}")

# Check for cases with ID 66 but different name?
print(f"\n--- ID 66 (Salta) Rows ---")
print(len(df_2024[df_2024['ID_PROV_RESI_CARGA'] == 66]))

# Check for cases with ID 38 (Jujuy) Rows
print(f"\n--- ID 38 (Jujuy) Rows ---")
print(len(df_2024[df_2024['ID_PROV_RESI_CARGA'] == 38]))
