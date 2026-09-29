# -*- coding: utf-8 -*-
# Tests del juego Snake.

import random
import unittest

from tests.tk_falso import EventoFalso
from engine.snake import Snake, COLOR_SNAKE_CABEZA, COLOR_SNAKE_CUERPO, COLOR_FOOD


def accion(verbo, objeto=None, params=None):
    return {'accion': verbo, 'objeto': objeto, 'params': params or []}


def datos_snake(inicio=(2, 2)):
    # Tablero 5x5, mismos eventos que games/snake.brick
    return {
        'tipo_juego': 'SNAKE',
        'config': {'grid_size': [5, 5]},
        'shapes': {'PIXEL': {'estados': [[[1]]], 'color': 'CYAN', 'chance': 10}},
        'events': {
            'ON_START': [accion('SPAWN', 'PLAYER', [list(inicio)] if inicio else []),
                         accion('SPAWN', 'FOOD', ['RANDOM'])],
            'ON_TICK': [accion('MOVE', 'PLAYER', ['FORWARD'])],
            'ON_EAT_FOOD': [accion('INCREASE_SCORE', '10'),
                            accion('GROW', 'PLAYER', ['1']),
                            accion('SPAWN', 'FOOD', ['RANDOM'])],
            'ON_COLLISION_WALL': [accion('GAME_OVER')],
            'ON_COLLISION_SELF': [accion('GAME_OVER')],
            'ON_KEY_UP': [accion('SET_DIRECTION', 'UP')],
            'ON_KEY_DOWN': [accion('SET_DIRECTION', 'DOWN')],
            'ON_KEY_LEFT': [accion('SET_DIRECTION', 'LEFT')],
            'ON_KEY_RIGHT': [accion('SET_DIRECTION', 'RIGHT')],
        },
    }


class TestSnakeBase(unittest.TestCase):
    # Controla random.randint para saber donde aparece la comida

    def setUp(self):
        self._randint_original = random.randint
        self.forzar_comida([(0, 0)])

    def tearDown(self):
        random.randint = self._randint_original

    def forzar_comida(self, posiciones):
        valores = []
        for x, y in posiciones:
            valores.extend([x, y])
        random.randint = lambda a, b: valores.pop(0) if valores else 0


class TestSnake(TestSnakeBase):

    def test_inicio(self):
        self.forzar_comida([(4, 1)])
        juego = Snake(datos_snake())
        self.assertEqual(juego.velocidad_gravedad, 0.15)
        self.assertEqual(juego.serpiente_direccion, (1, 0))
        self.assertEqual(juego.serpiente_cuerpo, [(2, 2)])
        self.assertEqual(juego.posicion_comida, (4, 1))

        # La comida nunca aparece sobre la serpiente
        self.forzar_comida([(2, 2), (3, 4)])
        self.assertEqual(Snake(datos_snake()).posicion_comida, (3, 4))

        # SPAWN PLAYER sin coordenadas: al centro
        self.assertEqual(Snake(datos_snake(inicio=None)).serpiente_cuerpo, [(2, 2)])

    def test_movimiento_y_choques(self):
        juego = Snake(datos_snake())
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.serpiente_cuerpo, [(3, 2)])

        juego.serpiente_cuerpo = []
        juego.snake_mover_jugador()   # sin cuerpo no falla
        self.assertEqual(juego.serpiente_cuerpo, [])

        # Puede entrar donde estaba la cola (la cola se mueve en el mismo tick)
        juego.serpiente_cuerpo = [(2, 2), (2, 3), (1, 3), (1, 2)]
        juego.serpiente_direccion = (-1, 0)
        juego.ejecutar_evento('ON_TICK')
        self.assertFalse(juego.juego_terminado)
        self.assertEqual(juego.serpiente_cuerpo, [(1, 2), (2, 2), (2, 3), (1, 3)])

        juego = Snake(datos_snake())
        juego.serpiente_cuerpo = [(2, 2), (2, 3), (1, 3), (1, 2), (1, 1)]
        juego.serpiente_direccion = (-1, 0)
        juego.ejecutar_evento('ON_TICK')
        self.assertTrue(juego.juego_terminado, 'choque consigo misma')

        juego = Snake(datos_snake(inicio=(4, 2)))
        juego.ejecutar_evento('ON_TICK')
        self.assertTrue(juego.juego_terminado, 'choque con la pared')
        self.assertEqual(juego.serpiente_cuerpo, [(4, 2)])

    def test_comer(self):
        self.forzar_comida([(3, 2), (0, 4)])
        juego = Snake(datos_snake())
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.serpiente_cuerpo, [(3, 2), (2, 2)])
        self.assertEqual(juego.puntuacion, 10)
        self.assertEqual(juego.posicion_comida, (0, 4))

    def test_crecer_cantidad(self):
        # GROW PLAYER 3 crece 3 en total (1 al comer + 2 en los siguientes ticks)
        datos = datos_snake()
        datos['events']['ON_EAT_FOOD'] = [accion('GROW', 'PLAYER', ['3'])]
        juego = Snake(datos)
        juego.posicion_comida = (3, 2)
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(len(juego.serpiente_cuerpo), 2)
        juego.snake_cambiar_direccion('UP')
        juego.ejecutar_evento('ON_TICK')
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(len(juego.serpiente_cuerpo), 4)

        # Sin GROW en el .brick, comer no hace crecer
        datos = datos_snake()
        datos['events']['ON_EAT_FOOD'] = []
        juego = Snake(datos)
        juego.posicion_comida = (3, 2)
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.serpiente_cuerpo, [(3, 2)])

    def test_direccion(self):
        juego = Snake(datos_snake())
        juego.posicion_comida = (4, 4)   # lejos de la ruta, para no comer a mitad
        # No puede dar media vuelta (un giro por tick)
        for tecla, esperada in [('LEFT', (1, 0)), ('UP', (0, -1)), ('DOWN', (0, -1)),
                                ('LEFT', (-1, 0)), ('RIGHT', (-1, 0)), ('DOWN', (0, 1))]:
            juego.snake_cambiar_direccion(tecla)
            juego.ejecutar_evento('ON_TICK')
            self.assertEqual(juego.serpiente_direccion, esperada, tecla)
        # Teclas del teclado
        for tecla, esperada in [('Left', (-1, 0)), ('Up', (0, -1)), ('Right', (1, 0)),
                                ('Down', (0, 1)), ('a', (0, 1))]:
            juego.manejar_input_gui(EventoFalso(tecla))
            juego.ejecutar_evento('ON_TICK')
            self.assertEqual(juego.serpiente_direccion, esperada, tecla)

        # Los controles los define el .brick: sin ON_KEY_LEFT, Left no hace nada
        datos = datos_snake()
        del datos['events']['ON_KEY_LEFT']
        juego = Snake(datos)
        juego.manejar_input_gui(EventoFalso('Up'))
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.serpiente_direccion, (0, -1))
        juego.manejar_input_gui(EventoFalso('Left'))
        self.assertEqual(juego.serpiente_direccion, (0, -1))

    def test_doble_giro_rapido_no_mata(self):
        # Yendo a la derecha, ABAJO + IZQUIERDA antes del tick: antes el
        # segundo giro mataba contra el propio cuerpo; ahora solo vale el primero
        juego = Snake(datos_snake())
        juego.serpiente_cuerpo = [(3, 2), (2, 2), (1, 2)]
        juego.serpiente_direccion = (1, 0)
        juego.posicion_comida = (0, 0)
        juego.snake_cambiar_direccion('DOWN')
        juego.snake_cambiar_direccion('LEFT')
        juego.ejecutar_evento('ON_TICK')
        self.assertFalse(juego.juego_terminado)
        self.assertEqual(juego.serpiente_direccion, (0, 1))
        self.assertEqual(juego.serpiente_cuerpo[0], (3, 3))

    def test_dibujar_comida_y_serpiente(self):
        juego = Snake(datos_snake())
        juego.serpiente_cuerpo = [(2, 2), (1, 2)]
        juego.dibujar()
        self.assertEqual(juego.canvas.rectangulos, [
            ((0, 0, 25, 25), COLOR_FOOD),
            ((50, 50, 75, 75), COLOR_SNAKE_CABEZA),
            ((25, 50, 50, 75), COLOR_SNAKE_CUERPO),
        ])


if __name__ == '__main__':
    unittest.main()
