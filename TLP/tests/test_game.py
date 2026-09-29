# -*- coding: utf-8 -*-
# Tests de la clase base Game (lo comun a todos los juegos).

import unittest

from tests.tk_falso import EventoFalso
from engine.game import Game, COLOR_GRID_FIJA


class JuegoPrueba(Game):
    # Juego minimo para probar Game sin depender de Tetris ni Snake
    def inicializar_estado(self):
        self.llamadas = ['inicializar_estado']
        self.acciones = []
        self.velocidad_gravedad = 0.1

    def ejecutar_accion(self, verbo, objeto, accion):
        self.acciones.append((verbo, objeto))

    def dibujar_elementos(self):
        self.llamadas.append('dibujar_elementos')


def datos(eventos=None, grid=None):
    datos_juego = {'tipo_juego': 'PRUEBA', 'config': {}, 'shapes': {}, 'events': eventos or {}}
    if grid:
        datos_juego['config']['grid_size'] = grid
    return datos_juego


class TestGame(unittest.TestCase):

    def test_clase_abstracta(self):
        self.assertRaises(NotImplementedError, Game, datos())
        juego = JuegoPrueba(datos())
        self.assertRaises(NotImplementedError, Game.ejecutar_accion, juego, 'SPAWN', None, {})
        self.assertRaises(NotImplementedError, Game.dibujar_elementos, juego)

    def test_inicio(self):
        # Valores por defecto
        juego = JuegoPrueba(datos())
        self.assertEqual((juego.ancho, juego.alto), (10, 20))
        self.assertEqual(juego.grid, [[0] * 10 for _ in range(20)])
        self.assertEqual((juego.puntuacion, juego.frame, juego.timer_gravedad), (0, 0, 0))
        self.assertFalse(juego.juego_terminado)
        self.assertEqual(juego.timer_id, None)
        datos_juego = datos()
        del datos_juego['tipo_juego']
        self.assertEqual(JuegoPrueba(datos_juego).tipo_juego, 'TETRIS')

        # Grid desde config y ventana
        juego = JuegoPrueba(datos(grid=[4, 6]))
        self.assertEqual(juego.grid, [[0] * 4 for _ in range(6)])
        self.assertEqual(juego.root.titulo, 'BrickScript - PRUEBA')
        self.assertEqual(juego.root.protocolos['WM_DELETE_WINDOW'], juego.cerrar_ventana)
        self.assertEqual(juego.root.binds['<Key>'], juego.manejar_input_gui)
        self.assertEqual((juego.canvas.opciones['width'], juego.canvas.opciones['height']), (4 * 25, 6 * 25))

        # ON_START se ejecuta despues de inicializar_estado
        juego = JuegoPrueba(datos({'ON_START': [{'accion': 'SPAWN', 'objeto': 'X', 'params': []}]}))
        self.assertEqual(juego.acciones, [('SPAWN', 'X')])

    def test_eventos_y_teclas(self):
        eventos = {'ON_TICK': [{'accion': 'INCREASE_SCORE', 'objeto': '15', 'params': []},
                               {'accion': 'MOVE', 'objeto': 'PLAYER', 'params': []}],
                   'ON_FIN': [{'accion': 'GAME_OVER', 'objeto': None, 'params': []}]}
        juego = JuegoPrueba(datos(eventos))
        juego.ejecutar_evento('ON_NADA')
        self.assertEqual(juego.acciones, [])
        juego.ejecutar_evento('ON_TICK')
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.puntuacion, 30)
        # Todas las acciones pasan al juego, tambien las que resuelve Game
        self.assertEqual(juego.acciones, [('INCREASE_SCORE', '15'), ('MOVE', 'PLAYER')] * 2)
        juego.ejecutar_evento('ON_FIN')
        self.assertTrue(juego.juego_terminado)

        # Las flechas disparan ON_KEY_*; el resto de teclas se ignora
        juego = JuegoPrueba(datos({'ON_KEY_UP': [{'accion': 'MOVE', 'objeto': 'UP', 'params': []}]}))
        juego.manejar_input_gui(EventoFalso('Up'))
        juego.manejar_input_gui(EventoFalso('Down'))
        juego.manejar_input_gui(EventoFalso('a'))
        self.assertEqual(juego.acciones, [('MOVE', 'UP')])

    def test_loop(self):
        eventos = {'ON_TICK': [{'accion': 'INCREASE_SCORE', 'objeto': '1', 'params': []}]}
        juego = JuegoPrueba(datos(eventos))
        juego.run()
        self.assertEqual(juego.root.afters, [(50, juego.game_loop)])

        # El tick llega cuando se acumula la gravedad y el loop se reprograma
        juego.velocidad_gravedad = 0.15
        juego.game_loop()
        juego.game_loop()
        self.assertEqual(juego.puntuacion, 0)
        juego.game_loop()
        self.assertEqual(juego.puntuacion, 1)
        self.assertEqual(juego.timer_gravedad, 0)
        self.assertEqual(juego.root.afters[-1], (50, juego.game_loop))
        self.assertEqual(juego.timer_id, 'after#4')

        # Con game over no se reprograma y muestra la ventana final
        juego.juego_terminado = True
        juego.game_loop()
        self.assertEqual(len(juego.root.afters), 4)
        ventana = juego.root.hijos[-1]
        self.assertEqual(ventana.titulo, 'Game Over')
        self.assertIn('Puntuacion Final: 1', [hijo.opciones.get('text') for hijo in ventana.hijos])

        self.assertRaises(SystemExit, juego.cerrar_ventana)
        self.assertEqual(juego.root.cancelados, ['after#4'])
        self.assertTrue(juego.root.destruido)

    def test_dibujo(self):
        juego = JuegoPrueba(datos(grid=[3, 3]))
        juego.puntuacion = 42
        juego.grid[2][1] = 1
        juego.dibujar()
        juego.dibujar()   # borra el frame anterior: no duplica rectangulos
        self.assertEqual(juego.frame, 2)
        self.assertEqual(juego.label_score.opciones['text'], 'PUNTUACION\n42')
        self.assertIn('dibujar_elementos', juego.llamadas)
        self.assertEqual(juego.canvas.rectangulos, [((25, 50, 50, 75), COLOR_GRID_FIJA)])
        juego.dibujar_celda(2, 3, '#123456')
        self.assertEqual(juego.canvas.rectangulos[-1], ((50, 75, 75, 100), '#123456'))


if __name__ == '__main__':
    unittest.main()
