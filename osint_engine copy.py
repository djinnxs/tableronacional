"""
OSINT ENGINE — Motor de Inteligencia Epidemiológica
Extrae datos REALES de APIs públicas, cruza fuentes y construye perfiles geográficos.
"""
import requests
import pandas as pd
import re
import json
import hashlib
import time
from urllib.parse import quote_plus
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "EpiSeek-OSINT/2.0 (epidemiological-research)"
TIMEOUT = 12

def buscar_cuitonline(query: str) -> list:
    """Usa la librería oficial cuitonline para obtener datos reales y detallados."""
    try:
        import cuitonline
        
        # Búsqueda usando el método oficial
        personas = cuitonline.search(query)
        resultados = []
        
        for p in personas[:5]:  # Limitar a top 5 para velocidad
            # Mapear al formato esperado por el dashboard
            # Nota: La librería oficial usa 'direccion', 'provincia', etc.
            res = {
                "Nombre": getattr(p, 'nombre', ''),
                "CUIT": getattr(p, 'cuit', ''),
                "Tipo": getattr(p, 'tipo_persona', 'física'),
                "URL": getattr(p, 'url', ''),
                "Detalles": {
                    "Genero": getattr(p, 'genero', ''),
                    "Direccion": getattr(p, 'direccion', ''),
                    "Localidad": getattr(p, 'localidad', ''),
                    "Provincia": getattr(p, 'provincia', ''),
                    "Nacionalidad": getattr(p, 'nacionalidad', ''),
                    "Actividad": getattr(p, 'monotributo', '')  # Usamos monotributo como actividad si no hay campo actividad
                }
            }
            resultados.append(res)
        return resultados
    except Exception as e:
        print(f"Error en cuitonline oficial: {e}")
        return []

# ═══════════════════════════════════════════════════════════════════════════════
# DETECCIÓN INTELIGENTE DE TIPO DE QUERY
# ═══════════════════════════════════════════════════════════════════════════════

def detectar_tipo_query(query: str) -> str:
    q = query.strip()
    if re.match(r'^\d{7,8}$', q): return 'documento'
    if re.match(r'^\d{2}-\d{8}-\d$', q) or re.match(r'^\d{11}$', q): return 'cuit'
    if re.match(r'^[^@]+@[^@]+\.[^@]+$', q): return 'email'
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', q): return 'ip'
    if re.match(r'^(\+\d{1,3})?[\s\-]?\d{6,15}$', q): return 'telefono'
    if re.match(r'^https?://', q): return 'url'
    return 'usuario'

def generar_variaciones_username(query: str) -> list:
    """Genera variaciones inteligentes del nombre para maximizar hallazgos."""
    v = set()
    v.add(query)
    v.add(query.lower())
    v.add(query.replace(' ', ''))
    v.add(query.replace(' ', '_'))
    v.add(query.replace(' ', '.'))
    v.add(query.replace(' ', '-'))
    v.add(query.lower().replace(' ', ''))
    v.add(query.lower().replace(' ', '_'))
    v.add(query.lower().replace(' ', '.'))
    v.add(query.lower().replace(' ', '-'))
    if ' ' in query:
        partes = query.split()
        if len(partes) >= 2:
            v.add(partes[0][0].lower() + partes[-1].lower())       # jsmith
            v.add(partes[0].lower() + partes[-1][0].lower())       # johns
            v.add(partes[0].lower() + partes[-1].lower())           # johnsmith
            v.add(partes[-1].lower() + partes[0].lower())           # smithjohn
            v.add(partes[-1].lower() + partes[0][0].lower())       # smithj
            v.add(partes[0].lower() + '_' + partes[-1].lower())    # john_smith
            v.add(partes[0].lower() + '.' + partes[-1].lower())    # john.smith
            v.add(partes[-1].lower() + '_' + partes[0].lower())    # smith_john
            v.add(partes[0][:3].lower() + partes[-1][:3].lower())  # johsmi
    return list(v)

# ═══════════════════════════════════════════════════════════════════════════════
# API: iNATURALIST (datos reales con coordenadas GPS)
# ═══════════════════════════════════════════════════════════════════════════════

def _descubrir_usuarios_inat(query: str) -> list:
    """Descubre usuarios reales en iNaturalist por autocompletado y variaciones."""
    logins = set()
    # 1) Buscar por autocompletado (descubre nombres reales)
    for term in [query, query.split()[-1] if ' ' in query else query]:
        try:
            url = f"https://api.inaturalist.org/v1/users/autocomplete?q={quote_plus(term)}&per_page=20"
            r = requests.get(url, headers={'User-Agent': UA}, timeout=TIMEOUT)
            if r.status_code == 200:
                for u in r.json().get('results', []):
                    login = u.get('login', '')
                    name = (u.get('name') or '').lower()
                    q_low = query.lower()
                    # Incluir si el nombre o login coinciden parcialmente
                    if (q_low in name or q_low in login or
                        any(p in name or p in login for p in q_low.split())):
                        logins.add(login)
        except Exception:
            pass
    # 2) Agregar variaciones directas
    for var in generar_variaciones_username(query):
        logins.add(var)
    return list(logins)

def buscar_inaturalist(query: str, max_pages=5) -> pd.DataFrame:
    """Extrae observaciones geolocalizadas REALES de iNaturalist.
    Primero descubre usuarios reales, luego extrae todas sus observaciones."""
    usuarios = _descubrir_usuarios_inat(query)
    obs_totales = []
    seen_ids = set()

    for var in usuarios:
        for page in range(1, max_pages + 1):
            try:
                url = (f"https://api.inaturalist.org/v1/observations?"
                       f"user_login={quote_plus(var)}&per_page=200&page={page}"
                       f"&order=desc&order_by=observed_on")
                r = requests.get(url, headers={'User-Agent': UA}, timeout=TIMEOUT)
                if r.status_code != 200:
                    break
                data = r.json()
                results = data.get('results', [])
                if not results:
                    break
                for obs in results:
                    oid = obs.get('id')
                    if oid in seen_ids:
                        continue
                    seen_ids.add(oid)
                    geo = obs.get('geojson')
                    lat, lon = None, None
                    if geo and geo.get('coordinates'):
                        lon, lat = geo['coordinates']
                    place = obs.get('place_guess', '')
                    taxon = obs.get('taxon') or {}
                    photos = obs.get('photos', [])
                    photo_url = photos[0].get('url', '').replace('square', 'medium') if photos else ''
                    obs_totales.append({
                        'id': oid,
                        'lat': lat, 'lon': lon,
                        'Especie': obs.get('species_guess') or taxon.get('name', 'Desconocido'),
                        'Taxon': taxon.get('preferred_common_name') or taxon.get('name', ''),
                        'Fecha': obs.get('observed_on', ''),
                        'Hora': obs.get('time_observed_at', ''),
                        'Lugar': place,
                        'Calidad': obs.get('quality_grade', ''),
                        'Usuario': var,
                        'Usuario_Real': obs.get('user', {}).get('name', var),
                        'User_Login': obs.get('user', {}).get('login', var),
                        'Plataforma': 'iNaturalist',
                        'URL': f"https://www.inaturalist.org/observations/{oid}",
                        'Foto': photo_url,
                        'Descripcion': obs.get('description', '') or '',
                        'Pais': '',
                        'Coordenadas_Exactas': lat is not None,
                    })
            except Exception:
                break
    
    df = pd.DataFrame(obs_totales)
    if not df.empty and 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.sort_values('Fecha', ascending=False)
    return df

# ═══════════════════════════════════════════════════════════════════════════════
# API: GBIF (Base Global de Biodiversidad — datos de museo/campo)
# ═══════════════════════════════════════════════════════════════════════════════

def buscar_gbif(query: str, limit=500) -> pd.DataFrame:
    """Extrae registros de biodiversidad reales del GBIF.
    Usa búsqueda por texto (q=) Y por recordedBy para máxima cobertura."""
    registros = []
    seen = set()
    
    def _fetch_gbif(params_str, max_records=300):
        for offset in range(0, max_records, 300):
            try:
                url = f"https://api.gbif.org/v1/occurrence/search?{params_str}&limit=300&offset={offset}"
                r = requests.get(url, headers={'User-Agent': UA}, timeout=TIMEOUT)
                if r.status_code != 200:
                    break
                data = r.json()
                results = data.get('results', [])
                if not results:
                    break
                for rec in results:
                    key = rec.get('key')
                    if key in seen:
                        continue
                    seen.add(key)
                    lat = rec.get('decimalLatitude')
                    lon = rec.get('decimalLongitude')
                    registros.append({
                        'id': key,
                        'lat': lat, 'lon': lon,
                        'Especie': rec.get('species') or rec.get('scientificName', 'Desconocido'),
                        'Fecha': rec.get('eventDate', ''),
                        'Lugar': rec.get('locality') or rec.get('stateProvince', ''),
                        'Pais': rec.get('country', ''),
                        'Pais_Codigo': rec.get('countryCode', ''),
                        'Dataset': rec.get('datasetName', ''),
                        'Institucion': rec.get('institutionCode', ''),
                        'Registrado_por': rec.get('recordedBy', ''),
                        'Plataforma': 'GBIF',
                        'URL': f"https://www.gbif.org/occurrence/{key}",
                        'Coordenadas_Exactas': lat is not None,
                    })
            except Exception:
                break
    
    # Búsqueda 1: texto libre (la más poderosa - encontró 10810 registros en test)
    _fetch_gbif(f"q={quote_plus(query)}", limit)
    
    # Búsqueda 2: por recordedBy con apellido
    if ' ' in query:
        apellido = query.split()[-1]
        _fetch_gbif(f"recordedBy={quote_plus(apellido)}", min(limit, 300))
    
    df = pd.DataFrame(registros)
    if not df.empty and 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    return df

# ═══════════════════════════════════════════════════════════════════════════════
# API: WAYBACK MACHINE (historial de actividad web)
# ═══════════════════════════════════════════════════════════════════════════════

def buscar_wayback(query: str) -> list:
    """Busca capturas históricas de la persona en Wayback Machine."""
    resultados = []
    urls_check = [
        f"https://twitter.com/{query.replace(' ', '')}",
        f"https://www.instagram.com/{query.replace(' ', '')}/",
        f"https://www.facebook.com/{query.replace(' ', '')}",
        f"https://ebird.org/profile/{query.replace(' ', '')}",
        f"https://www.inaturalist.org/people/{query.replace(' ', '')}",
        f"https://github.com/{query.replace(' ', '')}",
        f"https://www.flickr.com/people/{query.replace(' ', '')}",
        f"https://www.strava.com/athletes/{query.replace(' ', '')}",
    ]
    for url in urls_check:
        try:
            api = f"https://archive.org/wayback/available?url={quote_plus(url)}"
            r = requests.get(api, headers={'User-Agent': UA}, timeout=8)
            if r.status_code == 200:
                data = r.json()
                snap = data.get('archived_snapshots', {}).get('closest', {})
                if snap.get('available'):
                    resultados.append({
                        'URL_Original': url,
                        'URL_Archivo': snap.get('url', ''),
                        'Fecha_Captura': snap.get('timestamp', ''),
                        'Status': snap.get('status', ''),
                    })
        except Exception:
            pass
    return resultados

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTRUCCIÓN DE PERFIL GEOGRÁFICO Y TIMELINE
# ═══════════════════════════════════════════════════════════════════════════════

def construir_timeline(df_inat: pd.DataFrame, df_gbif: pd.DataFrame) -> pd.DataFrame:
    """Fusiona datos de múltiples fuentes en un timeline unificado."""
    frames = []
    cols = ['Fecha', 'lat', 'lon', 'Lugar', 'Especie', 'Plataforma', 'URL']
    
    for df_src in [df_inat, df_gbif]:
        if df_src is not None and not df_src.empty:
            df_copy = df_src.copy()
            # Asegurar que exista columna 'Usuario'
            if 'Usuario' not in df_copy.columns:
                df_copy['Usuario'] = df_copy.get('Registrado_por', df_copy.get('User_Login', ''))
            use_cols = cols + ['Usuario']
            for c in use_cols:
                if c not in df_copy.columns:
                    df_copy[c] = ''
            frames.append(df_copy[use_cols].copy())
    
    if not frames:
        return pd.DataFrame()
    
    df = pd.concat(frames, ignore_index=True)
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df = df.dropna(subset=['lat', 'lon'])
    df = df.sort_values('Fecha')
    return df

def analizar_paises_visitados(timeline: pd.DataFrame) -> dict:
    """Analiza en qué países estuvo la persona según coordenadas."""
    paises = {}
    if timeline.empty:
        return paises
    
    for _, row in timeline.iterrows():
        lat, lon = row.get('lat'), row.get('lon')
        if pd.isna(lat) or pd.isna(lon):
            continue
        lugar = str(row.get('Lugar', ''))
        # Extraer país del campo Lugar
        if ',' in lugar:
            partes = [p.strip() for p in lugar.split(',')]
            pais_candidato = partes[-1]
        else:
            pais_candidato = lugar
        
        if pais_candidato and len(pais_candidato) > 1:
            if pais_candidato not in paises:
                paises[pais_candidato] = {
                    'primera_vez': row.get('Fecha'),
                    'ultima_vez': row.get('Fecha'),
                    'registros': 0,
                    'coordenadas': []
                }
            paises[pais_candidato]['registros'] += 1
            paises[pais_candidato]['ultima_vez'] = row.get('Fecha')
            paises[pais_candidato]['coordenadas'].append((lat, lon))
    
    return paises

def calcular_distancia_km(lat1, lon1, lat2, lon2):
    """Calcula distancia entre dos puntos GPS en km (Haversine)."""
    import math
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def analizar_velocidad_desplazamiento(timeline: pd.DataFrame) -> pd.DataFrame:
    """Detecta saltos geográficos sospechosos (velocidad de desplazamiento)."""
    if timeline.empty or len(timeline) < 2:
        return pd.DataFrame()
    
    saltos = []
    prev = None
    for _, row in timeline.iterrows():
        if pd.isna(row.get('lat')) or pd.isna(row.get('lon')) or pd.isna(row.get('Fecha')):
            continue
        if prev is not None:
            dist = calcular_distancia_km(prev['lat'], prev['lon'], row['lat'], row['lon'])
            delta = (row['Fecha'] - prev['Fecha']).total_seconds() / 3600
            vel = dist / max(delta, 0.01)
            saltos.append({
                'Desde': prev.get('Lugar', ''),
                'Hasta': row.get('Lugar', ''),
                'Fecha_Desde': prev['Fecha'],
                'Fecha_Hasta': row['Fecha'],
                'Distancia_km': round(dist, 1),
                'Horas': round(delta, 1),
                'Velocidad_kmh': round(vel, 1),
                'Sospechoso': vel > 900,  # Más de 900 km/h = probablemente vuelo
            })
        prev = row.to_dict()
    
    return pd.DataFrame(saltos)

# ═══════════════════════════════════════════════════════════════════════════════
# GENERADOR DE ENLACES OSINT (complemento a los datos reales)
# ═══════════════════════════════════════════════════════════════════════════════

def generar_enlaces_osint(query: str, tipo: str) -> list:
    """Genera enlaces de búsqueda organizados por categoría."""
    q = quote_plus(query)
    qr = query.replace(' ', '')
    qu = query.replace(' ', '_')
    
    enlaces = [
        # === NATURALEZA / GEO (Crítico para epidemiología) ===
        {"cat": "🌿 Naturaleza", "nombre": "iNaturalist Perfil", "url": f"https://www.inaturalist.org/people/{qr}", "prioridad": 1},
        {"cat": "🌿 Naturaleza", "nombre": "iNaturalist Observaciones", "url": f"https://www.inaturalist.org/observations?user_id={qr}", "prioridad": 1},
        {"cat": "🌿 Naturaleza", "nombre": "eBird Perfil", "url": f"https://ebird.org/profile/{qr}", "prioridad": 1},
        {"cat": "🌿 Naturaleza", "nombre": "eBird Listas", "url": f"https://ebird.org/checklist/search?userId={qr}", "prioridad": 1},
        {"cat": "🌿 Naturaleza", "nombre": "GBIF Registros", "url": f"https://www.gbif.org/occurrence/search?recordedBy={q}", "prioridad": 1},
        {"cat": "🌿 Naturaleza", "nombre": "Xeno-canto", "url": f"https://xeno-canto.org/explore?query={q}", "prioridad": 2},
        # === REDES SOCIALES (Global) ===
        {"cat": "💬 Redes", "nombre": "Twitter/X", "url": f"https://twitter.com/{qr}", "prioridad": 1},
        {"cat": "💬 Redes", "nombre": "Twitter Búsqueda", "url": f"https://twitter.com/search?q={q}", "prioridad": 1},
        {"cat": "💬 Redes", "nombre": "Facebook", "url": f"https://www.facebook.com/search/top/?q={q}", "prioridad": 1},
        {"cat": "💬 Redes", "nombre": "Instagram", "url": f"https://www.instagram.com/{qr}/", "prioridad": 1},
        {"cat": "💬 Redes", "nombre": "LinkedIn", "url": f"https://www.linkedin.com/search/results/people/?keywords={q}", "prioridad": 1},
        {"cat": "💬 Redes", "nombre": "TikTok", "url": f"https://www.tiktok.com/@{qr}", "prioridad": 2},
        {"cat": "💬 Redes", "nombre": "Reddit", "url": f"https://www.reddit.com/search/?q={q}", "prioridad": 2},
        {"cat": "💬 Redes", "nombre": "Flickr", "url": f"https://www.flickr.com/search/?q={q}", "prioridad": 2},
        {"cat": "💬 Redes", "nombre": "YouTube", "url": f"https://www.youtube.com/results?search_query={q}", "prioridad": 2},
        {"cat": "💬 Redes", "nombre": "GitHub", "url": f"https://github.com/{qr}", "prioridad": 2},
        # === GEO / RUTAS GPS ===
        {"cat": "🗺️ Geo/GPS", "nombre": "Strava", "url": f"https://www.strava.com/athletes/search?text={q}", "prioridad": 1},
        {"cat": "🗺️ Geo/GPS", "nombre": "Wikiloc", "url": f"https://www.wikiloc.com/wikiloc/find.do?q={q}", "prioridad": 1},
        {"cat": "🗺️ Geo/GPS", "nombre": "Google Maps", "url": f"https://www.google.com/maps/search/{q}", "prioridad": 2},
        # === OSINT PROFUNDO ===
        {"cat": "🕵️ OSINT", "nombre": "Sherlock", "url": f"https://www.google.com/search?q=sherlock+osint+{q}", "prioridad": 1},
        {"cat": "🕵️ OSINT", "nombre": "WhatsMyName", "url": f"https://whatsmyname.app/?q={qr}", "prioridad": 1},
        {"cat": "🕵️ OSINT", "nombre": "Wayback Machine", "url": f"https://web.archive.org/web/*/{qr}", "prioridad": 1},
        {"cat": "🕵️ OSINT", "nombre": "Pastebin", "url": f"https://pastebin.com/search?q={q}", "prioridad": 2},
        # === BÚSQUEDA PROFUNDA (Dorks) ===
        {"cat": "🔎 Deep Search", "nombre": "Google exacto", "url": f'https://www.google.com/search?q="{query}"', "prioridad": 1},
        {"cat": "🔎 Deep Search", "nombre": "Google PDFs", "url": f'https://www.google.com/search?q=filetype:pdf+"{query}"', "prioridad": 1},
        {"cat": "🔎 Deep Search", "nombre": "Google Docs/XLS", "url": f'https://www.google.com/search?q=filetype:xls+OR+filetype:doc+"{query}"', "prioridad": 1},
        {"cat": "🔎 Deep Search", "nombre": "Google SQL", "url": f'https://www.google.com/search?q=filetype:sql+"{query}"', "prioridad": 2},
        {"cat": "🔎 Deep Search", "nombre": "Bing", "url": f"https://www.bing.com/search?q={q}", "prioridad": 2},
        {"cat": "🔎 Deep Search", "nombre": "Yandex", "url": f"https://yandex.com/search/?text={q}", "prioridad": 2},
        {"cat": "🔎 Deep Search", "nombre": "DuckDuckGo", "url": f"https://duckduckgo.com/?q={q}", "prioridad": 2},
        {"cat": "🔎 Deep Search", "nombre": "Google Scholar", "url": f"https://scholar.google.com/scholar?q={q}", "prioridad": 2},
        {"cat": "🔎 Deep Search", "nombre": "Documentos (Dork)", "url": f"https://www.google.com/search?q={q}+filetype:pdf+OR+filetype:doc+OR+filetype:xls", "prioridad": 1},
        {"cat": "🔎 Deep Search", "nombre": "Menciones en Noticias", "url": f"https://www.google.com/search?q={q}+news+OR+noticias", "prioridad": 1},
        {"cat": "🔎 Deep Search", "nombre": "Directorio Público", "url": f"https://www.google.com/search?q=intitle:index.of+{q}", "prioridad": 2},
    ]
    
    # Agregar fuentes de documentos argentinos si aplica
    if tipo in ['documento', 'cuit']:
        enlaces.extend([
            {"cat": "📄 Documentos", "nombre": "CuitOnline (Detalle)", "url": f"https://www.cuitonline.com/detalle/{qr}", "prioridad": 1},
            {"cat": "📄 Documentos", "nombre": "Dateas (DNI/CUIL)", "url": f"https://www.dateas.com/es/consulta_cuit_cuil?name=&cuit={qr}", "prioridad": 1},
            {"cat": "📄 Documentos", "nombre": "AFIP CUIT", "url": f"https://www.google.com/search?q=consulta+cuit+{q}", "prioridad": 1},
            {"cat": "📄 Documentos", "nombre": "Boletín Oficial", "url": f"https://www.boletinoficial.gob.ar/search?q={q}", "prioridad": 1},
            {"cat": "📄 Documentos", "nombre": "BCRA Deudores", "url": f"https://www.google.com/search?q=BCRA+deudores+{q}", "prioridad": 1},
            {"cat": "📄 Documentos", "nombre": "Padrón Electoral", "url": f"https://www.google.com/search?q=padrón+electoral+{q}", "prioridad": 1},
        ])
    
    if tipo == 'usuario':
        enlaces.extend([
            {"cat": "🔎 Deep Search", "nombre": "CuitOnline (Búsqueda)", "url": f"https://www.cuitonline.com/search.php?q={q}", "prioridad": 1},
            {"cat": "🔎 Deep Search", "nombre": "Dateas (Nombres)", "url": f"https://www.dateas.com/es/consulta_cuit_cuil?name={q}&cuit=", "prioridad": 1},
            {"cat": "🔎 Deep Search", "nombre": "TruePeopleSearch", "url": f"https://www.truepeoplesearch.com/results?name={q}", "prioridad": 2},
            {"cat": "🔎 Deep Search", "nombre": "Spokeo", "url": f"https://www.spokeo.com/{qr}", "prioridad": 2},
            {"cat": "🔎 Deep Search", "nombre": "PeekYou", "url": f"https://www.peekyou.com/{qr}", "prioridad": 2},
        ])

    # Agregar herramientas recomendadas
    enlaces.append({"cat": "🛠️ Librerías/Herramientas", "nombre": "CuitOnline API (Python)", "url": "https://github.com/mgaitan/cuitonline", "prioridad": 1})
    
    if tipo == 'email':
        enlaces.extend([
            {"cat": "🔒 Seguridad", "nombre": "Have I Been Pwned", "url": f"https://haveibeenpwned.com/account/{q}", "prioridad": 1},
            {"cat": "🔒 Seguridad", "nombre": "EmailRep", "url": f"https://emailrep.io/{q}", "prioridad": 1},
        ])
    
    if tipo == 'ip':
        enlaces.extend([
            {"cat": "🔒 Seguridad", "nombre": "AbuseIPDB", "url": f"https://www.abuseipdb.com/check/{q}", "prioridad": 1},
            {"cat": "🔒 Seguridad", "nombre": "VirusTotal", "url": f"https://www.virustotal.com/gui/search/{q}", "prioridad": 1},
            {"cat": "🔒 Seguridad", "nombre": "Shodan", "url": f"https://www.shodan.io/host/{q}", "prioridad": 1},
        ])
    
    return enlaces

# ═══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN COMPLETA DEL ANÁLISIS
# ═══════════════════════════════════════════════════════════════════════════════

def ejecutar_analisis_completo(query: str, progress_callback=None):
    """Ejecuta todas las búsquedas y devuelve un informe completo."""
    tipo = detectar_tipo_query(query)
    resultados = {
        'query': query,
        'tipo': tipo,
        'timestamp': datetime.now().isoformat(),
        'variaciones': generar_variaciones_username(query),
    }
    
    if progress_callback:
        progress_callback(10, "Buscando en iNaturalist (observaciones con GPS)...")
    resultados['inaturalist'] = buscar_inaturalist(query)

    if progress_callback:
        progress_callback(25, "Extrayendo identidad real de CuitOnline...")
    resultados['cuitonline'] = buscar_cuitonline(query)
    
    if progress_callback:
        progress_callback(35, "Buscando en GBIF (base global de biodiversidad)...")
    resultados['gbif'] = buscar_gbif(query)
    
    if progress_callback:
        progress_callback(55, "Verificando Wayback Machine (historial web)...")
    resultados['wayback'] = buscar_wayback(query)
    
    if progress_callback:
        progress_callback(70, "Construyendo timeline geográfico...")
    resultados['timeline'] = construir_timeline(
        resultados['inaturalist'], resultados['gbif']
    )
    
    if progress_callback:
        progress_callback(80, "Analizando desplazamientos...")
    resultados['desplazamientos'] = analizar_velocidad_desplazamiento(
        resultados['timeline']
    )
    
    if progress_callback:
        progress_callback(85, "Analizando países visitados...")
    resultados['paises'] = analizar_paises_visitados(resultados['timeline'])
    
    if progress_callback:
        progress_callback(90, "Generando enlaces OSINT...")
    resultados['enlaces'] = generar_enlaces_osint(query, tipo)
    
    # Estadísticas finales
    total_obs = len(resultados['inaturalist']) + len(resultados['gbif'])
    total_geo = len(resultados['timeline'])
    total_paises = len(resultados['paises'])
    resultados['stats'] = {
        'total_observaciones': total_obs,
        'total_geolocalizadas': total_geo,
        'total_paises': total_paises,
        'total_enlaces': len(resultados['enlaces']),
        'total_wayback': len(resultados['wayback']),
        'total_identidades': len(resultados['cuitonline']),
        'tiene_datos_reales': (total_obs > 0 or len(resultados['cuitonline']) > 0),
    }
    
    if progress_callback:
        progress_callback(100, "Análisis completo.")
    
    return resultados
