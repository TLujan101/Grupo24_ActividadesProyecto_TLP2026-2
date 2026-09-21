# -*- coding: utf-8 -*-
# runtime.py (VERSION CON INTERFAZ GRAFICA USANDO Tkinter y caracteres ASCII unicamente)

import sys
import os
import json
import time
import random
import bisect
import Tkinter as tk # type: ignore
import tkMessageBox # type: ignore
from audio import GestorAudioNativo
try:
    import tracker as MotorCanciones
except ImportError:
    MotorCanciones = None

Colores = {
    "CYAN": "#00FFFF",
    "YELLOW": "#FFFF00",
    "PURPLE": "#AA00FF",
    "GREEN": "#00FF00",
    "RED": "#FF0000",
    "BLUE": "#0000FF",
    "ORANGE": "#FF7F00",
    "WHITE": "#FFFFFF",
    "BLACK": "#000000",
    "RAINBOW": "#FFFFFF"
}
Arcoiris = ["#FF0000","#FF7F00","#FFFF00","#00FF00","#0000FF","#AA00FF"]

def eleccion_ponderada(items, pesos):
    if len(items) != len(pesos):
        raise ValueError("items y pesos deben tener la misma longitud")
    acum = []
    s = 0
    for w in pesos:
        s += w
        acum.append(s)
    if s <= 0:
        raise ValueError("Los pesos deben sumar > 0")
    tiro = random.randint(1, s)
    return items[bisect.bisect_left(acum, tiro)]


class Juego:
    def mostrar_notificacion_powerup(self, nombre_powerup):
        if nombre_powerup == "SUPERBOMBA":
            texto_notif = "Power Up:SUPERBOMBA"
        elif nombre_powerup == "CLEAR_LINE_PIECE":
            texto_notif = "Power Up:LIMPIA LINEAS"
        elif nombre_powerup == "CLEAR_THREE_PIECE":
            texto_notif = "Power Up:LIMPIA COLUMNAS"
        elif nombre_powerup == "POWERUP":
            texto_notif = "Power Up:BOMBA"
                    
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
        
        notif.place(relx=0.95, rely=0.03, anchor="ne")
        self.root.after(2500, notif.destroy)

    def __init__(self, datos_juego):
        self.frame = 0
        self.datos_juego = datos_juego
        self.tipo_juego = self.datos_juego.get('tipo_juego', 'TETRIS')
        config = self.datos_juego.get('config', {})
        self.ancho = config.get('grid_size', [10, 20])[0]
        self.alto = config.get('grid_size', [10, 20])[1]
        self.grid = [[0 for _ in range(self.ancho)] for _ in range(self.alto)]
        self.rainbow_grid = [[False for _ in range(self.ancho)] for _ in range(self.alto)]
        self.puntuacion = 0
        self.juego_terminado = False

        self.lineas_animandose = []       #Lista de índices de filas a eliminar
        self.frames_animacion_lineas = 0   #Contador de frames
        self.max_frames_animacion = 6     #Duración de la animación en frames

        self.root = tk.Tk()
        self.root.title("BrickScript - " + self.tipo_juego)
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_ventana)

        self.taman_celda = 25 
        self.ancho_canvas = self.ancho * self.taman_celda
        self.alto_canvas = self.alto * self.taman_celda

        self.canvas = tk.Canvas(self.root, width=self.ancho_canvas, height=self.alto_canvas, bg='#111111')
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)

        self.marco_score = tk.Frame(self.root, width=150, height=self.alto_canvas, bg='#1e1e2e')
        self.marco_score.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        self.label_score = tk.Label(self.marco_score, text="PUNTUACION\n0", bg='#1e1e2e', fg='#03a80b', font=('Consolas', 16, 'bold'))
        self.label_score.pack(pady=40, padx=10)

        self.label_controles = tk.Label(self.marco_score, text="CONTROLES\nFlechas: Mover/Rotar", bg='#1e1e2e', fg='#03a80b', font=('Consolas', 10))
        self.label_controles.pack(pady=20, padx=10)

        self.root.bind('<Key>', self.manejar_input_gui)

        self.btn_sonido = tk.Button(
            self.marco_score, 
            text="Audio: ON", 
            command=self.toggle_audio,
            font=("Consolas", 10, "bold"),
            bg="#2a2a3e",
            fg="#03a80b",
            activebackground="#3e3e5e",
            activeforeground="#00ff22",
            relief="groove",
            bd=1,
            padx=8,
            pady=4
        )
        self.btn_sonido.pack(pady=20, padx=10)

        self.audio = GestorAudioNativo("songs")
        # La musica y los efectos solo vienen del .brick
        # (PLAY_MUSIC/PLAY_EFFECT); sin SONG/EFFECT arranca en silencio.

        if self.tipo_juego == 'TETRIS':
            self.pieza_actual = None
            self.pieza_color = "#00FFFF"
            self.powerup_pendiente = False
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

        if self.tipo_juego == 'SNAKE':
            self.serpiente_cuerpo = []
            self.serpiente_direccion = (1, 0)
            self.posicion_comida = None
            self.velocidad_gravedad = 0.15

        self.timer_gravedad = 0
        self.ejecutar_evento('ON_START')
        self.timer_id = None 

    def toggle_audio(self):
        es_silencioso = self.audio.alternar_silencio()
        if es_silencioso:
            self.btn_sonido.config(text="Audio: OFF", fg="#888888")
        else:
            self.btn_sonido.config(text="Audio: ON", fg="#03a80b")


    def run(self):
        self.root.after(50, self.game_loop)
        self.root.mainloop()

    def game_loop(self):
        if self.juego_terminado:
            self.mostrar_game_over()
            return

        if self.lineas_animandose:
            self.frames_animacion_lineas = self.frames_animacion_lineas + 1
            if self.frames_animacion_lineas >= self.max_frames_animacion:
                self.aplicar_borrado_lineas()
            self.dibujar()
            self.timer_id = self.root.after(50, self.game_loop)
            return 

        self.timer_gravedad = self.timer_gravedad + 0.05
        if self.timer_gravedad >= self.velocidad_gravedad:
            self.timer_gravedad = 0
            self.ejecutar_evento('ON_TICK')

        self.dibujar()
        self.timer_id = self.root.after(50, self.game_loop)

    def cerrar_ventana(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.audio.detener_todo()
        self.root.destroy()
        os._exit(0)

    def manejar_input_gui(self, event):
        #Bloquear controles mientras se reproduce la animación de borrado
        if self.lineas_animandose:
            return

        key = event.keysym.upper()

        if self.tipo_juego == 'TETRIS':
            if key == 'UP': self.ejecutar_evento('ON_KEY_UP')
            elif key == 'DOWN': self.ejecutar_evento('ON_KEY_DOWN')
            elif key == 'LEFT': self.ejecutar_evento('ON_KEY_LEFT')
            elif key == 'RIGHT': self.ejecutar_evento('ON_KEY_RIGHT')
        elif self.tipo_juego == 'SNAKE':
            if key == 'UP': self.snake_cambiar_direccion('UP')
            elif key == 'DOWN': self.snake_cambiar_direccion('DOWN')
            elif key == 'LEFT': self.snake_cambiar_direccion('LEFT')
            elif key == 'RIGHT': self.snake_cambiar_direccion('RIGHT')

    def dibujar(self):
            self.frame += 1
            self.canvas.delete("all") 
            self.label_score.config(text="PUNTUACION\n" + str(self.puntuacion))

            COLOR_GRID_FIJA = '#343434' 
            COLOR_SNAKE_CABEZA = '#00FF00' 
            COLOR_SNAKE_CUERPO = '#33CC33' 
            COLOR_FOOD = '#FF0000'      

            for y in range(self.alto):
                for x in range(self.ancho):
                    if self.grid[y][x] == 1:
                        # Verifica si la celda (x, y) o la fila 'y' está en proceso de animación
                        if (x, y) in self.lineas_animandose or y in self.lineas_animandose:
                            if self.frames_animacion_lineas % 2 == 0:
                                color = '#FFFFFF'
                            else:
                                color = '#555555'
                        elif self.rainbow_grid[y][x]:
                            color = Arcoiris[(self.frame // 6) % len(Arcoiris)]
                        else:
                            color = COLOR_GRID_FIJA

                        self.dibujar_celda(x, y, color)

            # 2. Dibujar la pieza actual de Tetris
            if self.tipo_juego == 'TETRIS' and self.pieza_actual and not self.lineas_animandose:
                matriz_pieza = self.pieza_actual[self.pieza_rotacion]
                for y_offset, fila in enumerate(matriz_pieza):
                    for x_offset, celda in enumerate(fila):
                        if celda == 1:
                            if self.pieza_color == Colores.get("RAINBOW", "#FFFFFF"):
                                color = Arcoiris[(self.frame // 6) % len(Arcoiris)]
                            else:
                                color = self.pieza_color
                            self.dibujar_celda(self.pieza_x + x_offset, self.pieza_y + y_offset, color)

            # 3. Dibujar Snake y Comida
            if self.tipo_juego == 'SNAKE':
                if self.posicion_comida:
                    x, y = self.posicion_comida
                    self.dibujar_celda(x, y, COLOR_FOOD)
                for i, segmento in enumerate(self.serpiente_cuerpo):
                    x, y = segmento
                    color = COLOR_SNAKE_CABEZA if i == 0 else COLOR_SNAKE_CUERPO
                    self.dibujar_celda(x, y, color)

    def dibujar_celda(self, x, y, color):
        ts = self.taman_celda 
        x1, y1 = x * ts, y * ts
        x2, y2 = x1 + ts, y1 + ts
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='#000000')

    def ejecutar_evento(self, nombre_evento):
        if nombre_evento in self.datos_juego['events']:
            for accion in self.datos_juego['events'][nombre_evento]:
                verbo, objeto = accion.get('accion'), accion.get('objeto')

                if verbo == 'INCREASE_SCORE': self.puntuacion += int(objeto)
                if verbo == 'GAME_OVER': self.juego_terminado = True
                if verbo == 'PLAY_MUSIC': self.musica_brick(objeto)
                if verbo == 'STOP_MUSIC': self.audio.detener_musica()
                if verbo == 'PLAY_EFFECT': self.efecto_brick(objeto)

                if self.tipo_juego == 'TETRIS':
                    if verbo == 'SPAWN': self.tetris_spawn_pieza()
                    if verbo == 'MOVE': self.tetris_mover_pieza(accion['params'][0])
                    if verbo == 'ROTATE': self.tetris_rotar_pieza()

                if self.tipo_juego == 'SNAKE':
                    if verbo == 'SPAWN' and objeto == 'PLAYER': self.snake_spawn_jugador(accion)
                    if verbo == 'SPAWN' and objeto == 'FOOD': self.snake_spawn_comida()
                    if verbo == 'MOVE' and objeto == 'PLAYER': self.snake_mover_jugador()

    def musica_brick(self, nombre):
        # Musica programada en el .brick (opcional): sintetiza y reproduce.
        canciones = self.datos_juego.get('songs', {})
        if not nombre or nombre not in canciones:
            return
        if MotorCanciones is None:
            return
        ruta = MotorCanciones.ruta_cancion(nombre, canciones[nombre].get('notas', []))
        if not ruta:
            return
        # Idempotente: ON_START se re-dispara en cada spawn; si el tema
        # ya suena no se reinicia.
        if self.audio.musica_actual != ruta or not self.audio.reproduciendo_musica:
            self.audio.reproducir_musica_fondo(ruta)

    def efecto_brick(self, nombre):
        # Efecto programado en el .brick: se sintetiza igual que una
        # cancion pero suena una sola vez (no en loop).
        efectos = self.datos_juego.get('effects', {})
        if not nombre or nombre not in efectos:
            return
        if MotorCanciones is None:
            return
        ruta = MotorCanciones.ruta_cancion(nombre, efectos[nombre].get('notas', []))
        if ruta:
            self.audio.reproducir_efecto(ruta)


    def tetris_spawn_pieza(self):
        if hasattr(self, 'siguiente_powerup') and self.siguiente_powerup:
            nombre_pieza = self.siguiente_powerup
            self.siguiente_powerup = None
        else:
            nombre_pieza = eleccion_ponderada(self._nombres_piezas, self._pesos_piezas)
        
        self.pieza_nombre = nombre_pieza

        Datos = self.datos_juego['shapes'][nombre_pieza]
        if isinstance(Datos, dict):
            self.pieza_actual = Datos["estados"]
            self.pieza_color = Colores.get(Datos.get("color", "CYAN"), "#00FFFF")
        else:
            self.pieza_actual = Datos
            self.pieza_color = "#00FFFF"

        self.pieza_x, self.pieza_y, self.pieza_rotacion = self.ancho / 2 - 1, 0, 0
        if self.tetris_verificar_colision(self.pieza_x, self.pieza_y, self.pieza_rotacion):
            self.juego_terminado = True

    def tetris_mover_pieza(self, direccion):
        if not self.pieza_actual or self.lineas_animandose: return
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
        if not self.pieza_actual or self.lineas_animandose: return
        nueva_rotacion = (self.pieza_rotacion + 1) % len(self.pieza_actual)
        if not self.tetris_verificar_colision(self.pieza_x, self.pieza_y, nueva_rotacion):
            self.pieza_rotacion = nueva_rotacion
            # Guarda anti-recursion: si el .brick pone ROTATE dentro de
            # ON ROTATE, la accion interna rota una vez mas sin re-disparar.
            if not getattr(self, '_en_rotate', False):
                self._en_rotate = True
                try:
                    self.ejecutar_evento('ON_ROTATE')
                finally:
                    self._en_rotate = False

    def tetris_fijar_pieza(self):
        matriz_pieza = self.pieza_actual[self.pieza_rotacion]

        es_bomba = (getattr(self, 'pieza_nombre', '') == 'POWERUP')
        es_limpia_filas = (getattr(self, 'pieza_nombre', '') == 'CLEAR_LINE_PIECE')
        es_superbomba = (getattr(self, 'pieza_nombre', '') == 'SUPERBOMBA')
        es_limpia_columnas = (getattr(self, 'pieza_nombre', '') == 'CLEAR_THREE_PIECE')

        if es_bomba:
            centro_x, centro_y = int(self.pieza_x), int(self.pieza_y)
            celdas_afectadas = []
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    nx, ny = centro_x + dx, centro_y + dy
                    if 0 <= ny < self.alto and 0 <= nx < self.ancho:
                        if self.grid[ny][nx] == 1:
                            celdas_afectadas.append((nx, ny))
                            
            self.lineas_animandose = celdas_afectadas
            self.frames_animacion_lineas = 0
            self.puntuacion += 150

        elif es_superbomba:
            base_x, base_y = int(self.pieza_x), int(self.pieza_y)
            celdas_afectadas = []
            for dy in range(-1, 4):
                for dx in range(-1, 4):
                    nx, ny = base_x + dx, base_y + dy
                    if 0 <= ny < self.alto and 0 <= nx < self.ancho:
                        if self.grid[ny][nx] == 1:
                            celdas_afectadas.append((nx, ny))

            self.lineas_animandose = celdas_afectadas
            self.frames_animacion_lineas = 0
            self.puntuacion += 350
            
        elif es_limpia_columnas:
            columnas_a_borrar = set()
            for y_offset, fila in enumerate(matriz_pieza):
                for x_offset, celda in enumerate(fila):
                    if celda == 1:
                        px = int(self.pieza_x + x_offset)
                        if 0 <= px < self.ancho:
                            columnas_a_borrar.add(px)

            celdas_afectadas = []
            for px in columnas_a_borrar:
                for py in range(self.alto):
                    if self.grid[py][px] == 1:
                        celdas_afectadas.append((px, py))
                    
            self.lineas_animandose = celdas_afectadas
            self.frames_animacion_lineas = 0
            self.puntuacion += len(columnas_a_borrar) * 250

        elif es_limpia_filas:
            filas_a_borrar = set()
            for y_offset, fila in enumerate(matriz_pieza):
                for x_offset, celda in enumerate(fila):
                    if celda == 1:
                        py = int(self.pieza_y + y_offset)
                        if 0 <= py < self.alto:
                            filas_a_borrar.add(py)

            self.lineas_animandose = list(filas_a_borrar)
            self.frames_animacion_lineas = 0
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
        
        # Si no hubo un powerup activado, verificamos lineas normales
        if not self.lineas_animandose:
            self.tetris_limpiar_lineas()
        
        if not self.lineas_animandose:
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

    # --- MODIFICADO: Solo detecta filas completas e inicia la animación ---
    def tetris_limpiar_lineas(self):
        Llenas = [i for i, fila in enumerate(self.grid) if all(fila)]
        if len(Llenas) == 0:
            return

        # Guardar índices para la animación y reiniciar contador
        self.lineas_animandose = Llenas
        self.frames_animacion_lineas = 0

    def aplicar_borrado_lineas(self):
        # Si la lista contiene tuplas (x, y), proviene de Bombas o Limpia Columnas
        if self.lineas_animandose and isinstance(self.lineas_animandose[0], tuple):
            self.ejecutar_evento('ON_EXPLOSION')
            for cx, cy in self.lineas_animandose:
                if 0 <= cy < self.alto and 0 <= cx < self.ancho:
                    self.grid[cy][cx] = 0
                    self.rainbow_grid[cy][cx] = False

        # De lo contrario, son enteros de filas (por Tetris estándar o Limpia Filas)
        else:
            Llenas = self.lineas_animandose
            lineas_limpias = len(Llenas)

            if lineas_limpias > 0:
                Bonus = sum(1 for i in Llenas for x in range(self.ancho) if self.rainbow_grid[i][x])
                self.grid = [[0] * self.ancho for _ in range(lineas_limpias)] + [
                    fila for i, fila in enumerate(self.grid) if i not in Llenas
                ]
                self.rainbow_grid = [[False] * self.ancho for _ in range(lineas_limpias)] + [
                    fila for i, fila in enumerate(self.rainbow_grid) if i not in Llenas
                ]

                for _ in range(lineas_limpias): self.ejecutar_evento('ON_LINE_CLEAR')
                for _ in range(Bonus): self.ejecutar_evento('ON_RAINBOW_LINE_CLEAR')

                # Probabilidad de otorgar Power-Up al limpiar líneas
                eleccion = random.random()
                if eleccion < 0.25:
                    self.siguiente_powerup = 'POWERUP'
                    self.mostrar_notificacion_powerup(self.siguiente_powerup)
                elif 0.25 <= eleccion < 0.45:
                    self.siguiente_powerup = 'CLEAR_LINE_PIECE'
                    self.mostrar_notificacion_powerup(self.siguiente_powerup)
                elif 0.45 <= eleccion < 0.65:
                    self.siguiente_powerup = 'SUPERBOMBA'
                    self.mostrar_notificacion_powerup(self.siguiente_powerup)
                elif 0.65 <= eleccion < 0.80:
                    self.siguiente_powerup = "CLEAR_THREE_PIECE"
                    self.mostrar_notificacion_powerup(self.siguiente_powerup)
                else:
                    self.siguiente_powerup = None

        # Reiniciar la lista de animación y solicitar nueva pieza
        self.lineas_animandose = []
        self.ejecutar_evento('ON_START')


    def snake_spawn_jugador(self, accion):
        coords = accion['params'][0] if accion['params'] else [self.ancho / 2, self.alto / 2]
        self.serpiente_cuerpo = [(coords[0], coords[1])]
        self.serpiente_direccion = (1, 0)

    def snake_spawn_comida(self):
        while True:
            x, y = random.randint(0, self.ancho - 1), random.randint(0, self.alto - 1)
            if (x, y) not in self.serpiente_cuerpo:
                self.posicion_comida = (x, y)
                break

    def snake_mover_jugador(self):
        if not self.serpiente_cuerpo: return
        cabeza_x, cabeza_y = self.serpiente_cuerpo[0]
        dir_x, dir_y = self.serpiente_direccion
        nueva_cabeza = (cabeza_x + dir_x, cabeza_y + dir_y)

        if not (0 <= nueva_cabeza[0] < self.ancho and 0 <= nueva_cabeza[1] < self.alto):
            self.ejecutar_evento('ON_COLLISION_WALL')
            return

        if nueva_cabeza in self.serpiente_cuerpo[:-1]:
            self.ejecutar_evento('ON_COLLISION_SELF')
            return

        self.serpiente_cuerpo.insert(0, nueva_cabeza)

        if nueva_cabeza == self.posicion_comida:
            self.ejecutar_evento('ON_EAT_FOOD')
        else:
            self.serpiente_cuerpo.pop()

    def snake_cambiar_direccion(self, direccion):
        if direccion == 'UP' and self.serpiente_direccion[1] != 1:
            self.serpiente_direccion = (0, -1)
        elif direccion == 'DOWN' and self.serpiente_direccion[1] != -1:
            self.serpiente_direccion = (0, 1)
        elif direccion == 'LEFT' and self.serpiente_direccion[0] != 1:
            self.serpiente_direccion = (-1, 0)
        elif direccion == 'RIGHT' and self.serpiente_direccion[0] != -1:
            self.serpiente_direccion = (1, 0)

    def mostrar_game_over(self):
        self.audio.detener_musica()
        self.ejecutar_evento('ON_GAME_OVER')

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
            command=lambda: (self.root.destroy(), os._exit(0))
        )
        btn_salir.pack(pady=20)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print ("Uso: python runtime.py <archivo_juego.json>")
        sys.exit(1)
    archivo_juego = sys.argv[1]
    try:
        with open(archivo_juego, 'r') as f:
            datos_juego = json.load(f)
    except IOError:
        print ("Error: No se pudo encontrar el archivo " + archivo_juego)
        sys.exit(1)
    juego = Juego(datos_juego)
    juego.run()