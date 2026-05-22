import duckdb
import pandas as pd

PROV_POP = 'data/poblacionxprovinciaindec.parquet'
DEPTO_POP = 'data/proyecciones_depto_indec.parquet'

with duckdb.connect() as con:
    print("--- Prov Pop ---")
    print(con.execute(f"SELECT DISTINCT juri, juri_nombre FROM '{PROV_POP}' WHERE juri > 1 ORDER BY juri").df())
    
    print("\n--- Depto Pop Buenos Aires ---")
    print(con.execute(f"SELECT DISTINCT departamento_codigo, departamento_nombre FROM '{DEPTO_POP}' WHERE juri_codigo = 6 LIMIT 10").df())
