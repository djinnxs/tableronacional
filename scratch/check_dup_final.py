import pandas as pd

# Read CSV with utf-8-sig to handle BOM correctly
df = pd.read_csv('data/Base_uni.csv', sep=';', encoding='latin-1', low_memory=False)
# Manually remove the BOM characters if latin-1 was used
df.columns = [c.lstrip('ï»¿') for c in df.columns]

print(f"Columns: {list(df.columns)}")

# Filter Salta 2024
# Salta 2024 Sífilis
# Use contains to avoid encoding issues for now
mask = (df['PROV_RESI_CARGA'] == 'Salta') & (df['FECHA_APERTURA'].str.contains('/2024', na=False)) & (df['EVENTO'].str.contains('ifilis', na=False, case=False))
df_filtered = df[mask]

print(f"\n--- SALTA 2024 SIFILIS ---")
print(f"Total Rows: {len(df_filtered)}")
if 'IDEVENTOCASO' in df_filtered.columns:
    print(f"Unique IDEVENTOCASO: {df_filtered['IDEVENTOCASO'].nunique()}")
else:
    print("IDEVENTOCASO not found in columns")

# Jujuy 2024
mask_j = (df['PROV_RESI_CARGA'] == 'Jujuy') & (df['FECHA_APERTURA'].str.contains('/2024', na=False)) & (df['EVENTO'].str.contains('ifilis', na=False, case=False))
df_j = df[mask_j]
print(f"\n--- JUJUY 2024 SIFILIS ---")
print(f"Total Rows: {len(df_j)}")
if 'IDEVENTOCASO' in df_j.columns:
    print(f"Unique IDEVENTOCASO: {df_j['IDEVENTOCASO'].nunique()}")
