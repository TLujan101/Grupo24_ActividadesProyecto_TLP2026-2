# -*- coding: utf-8 -*-
# Tests del juego Snake.

import random
import unittest

from tests.tk_falso import EventoFalso
from engine.snake import Snake
from engine.utilidades import Colores


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

    def test_el_desvio_tras_una_nube_tampoco_reversa(self):
        juego = Snake(datos_snake())
        juego.puntuacion = 10
        juego.serpiente_cuerpo = [(2, 2), (3, 2)]
        juego.serpiente_direccion = (-1, 0)
        juego.nubes = [(1, 2)]
        juego.posicion_comida = (4, 4)
        juego.ejecutar_evento('ON_TICK')
        self.assertFalse(juego.juego_terminado)
        self.assertEqual(juego.serpiente_direccion, (0, 1))
        self.assertEqual(juego.serpiente_cuerpo[0], (2, 3))

    def test_posicion_libre_evita_veneno_y_powerup(self):
        # Antes solo se evitaban cuerpo, nubes y comida: el veneno y el
        # power-up podian aparecer encima de otros elementos.
        juego = Snake(datos_snake())
        juego.serpiente_cuerpo = [(2, 2)]
        juego.nubes = [(1, 1)]
        juego.posicion_comida = (3, 3)
        juego.posicion_veneno = (0, 4)
        juego.posicion_powerup = (4, 0)
        # El azar insiste en la casilla del veneno.
        valores = [0, 4] * 40
        random.randint = lambda a, b: valores.pop(0) if valores else (0, 4)
        pos = juego._obtener_posicion_libre()
        self.assertIsNotNone(pos)
        self.assertNotIn(pos, [(2, 2), (1, 1), (3, 3), (0, 4), (4, 0)])

    def test_posicion_libre_no_se_cuelga_si_el_azar_repite_una_ocupada(self):
        # Regresion: con random devolviendo siempre la casilla de la comida,
        # _obtener_posicion_libre entraba en un bucle infinito.
        juego = Snake(datos_snake())
        juego.serpiente_cuerpo = [(1, 1)]
        juego.nubes = [(2, 2)]
        juego.posicion_comida = (0, 0)
        random.randint = lambda a, b: 0
        pos = juego._obtener_posicion_libre()
        self.assertIsNotNone(pos)
        self.assertNotIn(pos, [(1, 1), (2, 2), (0, 0)])

    def test_la_comida_no_aparece_sobre_veneno_ni_powerup(self):
        juego = Snake(datos_snake())
        juego.serpiente_cuerpo = [(2, 2)]
        juego.nubes = [(1, 1)]
        juego.posicion_comida = None
        juego.posicion_veneno = (3, 2)
        juego.posicion_powerup = (4, 2)
        valores = [3, 2] * 40          # el azar insiste en el veneno
        random.randint = lambda a, b: valores.pop(0) if valores else (3, 2)
        juego.snake_spawn_comida()
        self.assertIsNotNone(juego.posicion_comida)
        self.assertNotIn(juego.posicion_comida, [(2, 2), (1, 1), (3, 2), (4, 2)])

    def test_la_comida_no_se_cuelga_si_el_azar_repite_una_ocupada(self):
        juego = Snake(datos_snake())
        juego.serpiente_cuerpo = [(0, 0), (1, 0)]
        juego.nubes = [(2, 2)]
        juego.posicion_comida = None
        random.randint = lambda a, b: 0   # siempre (0, 0), ocupada por el cuerpo
        juego.snake_spawn_comida()
        self.assertIsNotNone(juego.posicion_comida)
        self.assertNotEqual(juego.posicion_comida, (0, 0))

    def test_nube_redirige_y_resetea_puntos(self):
        # Chocar con una nube cuesta todos los puntos: la serpiente se desvia a
        # la primera direccion libre (derecha, abajo, izquierda, arriba) y avanza.
        juego = Snake(datos_snake())
        juego.puntuacion = 20
        juego.serpiente_cuerpo = [(2, 2)]
        juego.serpiente_direccion = (1, 0)
        juego.nubes = [(3, 2)]
        juego.posicion_comida = (4, 4)
        juego.ejecutar_evento('ON_TICK')
        self.assertFalse(juego.juego_terminado)
        self.assertEqual(juego.puntuacion, 0, 'la nube drena todos los puntos a 0')
        self.assertEqual(juego.serpiente_direccion, (0, 1))
        self.assertEqual(juego.serpiente_cuerpo[0], (2, 3),
                         'redirige y avanza en el mismo tick')

    def test_nube_con_cero_puntos_mata_inmediatamente(self):
        juego = Snake(datos_snake())
        juego.puntuacion = 0
        juego.serpiente_cuerpo = [(2, 2)]
        juego.serpiente_direccion = (1, 0)
        juego.nubes = [(3, 2)]
        juego.ejecutar_evento('ON_TICK')
        self.assertTrue(juego.juego_terminado, 'chocar contra nube con 0 puntos termina la partida')

    def test_nube_acorralada_mata(self):
        # Sin ninguna direccion libre alrededor, la nube mata.
        juego = Snake(datos_snake())
        juego.puntuacion = 10
        juego.serpiente_cuerpo = [(0, 0)]
        juego.serpiente_direccion = (1, 0)
        juego.nubes = [(1, 0), (0, 1)]
        juego.posicion_comida = (4, 4)
        juego.ejecutar_evento('ON_TICK')
        self.assertTrue(juego.juego_terminado)

    def test_invulnerable_envuelve_por_la_pared(self):
        # Con el power-up, salir por la derecha reaparece por la izquierda.
        juego = Snake(datos_snake())
        juego.serpiente_cuerpo = [(4, 2), (3, 2)]
        juego.serpiente_direccion = (1, 0)
        juego.tiempo_invulnerable = 5
        juego.posicion_comida = (0, 4)
        juego.ejecutar_evento('ON_TICK')
        self.assertFalse(juego.juego_terminado)
        self.assertEqual(juego.serpiente_direccion, (1, 0))
        self.assertEqual(juego.serpiente_cuerpo, [(0, 2), (4, 2)])

    def test_invulnerable_envuelve_por_la_pared_vertical(self):
        juego = Snake(datos_snake())
        juego.serpiente_cuerpo = [(2, 0), (2, 1)]
        juego.serpiente_direccion = (0, -1)
        juego.tiempo_invulnerable = 5
        juego.posicion_comida = (4, 4)
        juego.ejecutar_evento('ON_TICK')
        self.assertFalse(juego.juego_terminado)
        self.assertEqual(juego.serpiente_cuerpo, [(2, 4), (2, 0)])

    def test_invulnerable_atraviesa_las_nubes(self):
        juego = Snake(datos_snake())
        juego.serpiente_cuerpo = [(2, 2)]
        juego.serpiente_direccion = (1, 0)
        juego.nubes = [(3, 2)]
        juego.tiempo_invulnerable = 5
        juego.posicion_comida = (4, 4)
        juego.ejecutar_evento('ON_TICK')
        self.assertFalse(juego.juego_terminado)
        self.assertEqual(juego.serpiente_direccion, (1, 0),
                         'no debe desviarse')
        self.assertEqual(juego.serpiente_cuerpo[0], (3, 2))
        self.assertIn((3, 2), juego.nubes, 'la nube sigue ahi')

    def test_invulnerable_atraviesa_el_cuerpo(self):
        # Con el power-up la serpiente se puede pasar por encima de su propio
        # cuerpo: no redirige y no muere.
        juego = Snake(datos_snake())
        juego.serpiente_cuerpo = [(2, 2), (2, 3), (1, 3), (1, 2), (1, 1)]
        juego.serpiente_direccion = (-1, 0)
        juego.tiempo_invulnerable = 5
        juego.posicion_comida = (0, 0)
        juego.ejecutar_evento('ON_TICK')
        self.assertFalse(juego.juego_terminado)
        self.assertEqual(juego.serpiente_direccion, (-1, 0),
                         'no debe desviarse')
        self.assertEqual(juego.serpiente_cuerpo,
                         [(1, 2), (2, 2), (2, 3), (1, 3), (1, 2)])

    def test_tras_el_powerup_el_cuerpo_vuelve_a_ser_solido(self):
        juego = Snake(datos_snake())
        juego.serpiente_cuerpo = [(2, 2), (2, 3), (1, 3), (1, 2), (1, 1)]
        juego.serpiente_direccion = (-1, 0)
        juego.tiempo_invulnerable = 0
        juego.posicion_comida = (0, 0)
        juego.ejecutar_evento('ON_TICK')
        self.assertTrue(juego.juego_terminado)

    def test_invulnerable_acorralada_no_muere(self):
        # Con el power-up el borde envuelve: ya no se puede morir acorralada.
        juego = Snake(datos_snake())
        juego.serpiente_cuerpo = [(0, 0), (1, 0), (0, 1)]
        juego.crecimiento_pendiente = 1      # la cola aun no se libera
        juego.serpiente_direccion = (-1, 0)
        juego.tiempo_invulnerable = 5
        juego.posicion_comida = (4, 4)
        juego.ejecutar_evento('ON_TICK')
        self.assertFalse(juego.juego_terminado)
        self.assertEqual(juego.serpiente_cuerpo[0], (4, 0))

    def test_triangulos_apuntan_a_la_derecha_en_linea_recta(self):
        # En el nivel Entusiasta cada triangulo apunta hacia donde llego:
        # en una recta hacia la derecha, el vertice queda en el borde derecho.
        juego = Snake(datos_snake())
        juego.cargar_configuracion_nivel({'geometry': 'TRIANGLE'})
        juego.posicion_comida = None
        juego.serpiente_cuerpo = [(2, 2), (1, 2), (0, 2)]
        juego.serpiente_direccion = (1, 0)
        juego.dibujar()
        self.assertEqual([p for p, _ in juego.canvas.poligonos],
                         [[73, 62.5, 52, 52, 52, 73],
                          [48, 62.5, 27, 52, 27, 73],
                          [23, 62.5, 2, 52, 2, 73]])

    def test_triangulos_siguen_la_curva_del_cuerpo(self):
        # Cabeza a la derecha; el segmento doblado apunta hacia abajo porque
        # llego desde arriba, y la cola hereda esa direccion.
        juego = Snake(datos_snake())
        juego.cargar_configuracion_nivel({'geometry': 'TRIANGLE'})
        juego.posicion_comida = None
        juego.serpiente_cuerpo = [(3, 2), (2, 2), (2, 1)]
        juego.serpiente_direccion = (1, 0)
        juego.dibujar()
        self.assertEqual([p for p, _ in juego.canvas.poligonos],
                         [[98, 62.5, 77, 52, 77, 73],
                          [62.5, 73, 52, 52, 73, 52],
                          [62.5, 48, 52, 27, 73, 27]])

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
        # La serpiente sigue siendo de rectangulos en RECT; el primer rectangulo
        # ya no es la comida sino el tallo del icono de baya
        self.assertEqual([f for _, f in juego.canvas.rectangulos],
                         ['#4B2E0A',
                          Colores.get("DARK GREEN", "#2EB72E"),
                          Colores.get("GREEN", '#33CC33')])
        self.assertEqual(juego.canvas.rectangulos[1:],
                         [((50, 50, 75, 75), Colores.get("DARK GREEN", "#2EB72E")),
                          ((25, 50, 50, 75), Colores.get("GREEN", '#33CC33'))])

    def test_dibujar_comida_es_el_icono_de_baya(self):
        # La baya normal usa el MISMO icono que la venenosa, solo cambia el color
        juego = Snake(datos_snake())
        juego.dibujar()
        rellenos_rect = [f for _, f in juego.canvas.rectangulos]
        rellenos_oval = [f for _, f in juego.canvas.ovales]
        self.assertIn(Colores.get("RED", '#FF0000'), rellenos_oval,
                      'la baya se dibuja como ovalo')
        self.assertNotIn(Colores.get("RED", '#FF0000'), rellenos_rect,
                         'ya no es un rectangulo plano')
        self.assertEqual([f for _, f in juego.canvas.poligonos],
                         [Colores.get("GREEN", '#00FF00')],
                         'lleva la hoja del icono de veneno')

    def test_veneno_termina_la_partida_si_el_nivel_lo_pide(self):
        datos = datos_snake()
        datos['events']['ON_EAT_POISON'] = [accion('DECREASE_SCORE', '5')]
        juego = Snake(datos)
        juego.puntuacion = 10
        self.forzar_comida([(4, 4), (1, 4)])
        juego.cargar_configuracion_nivel({'poison_enabled': True, 'poison_kills': True})
        juego.posicion_veneno = (3, 2)
        juego.ejecutar_evento('ON_TICK')
        self.assertTrue(juego.juego_terminado, 'POISON_KILLS TRUE termina la partida')
        self.assertEqual(juego.puntuacion, 5, 'el evento global ON EAT_POISON tambien corre')

    def test_el_veneno_reaparece_donde_lo_dice_el_evento(self):
        # ON EAT_POISON trae SPAWN POISON AT RANDOM: el motor no debe pisarlo
        # con su propio respawn (y con random determinista, eso bucleaba).
        datos = datos_snake()
        datos['events']['ON_EAT_POISON'] = [accion('SPAWN', 'POISON', ['RANDOM'])]
        juego = Snake(datos)
        juego.posicion_comida = (1, 1)          # deja (0, 0) libre
        juego.posicion_veneno = (3, 2)
        self.forzar_comida([(0, 0), (4, 4)])    # evento -> (0,0); motor -> (4,4)
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.posicion_veneno, (0, 0),
                         'el motor piso el SPAWN POISON del evento')

    def test_el_powerup_reaparece_donde_lo_dice_el_evento(self):
        datos = datos_snake()
        datos['events']['ON_EAT_POWERUP'] = [accion('SPAWN', 'POWERUP', ['RANDOM'])]
        juego = Snake(datos)
        juego.posicion_comida = (1, 1)
        juego.posicion_powerup = (3, 2)
        self.forzar_comida([(0, 0), (4, 4)])
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.posicion_powerup, (0, 0),
                         'el motor piso el SPAWN POWERUP del evento')

    def test_el_powerup_se_dibuja_como_baya_amarilla(self):
        # El power-up usa el mismo icono de baya, pero en amarillo
        juego = Snake(datos_snake())
        juego.posicion_powerup = (4, 4)
        juego.dibujar()
        amarillo = Colores.get("YELLOW", '#FFD700')
        self.assertIn(amarillo, [f for _, f in juego.canvas.ovales])
        self.assertNotIn(amarillo, [f for _, f in juego.canvas.rectangulos])

    def test_el_parpadeo_acelera_cuando_se_acaba(self):
        juego = Snake(datos_snake())
        juego.tiempo_invulnerable_total = 10
        juego.tiempo_invulnerable = 10
        self.assertEqual(juego.intervalo_parpadeo(), 6, '300 ms con tiempo de sobra')
        juego.tiempo_invulnerable = 5
        self.assertEqual(juego.intervalo_parpadeo(), 3)
        juego.tiempo_invulnerable = 0.2
        self.assertEqual(juego.intervalo_parpadeo(), 1, '50 ms cuando casi se acaba')

    def test_cabeza_parpadea_amarillo_con_invulnerabilidad(self):
        juego = Snake(datos_snake())
        juego.serpiente_cuerpo = [(2, 2)]
        juego.tiempo_invulnerable = 5
        juego.tiempo_invulnerable_total = 10
        juego.frame_counter = 0
        juego.dibujar()
        self.assertEqual(juego.canvas.rectangulos[-1][1], Colores.get("YELLOW", '#FFFF00'),
                         'la cabeza parpadea en amarillo')
        juego.frame_counter = juego.intervalo_parpadeo()
        juego.dibujar()
        self.assertEqual(juego.canvas.rectangulos[-1][1], Colores.get("DARK GREEN", "#2EB72E"),
                         'en el frame siguiente vuelve a su color normal')

    def test_cola_nyan_primer_frame_usa_degradado_en_orden(self):
        # En el primer frame la cabeza es blanca y la cola va en orden:
        # rojo, naranja, verde, azul, morado, ciclando cada 5 segmentos.
        juego = Snake(datos_snake())
        juego.cargar_configuracion_nivel({'geometry': 'NYAN_CAT'})
        juego.nubes = []
        juego.posicion_comida = None
        juego.posicion_veneno = None
        juego.posicion_powerup = None
        juego.serpiente_cuerpo = [(0, i) for i in range(7)]
        juego.frame_counter = 0    # el primer dibujar() es el frame 1 (offset 0)
        juego.dibujar()
        colores = [color for _, color in juego.canvas.ovales]
        self.assertEqual(colores, [
            Colores.get("WHITE", "#FFFFFF"),
            '#FF0000', '#FF7F00', '#00FF00', '#0000FF', '#AA00FF',
            '#FF0000',
        ])

    def test_cabeza_nyan_dibuja_circulo_con_rasgos_de_gato(self):
        juego = Snake(datos_snake())
        juego.cargar_configuracion_nivel({'geometry': 'NYAN_CAT'})
        juego.nubes = []
        juego.posicion_comida = None
        juego.serpiente_cuerpo = [(2, 2)]
        juego.dibujar()

        # Debe tener exactamente un circulo base blanco
        self.assertEqual(len(juego.canvas.ovales), 1)
        self.assertEqual(juego.canvas.ovales[0][1], Colores.get("WHITE", "#FFFFFF"))

        # Debe tener poligonos correspondientes a las orejitas
        self.assertGreaterEqual(len(juego.canvas.poligonos), 2)

        # Debe tener rectangulos correspondientes a los ojos, mejillas y nariz
        self.assertGreaterEqual(len(juego.canvas.rectangulos), 4)

    def test_cabeza_nyan_orienta_segun_direccion(self):
        # Al cambiar la direccion, los vertices de las orejitas rotan con ella.
        juego = Snake(datos_snake())
        juego.cargar_configuracion_nivel({'geometry': 'NYAN_CAT'})
        juego.posicion_comida = None       # la baya tambien es un ovalo
        juego.serpiente_cuerpo = [(2, 2)]
        juego.serpiente_direccion = (0, -1)  # ARRIBA
        juego.dibujar()
        poligonos_up = list(juego.canvas.poligonos)
        ovales_up = list(juego.canvas.ovales)

        juego.serpiente_direccion = (1, 0)   # DERECHA
        juego.dibujar()
        poligonos_right = list(juego.canvas.poligonos)

        self.assertNotEqual(poligonos_up, poligonos_right,
                            'los vertices de las orejas deben rotar con la direccion')
        # Sigue siendo un unico ovalo en cualquier orientacion
        self.assertEqual(len(juego.canvas.ovales), 1)
        self.assertEqual(juego.canvas.ovales, ovales_up)

    def test_la_cola_nyan_fluye_dinamicamente_con_los_frames(self):
        # La cola arcoiris fluye, pero a paso lento (un paso cada 3 frames):
        # dentro de un mismo paso no cambia, y pasado el paso si.
        juego = Snake(datos_snake())
        juego.cargar_configuracion_nivel({'geometry': 'NYAN_CAT'})
        juego.nubes = []
        juego.posicion_comida = None
        juego.posicion_veneno = None
        juego.posicion_powerup = None
        juego.serpiente_cuerpo = [(0, i) for i in range(5)]
        juego.dibujar()                       # frame 1
        frame1 = [color for _, color in juego.canvas.ovales]
        juego.dibujar()                       # frame 2: mismo paso
        frame2 = [color for _, color in juego.canvas.ovales]
        juego.dibujar()                       # frame 3: mismo paso
        juego.dibujar()                       # frame 4: siguiente paso
        frame4 = [color for _, color in juego.canvas.ovales]
        self.assertEqual(frame1, frame2, 'no parpadea dentro del mismo paso')
        # La cabeza sigue blanca, pero la cola fluyo
        self.assertEqual(frame1[0], frame4[0])
        self.assertNotEqual(frame1[1:], frame4[1:],
                            'los colores de la cola deben fluir con los frames')

    def test_veneno_se_despeja_estando_invulnerable(self):
        datos = datos_snake()
        datos['events']['ON_EAT_POISON'] = [accion('DECREASE_SCORE', '5')]
        juego = Snake(datos)
        juego.puntuacion = 10
        self.forzar_comida([(4, 4), (1, 4)])   # celdas libres para el veneno
        juego.cargar_configuracion_nivel({'poison_enabled': True, 'poison_kills': True})
        juego.posicion_veneno = (3, 2)
        juego.tiempo_invulnerable = 3
        juego.ejecutar_evento('ON_TICK')
        self.assertFalse(juego.juego_terminado)
        self.assertEqual(juego.puntuacion, 10, 'no resta puntos')
        self.assertNotEqual(juego.posicion_veneno, (3, 2), 'la baya se consume y reposiciona')

    def test_veneno_sin_poison_kills_no_mata(self):
        datos = datos_snake()
        datos['events']['ON_EAT_POISON'] = [accion('DECREASE_SCORE', '5')]
        juego = Snake(datos)
        juego.puntuacion = 10
        self.forzar_comida([(4, 4), (1, 4)])
        juego.cargar_configuracion_nivel({'poison_enabled': True})
        juego.posicion_veneno = (3, 2)
        juego.ejecutar_evento('ON_TICK')
        self.assertFalse(juego.juego_terminado, 'sin el modificador el veneno solo resta puntos')
        self.assertEqual(juego.puntuacion, 5)

    def test_poison_kills_se_relee_al_cambiar_de_nivel(self):
        datos = datos_snake()
        datos['config']['start_level'] = 'BABY'
        datos['levels'] = [{'nombre': 'BABY'}, {'nombre': 'NYAN_CAT', 'poison_kills': True}]
        juego = Snake(datos)
        self.assertFalse(getattr(juego, 'veneno_mata', False))
        juego.elegir_nivel(1)
        self.assertTrue(juego.veneno_mata, 'NYAN_CAT declara POISON_KILLS TRUE')
        juego.elegir_nivel(0)
        self.assertFalse(juego.veneno_mata, 'volver a BABY debe apagarlo')

    def test_invulnerabilidad_toma_la_duracion_del_nivel(self):
        # El evento es global y dice 10, pero el nivel manda (NYAN_CAT: 15)
        juego = Snake(datos_snake())
        self.forzar_comida([(4, 4)])   # celda libre para el power-up
        juego.cargar_configuracion_nivel({'invulnerability_duration': 15})
        juego.conceder_invulnerabilidad(10)
        self.assertEqual(juego.tiempo_invulnerable, 15)

    def test_invulnerabilidad_sin_duracion_del_nivel_usa_la_del_evento(self):
        # Un nivel sin INVULNERABILITY_DURATION (BABY) no pisa el 10 del evento
        juego = Snake(datos_snake())
        self.forzar_comida([(4, 4)])   # celda libre para el veneno
        juego.cargar_configuracion_nivel({'poison_enabled': True})
        juego.conceder_invulnerabilidad(10)
        self.assertEqual(juego.tiempo_invulnerable, 10)

    def test_invulnerabilidad_dura_segundos_no_ticks(self):
        datos = datos_snake()
        juego = Snake(datos)                     # 0.15 s por tick -> 3 s = 20 ticks
        juego.posicion_comida = None             # aqui solo importa el cronometro
        juego.conceder_invulnerabilidad(3)
        for _ in range(19):                      # 19 ticks = 2.85 s
            juego.snake_mover_jugador()
        self.assertFalse(juego.juego_terminado,
                         'a los 19 ticks (2.85 s) sigue dentro de los 3 s')
        self.assertGreater(juego.tiempo_invulnerable, 0)
        for _ in range(2):                       # 21 ticks: ya paso de 3 s
            juego.snake_mover_jugador()
        self.assertLessEqual(juego.tiempo_invulnerable, 0,
                             'la duracion es en segundos, no en ticks')

        # Ya sin el power-up, la pared vuelve a matar.
        juego.serpiente_cuerpo = [(4, 2)]
        juego.serpiente_direccion = (1, 0)
        juego.snake_mover_jugador()
        self.assertTrue(juego.juego_terminado,
                        'pasados los 3 s la pared vuelve a matar')

    def test_nyan_cat_colision_pared_gasta_puntos_y_salva(self):
        juego = Snake(datos_snake(inicio=(4, 2)))
        juego.cargar_configuracion_nivel({'geometry': 'NYAN_CAT'})
        juego.puntuacion = 30
        juego.ejecutar_evento('ON_TICK')
        self.assertFalse(juego.juego_terminado, 'con puntos, Nyan Cat no muere contra la pared')
        self.assertEqual(juego.puntuacion, 0, 'pierde todos los puntos como penalizacion')
        self.assertEqual(juego.serpiente_cuerpo[0], (0, 2), 'hace wrap-around al otro lado')

    def test_nyan_cat_colision_pared_con_cero_puntos_muere(self):
        juego = Snake(datos_snake(inicio=(4, 2)))
        juego.cargar_configuracion_nivel({'geometry': 'NYAN_CAT'})
        juego.puntuacion = 0
        juego.ejecutar_evento('ON_TICK')
        self.assertTrue(juego.juego_terminado, 'con 0 puntos, la pared es mortal')

    def test_nyan_cat_colision_cuerpo_gasta_puntos_y_salva(self):
        juego = Snake(datos_snake())
        juego.cargar_configuracion_nivel({'geometry': 'NYAN_CAT'})
        juego.puntuacion = 50
        juego.serpiente_cuerpo = [(2, 2), (2, 3), (1, 3), (1, 2), (1, 1)]
        juego.serpiente_direccion = (-1, 0)
        juego.ejecutar_evento('ON_TICK')
        self.assertFalse(juego.juego_terminado, 'con puntos sobrevive a la auto-colision')
        self.assertEqual(juego.puntuacion, 0)

    def test_powerup_cooldown_reaparicion(self):
        juego = Snake(datos_snake())
        juego.cargar_configuracion_nivel({'invulnerability_duration': 5})
        juego.serpiente_cuerpo = [(2, 2)]
        juego.serpiente_direccion = (1, 0)
        juego.posicion_powerup = (3, 2)
        juego.posicion_comida = (0, 0)
        juego.ejecutar_evento('ON_TICK')
        self.assertIsNone(juego.posicion_powerup, 'al comerlo queda en cooldown y no reaparece al instante')
        self.assertGreater(juego.cooldown_powerup, 0)

    def test_powerup_reaparece_al_acabar_el_cooldown(self):
        juego = Snake(datos_snake())
        juego.cargar_configuracion_nivel({'invulnerability_duration': 5})
        juego.posicion_powerup = None
        juego.cooldown_powerup = 0.1
        juego.posicion_comida = (0, 0)
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.cooldown_powerup, 0)
        self.assertIsNotNone(juego.posicion_powerup)

    def test_tick_del_nivel(self):
        # snake.py no cambia: el nivel pisa el 0.15 que Snake deja en
        # inicializar_estado()
        datos = datos_snake()
        datos['config']['start_level'] = 'NYAN_CAT'
        datos['levels'] = [{'nombre': 'BABY'}, {'nombre': 'NYAN_CAT', 'tick': 0.06}]
        self.assertEqual(Snake(datos).velocidad_gravedad, 0.06)

        # Sin declararlo, Snake conserva su 0.15
        self.assertEqual(Snake(datos_snake()).velocidad_gravedad, 0.15)


if __name__ == '__main__':
    unittest.main()
