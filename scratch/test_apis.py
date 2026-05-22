import requests
# Test 1: Buscar usuarios por nombre en iNaturalist
r = requests.get('https://api.inaturalist.org/v1/users/autocomplete?q=schilperoord', timeout=10)
data = r.json()
print(f"Usuarios encontrados: {data.get('total_results', 0)}")
for u in data.get('results', []):
    print(f"  login={u.get('login')}, name={u.get('name')}, obs={u.get('observations_count')}")

# Test 2: Buscar por nombre con texto
r2 = requests.get('https://api.inaturalist.org/v1/observations?q=schilperoord&per_page=5', timeout=10)
d2 = r2.json()
print(f"\nObservaciones por texto: {d2.get('total_results', 0)}")
for obs in d2.get('results', [])[:3]:
    user = obs.get('user', {})
    print(f"  user={user.get('login')}, place={obs.get('place_guess')}, date={obs.get('observed_on')}")

# Test 3: GBIF search
r3 = requests.get('https://api.gbif.org/v1/occurrence/search?q=schilperoord&limit=5', timeout=10)
d3 = r3.json()
print(f"\nGBIF registros: {d3.get('count', 0)}")
for rec in d3.get('results', [])[:3]:
    print(f"  sp={rec.get('species')}, country={rec.get('country')}, date={rec.get('eventDate')}, by={rec.get('recordedBy')}")
