import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import streamlit.components.v1 as stc
import pandas as pd
import requests
from urllib.parse import quote_plus
import plotly.express as px
import time
import re
from utils import format_df_spanish

# ─── Configuración de la página ───────────────────────────────────────────────
st.set_page_config(
    page_title="Buscador — Rastreo de Actividad",
    page_icon="🔍",
    layout="wide"
)

# ─── CSS personalizado ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Rajdhani', sans-serif;
}

.stApp {
    background-color: #0a0e1a;
    color: #c8d8e8;
}

/* Título principal */
h1, h2, h3 {
    font-family: 'Share Tech Mono', monospace !important;
    color: #00e5ff !important;
}

/* Cajas de información */
.info-box {
    background: linear-gradient(135deg, #0d1b2a 0%, #112233 100%);
    border: 1px solid #00e5ff33;
    border-left: 3px solid #00e5ff;
    border-radius: 4px;
    padding: 14px 18px;
    margin: 8px 0;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.82rem;
    color: #8ecae6;
}

/* Tarjeta de resultado */
.result-card {
    background: #0d1b2a;
    border: 1px solid #1a3a5c;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 4px 0;
    transition: border-color 0.2s;
}
.result-card:hover {
    border-color: #00e5ff;
}

/* Badge de fuente */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 0.7rem;
    font-family: 'Share Tech Mono', monospace;
    font-weight: 700;
    letter-spacing: 0.05em;
    margin-right: 6px;
}
.badge-ebird     { background:#1a4a1a; color:#4ade80; border:1px solid #4ade8055; }
.badge-inaturalist{ background:#2a3a1a; color:#a3e635; border:1px solid #a3e63555; }
.badge-twitter   { background:#1a2a3a; color:#38bdf8; border:1px solid #38bdf855; }
.badge-reddit    { background:#3a1a0a; color:#fb923c; border:1px solid #fb923c55; }
.badge-facebook  { background:#1a2a4a; color:#818cf8; border:1px solid #818cf855; }
.badge-instagram { background:#3a1a2a; color:#f472b6; border:1px solid #f472b655; }
.badge-flickr    { background:#3a2a0a; color:#fb923c; border:1px solid #fb923c55; }
.badge-youtube   { background:#3a1a1a; color:#f87171; border:1px solid #f8717155; }
.badge-github    { background:#1a1a2a; color:#a78bfa; border:1px solid #a78bfa55; }
.badge-linkedin  { background:#0a2a3a; color:#60a5fa; border:1px solid #60a5fa55; }
.badge-google    { background:#1a1a1a; color:#94a3b8; border:1px solid #94a3b855; }
.badge-wayback   { background:#2a1a0a; color:#fbbf24; border:1px solid #fbbf2455; }
.badge-default   { background:#1a1a1a; color:#94a3b8; border:1px solid #94a3b855; }

/* Enlace de resultado */
a.result-link {
    color: #00e5ff;
    text-decoration: none;
    font-size: 0.85rem;
}
a.result-link:hover {
    text-decoration: underline;
}

/* Barra de progreso */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #00e5ff, #0077b6);
}

/* Botón principal */
div.stButton > button {
    background: linear-gradient(90deg, #023e8a, #0077b6);
    color: #ffffff;
    border: 1px solid #00b4d8;
    border-radius: 4px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 1rem;
    padding: 10px 28px;
    letter-spacing: 0.08em;
    transition: all 0.2s;
}
div.stButton > button:hover {
    background: linear-gradient(90deg, #0077b6, #00b4d8);
    border-color: #00e5ff;
    box-shadow: 0 0 12px #00e5ff55;
}

/* Input text */
div[data-baseweb="input"] input {
    background: #0d1b2a !important;
    border: 1px solid #1a3a5c !important;
    color: #c8d8e8 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.95rem !important;
    border-radius: 4px !important;
}
div[data-baseweb="input"] input:focus {
    border-color: #00e5ff !important;
    box-shadow: 0 0 8px #00e5ff33 !important;
}

/* Separador */
hr { border-color: #1a3a5c !important; }

/* Métricas */
[data-testid="metric-container"] {
    background: #0d1b2a;
    border: 1px solid #1a3a5c;
    border-radius: 6px;
    padding: 12px;
}
[data-testid="metric-container"] label {
    color: #8ecae6 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.75rem !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #00e5ff !important;
    font-family: 'Share Tech Mono', monospace !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Fuentes OSINT ────────────────────────────────────────────────────────────

FUENTES = [
    # Naturaleza / Aves / Observación
    {
        "nombre": "eBird",
        "tipo": "ebird",
        "url_tpl": "https://ebird.org/profile/{q}",
        "search_tpl": "https://ebird.org/search?q={q}",
        "categoria": "Naturaleza",
        "descripcion": "Perfil de usuario en eBird (observación de aves)"
    },
    {
        "nombre": "eBird Listas",
        "tipo": "ebird",
        "url_tpl": "https://ebird.org/checklist/search?userId={q}",
        "search_tpl": "https://ebird.org/checklist/search?userId={q}",
        "categoria": "Naturaleza",
        "descripcion": "Listas de observación en eBird"
    },
    {
        "nombre": "iNaturalist",
        "tipo": "inaturalist",
        "url_tpl": "https://www.inaturalist.org/people/{q}",
        "search_tpl": "https://www.inaturalist.org/people/{q}",
        "categoria": "Naturaleza",
        "descripcion": "Observaciones de naturaleza en iNaturalist"
    },
    {
        "nombre": "Xeno-canto",
        "tipo": "default",
        "url_tpl": "https://xeno-canto.org/explore?query={q}",
        "search_tpl": "https://xeno-canto.org/explore?query={q}",
        "categoria": "Naturaleza",
        "descripcion": "Grabaciones de cantos de aves"
    },
    # Redes sociales
    {
        "nombre": "Twitter/X",
        "tipo": "twitter",
        "url_tpl": "https://twitter.com/{q}",
        "search_tpl": "https://twitter.com/search?q={q}",
        "categoria": "Red Social",
        "descripcion": "Perfil y búsqueda en Twitter/X"
    },
    {
        "nombre": "Reddit",
        "tipo": "reddit",
        "url_tpl": "https://www.reddit.com/user/{q}",
        "search_tpl": "https://www.reddit.com/search/?q={q}",
        "categoria": "Red Social",
        "descripcion": "Perfil y posts en Reddit"
    },
    {
        "nombre": "Facebook",
        "tipo": "facebook",
        "url_tpl": "https://www.facebook.com/{q}",
        "search_tpl": "https://www.facebook.com/search/top/?q={q}",
        "categoria": "Red Social",
        "descripcion": "Perfil en Facebook"
    },
    {
        "nombre": "Instagram",
        "tipo": "instagram",
        "url_tpl": "https://www.instagram.com/{q}/",
        "search_tpl": "https://www.instagram.com/{q}/",
        "categoria": "Red Social",
        "descripcion": "Perfil en Instagram"
    },
    {
        "nombre": "LinkedIn",
        "tipo": "linkedin",
        "url_tpl": "https://www.linkedin.com/in/{q}",
        "search_tpl": "https://www.linkedin.com/search/results/people/?keywords={q}",
        "categoria": "Red Social",
        "descripcion": "Perfil profesional en LinkedIn"
    },
    # Fotos / Video
    {
        "nombre": "Flickr",
        "tipo": "flickr",
        "url_tpl": "https://www.flickr.com/people/{q}",
        "search_tpl": "https://www.flickr.com/search/?q={q}",
        "categoria": "Fotos",
        "descripcion": "Galería de fotos en Flickr"
    },
    {
        "nombre": "YouTube",
        "tipo": "youtube",
        "url_tpl": "https://www.youtube.com/@{q}",
        "search_tpl": "https://www.youtube.com/results?search_query={q}",
        "categoria": "Video",
        "descripcion": "Canal y búsqueda en YouTube"
    },
    # Código / Técnico
    {
        "nombre": "GitHub",
        "tipo": "github",
        "url_tpl": "https://github.com/{q}",
        "search_tpl": "https://github.com/search?q={q}",
        "categoria": "Técnico",
        "descripcion": "Perfil de desarrollador en GitHub"
    },
    # Búsqueda general
    {
        "nombre": "Google",
        "tipo": "google",
        "url_tpl": 'https://www.google.com/search?q="{q}"',
        "search_tpl": 'https://www.google.com/search?q="{q}"',
        "categoria": "Búsqueda",
        "descripcion": "Búsqueda general en Google"
    },
    {
        "nombre": "Google + Argentina",
        "tipo": "google",
        "url_tpl": 'https://www.google.com/search?q="{q}"+Argentina',
        "search_tpl": 'https://www.google.com/search?q="{q}"+Argentina',
        "categoria": "Búsqueda",
        "descripcion": "Búsqueda Google filtrada a Argentina"
    },
    {
        "nombre": "Google + Lugares",
        "tipo": "google",
        "url_tpl": 'https://www.google.com/search?q="{q}"+lugares+viaje+Argentina',
        "search_tpl": 'https://www.google.com/search?q="{q}"+lugares+viaje+Argentina',
        "categoria": "Búsqueda",
        "descripcion": "Búsqueda de trayectoria y lugares visitados"
    },
    {
        "nombre": "Bing",
        "tipo": "google",
        "url_tpl": "https://www.bing.com/search?q={q}",
        "search_tpl": "https://www.bing.com/search?q={q}",
        "categoria": "Búsqueda",
        "descripcion": "Búsqueda en Bing"
    },
    # Foros y comunidades
    {
        "nombre": "Forobirds",
        "tipo": "default",
        "url_tpl": "https://www.forobirds.com.ar/search?q={q}",
        "search_tpl": "https://www.forobirds.com.ar/search?q={q}",
        "categoria": "Foro",
        "descripcion": "Foro de aves de Argentina"
    },
    {
        "nombre": "Aves Argentinas",
        "tipo": "default",
        "url_tpl": "https://www.avesargentinas.org.ar/?s={q}",
        "search_tpl": "https://www.avesargentinas.org.ar/?s={q}",
        "categoria": "Foro",
        "descripcion": "Asociación Aves Argentinas — Búsqueda"
    },
    {
        "nombre": "Wayback Machine",
        "tipo": "wayback",
        "url_tpl": "https://web.archive.org/web/*/{q}",
        "search_tpl": "https://web.archive.org/web/*/{q}",
        "categoria": "Archivo",
        "descripcion": "Páginas archivadas en Wayback Machine"
    },
    {
        "nombre": "Pastebin",
        "tipo": "default",
        "url_tpl": "https://pastebin.com/search?q={q}",
        "search_tpl": "https://pastebin.com/search?q={q}",
        "categoria": "Archivo",
        "descripcion": "Búsqueda en Pastebin"
    },
    # OSINT específico
    {
        "nombre": "Sherlock (web)",
        "tipo": "default",
        "url_tpl": "https://sherlock-project.github.io/?q={q}",
        "search_tpl": "https://www.google.com/search?q=sherlock+osint+{q}",
        "categoria": "OSINT",
        "descripcion": "Proyecto Sherlock — rastreo de usuario en 400+ sitios"
    },
    {
        "nombre": "WhatsMyName",
        "tipo": "default",
        "url_tpl": "https://whatsmyname.app/?q={q}",
        "search_tpl": "https://whatsmyname.app/?q={q}",
        "categoria": "OSINT",
        "descripcion": "Verificación de nombre de usuario en múltiples plataformas"
    },
    {
        "nombre": "Namecheckr",
        "tipo": "default",
        "url_tpl": "https://www.namecheckr.com/check?q={q}",
        "search_tpl": "https://www.namecheckr.com/check?q={q}",
        "categoria": "OSINT",
        "descripcion": "Disponibilidad de nombre de usuario en redes"
    },
    # Mapas / Geo / Rastreo GPS
    {
        "nombre": "Google Maps",
        "tipo": "google",
        "url_tpl": "https://www.google.com/maps/search/{q}",
        "search_tpl": "https://www.google.com/maps/search/{q}",
        "categoria": "Geo",
        "descripcion": "Búsqueda geográfica en Google Maps"
    },
    {
        "nombre": "OpenStreetMap",
        "tipo": "default",
        "url_tpl": "https://www.openstreetmap.org/search?query={q}",
        "search_tpl": "https://www.openstreetmap.org/search?query={q}",
        "categoria": "Geo",
        "descripcion": "Búsqueda en OpenStreetMap"
    },
    {
        "nombre": "Strava",
        "tipo": "strava",
        "url_tpl": "https://www.strava.com/athletes/search?utf8=✓&text={q}",
        "search_tpl": "https://www.strava.com/athletes/search?utf8=✓&text={q}",
        "categoria": "Geo",
        "descripcion": "Rutas GPS de actividad física (correr, ciclismo, caminata)"
    },
    {
        "nombre": "Wikiloc",
        "tipo": "default",
        "url_tpl": "https://www.wikiloc.com/wikiloc/find.do?q={q}",
        "search_tpl": "https://www.wikiloc.com/wikiloc/find.do?q={q}",
        "categoria": "Geo",
        "descripcion": "Rutas y senderos GPS compartidos por usuarios"
    },
    # Fuentes globales adicionales
    {
        "nombre": "TikTok",
        "tipo": "default",
        "url_tpl": "https://www.tiktok.com/@{q}",
        "search_tpl": "https://www.tiktok.com/search?q={q}",
        "categoria": "Red Social",
        "descripcion": "Perfil y búsqueda en TikTok"
    },
    {
        "nombre": "Yandex",
        "tipo": "default",
        "url_tpl": "https://yandex.com/search/?text={q}",
        "search_tpl": "https://yandex.com/search/?text={q}",
        "categoria": "Búsqueda",
        "descripcion": "Motor de búsqueda ruso — cobertura global alternativa"
    },
    {
        "nombre": "DuckDuckGo",
        "tipo": "default",
        "url_tpl": "https://duckduckgo.com/?q={q}",
        "search_tpl": "https://duckduckgo.com/?q={q}",
        "categoria": "Búsqueda",
        "descripcion": "Búsqueda privada global"
    },
    {
        "nombre": "GBIF",
        "tipo": "default",
        "url_tpl": "https://www.gbif.org/occurrence/search?recordedBy={q}",
        "search_tpl": "https://www.gbif.org/occurrence/search?recordedBy={q}",
        "categoria": "Naturaleza",
        "descripcion": "Base global de biodiversidad — registros por recolector"
    },
    {
        "nombre": "Google Scholar",
        "tipo": "google",
        "url_tpl": "https://scholar.google.com/scholar?q={q}",
        "search_tpl": "https://scholar.google.com/scholar?q={q}",
        "categoria": "Búsqueda",
        "descripcion": "Publicaciones académicas y científicas"
    },
]


def build_url(tpl: str, query: str) -> str:
    """Reemplaza {q} en la plantilla con la query codificada."""
    return tpl.replace("{q}", quote_plus(query))


def generar_resultados(query: str) -> pd.DataFrame:
    """Genera la tabla de resultados OSINT para la query dada."""
    rows = []
    for fuente in FUENTES:
        url_perfil = build_url(fuente["url_tpl"], query)
        url_busqueda = build_url(fuente["search_tpl"], query)
        rows.append({
            "Fuente": fuente["nombre"],
            "Categoría": fuente["categoria"],
            "Descripción": fuente["descripcion"],
            "URL Perfil / Búsqueda": url_busqueda,
            "URL Directa": url_perfil,
            "Tipo": fuente["tipo"],
        })
    return pd.DataFrame(rows)


def render_tabla_html(df: pd.DataFrame) -> str:
    """Genera HTML de tabla con badges y enlaces clicables."""
    badge_map = {
        "ebird": "badge-ebird",
        "inaturalist": "badge-inaturalist",
        "twitter": "badge-twitter",
        "reddit": "badge-reddit",
        "facebook": "badge-facebook",
        "instagram": "badge-instagram",
        "flickr": "badge-flickr",
        "youtube": "badge-youtube",
        "github": "badge-github",
        "linkedin": "badge-linkedin",
        "google": "badge-google",
        "wayback": "badge-wayback",
        "default": "badge-default",
    }

    filas_html = ""
    for _, row in df.iterrows():
        badge_cls = badge_map.get(row["Tipo"], "badge-default")
        filas_html += f"""
        <tr>
          <td>
            <span class="badge {badge_cls}">{row['Categoría']}</span>
            <strong style="color:#c8d8e8">{row['Fuente']}</strong>
          </td>
          <td style="color:#8ecae6;font-size:0.82rem">{row['Descripción']}</td>
          <td>
            <a href="{row['URL Perfil / Búsqueda']}" target="_blank" class="result-link">
              🔗 Abrir →
            </a>
          </td>
          <td>
            <a href="{row['URL Directa']}" target="_blank" class="result-link" style="color:#4ade80">
              👤 Perfil →
            </a>
          </td>
        </tr>"""

    return f"""
    <style>
    table.osint-table {{
        width: 100%;
        border-collapse: collapse;
        font-family: 'Rajdhani', sans-serif;
        font-size: 0.9rem;
    }}
    table.osint-table th {{
        background: #0d1b2a;
        color: #00e5ff;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.75rem;
        letter-spacing: 0.08em;
        padding: 10px 12px;
        text-align: left;
        border-bottom: 2px solid #00e5ff44;
    }}
    table.osint-table td {{
        padding: 8px 12px;
        border-bottom: 1px solid #1a3a5c;
        vertical-align: middle;
    }}
    table.osint-table tr:hover td {{
        background: #0d2040;
    }}
    </style>
    <table class="osint-table">
      <thead>
        <tr>
          <th>FUENTE</th>
          <th>DESCRIPCIÓN</th>
          <th>BÚSQUEDA</th>
          <th>PERFIL DIRECTO</th>
        </tr>
      </thead>
      <tbody>
        {filas_html}
      </tbody>
    </table>
    """


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    # Header
    st.markdown("""
    <div style="border-bottom:1px solid #1a3a5c; padding-bottom:16px; margin-bottom:24px">
      <h1 style="margin:0; font-size:1.8rem; letter-spacing:0.05em">
        🔍 INVESTIGACIÓN
      </h1>
      <p style="color:#8ecae6; font-family:'Share Tech Mono',monospace; font-size:0.8rem; margin:4px 0 0">
        Rastreo de actividad pública · Redes sociales · Foros · Plataformas de naturaleza
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Aviso de uso responsable
    st.markdown("""
    <div class="info-box">
      ⚠️ <strong>USO RESPONSABLE:</strong> Esta herramienta genera únicamente enlaces a
      búsquedas <em>públicas</em> en plataformas de acceso abierto. No extrae datos privados
      ni vulnera sistemas. Destinada a investigación epidemiológica y periodismo de salud pública.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ─── Formulario de búsqueda ───────────────────────────────────────────────
    col_input, col_btn = st.columns([4, 1])

    with col_input:
        query = st.text_input(
            label="Dato de búsqueda",
            placeholder="Usuario, nombre completo, DNI, pasaporte, alias, email…",
            label_visibility="collapsed",
            key="osint_query"
        )
    with col_btn:
        buscar = st.button("🔎 INICIAR BÚSQUEDA", use_container_width=True)

    # Sugerencia rápida
    st.markdown("""
    <p style="color:#4a6a8a; font-family:'Share Tech Mono',monospace; font-size:0.72rem; margin-top:4px">
      Ejemplo: <code style="color:#166534; background:#d1fae5; padding:2px 6px; border-radius:3px">leo schilperoord</code> · 
               <code style="color:#166534; background:#d1fae5; padding:2px 6px; border-radius:3px">lschilperoord</code> · 
               <code style="color:#166534; background:#d1fae5; padding:2px 6px; border-radius:3px">DNI 12345678</code>
    </p>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ─── Ejecución ────────────────────────────────────────────────────────────
    if buscar and query.strip():
        query_clean = query.strip()

        with st.spinner("Construyendo mapa de búsqueda OSINT..."):
            # Simulamos progreso visual
            bar = st.progress(0)
            for i in range(0, 101, 10):
                time.sleep(0.04)
                bar.progress(i)
            bar.empty()

            df = generar_resultados(query_clean)

        # ─── Métricas ─────────────────────────────────────────────────────────
        cols = st.columns(4)
        total = len(df)
        categorias = df["Categoría"].nunique()
        fuentes_nat = len(df[df["Categoría"] == "Naturaleza"])
        fuentes_social = len(df[df["Categoría"] == "Red Social"])

        with cols[0]:
            st.metric("Total de Fuentes", f"{int(total):,}".replace(",", "."))
        with cols[1]:
            st.metric("Categorías", f"{int(categorias):,}".replace(",", "."))
        with cols[2]:
            st.metric("Naturaleza / Aves", f"{int(fuentes_nat):,}".replace(",", "."))
        with cols[3]:
            st.metric("Redes Sociales", f"{int(fuentes_social):,}".replace(",", "."))

        st.markdown(f"""
        <p style="color:#8ecae6; font-family:'Share Tech Mono',monospace; font-size:0.78rem; margin:8px 0 16px">
          › Búsqueda generada para: <strong style="color:#00e5ff">{query_clean}</strong>
        </p>
        """, unsafe_allow_html=True)

        # ─── Descarga CSV ──────────────────────────────────────────────────────
        df_export = df.drop(columns=["Tipo"])
        csv_bytes = df_export.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Descargar resultados CSV",
            data=csv_bytes,
            file_name=f"osint_{re.sub(r'[^a-z0-9]', '_', query_clean.lower())}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown("---")

        # ─── Tabla por categoría ──────────────────────────────────────────────
        categorias_orden = [
            "Naturaleza", "Red Social", "Fotos", "Video",
            "Búsqueda", "Foro", "Técnico", "Archivo", "OSINT", "Geo"
        ]

        for cat in categorias_orden:
            df_cat = df[df["Categoría"] == cat]
            if df_cat.empty:
                continue

            iconos = {
                "Naturaleza": "🌿", "Red Social": "💬", "Fotos": "📷",
                "Video": "🎬", "Búsqueda": "🔍", "Foro": "🗣️",
                "Técnico": "⚙️", "Archivo": "🗄️", "OSINT": "🕵️", "Geo": "🗺️"
            }
            icono = iconos.get(cat, "•")

            with st.expander(f"{icono} {cat.upper()}  —  {len(df_cat)} fuentes", expanded=(cat == "Naturaleza")):
                tabla_html = render_tabla_html(df_cat)
                height = min(60 + len(df_cat) * 50, 600)
                st.html(f'<div style="height:{height}px; overflow-y:auto; border:1px solid #1a3a5c; border-radius:6px;">{tabla_html}</div>')

        # ─── Mapa de rastreo geográfico (iNaturalist) ─────────────────────────
        with st.expander("🗺️ MAPA DE RASTREO GEOGRÁFICO (iNaturalist)", expanded=False):
            st.markdown("Consulta automática a la API de iNaturalist para obtener ubicaciones de observaciones.")
            variaciones = [query_clean.replace(' ', ''), query_clean.replace(' ', '_'), query_clean.replace(' ', '-')]
            if ' ' in query_clean:
                partes = query_clean.split()
                variaciones.append(partes[0][0] + partes[-1])
            todas = list(set([query_clean] + variaciones))
            obs_totales = []
            for var in todas:
                try:
                    url_api = f"https://api.inaturalist.org/v1/observations?user_login={quote_plus(var)}&per_page=200&order=desc&order_by=observed_on"
                    resp = requests.get(url_api, headers={'User-Agent': 'TableroEpidemiologico/1.0'}, timeout=10)
                    if resp.status_code == 200:
                        datos = resp.json()
                        for obs in datos.get('results', []):
                            if obs.get('geojson') and obs['geojson'].get('coordinates'):
                                lon, lat = obs['geojson']['coordinates']
                                obs_totales.append({
                                    'lat': lat, 'lon': lon,
                                    'Especie': obs.get('species_guess', 'Desconocido'),
                                    'Fecha': obs.get('observed_on', 'Sin fecha'),
                                    'Lugar': obs.get('place_guess', 'Sin lugar'),
                                    'Usuario': var
                                })
                except:
                    pass
            if obs_totales:
                df_geo = pd.DataFrame(obs_totales)
                st.success(f"Se encontraron {len(df_geo)} observaciones con coordenadas.")
                fig_map = px.scatter_map(
                    df_geo, lat='lat', lon='lon',
                    hover_name='Especie', hover_data=['Fecha', 'Lugar', 'Usuario'],
                    color_discrete_sequence=['#e11d48'], map_style='carto-positron',
                    zoom=2, height=500, title='Ubicaciones de observaciones'
                )
                fig_map.update_traces(marker=dict(size=10))
                fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, map={"center": {"lat": df_geo['lat'].mean(), "lon": df_geo['lon'].mean()}})
                st.plotly_chart(fig_map, width='stretch')
                st.dataframe(format_df_spanish(df_geo[['Fecha', 'Lugar', 'Especie', 'Usuario']].sort_values('Fecha', ascending=False)), width='stretch', hide_index=True)
            else:
                st.info("No se encontraron observaciones geolocalizadas en iNaturalist para las variaciones del nombre buscado.")

        # ─── Tabla completa (colapsada) ───────────────────────────────────────
        with st.expander("📋 Ver tabla completa (todas las fuentes)"):
            tabla_completa = render_tabla_html(df)
            height_full = min(60 + len(df) * 50, 800)
            st.html(f'<div style="height:{height_full}px; overflow-y:auto; border:1px solid #1a3a5c; border-radius:6px;">{tabla_completa}</div>')

    elif buscar and not query.strip():
        st.warning("⚠️ Ingresá un dato de búsqueda antes de continuar.")

    # ─── Panel de ayuda ───────────────────────────────────────────────────────
    with st.expander("ℹ️ Guía de uso y técnicas"):
        st.markdown("""
        ### Estrategia de búsqueda recomendada

        **Paso 1 — Nombre de usuario**
        Buscá el alias exacto (ej. `lschilperoord`, `leo_schilperoord`).
        Comenzá por las fuentes de **Naturaleza** (eBird, iNaturalist) que registran geolocalización precisa.

        **Paso 2 — Nombre completo**
        Buscá `Nombre Apellido` entre comillas para resultados exactos.
        Google te mostrará foros, notas de prensa, comentarios.

        **Paso 3 — Combinaciones**
        `"nombre" argentina`, `"nombre" birding`, `"nombre" hantavirus`.

        **Paso 4 — Identificadores**
        Si tenés DNI, pasaporte o email, usalos para cruzar registros.

        **Paso 5 — Wayback Machine**
        Permite ver páginas o perfiles ya eliminados.

        ---
        ### eBird — clave para rastreo geográfico
        Los checklists de eBird contienen **fecha, hora y coordenadas GPS** exactas de cada observación.
        La URL `ebird.org/checklist/search?userId=USUARIO` lista todas las salidas del birder.
        Cada checklist tiene un mapa con la ubicación precisa.

        ---
        ### iNaturalist
        Cada observación incluye fecha, lugar y coordenadas. El mapa de usuario muestra
        todos los sitios visitados en un solo vistazo.
        """)


if __name__ == "__main__":
    main()