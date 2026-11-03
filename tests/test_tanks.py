# -*- coding: utf-8 -*-
# Tests del juego Tanks (GAME_TYPE TANKS): el .brick real y el motor
# (jugador, balas, enemigos, muros y martillo).

import os
import random
import unittest

import compiler
from engine import crear_juego
from engine.tanks import Tanks
from engine.utilidades import Colores

CARPETA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def accion(verbo, objeto=None, params=None):
    return {'accion': verbo, 'objeto': objeto, 'params': params or []}


class TestBrickTanks(unittest.TestCase):

    def compilar(self):
        with open(os.path.join(CARPETA_RAIZ, 'games', 'tanks.brick')) as f:
            return compiler.Parser(compiler.lexer(f.read())).parse()

    def test_declara_el_juego_y_las_formas(self):
        datos = self.compilar()
        self.assertEqual(datos['tipo_juego'], 'TANKS')
        self.assertEqual(datos['config']['grid_size'], [15, 15])
        self.assertEqual(datos['shapes']['JUGADOR']['type'], 'PLAYER')
        self.assertEqual(datos['shapes']['JUGADOR']['hp'], 3)
        self.assertEqual(datos['shapes']['ENEMIGO_RAPIDO']['speed'], 4)
        self.assertEqual(datos['shapes']['BALA_JUGADOR']['owner'], 'PLAYER')
        self.assertEqual(datos['shapes']['BALA_ENEMIGA']['owner'], 'ENEMY')
        self.assertEqual(datos['shapes']['MURO']['type'], 'WALL')
        self.assertEqual(datos['shapes']['MARTILLO']['heal'], 1)

    def test_niveles_y_muros(self):
        datos = self.compilar()
        self.assertEqual([n['nombre'] for n in datos['levels']], ['PATRULLA', 'ASEDIO'])
        self.assertEqual(datos['config']['start_level'], 'PATRULLA')
        self.assertEqual([n.get('walls') for n in datos['levels']], [6, 10])

    def test_audio_y_eventos(self):
        datos = self.compilar()
        self.assertIn('TANK_TEMA', datos['songs'])
        for efecto in ('DISPARO', 'IMPACTO', 'MORIR'):
            self.assertIn(efecto, datos['effects'])
        for evento in ('ON_START', 'ON_KEY_SHOOT', 'ON_ENEMY_DEFEATED',
                       'ON_EAT_HAMMER', 'ON_BULLET_HIT_WALL', 'ON_GAME_OVER'):
            self.assertIn(evento, datos['events'])

    def test_el_registro_crea_la_clase(self):
        self.assertIsInstance(crear_juego(self.compilar()), Tanks)


def datos_tanks(inicio=(2, 4)):
    # Tablero 8x8 y eventos equivalentes a games/tanks.brick, en pequeño.
    eventos = {
        'ON_START': [accion('SPAWN', 'JUGADOR', [list(inicio)] if inicio else [])],
        'ON_KEY_UP': [accion('MOVE', 'PLAYER', ['UP'])],
        'ON_KEY_DOWN': [accion('MOVE', 'PLAYER', ['DOWN'])],
        'ON_KEY_LEFT': [accion('MOVE', 'PLAYER', ['LEFT'])],
        'ON_KEY_RIGHT': [accion('MOVE', 'PLAYER', ['RIGHT'])],
        'ON_KEY_SHOOT': [accion('SHOOT', 'PLAYER')],
        'ON_ENEMY_DEFEATED': [accion('INCREASE_SCORE', '100'),
                              accion('SPAWN', 'ENEMIGO', ['RANDOM'])],
        'ON_EAT_HAMMER': [accion('HEAL', 'PLAYER')],
        'ON_PLAYER_HIT': [accion('INCREASE_SCORE', '1')],
        'ON_BULLET_HIT_WALL': [accion('INCREASE_SCORE', '7')],
        'ON_GAME_OVER': [accion('INCREASE_SCORE', '1')],
    }
    return {
        'tipo_juego': 'TANKS',
        'config': {'grid_size': [8, 8]},
        'shapes': {
            'JUGADOR': {'type': 'PLAYER', 'hp': 3, 'color': 'GREEN',
                        'estados': [[[0, 1, 0], [1, 1, 1], [0, 1, 0]]]},
            'ENEMIGO': {'type': 'ENEMY', 'hp': 1, 'speed': 2, 'fire_rate': 3,
                        'color': 'RED', 'estados': [[[1]]]},
            'BALA_JUGADOR': {'type': 'BULLET', 'owner': 'PLAYER', 'damage': 1,
                             'color': 'CYAN', 'estados': [[[1]]]},
            'BALA_ENEMIGA': {'type': 'BULLET', 'owner': 'ENEMY', 'damage': 1,
                             'color': 'YELLOW', 'estados': [[[1]]]},
            'MURO': {'type': 'WALL', 'color': 'GRAY', 'estados': [[[1]]]},
            'MARTILLO': {'type': 'PICKUP', 'heal': 1, 'color': 'YELLOW',
                         'estados': [[[1]]]},
        },
        'events': eventos,
    }


def agregar_enemigo(juego, x, y, direccion=(1, 0), hp=1, nombre='ENEMIGO'):
    juego.enemigos.append({'nombre': nombre, 'x': x, 'y': y, 'hp': hp, 'max_hp': hp,
                           'direccion': direccion,
                           'tiempo_movimiento': 0.0, 'tiempo_disparo': 0.0})
    return juego.enemigos[-1]


class TestTanks(unittest.TestCase):

    def setUp(self):
        random.seed(1234)

    def test_spawn_jugador_teclas_y_hp(self):
        juego = Tanks(datos_tanks())
        self.assertEqual(juego.jugador['hp'], 3)
        self.assertEqual(juego.jugador['max_hp'], 3)
        self.assertEqual((juego.jugador['x'], juego.jugador['y']), (2, 4))
        self.assertEqual(juego.jugador['orientacion'], (0, -1))
        juego.dibujar()
        self.assertEqual(juego.label_vida.opciones['text'], 'VIDA 3/3')
        self.assertEqual(len(juego.canvas.rectangulos), 5)      # la cruz del jugador
        self.assertEqual(set(c[1] for c in juego.canvas.rectangulos),
                         set([Colores['GREEN']]))

        juego.manejar_tecla('RIGHT')
        self.assertEqual(juego.jugador['orientacion'], (1, 0))
        self.assertEqual((juego.jugador['x'], juego.jugador['y']), (3, 4))

    def test_disparo_avanza_y_respeta_cooldown(self):
        juego = Tanks(datos_tanks())
        juego.jugador['orientacion'] = (1, 0)
        juego.manejar_tecla('SPACE')
        self.assertEqual(len(juego.balas), 1)
        bala = juego.balas[0]
        self.assertEqual((bala['x'], bala['y'], bala['dx'], bala['dy']), (5, 5, 1, 0))
        self.assertEqual(bala['dueno'], 'PLAYER')
        self.assertEqual((bala['dano'], bala['color']), (1, Colores['CYAN']))
        self.assertEqual(juego.jugador['cooldown'], 0.3)

        juego.manejar_tecla('SPACE')          # cooldown activo: no sale otra
        self.assertEqual(len(juego.balas), 1)

        juego.ejecutar_evento('ON_TICK')      # la bala avanza sola
        self.assertEqual((juego.balas[0]['x'], juego.balas[0]['y']), (6, 5))

    def test_el_jugador_no_atraviesa_muros_ni_bordes(self):
        juego = Tanks(datos_tanks())
        juego.grid[5][5] = 1                  # (5,5) esta en la huella del paso a la derecha
        juego.manejar_tecla('RIGHT')
        self.assertEqual(juego.jugador['x'], 2)
        self.assertEqual(juego.jugador['orientacion'], (1, 0))   # igual apunta

        juego.jugador['x'] = 6                # pegado al borde derecho (8 columnas)
        juego.manejar_tecla('RIGHT')
        self.assertEqual(juego.jugador['x'], 6)

    def test_la_bala_destruye_el_muro(self):
        juego = Tanks(datos_tanks())
        juego.jugador['orientacion'] = (1, 0)
        juego.grid[5][6] = 1
        juego.manejar_tecla('SPACE')
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.balas, [])
        self.assertEqual(juego.grid[5][6], 0)
        self.assertEqual(juego.puntuacion, 7)          # ON_BULLET_HIT_WALL corrio

    def test_bala_del_jugador_dana_y_mata(self):
        juego = Tanks(datos_tanks())
        juego.jugador['orientacion'] = (1, 0)
        enemigo = agregar_enemigo(juego, 6, 5, hp=2)
        juego.manejar_tecla('SPACE')
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(enemigo['hp'], 1)
        self.assertEqual(juego.balas, [])
        self.assertIn(enemigo, juego.enemigos)

        juego.jugador['cooldown'] = 0
        juego.manejar_tecla('SPACE')
        juego.ejecutar_evento('ON_TICK')
        self.assertNotIn(enemigo, juego.enemigos)
        self.assertEqual(juego.puntuacion, 100)        # ON_ENEMY_DEFEATED
        self.assertEqual(len(juego.enemigos), 1)       # el .brick lo respawneo

    def test_bala_enemiga_baja_la_vida_y_termina(self):
        juego = Tanks(datos_tanks())
        bala = {'x': 3, 'y': 7, 'dx': 0, 'dy': -1, 'dueno': 'ENEMY',
                'dano': 1, 'color': Colores['YELLOW']}
        juego.balas = [dict(bala)]
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.jugador['hp'], 2)
        self.assertEqual(juego.balas, [])
        self.assertEqual(juego.puntuacion, 1)          # ON_PLAYER_HIT

        juego.jugador['hp'] = 1
        juego.balas = [dict(bala)]
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.jugador['hp'], 0)
        self.assertTrue(juego.juego_terminado)

        juego.game_loop()      # emite ON_GAME_OVER una vez
        juego.game_loop()      # y no lo repite
        self.assertEqual(juego.puntuacion, 3)

    def test_spawn_del_jugador_en_el_borde_se_recorta(self):
        # Review Focus 1: un spawn que no cabe dejaria la partida sin jugador.
        juego = Tanks(datos_tanks(inicio=(7, 7)))
        self.assertEqual((juego.jugador['x'], juego.jugador['y']), (5, 5))
        juego.dibujar()
        for (x1, y1, x2, y2), _ in juego.canvas.rectangulos:
            self.assertTrue(0 <= x1 < juego.ancho_canvas and 0 <= y1 < juego.alto_canvas)

    def test_disparo_contra_el_borde_no_crea_bala(self):
        # Review Focus 4: sin cooldown, apuntar afuera permitiria rafagas.
        juego = Tanks(datos_tanks())
        juego.jugador['y'] = 0                # el cañon apunta arriba, fuera del tablero
        juego.manejar_tecla('SPACE')
        self.assertEqual(juego.balas, [])
        self.assertEqual(juego.jugador['cooldown'], 0.3)


class TestTanksMundo(unittest.TestCase):

    def setUp(self):
        random.seed(1234)

    def test_martillo_sana_y_reaparece(self):
        juego = Tanks(datos_tanks())
        juego.jugador['hp'] = 1
        juego.martillo = (3, 5)          # dentro de la cruz del jugador
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.jugador['hp'], 2)
        self.assertIsNotNone(juego.martillo)
        self.assertNotEqual(juego.martillo, (3, 5))

    def test_el_evento_puede_reubicar_el_martillo_sin_duplicarlo(self):
        datos = datos_tanks()
        datos['events']['ON_EAT_HAMMER'] = [accion('HEAL', 'PLAYER'),
                                            accion('SPAWN', 'MARTILLO', [[7, 7]])]
        juego = Tanks(datos)
        juego.jugador['hp'] = 2
        juego.martillo = (3, 5)
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.jugador['hp'], 3)
        self.assertEqual(juego.martillo, (7, 7))   # el motor no lo movio otra vez

    def test_martillo_sin_celda_libre_no_repite_el_evento(self):
        # Review Focus 3: tablero lleno de muros salvo la huella del jugador.
        # El martillo se cura una vez y queda en None; no hay bucle.
        juego = Tanks(datos_tanks())
        juego.jugador['hp'] = 1
        for y in range(juego.alto):
            for x in range(juego.ancho):
                juego.grid[y][x] = 1
        for x, y in juego._celdas_jugador():
            juego.grid[y][x] = 0
        juego.martillo = (3, 5)          # dentro de la cruz del jugador
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.jugador['hp'], 2)
        self.assertIsNone(juego.martillo)
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.jugador['hp'], 2)

    def test_enemigo_se_mueve_solo(self):
        juego = Tanks(datos_tanks())
        enemigo = agregar_enemigo(juego, 0, 0)
        juego.avanzar_mundo(0.5)                   # SPEED 2 => un paso cada 0.5 s
        self.assertEqual((enemigo['x'], enemigo['y']), (1, 0))

    def test_enemigo_gira_al_chocar(self):
        juego = Tanks(datos_tanks())
        enemigo = agregar_enemigo(juego, 0, 0)
        juego.grid[0][1] = 1
        juego.avanzar_mundo(0.5)
        self.assertEqual(enemigo['direccion'], (0, 1))
        self.assertEqual((enemigo['x'], enemigo['y']), (0, 1))

    def test_enemigo_rodeado_se_queda_quieto(self):
        # Review Focus 2: cuatro muros alrededor; ni bucle ni atravesarlos.
        juego = Tanks(datos_tanks())
        enemigo = agregar_enemigo(juego, 1, 1)
        for x, y in ((2, 1), (0, 1), (1, 0), (1, 2)):
            juego.grid[y][x] = 1
        juego.avanzar_mundo(0.5)
        self.assertEqual((enemigo['x'], enemigo['y']), (1, 1))
        self.assertEqual(enemigo['direccion'], (1, 0))   # cuatro giros, vuelve al inicio

    def test_enemigo_dispara_apuntado(self):
        juego = Tanks(datos_tanks())     # jugador 3x3 en (2,4): centro (3,5)
        # Misma columna que el centro del jugador y baja por ella (si apuntara
        # a la derecha, el primer paso lo sacaria de la columna).
        agregar_enemigo(juego, 3, 0, direccion=(0, 1))
        juego.avanzar_mundo(3.0)         # FIRE_RATE 3
        balas = [b for b in juego.balas if b['dueno'] == 'ENEMY']
        self.assertEqual(len(balas), 1)
        self.assertEqual((balas[0]['dx'], balas[0]['dy']), (0, 1))

    def test_enemigo_desalineado_dispara_al_frente(self):
        juego = Tanks(datos_tanks())
        agregar_enemigo(juego, 0, 0)
        juego.avanzar_mundo(3.0)
        balas = [b for b in juego.balas if b['dueno'] == 'ENEMY']
        self.assertEqual(len(balas), 1)
        self.assertEqual((balas[0]['dx'], balas[0]['dy']), (1, 0))

    def test_los_muros_del_nivel_se_generan_al_iniciar(self):
        datos = datos_tanks()
        datos['levels'] = [{'nombre': 'BABY', 'walls': 6}]
        # Sin ON_START: los spawns borran muros bajo su matriz y el conteo
        # exacto dejaria de ser 6.
        datos['events'].pop('ON_START')
        juego = Tanks(datos)
        self.assertEqual(sum(fila.count(1) for fila in juego.grid), 6)

    def test_muros_se_limitan_a_las_celdas_del_tablero(self):
        # Review Focus 5: WALLS 100 en 8x8 = 64 celdas; no cuelga y se corta.
        datos = datos_tanks()
        datos['levels'] = [{'nombre': 'BABY', 'walls': 100}]
        datos['events'].pop('ON_START')          # sin jugador, el tablero queda lleno
        juego = Tanks(datos)
        self.assertEqual(sum(fila.count(1) for fila in juego.grid), 64)

    def test_dos_niveles_no_dejan_muros_sobre_el_menu(self):
        datos = datos_tanks()
        datos['levels'] = [{'nombre': 'PATRULLA', 'tick': 0.12, 'walls': 6},
                           {'nombre': 'ASEDIO', 'tick': 0.08, 'walls': 10}]
        datos['config']['start_level'] = 'PATRULLA'
        datos['events'].pop('ON_START')          # spawns no borran muros
        juego = Tanks(datos)
        self.assertFalse(juego.iniciado)
        self.assertEqual(sum(fila.count(1) for fila in juego.grid), 0)

        juego.run()
        juego.botones_nivel[1].opciones['command']()
        self.assertTrue(juego.iniciado)
        self.assertEqual(juego.velocidad_gravedad, 0.08)
        self.assertEqual(sum(fila.count(1) for fila in juego.grid), 10)

    def test_fuzz_cinco_teclas_trescientas_veces(self):
        juego = Tanks(datos_tanks())
        teclas = ['UP', 'DOWN', 'LEFT', 'RIGHT', 'SPACE']
        for _ in range(300):
            if juego.juego_terminado:
                break
            juego.manejar_tecla(random.choice(teclas))
            juego.game_loop()
        self.assertGreater(juego.frame, 0)
