# -*- coding: utf-8 -*-
# game.py --- Clase base de todos los juegos de BrickScript.
#
# Contiene SOLO lo comun a cualquier juego: la cuadricula, la puntuacion,
# la ventana de Tkinter, el ciclo de juego, el despacho de eventos y la
# pantalla de GAME OVER.
#
# Cada juego concreto (Tetris, Snake, ...) hereda de Game y sobreescribe
# estos metodos:
#   - inicializar_estado(): variables propias del juego y velocidad_gravedad.
#   - ejecutar_accion(verbo, objeto, accion): acciones propias del juego.
#   - dibujar_elementos():  dibuja lo que no es la cuadricula fija.
#   - color_celda_grid(x, y): (opcional) color de una celda fija.

import sys
import Tkinter as tk

from . import tracker
from .audio import GestorAudioNativo

COLOR_GRID_FIJA = '#343434' # Gris oscuro para las celdas fijadas


class Game(object):

    def __init__(self, datos_juego):
        self.frame = 0
        self.datos_juego = datos_juego
        self.tipo_juego = self.datos_juego.get('tipo_juego', 'TETRIS')
        config = self.datos_juego.get('config', {})
        self.ancho = config.get('grid_size', [10, 20])[0]
        self.alto = config.get('grid_size', [10, 20])[1]
        self.grid = [[0 for _ in range(self.ancho)] for _ in range(self.alto)]
        self.puntuacion = 0
        self.juego_terminado = False

        # --- Configuracion de la GUI ---
        self.root = tk.Tk()
        self.root.title("BrickScript - " + self.tipo_juego)
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_ventana)

        self.taman_celda = 25 # Pixeles por celda
        self.ancho_canvas = self.ancho * self.taman_celda
        self.alto_canvas = self.alto * self.taman_celda

        # Canvas para dibujar el juego
        self.canvas = tk.Canvas(self.root, width=self.ancho_canvas, height=self.alto_canvas, bg='#111111')
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)

        # Marco lateral para la puntuacion y controles
        self.marco_score = tk.Frame(self.root, width=150, height=self.alto_canvas, bg='#1e1e2e')
        self.marco_score.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        self.label_score = tk.Label(self.marco_score, text="PUNTUACION\n0", bg='#1e1e2e', fg='#03a80b', font=('Consolas', 16, 'bold'))
        self.label_score.pack(pady=40, padx=10)

        self.label_controles = tk.Label(self.marco_score, text="CONTROLES\nFlechas: Mover/Rotar", bg='#1e1e2e', fg='#03a80b', font=('Consolas', 10))
        self.label_controles.pack(pady=20, padx=10)

        # Boton de silencio (verde suena, gris no). Solo si el .brick
        # declara audio: si no, solo ocuparia espacio.
        self.audio = self.crear_audio()
        if self.tiene_audio():
            self.btn_sonido = tk.Button(self.marco_score, text="Audio: ON",
                                        command=self.toggle_audio,
                                        font=('Consolas', 10, 'bold'),
                                        bg='#2a2a3e', fg='#03a80b')
            self.btn_sonido.pack(pady=10, padx=10)

        self.root.bind('<Key>', self.manejar_input_gui)

        self.inicializar_estado()

        self._game_over_emitido = False
        self.timer_gravedad = 0
        self.ejecutar_evento('ON_START')
        self.timer_id = None


    # METODOS QUE CADA JUEGO DEBE SOBREESCRIBIR
    # -----------------------------------------

    def inicializar_estado(self):
        # Variables propias del juego y self.velocidad_gravedad.
        raise NotImplementedError("El juego debe implementar inicializar_estado()")

    def ejecutar_accion(self, verbo, objeto, accion):
        # Acciones propias del juego (SPAWN, MOVE, ROTATE, GROW, ...)
        raise NotImplementedError("El juego debe implementar ejecutar_accion()")

    def dibujar_elementos(self):
        # Piezas/jugadores sobre la cuadricula.
        raise NotImplementedError("El juego debe implementar dibujar_elementos()")

    def color_celda_grid(self, x, y):
        # Color de una celda fija. Sobreescribible.
        return COLOR_GRID_FIJA

    def animacion_borrado_activa(self):
        # Los juegos con borrado de filas (Tetris) lo sobreescriben.
        return False

    def avanzar_animacion_borrado(self):
        # Un frame de la animacion de borrado. Tetris lo sobreescribe.
        pass


    # AUDIO (opcional: sin SONG ni EFFECT el juego arranca en silencio)
    # -----

    def tiene_audio(self):
        # SONG o EFFECT declarados en el .brick.
        return bool(self.datos_juego.get('songs') or self.datos_juego.get('effects'))

    def crear_audio(self):
        # Los tests lo sobreescriben para no abrir sonido real.
        return GestorAudioNativo()

    def toggle_audio(self):
        silenciado = self.audio.alternar_silencio()
        if silenciado:
            self.btn_sonido.config(text="Audio: OFF", fg="#888888")
        else:
            self.btn_sonido.config(text="Audio: ON", fg="#03a80b")

    def musica_brick(self, nombre):
        # Sintetiza la cancion (queda en RAM) y la pone en bucle.
        canciones = self.datos_juego.get('songs', {})
        if not nombre or nombre not in canciones:
            return
        notas = canciones[nombre].get('notas', [])
        firma = tracker.firma_partitura(notas)

        # Idempotente: ON_START se re-dispara al fijar cada pieza.
        if firma == self.audio.musica_actual and self.audio.reproduciendo_musica:
            return

        pcm = tracker.cancion_pcm(nombre, notas)
        if not pcm:
            return
        self.audio.reproducir_musica_fondo(pcm, firma)

    def efecto_brick(self, nombre):
        # Un efecto se sintetiza igual que una cancion pero suena una vez.
        efectos = self.datos_juego.get('effects', {})
        if not nombre or nombre not in efectos:
            return
        notas = efectos[nombre].get('notas', [])
        pcm = tracker.cancion_pcm(nombre, notas)
        if not pcm:
            return
        self.audio.reproducir_efecto(pcm)


    # CICLO DE JUEGO
    # --------------

    def run(self):
        self.root.after(50, self.game_loop)
        self.root.mainloop()

    def game_loop(self):
        if self.juego_terminado:
            # ON_GAME_OVER se emite una sola vez.
            if not self._game_over_emitido:
                self._game_over_emitido = True
                self.ejecutar_evento('ON_GAME_OVER')
            self.mostrar_game_over()
            return

        # Animacion de borrado: el tablero queda congelado (sin gravedad) hasta
        # que el juego confirme el borrado de las lineas. El frame en que se
        # borra tambien dibuja y reprograma el loop como cualquier otro.
        if self.animacion_borrado_activa():
            self.avanzar_animacion_borrado()
        else:
            # Gravedad: el loop corre cada 50ms.
            self.timer_gravedad += 0.05
            if self.timer_gravedad >= self.velocidad_gravedad:
                self.timer_gravedad = 0
                self.ejecutar_evento('ON_TICK')

        self.dibujar()

        self.timer_id = self.root.after(50, self.game_loop)

    def cerrar_ventana(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        # Suelta el audio antes de destruir: si no, queda sonido sonando.
        try:
            self.audio.detener_todo()
        except Exception:
            pass
        self.root.destroy()
        sys.exit(0)


    # ENTRADA Y EVENTOS
    # -----------------

    def manejar_input_gui(self, event):
        key = event.keysym.upper()
        self.manejar_tecla(key)

    def manejar_tecla(self, key):
        # Las flechas disparan ON_KEY_*; cada juego decide la accion.
        if key in ('UP', 'DOWN', 'LEFT', 'RIGHT'):
            self.ejecutar_evento('ON_KEY_' + key)

    def ejecutar_evento(self, nombre_evento):
        if nombre_evento in self.datos_juego['events']:
            for accion in self.datos_juego['events'][nombre_evento]:
                verbo, objeto = accion.get('accion'), accion.get('objeto')

                if verbo == 'INCREASE_SCORE':
                    try:
                        self.puntuacion += int(objeto)
                    except (ValueError, TypeError):
                        pass
                if verbo == 'GAME_OVER': self.juego_terminado = True

                # Audio declarado en el .brick
                if verbo == 'PLAY_MUSIC': self.musica_brick(objeto)
                if verbo == 'PLAY_EFFECT': self.efecto_brick(objeto)
                if verbo == 'STOP_MUSIC': self.audio.detener_musica()

                # Acciones propias de cada juego
                self.ejecutar_accion(verbo, objeto, accion)


    # DIBUJO
    # ------

    def dibujar(self):
        self.frame += 1
        self.canvas.delete("all")
        self.label_score.config(text="PUNTUACION\n" + str(self.puntuacion))

        # 1. Dibujar la cuadricula estatica (grid base)
        for y in range(self.alto):
            for x in range(self.ancho):
                if self.grid[y][x] == 1:
                    self.dibujar_celda(x, y, self.color_celda_grid(x, y))

        # 2. Dibujar los elementos propios del juego
        self.dibujar_elementos()

    def dibujar_celda(self, x, y, color):
        x1, y1 = x * self.taman_celda, y * self.taman_celda
        x2, y2 = x1 + self.taman_celda, y1 + self.taman_celda
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='#000000')


    # METODOS DE SALIDA (ADAPTADOS A GUI)
    # -----------------------------------

    def mostrar_game_over(self):
        top = tk.Toplevel(self.root)
        top.title("Game Over")
        top.geometry("320x200")
        top.configure(bg="#1e1e2e")
        top.resizable(False, False)

        top.transient(self.root)

        lbl_titulo = tk.Label(
            top,
            text=u"FIN DEL JUEGO",
            font=("Consolas", 16, "bold"),
            fg="#03a80b",
            bg="#1e1e2e"
        )
        lbl_titulo.pack(pady=(25, 10))

        lbl_score = tk.Label(
            top,
            text="Puntuacion Final: {}".format(self.puntuacion),
            font=("Consolas", 12),
            fg="#03a80b",
            bg="#1e1e2e"
        )
        lbl_score.pack(pady=5)

        btn_salir = tk.Button(
            top,
            text="Aceptar",
            font=("Consolas", 10, "bold"),
            bg="#03a80b",
            fg="#1e1e2e",
            activebackground="#027b08",
            activeforeground="#1e1e2e",
            bd=0,
            padx=20,
            pady=5,
            # Misma salida que la X: tambien suelta el audio.
            command=self.cerrar_ventana
        )
        btn_salir.pack(pady=20)
