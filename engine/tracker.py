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

# Timbres. La senoidal es suave y no cansa el oído (tetris la usa). La
# cuadrada es la de los chips de 8 bits, y por eso suena "chiptune": es lo que
# hace que un tema se lea como retro.
ONDA_SENOIDAL = 'SINE'
ONDA_CUADRADA = 'SQUARE'

# Cache en RAM: {firma: pcm_bytes}. La firma es el MD5 de la partitura,
# asi dos canciones con las mismas notas comparten un solo bloque.
_CACHE = {}


def firma_partitura(notas, onda=ONDA_SENOIDAL):
    # Huella del contenido: cambiar una nota produce otra firma y por tanto
    # otra cancion sintetizada, sin tener que invalidar nada a mano. La onda va
    # dentro de la firma porque el timbre tambien es contenido: sin esto, una
    # cancion cuadrada y una senoidal con las mismas notas compartirian la
    # entrada de cache y la segunda sonaria con el timbre equivocado.
    return hashlib.md5(repr((onda, notas)).encode('utf-8')).hexdigest()[:12]


def firma_voces(voces, onda=ONDA_SENOIDAL):
    return hashlib.md5(repr((onda, voces)).encode('utf-8')).hexdigest()[:12]


def cancion_pcm(nombre, notas, onda=ONDA_SENOIDAL):
    """Devuelve el PCM crudo (16 bits LE, mono) de la cancion, o None.

    `nombre` solo se usa para depurar; la cache se indexa por contenido.
    """
    if not notas:
        return None
    firma = firma_partitura(notas, onda)
    if firma in _CACHE:
        return _CACHE[firma]
    try:
        pcm = sintetizar(notas, onda)
    except Exception:
        return None
    _CACHE[firma] = pcm
    return pcm


def cancion_pcm_voces(nombre, voces, onda=ONDA_SENOIDAL):
    """PCM de una cancion con varias voces mezcladas, o None.

    Cada voz se sintetiza por separado y luego se suman muestra a muestra. Las
    voces se alinean por el principio: la mas corta se rellena con silencio.
    Con una sola voz da EXACTAMENTE el mismo PCM que cancion_pcm().
    """
    voces = [v for v in voces if v]
    if not voces:
        return None
    firma = firma_voces(voces, onda)
    if firma in _CACHE:
        return _CACHE[firma]
    try:
        pcm = sintetizar_voces(voces, onda)
    except Exception:
        return None
    _CACHE[firma] = pcm
    return pcm


def sintetizar(notas, onda=ONDA_SENOIDAL):
    """Una sola voz: PCM crudo (16 bits LE, mono) de la partitura.

    Se acumula en un array('h') y no en una lista de floats a proposito:
    un array de 'h' ocupa 2 bytes por muestra, mientras que la misma lista
    de floats ocuparia del orden de 24 bytes. Para una cancion de 14 s son
    ~620 KB en vez de ~7 MB.

    Una nota de frecuencia 0 (un REST) suena a silencio en cualquier timbre:
    con cuadrada, sin(2*pi*0*t) = 0 cae del lado positivo y daria un nivel
    alto fijo, así que hay una rama `frec == 0.0` que la llama cero. El bucle
    sigue consumiendo sus muestras, así que el silencio suma tiempo.
    """
    return _normalizar(_render_voz(notas, onda))


def sintetizar_voces(voces, onda=ONDA_SENOIDAL):
    """Mezcla N voces en un solo PCM: cada una se sintetiza aparte y se suman
    muestra a muestra, alineadas por el principio.

    Una voz controla su propio volumen de forma implicita: si dos suenan a la
    vez la suma da mas energia, y la normalizacion final baja el pico para que
    no sature. La voz mas corta se rellena con silencio. Con una sola voz da
    EXACTAMENTE el mismo PCM que sintetizar().
    """
    if len(voces) == 1:
        return sintetizar(voces[0], onda)
    canales = [_render_voz(notas, onda) for notas in voces]
    largo = max(len(c[0]) for c in canales)
    # La mezcla se acumula en enteros de Python, sin tope de 16 bits: sumar
    # varias voces al maximo pasa de 32767 y un array('h') lanzaria
    # OverflowError. El pico real es el de la mezcla, no el mayor pico
    # individual: con dos voces identicas la suma duplica el pico.
    mezcla = [0] * largo
    for muestras, _ in canales:
        for i in range(len(muestras)):
            mezcla[i] += muestras[i]
    pico = max([abs(x) for x in mezcla] + [1e-9])
    return _normalizar((mezcla, pico))


def _render_voz(notas, onda):
    """Una voz sola, SIN normalizar. Devuelve (muestras, pico)."""
    muestras = array.array('h')
    pico = 1e-9
    cuadrada = (onda == ONDA_CUADRADA)

    for voz in notas:
        frec, ms = float(voz[0]), int(voz[1])
        total = max(1, int(FPS * ms / 1000.0))
        # Envolvente de ataque y liberacion muy corta: sin clics entre notas.
        borde = max(1, int(FPS * 0.005))
        for i in range(total):
            t = float(i) / FPS
            if frec == 0.0:
                # Un REST calla en cualquier timbre: con cuadrada, sin(0) = 0
                # caeria del lado positivo y sonaria un nivel alto fijo.
                lead = 0.0
                bajo = 0.0
            elif cuadrada:
                # Solo dos niveles. El sub-octavo se apaga: en un chiptune lo
                # que suena es la cuadrada limpia, no una mezcla.
                lead = 1.0 if math.sin(2 * math.pi * frec * t) >= 0 else -1.0
                bajo = 0.0
            else:
                lead = math.sin(2 * math.pi * frec * t)
                bajo = math.sin(2 * math.pi * (frec / 2.0) * t)
            env = min(1.0, float(i) / borde, float(total - i) / borde)
            muestra = (0.22 * lead + 0.10 * bajo) * env * 32767.0
            # La senoidal se rectifica para que sea siempre positiva. La
            # cuadrada NO: si se rectificara, el ciclo negativo se volveria
            # positivo y la onda seria un bloque recto sin alternancia, o sea
            # un clic en vez de un timbre.
            if not cuadrada and muestra < 0:
                muestra = -muestra
            if abs(muestra) > pico:
                pico = abs(muestra)
            muestras.append(int(muestra))

    return (muestras, pico)


def _normalizar(render):
    """Segunda pasada: escalar al pico objetivo. Se puede hacer porque el array
    ya esta completo en memoria."""
    muestras, pico = render
    factor = (32767.0 * PICO) / pico
    # Se construye un array nuevo en vez de escribir encima: la mezcla puede
    # llegar como lista de enteros sin tope, y el resultado final es el mismo.
    escaladas = [int(max(-32768, min(32767, round(x * factor)))) for x in muestras]

    return array.array('h', escaladas).tostring()


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