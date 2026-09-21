# -*- coding: utf-8 -*-
# tracker.py - Motor de canciones programadas en .brick (Python 2.7 Stdlib)
# Sintetiza las partituras del JSON a .wav en el primer run, con cache.
# Timbre: lead senoidal + bajo senoidal una octava abajo (receta validada
# en pruebas: acompana sin competir). Pico normalizado al 4%, igual que
# los .wav de songs/ para mantener el balance con mute/volumen.
import hashlib
import math
import os
import struct
import tempfile
import wave

FPS = 22050
PICO = 0.04

try:
    _texto = unicode
except NameError:
    _texto = str


def ruta_cancion(nombre, notas):
    """Devuelve el .wav sintetizado para la cancion (lo genera si falta)."""
    if not notas:
        return None
    base = os.path.join(tempfile.gettempdir(), "brickscript_brick")
    if not os.path.isdir(base):
        try:
            os.makedirs(base)
        except Exception:
            return None
    firma = hashlib.md5(repr(notas).encode("utf-8")).hexdigest()[:12]
    ruta = os.path.join(base, "%s_%s.wav" % (nombre, firma))
    if isinstance(ruta, _texto):
        # MCI (winmm ANSI) no acepta unicode: error 292. Todo bytes.
        ruta = ruta.encode("mbcs")
    if os.path.isfile(ruta) and os.path.getsize(ruta) > 0:
        return ruta
    try:
        return sintetizar(ruta, notas)
    except Exception:
        return None


def sintetizar(ruta, notas):
    muestras = []
    for voz in notas:
        frec, ms = float(voz[0]), int(voz[1])
        total = max(1, int(FPS * ms / 1000.0))
        borde = max(1, int(FPS * 0.005))
        for i in range(total):
            t = float(i) / FPS
            lead = math.sin(2 * math.pi * frec * t)
            bajo = math.sin(2 * math.pi * (frec / 2.0) * t)
            env = min(1.0, float(i) / borde, float(total - i) / borde)
            muestras.append((0.22 * lead + 0.10 * bajo) * env)
    pico = max([abs(m) for m in muestras] + [1e-9])
    factor = (32767.0 * PICO) / pico
    datos = struct.pack("<%dh" % len(muestras),
                        *[int(max(-32768, min(32767, round(m * factor))))
                          for m in muestras])
    w = wave.open(ruta, "wb")
    try:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FPS)
        w.writeframes(datos)
    finally:
        w.close()
    return ruta
