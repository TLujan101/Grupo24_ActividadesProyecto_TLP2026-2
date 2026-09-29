# -*- coding: utf-8 -*-
# snake.py --- Juego SNAKE (GAME_TYPE SNAKE). Hereda todo lo basico de Game.

import random

from .game import Game

COLOR_SNAKE_CABEZA = '#00FF00' # Verde brillante
COLOR_SNAKE_CUERPO = '#33CC33' # Verde normal
COLOR_FOOD = '#FF0000'      # Rojo


class Snake(Game):

    # CONFIGURACION PROPIA DEL JUEGO (sobreescribe a Game)
    # ----------------------------------------------------

    def inicializar_estado(self):
        self.serpiente_cuerpo = []
        self.serpiente_direccion = (1, 0)
        self.direccion_pendiente = None
        self.posicion_comida = None
        self.crecimiento_pendiente = 0
        self.velocidad_gravedad = 0.15

    def ejecutar_accion(self, verbo, objeto, accion):
        if verbo == 'SPAWN' and objeto == 'PLAYER': self.snake_spawn_jugador(accion)
        if verbo == 'SPAWN' and objeto == 'FOOD': self.snake_spawn_comida()
        if verbo == 'MOVE' and objeto == 'PLAYER': self.snake_mover_jugador()
        if verbo == 'SET_DIRECTION': self.snake_cambiar_direccion(objeto)
        if verbo == 'GROW': self.snake_crecer(objeto, accion)

    def dibujar_elementos(self):
        # Comida
        if self.posicion_comida:
            x, y = self.posicion_comida
            self.dibujar_celda(x, y, COLOR_FOOD)
        # Cuerpo de la Serpiente
        for i, segmento in enumerate(self.serpiente_cuerpo):
            x, y = segmento
            color = COLOR_SNAKE_CABEZA if i == 0 else COLOR_SNAKE_CUERPO
            self.dibujar_celda(x, y, color)


    # METODOS DE LOGICA DE JUEGO
    # --------------------------

    def snake_spawn_jugador(self, accion):
        coords = accion['params'][0] if accion['params'] else [self.ancho // 2, self.alto // 2]
        self.serpiente_cuerpo = [(coords[0], coords[1])]
        self.serpiente_direccion = (1, 0)

    def snake_spawn_comida(self):
        # Tablero lleno = victoria: no hay donde poner comida
        if len(self.serpiente_cuerpo) >= self.ancho * self.alto:
            self.juego_terminado = True
            return
        while True:
            x, y = random.randint(0, self.ancho - 1), random.randint(0, self.alto - 1)
            if (x, y) not in self.serpiente_cuerpo:
                self.posicion_comida = (x, y)
                break

    def snake_mover_jugador(self):
        if not self.serpiente_cuerpo: return
        # Un giro por tick: el giro pedido se aplica al moverse
        if self.direccion_pendiente is not None:
            self.serpiente_direccion = self.direccion_pendiente
            self.direccion_pendiente = None
        cabeza_x, cabeza_y = self.serpiente_cuerpo[0]
        dir_x, dir_y = self.serpiente_direccion
        nueva_cabeza = (cabeza_x + dir_x, cabeza_y + dir_y)

        if not (0 <= nueva_cabeza[0] < self.ancho and 0 <= nueva_cabeza[1] < self.alto):
            self.ejecutar_evento('ON_COLLISION_WALL')
            return

        # Con crecimiento pendiente la cola no se mueve: chocar con ella si mata
        cuerpo_solido = self.serpiente_cuerpo if self.crecimiento_pendiente > 0 else self.serpiente_cuerpo[:-1]
        if nueva_cabeza in cuerpo_solido:
            self.ejecutar_evento('ON_COLLISION_SELF')
            return

        self.serpiente_cuerpo.insert(0, nueva_cabeza)

        if nueva_cabeza == self.posicion_comida:
            self.ejecutar_evento('ON_EAT_FOOD')

        # El crecimiento lo manda el .brick via GROW; sin pendiente se quita la cola
        if self.crecimiento_pendiente > 0:
            self.crecimiento_pendiente -= 1
        else:
            self.serpiente_cuerpo.pop()

    def snake_cambiar_direccion(self, direccion):
        # Se encola para el proximo tick (un giro por tick): asi dos teclas
        # rapidas no suman un giro de 180 contra el cuerpo. Se valida contra
        # la direccion actual, asi cambiar de opinion antes del tick vale.
        if direccion == 'UP' and self.serpiente_direccion[1] != 1:
            self.direccion_pendiente = (0, -1)
        elif direccion == 'DOWN' and self.serpiente_direccion[1] != -1:
            self.direccion_pendiente = (0, 1)
        elif direccion == 'LEFT' and self.serpiente_direccion[0] != 1:
            self.direccion_pendiente = (-1, 0)
        elif direccion == 'RIGHT' and self.serpiente_direccion[0] != -1:
            self.direccion_pendiente = (1, 0)

    def snake_crecer(self, objeto=None, accion=None):
        cantidad = 1
        try:
            params = (accion or {}).get('params', [])
            if params:
                cantidad = int(params[0])
        except (ValueError, TypeError):
            cantidad = 1
        if cantidad < 1:
            return
        self.crecimiento_pendiente += cantidad
