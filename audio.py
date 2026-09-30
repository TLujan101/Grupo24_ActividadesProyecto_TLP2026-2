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
# OJO con paplay: --raw es una bandera SIN valor, el formato va aparte en
# --format=. Escribir '--raw=s16le' hace que pacat >= 15 salga al instante con
# "option '--raw' doesn't allow an argument", el pipe se rompe y el juego
# suena mudo sin avisar.
FORMATO_PCM = {'paplay': ['--raw', '--format=s16le', '--rate=%d' % tracker.FPS, '--channels=1'],
               'aplay':  ['-f', 'S16_LE', '-r', str(tracker.FPS), '-c', '1', '-t', 'raw']}


def _detectar_reproductor_linux():
    # Devuelve (comando, flags) del primer reproductor que este INSTALADO y de
    # verdad ACEPTE estos flags. Solo con 'which' no alcanza: un reproductor
    # puede estar presente y rechazar el formato, y entonces el juego suena
    # mudo sin explicar nada (pasaba con 'paplay --raw=s16le').
    #
    # El sondeo le manda entrada VACIA: no emite audio (nada que clickear) pero
    # obliga al proceso a parsear los flags y conectar con el destino. Codigo 0
    # y stderr vacio = sirve. Asi, si paplay falla, se prueba aplay en vez de
    # rendirse en silencio.
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
        """Vuelca el PCM en stdin. Aqui si se bloquea, a proposito: el pipe
        aplica contrapresion, asi que el reproductor marca el ritmo real y la
        cancion no adelanta. Bloquear dura lo que dura la cancion."""
        try:
            proc.stdin.write(pcm)
            proc.stdin.close()
        except Exception:
            pass

    def _lanzar_linux(self, pcm, es_musica):
        """Abre el reproductor, REGISTRA el hijo y despues inyecta el PCM.

        El orden importa: registrar despues de inyectar dejaba al proceso
        invisible durante toda la cancion (inyectar bloquea), y entonces ni
        el boton de silencio ni el cierre tenian a que matar.
        """
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
        # Saca un hijo del registro cuando ya termino (asi no crece sin fin).
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
        """Reserva un slot de efecto. Devuelve (archivo, alias) del MISMO numero.

        Antes el archivo se nombraba con un contador y el alias MCI se
        calculaba RE-LEYENDO ese contador despues, en otra seccion critica. Con
        efectos simultaneos los dos se desincronizaban: sfx_2.wav y sfx_10.wav
        acababan con el alias sfx_2, y el 'close sfx_2' del segundo cortaba el
        sonido del primero a media vuelta. Ahora salen del mismo numero, asi
        que un archivo y su alias siempre van juntos.
        """
        with self._lock:
            self._sfx_id += 1
            numero = self._sfx_id
        return (os.path.join(self._dir_temp, 'sfx_%d.wav' % numero),
                'sfx_%d' % (numero % 8))

    def _sigo_vivo(self, generacion):
        """True si ESTE hilo sigue siendo el dueno de la musica.

        'reproduciendo_musica' no alcanza: en un cambio de cancion o en un
        un-mute vuelve a True ANTES de que el hilo anterior termine, y entonces
        el viejo se cree vivo otra vez y los dos hilos mueven el mismo alias MCI
        'bgm'. La generacion sube con cada cancion pedida, asi que el hilo viejo
        se retira en cuanto hay una nueva.
        """
        with self._lock:
            return (self.reproduciendo_musica
                    and not self.silenciado
                    and self._generacion == generacion)

    # MUSICA DE FONDO
    # ----------------

    def _loop_linux(self, pcm, generacion):
        # Relanza el reproductor cada vez que termina la cancion. El pipe
        # aplica contrapresion, asi que escribir el PCM ya marca el ritmo.
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

        # El hilo solo cierra 'bgm' si sigue siendo el dueño: si otra cancion
        # ya tomó el alias, cerrarlo le cortaría el sonido a esta.
        if not self._sigo_vivo(generacion):
            with self._lock:
                es_mio = self._generacion == generacion
            if es_mio:
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

        # La generacion sube ANTES de tocar ninguna bandera: es lo que retira
        # al hilo de la cancion anterior. Si se hiciera despues, ese hilo
        # veria 'reproduciendo_musica' en True y creeria que sigue siendo el
        # dueno del alias 'bgm'.
        with self._lock:
            self._generacion += 1
            generacion = self._generacion
            self.musica_actual = firma
            self._pcm_actual = pcm
            self._firma_actual = firma
            self.reproduciendo_musica = True

        if IS_LINUX:
            objetivo, args = self._loop_linux, (pcm, generacion)
        elif IS_WIN and _mci and self._ruta_musica:
            try:
                self._escribir_wav(self._ruta_musica, pcm)
            except Exception:
                # Sin scratch no hay musica, pero no es motivo para tumbar el
                # juego: se sigue jugando en silencio.
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
            # Sin esto el proceso hijo queda huerfano sonando hasta que
            # termina su cancion, aunque el juego ya haya cerrado.
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
            # _efecto_nuevo() devuelve archivo y alias del MISMO numero, para
            # que dos efectos simultaneos no acaben compartiendo alias MCI.
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
            # Retomar. Antes solo se ponia musica_actual=None y se esperaba a
            # que el .brick pidiera la cancion otra vez, pero ON_START no
            # vuelve a dispararse: pulsar "Audio: ON" no hacia sonar nada.
            # _pcm_actual sigue teniendo los bytes, asi que se relanza directo.
            self.musica_actual = None
            if self._pcm_actual:
                self.reproducir_musica_fondo(self._pcm_actual, self._firma_actual)
        return self.silenciado

    def detener_todo(self):
        """Libera todo. Se llama antes de destruir la ventana."""
        self.detener_musica()
        # Los efectos de sonido son procesos sueltos, sin relacion con la
        # musica, y antes no se guardaban en ningun sitio: al cerrar el
        # juego seguian sonando solos.
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