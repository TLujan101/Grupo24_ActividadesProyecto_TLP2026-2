# -*- coding: utf-8 -*-
# Tests del juego Tetris.

import random
import unittest

from tests.tk_falso import EventoFalso
from engine.game import COLOR_GRID_FIJA
from engine.tetris import Tetris
from engine.utilidades import Colores, Arcoiris

PIEZA_O = [[[1, 1], [1, 1]]]
PIEZA_I = [[[0, 1, 0], [0, 1, 0], [0, 1, 0]],
           [[0, 0, 0], [1, 1, 1], [0, 0, 0]]]


def accion(verbo, objeto=None, params=None):
    return {'accion': verbo, 'objeto': objeto, 'params': params or []}


def datos_tetris():
    # Tablero 6x6. Solo O_PIECE tiene chance > 0, asi el spawn es predecible.
    return {
        'tipo_juego': 'TETRIS',
        'config': {'grid_size': [6, 6]},
        'shapes': {
            'O_PIECE': {'estados': PIEZA_O, 'color': 'YELLOW', 'chance': 10},
            'I_PIECE': {'estados': PIEZA_I, 'color': 'CYAN', 'chance': 0},
            'POWERUP': {'estados': [[[1]]], 'color': 'RAINBOW', 'chance': 0},
            'CLEAR_LINE_PIECE': {'estados': [[[1], [1]]], 'color': 'RAINBOW', 'chance': 0},
            'SUPERBOMBA': {'estados': [[[1]]], 'color': 'RAINBOW', 'chance': 0},
            'CLEAR_THREE_PIECE': {'estados': [[[1, 0, 1]]], 'color': 'RAINBOW', 'chance': 0},
        },
        'events': {
            'ON_START': [accion('SPAWN', 'RANDOM_SHAPE')],
            'ON_TICK': [accion('MOVE', 'CURRENT_PIEZA', ['DOWN'])],
            'ON_KEY_UP': [accion('ROTATE', 'CURRENT_PIEZA')],
            'ON_KEY_DOWN': [accion('MOVE', 'CURRENT_PIEZA', ['DOWN'])],
            'ON_KEY_LEFT': [accion('MOVE', 'CURRENT_PIEZA', ['LEFT'])],
            'ON_KEY_RIGHT': [accion('MOVE', 'CURRENT_PIEZA', ['RIGHT'])],
            'ON_LINE_CLEAR': [accion('INCREASE_SCORE', '100')],
        },
    }


def poner_pieza(juego, nombre, x, y, rotacion=0):
    juego.pieza_nombre = nombre
    juego.pieza_actual = juego.datos_juego['shapes'][nombre]['estados']
    juego.pieza_x, juego.pieza_y, juego.pieza_rotacion = x, y, rotacion


class TestTetrisBase(unittest.TestCase):
    # Guarda y restaura random.random para poder forzar los power ups

    def setUp(self):
        self._random_original = random.random
        random.random = lambda: 0.99   # por defecto: sin power up

    def tearDown(self):
        random.random = self._random_original

    def forzar_random(self, valor):
        random.random = lambda: valor


class TestTetris(TestTetrisBase):

    def test_inicio(self):
        juego = Tetris(datos_tetris())
        self.assertEqual(juego.velocidad_gravedad, 0.4)
        # Pool de piezas con sus pesos; POWERUP nunca sale al azar
        pool = dict(zip(juego._nombres_piezas, juego._pesos_piezas))
        self.assertNotIn('POWERUP', pool)
        self.assertEqual((pool['O_PIECE'], pool['I_PIECE'], pool['CLEAR_LINE_PIECE']), (10, 0, 0))
        # ON_START hace spawn
        self.assertEqual(juego.pieza_nombre, 'O_PIECE')
        self.assertEqual(juego.pieza_actual, PIEZA_O)
        self.assertEqual(juego.pieza_color, Colores['YELLOW'])
        self.assertEqual((juego.pieza_x, juego.pieza_y, juego.pieza_rotacion), (2, 0, 0))

        # Formas en el formato viejo (lista de estados, sin color ni chance)
        datos_juego = datos_tetris()
        datos_juego['shapes'] = {'VIEJA': [[[1]]]}
        juego = Tetris(datos_juego)
        self.assertEqual((juego._nombres_piezas, juego._pesos_piezas), (['VIEJA'], [10]))
        self.assertEqual((juego.pieza_actual, juego.pieza_color), ([[[1]]], '#00FFFF'))

    def test_spawn(self):
        juego = Tetris(datos_tetris())
        juego.siguiente_powerup = 'POWERUP'
        juego.tetris_spawn_pieza()
        self.assertEqual((juego.pieza_nombre, juego.pieza_color), ('POWERUP', Colores['RAINBOW']))
        self.assertEqual(juego.siguiente_powerup, None)
        juego.tetris_spawn_pieza()
        self.assertEqual(juego.pieza_nombre, 'O_PIECE')
        # Si la pieza nueva choca, se termina el juego
        juego.grid[1][3] = 1
        juego.tetris_spawn_pieza()
        self.assertTrue(juego.juego_terminado)

    def test_mover_y_colisiones(self):
        juego = Tetris(datos_tetris())
        self.assertFalse(juego.tetris_verificar_colision(0, 0, 0))
        self.assertTrue(juego.tetris_verificar_colision(-1, 0, 0))
        self.assertTrue(juego.tetris_verificar_colision(5, 0, 0))
        self.assertTrue(juego.tetris_verificar_colision(0, 5, 0))

        for _ in range(3):
            juego.tetris_mover_pieza('LEFT')
        self.assertEqual(juego.pieza_x, 0, 'se detiene en la pared izquierda')
        for _ in range(6):
            juego.tetris_mover_pieza('RIGHT')
        self.assertEqual(juego.pieza_x, 4, 'se detiene en la pared derecha')
        juego.tetris_mover_pieza('DOWN')
        self.assertEqual(juego.pieza_y, 1)

        juego = Tetris(datos_tetris())
        juego.grid[0][1] = 1
        juego.tetris_mover_pieza('LEFT')
        self.assertEqual(juego.pieza_x, 2, 'bloqueada por una celda ocupada')
        juego.grid[3][3] = 1
        self.assertTrue(juego.tetris_verificar_colision(2, 2, 0))

        # Sin pieza nada falla
        juego.pieza_actual = None
        self.assertFalse(juego.tetris_verificar_colision(-10, -10, 0))
        juego.tetris_mover_pieza('LEFT')
        juego.tetris_rotar_pieza()

    def test_rotar(self):
        juego = Tetris(datos_tetris())
        poner_pieza(juego, 'I_PIECE', 2, 1)
        juego.tetris_rotar_pieza()
        self.assertEqual(juego.pieza_rotacion, 1)
        juego.manejar_input_gui(EventoFalso('Up'))
        self.assertEqual(juego.pieza_rotacion, 0)
        poner_pieza(juego, 'I_PIECE', -1, 1)
        juego.tetris_rotar_pieza()
        self.assertEqual(juego.pieza_rotacion, 0, 'la pared bloquea la rotacion')

    def test_controles(self):
        juego = Tetris(datos_tetris())
        juego.manejar_input_gui(EventoFalso('a'))
        self.assertEqual((juego.pieza_x, juego.pieza_y), (2, 0), 'tecla desconocida')
        juego.manejar_input_gui(EventoFalso('Left'))
        self.assertEqual(juego.pieza_x, 1)
        juego.manejar_input_gui(EventoFalso('Right'))
        juego.manejar_input_gui(EventoFalso('Right'))
        self.assertEqual(juego.pieza_x, 3)
        juego.manejar_input_gui(EventoFalso('Down'))
        self.assertEqual(juego.pieza_y, 1)
        # Acciones de otros juegos se ignoran
        juego.ejecutar_accion('GROW', 'PLAYER', accion('GROW', 'PLAYER', ['1']))
        juego.ejecutar_accion('SET_DIRECTION', 'UP', accion('SET_DIRECTION', 'UP'))

    def test_caida_fijado_y_linea(self):
        juego = Tetris(datos_tetris())
        juego.grid[5] = [1, 1, 0, 0, 1, 1]
        for _ in range(4):
            juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.pieza_y, 4)
        juego.ejecutar_evento('ON_TICK')
        # Se fija, completa la fila de abajo y la limpia
        self.assertEqual(juego.grid[4], [0] * 6)
        self.assertEqual(juego.grid[5], [0, 0, 1, 1, 0, 0])
        self.assertEqual(juego.puntuacion, 100)
        # Se genera una pieza nueva arriba
        self.assertEqual((juego.pieza_nombre, juego.pieza_x, juego.pieza_y), ('O_PIECE', 2, 0))

    def test_power_ups_al_fijar(self):
        # Bomba: explota radio 1
        juego = Tetris(datos_tetris())
        for y in range(3, 6):
            juego.grid[y] = [1, 1, 1, 1, 1, 0]
        poner_pieza(juego, 'POWERUP', 2, 4)
        juego.tetris_fijar_pieza()
        for y in range(3, 6):
            self.assertEqual(juego.grid[y], [1, 0, 0, 0, 1, 0], 'bomba')
        self.assertEqual(juego.puntuacion, 150)
        # En la esquina: lo que queda fuera del tablero se ignora y sale la siguiente pieza
        poner_pieza(juego, 'POWERUP', 0, 5)
        juego.tetris_fijar_pieza()
        self.assertEqual((juego.pieza_nombre, juego.pieza_x, juego.pieza_y), ('O_PIECE', 2, 0))

        # Superbomba
        juego = Tetris(datos_tetris())
        for y in range(1, 6):
            juego.grid[y] = [1, 1, 1, 1, 1, 0]
        poner_pieza(juego, 'SUPERBOMBA', 1, 3)
        juego.tetris_fijar_pieza()
        self.assertEqual(juego.grid[1], [1, 1, 1, 1, 1, 0])
        for y in range(2, 6):
            self.assertEqual(juego.grid[y], [0] * 6, 'superbomba')
        self.assertEqual(juego.puntuacion, 350)

        # Limpia columnas
        juego = Tetris(datos_tetris())
        for y in range(2, 6):
            juego.grid[y] = [1, 1, 1, 1, 1, 0]
        poner_pieza(juego, 'CLEAR_THREE_PIECE', 1, 0)
        juego.tetris_fijar_pieza()
        for y in range(2, 6):
            self.assertEqual(juego.grid[y], [1, 0, 1, 0, 1, 0], 'limpia columnas')
        self.assertEqual(juego.puntuacion, 500)

        # Limpia filas
        juego = Tetris(datos_tetris())
        for y in range(4):
            juego.grid[2 + y][y] = 1
        poner_pieza(juego, 'CLEAR_LINE_PIECE', 0, 3)
        juego.tetris_fijar_pieza()
        self.assertEqual(juego.grid[3], [0] * 6, 'limpia filas')
        self.assertEqual(juego.grid[4], [1, 0, 0, 0, 0, 0])
        self.assertEqual(juego.grid[5], [0, 0, 0, 1, 0, 0])
        self.assertEqual(juego.puntuacion, 400)

    def test_limpiar_lineas(self):
        juego = Tetris(datos_tetris())
        juego.grid[3] = [1, 0, 0, 0, 0, 0]
        juego.grid[4] = [1, 1, 1, 1, 1, 0]
        juego.tetris_limpiar_lineas()
        self.assertEqual(juego.puntuacion, 0, 'sin lineas llenas no pasa nada')

        juego.grid[4] = [1] * 6
        juego.grid[5] = [1] * 6
        juego.tetris_limpiar_lineas()
        self.assertEqual(juego.grid[5], [1, 0, 0, 0, 0, 0])
        self.assertEqual(juego.puntuacion, 2 * 100)   # 2 lineas

    def test_sorteo_de_power_up(self):
        casos = [(0.1, 'POWERUP', 'Power Up:BOMBA'),
                 (0.3, 'CLEAR_LINE_PIECE', 'Power Up:LIMPIA LINEAS'),
                 (0.5, 'SUPERBOMBA', 'Power Up:SUPERBOMBA'),
                 (0.7, 'CLEAR_THREE_PIECE', 'Power Up:LIMPIA COLUMNAS'),
                 (0.9, None, None),
                 # Los limites exactos caen en el rango superior
                 (0.25, 'CLEAR_LINE_PIECE', 'Power Up:LIMPIA LINEAS'),
                 (0.45, 'SUPERBOMBA', 'Power Up:SUPERBOMBA'),
                 (0.65, 'CLEAR_THREE_PIECE', 'Power Up:LIMPIA COLUMNAS')]
        for valor, powerup, texto in casos:
            self.forzar_random(valor)
            juego = Tetris(datos_tetris())
            juego.grid[3] = [1] * 6
            juego.grid[4] = [1] * 6
            juego.grid[5] = [1] * 6
            juego.tetris_limpiar_lineas()
            self.assertEqual(juego.siguiente_powerup, powerup, valor)
            if texto:
                notif = juego.root.hijos[-1]
                self.assertEqual(notif.opciones.get('text'), texto)
                self.assertEqual(juego.root.afters[-1], (2500, notif.destroy))

        # Simple/doble no dan premio (solo triple)
        for filas in (1, 2):
            self.forzar_random(0.1)
            juego = Tetris(datos_tetris())
            for i in range(filas):
                juego.grid[5 - i] = [1] * 6
            juego.tetris_limpiar_lineas()
            self.assertEqual(juego.siguiente_powerup, None, filas)

        # La siguiente pieza es el power up sorteado
        self.forzar_random(0.1)
        juego = Tetris(datos_tetris())
        juego.grid[3] = [1] * 6
        juego.grid[4] = [1] * 6
        juego.grid[5] = [1] * 6
        juego.tetris_limpiar_lineas()
        self.assertEqual(juego.siguiente_powerup, 'POWERUP')
        juego.tetris_spawn_pieza()
        self.assertEqual((juego.pieza_nombre, juego.siguiente_powerup), ('POWERUP', None))

    def test_dibujar(self):
        juego = Tetris(datos_tetris())
        juego.dibujar()
        amarillo = Colores['YELLOW']
        self.assertEqual(juego.canvas.rectangulos, [
            ((50, 0, 75, 25), amarillo), ((75, 0, 100, 25), amarillo),
            ((50, 25, 75, 50), amarillo), ((75, 25, 100, 50), amarillo)])

        # Pieza arcoiris: el color cambia con el frame
        juego.siguiente_powerup = 'POWERUP'
        juego.tetris_spawn_pieza()
        juego.frame = 11   # dibujar() lo sube a 12 -> 12 // 6 = 2
        juego.dibujar()
        self.assertEqual(juego.canvas.rectangulos, [((50, 0, 75, 25), Arcoiris[2])])

        # Celdas fijas: siempre en gris
        juego.pieza_actual = None
        juego.grid[5][0] = 1
        juego.grid[5][1] = 1
        juego.frame = -1
        juego.dibujar()
        self.assertEqual(juego.canvas.rectangulos,
                         [((0, 125, 25, 150), COLOR_GRID_FIJA), ((25, 125, 50, 150), COLOR_GRID_FIJA)])


if __name__ == '__main__':
    unittest.main()
