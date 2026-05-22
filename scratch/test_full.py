import sys
sys.path.insert(0, '.')
from osint_engine import buscar_inaturalist, buscar_gbif, construir_timeline

print("=== iNATURALIST ===")
df_i = buscar_inaturalist('schilperoord', max_pages=1)
print(f"Observaciones: {len(df_i)}")
if not df_i.empty:
    print(df_i[['Fecha','Lugar','Especie','lat','lon','User_Login']].head(5).to_string())

print("\n=== GBIF ===")
df_g = buscar_gbif('schilperoord', limit=300)
print(f"Registros: {len(df_g)}")
if not df_g.empty:
    geo = df_g[df_g['lat'].notna()]
    print(f"Con GPS: {len(geo)}")
    print(df_g[['Fecha','Lugar','Pais','Especie']].head(5).to_string())

print("\n=== TIMELINE ===")
tl = construir_timeline(df_i, df_g)
print(f"Puntos GPS totales: {len(tl)}")
if not tl.empty:
    print(tl[['Fecha','Lugar','Plataforma']].head(5).to_string())
