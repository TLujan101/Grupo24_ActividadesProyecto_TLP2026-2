# -*- coding: utf-8 -*-
# audio.py --- Reproduce el PCM de engine/tracker.py (solo stdlib).
# Musica y efectos van por separado: un efecto nunca corta la musica.
# Linux: PCM por stdin (paplay/aplay). Windows: MCI solo abre rutas, asi que
# se usa un .wav temporal que se borra al cerrar (pw-play no sirve: no lee
# stdin). Efectos en pool de 8 alias MCI y contador de generacion para que
# sonidos simultaneos no se corten entre si.

import os
import sys
import time
import shutil
import tempfile
import threading
import subprocess

from . import tracker

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

# PCM mono 16 bits little-endian. OJO paplay: --raw es bandera SIN valor
# (el formato va en --format=); '--raw=s16le' rompe el pipe en silencio.
FORMATO_PCM = {'paplay': ['--raw', '--format=s16le', '--rate=%d' % tracker.FPS, '--channels=1'],
               'aplay':  ['-f', 'S16_LE', '-r', str(tracker.FPS), '-c', '1', '-t', 'raw']}


def _detectar_reproductor_linux():
    # Prueba con entrada vacia: obliga a parsear flags sin sonar. Solo
    # 'which' no basta: instalado no significa que acepte el formato.
    for cmd in ('paplay', 'aplay'):
        flags = FORMATO_PCM[cmd]
        try:
            p = subprocess.Popen([cmd] + flags, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            salida = p.communicate('')[1].strip()
            if p.returncode == 0:
                return (cmd, flags)
            sys.stderr.write('[audio] %s instalado pero no sirve (%s), se prueba el siguiente\n'
                             % (cmd, salida or 'codigo %d' % p.returncode))
        except Exception:
            # No esta instalado (OSError): se pasa al siguiente sin quejarse.
            pass
    sys.stderr.write('[audio] no hay reproductor de audio crudo en este sistema; el juego ira sin sonido\n')
    return (None, [])


class GestorAudioNativo(object):
    """Gestor de audio multicanal. Python 2.7, solo biblioteca estandar."""

    def __init__(self):
        self.silenciado = False
        self.reproduciendo_musica = False
        self.musica_actual = None      # firma de la cancion que suena
        self.hilo_musica = None
        self._proc_musica = None       # proceso hijo en Linux, para matarlo
        self._procs_vivos = set()      # TODOS los hijos vivos (musica y efectos)
        self._pcm_actual = None       # ultima cancion sintetizada, para el un-mute
        self._firma_actual = None
        self._sfx_id = 0
        self._generacion = 0          # ver _sigo_vivo(): invalida el hilo viejo
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

    def _abrir(self):
        """Arranca el reproductor. NO inyecta nada, asi que no se bloquea."""
        cmd, flags = self.reproductor
        return subprocess.Popen([cmd] + flags, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def _inyectar(self, proc, pcm):
        """Vuelca el PCM en stdin; bloquea lo que dura la cancion (la
        contrapresion del pipe marca el ritmo real)."""
        try:
            proc.stdin.write(pcm)
            proc.stdin.close()
        except Exception:
            pass

    def _lanzar_linux(self, pcm, es_musica):
        """Registra el hijo ANTES de inyectar: si no, es invisible mientras
        bloquea y no hay nada que matar al silenciar o cerrar."""
        if not self.reproductor[0]:
            return None
        try:
            proc = self._abrir()
        except Exception:
            return None
        with self._lock:
            self._procs_vivos.add(proc)
            if es_musica:
                self._proc_musica = proc
        self._inyectar(proc, pcm)
        return proc

    def _olvidar(self, proc):
        # Saca hijos terminados del registro.
        with self._lock:
            self._procs_vivos.discard(proc)
            if self._proc_musica is proc:
                self._proc_musica = None

    def _matar(self, proc):
        if proc is None:
            return
        try:
            proc.kill()
        except Exception:
            pass

    def _efecto_nuevo(self):
        """Reserva archivo y alias del MISMO numero: antes salian de
        contadores separados y dos efectos simultaneos podian compartir
        alias y cortarse entre si."""
        with self._lock:
            self._sfx_id += 1
            numero = self._sfx_id
        return (os.path.join(self._dir_temp, 'sfx_%d.wav' % numero),
                'sfx_%d' % (numero % 8))

    def _sigo_vivo(self, generacion):
        """La bandera no alcanza: en un cambio de cancion vuelve a True antes
        de que el hilo viejo termine. La generacion sube con cada cancion y
        retira al anterior."""
        with self._lock:
            return (self.reproduciendo_musica
                    and not self.silenciado
                    and self._generacion == generacion)

    # MUSICA DE FONDO
    # ----------------

    def _loop_linux(self, pcm, generacion):
        # Relanza el reproductor por cancion; el pipe ya marca el ritmo.
        while self._sigo_vivo(generacion):
            proc = self._lanzar_linux(pcm, es_musica=True)
            if proc is None:
                break
            while proc.poll() is None:
                if not self._sigo_vivo(generacion):
                    self._matar(proc)
                    break
                time.sleep(0.08)
            self._olvidar(proc)

    def _loop_mci(self, pcm, generacion):
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
        while self._sigo_vivo(generacion):
            try:
                _mci('play bgm from 0', None, 0, 0)
                while self._sigo_vivo(generacion):
                    time.sleep(0.08)
                    _mci('status bgm mode', buf, 64, 0)
                    if buf.value != 'playing':
                        break
            except Exception:
                break

        # Cierra 'bgm' siempre: con el alias abierto Windows bloquea el
        # scratch y no se puede reescribir (reproduce_musica_fondo espera
        # con join() a este hilo antes de escribir de nuevo).
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

        # La generacion sube ANTES de las banderas (retira al hilo anterior)
        # y se espera su salida: en Windows el scratch es exclusivo y
        # escribir encima da Permission denied.
        with self._lock:
            self._generacion += 1
            generacion = self._generacion
            self.musica_actual = firma
            self._pcm_actual = pcm
            self._firma_actual = firma
            self.reproduciendo_musica = True

        self._esperar_hilo_musica()

        if IS_LINUX:
            objetivo, args = self._loop_linux, (pcm, generacion)
        elif IS_WIN and _mci and self._ruta_musica:
            try:
                self._escribir_wav(self._ruta_musica, pcm)
            except (IOError, OSError), e:
                # Sin scratch no hay musica, pero el juego sigue en silencio.
                sys.stderr.write('[audio] no se pudo escribir el temporal de audio (%s); '
                                 'la musica queda en silencio\n' % e)
                with self._lock:
                    self.reproduciendo_musica = False
                return
            objetivo, args = self._loop_mci, (pcm, generacion)
        else:
            with self._lock:
                self.reproduciendo_musica = False
            return

        self.hilo_musica = threading.Thread(target=objetivo, args=args)
        self.hilo_musica.daemon = True
        self.hilo_musica.start()

    def _esperar_hilo_musica(self):
        """Espera a que el hilo de musica anterior termine (o se rindan)."""
        hilo = self.hilo_musica
        if hilo is None or hilo is threading.current_thread():
            return
        hilo.join(2.0)
        if hilo.is_alive():
            sys.stderr.write('[audio] el hilo de la cancion anterior no termino a tiempo\n')
            return
        self.hilo_musica = None

    def detener_musica(self):
        """Corta la musica de inmediato."""
        with self._lock:
            self.reproduciendo_musica = False
        if IS_WIN and _mci:
            try:
                _mci('stop bgm', None, 0, 0)
                _mci('close bgm', None, 0, 0)
            except Exception:
                pass
        else:
            # Si no, el hijo queda huerfano sonando tras cerrar.
            with self._lock:
                proc, self._proc_musica = self._proc_musica, None
            self._matar(proc)

    # EFECTOS
    # -------

    def reproducir_efecto(self, pcm):
        """Reproduce un efecto una vez, sin cortar la musica."""
        if self.silenciado or not pcm or not self.disponible():
            return

        if IS_LINUX:
            def _sfz_linux():
                proc = self._lanzar_linux(pcm, es_musica=False)
                if proc is not None:
                    try:
                        proc.wait()
                    except Exception:
                        pass
                    self._olvidar(proc)
            t = threading.Thread(target=_sfz_linux)
            t.daemon = True
            t.start()
            return

        if IS_WIN and _mci and self._dir_temp:
            ruta, alias = self._efecto_nuevo()
            try:
                self._escribir_wav(ruta, pcm)
            except Exception:
                return

            def _sfz_mci():
                buf = ctypes.create_string_buffer(64)
                ruta_win = ruta.replace('/', '\\')
                try:
                    _mci('close %s' % alias, None, 0, 0)
                    _mci('open "%s" alias %s' % (ruta_win, alias), None, 0, 0)
                    _mci('play %s from 0' % alias, None, 0, 0)
                    # Solo se borra cuando MCI suelta el archivo.
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
            # ON_START no se repite: se relanza con los bytes guardados.
            self.musica_actual = None
            if self._pcm_actual:
                self.reproducir_musica_fondo(self._pcm_actual, self._firma_actual)
        return self.silenciado

    def detener_todo(self):
        """Libera todo. Se llama antes de destruir la ventana."""
        self.detener_musica()
        # Los efectos son procesos sueltos: antes seguian sonando tras cerrar.
        with self._lock:
            pendientes = list(self._procs_vivos)
            self._procs_vivos.clear()
        for proc in pendientes:
            self._matar(proc)
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