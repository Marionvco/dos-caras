"""
Dos Caras — prototipo
Noticias vistas desde todos los lados, para salir de la burbuja del algoritmo.

Cómo funciona:
1. Lee titulares recientes de medios chilenos de distinta tendencia (vía Google News RSS).
2. La IA (Gemini gratis, o Claude) agrupa los titulares que hablan del mismo hecho.
3. Para cada hecho muestra: cómo lo cuenta cada lado, lo que coinciden (la intersección),
   la mirada de otros países involucrados, y podcasts y videos sobre el tema.
   dónde difieren y qué afirmaciones tienen respaldo de varios lados.
"""

import datetime
import html
import json
import urllib.parse
import urllib.request

import feedparser
import streamlit as st

from fuentes import ACTORES, AGENCIAS, CONFLICTOS, MEDIOS, MEDIOS_INTERNACIONALES, PAISES

# Modelos gratuitos de Gemini, en orden de preferencia (si uno está saturado, prueba el siguiente)
MODELOS_GEMINI = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
MODELO_CLAUDE = "claude-sonnet-5-5"  # opción pagada
AGENTE = "Mozilla/5.0 (compatible; DosCaras/0.1)"
ORDEN = ["izquierda", "centro", "derecha"]
ETIQUETAS = {"izquierda": "⬅️ Izquierda", "centro": "⏺️ Centro", "derecha": "➡️ Derecha"}
TRES_HORAS = 3 * 60 * 60

st.set_page_config(page_title="Dos Caras", page_icon="⚖️", layout="wide")


# ---------------------------------------------------------------- utilidades
def seguro(texto):
    """Evita que símbolos de los titulares ($, [, ]) rompan el formato."""
    return str(texto).replace("$", "\\$").replace("[", "(").replace("]", ")")


def url_google_news(consulta, pais="CL", hl="es-419", ceid="CL:es-419"):
    params = {"q": consulta, "hl": hl, "gl": pais, "ceid": ceid}
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)


def leer_json_web(url):
    try:
        pedido = urllib.request.Request(url, headers={"User-Agent": AGENTE})
        with urllib.request.urlopen(pedido, timeout=15) as r:
            return json.load(r)
    except Exception:
        return {}


def rango_fechas(periodo):
    """periodo: número de días hacia atrás, o (desde, hasta) como textos 'AAAA-MM-DD'.
    Devuelve (desde, hasta) como fechas; 'hasta' es el día siguiente al último incluido."""
    hoy = datetime.date.today()
    if isinstance(periodo, (tuple, list)):
        return datetime.date.fromisoformat(periodo[0]), datetime.date.fromisoformat(periodo[1])
    return hoy - datetime.timedelta(days=int(periodo)), hoy + datetime.timedelta(days=1)


def filtro_fecha(periodo):
    """Filtro de fechas para Google News: reciente con 'when:', antiguo con 'after:'/'before:'."""
    if not isinstance(periodo, (tuple, list)) and int(periodo) <= 30:
        return f"when:{int(periodo)}d"
    desde, hasta = rango_fechas(periodo)
    return f"after:{desde.isoformat()} before:{hasta.isoformat()}"


def texto_periodo(periodo):
    if isinstance(periodo, (tuple, list)):
        desde, hasta = rango_fechas(periodo)
        ultimo = hasta - datetime.timedelta(days=1)
        return f"del {desde.strftime('%d-%m-%Y')} al {ultimo.strftime('%d-%m-%Y')}"
    return f"de los últimos {int(periodo)} días"


def limpiar_titulo(titulo):
    # Google News agrega " - Nombre del medio" al final del titular
    return titulo.rsplit(" - ", 1)[0].strip() if " - " in titulo else titulo.strip()


def extraer_json(texto):
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fin == -1:
        raise ValueError("La IA no devolvió un resultado legible. Intenta de nuevo.")
    return json.loads(texto[inicio : fin + 1])


def lista_para_prompt(noticias):
    return "\n".join(
        f"{n['id']} | {n['tendencia']} | {n['medio']} | {n['titulo']}" for n in noticias
    )


# ------------------------------------------------------- 1. traer titulares
@st.cache_data(ttl=TRES_HORAS, show_spinner=False)
def traer_titulares(texto_busqueda, dias, max_por_medio):
    noticias, vistos = [], set()
    for medio in MEDIOS:
        consulta = f"{texto_busqueda} site:{medio['dominio']} {filtro_fecha(dias)}".strip()
        feed = feedparser.parse(url_google_news(consulta), agent=AGENTE)
        for entrada in feed.entries[:max_por_medio]:
            titulo = limpiar_titulo(entrada.get("title", ""))
            if not titulo or titulo in vistos:
                continue
            vistos.add(titulo)
            noticias.append(
                {
                    "id": len(noticias),
                    "medio": medio["nombre"],
                    "tendencia": medio["tendencia"],
                    "titulo": titulo,
                    "link": entrada.get("link", ""),
                }
            )
    return noticias


@st.cache_data(ttl=TRES_HORAS, show_spinner=False)
def traer_de_pais(busqueda, codigo, dias=7, n=6):
    """Titulares del Google News de otro país, en su idioma."""
    pais = PAISES[codigo]
    url = url_google_news(f"{busqueda} {filtro_fecha(dias)}", codigo, pais["hl"], pais["ceid"])
    feed = feedparser.parse(url, agent=AGENTE)
    salida = []
    idioma = idioma_de(pais["hl"])
    return [entrada_a_noticia(e, idioma=idioma) for e in feed.entries[:n]]


@st.cache_data(ttl=TRES_HORAS, show_spinner=False)
def traer_internacionales(busqueda, dias=7, n=2):
    """Titulares de medios internacionales en español."""
    salida = []
    for medio in MEDIOS_INTERNACIONALES:
        consulta = f"{busqueda} site:{medio['dominio']} {filtro_fecha(dias)}"
        feed = feedparser.parse(url_google_news(consulta), agent=AGENTE)
        for entrada in feed.entries[:n]:
            salida.append(
                {
                    "medio": medio["nombre"],
                    "titulo": limpiar_titulo(entrada.get("title", "")),
                    "link": entrada.get("link", ""),
                }
            )
    return salida


def entrada_a_noticia(entrada, medio=None, idioma=None):
    """idioma: None si está en español; si no, el nombre del idioma (para traducirlo)."""
    fuente = entrada.get("source", {}) or {}
    return {
        "medio": medio or fuente.get("title", "") or "Google News",
        "titulo": limpiar_titulo(entrada.get("title", "")),
        "link": entrada.get("link", ""),
        "idioma": idioma,
    }


def idioma_de(hl):
    nombres = {"en": "inglés", "pt": "portugués", "fr": "francés", "de": "alemán", "zh": "chino", "ru": "ruso"}
    return nombres.get(hl.split("-")[0])


def numerar_para_traducir(grupos):
    """Pone un número a cada titular que no está en español, para pedir su traducción."""
    k = 1
    for g in grupos:
        for noticia in g["noticias"]:
            if noticia.get("idioma"):
                noticia["n"] = k
                k += 1
    return grupos


@st.cache_data(ttl=TRES_HORAS, show_spinner=False)
def traer_actor(codigo, busqueda_en, dias, n=6):
    """Titulares de un actor de un conflicto: su Google News, o sus medios propios."""
    if codigo in ACTORES:
        actor = ACTORES[codigo]
    else:  # un país de la lista PAISES: se busca en su Google News
        p = PAISES[codigo]
        actor = {"nombre": p["nombre"], "edicion": (p["hl"], p["ceid"], codigo)}
    salida = []
    if "edicion" in actor:
        hl, ceid, gl = actor["edicion"]
        feed = feedparser.parse(url_google_news(f"{busqueda_en} {filtro_fecha(dias)}", gl, hl, ceid), agent=AGENTE)
        salida += [entrada_a_noticia(e, idioma=idioma_de(hl)) for e in feed.entries[:n]]
    for nombre, dominio in actor.get("sitios", []):
        consulta = f"{busqueda_en} site:{dominio} {filtro_fecha(dias)}"
        feed = feedparser.parse(url_google_news(consulta, "US", "en-US", "US:en"), agent=AGENTE)
        salida += [entrada_a_noticia(e, nombre, "inglés") for e in feed.entries[:3]]
    return salida


@st.cache_data(ttl=TRES_HORAS, show_spinner=False)
def traer_agencias(busqueda_en, dias, n=2):
    salida = []
    for nombre, dominio in AGENCIAS:
        consulta = f"{busqueda_en} site:{dominio} {filtro_fecha(dias)}"
        feed = feedparser.parse(url_google_news(consulta, "US", "en-US", "US:en"), agent=AGENTE)
        salida += [entrada_a_noticia(e, nombre, "inglés") for e in feed.entries[:n]]
    return salida


@st.cache_data(ttl=TRES_HORAS, show_spinner=False)
def traer_impacto_chile(busqueda_es, dias, n=8):
    """Titulares chilenos que conectan el conflicto con Chile."""
    feed = feedparser.parse(url_google_news(f"{busqueda_es} Chile {filtro_fecha(dias)}"), agent=AGENTE)
    return [entrada_a_noticia(e) for e in feed.entries[:n]]


@st.cache_data(ttl=TRES_HORAS, show_spinner=False)
def buscar_podcasts(busqueda, n=5, pais="CL"):
    """Episodios de podcast sobre el tema (catálogo de Apple Podcasts, gratis y sin clave)."""
    params = {
        "term": busqueda,
        "media": "podcast",
        "entity": "podcastEpisode",
        "country": pais,
        "limit": 15,
    }
    datos = leer_json_web("https://itunes.apple.com/search?" + urllib.parse.urlencode(params))
    episodios = [
        {
            "titulo": x.get("trackName", ""),
            "programa": x.get("collectionName", ""),
            "link": x.get("trackViewUrl", ""),
            "fecha": (x.get("releaseDate") or "")[:10],
        }
        for x in datos.get("results", [])
        if x.get("trackName")
    ]
    episodios.sort(key=lambda e: e["fecha"], reverse=True)  # los más recientes primero
    return episodios[:n]


@st.cache_data(ttl=TRES_HORAS, show_spinner=False)
def buscar_videos(busqueda, n=4, idioma="es", region="CL", periodo=7):
    """Videos de YouTube sobre el tema. Solo funciona si hay YOUTUBE_API_KEY en los Secrets."""
    clave = secreto("YOUTUBE_API_KEY")
    if not clave:
        return None
    desde_d, hasta_d = rango_fechas(periodo)
    params = {
        "part": "snippet",
        "q": busqueda,
        "type": "video",
        "maxResults": n,
        "order": "relevance",
        "relevanceLanguage": idioma,
        "regionCode": region,
        "publishedAfter": f"{desde_d.isoformat()}T00:00:00Z",
        "publishedBefore": f"{hasta_d.isoformat()}T00:00:00Z",
        "key": clave,
    }
    datos = leer_json_web("https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode(params))
    return [
        {
            "titulo": html.unescape(v["snippet"]["title"]),
            "canal": v["snippet"]["channelTitle"],
            "url": f"https://www.youtube.com/watch?v={v['id']['videoId']}",
        }
        for v in datos.get("items", [])
        if v.get("id", {}).get("videoId")
    ]


# ------------------------------------------------------------ 2. la IA
def secreto(nombre, por_defecto=None):
    try:
        return st.secrets[nombre]
    except Exception:
        return por_defecto


def llamar_ia(prompt, max_tokens=3000):
    """Usa Gemini (capa gratuita) si hay GEMINI_API_KEY; si no, Claude con ANTHROPIC_API_KEY."""
    clave_gemini = secreto("GEMINI_API_KEY")
    clave_claude = secreto("ANTHROPIC_API_KEY")

    if clave_gemini:
        import time

        from google import genai

        # El cliente se guarda en una variable: si no, se cierra antes de enviar la pregunta.
        cliente = genai.Client(api_key=clave_gemini)
        preferido = secreto("GEMINI_MODEL")
        modelos = ([preferido] if preferido else []) + MODELOS_GEMINI
        ultimo_error = None
        for modelo in modelos:
            for intento in range(2):  # si está saturado: espera y reintenta, luego prueba otro modelo
                try:
                    respuesta = cliente.models.generate_content(
                        model=modelo,
                        contents=prompt,
                        # margen extra: los modelos nuevos de Gemini "piensan" antes de responder
                        config={
                            "response_mime_type": "application/json",
                            "max_output_tokens": max_tokens * 3,
                        },
                    )
                    return extraer_json(respuesta.text or "")
                except Exception as e:
                    ultimo_error = e
                    texto_error = str(e)
                    saturado = any(c in texto_error for c in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "overloaded"))
                    no_existe = "404" in texto_error or "NOT_FOUND" in texto_error
                    if no_existe:
                        break  # este modelo no está disponible: pasar al siguiente
                    if not saturado:
                        raise
                    time.sleep(3 * (intento + 1))
        raise RuntimeError(
            "Los modelos gratuitos de Gemini están saturados en este momento. "
            f"Prueba de nuevo en unos minutos. (Detalle: {ultimo_error})"
        )

    if clave_claude:
        from anthropic import Anthropic

        respuesta = Anthropic(api_key=clave_claude).messages.create(
            model=secreto("CLAUDE_MODEL", MODELO_CLAUDE),
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        texto = "".join(b.text for b in respuesta.content if getattr(b, "type", "") == "text")
        return extraer_json(texto)

    raise RuntimeError("Falta la clave de la IA (GEMINI_API_KEY) en los Secrets de la app.")


@st.cache_data(ttl=TRES_HORAS, show_spinner=False)
def palabras_clave(texto):
    """Si el usuario pega un titular largo, lo convierte en una búsqueda corta."""
    if len(texto.split()) <= 5:
        return texto
    prompt = f"""Convierte este titular o texto de noticia en una búsqueda corta (3 a 6 palabras clave,
sin adjetivos ni palabras cargadas) que sirva para encontrar la misma noticia en otros medios.
Responde SOLO con JSON: {{"busqueda": "..."}}

TEXTO: {texto}"""
    return llamar_ia(prompt, 200).get("busqueda", texto)


@st.cache_data(ttl=TRES_HORAS, show_spinner=False)
def agrupar_temas(noticias, n_temas):
    prompt = f"""Eres un editor de noticias neutral. Abajo hay titulares de medios chilenos
(formato: id | tendencia del medio | medio | titular).

Identifica hasta {n_temas} HECHOS o TEMAS concretos que hayan sido cubiertos por medios de al menos
DOS tendencias distintas. Prioriza temas de interés público (política, economía, sociedad, seguridad,
salud, educación). Ignora deportes, farándula, horóscopo y avisos. Cada titular va en un solo tema.

Responde SOLO con JSON con esta forma:
{{"temas": [{{"tema": "nombre corto y neutral del tema", "ids": [1, 5, 9]}}]}}

TITULARES:
{lista_para_prompt(noticias)}"""
    return llamar_ia(prompt, 3000).get("temas", [])


@st.cache_data(ttl=TRES_HORAS, show_spinner=False)
def analizar_tema(tema, noticias):
    prompt = f"""Eres un analista de medios riguroso y neutral. Tema: "{tema}".
Estos son titulares sobre el tema, de medios con distinta tendencia
(formato: id | tendencia del medio | medio | titular):

{lista_para_prompt(noticias)}

Reglas:
- Analiza SOLO con lo que dicen estos titulares. No inventes hechos ni completes con suposiciones.
- Si una tendencia no tiene titulares, dilo: que un lado no cubra un tema también es información.
- No juzgues qué lado tiene razón. Muestra qué está respaldado por varios lados y qué no.
- Usa lenguaje simple y sin adjetivos cargados.

Responde SOLO con JSON con esta forma:
{{
  "resumen_neutral": "2 o 3 frases con lo que se sabe",
  "enfoques": {{
    "izquierda": "cómo lo presentan estos medios, o 'Sin cobertura en los medios revisados'",
    "centro": "...",
    "derecha": "..."
  }},
  "en_comun": ["hechos que aparecen en medios de distintas tendencias"],
  "diferencias": ["diferencias de énfasis, lenguaje o lo que cada lado omite"],
  "afirmaciones": [
    {{"afirmacion": "...",
      "respaldo": "Coinciden varias tendencias | Solo una tendencia lo afirma | Requiere verificación",
      "comentario": "por qué"}}
  ],
  "preguntas_abiertas": ["qué falta saber para formarse una opinión propia"],
  "busqueda": "3 a 6 palabras clave en español para buscar este mismo tema en otros medios",
  "paises": [
    {{"codigo": "código de 2 letras", "busqueda": "3 a 6 palabras clave en el idioma de ese país"}}
  ]
}}

En "paises" pon SOLO los países distintos de Chile que estén directamente involucrados en el tema
(por ejemplo, un conflicto o acuerdo con ese país, o declaraciones de su gobierno o embajador).
Usa solo estos códigos: {", ".join(f"{c} ({p['nombre']})" for c, p in PAISES.items())}.
Si el tema es solo nacional, deja "paises" como lista vacía []."""
    return llamar_ia(prompt, 3000)


def lista_simple(noticias):
    """Los titulares en otro idioma llevan su número [n], para pedir la traducción."""
    return "\n".join(
        (f"[{x['n']}] " if x.get("n") else "- ") + f"{x['medio']} | {x['titulo']}" for x in noticias
    )


INSTRUCCION_TRADUCIR = """
Además, en "traducciones" traduce al español CADA titular marcado con [número], de forma fiel
(sin agregar ni quitar sentido, ni suavizar el tono). La clave es el número como texto."""


@st.cache_data(ttl=TRES_HORAS, show_spinner=False)
def comparar_paises(tema, noticias_chile, grupos):
    bloques = "\n\n".join(f"TITULARES DE {g['nombre'].upper()}:\n{lista_simple(g['noticias'])}" for g in grupos)
    nombres = ["Chile"] + [g["nombre"] for g in grupos]
    prompt = f"""Eres un analista de medios internacional, riguroso y neutral. Tema: "{tema}".
Compara cómo cuentan este tema los medios de distintos países. Algunos titulares pueden estar en
otro idioma: analízalos igual, pero responde todo en español.

TITULARES DE CHILE:
{lista_simple(noticias_chile)}

{bloques}

Reglas:
- Usa SOLO lo que dicen estos titulares. No inventes hechos.
- No juzgues qué país tiene razón. Muestra qué coincide y qué no.
- Si los titulares de un país hablan de otra cosa, dilo.

Responde SOLO con JSON con esta forma:
{{
  "miradas": {{{", ".join(f'"{n}": "cómo lo presentan sus medios"' for n in nombres)}}},
  "en_comun": ["hechos que reportan medios de distintos países"],
  "diferencias": ["diferencias de enfoque entre países: qué destaca u omite cada uno"],
  "traducciones": {{"1": "titular 1 traducido al español"}}
}}
{INSTRUCCION_TRADUCIR}"""
    return llamar_ia(prompt, 3500)


def todos_los_actores():
    return list(ACTORES) + [c for c in PAISES if c not in ACTORES]


def nombre_actor(codigo):
    return ACTORES[codigo]["nombre"] if codigo in ACTORES else PAISES[codigo]["nombre"]


@st.cache_data(ttl=TRES_HORAS, show_spinner=False)
def definir_conflicto(texto):
    """Convierte lo que escribe el usuario en un conflicto con sus lados y palabras de búsqueda."""
    codigos = ", ".join(f"{c} ({nombre_actor(c)})" for c in todos_los_actores())
    prompt = f"""El usuario quiere entender este conflicto o tema internacional: "{texto}".
Identifica los actores principales (1 a 3 países o bloques) usando SOLO estos códigos: {codigos}.
Si el tema involucra a Chile, NO incluyas a Chile como actor (Chile ya se revisa aparte).
Responde SOLO con JSON:
{{"nombre": "nombre corto y neutral del conflicto",
  "actores": ["US", "CN"],
  "busqueda_en": "3 a 5 palabras clave en inglés",
  "busqueda_es": "3 a 5 palabras clave en español"}}"""
    datos = llamar_ia(prompt, 400)
    datos["actores"] = [a for a in datos.get("actores", []) if a in todos_los_actores()][:3]
    return datos


@st.cache_data(ttl=TRES_HORAS, show_spinner=False)
def analizar_geopolitica(nombre, grupos):
    bloques = "\n\n".join(
        f"TITULARES DE {g['nombre'].upper()}" + (f" ({g['nota']})" if g.get("nota") else "")
        + f":\n{lista_simple(g['noticias'])}"
        for g in grupos
    )
    lados = [g["nombre"] for g in grupos if g["tipo"] == "actor"]
    prompt = f"""Eres un analista internacional riguroso y neutral, que explica a lectores chilenos.
Tema: "{nombre}". Abajo hay titulares de los medios de cada lado, de agencias internacionales y
de medios chilenos. Muchos están en inglés: analízalos igual, pero responde todo en español.

{bloques}

Reglas:
- Usa SOLO lo que dicen estos titulares. No inventes hechos, cifras ni declaraciones.
- No tomes partido. Los medios estatales muestran la postura oficial de su gobierno: preséntala como tal.
- Para el impacto en Chile, separa lo que dicen los titulares de lo que es solo una posibilidad.

Responde SOLO con JSON con esta forma:
{{
  "resumen_neutral": "2 o 3 frases con lo que se sabe",
  "miradas": {{{", ".join(f'"{n}": "cómo presenta el tema este lado"' for n in lados)}, "Agencias internacionales": "..."}},
  "en_comun": ["hechos que reportan medios de distintos lados"],
  "diferencias": ["en qué difieren los relatos: culpas, causas, lo que cada uno omite"],
  "impacto_chile": [
    {{"canal": "por ejemplo: precio del cobre, combustibles, dólar, exportaciones",
      "efecto": "cómo podría afectar a Chile, en lenguaje simple",
      "respaldo": "Lo dicen los titulares | Posible, requiere verificación"}}
  ],
  "preguntas_abiertas": ["qué falta saber"],
  "traducciones": {{"1": "titular 1 traducido al español"}}
}}
{INSTRUCCION_TRADUCIR}"""
    return llamar_ia(prompt, 5000)


# ---------------------------------------------------------- 3. mostrar
def lista_puntos(titulo, items):
    st.markdown(f"**{titulo}**")
    if not items:
        st.markdown("_Nada que destacar._")
    for x in items:
        st.markdown(f"- {seguro(x)}")


def lista_titulares(noticias, traducciones=None):
    """Titulares con link. Si están en otro idioma: el titular en español y, debajo, el original."""
    traducciones = traducciones or {}
    for x in noticias:
        traducido = traducciones.get(str(x.get("n"))) if x.get("n") else None
        if traducido:
            st.markdown(
                f"- [{seguro(traducido)}]({x['link']}) — *{seguro(x['medio'])}*  \n"
                f"  <small>Original en {x['idioma']}: “{seguro(x['titulo'])}”</small>",
                unsafe_allow_html=True,
            )
        else:
            aviso = f" · <small>en {x['idioma']}</small>" if x.get("idioma") else ""
            st.markdown(
                f"- [{seguro(x['titulo'])}]({x['link']}) — *{seguro(x['medio'])}*{aviso}",
                unsafe_allow_html=True,
            )


def mostrar_extras(tema, noticias, analisis, clave_ui, periodo=7):
    """Otros países, podcasts y videos. Solo se calcula si el usuario lo pide (ahorra la IA gratis)."""
    busqueda = analisis.get("busqueda") or tema
    paises = [p for p in analisis.get("paises", []) or [] if p.get("codigo") in PAISES]
    nombres_paises = ", ".join(PAISES[p["codigo"]]["nombre"] for p in paises)
    etiqueta = "🌎 Otros países, 🎧 podcasts y 🎥 videos"
    if nombres_paises:
        etiqueta += f" — involucra a {nombres_paises}"
    if not st.toggle(etiqueta, key=f"extras_{clave_ui}"):
        return

    # --- La mirada desde otros países
    with st.spinner("Buscando cómo lo cuentan en otros países..."):
        grupos = []
        for p in paises:
            encontradas = traer_de_pais(p.get("busqueda") or busqueda, p["codigo"], periodo)
            if encontradas:
                grupos.append({"nombre": PAISES[p["codigo"]]["nombre"], "noticias": encontradas})
        internacionales = traer_internacionales(busqueda, periodo)
        if internacionales:
            grupos.append({"nombre": "Medios internacionales", "noticias": internacionales})
        numerar_para_traducir(grupos)

    st.markdown("### 🌎 La mirada desde otros países")
    if not paises:
        st.caption("Es un tema nacional: se muestra cómo lo cubren medios internacionales.")
    if not grupos:
        st.caption(f"No encontré cobertura de otros países sobre este tema {texto_periodo(periodo)}.")
    else:
        try:
            with st.spinner("La IA está comparando las miradas de cada país..."):
                comparacion = comparar_paises(tema, noticias, grupos)
        except Exception as e:
            comparacion = {}
            st.warning(f"No pude comparar las miradas: {e}")
        miradas = comparacion.get("miradas", {})
        columnas = st.columns(len(grupos) + 1)
        with columnas[0]:
            st.markdown("#### Chile")
            st.caption(seguro(miradas.get("Chile", "")))
            st.caption("Titulares chilenos: arriba, en las tres columnas.")
        for col, g in zip(columnas[1:], grupos):
            with col:
                st.markdown(f"#### {g['nombre']}")
                st.caption(seguro(miradas.get(g["nombre"], "")))
                lista_titulares(g["noticias"], comparacion.get("traducciones"))
        if comparacion:
            c1, c2 = st.columns(2)
            with c1:
                lista_puntos("🤝 Lo que coinciden entre países", comparacion.get("en_comun", []))
            with c2:
                lista_puntos("↔️ Dónde difieren los países", comparacion.get("diferencias", []))

    # --- Podcasts y videos
    st.markdown("### 🎧 Podcasts y 🎥 videos sobre el tema")
    st.caption("Encontrados automáticamente: no están verificados ni clasificados por tendencia.")
    bloque_multimedia(busqueda, periodo=periodo)


def bloque_multimedia(busqueda, pais="CL", idioma="es", region="CL", periodo=7):
    """Podcasts y videos sobre una búsqueda, en un idioma."""
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🎧 Episodios de podcast**")
        with st.spinner("Buscando podcasts..."):
            episodios = buscar_podcasts(busqueda, pais=pais)
        if not episodios:
            st.markdown("_No encontré episodios sobre este tema._")
        for e in episodios:
            st.markdown(f"- [{seguro(e['titulo'])}]({e['link']}) — *{seguro(e['programa'])}*, {e['fecha']}")
        st.link_button(
            "Buscar en Spotify",
            "https://open.spotify.com/search/" + urllib.parse.quote(busqueda) + "/episodes",
        )
    with c2:
        st.markdown("**🎥 Videos**")
        videos = buscar_videos(busqueda, idioma=idioma, region=region, periodo=periodo)
        if videos:
            for v in videos:
                st.video(v["url"])
                st.caption(f"{seguro(v['titulo'])} — {seguro(v['canal'])}")
        elif videos is not None:
            st.markdown("_No encontré videos recientes sobre este tema._")
        st.link_button(
            "Buscar en YouTube",
            "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": busqueda}),
        )


def mostrar_geopolitica(nombre, grupos, analisis):
    st.subheader(seguro(nombre))
    st.write(seguro(analisis.get("resumen_neutral", "")))

    miradas = analisis.get("miradas", {})
    lados = [g for g in grupos if g["tipo"] != "chile"]
    for col, g in zip(st.columns(len(lados)), lados):
        with col:
            st.markdown(f"#### {g['nombre']}")
            if g.get("nota"):
                st.info(g["nota"])
            st.caption(seguro(miradas.get(g["nombre"], "")))
            if g["noticias"]:
                lista_titulares(g["noticias"], analisis.get("traducciones"))
            else:
                st.markdown("_Sin titulares en los últimos días._")

    c1, c2 = st.columns(2)
    with c1:
        lista_puntos("🤝 Lo que coinciden los distintos lados", analisis.get("en_comun", []))
    with c2:
        lista_puntos("↔️ Dónde difieren los relatos", analisis.get("diferencias", []))

    st.markdown("### 📈 ¿Cómo podría afectar a Chile?")
    impacto = analisis.get("impacto_chile", [])
    if impacto:
        st.dataframe(
            [
                {
                    "Canal": i.get("canal", ""),
                    "Posible efecto": i.get("efecto", ""),
                    "Respaldo": i.get("respaldo", ""),
                }
                for i in impacto
            ],
            hide_index=True,
        )
    chile = next((g for g in grupos if g["tipo"] == "chile"), None)
    if chile and chile["noticias"]:
        with st.expander("Titulares chilenos sobre el impacto en Chile"):
            lista_titulares(chile["noticias"])

    lista_puntos("❓ Preguntas abiertas", analisis.get("preguntas_abiertas", []))


def mostrar_multimedia_geo(conflicto, clave_ui, periodo=7):
    """Podcasts y videos del conflicto, en español y en inglés. Se carga solo si el usuario lo pide."""
    if not st.toggle("🎧 Podcasts y 🎥 videos sobre este conflicto", key=f"multi_{clave_ui}"):
        return
    st.caption(
        "Encontrados automáticamente: no están verificados ni clasificados por lado. "
        "Revisa quién los produce antes de darlos por ciertos."
    )
    pestana_es, pestana_en = st.tabs(["En español", "En inglés"])
    with pestana_es:
        bloque_multimedia(conflicto["busqueda_es"], pais="CL", idioma="es", region="CL", periodo=periodo)
    with pestana_en:
        bloque_multimedia(conflicto["busqueda_en"], pais="US", idioma="en", region="US", periodo=periodo)


def mostrar_analisis(tema, noticias, analisis, clave_ui="0", periodo=7):
    st.subheader(seguro(tema))
    st.write(seguro(analisis.get("resumen_neutral", "")))

    enfoques = analisis.get("enfoques", {})
    for col, tendencia in zip(st.columns(3), ORDEN):
        with col:
            st.markdown(f"#### {ETIQUETAS[tendencia]}")
            st.caption(seguro(enfoques.get(tendencia, "")))
            propias = [n for n in noticias if n["tendencia"] == tendencia]
            if not propias:
                st.markdown("_Sin titulares en los medios revisados._")
            for n in propias:
                st.markdown(f"- [{seguro(n['titulo'])}]({n['link']}) — *{n['medio']}*")

    c1, c2 = st.columns(2)
    with c1:
        lista_puntos("🤝 Lo que coinciden (la intersección)", analisis.get("en_comun", []))
    with c2:
        lista_puntos("↔️ Dónde difieren", analisis.get("diferencias", []))

    afirmaciones = analisis.get("afirmaciones", [])
    if afirmaciones:
        st.markdown("**🔎 Afirmaciones y su respaldo**")
        st.dataframe(
            [
                {
                    "Afirmación": a.get("afirmacion", ""),
                    "Respaldo": a.get("respaldo", ""),
                    "Comentario": a.get("comentario", ""),
                }
                for a in afirmaciones
            ],
            hide_index=True,
        )

    lista_puntos("❓ Preguntas abiertas", analisis.get("preguntas_abiertas", []))
    mostrar_extras(tema, noticias, analisis, clave_ui, periodo)
    st.divider()


# ------------------------------------------------------------ pantalla
st.title("⚖️ Dos Caras")
st.markdown("#### Las noticias completas, no solo la mitad que el algoritmo elige para ti.")

with st.container(border=True):
    st.markdown(
        "Las redes sociales y los buscadores aprenden lo que te gusta y te muestran más de lo mismo. "
        "Sin darte cuenta, terminas viendo **una sola cara de la moneda**.\n\n"
        "**Dos Caras rompe esa burbuja.** Reunimos lo que publican medios de distintas tendencias y "
        "países sobre un mismo hecho, y con inteligencia artificial te mostramos **en qué coinciden, "
        "dónde difieren y qué está realmente respaldado**."
    )
    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown(
            "**🧭 Todas las miradas**  \nIzquierda, centro y derecha. Chile y el mundo. "
            "Lado a lado, en una sola pantalla."
        )
    with p2:
        st.markdown(
            "**🤝 Los hechos en común**  \nLa intersección de lo que todos reportan, "
            "separada de la opinión y del énfasis de cada medio."
        )
    with p3:
        st.markdown(
            "**🔎 Tú decides**  \nFuentes originales a un clic, más podcasts y videos, "
            "para que formes tu propia opinión."
        )
    st.markdown("**No te decimos qué pensar. Te mostramos el panorama completo.**")

with st.sidebar:
    st.header("Ajustes")
    dias = st.slider("Noticias de los últimos días", 1, 7, 1)
    max_por_medio = st.slider("Titulares por medio", 5, 20, 10)
    n_temas = st.slider("Temas a analizar", 2, 8, 4)
    if st.button("🔄 Traer noticias nuevas"):
        st.cache_data.clear()
    with st.expander("Medios revisados y su tendencia"):
        for m in MEDIOS:
            st.write(f"{ETIQUETAS[m['tendencia']]} — {m['nombre']}")
        st.caption("Clasificación inicial, editable en fuentes.py.")

def ejecutar_geo(conflicto, dias_g, clave_ui, min_actores=2):
    """Trae las noticias de cada lado, las analiza y muestra todo (también podcasts y videos)."""
    if len(conflicto.get("actores", [])) < min_actores:
        st.warning(
            "No pude identificar los lados con los países disponibles. "
            "Prueba describiéndolo de otra forma (o agrega el país en fuentes.py)."
        )
        return
    with st.spinner("Leyendo los medios de cada lado..."):
        grupos = []
        for codigo in conflicto.get("actores", []):
            actor = ACTORES.get(codigo, {})
            grupos.append(
                {
                    "nombre": nombre_actor(codigo),
                    "nota": actor.get("nota", ""),
                    "tipo": "actor",
                    "noticias": traer_actor(codigo, conflicto["busqueda_en"], dias_g),
                }
            )
        grupos.append(
            {
                "nombre": "Agencias internacionales",
                "nota": "",
                "tipo": "agencias",
                "noticias": traer_agencias(conflicto["busqueda_en"], dias_g),
            }
        )
        grupos.append(
            {
                "nombre": "Medios chilenos",
                "nota": "",
                "tipo": "chile",
                "noticias": traer_impacto_chile(conflicto["busqueda_es"], dias_g),
            }
        )
    numerar_para_traducir(grupos)
    total = sum(len(g["noticias"]) for g in grupos)
    st.caption(f"{total} titulares encontrados.")
    if total == 0:
        st.warning("No encontré noticias recientes sobre este tema.")
        return
    with st.spinner("La IA está comparando los relatos de cada lado..."):
        analisis_geo = analizar_geopolitica(conflicto["nombre"], grupos)
    mostrar_geopolitica(conflicto["nombre"], grupos, analisis_geo)
    mostrar_multimedia_geo(conflicto, clave_ui, dias_g)


def buscar_en_chile(texto, rango_busqueda):
    with st.spinner("Buscando en los medios chilenos..."):
        clave = palabras_clave(texto)
        noticias = traer_titulares(clave, rango_busqueda, 5)
    st.caption(f"Búsqueda usada: {clave}")
    if not noticias:
        st.warning("No encontré esta noticia en los medios chilenos revisados. Prueba con menos palabras.")
        return
    with st.spinner("La IA está comparando los enfoques..."):
        analisis = analizar_tema(texto, noticias[:40])
    mostrar_analisis(texto, noticias[:40], analisis, "busqueda", rango_busqueda)


def buscar_en_mundo(texto, rango_busqueda):
    with st.spinner("La IA está identificando los países involucrados..."):
        tema = definir_conflicto(texto)
    if tema.get("actores"):
        st.caption("Países o bloques revisados: " + ", ".join(nombre_actor(c) for c in tema["actores"]))
    else:
        st.caption("No se identificó un país en particular: se revisan agencias internacionales y medios chilenos.")
    ejecutar_geo(tema, rango_busqueda, "mundo_" + texto, min_actores=0)


tab_hoy, tab_buscar, tab_geo = st.tabs(
    ["📰 Temas del día", "🔍 Buscar una noticia", "🌐 Geopolítica"]
)

with tab_hoy:
    if st.button("Analizar los temas del día", type="primary"):
        st.session_state["hoy"] = True
    if st.session_state.get("hoy"):
        try:
            with st.spinner("Leyendo titulares de los medios..."):
                noticias = traer_titulares("", dias, max_por_medio)
            if not noticias:
                st.warning("No llegaron titulares. Prueba de nuevo en unos minutos.")
            else:
                n_medios = len({n["medio"] for n in noticias})
                st.caption(f"{len(noticias)} titulares de {n_medios} medios.")
                with st.spinner("La IA está agrupando los temas..."):
                    temas = agrupar_temas(noticias, n_temas)
                por_id = {n["id"]: n for n in noticias}
                mostrados = 0
                for t in temas:
                    grupo = [por_id[i] for i in t.get("ids", []) if i in por_id]
                    if len({n["tendencia"] for n in grupo}) < 2:
                        continue
                    with st.spinner(f"Analizando: {t.get('tema', '')}..."):
                        analisis = analizar_tema(t.get("tema", ""), grupo)
                    mostrar_analisis(t.get("tema", ""), grupo, analisis, f"hoy_{mostrados}", max(dias, 7))
                    mostrados += 1
                if mostrados == 0:
                    st.info("Hoy no hubo temas cubiertos por más de una tendencia.")
        except Exception as e:
            st.error(f"Algo falló: {e}")

with tab_buscar:
    st.write(
        "¿Viste una noticia y quieres conocer todas sus caras? Escribe el tema o pega el titular. "
        "Te mostramos cómo la cuentan los distintos medios, en Chile y en el mundo, con su análisis, "
        "podcasts y videos."
    )
    consulta = st.text_input("Tema o titular", placeholder="Ej: reforma de pensiones, aranceles al cobre, elecciones en Brasil")
    b1, b2 = st.columns(2)
    with b1:
        alcance = st.radio("¿Dónde buscar?", ["Chile", "El mundo", "Chile y el mundo"], horizontal=True)
    with b2:
        OPCIONES_PERIODO = {
            "Últimos 3 días": 3,
            "Últimos 7 días": 7,
            "Último mes": 30,
            "Últimos 3 meses": 90,
            "Último año": 365,
            "📅 Elegir fechas": None,
        }
        eleccion = st.selectbox("Período", list(OPCIONES_PERIODO), index=1)
        rango = OPCIONES_PERIODO[eleccion]
        if rango is None:
            hoy = datetime.date.today()
            fechas = st.date_input(
                "Desde – hasta",
                value=(hoy - datetime.timedelta(days=30), hoy),
                min_value=datetime.date(2005, 1, 1),
                max_value=hoy,
                format="DD/MM/YYYY",
            )
            if isinstance(fechas, (tuple, list)) and len(fechas) == 2:
                rango = (fechas[0].isoformat(), (fechas[1] + datetime.timedelta(days=1)).isoformat())
            else:
                rango = 30
                st.caption("Elige la fecha de inicio y la de término en el calendario.")
    if st.button("Buscar todas las caras", type="primary") and consulta.strip():
        st.session_state["busqueda"] = (consulta.strip(), rango, alcance)
    if st.session_state.get("busqueda"):
        texto, rango_busqueda, alcance_b = st.session_state["busqueda"]
        try:
            if alcance_b in ("Chile", "Chile y el mundo"):
                if alcance_b == "Chile y el mundo":
                    st.markdown("## 📍 En Chile")
                buscar_en_chile(texto, rango_busqueda)
            if alcance_b in ("El mundo", "Chile y el mundo"):
                if alcance_b == "Chile y el mundo":
                    st.markdown("## 🌐 En el mundo")
                buscar_en_mundo(texto, rango_busqueda)
        except Exception as e:
            st.error(f"Algo falló: {e}")

with tab_geo:
    st.write(
        "Conflictos internacionales que pueden afectar la economía de Chile, contados por cada lado "
        "desde sus propios medios."
    )
    OTRO = "✏️ Otro (escríbelo)"
    opciones = [c["nombre"] for c in CONFLICTOS] + [OTRO]
    elegido = st.selectbox("Conflicto", opciones)
    texto_otro = ""
    if elegido == OTRO:
        texto_otro = st.text_input(
            "¿Qué conflicto quieres entender?", placeholder="Ej: Rusia y Ucrania, gas y petróleo"
        )
    dias_geo = st.selectbox(
        "Noticias de los últimos",
        [3, 7, 14, 30, 90],
        index=1,
        format_func=lambda d: {30: "Último mes", 90: "Últimos 3 meses"}.get(d, f"{d} días"),
    )
    if st.button("Ver los dos lados", type="primary", key="btn_geo"):
        st.session_state["geo"] = (elegido, texto_otro.strip(), dias_geo)

    if st.session_state.get("geo"):
        elegido_g, otro_g, dias_g = st.session_state["geo"]
        try:
            conflicto = None
            if elegido_g == OTRO:
                if not otro_g:
                    st.warning("Escribe el conflicto que quieres entender.")
                else:
                    with st.spinner("La IA está identificando los lados del conflicto..."):
                        conflicto = definir_conflicto(otro_g)
            else:
                conflicto = next(c for c in CONFLICTOS if c["nombre"] == elegido_g)
            if conflicto is not None:
                ejecutar_geo(conflicto, dias_g, "geo_" + conflicto["nombre"])
        except Exception as e:
            st.error(f"Algo falló: {e}")

st.caption(
    "⚠️ Prototipo. El análisis se basa en titulares, no en los artículos completos, y la IA puede "
    "equivocarse. La tendencia de cada medio es una clasificación general, no de cada periodista. "
    "Lee las fuentes originales antes de sacar conclusiones."
)
