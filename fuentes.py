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
