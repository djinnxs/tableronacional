import pandas as pd

CSV_PATH = 'data/Base_uni.csv'
df = pd.read_csv(CSV_PATH, sep=';', encoding='latin-1', low_memory=False)
df['FECHA_APERTURA'] = pd.to_datetime(df['FECHA_APERTURA'], format='%d/%m/%Y', errors='coerce')
df['ANIO'] = df['FECHA_APERTURA'].dt.year

mask_sifilis = df['EVENTO'].str.contains('ifilis', case=False, na=False)
# Ensure we only get the simple 'Sífilis' if possible, or list them
print(f"Unique events matching 'ifilis': {df[mask_sifilis]['EVENTO'].unique()}")
event_name = 'Sífilis' # Try direct again but I'll use mask in logic

print("--- VERIFICATION ---")

# Salta 2024
mask_salta = (df['PROV_RESI_CARGA'] == 'Salta') & (df['ANIO'] == 2024) & (df['EVENTO'] == 'S\u00edfilis')
salta_all = df[mask_salta]
print(f"Salta 2024 S\u00edfilis Total: {len(salta_all)}")

# Jujuy 2024
mask_jujuy = (df['PROV_RESI_CARGA'] == 'Jujuy') & (df['ANIO'] == 2024) & (df['EVENTO'] == 'S\u00edfilis')
jujuy_all = df[mask_jujuy]
print(f"Jujuy 2024 S\u00edfilis Total: {len(jujuy_all)}")

# Check ID_DEPTO_RESI_CARGA for Jujuy
# The ID usually looks like 38XXX. 38000 is often used for undefined.
# Let's see unique values
print("\nJujuy Depto IDs:")
print(jujuy_all['ID_DEPTO_RESI_CARGA'].value_counts())

# Check for id_provincia 00 cases
total_2024_sif = df[(df['ANIO'] == 2024) & (df['EVENTO'] == event_name)]
print(f"\nTotal National 2024 Sífilis: {len(total_2024_sif)}")
print(f"Cases without Province ID: {len(total_2024_sif[total_2024_sif['ID_PROV_RESI_CARGA'].isna()])}")
