# -*- coding: utf-8 -*-
# engine --- Un archivo por juego. Todos heredan de Game (game.py).
# Modulos de apoyo: audio.py/tracker.py (musica sintetizada),
# utilidades.py (colores y sorteo ponderado).
#
# Para agregar un juego nuevo:
#   1. Crear engine/<nombre>.py con una clase hija de Game.
#   2. Registrarla en JUEGOS con su GAME_TYPE.

from .game import Game
from .tetris import Tetris
from .snake import Snake

__all__ = ['Game', 'Tetris', 'Snake', 'JUEGOS', 'crear_juego']

# GAME_TYPE del .brick -> clase que ejecuta ese juego
JUEGOS = {
    'TETRIS': Tetris,
    'SNAKE': Snake,
}

def crear_juego(datos_juego):
    tipo_juego = datos_juego.get('tipo_juego', 'TETRIS')
    if tipo_juego not in JUEGOS:
        raise ValueError("Tipo de juego desconocido: " + str(tipo_juego))
    return JUEGOS[tipo_juego](datos_juego)
