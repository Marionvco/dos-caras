"""
Lista de medios que revisa la app.

IMPORTANTE: la tendencia es una clasificación INICIAL para probar el prototipo.
Revísala y ajústala a tu criterio (y publícala en la app, para ser transparente).

Para agregar un medio, copia una línea y cambia nombre, dominio y tendencia.
Tendencia puede ser: "izquierda", "centro" o "derecha".
"""

MEDIOS = [
    # Tendencia derecha / centroderecha
    {"nombre": "La Tercera", "dominio": "latercera.com", "tendencia": "derecha"},
    {"nombre": "Emol (El Mercurio)", "dominio": "emol.com", "tendencia": "derecha"},
    {"nombre": "El Líbero", "dominio": "ellibero.cl", "tendencia": "derecha"},
    {"nombre": "Ex-Ante", "dominio": "ex-ante.cl", "tendencia": "derecha"},
    # Tendencia centro / generalistas
    {"nombre": "BioBioChile", "dominio": "biobiochile.cl", "tendencia": "centro"},
    {"nombre": "Cooperativa", "dominio": "cooperativa.cl", "tendencia": "centro"},
    {"nombre": "24 Horas (TVN)", "dominio": "24horas.cl", "tendencia": "centro"},
    # Tendencia izquierda / centroizquierda
    {"nombre": "El Mostrador", "dominio": "elmostrador.cl", "tendencia": "izquierda"},
    {"nombre": "The Clinic", "dominio": "theclinic.cl", "tendencia": "izquierda"},
    {"nombre": "El Desconcierto", "dominio": "eldesconcierto.cl", "tendencia": "izquierda"},
    {"nombre": "Radio U. de Chile", "dominio": "radio.uchile.cl", "tendencia": "izquierda"},
]


# Prensa económica especializada (pestaña Economía). Se muestra en su propia columna.
MEDIOS_ECONOMICOS = [
    {"nombre": "Diario Financiero", "dominio": "df.cl"},
    {"nombre": "Pulso (La Tercera)", "dominio": "latercera.com/pulso"},
    {"nombre": "El Mostrador Mercados", "dominio": "elmostrador.cl/mercados"},
    {"nombre": "Bloomberg Línea", "dominio": "bloomberglinea.com"},
]

# Palabras con que se buscan noticias económicas en los medios generales.
CONSULTA_ECONOMIA = (
    '(economía OR inflación OR IPC OR dólar OR cobre OR "Banco Central" OR empleo '
    'OR desempleo OR impuestos OR pensiones OR exportaciones OR combustibles OR sueldo)'
)

# Indicadores que se muestran arriba de la pestaña Economía (fuente: mindicador.cl).
# código de mindicador.cl: (nombre a mostrar, formato)
INDICADORES = {
    "dolar": ("Dólar", "$"),
    "euro": ("Euro", "$"),
    "uf": ("UF", "$"),
    "utm": ("UTM", "$"),
    "ipc": ("IPC (mensual)", "%"),
    "tpm": ("Tasa de política monetaria", "%"),
    "libra_cobre": ("Cobre (US$/libra)", "US$"),
    "tasa_desempleo": ("Desempleo", "%"),
}


# Medios internacionales en español: se usan para ver cómo se cuenta un tema chileno desde fuera.
MEDIOS_INTERNACIONALES = [
    {"nombre": "BBC Mundo", "dominio": "bbc.com"},
    {"nombre": "DW en español", "dominio": "dw.com"},
    {"nombre": "France 24 en español", "dominio": "france24.com"},
    {"nombre": "EFE", "dominio": "efe.com"},
    {"nombre": "El País", "dominio": "elpais.com"},
    {"nombre": "CNN en Español", "dominio": "cnnespanol.cnn.com"},
]


# Países que la app puede consultar cuando un tema involucra a otro país.
# Se busca la noticia en el Google News de ese país, en su idioma.
# Para agregar uno: código de 2 letras, nombre, idioma (hl) y edición (ceid) de Google News.
PAISES = {
    "AR": {"nombre": "Argentina", "hl": "es-419", "ceid": "AR:es-419"},
    "PE": {"nombre": "Perú", "hl": "es-419", "ceid": "PE:es-419"},
    "BO": {"nombre": "Bolivia", "hl": "es-419", "ceid": "BO:es-419"},
    "BR": {"nombre": "Brasil", "hl": "pt-BR", "ceid": "BR:pt-419"},
    "MX": {"nombre": "México", "hl": "es-419", "ceid": "MX:es-419"},
    "CO": {"nombre": "Colombia", "hl": "es-419", "ceid": "CO:es-419"},
    "VE": {"nombre": "Venezuela", "hl": "es-419", "ceid": "VE:es-419"},
    "US": {"nombre": "Estados Unidos", "hl": "en-US", "ceid": "US:en"},
    "ES": {"nombre": "España", "hl": "es", "ceid": "ES:es"},
    "GB": {"nombre": "Reino Unido", "hl": "en-GB", "ceid": "GB:en"},
    "FR": {"nombre": "Francia", "hl": "fr", "ceid": "FR:fr"},
    "DE": {"nombre": "Alemania", "hl": "de", "ceid": "DE:de"},
}


# ------------------------------------------------------------------ GEOPOLÍTICA
# Actores de los conflictos internacionales y dónde leer su versión.
# "edicion": se busca en el Google News de ese país (idioma, edición, país).
# "sitios": se busca en esos medios específicos (en inglés).
# "nota": aviso que se muestra al lector (por ejemplo, si son medios estatales).
ACTORES = {
    "US": {"nombre": "Estados Unidos", "edicion": ("en-US", "US:en", "US")},
    "CN": {
        "nombre": "China",
        "sitios": [("Xinhua", "xinhuanet.com"), ("Global Times", "globaltimes.cn"), ("CGTN", "cgtn.com")],
        "nota": "Medios estatales chinos: reflejan la postura oficial del gobierno.",
    },
    "RU": {
        "nombre": "Rusia",
        "sitios": [("TASS", "tass.com"), ("RT", "rt.com")],
        "nota": "Medios estatales rusos: reflejan la postura oficial del gobierno.",
    },
    "IR": {
        "nombre": "Irán",
        "sitios": [("Press TV", "presstv.ir"), ("Tehran Times", "tehrantimes.com"), ("IRNA", "irna.ir")],
        "nota": "Medios estatales o afines al gobierno iraní: reflejan su postura oficial.",
    },
    "UA": {
        "nombre": "Ucrania",
        "sitios": [("Kyiv Independent", "kyivindependent.com"), ("Ukrinform", "ukrinform.net")],
    },
    "IL": {
        "nombre": "Israel",
        "sitios": [("The Times of Israel", "timesofisrael.com"), ("Haaretz", "haaretz.com")],
    },
    "EU": {
        "nombre": "Unión Europea",
        "sitios": [("Euronews", "euronews.com"), ("Politico Europe", "politico.eu")],
    },
}

# Agencias y medios internacionales que cubren a todos los lados.
AGENCIAS = [
    ("Reuters", "reuters.com"),
    ("AP", "apnews.com"),
    ("BBC", "bbc.com"),
    ("Al Jazeera", "aljazeera.com"),
]

# Conflictos que aparecen en la lista. Para agregar uno, copia un bloque.
# "busqueda_en": palabras clave en inglés (para los medios de cada lado).
# "busqueda_es": palabras clave en español (para medios chilenos e impacto en Chile).
CONFLICTOS = [
    {
        "nombre": "Estados Unidos vs Irán",
        "actores": ["US", "IR"],
        "busqueda_en": "United States Iran",
        "busqueda_es": "Estados Unidos Irán",
    },
    {
        "nombre": "Guerra comercial Estados Unidos vs China",
        "actores": ["US", "CN"],
        "busqueda_en": "US China tariffs trade",
        "busqueda_es": "China Estados Unidos aranceles",
    },
    {
        "nombre": "Sanciones de Estados Unidos a Rusia",
        "actores": ["US", "RU"],
        "busqueda_en": "US sanctions Russia",
        "busqueda_es": "sanciones Estados Unidos Rusia",
    },
]
