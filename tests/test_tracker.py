# -*- coding: utf-8 -*-
# Tests del sintetizador: silencios, ondas y la cache de partituras.

import array
import unittest

from engine import tracker


def muestras_de(pcm):
    a = array.array('h')
    a.fromstring(pcm)
    return a


def huella(pcm):
    # Comparar PCM completos a mano vuelca 600 KB al console cuando falla. Se
    # compara la huella: si dos difieren, la huella lo dice en 12 caracteres.
    import hashlib
    return hashlib.md5(pcm).hexdigest()[:12]


class TestSilencios(unittest.TestCase):

    def test_un_silencio_no_suena_pero_su_tiempo_cuenta(self):
        # Un REST es una nota de frecuencia 0: sen(0) = 0, asi que el
        # sintetizador no necesita ninguna rama especial para callar.
        pcm = tracker.cancion_pcm('silencio', [[0.0, 400]])
        muestras = muestras_de(pcm)
        self.assertEqual(len(muestras), int(tracker.FPS * 400 / 1000.0))
        self.assertTrue(all(m == 0 for m in muestras))

    def test_un_silencio_es_silencio_tambien_en_cuadrada(self):
        # Un REST es frecuencia 0 y tiene que callar en cualquier timbre. Con
        # onda cuadrada, sin(2*pi*0*t) = 0 cae del lado positivo y daria un
        # nivel alto fijo: un zumbido en vez de un silencio.
        muestras = muestras_de(tracker.cancion_pcm('rest-cuadrada', [[0.0, 400]],
                                                    'SQUARE'))
        self.assertTrue(all(m == 0 for m in muestras))

    def test_el_silencio_ocupa_lugar_en_la_linea_de_tiempo(self):
        # Dos notas de 200 ms suman 400; con un silencio de 400 en medio
        # suman 800. El silencio tiene que SUMAR tiempo, no quitárselo a las
        # notas de al lado.
        dos_notas = tracker.cancion_pcm('a', [[440.0, 200], [440.0, 200]])
        con_silencio = tracker.cancion_pcm('b', [[440.0, 200], [0.0, 400], [440.0, 200]])
        self.assertEqual(len(muestras_de(con_silencio)) - len(muestras_de(dos_notas)),
                         int(tracker.FPS * 400 / 1000.0))


class TestOndas(unittest.TestCase):

    def test_la_onda_cuadrada_no_es_la_senoidal(self):
        notas = [[440.0, 200]]
        senoidal = tracker.cancion_pcm('senoidal', notas, 'SINE')
        cuadrada = tracker.cancion_pcm('cuadrada', notas, 'SQUARE')
        self.assertIsNotNone(senoidal)
        self.assertIsNotNone(cuadrada)
        self.assertNotEqual(huella(senoidal), huella(cuadrada))

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
        self.assertEqual(huella(tracker.cancion_pcm('a', notas, 'SINE')),
                         huella(tracker.cancion_pcm('b', notas, 'SINE')))


class TestVoces(unittest.TestCase):

    def tearDown(self):
        tracker.limpiar_cache()

    def test_una_voz_da_el_mismo_pcm_que_la_forma_antigua(self):
        # El invariante que protege la musica de Tetris: pasar una sola voz por
        # el camino nuevo tiene que dar EXACTAMENTE el mismo PCM que antes.
        notas = [[440.0, 200], [523.3, 300]]
        self.assertEqual(huella(tracker.cancion_pcm('x', notas)),
                         huella(tracker.cancion_pcm_voces('x', [notas])))

    def test_dos_voces_duran_lo_que_la_mas_larga(self):
        # La mezcla se alinea al inicio: la voz corta se rellena con silencio.
        corta = [[440.0, 100]]
        larga = [[440.0, 200], [523.3, 200]]
        mezcla = muestras_de(tracker.cancion_pcm_voces('m', [corta, larga]))
        self.assertEqual(len(mezcla), 2 * int(tracker.FPS * 0.2))

    def test_la_voz_corta_no_parte_la_cancion(self):
        # Si la voz 2 acaba antes, la 1 tiene que seguir sonando sola.
        larga = [[440.0, 400]]
        corta = [[220.0, 100]]
        con_dos = tracker.cancion_pcm_voces('a', [larga, corta])
        solo = tracker.cancion_pcm('b', larga)
        self.assertNotEqual(huella(con_dos), huella(solo))   # el bajo cambia el resultado
        self.assertEqual(len(muestras_de(con_dos)), len(muestras_de(solo)))

    def test_un_silencio_en_una_voz_no_apaga_la_otra(self):
        # Este es el caso real del bajo: la melodia descansa y el bajo sigue.
        melodia = [[0.0, 400]]
        bajo = [[220.0, 400]]
        mezcla = muestras_de(tracker.cancion_pcm_voces('m', [melodia, bajo]))
        self.assertTrue(any(m != 0 for m in mezcla))
        # Y al reves: si solo la melodia suena, tambien hay energia
        mezcla2 = muestras_de(tracker.cancion_pcm_voces('m2', [bajo, melodia]))
        self.assertTrue(any(m != 0 for m in mezcla2))

    def test_la_firma_distingue_una_de_una_misma_mas_varias_voces(self):
        nota = [[440.0, 200]]
        # Mismo contenido, misma firma de voces
        self.assertEqual(tracker.firma_voces([nota[0]], 'SINE'),
                         tracker.firma_voces([nota[0]], 'SINE'))
        # Distinto contenido, distinta firma
        self.assertNotEqual(tracker.firma_voces([nota[0]], 'SINE'),
                            tracker.firma_voces([[nota[0][0], 400]], 'SINE'))
        # La firma de una lista plana por firma_partitura es la misma que por
        # firma_voces (ambas hashean repr((onda, notas))); el motor las elige
        # segun el bloque que lleve el .brick.
        self.assertEqual(tracker.firma_partitura(nota, 'SINE'),
                         tracker.firma_voces(nota, 'SINE'))

    def test_tres_voces_tambien(self):
        # No es "dos voces": es N.
        v = [[[440.0, 200]], [[220.0, 200]], [[330.0, 200]]]
        self.assertEqual(len(muestras_de(tracker.cancion_pcm_voces('t', v))),
                         int(tracker.FPS * 0.2))

    def test_muchas_voces_no_reventan_el_rango_de_16_bits(self):
        # La mezcla ocurre ANTES de normalizar, y sumar N voces al maximo se
        # pasa de 32767 a partir de unas 5. Un array('h') lanza OverflowError
        # en ese caso, y cancion_pcm_voces se come la excepcion y devuelve None:
        # la cancion sonaria en silencio sin decir nada. Este test falla si
        # vuelve a pasar.
        voces = [[[440.0, 400]] for _ in range(8)]
        pcm = tracker.cancion_pcm_voces('muchas', voces, 'SQUARE')
        self.assertIsNotNone(pcm, 'la mezcla de 8 voces devolvio None')
        muestras = muestras_de(pcm)
        # Si las muestras hubieran dado la vuelta, el pico seria un disparate
        # negativo en vez del techo previsto.
        self.assertEqual(max(max(muestras), -min(muestras)),
                         int(round(32767 * tracker.PICO)))
        for m in muestras:
            self.assertTrue(-32768 <= m <= 32767)


if __name__ == '__main__':
    unittest.main()