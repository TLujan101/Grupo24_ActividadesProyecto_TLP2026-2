# -*- coding: utf-8 -*-
# snake.py --- Juego SNAKE (GAME_TYPE SNAKE). Hereda todo lo basico de Game.

import random
from .game import Game
from .utilidades import Colores

# Cola de Nyan Cat: degradado fijo (rojo, naranja, verde, azul, morado) que
# cicla cada 5 segmentos. Depende de la posicion y no del frame: animarlo
# hacia que la cola "corriera" y distraia del juego.
COLORES_NYAN = ["#FF0000", "#FF7F00", "#00FF00", "#0000FF", "#AA00FF"]

class Snake(Game):

    # CONFIGURACION PROPIA DEL JUEGO (sobreescribe a Game)
    # ----------------------------------------------------
    def cargar_configuracion_nivel(self, nivel_data):
        """El motor lee la configuración completa definida en el .brick"""
        if nivel_data and isinstance(nivel_data, dict):
            self.geometria_nivel = str(nivel_data.get('geometry', 'RECT')).upper()
            self.duracion_inv_config = int(nivel_data.get('invulnerability_duration', 0))
            self.permitir_veneno = bool(nivel_data.get('poison_enabled', False))
            # Si comer veneno termina la partida depende DEL NIVEL: el evento
            # ON EAT_POISON es global y no puede decidirlo.
            self.veneno_mata = bool(nivel_data.get('poison_kills', False))
            self.cantidad_nubes = int(nivel_data.get('clouds_count', 0))

            # Generar los elementos del nivel inmediatamente al cargarlo
            self.generar_elementos_por_nivel()

    def inicializar_estado(self):
        self.serpiente_cuerpo = []
        self.serpiente_direccion = (1, 0)
        self.direccion_pendiente = None

        self.posicion_comida = None
        self.posicion_veneno = None
        self.posicion_powerup = None
        self.nubes = []

        self.crecimiento_pendiente = 0
        self.velocidad_gravedad = 0.15

        if not hasattr(self, 'geometria_nivel') or not self.geometria_nivel:
            self.geometria_nivel = "RECT"
        self.tiempo_invulnerable = 0
        self.tiempo_invulnerable_total = 0
        self.frame_counter = 0

    def iniciar_partida(self):
        """Se ejecuta al iniciar la partida después de elegir nivel"""
        if hasattr(super(Snake, self), 'iniciar_partida'):
            super(Snake, self).iniciar_partida()

        # Asegurar generación al arrancar la partida
        self.generar_elementos_por_nivel()

    def generar_elementos_por_nivel(self):
        self.nubes = []
        self.posicion_veneno = None
        self.posicion_powerup = None

        # 1. Nubes según CLOUDS_COUNT
        for _ in range(getattr(self, 'cantidad_nubes', 0)):
            self.snake_spawn_nube()

        # 2. Veneno si POISON_ENABLED es True
        if getattr(self, 'permitir_veneno', False):
            self.snake_spawn_veneno()

        # 3. Power-up si hay duración de invulnerabilidad
        if getattr(self, 'duracion_inv_config', 0) > 0:
            self.snake_spawn_powerup()

    def snake_spawn_nube(self, accion=None):
        params = (accion or {}).get('params', [])
        if params and params[0] != 'RANDOM':
            coords = params[0]
            self.nubes.append((coords[0], coords[1]))
        else:
            pos = self._obtener_posicion_libre()
            if pos:
                self.nubes.append(pos)

    def snake_spawn_comida(self):
        """Comida con la misma lista de ocupadas que el resto de elementos."""
        pos = self._obtener_posicion_libre()
        if pos is None:
            self.juego_terminado = True   # tablero lleno
            return
        self.posicion_comida = pos

    def snake_spawn_veneno(self):
        pos = self._obtener_posicion_libre()
        if pos:
            self.posicion_veneno = pos

    def snake_spawn_powerup(self):
        pos = self._obtener_posicion_libre()
        if pos:
            self.posicion_powerup = pos

    def elegir_nivel(self, nombre_nivel):
        """Intercepta la selección de nivel y extrae todos sus parámetros"""
        if hasattr(super(Snake, self), 'elegir_nivel'):
            super(Snake, self).elegir_nivel(nombre_nivel)

        self.nivel_actual = nombre_nivel
        lvl_val = None

        if hasattr(self, 'datos_juego'):
            niveles = self.datos_juego.get('levels', [])

            if isinstance(nombre_nivel, int) or (isinstance(nombre_nivel, str) and str(nombre_nivel).isdigit()):
                idx = int(nombre_nivel)
                if isinstance(niveles, list) and 0 <= idx < len(niveles):
                    lvl_val = niveles[idx]
            elif isinstance(niveles, list):
                for l in niveles:
                    if isinstance(l, dict):
                        nombre_json = l.get('nombre') or l.get('name')
                        if str(nombre_json).upper() == str(nombre_nivel).upper():
                            lvl_val = l
                            break
            elif isinstance(niveles, dict):
                for lvl_key, l in niveles.items():
                    if str(lvl_key).upper() == str(nombre_nivel).upper():
                        if isinstance(l, dict):
                            lvl_val = l
                            break

        if isinstance(lvl_val, dict):
            self.cargar_configuracion_nivel(lvl_val)

    def ejecutar_accion(self, verbo, objeto, accion):
        if verbo == 'SPAWN':
            if objeto == 'PLAYER': self.snake_spawn_jugador(accion)
            elif objeto == 'FOOD': self.snake_spawn_comida()
            elif objeto == 'POISON': self.snake_spawn_veneno()
            elif objeto == 'POWERUP': self.snake_spawn_powerup()
            elif objeto == 'CLOUD': self.snake_spawn_nube(accion)
        elif verbo == 'MOVE' and objeto == 'PLAYER':
            self.snake_mover_jugador()
        elif verbo == 'SET_DIRECTION':
            self.snake_cambiar_direccion(objeto)
        elif verbo == 'GROW':
            self.snake_crecer(objeto, accion)
        elif verbo == 'GRANT_INVULNERABILITY':
            self.conceder_invulnerabilidad(objeto)
        elif verbo == 'RESET_SCORE':
            self.score = 0

    def dibujar_circulo_celda(self, x, y, color):
        """Dibuja un círculo exacto usando el canvas y la variable correcta del motor"""
        if hasattr(self, 'canvas') and hasattr(self, 'taman_celda'):
            x1 = x * self.taman_celda + 2
            y1 = y * self.taman_celda + 2
            x2 = (x + 1) * self.taman_celda - 2
            y2 = (y + 1) * self.taman_celda - 2
            self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline="")
        else:
            self.dibujar_celda(x, y, color)

    def dibujar_nube_celda(self, x, y, color):
        c = self.taman_celda
        x1, y1 = x * c, y * c
        self.canvas.create_oval(x1 + c*0.05, y1 + c*0.40, x1 + c*0.45, y1 + c*0.80, fill=color, outline="")
        self.canvas.create_oval(x1 + c*0.25, y1 + c*0.15, x1 + c*0.70, y1 + c*0.65, fill=color, outline="")
        self.canvas.create_oval(x1 + c*0.55, y1 + c*0.35, x1 + c*0.95, y1 + c*0.75, fill=color, outline="")
        self.canvas.create_rectangle(x1 + c*0.10, y1 + c*0.58, x1 + c*0.90, y1 + c*0.82, fill=color, outline="")

    def dibujar_baya_celda(self, x, y, color):
        """Baya redonda con tallo y hoja, dentro de la celda.

        La misma forma sirve para las tres bayas: la normal (roja), la
        venenosa (morada) y el power-up (amarillo). Solo cambia el color.
        """
        c = self.taman_celda
        x1, y1 = x * c, y * c
        cx = x1 + c / 2.0
        # Tallo
        self.canvas.create_rectangle(cx - c*0.04, y1 + c*0.18,
                                     cx + c*0.04, y1 + c*0.34,
                                     fill="#4B2E0A", outline="")
        # Baya
        self.canvas.create_oval(x1 + c*0.18, y1 + c*0.30,
                                x1 + c*0.82, y1 + c*0.94,
                                fill=color, outline="")
        # Hoja
        self.canvas.create_polygon([
            cx, y1 + c*0.28,
            x1 + c*0.78, y1 + c*0.10,
            x1 + c*0.62, y1 + c*0.32,
        ], fill=Colores.get("GREEN", "#00FF00"), outline="")


    def intervalo_parpadeo(self):
        """Frames entre cambio y cambio del parpadeo de la cabeza invulnerable.

        Va de 6 frames (300 ms) con tiempo de sobra a 1 frame (50 ms) cuando el
        power-up esta por acabarse: el parpadeo se acelera para que se note.
        """
        total = getattr(self, 'tiempo_invulnerable_total', 0)
        if not total:
            return 1
        fraccion = float(self.tiempo_invulnerable) / float(total)
        if fraccion < 0:
            fraccion = 0.0
        if fraccion > 1:
            fraccion = 1.0
        return int(1 + 5 * fraccion)

    def cabeza_parpadeando(self):
        """True en los frames en los que la cabeza va en amarillo."""
        if getattr(self, 'tiempo_invulnerable', 0) <= 0:
            return False
        return (self.frame_counter // self.intervalo_parpadeo()) % 2 == 0

    def _direccion_del_segmento(self, indice):
        """Direccion con la que llego cada segmento (orienta el triangulo).

        La cabeza usa la direccion actual; el resto, el vector desde el
        segmento siguiente. La cola hereda la direccion del penultimo.
        """
        cuerpo = self.serpiente_cuerpo
        if indice == 0:
            return self.serpiente_direccion
        if indice + 1 < len(cuerpo):
            actual, siguiente = cuerpo[indice], cuerpo[indice + 1]
            return (actual[0] - siguiente[0], actual[1] - siguiente[1])
        return self._direccion_del_segmento(indice - 1)

    def dibujar_triangulo_celda(self, x, y, color, direccion=(0, -1)):
        """Dibuja un triángulo que apunta hacia donde se movió la serpiente."""
        if hasattr(self, 'canvas') and hasattr(self, 'taman_celda'):
            c = self.taman_celda
            x1 = x * c
            y1 = y * c
            x2 = x1 + c
            y2 = y1 + c
            m = 2
            cx = x1 + c / 2.0
            cy = y1 + c / 2.0
            dx, dy = direccion
            if dx > 0:      # derecha
                puntos = [x2 - m, cy, x1 + m, y1 + m, x1 + m, y2 - m]
            elif dx < 0:    # izquierda
                puntos = [x1 + m, cy, x2 - m, y1 + m, x2 - m, y2 - m]
            elif dy < 0:    # arriba (default)
                puntos = [cx, y1 + m, x1 + m, y2 - m, x2 - m, y2 - m]
            else:           # abajo
                puntos = [cx, y2 - m, x1 + m, y1 + m, x2 - m, y1 + m]
            self.canvas.create_polygon(puntos, fill=color, outline="")
        else:
            self.dibujar_celda(x, y, color)

    def dibujar_elementos(self):
        # Incrementar el contador de frames para el parpadeo de la cabeza
        # invulnerable (la cola ya no se anima).
        self.frame_counter = getattr(self, 'frame_counter', 0) + 1

        # 1. Dibujar Nubes Obstáculo
        for nube in self.nubes:
            self.dibujar_nube_celda(nube[0], nube[1], Colores.get("WHITE", '#A9A9A9'))

        # 2. Dibujar Comida, Veneno y Power-up
        # Las tres bayas comparten el mismo icono: solo cambia el color
        if self.posicion_comida:
            self.dibujar_baya_celda(self.posicion_comida[0], self.posicion_comida[1], Colores.get("RED", '#FF0000'))
        if self.posicion_veneno:
            self.dibujar_baya_celda(self.posicion_veneno[0], self.posicion_veneno[1], Colores.get("PURPLE", '#800080'))
        if self.posicion_powerup:
            self.dibujar_baya_celda(self.posicion_powerup[0], self.posicion_powerup[1], Colores.get("YELLOW", '#FFD700'))

        # 3. Cuerpo y Cabeza de la Serpiente
        geo = str(getattr(self, 'geometria_nivel', 'RECT')).upper()

        for i, segmento in enumerate(self.serpiente_cuerpo):
            x, y = segmento

            # Asignación de colores usando Arcoiris y Colores desde utilidades.py
            if geo == "NYAN_CAT":
                if i == 0:
                    color = Colores.get("GRAY", "#7D7D7D")  # Gris para la cabeza
                else:
                    # Degradado fijo por posicion: la cola no se anima.
                    color = COLORES_NYAN[(i - 1) % len(COLORES_NYAN)]
            else:
                color = Colores.get("DARK GREEN", "#2EB72E") if i == 0 else Colores.get("GREEN", '#33CC33')

            # Mientras dure el power-up la cabeza parpadea en amarillo, y cada
            # vez mas rapido: es la aviso de que se esta acabando.
            if i == 0 and self.cabeza_parpadeando():
                color = Colores.get("YELLOW", '#FFFF00')

            # Renderizado físico según la geometría del nivel deseado
            if geo == "CIRCLE" or geo == "NYAN_CAT":
                # Tanto la cabeza como la cola de Nyan Cat y el modo círculo usan óvalos
                self.dibujar_circulo_celda(x, y, color)
            elif geo == "TRIANGLE":
                # El nivel Entusiasta usa triángulos orientados hacia donde
                # llegó cada segmento.
                self.dibujar_triangulo_celda(x, y, color,
                                             self._direccion_del_segmento(i))
            elif geo == "NUBE":
                self.dibujar_nube_celda(x, y, color)
            else:
                # Por defecto rectángulo (Baby / RECT)
                self.dibujar_celda(x, y, color)

    # METODOS DE LOGICA DE JUEGO Y ENTIDADES
    # ----------------------------------------------------

    def snake_spawn_jugador(self, accion):
        coords = accion['params'][0] if accion['params'] else [self.ancho // 2, self.alto // 2]
        self.serpiente_cuerpo = [(coords[0], coords[1])]
        self.serpiente_direccion = (1, 0)

    def inicializar_estado(self):
        self.serpiente_cuerpo = []
        self.serpiente_direccion = (1, 0)
        self.direccion_pendiente = None

        self.posicion_comida = None
        self.posicion_veneno = None
        self.posicion_powerup = None
        self.nubes = []

        self.crecimiento_pendiente = 0
        self.velocidad_gravedad = 0.15

        if not hasattr(self, 'geometria_nivel') or not self.geometria_nivel:
            self.geometria_nivel = "RECT"
        self.tiempo_invulnerable = 0
        self.tiempo_invulnerable_total = 0
        self.frame_counter = 0

    def iniciar_partida(self):
        """Se ejecuta al iniciar la partida después de elegir nivel"""
        if hasattr(super(Snake, self), 'iniciar_partida'):
            super(Snake, self).iniciar_partida()

        # Generar elementos dinámicamente según la configuración del nivel activo
        self.generar_elementos_por_nivel()

    def generar_elementos_por_nivel(self):
        self.nubes = []
        self.posicion_veneno = None
        self.posicion_powerup = None

        # 1. Nubes según CLOUDS_COUNT
        for _ in range(getattr(self, 'cantidad_nubes', 0)):
            self.snake_spawn_nube()

        # 2. Veneno si POISON_ENABLED es True
        if getattr(self, 'permitir_veneno', False):
            self.snake_spawn_veneno()

        # 3. Power-up si hay duración de invulnerabilidad
        if getattr(self, 'duracion_inv_config', 0) > 0:
            self.snake_spawn_powerup()

    def _casillas_ocupadas(self):
        """Cuerpo, nubes y los tres consumibles: nada puede aparecer aqui."""
        ocupadas = set(self.serpiente_cuerpo)
        ocupadas.update(getattr(self, 'nubes', []))
        for nombre in ('posicion_comida', 'posicion_veneno', 'posicion_powerup'):
            pos = getattr(self, nombre, None)
            if pos is not None:
                ocupadas.add(pos)
        return ocupadas

    def _obtener_posicion_libre(self):
        ocupadas = self._casillas_ocupadas()
        libres = [(x, y) for y in range(self.alto) for x in range(self.ancho)
                  if (x, y) not in ocupadas]
        if not libres:
            return None

        # Se conserva el muestreo por coordenadas de siempre, pero acotado: si
        # el azar insiste en una casilla ocupada (p. ej. un random fijo o un
        # tablero casi lleno), cae a la lista de libres en vez de colgarse.
        for _ in range(len(libres)):
            pos = (random.randint(0, self.ancho - 1), random.randint(0, self.alto - 1))
            if pos in libres:
                return pos
        return libres[0]

    def conceder_invulnerabilidad(self, segundos):
        try:
            duracion = int(segundos)
        except (ValueError, TypeError):
            duracion = 5
        # INVULNERABILITY_DURATION del nivel manda sobre el numero del evento:
        # ON EAT_POWERUP es global y no puede variar por nivel, pero el nivel
        # si puede decir cuanto dura (NYAN_CAT 15, ENTUSIASTA 10).
        duracion_nivel = getattr(self, 'duracion_inv_config', 0)
        if duracion_nivel and duracion_nivel > 0:
            duracion = int(duracion_nivel)
        self.tiempo_invulnerable = duracion
        # La duracion total es la que permite saber cuanto queda y acelerar el
        # parpadeo de la cabeza conforme se acaba.
        self.tiempo_invulnerable_total = duracion

    def snake_crecer(self, objeto=None, accion=None):
        cantidad = 1
        try:
            params = (accion or {}).get('params', [])
            if params:
                cantidad = int(params[0])
        except (ValueError, TypeError):
            cantidad = 1

        if cantidad >= 1:
            self.crecimiento_pendiente += cantidad



    # Orden fijo de reintento tras un choque: derecha, abajo, izquierda,
    # arriba. Determinista a proposito: el jugador puede anticiparlo.
    DIRECCIONES_REDIRECCION = [(1, 0), (0, 1), (-1, 0), (0, -1)]

    def _dentro_del_tablero(self, celda):
        return 0 <= celda[0] < self.ancho and 0 <= celda[1] < self.alto

    def _redirigir_tras_choque(self):
        """Primera direccion libre en orden fijo; None si no hay ninguna.

        Deja puesta la direccion nueva y devuelve la celda hacia la que avanza.
        """
        cabeza = self.serpiente_cuerpo[0]
        nubes = getattr(self, 'nubes', [])
        # Una media vuelta nunca vale: la celda de la cola se libera en el
        # mismo tick y parecia libre, pero reversar atraviesa el propio cuerpo.
        inversa = (-self.serpiente_direccion[0], -self.serpiente_direccion[1])
        for dx, dy in self.DIRECCIONES_REDIRECCION:
            if (dx, dy) == inversa:
                continue
            destino = (cabeza[0] + dx, cabeza[1] + dy)
            if not self._dentro_del_tablero(destino) or destino in nubes:
                continue
            comiendo = (destino == self.posicion_comida)
            cuerpo_solido = (self.serpiente_cuerpo
                             if (self.crecimiento_pendiente > 0 or comiendo)
                             else self.serpiente_cuerpo[:-1])
            if destino in cuerpo_solido:
                continue
            self.serpiente_direccion = (dx, dy)
            return destino
        return None

    def snake_mover_jugador(self):
        if not self.serpiente_cuerpo: return

        if self.tiempo_invulnerable > 0:
            # Cuenta en SEGUNDOS de juego, no en ticks: velocidad_gravedad es
            # lo que dura un tick (TICK del nivel), asi que el power-up de 10
            # dura 10 s reales aunque el nivel corra a 0.06 s por tick.
            self.tiempo_invulnerable -= self.velocidad_gravedad

        if self.direccion_pendiente is not None:
            self.serpiente_direccion = self.direccion_pendiente
            self.direccion_pendiente = None

        cabeza_x, cabeza_y = self.serpiente_cuerpo[0]
        dir_x, dir_y = self.serpiente_direccion
        nueva_cabeza = (cabeza_x + dir_x, cabeza_y + dir_y)

        es_invulnerable = self.tiempo_invulnerable > 0

        # 1. Pared: sin power-up mata; con power-up envuelve al lado opuesto.
        if not self._dentro_del_tablero(nueva_cabeza):
            if not es_invulnerable:
                self.ejecutar_evento('ON_COLLISION_WALL')
                return
            nueva_cabeza = (nueva_cabeza[0] % self.ancho,
                            nueva_cabeza[1] % self.alto)

        # 2. Nube: con power-up se atraviesa; sin el, desvia o mata.
        elif hasattr(self, 'nubes') and nueva_cabeza in self.nubes:
            if not es_invulnerable:
                nueva_cabeza = self._redirigir_tras_choque()
                if nueva_cabeza is None:
                    # OJO: el evento se llama ON_GAME_OVER; ejecutar_evento('GAME_OVER')
                    # no hacia nada. La bandera dispara ON_GAME_OVER en el game loop.
                    self.juego_terminado = True
                    return

        # 3. Auto-colisión: sin power-up mata; con power-up la atraviesa.
        else:
            comiendo = (nueva_cabeza == self.posicion_comida)
            cuerpo_solido = self.serpiente_cuerpo if (self.crecimiento_pendiente > 0 or comiendo) else self.serpiente_cuerpo[:-1]

            if nueva_cabeza in cuerpo_solido and not es_invulnerable:
                self.ejecutar_evento('ON_COLLISION_SELF')
                return

        # 4. Insertar la nueva cabeza
        self.serpiente_cuerpo.insert(0, nueva_cabeza)

        # 5. Comprobar consumo de elementos
        # Solo se fuerza la reaparicion si el evento NO la hizo: ON EAT_FOOD,
        # ON EAT_POISON y ON EAT_POWERUP ya traen su SPAWN ... AT RANDOM. Pisar
        # ese spawn duplicaba la reaparicion y, con random determinista (tests),
        # entraba en un bucle infinito.
        if nueva_cabeza == self.posicion_comida:
            self.ejecutar_evento('ON_EAT_FOOD')
            if self.posicion_comida == nueva_cabeza:
                self.posicion_comida = self._obtener_posicion_libre()
        elif (hasattr(self, 'posicion_veneno') and nueva_cabeza == self.posicion_veneno
              and not es_invulnerable):
            # Con el power-up activo la baya morada esta neutralizada: no resta
            # puntos, no termina la partida y tampoco se consume.
            self.ejecutar_evento('ON_EAT_POISON')
            if self.posicion_veneno == nueva_cabeza:
                self.posicion_veneno = self._obtener_posicion_libre()
            # POISON_KILLS es del nivel, no del evento: solo algunos niveles
            # convierten la baya en game over.
            if getattr(self, 'veneno_mata', False):
                self.juego_terminado = True
        elif hasattr(self, 'posicion_powerup') and nueva_cabeza == self.posicion_powerup:
            self.ejecutar_evento('ON_EAT_POWERUP')
            if self.posicion_powerup == nueva_cabeza:
                self.posicion_powerup = self._obtener_posicion_libre()

        # 6. Manejar crecimiento o recortar la cola
        if self.crecimiento_pendiente > 0:
            self.crecimiento_pendiente -= 1
        else:
            self.serpiente_cuerpo.pop()

    def snake_cambiar_direccion(self, direccion):
        if direccion == 'UP' and self.serpiente_direccion[1] != 1:
            self.direccion_pendiente = (0, -1)
        elif direccion == 'DOWN' and self.serpiente_direccion[1] != -1:
            self.direccion_pendiente = (0, 1)
        elif direccion == 'LEFT' and self.serpiente_direccion[0] != 1:
            self.direccion_pendiente = (-1, 0)
        elif direccion == 'RIGHT' and self.serpiente_direccion[0] != -1:
            self.direccion_pendiente = (1, 0)
