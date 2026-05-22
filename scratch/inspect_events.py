import duckdb
import pandas as pd

BASE_PARQUET = 'data/base_nacional.parquet'

with duckdb.connect() as con:
    print("--- Checking Missing Location ---")
    query = f"SELECT id_provincia, Provincia, COUNT(*) as n FROM '{BASE_PARQUET}' WHERE id_provincia IS NULL OR id_provincia = '' OR id_provincia = '00' GROUP BY 1, 2"
    print(con.execute(query).df())
    
    print("\n--- Event List Sample ---")
    print(con.execute(f"SELECT DISTINCT Evento FROM '{BASE_PARQUET}' LIMIT 10").df())
