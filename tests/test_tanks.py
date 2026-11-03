# -*- coding: utf-8 -*-
# Tests del juego Tanks (GAME_TYPE TANKS): el .brick real y el motor
# (jugador, balas, enemigos, muros y martillo).

import os
import unittest

import compiler

CARPETA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
