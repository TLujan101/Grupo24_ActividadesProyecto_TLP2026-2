# -*- coding: utf-8 -*-
# tracker.py --- Sintetizador de las canciones programadas en el .brick.
#
# Convierte una partitura (lista de pares [Hz, ms]) en PCM crudo y lo deja
# en RAM. NO escribe archivos: la cache es un diccionario en memoria, de
# modo que la primera vez que suena una cancion se sintetiza (unas decimas
# de segundo) y las siguientes son instantaneas. El audio vive unicamente
# mientras el proceso este vivo.
#
# Timbre: lead senoidal + bajo senoidal una octava abajo (acompania sin
# competir). Pico normalizado al 4% para que quede de fondo, sin fatigar.
#
# La unica parte que toca disco es audio.py en Windows, porque MCI solo
# acepta rutas de archivo (ver cabecera_wav).

import array
import hashlib
import math
import struct

FPS = 22050                  # muestras por segundo
PICO = 0.04                  # amplitud maxima normalizada
BYTES_POR_MUESTRA = 2        # mono de 16 bits

# Cache en RAM: {firma: pcm_bytes}. La firma es el MD5 de la partitura,
# asi dos canciones con las mismas notas comparten un solo bloque.
_CACHE = {}


def firma_partitura(notas):
    # Huella del contenido: cambiar una nota produce otra firma y por tanto
    # otra cancion sintetizada, sin tener que invalidar nada a mano.
    return hashlib.md5(repr(notas).encode('utf-8')).hexdigest()[:12]


def cancion_pcm(nombre, notas):
    """Devuelve el PCM crudo (16 bits LE, mono) de la cancion, o None.

    `nombre` solo se usa para depurar; la cache se indexa por contenido.
    """
    if not notas:
        return None
    firma = firma_partitura(notas)
    if firma in _CACHE:
        return _CACHE[firma]
    try:
        pcm = sintetizar(notas)
    except Exception:
        return None
    _CACHE[firma] = pcm
    return pcm


def duracion_pcm(notas):
    """Duracion total de la partitura en milisegundos."""
    return sum(int(voz[1]) for voz in notas)


def sintetizar(notas):
    """Genera las muestras de la partitura y devuelve el PCM empaquetado.

    Se acumula en un array('h') y no en una lista de floats a proposito:
    un array de 'h' ocupa 2 bytes por muestra, mientras que la misma lista
    de floats ocuparia del orden de 24 bytes. Para una cancion de 14 s son
    ~620 KB en vez de ~7 MB.
    """
    muestras = array.array('h')
    pico = 1e-9

    for voz in notas:
        frec, ms = float(voz[0]), int(voz[1])
        total = max(1, int(FPS * ms / 1000.0))
        # Envolvente de ataque y liberacion muy corta: sin clics entre notas.
        borde = max(1, int(FPS * 0.005))
        for i in range(total):
            t = float(i) / FPS
            lead = math.sin(2 * math.pi * frec * t)
            bajo = math.sin(2 * math.pi * (frec / 2.0) * t)
            env = min(1.0, float(i) / borde, float(total - i) / borde)
            muestra = (0.22 * lead + 0.10 * bajo) * env * 32767.0
            if muestra < 0:
                muestra = -muestra
            if muestra > pico:
                pico = muestra
            muestras.append(int(muestra))

    # Segunda pasada: normalizar al pico objetivo. Se puede hacer porque el
    # array ya esta completo en memoria.
    factor = (32767.0 * PICO) / pico
    for i in range(len(muestras)):
        muestras[i] = int(max(-32768, min(32767, round(muestras[i] * factor))))

    return muestras.tostring()


def cabecera_wav(n_muestras):
    """Cabecera RIFF/WAV de 44 bytes para mono 16 bits a FPS Hz."""
    datos = n_muestras * BYTES_POR_MUESTRA
    return struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        'RIFF', 36 + datos, 'WAVE',
        'fmt ', 16,            # tamano del bloque fmt
        1,                     # PCM sin comprimir
        1,                     # mono
        FPS,
        FPS * BYTES_POR_MUESTRA,
        BYTES_POR_MUESTRA,
        16,
        'data', datos,
    )


def wav_completo(pcm):
    """PCM crudo envuelto en un WAV completo (lo que MCI necesita en Windows)."""
    return cabecera_wav(len(pcm) // BYTES_POR_MUESTRA) + pcm


def limpiar_cache():
    """Libera las canciones sintetizadas. La usa el boton de silencio."""
    _CACHE.clear()