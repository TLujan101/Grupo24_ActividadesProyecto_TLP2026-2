# -*- coding: utf-8 -*-
# Tests del compilador: el lexer y el parser de BrickScript.

import unittest

import compiler


class TestLexer(unittest.TestCase):

    def test_decimales(self):
        # El punto decimal viaja dentro del token, no como dos numeros sueltos
        self.assertEqual(compiler.lexer('TICK 0.15'), ['TICK', '0.15'])
        self.assertEqual(compiler.lexer('TICK 0.06'), ['TICK', '0.06'])
        self.assertEqual(compiler.lexer('TICK 150'), ['TICK', '150'])

    def test_enteros_siguen_igual(self):
        # GAME_GRID, CHANCE y las notas no deben cambiar
        self.assertEqual(compiler.lexer('GAME_GRID (18, 18)'),
                         ['GAME_GRID', '(', '18', ',', '18', ')'])
        self.assertEqual(compiler.lexer('DEFINE SHAPE X COLOR CYAN CHANCE 10:'),
                         ['DEFINE', 'SHAPE', 'X', 'COLOR', 'CYAN', 'CHANCE', '10', ':'])
        self.assertEqual(compiler.lexer('DEFINE SONG C: NOTE E5 400'),
                         ['DEFINE', 'SONG', 'C', ':', 'NOTE', 'E5', '400'])

    def test_identificadores_en_mayusculas(self):
        # Un nombre de nivel en minusculas o mezclado no es un token valido:
        # el lenguaje entero esta en mayusculas.
        self.assertEqual(compiler.lexer('LEVEL NYAN_CAT:'),
                         ['LEVEL', 'NYAN_CAT', ':'])
        self.assertRaises(Exception, compiler.lexer, 'LEVEL Enthusiasta:')

    def test_cadena_con_comentarios_y_decimales(self):
        fuente = '# velocidad\nLEVEL BABY:\n  TICK 0.15\nEND'
        self.assertEqual(compiler.lexer(fuente),
                         ['LEVEL', 'BABY', ':', 'TICK', '0.15', 'END'])


BRICK_CON_NIVELES = """
GAME_TYPE SNAKE
GAME_GRID (18, 18)
LEVELS:
  START: NYAN_CAT
  LEVEL BABY:
    TICK 0.15
  END
  LEVEL ENTUSIASTA:
    TICK 0.10
  END
  LEVEL NYAN_CAT:
    TICK 0.06
  END
END
ON START:
  SPAWN PLAYER AT (9, 9)
END
"""


def compilar(fuente):
    return compiler.Parser(compiler.lexer(fuente)).parse()


class TestParserNiveles(unittest.TestCase):

    def test_bloque_niveles(self):
        ast = compilar(BRICK_CON_NIVELES)
        self.assertEqual(ast['config']['start_level'], 'NYAN_CAT')
        self.assertEqual(ast['levels'], [{'nombre': 'BABY', 'tick': 0.15},
                                         {'nombre': 'ENTUSIASTA', 'tick': 0.1},
                                         {'nombre': 'NYAN_CAT', 'tick': 0.06}])

    def test_sin_bloque_niveles_queda_baby(self):
        # Punto D: sin la etiqueta de niveles se asigna Baby por defecto.
        # El nivel existe y es el inicial, pero NO lleva valores: el default de
        # cada modificador lo aporta el juego, no el compilador (Tetris 0.4 y
        # Snake 0.15 son distintos y el compilador no sabe cual corre).
        ast = compilar('GAME_TYPE SNAKE\nGAME_GRID (18, 18)\n')
        self.assertEqual(ast['levels'], [{'nombre': 'BABY'}])
        self.assertEqual(ast['config']['start_level'], 'BABY')

    def test_start_ausente_usa_el_primer_nivel(self):
        ast = compilar('LEVELS:\n  LEVEL ENTUSIASTA:\n    TICK 0.1\n  END\nEND\n')
        self.assertEqual(ast['config']['start_level'], 'ENTUSIASTA')

    def test_nivel_sin_modificadores(self):
        ast = compilar('LEVELS:\n  LEVEL BABY:\n  END\nEND\n')
        self.assertEqual(ast['levels'], [{'nombre': 'BABY'}])

    def test_el_bloque_va_en_cualquier_posicion(self):
        # El parser es un despachador de tokens: el bloque no depende del orden
        for fuente in ('LEVELS:\n  LEVEL BABY:\n  END\nEND\nGAME_TYPE SNAKE\n',
                       'GAME_TYPE SNAKE\nLEVELS:\n  LEVEL BABY:\n  END\nEND\n'):
            self.assertEqual(compilar(fuente)['config']['start_level'], 'BABY')

    def test_errores_de_validacion(self):
        casos = [
            # (fuente, fragmento del mensaje)
            ('LEVELS:\n  START: X\n  LEVEL BABY:\n  END\nEND\n',
             "el nivel inicial 'X' no esta definido"),
            ('LEVELS:\n  LEVEL BABY:\n  END\n  LEVEL BABY:\n  END\nEND\n',
             "el nivel 'BABY' esta definido dos veces"),
            ('LEVELS:\nEND\n', 'LEVELS no declara ningun nivel'),
            ('LEVELS:\n  LEVEL BABY:\n    TICK 0\n  END\nEND\n',
             "TICK del nivel 'BABY' debe ser mayor que 0"),
            ('LEVELS:\n  LEVEL BABY:\n    TIC 0.15\n  END\nEND\n',
             "modificador desconocido 'TIC' en el nivel 'BABY'"),
            # nan <= 0 es False e inf <= 0 tambien: la comparacion sola no
            # los caza. Sin esto el motor se come un TICK nan y el juego queda
            # congelado (0.05 >= nan es False para siempre), sin error.
            ('LEVELS:\n  LEVEL BABY:\n    TICK NAN\n  END\nEND\n',
             "TICK del nivel 'BABY' debe ser mayor que 0"),
            ('LEVELS:\n  LEVEL BABY:\n    TICK INF\n  END\nEND\n',
             "TICK del nivel 'BABY' debe ser mayor que 0"),
            ('LEVELS:\n  LEVEL BABY:\n    TICK INFINITY\n  END\nEND\n',
             "TICK del nivel 'BABY' debe ser mayor que 0"),
            # Un segundo bloque descartaria el primero en silencio, y el autor
            # creeria haber declarado los dos.
            ('LEVELS:\n  LEVEL UNO:\n  END\nEND\nLEVELS:\n  LEVEL DOS:\n  END\nEND\n',
             'LEVELS esta declarado mas de una vez'),
        ]
        for fuente, esperado in casos:
            # assertRaises como contexto (py2.7). Nada de try/except con
            # self.fail adentro: AssertionError hereda de Exception, asi que el
            # except se tragaria el fallo propio y la asercion se cumpliria
            # sola.
            with self.assertRaises(Exception) as contexto:
                compilar(fuente)
            self.assertIn(esperado, str(contexto.exception))

    def test_modificador_music(self):
        # MUSIC toma un identificador, no un decimal como TICK: la tabla de
        # modificadores tiene que distinguir los dos tipos de valor.
        fuente = ('DEFINE SONG TEMA_CALMO:\n  NOTE C5 440\nEND\n'
                  'DEFINE SONG TEMA_NYAN:\n  NOTE E5 440\nEND\n'
                  'LEVELS:\n'
                  '  LEVEL BABY:\n    MUSIC TEMA_CALMO\n  END\n'
                  '  LEVEL NYAN_CAT:\n    TICK 0.06\n    MUSIC TEMA_NYAN\n  END\n'
                  'END\n')
        ast = compilar(fuente)
        self.assertEqual(ast['levels'],
                         [{'nombre': 'BABY', 'music': 'TEMA_CALMO'},
                          {'nombre': 'NYAN_CAT', 'tick': 0.06, 'music': 'TEMA_NYAN'}])

    def test_music_exige_nombre(self):
        with self.assertRaises(Exception) as contexto:
            compilar('LEVELS:\n  LEVEL BABY:\n    MUSIC\n  END\nEND\n')
        self.assertIn("se esperaba el nombre de la cancion", str(contexto.exception))

    def test_music_debe_nombrar_una_cancion_declarada(self):
        # El motor tolera un nombre inexistente (suena mudo), pero aqui se
        # rechaza: un typo en el nombre dejaria el nivel mudo sin decir por que.
        # Se comprueba al final del parse, asi que el orden de los bloques da
        # igual: la cancion puede declararse DESPUES del LEVELS.
        fuente = ('LEVELS:\n  LEVEL BABY:\n    MUSIC TEMA_CALMO\n  END\nEND\n'
                  'DEFINE SONG TEMA_CALMO:\n  NOTE E5 440\nEND\n')
        self.assertEqual(compilar(fuente)['levels'][0]['music'], 'TEMA_CALMO')

        with self.assertRaises(Exception) as contexto:
            compilar('LEVELS:\n  LEVEL BABY:\n    MUSIC TEMA_X\n  END\nEND\n')
        self.assertIn("pide la cancion 'TEMA_X' pero no esta definida",
                      str(contexto.exception))

    def test_el_orden_de_los_niveles_sobrevive_al_json(self):
        # Razon de ser de que levels sea lista y no dict: en py2.7 un dict
        # pierde el orden de declaracion al pasar por JSON, y el menu se
        # numera por posicion. Este test es el round-trip completo.
        import json
        import StringIO
        fuente = ('LEVELS:\n'
                  '  LEVEL C:\n    TICK 0.3\n  END\n'
                  '  LEVEL A:\n    TICK 0.2\n  END\n'
                  '  LEVEL B:\n    TICK 0.1\n  END\n'
                  'END\n')
        ast = compilar(fuente)
        # Como el compilador escribe (json.dump) y el runtime lee (json.load)
        salida = StringIO.StringIO()
        json.dump(ast, salida)
        salida.seek(0)
        recuperado = json.load(salida)
        self.assertEqual([n['nombre'] for n in recuperado['levels']],
                         ['C', 'A', 'B'])
        self.assertEqual([n['tick'] for n in recuperado['levels']],
                         [0.3, 0.2, 0.1])


if __name__ == '__main__':
    unittest.main()