# -*- coding: utf-8 -*-
# audio.py --- Reproduccion del audio sintetizado en tracker.py.
#
# Recibe PCM crudo (no rutas) y lo manda a los parlantes. Musica de fondo
# y efectos van en canales separados, de modo que un efecto nunca corta la
# musica.
#
# DOS FORMAS DE REPRODUCIR, y la razon de la diferencia:
#
#   Linux  -> se le pasa el PCM por la tuberia de entrada estandar. No se
#             toca el disco en ningun momento. Es lo natural: paplay y
#             aplay leen audio crudo de stdin.
#   Windows-> MCI (winmm.dll) solo sabe abrir RUTAS de archivo, no memoria.
#             No hay forma de reproducir un buffer en RAM con esta API,
#             asi que ahi si se escribe un .wav temporal. Se escribe en una
#             carpeta propia que se borra al cerrar el juego, y el archivo de
#             musica es uno solo que se reescribe al cambiar de tema, de
#             modo que nunca queda basura acumulada.
#
# pw-play queda fuera a proposito: solo reproduce archivos, no acepta stdin.

import os
import sys
import time
import shutil
import tempfile
import threading
import subprocess

import tracker

IS_WIN = sys.platform.startswith('win')
IS_LINUX = sys.platform.startswith('linux')

if IS_WIN:
    try:
        import ctypes
        _mci = ctypes.windll.winmm.mciSendStringA
    except Exception:
        _mci = None
else:
    _mci = None

# Formato que describe el PCM de tracker.py: mono 16 bits little-endian.
FORMATO_PCM = {'paplay': ['--raw=s16le', '--rate=%d' % tracker.FPS, '--channels=1'],
               'aplay':  ['-f', 'S16_LE', '-r', str(tracker.FPS), '-c', '1', '-t', 'raw']}


def _detectar_reproductor_linux():
    # Devuelve (comando, flags) del primer reproductor disponible que sepa
    # leer PCM crudo de stdin. Si no hay ninguno, el juego sigue sin audio.
    for cmd in ('paplay', 'aplay'):
        try:
            p = subprocess.Popen(['which', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.communicate()
            if p.returncode == 0:
                return (cmd, FORMATO_PCM[cmd])
        except Exception:
            pass
    return (None, [])


class GestorAudioNativo(object):
    """Gestor de audio multicanal. Python 2.7, solo biblioteca estandar."""

    def __init__(self):
        self.silenciado = False
        self.reproduciendo_musica = False
        self.musica_actual = None      # firma de la cancion que suena
        self.hilo_musica = None
        self._proc_musica = None       # proceso hijo en Linux, para matarlo
        self._sfx_id = 0
        self._lock = threading.Lock()
        self.reproductor = _detectar_reproductor_linux() if IS_LINUX else None

        # Windows: MCI exige archivo, asi que hay un scratch en disco.
        self._dir_temp = None
        self._ruta_musica = None
        if IS_WIN:
            try:
                self._dir_temp = tempfile.mkdtemp(prefix='brickscript_audio_')
                self._ruta_musica = os.path.join(self._dir_temp, 'musica.wav')
            except Exception:
                self._dir_temp = None
                self._ruta_musica = None

    # AYUDANTES DE PLATAFORMA
    # -----------------------

    def disponible(self):
        """True si esta plataforma puede reproducir audio."""
        if IS_WIN:
            return _mci is not None
        if IS_LINUX:
            return self.reproductor[0] is not None
        return False

    def _escribir_wav(self, ruta, pcm):
        # Solo Windows. Escribe el WAV completo que MCI va a abrir.
        with open(ruta, 'wb') as f:
            f.write(tracker.wav_completo(pcm))

    def _lanzar_linux(self, pcm):
        """Inyecta el PCM por stdin. Devuelve el proceso, o None."""
        cmd, flags = self.reproductor
        if not cmd:
            return None
        proc = subprocess.Popen([cmd] + flags, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Se escribe desde este hilo: el pipe aplica contrapresion, asi que
        # el reproductor marca el ritmo real y la cancion no adelanta.
        try:
            proc.stdin.write(pcm)
            proc.stdin.close()
        except Exception:
            pass
        return proc

    def _ruta_efecto(self):
        # Un archivo por efecto, para no pisar uno que MCI todavia tiene
        # abierto. Se borra al terminar de sonar.
        with self._lock:
            self._sfx_id += 1
            nombre = 'sfx_%d.wav' % self._sfx_id
        return os.path.join(self._dir_temp, nombre)

    # MUSICA DE FONDO
    # ----------------

    def _loop_linux(self, pcm):
        # Relanza el reproductor cada vez que termina la cancion. El pipe
        # aplica contrapresion, asi que escribir el PCM ya marca el ritmo.
        while self.reproduciendo_musica and not self.silenciado:
            proc = self._lanzar_linux(pcm)
            if proc is None:
                break
            with self._lock:
                self._proc_musica = proc
            while proc.poll() is None:
                if not self.reproduciendo_musica or self.silenciado:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    break
                time.sleep(0.08)
            with self._lock:
                if self._proc_musica is proc:
                    self._proc_musica = None

    def _loop_mci(self, pcm):
        # MCI abre por ruta, asi que hay que pasarle bytes ANSI y no unicode.
        ruta = self._ruta_musica
        if not isinstance(ruta, str):
            ruta = ruta.encode('mbcs')
        ruta = ruta.replace('/', '\\')
        try:
            _mci('close bgm', None, 0, 0)
            _mci('open "%s" alias bgm' % ruta, None, 0, 0)
        except Exception:
            return

        buf = ctypes.create_string_buffer(64)
        while self.reproduciendo_musica and not self.silenciado:
            try:
                _mci('play bgm from 0', None, 0, 0)
                while self.reproduciendo_musica and not self.silenciado:
                    time.sleep(0.08)
                    _mci('status bgm mode', buf, 64, 0)
                    if buf.value != 'playing':
                        break
            except Exception:
                break

        try:
            _mci('stop bgm', None, 0, 0)
            _mci('close bgm', None, 0, 0)
        except Exception:
            pass

    def reproducir_musica_fondo(self, pcm, firma):
        """Reproduce la musica en bucle. `firma` identifica la cancion."""
        self.detener_musica()
        if self.silenciado or not pcm or not self.disponible():
            return

        self.musica_actual = firma
        self._pcm_actual = pcm
        self.reproduciendo_musica = True

        if IS_LINUX:
            objetivo, args = self._loop_linux, (pcm,)
        elif IS_WIN and _mci and self._ruta_musica:
            try:
                self._escribir_wav(self._ruta_musica, pcm)
            except Exception:
                self.reproduciendo_musica = False
                return
            objetivo, args = self._loop_mci, (pcm,)
        else:
            self.reproduciendo_musica = False
            return

        self.hilo_musica = threading.Thread(target=objetivo, args=args)
        self.hilo_musica.daemon = True
        self.hilo_musica.start()

    def detener_musica(self):
        """Corta la musica de inmediato."""
        self.reproduciendo_musica = False
        if IS_WIN and _mci:
            try:
                _mci('stop bgm', None, 0, 0)
                _mci('close bgm', None, 0, 0)
            except Exception:
                pass
        elif IS_LINUX:
            # Sin esto el proceso hijo queda huerfano sonando hasta que
            # termina su cancion, aunque el juego ya haya cerrado.
            with self._lock:
                proc, self._proc_musica = self._proc_musica, None
            if proc is not None:
                try:
                    proc.kill()
                except Exception:
                    pass

    # EFECTOS
    # -------

    def reproducir_efecto(self, pcm):
        """Reproduce un efecto una vez, sin cortar la musica."""
        if self.silenciado or not pcm or not self.disponible():
            return

        if IS_LINUX:
            def _sfz_linux():
                proc = self._lanzar_linux(pcm)
                if proc is not None:
                    try:
                        proc.wait()
                    except Exception:
                        pass
            t = threading.Thread(target=_sfz_linux)
            t.daemon = True
            t.start()
            return

        if IS_WIN and _mci and self._dir_temp:
            ruta = self._ruta_efecto()
            try:
                self._escribir_wav(ruta, pcm)
            except Exception:
                return
            with self._lock:
                alias = 'sfx_%d' % (self._sfx_id % 8)

            def _sfz_mci():
                buf = ctypes.create_string_buffer(64)
                ruta_win = ruta.replace('/', '\\')
                try:
                    _mci('close %s' % alias, None, 0, 0)
                    _mci('open "%s" alias %s' % (ruta_win, alias), None, 0, 0)
                    _mci('play %s from 0' % alias, None, 0, 0)
                    # Se espera a que MCI termine de leer el archivo: solo
                    # entonces se puede cerrar el alias y borrarlo.
                    while True:
                        time.sleep(0.02)
                        _mci('status %s mode' % alias, buf, 64, 0)
                        if buf.value != 'playing':
                            break
                    _mci('close %s' % alias, None, 0, 0)
                except Exception:
                    pass
                try:
                    os.remove(ruta)
                except Exception:
                    pass

            t = threading.Thread(target=_sfz_mci)
            t.daemon = True
            t.start()

    # CONTROL
    # -------

    def alternar_silencio(self):
        """Alterna Mute / Unmute. Devuelve True si quedo silenciado."""
        self.silenciado = not self.silenciado
        if self.silenciado:
            self.detener_musica()
            tracker.limpiar_cache()
        else:
            # Para retomar hay que volver a pedir la cancion: la cache se
            # vacio al silenciar, y el .brick la vuelve a pedir en el proximo
            # evento. Si no hay ninguna, el juego sigue en silencio.
            self.musica_actual = None
        return self.silenciado

    def detener_todo(self):
        """Libera todo. Se llama antes de destruir la ventana."""
        self.detener_musica()
        if IS_WIN and _mci:
            try:
                for i in range(8):
                    _mci('close sfx_%d' % i, None, 0, 0)
                _mci('close bgm', None, 0, 0)
            except Exception:
                pass
        if self._dir_temp:
            try:
                shutil.rmtree(self._dir_temp, ignore_errors=True)
            except Exception:
                pass
            self._dir_temp = None