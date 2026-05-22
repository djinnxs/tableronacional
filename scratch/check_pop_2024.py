import pandas as pd
import duckdb

# Test the exact query used in home.py for provinces
con = duckdb.connect()
selected_anio = 2026
PROV_POP_PARQUET = 'data/poblacionxprovinciaindec.parquet'
DEPTO_POP_PARQUET = 'data/proyecciones_depto_indec.parquet'

# Province population query
pop_prov_sql = f"SELECT juri as id_provincia, SUM(poblacion) as Poblacion FROM '{PROV_POP_PARQUET}' WHERE ano = {selected_anio} AND sexo_nombre = 'Ambos sexos' GROUP BY juri"
pop_prov = con.execute(pop_prov_sql).df()
print(f"Provinces found for {selected_anio}:", len(pop_prov))
pop_prov['id_provincia'] = pop_prov['id_provincia'].astype(str).str.zfill(2)
print(pop_prov.head(10).to_string())

print()
# Now check what id_provincia looks like in the case data
BASE_PARQUET = 'data/base_nacional.parquet'
prov_data = con.execute(f"SELECT id_provincia, Provincia, SUM(CANTIDAD) as Casos FROM '{BASE_PARQUET}' WHERE ANIO = {selected_anio} AND id_provincia != '00' GROUP BY id_provincia, Provincia ORDER BY Casos DESC").df()
prov_data['id_provincia'] = prov_data['id_provincia'].astype(str).str.zfill(2)
print("Case data provinces:")
print(prov_data.head(10).to_string())
print()
# Try merge
merged = prov_data.merge(pop_prov, on='id_provincia', how='left')
print("After merge:")
print(merged.head(10).to_string())
