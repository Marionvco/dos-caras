"""
Dos Caras — prototipo
Noticias vistas desde todos los lados, para salir de la burbuja del algoritmo.

Cómo funciona:
1. Lee titulares recientes de medios chilenos de distinta tendencia (vía Google News RSS).
2. La IA (Gemini gratis, o Claude) agrupa los titulares que hablan del mismo hecho.
3. Para cada hecho muestra: cómo lo cuenta cada lado, lo que coinciden (la intersección),
   dónde difieren y qué afirmaciones tienen respaldo de varios lados.
"""

import json
import urllib.parse

import feedparser
import streamlit as st


from fuentes import MEDIOS

MODELO_GEMINI = "gemini-3.8-flash"  # capa gratuita
MODELO_CLAUDE = "claude-sonnet-5-5"  # opción pagada
AGENTE = "Mozilla/5.0 (compatible; DosCaras/0.1)"
ORDEN = ["izquierda", "centro", "derecha"]
ETIQUETAS = {"izquierda": "⬅️ Izquierda", "centro": "⏺️ Centro", "derecha": "➡️ Derecha"}
TRES_HORAS = 3 * 60 * 60

st.set_page_config(page_title="Dos Caras", page_icon="🪙", layout="wide")


# ---------------------------------------------------------------- utilidades
def seguro(texto):
    """Evita que símbolos de los titulares ($, [, ]) rompan el formato."""
    return str(texto).replace("$", "\\$").replace("[", "(").replace("]", ")")


def url_google_news(consulta):
    params = {"q": consulta, "hl": "es-419", "gl": "CL", "ceid": "CL:es-419"}
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)


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
        consulta = f"{texto_busqueda} site:{medio['dominio']} when:{dias}d".strip()
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
        from google import genai

        respuesta = genai.Client(api_key=clave_gemini).models.generate_content(
            model=secreto("GEMINI_MODEL", MODELO_GEMINI),
            contents=prompt,
            config={"response_mime_type": "application/json", "max_output_tokens": max_tokens},
        )
        return extraer_json(respuesta.text or "")

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
  "preguntas_abiertas": ["qué falta saber para formarse una opinión propia"]
}}"""
    return llamar_ia(prompt, 3000)


# ---------------------------------------------------------- 3. mostrar
def lista_puntos(titulo, items):
    st.markdown(f"**{titulo}**")
    if not items:
        st.markdown("_Nada que destacar._")
    for x in items:
        st.markdown(f"- {seguro(x)}")


def mostrar_analisis(tema, noticias, analisis):
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
    st.divider()


# ------------------------------------------------------------ pantalla
st.title("🪙 Dos Caras")
st.caption("Las noticias vistas desde todos los lados, para salir de la burbuja del algoritmo.")

with st.sidebar:
    st.header("Ajustes")
    dias = st.slider("Noticias de los últimos días", 1, 3, 1)
    max_por_medio = st.slider("Titulares por medio", 5, 20, 10)
    n_temas = st.slider("Temas a analizar", 2, 8, 4)
    if st.button("🔄 Traer noticias nuevas"):
        st.cache_data.clear()
    with st.expander("Medios revisados y su tendencia"):
        for m in MEDIOS:
            st.write(f"{ETIQUETAS[m['tendencia']]} — {m['nombre']}")
        st.caption("Clasificación inicial, editable en fuentes.py.")

tab_hoy, tab_buscar = st.tabs(["📰 Temas del día", "🔍 Ver las otras caras de una noticia"])

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
                    mostrar_analisis(t.get("tema", ""), grupo, analisis)
                    mostrados += 1
                if mostrados == 0:
                    st.info("Hoy no hubo temas cubiertos por más de una tendencia.")
        except Exception as e:
            st.error(f"Algo falló: {e}")

with tab_buscar:
    st.write(
        "¿Viste una noticia y quieres saber cómo la cuentan los otros lados? "
        "Escribe el tema o pega el titular."
    )
    consulta = st.text_input("Tema o titular", placeholder="Ej: reforma de pensiones")
    rango = st.selectbox("Buscar en", [3, 7, 30], index=1, format_func=lambda d: f"Últimos {d} días")
    if st.button("Buscar las otras caras", type="primary") and consulta.strip():
        st.session_state["busqueda"] = (consulta.strip(), rango)
    if st.session_state.get("busqueda"):
        texto, rango_busqueda = st.session_state["busqueda"]
        try:
            with st.spinner("Buscando en todos los medios..."):
                clave = palabras_clave(texto)
                noticias = traer_titulares(clave, rango_busqueda, 5)
            st.caption(f"Búsqueda usada: {clave}")
            if not noticias:
                st.warning("No encontré esta noticia en los medios revisados. Prueba con menos palabras.")
            else:
                with st.spinner("La IA está comparando los enfoques..."):
                    analisis = analizar_tema(texto, noticias[:40])
                mostrar_analisis(texto, noticias[:40], analisis)
        except Exception as e:
            st.error(f"Algo falló: {e}")

st.caption(
    "⚠️ Prototipo. El análisis se basa en titulares, no en los artículos completos, y la IA puede "
    "equivocarse. La tendencia de cada medio es una clasificación general, no de cada periodista. "
    "Lee las fuentes originales antes de sacar conclusiones."
)
