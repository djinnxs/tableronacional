import pandas as pd

CSV_PATH = 'data/Base_uni.csv'
df = pd.read_csv(CSV_PATH, sep=';', encoding='latin-1', low_memory=False)

# Filter by string matching to avoid date parsing issues
mask_2024 = df['FECHA_APERTURA'].str.contains('/2024', na=False)
mask_sifilis = df['EVENTO'].str.contains('ifilis', na=False)

print("--- RAW DATA COUNTS (STRING MATCH) ---")

# Salta
mask_salta = (df['PROV_RESI_CARGA'] == 'Salta') & mask_2024 & mask_sifilis
print(f"Salta 2024 matching 'ifilis': {len(df[mask_salta])}")

# Jujuy
mask_jujuy = (df['PROV_RESI_CARGA'] == 'Jujuy') & mask_2024 & mask_sifilis
print(f"Jujuy 2024 Sífilis: {len(df[mask_jujuy])}")

# Check event names to be sure
print(f"\nUnique events containing 'Sífilis':")
print(df[df['EVENTO'].str.contains('Sífilis', na=False)]['EVENTO'].unique())
