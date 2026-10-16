# -*- coding: utf-8 -*-
# Tests del sintetizador: silencios, ondas y la cache de partituras.

import array
import unittest

from engine import tracker


def muestras_de(pcm):
    a = array.array('h')
    a.fromstring(pcm)
    return a


class TestSilencios(unittest.TestCase):

    def test_un_silencio_no_suena_pero_su_tiempo_cuenta(self):
        # Un REST es una nota de frecuencia 0: sen(0) = 0, asi que el
        # sintetizador no necesita ninguna rama especial para callar.
        pcm = tracker.cancion_pcm('silencio', [[0.0, 400]])
        muestras = muestras_de(pcm)
        self.assertEqual(len(muestras), int(tracker.FPS * 400 / 1000.0))
        self.assertTrue(all(m == 0 for m in muestras))

    def test_el_silencio_ocupa_lugar_en_la_linea_de_tiempo(self):
        # Dos notas de 200 ms suman 400; con un silencio de 400 en medio
        # suman 800. El silencio tiene que SUMAR tiempo, no quitárselo a las
        # notas de al lado.
        dos_notas = tracker.cancion_pcm('a', [[440.0, 200], [440.0, 200]])
        con_silencio = tracker.cancion_pcm('b', [[440.0, 200], [0.0, 400], [440.0, 200]])
        self.assertEqual(len(muestras_de(con_silencio)) - len(muestras_de(dos_notas)),
                         int(tracker.FPS * 400 / 1000.0))
        self.assertEqual(tracker.duracion_pcm([[440.0, 200], [0.0, 400], [440.0, 200]]), 800)


class TestOndas(unittest.TestCase):

    def test_la_onda_cuadrada_no_es_la_senoidal(self):
        notas = [[440.0, 200]]
        senoidal = tracker.cancion_pcm('senoidal', notas, 'SINE')
        cuadrada = tracker.cancion_pcm('cuadrada', notas, 'SQUARE')
        self.assertIsNotNone(senoidal)
        self.assertIsNotNone(cuadrada)
        self.assertNotEqual(senoidal, cuadrada)

    def test_la_cuadrada_es_bipolar_y_de_dos_niveles(self):
        # Se mira el medio de la nota: el ataque y la liberacion (5 ms) crean
        # valores intermedios a proposito, para que no haya clics entre notas.
        muestras = muestras_de(tracker.cancion_pcm('c', [[440.0, 200]], 'SQUARE'))
        medio = muestras[len(muestras) // 10: len(muestras) * 9 // 10]
        niveles = sorted(set(medio))
        self.assertEqual(len(niveles), 2, 'una cuadrada deberia dar dos niveles')
        # Y opuestos: si estuviera rectificada serian los dos positivos y la
        # onda seria un bloque recto en vez de un timbre.
        self.assertLess(niveles[0], 0)
        self.assertGreater(niveles[1], 0)
        self.assertEqual(abs(niveles[0]), abs(niveles[1]))

    def test_la_firma_incluye_la_onda(self):
        # Si la firma no incluyera la onda, una cancion cuadrada y una senoidal
        # con las mismas notas compartirian la entrada de cache y la segunda
        # sonaria con el timbre equivocado, en silencio y sin avisar.
        notas = [[440.0, 200]]
        self.assertNotEqual(tracker.firma_partitura(notas, 'SQUARE'),
                            tracker.firma_partitura(notas, 'SINE'))
        self.assertEqual(tracker.firma_partitura(notas, 'SINE'),
                         tracker.firma_partitura(notas))       # SINE es el default


class TestCache(unittest.TestCase):

    def tearDown(self):
        tracker.limpiar_cache()

    def test_mismas_notas_distinta_onda_no_comparten_cache(self):
        notas = [[440.0, 200]]
        uno = tracker.cancion_pcm('x', notas, 'SINE')
        dos = tracker.cancion_pcm('y', notas, 'SQUARE')
        self.assertNotEqual(uno, dos)
        # Y da igual el orden: si se pidiera al revés, tampoco debe cambiar.
        tres = tracker.cancion_pcm('z', notas, 'SQUARE')
        self.assertEqual(dos, tres)

    def test_mismas_notas_misma_onda_si_comparten(self):
        notas = [[440.0, 200]]
        self.assertEqual(tracker.cancion_pcm('a', notas, 'SINE'),
                         tracker.cancion_pcm('b', notas, 'SINE'))


if __name__ == '__main__':
    unittest.main()