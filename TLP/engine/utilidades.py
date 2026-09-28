# -*- coding: utf-8 -*-
# utilidades.py --- Constantes y funciones de apoyo compartidas por los juegos.

import random
import bisect

Colores = {
    "CYAN": "#00FFFF",
    "YELLOW": "#FFFF00",
    "PURPLE": "#AA00FF",
    "GREEN": "#00FF00",
    "RED": "#FF0000",
    "BLUE": "#0000FF",
    "ORANGE": "#FF7F00",
    "WHITE": "#FFFFFF",
    "BLACK": "#000000",
    "RAINBOW": "#FFFFFF"
}
Arcoiris = ["#FF0000","#FF7F00","#FFFF00","#00FF00","#0000FF","#AA00FF"]

def eleccion_ponderada(items, pesos):
    if len(items) != len(pesos):
        raise ValueError("items y pesos deben tener la misma longitud")
    acum = []
    s = 0
    for w in pesos:
        s += w
        acum.append(s)
    if s <= 0:
        raise ValueError("Los pesos deben sumar > 0")
    tiro = random.randint(1, s)
    return items[bisect.bisect_left(acum, tiro)]
