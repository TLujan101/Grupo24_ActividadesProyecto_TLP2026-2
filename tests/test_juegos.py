# -*- coding: utf-8 -*-
# Tests de integracion: compilar los .brick reales, crear el juego correcto
# y ejecutar el runtime.

import array
import glob
import hashlib
import json
import os
import random
import subprocess
import sys
import unittest

import compiler
from engine import crear_juego, JUEGOS, Game, Tetris, Snake, tracker
from engine.utilidades import eleccion_ponderada

CARPETA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def compilar(ruta_brick):
    with open(ruta_brick, 'r') as f:
        codigo = f.read()
    return compiler.Parser(compiler.lexer(codigo)).parse()


class TestRegistroDeJuegos(unittest.TestCase):

    def test_crear_juego_por_tipo(self):
        for clase in JUEGOS.values():
            self.assertTrue(issubclass(clase, Game))
        vacio = {'config': {}, 'shapes': {'X': [[[1]]]}, 'events': {}}
        vacio['tipo_juego'] = 'TETRIS'
        self.assertIsInstance(crear_juego(vacio), Tetris)
        vacio['tipo_juego'] = 'SNAKE'
        self.assertIsInstance(crear_juego(vacio), Snake)
        self.assertRaises(ValueError, crear_juego, {'tipo_juego': 'PONG', 'events': {}})

    def test_eleccion_ponderada(self):
        self.assertRaises(ValueError, eleccion_ponderada, ['a', 'b'], [1])
        self.assertRaises(ValueError, eleccion_ponderada, ['a', 'b'], [0, 0])
        for _ in range(50):
            self.assertEqual(eleccion_ponderada(['a', 'b', 'c'], [0, 5, 0]), 'b')


class TestJuegosReales(unittest.TestCase):
    # Cada .brick de games/ debe compilar, crear su clase y aguantar
    # varios ciclos de juego con teclas al azar.

    def test_games_brick(self):
        archivos = sorted(glob.glob(os.path.join(CARPETA_RAIZ, 'games', '*.brick')))
        self.assertTrue(archivos)
        teclas = ['Up', 'Down', 'Left', 'Right']
        for ruta in archivos:
            random.seed(1234)
            datos_juego = compilar(ruta)
            juego = crear_juego(datos_juego)
            self.assertIsInstance(juego, JUEGOS[datos_juego['tipo_juego']], ruta)
            for _ in range(300):
                if juego.juego_terminado:
                    break
                juego.manejar_tecla(random.choice(teclas).upper())
                juego.game_loop()

    def test_snake_remake_abre_menu_y_arranca_al_elegir(self):
        # snake_remake.brick declara tres niveles: la partida no arranca sola y
        # el jugador elige con una tecla o con un clic. snake.brick (clasico)
        # no hace esto.
        random.seed(1234)
        datos_juego = compilar(os.path.join(CARPETA_RAIZ, 'games', 'snake_remake.brick'))
        self.assertEqual(datos_juego['config']['start_level'], 'NYAN_CAT')
        self.assertEqual([n['nombre'] for n in datos_juego['levels']],
                         ['BABY', 'ENTUSIASTA', 'NYAN_CAT'])

        juego = crear_juego(datos_juego)
        self.assertFalse(juego.iniciado)
        self.assertEqual(juego.serpiente_cuerpo, [])
        juego.run()                                   # abre el menu
        self.assertEqual([b.opciones['text'] for b in juego.botones_nivel],
                         ['1. Baby', '2. Entusiasta', '3. Nyan Cat'])

        juego.botones_nivel[1].opciones['command']()  # clic en Entusiasta
        self.assertTrue(juego.iniciado)
        self.assertEqual(juego.nivel_actual, 'ENTUSIASTA')
        self.assertEqual(juego.velocidad_gravedad, 0.1)
        self.assertEqual(len(juego.serpiente_cuerpo), 1)   # ON_START corrio
        self.assertIsNotNone(juego.posicion_comida)

        # Y la partida corre normal desde ahi
        for _ in range(30):
            juego.manejar_tecla(random.choice(['UP', 'DOWN', 'LEFT', 'RIGHT']))
            juego.game_loop()

    def test_powerup_solo_da_invulnerabilidad(self):
        # El power-up no da puntos ni alarga: solo invulnerabilidad.
        datos_juego = compilar(os.path.join(CARPETA_RAIZ, 'games', 'snake_remake.brick'))
        verbos = [a['accion'] for a in datos_juego['events']['ON_EAT_POWERUP']]
        self.assertIn('GRANT_INVULNERABILITY', verbos)
        self.assertNotIn('GROW', verbos)
        self.assertNotIn('INCREASE_SCORE', verbos)
        # Nyan Cat es la dificultad maxima: su power-up dura menos.
        duraciones = dict((n['nombre'], n.get('invulnerability_duration'))
                          for n in datos_juego['levels'])
        self.assertEqual(duraciones['ENTUSIASTA'], 7)
        self.assertEqual(duraciones['NYAN_CAT'], 5)
        self.assertLess(duraciones['NYAN_CAT'], duraciones['ENTUSIASTA'])

    def test_snake_remake_tiene_musica_por_nivel_y_efectos(self):
        from engine import tracker
        random.seed(1234)
        datos_juego = compilar(os.path.join(CARPETA_RAIZ, 'games', 'snake_remake.brick'))

        # Cada nivel declara su tema, y el compilador ya habria fallado si
        # alguno nombrara una cancion que no existe.
        musicas = [n.get('music') for n in datos_juego['levels']]
        self.assertEqual(sorted(musicas), ['TEMA_CALMO', 'TEMA_ENTUSIASTA', 'TEMA_NYAN'])
        for nombre in musicas:
            self.assertIn(nombre, datos_juego['songs'])
            cancion = datos_juego['songs'][nombre]
            # Una cancion puede ir en una sola voz (notas) o en varias (voces).
            self.assertTrue(cancion.get('notas') or cancion.get('voces'))

        # Efectos de comer y de morir.
        self.assertIn('COMER', datos_juego['effects'])
        self.assertIn('MORIR', datos_juego['effects'])

        # Al elegir un nivel suena SU tema, y el menu calla antes.
        juego = crear_juego(datos_juego)
        juego.run()
        self.assertEqual(juego.audio.llamadas, [])
        juego.botones_nivel[0].opciones['command']()          # '1. Baby'
        esperado = tracker.firma_partitura(datos_juego['songs']['TEMA_CALMO']['notas'])
        self.assertEqual(juego.audio.musica_actual, esperado)

        # Comer suena el efecto, sin cortar la musica.
        juego.audio.llamadas = []
        juego.posicion_comida = (juego.serpiente_cuerpo[0][0] + 1,
                                juego.serpiente_cuerpo[0][1])
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.audio.llamadas, [('efecto',)])
        self.assertEqual(juego.audio.musica_actual, esperado)

    def test_tema_nyan_sintetiza_el_pcm_esperado(self):
        # 6 compases de 4/4 a 150 BPM: 48 corcheas de 200 ms = 9.6 s, dos voces
        # (lead + arpegio) que el sintetizador mezcla y normaliza.
        datos_juego = compilar(os.path.join(CARPETA_RAIZ, 'games', 'snake_remake.brick'))
        cancion = datos_juego['songs']['TEMA_NYAN']
        pcm = tracker.cancion_pcm_voces('TEMA_NYAN', cancion['voces'], cancion['wave'])
        muestras = array.array('h')
        muestras.fromstring(pcm)
        # La mezcla se alinea por el principio: mide como la voz mas larga.
        esperado = max(sum(max(1, int(tracker.FPS * ms / 1000.0)) for _, ms in voz)
                        for voz in cancion['voces'])
        self.assertEqual(len(muestras), esperado)
        self.assertTrue(any(m != 0 for m in muestras))
        # Test dorado: la cancion no cambia sin querer (mismo patron que Tetris).
        # El md5 es el del preview que se escucho antes de fijarlo.
        self.assertEqual(hashlib.md5(pcm).hexdigest(),
                         'b5c00a9d824a221678215ea6ca64c173')

    def test_tema_tetris_pcm_identico_byte_a_byte(self):
        # Test dorado: el camino senoidal no se puede mover sin que este test
        # grite. 37 notas, 620928 bytes, md5 fijo.
        datos_juego = compilar(os.path.join(CARPETA_RAIZ, 'games', 'tetris_reborn.brick'))
        cancion = datos_juego['songs']['TETRIS_TEMA_A']
        pcm = tracker.cancion_pcm('TETRIS_TEMA_A', cancion['notas'],
                                   cancion.get('wave', tracker.ONDA_SENOIDAL))
        self.assertEqual(len(pcm), 620928)
        self.assertEqual(hashlib.md5(pcm).hexdigest(),
                         '773d9d4ca93f5565e853cfc40bda2c5a')

    def test_snake_clasico_no_abre_menu(self):
        datos_juego = compilar(os.path.join(CARPETA_RAIZ, 'games', 'snake.brick'))
        self.assertEqual(datos_juego['config']['start_level'], 'BABY')
        juego = crear_juego(datos_juego)
        self.assertTrue(juego.iniciado)      # arranca solo, como siempre
        self.assertEqual(juego.velocidad_gravedad, 0.15)
        juego.run()
        self.assertEqual(juego.botones_nivel, [])
        self.assertEqual(juego.root.afters, [(50, juego.game_loop)])


class TestRuntime(unittest.TestCase):

    def ejecutar(self, *argumentos):
        proceso = subprocess.Popen([sys.executable, 'runtime.py'] + list(argumentos),
                                   cwd=CARPETA_RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        salida = proceso.communicate()[0]
        return proceso.returncode, salida

    def test_errores_del_runtime(self):
        codigo, salida = self.ejecutar()
        self.assertEqual(codigo, 1)
        self.assertIn('Uso: python runtime.py', salida)

        codigo, salida = self.ejecutar('no_existe.json')
        self.assertEqual(codigo, 1)
        self.assertIn('No se pudo encontrar el archivo', salida)

        ruta = os.path.join(CARPETA_RAIZ, 'tests', '_tipo_desconocido.json')
        with open(ruta, 'w') as f:
            json.dump({'tipo_juego': 'PONG', 'config': {}, 'shapes': {}, 'events': {}}, f)
        try:
            codigo, salida = self.ejecutar(ruta)
        finally:
            os.remove(ruta)
        self.assertEqual(codigo, 1)
        self.assertIn('Tipo de juego desconocido: PONG', salida)


if __name__ == '__main__':
    unittest.main()
