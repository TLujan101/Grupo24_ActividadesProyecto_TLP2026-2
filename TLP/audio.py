# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import threading

class GestorAudioNativo(object):
    def __init__(self, carpeta_sonidos="songs"):
        self.carpeta = carpeta_sonidos
        self.hilo_musica = None
        self.reproduciendo_musica = False
        self.silenciado = False
        self.proceso_musica = None
        self.procesos_efectos = []

    def reproducir_efecto(self, nombre_archivo):
        if self.silenciado:
            return

        ruta = os.path.abspath(os.path.join(self.carpeta, nombre_archivo))
        if not os.path.exists(ruta):
            return

        def _play():
            os_type = sys.platform
            cmd = []
            if os_type.startswith('win'):
                cmd = ['powershell', '-c', '(New-Object Media.SoundPlayer "{0}").PlaySync()'.format(ruta)]
            elif os_type.startswith('darwin'):
                cmd = ['afplay', ruta]
            elif os_type.startswith('linux'):
                cmd = ['aplay', '-q', ruta]

            if cmd:
                try:
                    p = subprocess.Popen(cmd)
                    self.procesos_efectos.append(p)
                    p.wait()
                    if p in self.procesos_efectos:
                        self.procesos_efectos.remove(p)
                except Exception as e:
                    print("Error al reproducir efecto:", e)

        hilo = threading.Thread(target=_play)
        hilo.daemon = True
        hilo.start()

    def reproducir_musica_fondo(self, nombre_archivo):
        # Detiene cualquier musica anterior primero
        self.detener_musica()

        if self.silenciado:
            return

        ruta = os.path.abspath(os.path.join(self.carpeta, nombre_archivo))
        if not os.path.exists(ruta):
            return

        self.reproduciendo_musica = True

        def _bucle_musica():
            os_type = sys.platform
            while self.reproduciendo_musica and not self.silenciado:
                cmd = []
                if os_type.startswith('win'):
                    cmd = ['powershell', '-c', '(New-Object Media.SoundPlayer "{0}").PlaySync()'.format(ruta)]
                elif os_type.startswith('darwin'):
                    cmd = ['afplay', ruta]
                elif os_type.startswith('linux'):
                    cmd = ['aplay', '-q', ruta]

                if cmd:
                    try:
                        self.proceso_musica = subprocess.Popen(cmd)
                        self.proceso_musica.wait()
                    except Exception:
                        break

        self.hilo_musica = threading.Thread(target=_bucle_musica)
        self.hilo_musica.daemon = True
        self.hilo_musica.start()

    def detener_musica(self):
        self.reproduciendo_musica = False
        if self.proceso_musica:
            try:
                self.proceso_musica.kill()
            except Exception:
                pass
            self.proceso_musica = None

    def alternar_silencio(self):
        self.silenciado = not self.silenciado
        if self.silenciado:
            self.detener_musica()
            # Detener efectos sonando
            for p in list(self.procesos_efectos):
                try:
                    p.kill()
                except Exception:
                    pass
            self.procesos_efectos = []
        return self.silenciado