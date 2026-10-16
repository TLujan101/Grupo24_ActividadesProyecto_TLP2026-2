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


def datos_niveles(niveles, inicio='BABY', eventos=None):
    datos_juego = datos(eventos)
    datos_juego['config']['start_level'] = inicio
    datos_juego['levels'] = niveles
    return datos_juego


NIVELES_TRES = [{'nombre': 'BABY', 'tick': 0.15},
                {'nombre': 'ENTUSIASTA', 'tick': 0.1},
                {'nombre': 'NYAN_CAT', 'tick': 0.06}]


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


class TestNiveles(unittest.TestCase):

    def test_estado_del_nivel_activo(self):
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'NYAN_CAT'))
        self.assertEqual(juego.nivel_actual, 'NYAN_CAT')
        self.assertEqual(juego.nivel_config['tick'], 0.06)
        # Con 3 niveles hay algo que preguntar: la partida NO arranca sola.
        # El tick si se aplico ya (ver test_ticket_del_nivel...).
        self.assertFalse(juego.iniciado)

    def test_un_solo_nivel_arranca_solo(self):
        # El .brick clasico declara un solo nivel: nada que preguntar, asi que
        # la partida arranca en __init__ como siempre.
        juego = JuegoPrueba(datos_niveles([{'nombre': 'BABY', 'tick': 0.15}], 'BABY'))
        self.assertTrue(juego.iniciado)
        self.assertEqual(juego.velocidad_gravedad, 0.15)

    def test_ticket_del_nivel_pisa_el_default_del_juego(self):
        # JuegoPrueba deja velocidad_gravedad = 0.1 (test_game.py:26)
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'NYAN_CAT'))
        self.assertEqual(juego.velocidad_gravedad, 0.06)

    def test_nivel_sin_tick_no_toca_el_default(self):
        # El default lo aporta el juego (Tetris 0.4, Snake 0.15), no el nivel
        juego = JuegoPrueba(datos_niveles([{'nombre': 'BABY'}], 'BABY'))
        self.assertEqual(juego.velocidad_gravedad, 0.1)

    def test_config_de_nivel(self):
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'ENTUSIASTA'))
        self.assertEqual(juego.config_de_nivel('BABY')['tick'], 0.15)
        self.assertEqual(juego.config_de_nivel('NO_EXISTE'), {})

    def test_json_sin_levels_no_revienta(self):
        # games/tetris.json y games/tetris_reborn.json fueron compilados por la
        # version anterior del compilador y no tienen la clave. Tambien
        # tests/test_juegos.py:31 fabrica juegos a mano.
        juego = JuegoPrueba(datos())            # sin 'levels' ni 'start_level'
        self.assertEqual(juego.niveles, [])
        self.assertEqual(juego.nivel_actual, Game.NIVEL_POR_DEFECTO)
        self.assertEqual(juego.nivel_config, {})
        self.assertEqual(juego.velocidad_gravedad, 0.1)
        self.assertTrue(juego.iniciado)

    def test_nivel_inicial_inexistente_cae_a_vacio(self):
        # Un start_level que no esta en la lista no debe romper el arranque
        juego = JuegoPrueba(datos_niveles([{'nombre': 'BABY'}], 'FANTASMA'))
        self.assertEqual(juego.nivel_config, {})
        self.assertEqual(juego.velocidad_gravedad, 0.1)


class TestMenuNiveles(unittest.TestCase):

    def test_sin_menu_no_hay_botones(self):
        # Un solo nivel: nada que elegir, el juego arranca solo como siempre
        juego = JuegoPrueba(datos_niveles([{'nombre': 'BABY', 'tick': 0.15}], 'BABY'))
        self.assertTrue(juego.iniciado)
        juego.run()
        self.assertEqual(juego.root.afters, [(50, juego.game_loop)])
        self.assertEqual(juego.botones_nivel, [])

    def test_menu_crea_un_boton_por_nivel_en_orden(self):
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'NYAN_CAT'))
        self.assertFalse(juego.iniciado)          # la partida no arranca sola
        juego.run()
        # El loop espera a la eleccion
        self.assertEqual(juego.root.afters, [])
        self.assertEqual([b.opciones['text'] for b in juego.botones_nivel],
                         ['1. Baby', '2. Entusiasta', '3. Nyan Cat'])

    def test_etiqueta_sale_del_identificador(self):
        # El motor no tiene una tabla de nombres: traduce el identificador.
        # NYAN_CAT -> 'Nyan Cat', sin tocar el .brick.
        self.assertEqual(Game.etiqueta_nivel('NYAN_CAT'), 'Nyan Cat')
        self.assertEqual(Game.etiqueta_nivel('BABY'), 'Baby')
        self.assertEqual(Game.etiqueta_nivel('ENTUSIASTA'), 'Entusiasta')

    def test_tecla_elige_nivel_y_arranca(self):
        eventos = {'ON_START': [{'accion': 'SPAWN', 'objeto': 'X', 'params': []}]}
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'BABY', eventos))
        juego.run()
        juego.manejar_input_gui(EventoFalso('3'))   # la tercera tecla = NYAN_CAT
        self.assertEqual(juego.nivel_actual, 'NYAN_CAT')
        self.assertEqual(juego.velocidad_gravedad, 0.06)
        self.assertEqual(juego.acciones, [('SPAWN', 'X')])   # ON_START corrio
        self.assertTrue(juego.iniciado)
        self.assertEqual(juego.root.afters[-1], (50, juego.game_loop))

    def test_click_elige_nivel_igual_que_la_tecla(self):
        # El command del boton y la tecla llaman a la misma funcion
        eventos = {'ON_START': [{'accion': 'SPAWN', 'objeto': 'X', 'params': []}]}
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'BABY', eventos))
        juego.run()
        juego.botones_nivel[1].opciones['command']()   # clic en '2. Entusiasta'
        self.assertEqual(juego.nivel_actual, 'ENTUSIASTA')
        self.assertEqual(juego.velocidad_gravedad, 0.1)
        self.assertEqual(juego.acciones, [('SPAWN', 'X')])
        self.assertTrue(juego.iniciado)
        self.assertEqual(juego.root.afters[-1], (50, juego.game_loop))

    def test_al_elegir_los_botones_desaparecen(self):
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'BABY'))
        juego.run()
        # Guardar los widgets ANTES de elegir: elegir_nivel() vacia
        # self.botones_nivel, asi que afirmar sobre la lista despues seria
        # afirmar sobre [] y all() de [] es True vacuamente.
        botones = list(juego.botones_nivel)
        self.assertEqual(len(botones), 3)
        self.assertFalse(any(b.destruido for b in botones))
        juego.manejar_input_gui(EventoFalso('1'))
        self.assertTrue(all(b.destruido for b in botones))
        self.assertEqual(juego.botones_nivel, [])

    def test_al_elegir_tambien_desaparece_el_rotulo(self):
        # El spec 6.5 pide destruir el titulo tambien: si se queda, el texto
        # 'ELIGE NIVEL' flota sobre la partida empezada.
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'BABY'))
        juego.run()
        rotulo = juego._rotulo_nivel
        self.assertIsNotNone(rotulo)
        self.assertEqual(rotulo.opciones['text'], 'ELIGE NIVEL')
        self.assertFalse(rotulo.destruido)
        juego.manejar_input_gui(EventoFalso('1'))
        self.assertTrue(rotulo.destruido)
        self.assertIsNone(juego._rotulo_nivel)

    def test_el_menu_se_arma_en_el_panel_lateral(self):
        # El menu va en marco_score, el panel que ya existe: sin ventana nueva.
        # Si se colgara de self.root, este test lo nota.
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'BABY'))
        juego.run()
        for widget in [juego._rotulo_nivel] + list(juego.botones_nivel):
            self.assertIs(widget.master, juego.marco_score)
        # Y ninguno cuelga de la ventana principal
        for hijo in juego.root.hijos:
            self.assertIsNot(hijo, juego._rotulo_nivel)
            self.assertNotIn(hijo, juego.botones_nivel)

    def test_con_el_menu_abierto_solo_sirven_los_digitos(self):
        eventos = {'ON_KEY_UP': [{'accion': 'MOVE', 'objeto': 'UP', 'params': []}]}
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'BABY', eventos))
        juego.run()
        juego.manejar_input_gui(EventoFalso('Up'))       # no debe filtrarse
        juego.manejar_input_gui(EventoFalso('7'))        # fuera de rango
        juego.manejar_input_gui(EventoFalso('a'))
        self.assertFalse(juego.iniciado)
        self.assertEqual(juego.acciones, [])
        self.assertEqual(juego.root.afters, [])

    def test_despues_de_elegir_las_flechas_vuelven_a_funcionar(self):
        eventos = {'ON_KEY_UP': [{'accion': 'MOVE', 'objeto': 'UP', 'params': []}]}
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'BABY', eventos))
        juego.run()
        juego.manejar_input_gui(EventoFalso('1'))
        juego.manejar_input_gui(EventoFalso('Up'))
        self.assertEqual(juego.acciones, [('MOVE', 'UP')])


if __name__ == '__main__':
    unittest.main()
