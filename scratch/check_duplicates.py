import pandas as pd

# Read CSV
df = pd.read_csv('data/Base_uni.csv', sep=';', encoding='latin-1', low_memory=False)
# Fix column names (remove BOM)
df.columns = [c.replace('\ufeff', '') for c in df.columns]

# Filter Salta 2024
mask_salta = (df['PROV_RESI_CARGA'] == 'Salta') & (df['FECHA_APERTURA'].str.contains('/2024', na=False))
df_salta = df[mask_salta]

# Find events matching 'ifilis'
sif_events = df_salta[df_salta['EVENTO'].str.contains('ifilis', na=False, case=False)]
print("--- SALTA 2024 SIFILIS ---")
print(f"Total rows matching 'ifilis': {len(sif_events)}")
print(f"Unique IDEVENTOCASO: {sif_events['IDEVENTOCASO'].nunique()}")
print(f"Unique event names found: {sif_events['EVENTO'].unique()}")

# Split by exact name
for name in sif_events['EVENTO'].unique():
    subset = sif_events[sif_events['EVENTO'] == name]
    print(f"  Event: {name}")
    print(f"    Rows: {len(subset)}")
    print(f"    Unique IDs: {subset['IDEVENTOCASO'].nunique()}")

print("\n--- JUJUY 2024 SIFILIS ---")
mask_jujuy = (df['PROV_RESI_CARGA'] == 'Jujuy') & (df['FECHA_APERTURA'].str.contains('/2024', na=False))
df_jujuy = df[mask_jujuy]
sif_jujuy = df_jujuy[df_jujuy['EVENTO'].str.contains('ifilis', na=False, case=False)]
print(f"Total rows matching 'ifilis': {len(sif_jujuy)}")
print(f"Unique IDEVENTOCASO: {sif_jujuy['IDEVENTOCASO'].nunique()}")
for name in sif_jujuy['EVENTO'].unique():
    subset = sif_jujuy[sif_jujuy['EVENTO'] == name]
    print(f"  Event: {name}")
    print(f"    Rows: {len(subset)}")
    print(f"    Unique IDs: {subset['IDEVENTOCASO'].nunique()}")
