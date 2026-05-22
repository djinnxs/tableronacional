import duckdb
import pandas as pd

BASE_PARQUET = 'data/base_nacional.parquet'
PROV_POP_PARQUET = 'data/poblacionxprovinciaindec.parquet'

with duckdb.connect() as con:
    print("--- Base Nacional IDs ---")
    print(con.execute(f"SELECT id_provincia, Provincia FROM '{BASE_PARQUET}' LIMIT 5").df())
    
    print("\n--- Population IDs ---")
    print(con.execute(f"SELECT juri, juri_nombre FROM '{PROV_POP_PARQUET}' LIMIT 5").df())
