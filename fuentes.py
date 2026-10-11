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
