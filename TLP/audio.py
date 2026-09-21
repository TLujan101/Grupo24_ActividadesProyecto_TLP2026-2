# -*- coding: utf-8 -*-
"""
audio.py - Gestor de Audio Multi-canal Polifónico (Python 2.7 Stdlib)
- Música y efectos de sonido simultáneos en canales separados (no se cortan entre sí).
- Amplitud calibrada al 4% - 5% (volumen suave, cálido y sin fatiga auditiva).
- Windows: Canales nativos independientes mediante MCI (winmm.dll).
- Linux: Subprocesos ligeros mediante aplay/pw-play/paplay mezclados por el sistema.
- Cierre instantáneo (0 ms) sin bloqueos.
"""
import sys
import os
import time
import threading
import subprocess

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


def _detectar_reproductor_linux():
    # Devuelve (comando, flags). -q solo existe en aplay; pasarlo a
    # paplay/pw-play los haria fallar en silencio.
    for cmd in ['pw-play', 'paplay', 'aplay']:
        try:
            p = subprocess.Popen(['which', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.communicate()
            if p.returncode == 0:
                if cmd == 'aplay':
                    return (cmd, ['-q'])
                return (cmd, [])
        except Exception:
            pass
    return ('aplay', ['-q'])


class GestorAudioNativo(object):
    """
    Gestor de audio multicanal nativo para Python 2.7.
    """
    def __init__(self, carpeta_sonidos="songs"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.isabs(carpeta_sonidos):
            self.carpeta = carpeta_sonidos
        else:
            self.carpeta = os.path.join(base_dir, carpeta_sonidos)

        self.silenciado = False
        self.reproduciendo_musica = False
        self.musica_actual = None
        self.hilo_musica = None
        self._proc_musica = None  # handle del reproductor hijo (Linux), para matarlo en seco
        self._sfx_id = 0
        self._lock = threading.Lock()
        self.reproductor_linux = _detectar_reproductor_linux() if IS_LINUX else None

    def _resolver(self, nombre_archivo):
        """Resuelve el .wav: acepta rutas absolutas (canciones del .brick
        sintetizadas en temporal) o nombres dentro de songs/."""
        if isinstance(nombre_archivo, unicode):
            # MCI (winmm ANSI) no acepta unicode: error 292. Todo bytes.
            # (Los nombres del JSON llegan como unicode.)
            nombre_archivo = nombre_archivo.encode("mbcs")
        if os.path.isabs(nombre_archivo) and os.path.isfile(nombre_archivo):
            return os.path.normpath(nombre_archivo)
        clave = os.path.basename(nombre_archivo)
        if not clave.endswith('.wav'):
            clave += '.wav'
        ruta = os.path.normpath(os.path.join(self.carpeta, clave))
        if os.path.isfile(ruta):
            return ruta
        return None

    def reproducir_musica_fondo(self, nombre_archivo):
        """Reproduce música de fondo en bucle asíncrono en su propio canal."""
        self.detener_musica()
        if self.silenciado or not nombre_archivo:
            return

        ruta = self._resolver(nombre_archivo)
        if ruta is None:
            return

        self.musica_actual = ruta
        self.reproduciendo_musica = True

        if IS_WIN and _mci:
            def _loop_mci():
                ruta_win = ruta.replace('/', '\\')
                try:
                    _mci('close bgm', None, 0, 0)
                    _mci('open "%s" alias bgm' % ruta_win, None, 0, 0)
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

            self.hilo_musica = threading.Thread(target=_loop_mci)
            self.hilo_musica.daemon = True
            self.hilo_musica.start()

        elif IS_LINUX:
            def _loop_linux():
                cmd, flags = self.reproductor_linux
                while self.reproduciendo_musica and not self.silenciado:
                    try:
                        p = subprocess.Popen([cmd] + flags + [ruta])
                        with self._lock:
                            self._proc_musica = p
                        while p.poll() is None:
                            if not self.reproduciendo_musica or self.silenciado:
                                try:
                                    p.kill()
                                except Exception:
                                    pass
                                return
                            time.sleep(0.08)
                    except Exception:
                        break

            self.hilo_musica = threading.Thread(target=_loop_linux)
            self.hilo_musica.daemon = True
            self.hilo_musica.start()

    def detener_musica(self):
        """Detiene la música de fondo inmediatamente."""
        self.reproduciendo_musica = False
        if IS_WIN and _mci:
            try:
                _mci('stop bgm', None, 0, 0)
                _mci('close bgm', None, 0, 0)
            except Exception:
                pass
        elif IS_LINUX:
            # Kill sincronico: sin esto el hijo quedaba huerfano sonando
            # hasta terminar el loop si el proceso moria antes del proximo poll.
            with self._lock:
                p, self._proc_musica = self._proc_musica, None
            if p is not None:
                try:
                    p.kill()
                except Exception:
                    pass

    def reproducir_efecto(self, nombre_archivo):
        """Reproduce un efecto de sonido simultáneamente sin cortar la música."""
        if self.silenciado or not nombre_archivo:
            return

        ruta = self._resolver(nombre_archivo)
        if ruta is None:
            return

        if IS_WIN and _mci:
            with self._lock:
                self._sfx_id = (self._sfx_id + 1) % 8
                alias = 'sfx_%d' % self._sfx_id

            def _play_sfx():
                ruta_win = ruta.replace('/', '\\')
                try:
                    _mci('close %s' % alias, None, 0, 0)
                    _mci('open "%s" alias %s' % (ruta_win, alias), None, 0, 0)
                    _mci('play %s from 0' % alias, None, 0, 0)
                except Exception:
                    pass

            t = threading.Thread(target=_play_sfx)
            t.daemon = True
            t.start()

        elif IS_LINUX:
            try:
                cmd, flags = self.reproductor_linux
                subprocess.Popen([cmd] + flags + [ruta])
            except Exception:
                pass

    def alternar_silencio(self):
        """Alterna el estado Mute / Unmute."""
        self.silenciado = not self.silenciado
        if self.silenciado:
            self.detener_musica()
        else:
            if self.musica_actual:
                self.reproducir_musica_fondo(self.musica_actual)
        return self.silenciado

    def detener_todo(self):
        """Libera todos los recursos de audio."""
        self.detener_musica()
        if IS_WIN and _mci:
            try:
                for i in range(8):
                    _mci('close sfx_%d' % i, None, 0, 0)
                _mci('close bgm', None, 0, 0)
            except Exception:
                pass