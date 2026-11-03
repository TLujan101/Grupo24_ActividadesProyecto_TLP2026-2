# -*- coding: utf-8 -*-
# tanks.py --- Juego TANKS (GAME_TYPE TANKS). Actividad 5, seccion A.
#
# El .brick declara formas (TYPE, HP, DAMAGE, SPEED, FIRE_RATE, HEAL, OWNER) y
# eventos; este motor no compara nombres de forma ni de nivel. Los muros son
# celdas de self.grid, asi que reutilizan el dibujo y la colision de Game.

import random
import Tkinter as tk

from .game import Game
from .utilidades import Colores

DIRECCIONES = {'UP': (0, -1), 'DOWN': (0, 1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}

# Giro de 90 grados a la DERECHA en coordenadas de pantalla (y crece hacia
# abajo). Es el giro de un enemigo cuando su paso esta bloqueado.
ROTACION_DERECHA = {(0, -1): (1, 0), (1, 0): (0, 1),
                    (0, 1): (-1, 0), (-1, 0): (0, -1)}

COOLDOWN_DISPARO = 0.3
TICK_POR_DEFECTO = 0.12
VIDA_JUGADOR = 3


class Tanks(Game):

    # ESTADO Y CONFIGURACION
    # ----------------------

    def inicializar_estado(self):
        self.jugador = None
        self.enemigos = []
        self.balas = []
        self.martillo = None
        self.velocidad_gravedad = TICK_POR_DEFECTO

        self.label_vida = tk.Label(self.marco_score,
                                   text='VIDA %d/%d' % (VIDA_JUGADOR, VIDA_JUGADOR),
                                   bg='#1e1e2e', fg=Colores.get('GREEN', '#00FF00'),
                                   font=('Consolas', 14, 'bold'))
        self.label_vida.pack(pady=10, padx=10)
        self.label_controles.config(text='CONTROLES\nFlechas: Mover\nEspacio: Disparar')

    # Cada forma del .brick, en orden estable: en py2.7 un dict no conserva
    # el orden de declaracion y "la primera forma PICKUP" debe ser predecible.

    def _formas(self):
        return sorted(self.datos_juego.get('shapes', {}).items())

    def _forma(self, nombre):
        return self.datos_juego.get('shapes', {}).get(nombre)

    def _formas_de_tipo(self, tipo, bando=None):
        encontradas = []
        for nombre, datos in self._formas():
            if not isinstance(datos, dict) or datos.get('type') != tipo:
                continue
            if bando is not None and datos.get('owner') != bando:
                continue
            encontradas.append((nombre, datos))
        return encontradas

    def _color_de(self, datos):
        if not isinstance(datos, dict):
            return Colores.get('CYAN', '#00FFFF')
        return Colores.get(datos.get('color', 'CYAN'), '#00FFFF')

    # MATRICES
    # --------

    @staticmethod
    def _matriz(datos):
        if isinstance(datos, dict):
            estados = datos.get('estados') or []
        else:
            estados = datos or []          # .json viejo: la forma ES la lista
        return estados[0] if estados else [[1]]

    @staticmethod
    def _rotar_matriz(matriz, direccion):
        # Las matrices de PLAYER/ENEMY/BOSS/WALL son cuadradas (lo garantiza el
        # compilador), asi que rotar no cambia la huella: solo cambia que
        # celdas estan encendidas.
        if direccion == (1, 0):            # derecha: 90 grados
            return [list(fila) for fila in zip(*matriz[::-1])]
        if direccion == (0, 1):            # abajo: 180 grados
            return [list(reversed(fila)) for fila in reversed(matriz)]
        if direccion == (-1, 0):           # izquierda: 270 grados
            return [list(fila) for fila in zip(*matriz)][::-1]
        return [list(fila) for fila in matriz]   # arriba: identidad

    @staticmethod
    def _celdas(matriz, x, y):
        return [(x + cx, y + cy)
                for cy, fila in enumerate(matriz)
                for cx, valor in enumerate(fila) if valor != 0]

    def _dentro(self, celda):
        return 0 <= celda[0] < self.ancho and 0 <= celda[1] < self.alto

    @staticmethod
    def _celda_frente(matriz, x, y, direccion):
        # Celda inmediatamente delante de la cara frontal, centrada en ella.
        lado = len(matriz)
        dx, dy = direccion
        if dx > 0:
            return (x + lado, y + lado // 2)
        if dx < 0:
            return (x - 1, y + lado // 2)
        if dy > 0:
            return (x + lado // 2, y + lado)
        return (x + lado // 2, y - 1)

    # OCUPACION
    # ---------

    def _celdas_jugador(self):
        if not self.jugador:
            return set()
        return set(self._celdas(self._matriz_jugador(), self.jugador['x'], self.jugador['y']))

    def _celdas_de_enemigo(self, enemigo):
        datos = self._forma(enemigo['nombre']) or {}
        matriz = self._rotar_matriz(self._matriz(datos), enemigo['direccion'])
        return set(self._celdas(matriz, enemigo['x'], enemigo['y']))

    def _ocupadas(self, sin_jugador=False, sin_enemigo=None):
        ocupadas = set()
        if self.jugador and not sin_jugador:
            ocupadas.update(self._celdas_jugador())
        for enemigo in self.enemigos:
            if enemigo is sin_enemigo:
                continue
            ocupadas.update(self._celdas_de_enemigo(enemigo))
        if self.martillo:
            ocupadas.add(self.martillo)
        for bala in self.balas:
            ocupadas.add((bala['x'], bala['y']))
        return ocupadas

    def _puede_ocupar(self, matriz, x, y, ignorar_muros=False, sin_jugador=False,
                      sin_enemigo=None):
        ocupadas = self._ocupadas(sin_jugador=sin_jugador, sin_enemigo=sin_enemigo)
        for cx, cy in self._celdas(matriz, x, y):
            if not self._dentro((cx, cy)):
                return False
            if not ignorar_muros and self.grid[cy][cx] != 0:
                return False
            if (cx, cy) in ocupadas:
                return False
        return True

    def _borrar_muros(self, matriz, x, y):
        for cx, cy in self._celdas(matriz, x, y):
            if self._dentro((cx, cy)):
                self.grid[cy][cx] = 0

    def _ancla_libre(self, matriz):
        candidatas = [(x, y) for y in range(self.alto) for x in range(self.ancho)
                      if self._puede_ocupar(matriz, x, y)]
        if not candidatas:
            return None
        # Muestreo acotado + fallback determinista (mismo patron que Snake):
        # con un random fijo o un tablero casi lleno no se cuelga.
        for _ in range(len(candidatas)):
            pos = (random.randint(0, self.ancho - 1), random.randint(0, self.alto - 1))
            if pos in candidatas:
                return pos
        return candidatas[0]

    # ACCIONES DEL .BRICK
    # -------------------

    def ejecutar_accion(self, verbo, objeto, accion):
        if verbo == 'SPAWN':
            self._spawn_forma(objeto, accion)
        elif verbo == 'MOVE' and objeto == 'PLAYER':
            self._mover_jugador(accion)
        elif verbo == 'SHOOT' and objeto == 'PLAYER':
            self._disparar_jugador()
        elif verbo == 'HEAL' and objeto == 'PLAYER':
            self._sanar_jugador()

    def _spawn_forma(self, nombre, accion):
        datos = self._forma(nombre)
        if not isinstance(datos, dict) and nombre in ('PLAYER', 'ENEMY'):
            # "SPAWN PLAYER" nombra el rol, no la forma (el .brick real lo
            # escribe asi). PLAYER es unico; ENEMY cae en la primera forma
            # enemiga en orden estable, y el .brick puede usar el nombre
            # explicito para elegir tipo.
            formas = self._formas_de_tipo(nombre)
            if formas:
                nombre, datos = formas[0]
        if not isinstance(datos, dict):
            return
        tipo = datos.get('type')
        if tipo == 'PLAYER':
            self._spawn_jugador(nombre, datos, accion)
            return
        if tipo == 'BULLET':
            return              # las balas solo nacen de SHOOT
        matriz = self._matriz(datos)
        params = (accion or {}).get('params', [])
        if params and params[0] != 'RANDOM':
            coords = params[0]
            ancla = (int(coords[0]), int(coords[1]))
        else:
            ancla = self._ancla_libre(matriz)
        if ancla is None:
            return
        # Player y enemigo borran los muros bajo su matriz; un muro o un
        # pickup, en cambio, respetan la celda ocupada.
        ignorar = tipo in ('PLAYER', 'ENEMY')
        if not self._puede_ocupar(matriz, ancla[0], ancla[1], ignorar_muros=ignorar):
            return
        if tipo == 'ENEMY':
            self._spawn_enemigo(nombre, datos, ancla)
        elif tipo == 'WALL':
            for x, y in self._celdas(matriz, ancla[0], ancla[1]):
                self.grid[y][x] = 1
        elif tipo == 'PICKUP':
            self.martillo = ancla

    def _spawn_jugador(self, nombre, datos, accion):
        matriz = self._matriz(datos)
        params = (accion or {}).get('params', [])
        if params and params[0] != 'RANDOM':
            coords = params[0]
            x, y = int(coords[0]), int(coords[1])
        else:
            ancla = self._ancla_libre(matriz)
            x, y = ancla if ancla else (self.ancho // 2, self.alto // 2)
        # El jugador siempre existe: si el .brick lo pone en el borde se
        # recorta al tablero en vez de ignorar el spawn (quedaria sin jugador).
        x = max(0, min(x, self.ancho - len(matriz[0])))
        y = max(0, min(y, self.alto - len(matriz)))
        self._borrar_muros(matriz, x, y)
        vida = int(datos.get('hp', VIDA_JUGADOR))
        self.jugador = {'nombre': nombre, 'x': x, 'y': y, 'hp': vida,
                        'max_hp': vida, 'orientacion': (0, -1), 'cooldown': 0.0}

    def _spawn_enemigo(self, nombre, datos, ancla):
        self._borrar_muros(self._matriz(datos), ancla[0], ancla[1])
        vida = int(datos.get('hp', 1))
        self.enemigos.append({'nombre': nombre, 'x': ancla[0], 'y': ancla[1],
                              'hp': vida, 'max_hp': vida, 'direccion': (1, 0),
                              'tiempo_movimiento': 0.0, 'tiempo_disparo': 0.0})

    def _matriz_jugador(self):
        datos = self._forma(self.jugador['nombre']) or {}
        return self._rotar_matriz(self._matriz(datos), self.jugador['orientacion'])

    def _mover_jugador(self, accion):
        params = (accion or {}).get('params', [])
        direccion = params[0] if params else 'UP'
        dx, dy = DIRECCIONES.get(direccion, (0, -1))
        if not self.jugador:
            # "instancia o reutiliza": un .brick sin SPAWN PLAYER sigue jugable.
            formas = self._formas_de_tipo('PLAYER')
            if not formas:
                return
            self._spawn_jugador(formas[0][0], formas[0][1], {'params': []})
        self.jugador['orientacion'] = (dx, dy)
        matriz = self._matriz_jugador()
        if self._puede_ocupar(matriz, self.jugador['x'] + dx, self.jugador['y'] + dy,
                              sin_jugador=True):
            self.jugador['x'] += dx
            self.jugador['y'] += dy

    def _bala_de_bando(self, bando):
        balas = self._formas_de_tipo('BULLET', bando)
        return balas[0] if balas else None

    def _disparar_jugador(self):
        if not self.jugador or self.jugador['cooldown'] > 0:
            return
        self.jugador['cooldown'] = COOLDOWN_DISPARO
        bala = self._bala_de_bando('PLAYER')
        if not bala:
            return
        nombre, datos = bala
        dx, dy = self.jugador['orientacion']
        x, y = self._celda_frente(self._matriz_jugador(), self.jugador['x'],
                                  self.jugador['y'], (dx, dy))
        if not self._dentro((x, y)):
            return
        if self.grid[y][x] != 0:
            # Disparar pegado a un muro lo destruye, pero no sale bala.
            self.grid[y][x] = 0
            return
        self.balas.append({'x': x, 'y': y, 'dx': dx, 'dy': dy, 'dueno': 'PLAYER',
                           'dano': int(datos.get('damage', 1)),
                           'color': self._color_de(datos)})

    def _sanar_jugador(self):
        if not self.jugador:
            return
        pickups = self._formas_de_tipo('PICKUP')
        cantidad = int(pickups[0][1].get('heal', 1)) if pickups else 1
        self.jugador['hp'] = min(self.jugador['max_hp'], self.jugador['hp'] + cantidad)

    # NIVEL Y MUROS
    # -------------

    def iniciar_partida(self):
        # Los muros se generan aqui y no en __init__: con dos niveles, __init__
        # corre mientras el jugador todavia ve el menu de eleccion. ON_START
        # llega despues, asi que los spawns borran los muros que los tapen.
        self.jugador = None
        self.enemigos = []
        self.balas = []
        self.martillo = None
        self._generar_muros()
        super(Tanks, self).iniciar_partida()

    def _generar_muros(self):
        self.grid = [[0 for _ in range(self.ancho)] for _ in range(self.alto)]
        cantidad = int(self.nivel_config.get('walls', 0) or 0)
        libres = [(x, y) for y in range(self.alto) for x in range(self.ancho)]
        for _ in range(cantidad):
            if not libres:
                break               # WALLS mayor que el tablero: se corta aqui
            pos = self._celda_libre_de(libres)
            self.grid[pos[1]][pos[0]] = 1
            libres.remove(pos)

    def _celda_libre_de(self, libres):
        # Mismo patron acotado que _ancla_libre: azar con fallback determinista.
        for _ in range(len(libres)):
            pos = (random.randint(0, self.ancho - 1), random.randint(0, self.alto - 1))
            if pos in libres:
                return pos
        return libres[0]

    # TICK
    # ----

    def ejecutar_evento(self, nombre_evento):
        # Game.ejecutar_evento despacha las acciones del .brick; Tanks adelanta
        # el mundo ANTES, para que el ON TICK del .brick vea el estado del tick.
        if nombre_evento == 'ON_TICK':
            self.avanzar_mundo(self.velocidad_gravedad)
        super(Tanks, self).ejecutar_evento(nombre_evento)

    def avanzar_mundo(self, delta):
        # Orden del spec: balas, enemigos (mover y disparar) y martillo. El
        # ON TICK del .brick corre despues, en ejecutar_evento.
        self._avanzar_balas()
        self._mover_enemigos(delta)
        self._disparar_enemigos(delta)
        self._recoger_martillo()
        if self.jugador and self.jugador['cooldown'] > 0:
            self.jugador['cooldown'] = max(0.0, self.jugador['cooldown'] - delta)

    def _mover_enemigos(self, delta):
        for enemigo in self.enemigos:
            datos = self._forma(enemigo['nombre']) or {}
            velocidad = int(datos.get('speed', 2) or 2)
            enemigo['tiempo_movimiento'] += delta
            if enemigo['tiempo_movimiento'] >= 1.0 / velocidad:
                enemigo['tiempo_movimiento'] -= 1.0 / velocidad
                self._intentar_mover_enemigo(enemigo)

    def _intentar_mover_enemigo(self, enemigo):
        datos = self._forma(enemigo['nombre']) or {}
        matriz = self._matriz(datos)
        # Cuatro intentos: la direccion actual y tres giros a la derecha. Si
        # las cuatro estan bloqueadas se queda quieto (sin bucle infinito).
        for _ in range(4):
            dx, dy = enemigo['direccion']
            girada = self._rotar_matriz(matriz, enemigo['direccion'])
            if self._puede_ocupar(girada, enemigo['x'] + dx, enemigo['y'] + dy,
                                  sin_enemigo=enemigo):
                enemigo['x'] += dx
                enemigo['y'] += dy
                return
            enemigo['direccion'] = ROTACION_DERECHA[enemigo['direccion']]

    def _centro(self, entidad, datos):
        lado = len(self._matriz(datos))
        return (entidad['x'] + lado // 2, entidad['y'] + lado // 2)

    def _direccion_apuntada(self, enemigo):
        # Con el jugador en la misma fila o columna, dispara por ese eje; si
        # no, por donde va. Sin pathfinding y sin nombres de forma de por medio.
        if not self.jugador:
            return enemigo['direccion']
        px, py = self._centro(self.jugador, self._forma(self.jugador['nombre']) or {})
        ex, ey = self._centro(enemigo, self._forma(enemigo['nombre']) or {})
        if px == ex:
            return (0, 1) if py > ey else (0, -1)
        if py == ey:
            return (1, 0) if px > ex else (-1, 0)
        return enemigo['direccion']

    def _disparar_enemigos(self, delta):
        for enemigo in self.enemigos:
            datos = self._forma(enemigo['nombre']) or {}
            cadencia = float(datos.get('fire_rate', 3) or 3)
            enemigo['tiempo_disparo'] += delta
            if enemigo['tiempo_disparo'] < cadencia:
                continue
            enemigo['tiempo_disparo'] -= cadencia
            bala = self._bala_de_bando('ENEMY')
            if not bala:
                continue
            nombre, datos_bala = bala
            direccion = self._direccion_apuntada(enemigo)
            matriz = self._rotar_matriz(self._matriz(datos), direccion)
            x, y = self._celda_frente(matriz, enemigo['x'], enemigo['y'], direccion)
            if not self._dentro((x, y)):
                continue
            if self.grid[y][x] != 0:
                self.grid[y][x] = 0      # las balas enemigas tambien rompen muros
                continue
            self.balas.append({'x': x, 'y': y, 'dx': direccion[0], 'dy': direccion[1],
                               'dueno': 'ENEMY',
                               'dano': int(datos_bala.get('damage', 1)),
                               'color': self._color_de(datos_bala)})

    def _recoger_martillo(self):
        if not self.jugador or not self.martillo:
            return
        if self.martillo not in self._celdas_jugador():
            return
        self.ejecutar_evento('ON_EAT_HAMMER')
        if self.martillo in self._celdas_jugador():
            # El evento no lo reubico: lo hace el motor (patron de Snake).
            self._spawn_martillo()

    def _spawn_martillo(self):
        pickups = self._formas_de_tipo('PICKUP')
        if not pickups:
            self.martillo = None
            return
        # Sin celda libre queda en None: no se repite el evento cada tick
        # (Review Focus 3).
        self.martillo = self._ancla_libre(self._matriz(pickups[0][1]))

    def _jugador_en(self, x, y):
        return (x, y) in self._celdas_jugador()

    def _enemigo_en(self, x, y):
        for enemigo in self.enemigos:
            if (x, y) in self._celdas_de_enemigo(enemigo):
                return enemigo
        return None

    def _avanzar_balas(self):
        supervivientes = []
        for bala in self.balas:
            bala['x'] += bala['dx']
            bala['y'] += bala['dy']
            if not self._dentro((bala['x'], bala['y'])):
                continue
            if self.grid[bala['y']][bala['x']] != 0:
                self.grid[bala['y']][bala['x']] = 0
                self.ejecutar_evento('ON_BULLET_HIT_WALL')
                continue
            if bala['dueno'] == 'PLAYER':
                enemigo = self._enemigo_en(bala['x'], bala['y'])
                if enemigo is None:
                    supervivientes.append(bala)
                    continue
                enemigo['hp'] -= bala['dano']
                if enemigo['hp'] <= 0:
                    self.enemigos.remove(enemigo)
                    self.ejecutar_evento('ON_ENEMY_DEFEATED')
                continue
            if self._jugador_en(bala['x'], bala['y']):
                self.jugador['hp'] -= bala['dano']
                self.ejecutar_evento('ON_PLAYER_HIT')
                if self.jugador['hp'] <= 0:
                    self.jugador['hp'] = 0
                    self.juego_terminado = True
                continue
            supervivientes.append(bala)
        self.balas = supervivientes

    # DIBUJO
    # ------

    def color_celda_grid(self, x, y):
        muros = self._formas_de_tipo('WALL')
        if muros:
            return self._color_de(muros[0][1])
        return Colores.get('GRAY', '#808080')

    def dibujar_elementos(self):
        if self.martillo:
            self._dibujar_martillo(self.martillo[0], self.martillo[1])
        for enemigo in self.enemigos:
            datos = self._forma(enemigo['nombre']) or {}
            matriz = self._rotar_matriz(self._matriz(datos), enemigo['direccion'])
            self._dibujar_entidad(matriz, enemigo['x'], enemigo['y'], self._color_de(datos))
        for bala in self.balas:
            self._dibujar_bala(bala)
        if self.jugador:
            datos = self._forma(self.jugador['nombre']) or {}
            self._dibujar_entidad(self._matriz_jugador(), self.jugador['x'],
                                  self.jugador['y'], self._color_de(datos))
        self._actualizar_label_vida()

    def _dibujar_entidad(self, matriz, x, y, color):
        for cx, cy in self._celdas(matriz, x, y):
            if self._dentro((cx, cy)):
                self.dibujar_celda(cx, cy, color)

    def _dibujar_bala(self, bala):
        self.dibujar_celda(bala['x'], bala['y'], bala['color'])
        c = self.taman_celda
        x1, y1 = bala['x'] * c, bala['y'] * c
        self.canvas.create_rectangle(x1 + c * 0.30, y1 + c * 0.30,
                                     x1 + c * 0.70, y1 + c * 0.70,
                                     fill='#FFFFFF', outline='')

    def _dibujar_martillo(self, x, y):
        pickups = self._formas_de_tipo('PICKUP')
        color = self._color_de(pickups[0][1]) if pickups else Colores.get('YELLOW', '#FFFF00')
        c = self.taman_celda
        x1, y1 = x * c, y * c
        self.canvas.create_rectangle(x1 + c * 0.42, y1 + c * 0.15,
                                     x1 + c * 0.58, y1 + c * 0.85,
                                     fill=color, outline='')
        self.canvas.create_rectangle(x1 + c * 0.12, y1 + c * 0.12,
                                     x1 + c * 0.88, y1 + c * 0.38,
                                     fill=color, outline='')

    def _actualizar_label_vida(self):
        if not self.jugador:
            return
        hp, maximo = self.jugador['hp'], self.jugador['max_hp']
        color = Colores.get('GREEN', '#00FF00') if hp > 1 else Colores.get('RED', '#FF0000')
        self.label_vida.config(text='VIDA %d/%d' % (hp, maximo), fg=color)
