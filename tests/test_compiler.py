# -*- coding: utf-8 -*-
# Tests del compilador: el lexer y el parser de BrickScript.

import json
import os
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

    def test_notas_acentuadas(self):
        # Un '#' precedido por letra A-G no abre comentario: si lo abriera, se
        # comia el resto de la linea y se perdia la duracion.
        self.assertEqual(compiler.lexer('NOTE D#4 200'), ['NOTE', 'D#4', '200'])
        # ... y los comentarios de verdad siguen funcionando
        self.assertEqual(compiler.lexer('# comentario'), [])
        self.assertEqual(compiler.lexer('NOTE C4 200 # cola'), ['NOTE', 'C4', '200'])
        self.assertEqual(compiler.lexer('# --- Niveles ---'), [])
        self.assertEqual(compiler.lexer('TICK 0.15 # el tick'), ['TICK', '0.15'])

    def test_nota_acentuada_esta_un_semitono_arriba(self):
        ast = compilar('DEFINE SONG X:\n  NOTE D4 200\n  NOTE D#4 200\nEND\n')
        natural, acentuada = (n[0] for n in ast['songs']['X']['notas'])
        # D# es la misma letra un semitono mas arriba: la razonancia de dos
        # vezes la frecuencia de la octava.
        self.assertAlmostEqual(acentuada / natural, 2 ** (1.0 / 12.0), places=3)

    def test_nota_invalida_falla_en_voz_alta(self):
        # Una letra que no es nota la rechaza el LEXER, antes de que el parser
        # la vea: H4 no matchea el patron de nota, asi que la H queda en 'resto'.
        # El mensaje lo dice el lexer, no el parser.
        with self.assertRaises(Exception) as contexto:
            compilar('DEFINE SONG X:\n  NOTE H4 200\nEND\n')
        self.assertIn("H", str(contexto.exception))

    def test_sostenido_sin_octava_lo_corta_el_lexer(self):
        # NOTA: la validacion de nota_a_hz es defensa en profundidad y no se
        # puede alcanzar desde el lexer, que solo produce tokens con la forma
        # [A-G]#?[0-9]+. Un sostenido sin octava lo rechaza el lexer.
        with self.assertRaises(Exception) as contexto:
            compilar('DEFINE SONG X:\n  NOTE D# 200\nEND\n')
        self.assertIn("'#'", str(contexto.exception))

    def test_silencio_rest(self):
        # REST se traduce a una nota de 0 Hz: sin(0) = 0, asi que suena mudo sin
        # que el sintetizador necesite ninguna rama especial.
        ast = compilar('DEFINE SONG X:\n  NOTE C4 200\n  NOTE REST 400\nEND\n')
        self.assertEqual(ast['songs']['X']['notas'], [[261.6, 200], [0.0, 400]])

    def test_onda_de_la_cancion(self):
            ast = compilar('DEFINE SONG X WAVE SQUARE:\n  NOTE C4 200\nEND\n')
            self.assertEqual(ast['songs']['X']['wave'], 'SQUARE')
            # Sin WAVE, senoidal
            ast = compilar('DEFINE SONG Y:\n  NOTE C4 200\nEND\n')
            self.assertEqual(ast['songs']['Y']['wave'], 'SINE')
            # Un efecto no lleva onda: suena una vez y no se elige timbre
            ast = compilar('DEFINE EFFECT Z:\n  NOTE C4 200\nEND\n')
            self.assertNotIn('wave', ast['effects']['Z'])

    def test_onda_invalida_avisada(self):
            with self.assertRaises(Exception) as contexto:
                compilar('DEFINE SONG X WAVE TRIANGULO:\n  NOTE C4 200\nEND\n')
            self.assertIn("onda 'TRIANGULO' no valida", str(contexto.exception))

    def test_cancion_con_varias_voces(self):
        ast = compilar('DEFINE SONG X WAVE SQUARE:\n'
                       '  VOICE 1:\n    NOTE C5 60\n    NOTE REST 60\n  END\n'
                       '  VOICE 2:\n    NOTE REST 60\n    NOTE G3 120\n  END\nEND\n')
        self.assertEqual(ast['songs']['X']['wave'], 'SQUARE')
        self.assertEqual(ast['songs']['X']['voces'],
                         [[[523.3, 60], [0.0, 60]], [[0.0, 60], [196.0, 120]]])
        # Con varias voces no se guarda 'notas': son dos listas, no una
        self.assertNotIn('notas', ast['songs']['X'])

    def test_una_cancion_de_una_sola_voce_no_lleva_voces(self):
        ast = compilar('DEFINE SONG X:\n  NOTE C5 60\nEND\n')
        self.assertNotIn('voces', ast['songs']['X'])
        self.assertEqual(ast['songs']['X']['notas'], [[523.3, 60]])

    def test_voce_repetida_avisada(self):
        with self.assertRaises(Exception) as contexto:
            compilar('DEFINE SONG X:\n'
                     '  VOICE 1:\n    NOTE C5 60\n  END\n'
                     '  VOICE 1:\n    NOTE G3 60\n  END\nEND\n')
        self.assertIn("la voz 1 esta definida dos veces", str(contexto.exception))

    def test_una_sola_voce_avisada(self):
        # Con una sola voz el bloque VOICE no tiene sentido: seria lo mismo que
        # escribir las notas directas, y asi se evita la confucion.
        with self.assertRaises(Exception) as contexto:
            compilar('DEFINE SONG X:\n  VOICE 1:\n    NOTE C5 60\n  END\nEND\n')
        self.assertIn("al menos dos voces", str(contexto.exception))

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


class TestTemaNyan(unittest.TestCase):

    def compilar_remake(self):
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(raiz, 'games', 'snake_remake.brick')) as f:
            return compilar(f.read())

    def test_tema_nyan_es_un_tema_propio_de_dos_voces(self):
        # TEMA_NYAN ya no es la transcripcion del tema publicado: es un tema
        # propio (lead + arpegio) en dos voces, con onda cuadrada.
        cancion = self.compilar_remake()['songs']['TEMA_NYAN']
        self.assertEqual(cancion['wave'], 'SQUARE')
        self.assertNotIn('notas', cancion)
        self.assertEqual(len(cancion['voces']), 2)

    def test_las_dos_voces_duran_lo_mismo(self):
        # Si el lead y el arpegio no miden lo mismo, suenan desfasados.
        cancion = self.compilar_remake()['songs']['TEMA_NYAN']
        for voz in cancion['voces']:
            self.assertEqual(len(voz), 48, '6 compases de 4/4 en corcheas')
            self.assertEqual(sum(ms for _, ms in voz), 9600, '48 corcheas de 200 ms')

    def test_el_tema_nyan_no_silencia_la_partida(self):
        # Ninguna voz puede tener un silencio largo: el loop sonaria roto.
        cancion = self.compilar_remake()['songs']['TEMA_NYAN']
        for voz in cancion['voces']:
            for frec, ms in voz:
                if frec == 0.0:
                    self.assertLessEqual(ms, 200, 'silencio mas largo que un slot')


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

    def test_modificador_poison_kills(self):
        # POISON_KILLS decide en cada nivel si comer veneno termina la partida
        ast = compilar('LEVELS:\n  LEVEL NYAN_CAT:\n    POISON_KILLS TRUE\n  END\nEND\n')
        self.assertIs(ast['levels'][0]['poison_kills'], True)
        ast = compilar('LEVELS:\n  LEVEL NYAN_CAT:\n    POISON_KILLS FALSE\n  END\nEND\n')
        self.assertIs(ast['levels'][0]['poison_kills'], False)

    def test_brick_remake_pone_poison_kills_solo_en_nyan_cat(self):
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(raiz, 'games', 'snake_remake.brick')) as f:
            ast = compilar(f.read())
        niveles = dict((n['nombre'], n) for n in ast['levels'])
        self.assertIs(niveles['NYAN_CAT']['poison_kills'], True)
        self.assertNotIn('poison_kills', niveles['BABY'])
        self.assertNotIn('poison_kills', niveles['ENTUSIASTA'])

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