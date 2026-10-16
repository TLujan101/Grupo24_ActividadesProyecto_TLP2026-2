# -*- coding: utf-8 -*-
# Tests de retrocompatibilidad: los juegos clasicos de games/ (todos los
# .brick cuyo nombre no dice "reborn" ni "remake") deben seguir funcionando
# con el compilador y el motor actuales.

import glob
import os
import random
import unittest

import compiler
from engine import crear_juego, Game

# Las variantes nuevas llevan una de estas palabras en el nombre del .brick
VARIANTES_NUEVAS = ('reborn', 'remake')
CARPETA_GAMES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'games')


def juegos_clasicos(tipo_juego):
    # Devuelve [(nombre_archivo, datos_juego)] de los clasicos de ese tipo
    clasicos = []
    for ruta in sorted(glob.glob(os.path.join(CARPETA_GAMES, '*.brick'))):
        if any(palabra in os.path.basename(ruta) for palabra in VARIANTES_NUEVAS):
            continue
        with open(ruta, 'r') as f:
            datos_juego = compiler.Parser(compiler.lexer(f.read())).parse()
        if datos_juego['tipo_juego'] == tipo_juego:
            clasicos.append((os.path.basename(ruta), datos_juego))
    return clasicos


class TestTetrisClasico(unittest.TestCase):

    def setUp(self):
        self._random_original = random.random
        self.clasicos = juegos_clasicos('TETRIS')
        self.assertTrue(self.clasicos, 'no hay ningun Tetris clasico en games/')

    def tearDown(self):
        random.random = self._random_original

    def limpiar_ultima_fila(self, juego):
        juego.grid[juego.alto - 1] = [1] * juego.ancho
        juego.tetris_limpiar_lineas()
        for _ in range(6):   # el borrado es diferido (parpadeo de la fila)
            juego.game_loop()
        juego.tetris_spawn_pieza()
        juego.dibujar()

    def test_partida_completa_hasta_game_over(self):
        # Sin power ups (random.random alto): las piezas caen hasta llenar
        # el tablero. Recorre fijar pieza, colisiones, rotar y game over.
        random.random = lambda: 0.99
        teclas = ['UP', 'DOWN', 'LEFT', 'RIGHT']
        for nombre, datos_juego in self.clasicos:
            random.seed(1234)
            juego = crear_juego(datos_juego)
            for _ in range(5000):
                if juego.juego_terminado:
                    break
                juego.manejar_tecla(random.choice(teclas))
                juego.game_loop()
            self.assertTrue(juego.juego_terminado, nombre)
            juego.game_loop()   # dibuja la pantalla de game over

    def test_limpiar_linea_sin_power_up(self):
        random.random = lambda: 0.99
        for nombre, datos_juego in self.clasicos:
            juego = crear_juego(datos_juego)
            self.limpiar_ultima_fila(juego)
            self.assertEqual(juego.puntuacion, 100, nombre)
            self.assertIn(juego.pieza_nombre, datos_juego['shapes'], nombre)

    # Sortear un power up que el .brick no define (tetris.brick) no debe
    # romper el spawn (antes lanzaba KeyError).
    def test_limpiar_linea_con_cualquier_sorteo(self):
        # Cada valor cae en un rango distinto del sorteo de power ups
        for sorteo in (0.10, 0.30, 0.50, 0.70, 0.90):
            random.random = lambda: sorteo
            for nombre, datos_juego in self.clasicos:
                juego = crear_juego(datos_juego)
                self.limpiar_ultima_fila(juego)
                self.assertIn(juego.pieza_nombre, datos_juego['shapes'], '%s %s' % (nombre, sorteo))


class TestSnakeClasico(unittest.TestCase):

    def setUp(self):
        self._randint_original = random.randint
        self.clasicos = juegos_clasicos('SNAKE')
        self.assertTrue(self.clasicos, 'no hay ningun Snake clasico en games/')

    def tearDown(self):
        random.randint = self._randint_original

    def test_inicio_y_comer(self):
        for nombre, datos_juego in self.clasicos:
            random.randint = self._randint_original
            juego = crear_juego(datos_juego)
            self.assertEqual(len(juego.serpiente_cuerpo), 1, nombre)
            self.assertIsNotNone(juego.posicion_comida, nombre)

            x, y = juego.serpiente_cuerpo[0]
            juego.posicion_comida = (x + 1, y)   # justo delante (va a la derecha)
            random.randint = lambda a, b: 0      # la comida nueva aparece en (0, 0)
            juego.snake_mover_jugador()
            self.assertEqual(juego.puntuacion, 10, nombre)
            self.assertEqual(juego.serpiente_cuerpo, [(x + 1, y), (x, y)], nombre)
            self.assertEqual(juego.posicion_comida, (0, 0), nombre)
            juego.dibujar()

    def test_partidas_hasta_game_over(self):
        teclas = ['UP', 'DOWN', 'LEFT', 'RIGHT']
        for nombre, datos_juego in self.clasicos:
            # Sin tocar nada, avanza hasta chocar con la pared
            juego = crear_juego(datos_juego)
            for _ in range(juego.ancho):
                if juego.juego_terminado:
                    break
                juego.snake_mover_jugador()
            self.assertTrue(juego.juego_terminado, nombre + ': choque con la pared')
            juego.game_loop()   # dibuja la pantalla de game over

            # Con teclas al azar tambien termina sin errores
            random.seed(1234)
            juego = crear_juego(datos_juego)
            for _ in range(2000):
                if juego.juego_terminado:
                    break
                juego.manejar_tecla(random.choice(teclas))
                juego.game_loop()
            self.assertTrue(juego.juego_terminado, nombre + ': teclas al azar')

    def test_nivel_por_defecto_en_los_clasicos(self):
        # Punto D: snake.brick no declara LEVELS, asi que debe compilar al
        # nivel Baby. El nombre se materializa; los valores no, porque cada
        # juego tiene su tick por defecto (Snake 0.15, Tetris 0.4).
        for nombre, datos_juego in self.clasicos:
            self.assertEqual(datos_juego['config']['start_level'], 'BABY', nombre)
            self.assertEqual(datos_juego['levels'], [{'nombre': 'BABY'}], nombre)
            self.assertNotIn('tick', datos_juego['levels'][0], nombre)

    def test_json_viejo_sin_levels_arranca(self):
        # Un .json compilado por la version anterior del compilador (no tiene
        # 'levels') tiene que seguir arrancando
        for nombre, datos_juego in self.clasicos:
            viejo = {'tipo_juego': 'SNAKE', 'config': {'grid_size': [5, 5]},
                     'shapes': {}, 'events': datos_juego['events']}
            juego = crear_juego(viejo)
            self.assertEqual(juego.nivel_actual, Game.NIVEL_POR_DEFECTO, nombre)
            self.assertEqual(juego.nivel_config, {}, nombre)
            self.assertEqual(juego.velocidad_gravedad, 0.15, nombre)


if __name__ == '__main__':
    unittest.main()
