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
#   - manejar_tecla(key):   que hacer con cada tecla (UP, DOWN, LEFT, RIGHT).
#   - ejecutar_accion(verbo, objeto, accion): acciones propias del juego.
#   - dibujar_elementos():  dibuja lo que no es la cuadricula fija.
#   - color_celda_grid(x, y): (opcional) color de una celda fija.

import sys
# Tkinter es la libreria GUI estandar de Python, compatible con 2.7
import Tkinter as tk

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
        # Configurar la accion al cerrar la ventana ('X' de la barra de titulo)
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

        # Nota: Se ha eliminado 'Q: Salir' de los controles en pantalla
        self.label_controles = tk.Label(self.marco_score, text="CONTROLES\nFlechas: Mover/Rotar", bg='#1e1e2e', fg='#03a80b', font=('Consolas', 10))
        self.label_controles.pack(pady=20, padx=10)

        # Configurar eventos de teclado. Usamos <Key> para capturar cualquier tecla
        self.root.bind('<Key>', self.manejar_input_gui)

        # Estado propio de cada juego (definido por la clase hija)
        self.inicializar_estado()

        self.timer_gravedad = 0
        self.ejecutar_evento('ON_START')
        self.timer_id = None # Para controlar el loop de Tkinter


    # METODOS QUE CADA JUEGO DEBE SOBREESCRIBIR
    # -----------------------------------------

    def inicializar_estado(self):
        # Debe crear las variables propias del juego y self.velocidad_gravedad
        raise NotImplementedError("El juego debe implementar inicializar_estado()")

    def manejar_tecla(self, key):
        # key es 'UP', 'DOWN', 'LEFT', 'RIGHT' u otra tecla en mayusculas
        raise NotImplementedError("El juego debe implementar manejar_tecla()")

    def ejecutar_accion(self, verbo, objeto, accion):
        # Acciones propias del juego (SPAWN, MOVE, ROTATE, GROW, ...)
        raise NotImplementedError("El juego debe implementar ejecutar_accion()")

    def dibujar_elementos(self):
        # Dibuja las piezas/jugadores que se mueven sobre la cuadricula
        raise NotImplementedError("El juego debe implementar dibujar_elementos()")

    def color_celda_grid(self, x, y):
        # Color de una celda fija de la cuadricula. Se puede sobreescribir.
        return COLOR_GRID_FIJA


    # CICLO DE JUEGO
    # --------------

    def run(self):
        # Inicia el ciclo principal de juego de Tkinter
        self.root.after(50, self.game_loop)
        self.root.mainloop()

    def game_loop(self):
        if self.juego_terminado:
            self.mostrar_game_over()
            return

        # Logica de TICK/Gravedad
        # El loop se ejecuta cada 50ms (0.05 segundos)
        self.timer_gravedad += 0.05
        if self.timer_gravedad >= self.velocidad_gravedad:
            self.timer_gravedad = 0
            self.ejecutar_evento('ON_TICK')

        self.dibujar()

        # Programa el siguiente ciclo de juego
        self.timer_id = self.root.after(50, self.game_loop)

    def cerrar_ventana(self):
        # Detiene el loop de juego de forma segura
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.root.destroy()
        sys.exit(0)


    # ENTRADA Y EVENTOS
    # -----------------

    def manejar_input_gui(self, event):
        key = event.keysym.upper()

        # La opcion de salir con 'Q' ha sido eliminada.

        # Cada juego decide que hace con la tecla
        self.manejar_tecla(key)

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

                # Acciones propias de cada juego
                self.ejecutar_accion(verbo, objeto, accion)


    # DIBUJO
    # ------

    def dibujar(self):
        self.frame += 1
        self.canvas.delete("all") # Borrar todo en cada frame
        self.label_score.config(text="PUNTUACION\n" + str(self.puntuacion))

        # 1. Dibujar la cuadricula estatica (grid base)
        for y in range(self.alto):
            for x in range(self.ancho):
                if self.grid[y][x] == 1:
                    self.dibujar_celda(x, y, self.color_celda_grid(x, y))

        # 2. Dibujar los elementos propios del juego
        self.dibujar_elementos()

    def dibujar_celda(self, x, y, color):
        ts = self.taman_celda # Alias para taman de celda
        x1, y1 = x * ts, y * ts
        x2, y2 = x1 + ts, y1 + ts
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='#000000')


    # METODOS DE SALIDA (ADAPTADOS A GUI)
    # -----------------------------------

    def mostrar_game_over(self):
        # Crear ventana emergente estilizada con Toplevel
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
            command=lambda: (self.root.destroy(), sys.exit(0))
        )
        btn_salir.pack(pady=20)
