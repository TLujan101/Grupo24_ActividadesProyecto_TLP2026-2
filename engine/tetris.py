# -*- coding: utf-8 -*-
# tetris.py --- Juego TETRIS (GAME_TYPE TETRIS). Hereda todo lo basico de Game.

import random
import Tkinter as tk

from .game import Game
from .utilidades import Colores, Arcoiris, eleccion_ponderada


class Tetris(Game):

    # CONFIGURACION PROPIA DEL JUEGO (sobreescribe a Game)
    # ----------------------------------------------------

    def inicializar_estado(self):
        self.pieza_actual = None
        self.pieza_color = "#00FFFF"
        self.pieza_es_arcoiris = False
        self.siguiente_powerup = None
        self._nombres_piezas = []
        self._pesos_piezas = []
        for NombrePool in self.datos_juego['shapes'].keys():
            if NombrePool == 'POWERUP':
                continue
            DatosPool = self.datos_juego['shapes'][NombrePool]
            if isinstance(DatosPool, dict):
                PesoPool = int(DatosPool.get('chance', 10))
            else:
                PesoPool = 10
            self._nombres_piezas.append(NombrePool)
            self._pesos_piezas.append(PesoPool)
        self.pieza_x, self.pieza_y, self.pieza_rotacion = 0, 0, 0
        self.velocidad_gravedad = 0.4

    def ejecutar_accion(self, verbo, objeto, accion):
        if verbo == 'SPAWN': self.tetris_spawn_pieza()
        if verbo == 'MOVE': self.tetris_mover_pieza(accion['params'][0])
        if verbo == 'ROTATE': self.tetris_rotar_pieza()

    def dibujar_elementos(self):
        # Dibujar la pieza actual de Tetris
        if self.pieza_actual:
            matriz_pieza = self.pieza_actual[self.pieza_rotacion]
            for y_offset, fila in enumerate(matriz_pieza):
                for x_offset, celda in enumerate(fila):
                    if celda == 1:
                        if getattr(self, 'pieza_es_arcoiris', False):
                            color = Arcoiris[(self.frame // 6) % len(Arcoiris)]
                        else:
                            color = self.pieza_color
                        self.dibujar_celda(self.pieza_x + x_offset, self.pieza_y + y_offset, color)


    # METODOS DE LOGICA DE JUEGO
    # --------------------------

    def mostrar_notificacion_powerup(self, nombre_powerup):
        if nombre_powerup == "SUPERBOMBA":
            texto_notif = "Power Up:SUPERBOMBA"
        elif nombre_powerup == "CLEAR_LINE_PIECE":
            texto_notif = "Power Up:LIMPIA LINEAS"
        elif nombre_powerup == "CLEAR_THREE_PIECE":
            texto_notif = "Power Up:LIMPIA COLUMNAS"
        elif nombre_powerup == "POWERUP":
                    texto_notif = "Power Up:BOMBA"
        else:
            return

        notif = tk.Label(
            self.root,
            text=texto_notif,
            font=("Consolas", 11, "bold"),
            bg="#1e1e2e",
            fg="#00ff22",
            bd=2,
            relief="solid",
            padx=12,
            pady=6
        )

        # Posicionar en la esquina superior derecha
        notif.place(relx=0.95, rely=0.03, anchor="ne")

        self.root.after(2500, notif.destroy)

    def tetris_spawn_pieza(self):
        if self.siguiente_powerup:
            nombre_pieza = self.siguiente_powerup
            self.siguiente_powerup = None
        else:
            nombre_pieza = eleccion_ponderada(self._nombres_piezas, self._pesos_piezas)

        self.pieza_nombre = nombre_pieza

        Datos = self.datos_juego['shapes'][nombre_pieza]
        if isinstance(Datos, dict):
            self.pieza_actual = Datos["estados"]
            # Asignamos el color original definido en la forma o RAINBOW
            self.pieza_color = Colores.get(Datos.get("color", "CYAN"), "#00FFFF")
            self.pieza_es_arcoiris = (Datos.get("color", "CYAN") == "RAINBOW")
        else:
            self.pieza_actual = Datos
            self.pieza_color = "#00FFFF"
            self.pieza_es_arcoiris = False

        self.pieza_x, self.pieza_y, self.pieza_rotacion = self.ancho // 2 - 1, 0, 0
        if self.tetris_verificar_colision(self.pieza_x, self.pieza_y, self.pieza_rotacion):
            self.juego_terminado = True

    def tetris_mover_pieza(self, direccion):
        if not self.pieza_actual: return
        dx, dy = 0, 0
        if direccion == 'LEFT': dx = -1
        elif direccion == 'RIGHT': dx = 1
        elif direccion == 'DOWN': dy = 1
        if not self.tetris_verificar_colision(self.pieza_x + dx, self.pieza_y + dy, self.pieza_rotacion):
            self.pieza_x += dx
            self.pieza_y += dy
        elif dy > 0:
            self.tetris_fijar_pieza()

    def tetris_rotar_pieza(self):
        if not self.pieza_actual: return
        nueva_rotacion = (self.pieza_rotacion + 1) % len(self.pieza_actual)
        if not self.tetris_verificar_colision(self.pieza_x, self.pieza_y, nueva_rotacion):
            self.pieza_rotacion = nueva_rotacion
            # Solo si la rotacion se pudo hacer: un .brick con
            # ON ROTATE: PLAY_EFFECT ... suena al rotar de verdad.
            self.ejecutar_evento('ON_ROTATE')

    def tetris_aplicar_gravedad(self):
        # Tras una explosion o limpieza quedan celdas flotando: compacta cada
        # columna hacia abajo conservando el orden de las que sobreviven.
        for x in range(self.ancho):
            Columna = [self.grid[y][x] for y in range(self.alto) if self.grid[y][x] != 0]
            for y in range(self.alto):
                if y < len(Columna):
                    self.grid[self.alto - 1 - y][x] = Columna[len(Columna) - 1 - y]
                else:
                    self.grid[self.alto - 1 - y][x] = 0

    def tetris_fijar_pieza(self):
        matriz_pieza = self.pieza_actual[self.pieza_rotacion]

        es_bomba = (getattr(self, 'pieza_nombre', '') == 'POWERUP')
        es_limpia_filas = (getattr(self, 'pieza_nombre', '') == 'CLEAR_LINE_PIECE')
        es_superbomba = (getattr(self, 'pieza_nombre', '') == 'SUPERBOMBA')
        es_limpia_columnas = (getattr(self, 'pieza_nombre', '') == 'CLEAR_THREE_PIECE')

        if es_bomba:
            centro_x, centro_y = int(self.pieza_x), int(self.pieza_y)
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    nx, ny = centro_x + dx, centro_y + dy
                    if 0 <= ny < self.alto and 0 <= nx < self.ancho:
                        self.grid[ny][nx] = 0
            self.puntuacion += 150
            self.ejecutar_evento('ON_EXPLOSION')
            self.tetris_aplicar_gravedad()

        elif es_superbomba:
            base_x, base_y = int(self.pieza_x), int(self.pieza_y)

            for dy in range(-1, 4):
                for dx in range(-1, 4):
                    nx = base_x + dx
                    ny = base_y + dy
                    if 0 <= ny < self.alto and 0 <= nx < self.ancho:
                        self.grid[ny][nx] = 0
            self.puntuacion += 350
            self.ejecutar_evento('ON_EXPLOSION')
            self.tetris_aplicar_gravedad()

        elif es_limpia_columnas:
            columnas_a_borrar = set()

            for y_offset, fila in enumerate(matriz_pieza):
                for x_offset, celda in enumerate(fila):
                    if celda == 1:
                        px = int(self.pieza_x + x_offset)
                        if 0 <= px < self.ancho:
                            columnas_a_borrar.add(px)

            for px in columnas_a_borrar:
                for py in range(self.alto):
                    self.grid[py][px] = 0

            self.puntuacion += len(columnas_a_borrar) * 250
            self.tetris_aplicar_gravedad()

        elif es_limpia_filas:
            filas_a_borrar = set()
            for y_offset, fila in enumerate(matriz_pieza):
                for x_offset, celda in enumerate(fila):
                    if celda == 1:
                        py = int(self.pieza_y + y_offset)
                        if 0 <= py < self.alto:
                            filas_a_borrar.add(py)

            for py in filas_a_borrar:
                self.grid[py] = [0] * self.ancho

            for py in sorted(list(filas_a_borrar)):
                self.grid.pop(py)
                self.grid.insert(0, [0] * self.ancho)

            self.puntuacion += len(filas_a_borrar) * 200

        else:
            for y_offset, fila in enumerate(matriz_pieza):
                for x_offset, celda in enumerate(fila):
                    if celda == 1:
                        px = int(self.pieza_x + x_offset)
                        py = int(self.pieza_y + y_offset)
                        if 0 <= py < self.alto and 0 <= px < self.ancho:
                            self.grid[py][px] = 1

        self.pieza_actual = None
        # Toda pieza que llega al suelo dispara este evento, sin importar si
        # era normal o un power-up. Los poderes con radio (bomba, superbomba)
        # disparan ademas ON_EXPLOSION.
        self.ejecutar_evento('ON_PIECE_LAND')
        self.tetris_limpiar_lineas()
        self.ejecutar_evento('ON_START')

    def tetris_verificar_colision(self, x, y, rotacion):
        if not self.pieza_actual: return False
        matriz_pieza = self.pieza_actual[rotacion]
        for y_offset, fila in enumerate(matriz_pieza):
            for x_offset, celda in enumerate(fila):
                if celda == 1:
                    nuevo_x, nuevo_y = x + x_offset, y + y_offset
                    if not (0 <= nuevo_x < self.ancho and 0 <= nuevo_y < self.alto and self.grid[nuevo_y][nuevo_x] == 0):
                        return True
        return False

    def tetris_limpiar_lineas(self):
        Llenas = [i for i, fila in enumerate(self.grid) if all(fila)]
        lineas_limpias = len(Llenas)
        if lineas_limpias == 0:
            return
        self.grid = [[0] * self.ancho for _ in range(lineas_limpias)] + [fila for i, fila in enumerate(self.grid) if i not in Llenas]
        for _ in range(lineas_limpias): self.ejecutar_evento('ON_LINE_CLEAR')
        # Triple (>= 3) da premio; simple/doble solo puntaje.
        if lineas_limpias >= 3:
            eleccion = random.random()
            if eleccion < 0.25:
                candidato = 'POWERUP'
            elif eleccion < 0.45:
                candidato = 'CLEAR_LINE_PIECE'
            elif eleccion < 0.65:
                candidato = 'SUPERBOMBA'
            elif eleccion < 0.80:
                candidato = "CLEAR_THREE_PIECE"
            else:
                candidato = None
            # Solo vale si el .brick define esa forma; si no, no hay premio.
            if candidato in self.datos_juego['shapes']:
                self.siguiente_powerup = candidato
                self.mostrar_notificacion_powerup(self.siguiente_powerup)
            else:
                self.siguiente_powerup = None
