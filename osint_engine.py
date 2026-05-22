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


# ═══════════════════════════════════════════════════════════════════════════════
# BÚSQUEDA EN CUITONLINE.COM (WEB SCRAPING REAL - VERSIÓN CORREGIDA)
# ═══════════════════════════════════════════════════════════════════════════════

def buscar_cuitonline(query: str) -> list:
    """
    Busca información en cuitonline.com por DNI, CUIT o nombre.
    Extrae nombre, CUIT, género, dirección, localidad, provincia, actividades, impuestos.
    """
    resultados = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    try:
        url = f"https://www.cuitonline.com/search.php?q={quote_plus(query)}"
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return []
        
        html = response.text
        
        # ============================================================
        # MÉTODO 1: Buscar link de detalle directo
        # ============================================================
        link_match = re.search(r'<a href="(/detalle/[^"]+)"[^>]*>.*?<h2[^>]*>(.*?)</h2>', html, re.DOTALL | re.IGNORECASE)
        
        if link_match:
            url_detalle = f"https://www.cuitonline.com{link_match.group(1)}"
            nombre = re.sub(r'<[^>]+>', '', link_match.group(2)).strip()
            
            cuit_match = re.search(r'<span class="cuit">(\d{2}-\d{8}-\d{1})</span>', html)
            cuit = cuit_match.group(1) if cuit_match else ''
            
            genero_match = re.search(r'<i>(masculino|femenino)</i>', html, re.IGNORECASE)
            genero = genero_match.group(1).capitalize() if genero_match else ''
            
            detalles = obtener_detalles_pagina(url_detalle, headers)
            
            resultados.append({
                'Nombre': nombre,
                'CUIT': cuit,
                'Tipo': 'Persona Física',
                'Genero': genero,
                'URL': url_detalle,
                'Detalles': detalles
            })
        
        # ============================================================
        # MÉTODO 2: Si el método 1 falla, buscar directamente
        # ============================================================
        elif not resultados:
            nombre_match = re.search(r'<h2[^>]*class="denominacion"[^>]*>(.*?)</h2>', html, re.DOTALL)
            if nombre_match:
                nombre = re.sub(r'<[^>]+>', '', nombre_match.group(1)).strip()
                
                cuit_match = re.search(r'(\d{2}-\d{8}-\d{1})', html)
                cuit = cuit_match.group(1) if cuit_match else ''
                
                genero_match = re.search(r'Persona Física.*?<i>(.*?)</i>', html, re.DOTALL | re.IGNORECASE)
                genero = genero_match.group(1).capitalize() if genero_match else ''
                
                # Buscar nacionalidad
                nacionalidad_match = re.search(r'Persona Física.*?\(.*?\)', html, re.DOTALL)
                nacionalidad = ''
                if nacionalidad_match:
                    texto = nacionalidad_match.group(0)
                    if 'Argentino' in texto:
                        nacionalidad = 'Argentina'
                
                direccion_match = re.search(r'Direcci[oó]n[^:]*:\s*<[^>]*>\s*([^<]+)', html, re.IGNORECASE)
                direccion = direccion_match.group(1).strip() if direccion_match else ''
                
                localidad_match = re.search(r'Localidad[^:]*:\s*<[^>]*>\s*([^<]+)', html, re.IGNORECASE)
                localidad = localidad_match.group(1).strip() if localidad_match else ''
                
                provincia_match = re.search(r'Provincia[^:]*:\s*<[^>]*>\s*([^<]+)', html, re.IGNORECASE)
                provincia = provincia_match.group(1).strip() if provincia_match else ''
                
                detalles = {
                    'Direccion': direccion,
                    'Localidad': localidad,
                    'Provincia': provincia,
                    'Nacionalidad': nacionalidad,
                    'Actividad': '',
                    'Impuestos': ''
                }
                
                resultados.append({
                    'Nombre': nombre,
                    'CUIT': cuit,
                    'Tipo': 'Persona Física',
                    'Genero': genero,
                    'URL': url,
                    'Detalles': detalles
                })
        
        return resultados[:5]
        
    except Exception as e:
        print(f"Error en buscar_cuitonline: {e}")
        return []


def obtener_detalles_pagina(url: str, headers: dict) -> dict:
    """
    Obtiene TODOS los detalles de la página de detalle de una persona.
    Extrae dirección, localidad, provincia, actividades, impuestos, etc.
    """
    detalles = {
        'Direccion': '',
        'Localidad': '',
        'Provincia': '',
        'Nacionalidad': '',
        'Actividad': '',
        'Actividades': [],
        'Impuestos': '',
        'Impuestos_Activos': [],
        'Empleador': '',
        'Fecha_Inscripcion': ''
    }
    
    try:
        time.sleep(0.5)
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return detalles
        
        html = response.text
        
        # 1. Nacionalidad
        nac_match = re.search(r'Persona Física[^,]*,\s*([A-Za-zÁÉÍÓÚáéíóúñÑ]+)', html, re.IGNORECASE)
        if nac_match:
            detalles['Nacionalidad'] = nac_match.group(1).strip()
        
        # 2. Dirección
        dir_match = re.search(r'<strong>Direcci[oó]n</strong>\s*:?\s*</?(?:td|div)[^>]*>\s*([^<]+)', html, re.IGNORECASE | re.DOTALL)
        if not dir_match:
            dir_match = re.search(r'Direcci[oó]n\s*:?\s*</?(?:td|div)[^>]*>\s*([^<]+)', html, re.IGNORECASE)
        if dir_match:
            detalles['Direccion'] = re.sub(r'<[^>]+>', '', dir_match.group(1)).strip()
        
        # 3. Localidad
        loc_match = re.search(r'<strong>Localidad</strong>\s*:?\s*</?(?:td|div)[^>]*>\s*([^<]+)', html, re.IGNORECASE | re.DOTALL)
        if not loc_match:
            loc_match = re.search(r'Localidad\s*:?\s*</?(?:td|div)[^>]*>\s*([^<]+)', html, re.IGNORECASE)
        if loc_match:
            detalles['Localidad'] = re.sub(r'<[^>]+>', '', loc_match.group(1)).strip()
        
        # 4. Provincia
        prov_match = re.search(r'<strong>Provincia</strong>\s*:?\s*</?(?:td|div)[^>]*>\s*([^<]+)', html, re.IGNORECASE | re.DOTALL)
        if not prov_match:
            prov_match = re.search(r'Provincia\s*:?\s*</?(?:td|div)[^>]*>\s*([^<]+)', html, re.IGNORECASE)
        if prov_match:
            detalles['Provincia'] = re.sub(r'<[^>]+>', '', prov_match.group(1)).strip()
        
        # 5. Fecha de inscripción
        fecha_match = re.search(r'Fecha de inscripci[oó]n\s*:?\s*</?(?:td|div)[^>]*>\s*([^<]+)', html, re.IGNORECASE)
        if fecha_match:
            detalles['Fecha_Inscripcion'] = re.sub(r'<[^>]+>', '', fecha_match.group(1)).strip()
        
        # 6. Empleador
        emp_match = re.search(r'Empleador\s*:?\s*</?(?:td|div)[^>]*>\s*([^<]+)', html, re.IGNORECASE)
        if emp_match:
            detalles['Empleador'] = re.sub(r'<[^>]+>', '', emp_match.group(1)).strip()
        
        # 7. Impuestos activos
        impuestos_section = re.search(r'Impuestos activos[^:]*:\s*(.*?)(?=<br|</div|$)', html, re.DOTALL | re.IGNORECASE)
        if impuestos_section:
            imp_text = impuestos_section.group(1)
            impuestos = re.findall(r'([A-ZÁÉÍÓÚÑ\s]+(?:PERSONAS FISICAS|EXENTO|INSCRIPTO|NO INSCRIPTO)?)', imp_text, re.IGNORECASE)
            detalles['Impuestos_Activos'] = [i.strip() for i in impuestos if i.strip() and len(i.strip()) > 3]
            detalles['Impuestos'] = ' | '.join(detalles['Impuestos_Activos'][:5])
        
        # 8. Actividades económicas
        act_section = re.search(r'Actividad(?:es)?[^:]*:\s*(.*?)(?=Nota:|$)', html, re.DOTALL | re.IGNORECASE)
        if act_section:
            act_text = act_section.group(1)
            actividades = re.findall(r'(\d+\s*-\s*[^<]+?)(?=<br|</div|$)', act_text)
            if actividades:
                detalles['Actividades'] = [a.strip() for a in actividades if a.strip()]
                detalles['Actividad'] = detalles['Actividades'][0] if detalles['Actividades'] else ''
        
        # 9. Búsqueda en tabla de datos
        if not detalles['Direccion'] and not detalles['Localidad']:
            patron_tabla = r'<td[^>]*class="[^"]*label[^"]*"[^>]*>(.*?)</td>\s*<td[^>]*class="[^"]*dato[^"]*"[^>]*>(.*?)</td>'
            matches = re.findall(patron_tabla, html, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                clave = re.sub(r'<[^>]+>', '', match[0]).strip().lower()
                valor = re.sub(r'<[^>]+>', '', match[1]).strip()
                
                if 'direcci' in clave:
                    detalles['Direccion'] = valor
                elif 'localidad' in clave:
                    detalles['Localidad'] = valor
                elif 'provincia' in clave:
                    detalles['Provincia'] = valor
                elif 'nacionalidad' in clave:
                    detalles['Nacionalidad'] = valor
                elif 'actividad' in clave:
                    detalles['Actividad'] = valor
                elif 'fecha de inscripci' in clave:
                    detalles['Fecha_Inscripcion'] = valor
                    
    except Exception as e:
        print(f"Error obteniendo detalles de {url}: {e}")
    
    return detalles


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
            v.add(partes[0][0].lower() + partes[-1].lower())
            v.add(partes[0].lower() + partes[-1][0].lower())
            v.add(partes[0].lower() + partes[-1].lower())
            v.add(partes[-1].lower() + partes[0].lower())
            v.add(partes[-1].lower() + partes[0][0].lower())
            v.add(partes[0].lower() + '_' + partes[-1].lower())
            v.add(partes[0].lower() + '.' + partes[-1].lower())
            v.add(partes[-1].lower() + '_' + partes[0].lower())
            v.add(partes[0][:3].lower() + partes[-1][:3].lower())
    return list(v)


# ═══════════════════════════════════════════════════════════════════════════════
# API: iNATURALIST
# ═══════════════════════════════════════════════════════════════════════════════

def _descubrir_usuarios_inat(query: str) -> list:
    """Descubre usuarios reales en iNaturalist por autocompletado y variaciones."""
    logins = set()
    for term in [query, query.split()[-1] if ' ' in query else query]:
        try:
            url = f"https://api.inaturalist.org/v1/users/autocomplete?q={quote_plus(term)}&per_page=20"
            r = requests.get(url, headers={'User-Agent': UA}, timeout=TIMEOUT)
            if r.status_code == 200:
                for u in r.json().get('results', []):
                    login = u.get('login', '')
                    name = (u.get('name') or '').lower()
                    q_low = query.lower()
                    if (q_low in name or q_low in login or
                        any(p in name or p in login for p in q_low.split())):
                        logins.add(login)
        except Exception:
            pass
    for var in generar_variaciones_username(query):
        logins.add(var)
    return list(logins)


def buscar_inaturalist(query: str, max_pages=5) -> pd.DataFrame:
    """Extrae observaciones geolocalizadas REALES de iNaturalist."""
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
                    obs_totales.append({
                        'id': oid,
                        'lat': lat, 'lon': lon,
                        'Especie': obs.get('species_guess') or taxon.get('name', 'Desconocido'),
                        'Fecha': obs.get('observed_on', ''),
                        'Lugar': place,
                        'Calidad': obs.get('quality_grade', ''),
                        'Usuario': var,
                        'Usuario_Real': obs.get('user', {}).get('name', var),
                        'Plataforma': 'iNaturalist',
                        'URL': f"https://www.inaturalist.org/observations/{oid}",
                    })
            except Exception:
                break
    
    df = pd.DataFrame(obs_totales)
    if not df.empty and 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.sort_values('Fecha', ascending=False)
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# API: GBIF
# ═══════════════════════════════════════════════════════════════════════════════

def buscar_gbif(query: str, limit=500) -> pd.DataFrame:
    """Extrae registros de biodiversidad reales del GBIF."""
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
                        'Registrado_por': rec.get('recordedBy', ''),
                        'Plataforma': 'GBIF',
                        'URL': f"https://www.gbif.org/occurrence/{key}",
                    })
            except Exception:
                break
    
    _fetch_gbif(f"q={quote_plus(query)}", limit)
    
    if ' ' in query:
        apellido = query.split()[-1]
        _fetch_gbif(f"recordedBy={quote_plus(apellido)}", min(limit, 300))
    
    df = pd.DataFrame(registros)
    if not df.empty and 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# API: WAYBACK MACHINE
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
                }
            paises[pais_candidato]['registros'] += 1
            paises[pais_candidato]['ultima_vez'] = row.get('Fecha')
    
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
                'Sospechoso': vel > 900,
            })
        prev = row.to_dict()
    
    return pd.DataFrame(saltos)


# ═══════════════════════════════════════════════════════════════════════════════
# GENERADOR DE ENLACES OSINT
# ═══════════════════════════════════════════════════════════════════════════════

def generar_enlaces_osint(query: str, tipo: str) -> list:
    """Genera enlaces de búsqueda organizados por categoría."""
    q = quote_plus(query)
    qr = query.replace(' ', '')
    
    enlaces = [
        {"cat": "🌿 Naturaleza", "nombre": "iNaturalist", "url": f"https://www.inaturalist.org/people/{qr}", "prioridad": 1},
        {"cat": "🌿 Naturaleza", "nombre": "eBird", "url": f"https://ebird.org/profile/{qr}", "prioridad": 1},
        {"cat": "💬 Redes", "nombre": "Twitter/X", "url": f"https://twitter.com/{qr}", "prioridad": 1},
        {"cat": "💬 Redes", "nombre": "Instagram", "url": f"https://www.instagram.com/{qr}/", "prioridad": 1},
        {"cat": "💬 Redes", "nombre": "Facebook", "url": f"https://www.facebook.com/search/top/?q={q}", "prioridad": 1},
        {"cat": "💬 Redes", "nombre": "LinkedIn", "url": f"https://www.linkedin.com/search/results/people/?keywords={q}", "prioridad": 1},
        {"cat": "🗺️ Geo/GPS", "nombre": "Strava", "url": f"https://www.strava.com/athletes/search?text={q}", "prioridad": 1},
        {"cat": "🕵️ OSINT", "nombre": "Wayback Machine", "url": f"https://web.archive.org/web/*/{qr}", "prioridad": 1},
        {"cat": "🔎 Deep Search", "nombre": "Google", "url": f'https://www.google.com/search?q="{query}"', "prioridad": 1},
        {"cat": "🔎 Deep Search", "nombre": "Google PDFs", "url": f'https://www.google.com/search?q=filetype:pdf+"{query}"', "prioridad": 1},
        {"cat": "📄 Documentos", "nombre": "CuitOnline", "url": f"https://www.cuitonline.com/search.php?q={q}", "prioridad": 1},
        {"cat": "📄 Documentos", "nombre": "Dateas", "url": f"https://www.dateas.com/es/consulta_cuit_cuil?name=&cuit={qr}", "prioridad": 1},
    ]
    
    if tipo in ['documento', 'cuit']:
        enlaces.extend([
            {"cat": "📄 Documentos", "nombre": "Boletín Oficial", "url": f"https://www.boletinoficial.gob.ar/search?q={q}", "prioridad": 1},
        ])
    
    return enlaces


# ═══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN COMPLETA
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
        progress_callback(10, "Buscando en iNaturalist...")
    resultados['inaturalist'] = buscar_inaturalist(query)

    if progress_callback:
        progress_callback(25, "Extrayendo identidad de CuitOnline...")
    resultados['cuitonline'] = buscar_cuitonline(query)
    
    if progress_callback:
        progress_callback(35, "Buscando en GBIF...")
    resultados['gbif'] = buscar_gbif(query)
    
    if progress_callback:
        progress_callback(55, "Verificando Wayback Machine...")
    resultados['wayback'] = buscar_wayback(query)
    
    if progress_callback:
        progress_callback(70, "Construyendo timeline...")
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
    
    total_obs = len(resultados['inaturalist']) + len(resultados['gbif'])
    total_geo = len(resultados['timeline'])
    resultados['stats'] = {
        'total_observaciones': total_obs,
        'total_geolocalizadas': total_geo,
        'total_paises': len(resultados['paises']),
        'total_enlaces': len(resultados['enlaces']),
        'total_wayback': len(resultados['wayback']),
        'total_identidades': len(resultados['cuitonline']),
        'tiene_datos_reales': (total_obs > 0 or len(resultados['cuitonline']) > 0),
    }
    
    if progress_callback:
        progress_callback(100, "Análisis completo.")
    
    return resultados