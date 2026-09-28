# -*- coding: utf-8 -*-
# Tests de integracion: compilar los .brick reales, crear el juego correcto
# y ejecutar el runtime.

import glob
import json
import os
import random
import subprocess
import sys
import unittest

import compiler
from engine import crear_juego, JUEGOS, Game, Tetris, Snake
from engine.utilidades import eleccion_ponderada

CARPETA_TLP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
        archivos = sorted(glob.glob(os.path.join(CARPETA_TLP, 'games', '*.brick')))
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


class TestRuntime(unittest.TestCase):

    def ejecutar(self, *argumentos):
        proceso = subprocess.Popen([sys.executable, 'runtime.py'] + list(argumentos),
                                   cwd=CARPETA_TLP, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        salida = proceso.communicate()[0]
        return proceso.returncode, salida

    def test_errores_del_runtime(self):
        codigo, salida = self.ejecutar()
        self.assertEqual(codigo, 1)
        self.assertIn('Uso: python runtime.py', salida)

        codigo, salida = self.ejecutar('no_existe.json')
        self.assertEqual(codigo, 1)
        self.assertIn('No se pudo encontrar el archivo', salida)

        ruta = os.path.join(CARPETA_TLP, 'tests', '_tipo_desconocido.json')
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
