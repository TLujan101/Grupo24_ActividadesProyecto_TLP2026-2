#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# compiler.py
# Compilador universal para BrickScript
# Uso: python compiler.py <archivo_entrada.brick>

import sys
import re
import json

# Techo para validar TICK:asi se rechazan nan e inf, que son floats validos
# pero romperian el ciclo de juego (ver parsear_nivel).
INFINITO = float('inf')

# Silencio dentro de una partitura. Es una palabra y no una letra porque REST
# no es una nota: no se puede afinar. Se traduce a una nota de 0 Hz, que el
# sintetizador produce como silencio (sen(0) = 0).
SILENCIO = 'REST'

# Timbres. Duplicados de tracker.ONDA_* a proposito: el compilador no importa
# de engine/ porque engine/__init__.py arrastraría Tkinter al proceso de
# compilación. Misma regla que NIVEL_POR_DEFECTO.
ONDA_SENOIDAL = 'SINE'
ONDAS = ('SINE', 'SQUARE')

# Scanner: una regex por clase de token. El orden emula maximal munch (Python
# se queda con la primera que casa, no con la mas larga): NOTA antes que
# PALABRA para no partir E5, y NUMERO con el decimal pegado para no partir
# 0.15. El nombre solo documenta; los tokens siguen siendo strings.
PATRONES_TOKEN = [
    ('NOTA', r'\b[A-G]#?[0-9]+\b'),   # E5, D#4
    ('PALABRA', r'\b[A-Z_]+\b'),      # GAME_TYPE, NYAN_CAT
    ('NUMERO', r'\d+(?:\.\d+)?'),     # 10, 0.15
    ('SIMBOLO', r'[\[\](),:]'),       # [ ] ( ) , :
]

# '#' tras A-G es sostenido (D#4); en cualquier otro caso abre comentario.
PATRON_COMENTARIO = r'(?<![A-G])#.*'

# (?:...) hace que findall devuelva el token completo, no sus grupos.
RE_TOKEN = re.compile(
    '|'.join('(?:' + patron + ')' for _, patron in PATRONES_TOKEN))
RE_COMENTARIO = re.compile(PATRON_COMENTARIO)


def lexer(codigo_fuente):
    codigo_fuente = RE_COMENTARIO.sub('', codigo_fuente)
    tokens = RE_TOKEN.findall(codigo_fuente)
    resto = RE_TOKEN.sub('', codigo_fuente)
    if resto.strip():
        raise Exception("Caracteres no reconocidos: '" + resto.strip()[:40] + "'")
    return tokens

class Parser:
    # El nivel por defecto existe siempre: si el .brick no declara LEVELS se
    # queda este. Solo es una etiqueta, no lleva comportamiento asociado; los
    # valores por defecto de cada modificador los aporta el juego, no el
    # compilador (Tetris y Snake tienen ticks distintos y el compilador es uno
    # solo para los dos).
    NIVEL_POR_DEFECTO = 'BABY'

    def __init__(self, tokens):
        self.tokens = tokens
        self.posicion = 0
        self.ast = {"tipo_juego": None,
                    "config": {"start_level": self.NIVEL_POR_DEFECTO},
                    "shapes": {}, "songs": {}, "effects": {}, "events": {},
                    "levels": [{"nombre": self.NIVEL_POR_DEFECTO}]}
        # True mientras levels sea el BABY materializado y no uno del .brick:
        # asi un nivel llamado BABY no choca con el default.
        self.niveles_es_default = True

    def parse(self):
        while self.posicion < len(self.tokens):
            token_actual = self.tokens[self.posicion]
            if token_actual == 'GAME_TYPE':
                self.parsear_tipo_juego()
            elif token_actual == 'GAME_GRID':
                self.parsear_grid()
            elif token_actual == 'DEFINE':
                # DEFINE abre tres cosas distintas: SHAPE, SONG y EFFECT.
                # Se mira el token siguiente para no comerse el DEFINE.
                siguiente = self.ver(1)
                if siguiente == 'SONG':
                    self.parsear_cancion()
                elif siguiente == 'EFFECT':
                    self.parsear_efecto()
                elif siguiente == 'BOSS':
                    # Bloque dedicado de la Actividad 5B: DEFINE BOSS ... END
                    # es un DEFINE SHAPE con TYPE BOSS ya puesto.
                    self.parsear_shape(forzar_tipo='BOSS')
                else:
                    self.parsear_shape()
            elif token_actual == 'LEVELS':
                self.parsear_niveles()
            elif token_actual == 'ON':
                self.parsear_evento()
            else:
                self.posicion += 1
        self.validar_musicas_de_niveles()
        if self.ast['tipo_juego'] == 'TANKS':
            self.validar_tanques()
        return self.ast

    def validar_musicas_de_niveles(self):
        # Va al FINAL del parse a proposito: asi el orden de los bloques da
        # igual y una cancion puede declararse despues del LEVELS. Sin esto, un
        # typo en el nombre dejaria el nivel mudo sin decir por que.
        for nivel in self.ast['levels']:
            cancion = nivel.get('music')
            if cancion and cancion not in self.ast['songs']:
                raise Exception("Error de sintaxis: el nivel '" + nivel['nombre'] +
                                "' pide la cancion '" + cancion +
                                "' pero no esta definida")

    def validar_tanques(self):
        # Solo GAME_TYPE TANKS: Snake y Tetris no declaran TYPE y no pasan por
        # aqui. Itera una lista ordenada porque en py2.7 el dict de shapes no
        # conserva el orden de declaracion.
        formas = sorted(self.ast['shapes'].items())
        dicts = [(nombre, datos) for nombre, datos in formas if isinstance(datos, dict)]

        jugadores = [nombre for nombre, datos in dicts if datos.get('type') == 'PLAYER']
        if len(jugadores) != 1:
            raise Exception("Error de sintaxis: TANKS necesita exactamente una forma con "
                            "TYPE PLAYER (hay " + str(len(jugadores)) + ")")
        if not [1 for _, datos in dicts if datos.get('type') == 'ENEMY']:
            raise Exception("Error de sintaxis: TANKS necesita al menos una forma con TYPE ENEMY")

        balas = [(nombre, datos) for nombre, datos in dicts if datos.get('type') == 'BULLET']
        for nombre, datos in balas:
            if datos.get('owner') not in self.BANDOS:
                raise Exception("Error de sintaxis: la bala '" + nombre +
                                "' necesita OWNER PLAYER o OWNER ENEMY")
        if not [1 for _, datos in balas if datos.get('owner') == 'PLAYER']:
            raise Exception("Error de sintaxis: TANKS necesita una bala con TYPE BULLET OWNER PLAYER")
        if not [1 for _, datos in balas if datos.get('owner') == 'ENEMY']:
            raise Exception("Error de sintaxis: TANKS necesita una bala con TYPE BULLET OWNER ENEMY")

        for nombre, datos in dicts:
            for clave, etiqueta in self.ETIQUETAS_NUMERICAS.items():
                if clave in datos and datos[clave] < 1:
                    raise Exception("Error de sintaxis: el atributo " + etiqueta +
                                    " de la forma '" + nombre + "' debe ser mayor o igual a 1")
            tipo = datos.get('type')
            for matriz in datos.get('estados') or []:
                if not matriz or not any(valor != 0 for fila in matriz for valor in fila):
                    raise Exception("Error de sintaxis: la forma '" + nombre +
                                    "' tiene la matriz sin celdas encendidas")
                ancho = len(matriz[0])
                for fila in matriz:
                    if len(fila) != ancho:
                        raise Exception("Error de sintaxis: la forma '" + nombre +
                                        "' tiene filas de distinto ancho")
                if tipo in self.MATRICES_CUADRADAS and len(matriz) != ancho:
                    raise Exception("Error de sintaxis: la forma '" + nombre + "' con TYPE " +
                                    str(tipo) + " necesita una matriz cuadrada")

    def consumir(self, token_esperado=None):
        if self.posicion < len(self.tokens):
            token = self.tokens[self.posicion]
            if token_esperado and token != token_esperado:
                raise Exception("Error de sintaxis: Se esperaba '" + token_esperado + "' pero se encontro '" + token + "'")
            self.posicion += 1
            return token
        if token_esperado:
            raise Exception("Error de sintaxis: Se esperaba '" + token_esperado + "' pero se llego al final del archivo.")
        return None

    def ver(self, adelante=0):
        # Token en la posicion actual (o `adelante` posiciones mas alla), o
        # None si se acabo. Evita IndexError en .brick truncados.
        pos = self.posicion + adelante
        if 0 <= pos < len(self.tokens):
            return self.tokens[pos]
        return None

    def consumir_numero(self):
        token = self.consumir()
        if token is None:
            raise Exception("Error de sintaxis: se esperaba un numero pero se llego al final del archivo.")
        try:
            return int(token)
        except ValueError:
            raise Exception("Error de sintaxis: se esperaba un numero pero se encontro '" + token + "'")

    def consumir_decimal(self):
        # El lexer entrega 0.15 como un solo token (ver token_regex), asi que
        # este es el unico punto del parser que acepta decimales.
        token = self.consumir()
        if token is None:
            raise Exception("Error de sintaxis: se esperaba un numero pero se llego al final del archivo.")
        try:
            return float(token)
        except ValueError:
            raise Exception("Error de sintaxis: se esperaba un numero pero se encontro '" + token + "'")

    def parsear_tipo_juego(self):
        self.consumir('GAME_TYPE')
        self.ast['tipo_juego'] = self.consumir()

    def parsear_grid(self):
        self.consumir('GAME_GRID')
        self.consumir('(')
        ancho = self.consumir_numero()
        self.consumir(',')
        alto = self.consumir_numero()
        self.consumir(')')
        self.ast['config']['grid_size'] = [ancho, alto]

    def parsear_shape(self, forzar_tipo=None):
            self.consumir('DEFINE')
            if forzar_tipo:
                self.consumir(forzar_tipo)
            else:
                self.consumir('SHAPE')
            nombre_shape = self.consumir()
            datos = {'geometry': 'RECT', 'color': 'CYAN', 'chance': 10}

            # TYPE: PLAYER y TYPE PLAYER son equivalentes: solo TYPE y OWNER
            # admiten los dos puntos opcionales.
            while self.ver() in self.ATRIBUTOS_SHAPE:
                token = self.consumir()
                clave, tipo = self.ATRIBUTOS_SHAPE[token]
                if token in ('TYPE', 'OWNER') and self.ver() == ':':
                    self.consumir(':')
                if tipo == 'numero':
                    datos[clave] = self.consumir_numero()
                    continue
                valor = self.consumir()
                if token == 'TYPE' and valor not in self.TIPOS_ENTIDAD:
                    raise Exception("Error de sintaxis: TYPE '" + str(valor) +
                                    "' no valido en la forma '" + nombre_shape +
                                    "' (use PLAYER, ENEMY, BULLET, WALL, PICKUP o BOSS)")
                if token == 'OWNER' and valor not in self.BANDOS:
                    raise Exception("Error de sintaxis: OWNER '" + str(valor) +
                                    "' no valido en la forma '" + nombre_shape +
                                    "' (use PLAYER o ENEMY)")
                datos[clave] = valor

            self.consumir(':')
            estados = []
            while self.ver() == 'STATE':
                self.consumir('STATE')
                self.consumir()
                self.consumir(':')
                matriz = []
                while self.ver() == '[':
                    fila = []
                    self.consumir('[')
                    while self.ver() != ']':
                        if self.ver() is None:
                            raise Exception("Error de sintaxis: fila sin ']' antes del fin del archivo.")
                        fila.append(self.consumir_numero())
                        if self.ver() == ',': self.consumir(',')
                    self.consumir(']')
                    matriz.append(fila)
                estados.append(matriz)
            self.consumir('END')
            datos['estados'] = estados
            if forzar_tipo:
                datos['type'] = forzar_tipo
            self.ast['shapes'][nombre_shape] = datos
    # NIVELES
    # --------
    #
    # levels es una LISTA y no un diccionario a proposito: el menu se numera por
    # posicion y en Python 2.7 un dict no conserva el orden de declaracion, asi
    # que la tecla 2 elegiria un nivel arbitrario.

    MODIFICADORES_NIVEL = {'TICK': ('tick', 'real'), 'MUSIC': ('music', 'nombre'), 'INVULNERABILITY_DURATION': ('invulnerability_duration','numero'), 'GEOMETRY': ('geometry', 'nombre'), 'POISON_ENABLED': ('poison_enabled', 'booleano'), 'POISON_KILLS': ('poison_kills', 'booleano'), 'CLOUDS_COUNT': ('clouds_count', 'numero'), 'WALLS': ('walls', 'numero'), 'TARGET_SCORE': ('target_score', 'numero')}

    # Atributos de DEFINE SHAPE. COLOR/CHANCE/GEOMETRY ya existian; el resto es
    # de la Actividad 5. La tabla guarda el tipo del valor para saber si se lee
    # con consumir_numero() o con consumir().
    ATRIBUTOS_SHAPE = {
        'GEOMETRY': ('geometry', 'nombre'),
        'COLOR': ('color', 'nombre'),
        'CHANCE': ('chance', 'numero'),
        'TYPE': ('type', 'nombre'),
        'HP': ('hp', 'numero'),
        'DAMAGE': ('damage', 'numero'),
        'SPEED': ('speed', 'numero'),
        'FIRE_RATE': ('fire_rate', 'numero'),
        'HEAL': ('heal', 'numero'),
        'OWNER': ('owner', 'nombre'),
    }
    TIPOS_ENTIDAD = ('PLAYER', 'ENEMY', 'BULLET', 'WALL', 'PICKUP', 'BOSS')
    BANDOS = ('PLAYER', 'ENEMY')
    # Solo se exige matriz cuadrada a las entidades que ocupan la grilla como
    # un bloque (la bala y el pickup son de 1 celda).
    MATRICES_CUADRADAS = ('PLAYER', 'ENEMY', 'BOSS', 'WALL')
    ETIQUETAS_NUMERICAS = {'hp': 'HP', 'damage': 'DAMAGE', 'speed': 'SPEED',
                           'fire_rate': 'FIRE_RATE', 'heal': 'HEAL'}

    def parsear_niveles(self):
        # LEVELS: [START: NOMBRE] (LEVEL NOMBRE: mods END)+ END
        if not self.niveles_es_default:
            # Sin esto, un segundo bloque pisaba el primero en silencio y el
            # autor creia haber declarado los dos.
            raise Exception("Error de sintaxis: LEVELS esta declarado mas de una vez")
        self.consumir('LEVELS')
        self.consumir(':')

        inicio = None
        if self.ver() == 'START':
            self.consumir('START')
            self.consumir(':')
            inicio = self.consumir()

        niveles = []
        # El nivel por defecto (BABY) NO cuenta como nombre ya declarado: un
        # .brick puede declarar perfectamente un nivel llamado BABY.
        vistos = []
        while self.ver() == 'LEVEL':
            nivel = self.parsear_nivel(vistos)
            vistos.append(nivel['nombre'])
            niveles.append(nivel)
        if not niveles:
            raise Exception("Error de sintaxis: LEVELS no declara ningun nivel")
        self.consumir('END')

        # Sin START arranca el primer nivel declarado, que es el orden del
        # .brick. El default BABY es del caso "no hay bloque LEVELS", y ese se
        # resuelve en __init__.
        if inicio is None:
            inicio = niveles[0]['nombre']
        if inicio not in [n['nombre'] for n in niveles]:
            raise Exception("Error de sintaxis: el nivel inicial '" + str(inicio) +
                            "' no esta definido")
        # Sin START, arranca el primer nivel declarado (el orden del .brick).
        self.ast['levels'] = niveles
        self.ast['config']['start_level'] = inicio
        self.niveles_es_default = False


    # AUDIO DECLARADO EN EL .BRICK
    # -----------------------------
    #
    # Una cancion o un efecto es una lista de notas; cada nota es un par
    # [frecuencia en Hz, duracion en ms]. El .brick escribe el nombre de la
    # nota (E5, A4) y el compilador lo traduce a Hercios con la afinacion
    # estandar, de modo que el runtime solo recibe numeros.

    NOTAS_SEMITONO = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

    def nota_a_hz(self, token):
        # Recibe el token completo: 'E5', 'D4' o 'D#4'. El sostenido suma un
        # semitono, asi que D#4 es la misma letra de D4 un semitono mas arriba.
        letra = token[0]
        if letra not in self.NOTAS_SEMITONO:
            raise Exception("Error de sintaxis: nota '" + token +
                            "' no valida (use A-G, opcional # y la octava, ej. E5 o D#4)")
        semitono = self.NOTAS_SEMITONO[letra]
        resto = token[1:]
        if resto.startswith('#'):
            semitono += 1
            resto = resto[1:]
        if not resto.isdigit():
            raise Exception("Error de sintaxis: nota '" + token +
                            "' no valida (use A-G, opcional # y la octava, ej. E5 o D#4)")
        midi = 12 * (int(resto) + 1) + semitono
        return round(440.0 * (2.0 ** ((midi - 69) / 12.0)), 1)

    def parsear_cancion(self):
        # DEFINE SONG <nombre> [WAVE <onda>] ":" <notas> END
        self.consumir('DEFINE')
        self.consumir('SONG')
        nombre = self.consumir()
        onda = ONDA_SENOIDAL
        if self.ver() == 'WAVE':
            self.consumir('WAVE')
            onda = self.consumir()
            if onda not in ONDAS:
                raise Exception("Error de sintaxis: onda '" + str(onda) +
                                "' no valida (use SINE o SQUARE)")
        self.consumir(':')
        if self.ver() == 'VOICE':
            # Varias voces: se mezclan muestra a muestra en el sintetizador.
            voces = self.leer_voces()
            self.ast['songs'][nombre] = {"voces": voces, "wave": onda}
        else:
            notas = self.leer_notas()
            self.ast['songs'][nombre] = {"notas": notas, "wave": onda}
        self.consumir('END')

    def leer_voces(self):
        # VOICE <n>: <notas> END  (dos o mas)
        # El numero es informativo: las voces se mezclan entre si, asi que solo
        # importa el orden de declaracion. Se valida para dar un error claro si
        # alguien repite uno.
        voces = []
        vistos = []
        while self.ver() == 'VOICE':
            self.consumir('VOICE')
            numero = self.consumir_numero()
            self.consumir(':')
            if numero in vistos:
                raise Exception("Error de sintaxis: la voz " + str(numero) +
                                " esta definida dos veces")
            vistos.append(numero)
            voces.append(self.leer_notas())
            self.consumir('END')
        if len(voces) < 2:
            raise Exception("Error de sintaxis: una cancion con VOICE necesita al "
                            "menos dos voces; con una sola, escribe las notas "
                            "directas despues de los dos puntos")
        return voces

    def parsear_efecto(self):
        self.consumir('DEFINE')
        self.consumir('EFFECT')
        nombre = self.consumir()
        self.consumir(':')
        notas = self.leer_notas()
        self.consumir('END')
        self.ast['effects'][nombre] = {"notas": notas}

    def leer_notas(self):
        notas = []
        while self.ver() == 'NOTE':
            self.consumir('NOTE')
            token_nota = self.consumir()
            if token_nota is None:
                raise Exception("Error de sintaxis: NOTE sin nombre antes del fin del archivo.")
            ms = self.consumir_numero()
            if token_nota == SILENCIO:
                # Un REST es una nota de frecuencia 0: sin(0) = 0, asi que el
                # sintetizador no necesita ninguna rama para callar, y el
                # tiempo sigue contando porque el bucle consume sus muestras.
                notas.append([0.0, ms])
            else:
                notas.append([self.nota_a_hz(token_nota), ms])
        return notas

    def parsear_nivel(self, vistos):
        self.consumir('LEVEL')
        nombre = self.consumir()
        self.consumir(':')
        if nombre in vistos:
            raise Exception("Error de sintaxis: el nivel '" + nombre +
                            "' esta definido dos veces")
        nivel = {'nombre': nombre}
        while self.ver() not in (':', 'END', None):
            entrada = self.MODIFICADORES_NIVEL.get(self.ver())
            if entrada is None:
                # Un modificador desconocido se reporta, nunca se ignora: si se
                # pasara, el nivel arrancaria con el default sin avisar.
                raise Exception("Error de sintaxis: modificador desconocido '" +
                                str(self.ver()) + "' en el nivel '" + nombre + "'")
            self.consumir()
            clave, tipo = entrada
            # TICK toma un real y MUSIC un identificador: por eso la tabla
            # guarda el tipo. Sin esto, float('TEMA_CALMO') reventaria.
            if tipo == 'real':
                nivel[clave] = self.consumir_decimal()
            elif tipo == 'numero':
                nivel[clave] = self.consumir_numero()
            elif tipo == 'booleano':
                if self.ver() is None or self.ver() == 'END':
                    raise Exception("Error de sintaxis: se esperaba el valor o nombre del "
                                    "modificador del nivel '" + nombre + "'")
                # TRUE/FALSE llegan como PALABRA. Sin convertirlo el motor
                # recibe el string 'FALSE' y bool('FALSE') es True: el veneno
                # se activaria en el nivel que lo apaga.
                nivel[clave] = str(self.consumir()).upper() == 'TRUE'
            else:
                if self.ver() is None or self.ver() == 'END':
                    raise Exception("Error de sintaxis: se esperaba el valor o nombre del "
                                    "modificador del nivel '" + nombre + "'")
                nivel[clave] = self.consumir()
        self.consumir('END')
        if 'tick' in nivel and not (0 < nivel['tick'] < INFINITO):
            # La comparacion sola no alcanza: en py2 nan <= 0 es False y
            # inf <= 0 tambien, asi que ambos se colaban. Con un TICK nan el
            # motor se come el valor (0.05 >= nan es False para siempre) y la
            # partida queda congelada sin error de compilacion. Ademas json.dump
            # escribe NaN/Infinity crudos, que no son JSON valido.
            raise Exception("Error de sintaxis: TICK del nivel '" + nombre +
                            "' debe ser mayor que 0")
        return nivel
    
    def parsear_evento(self):
        self.consumir('ON')
        nombre = self.consumir()
        # ON TARGET_SCORE 1000: guarda el umbral en config; ON TARGET_SCORE:
        # usa 1000 por defecto en el motor.
        if nombre == 'TARGET_SCORE' and self.ver() not in (':', None):
            token = self.ver()
            try:
                int(token)
            except (ValueError, TypeError):
                token = None
            if token is not None:
                self.ast['config']['target_score'] = self.consumir_numero()
        nombre_evento = 'ON_' + nombre
        self.consumir(':')
        acciones = []
        while self.ver() not in ('END', None):
            verbo = self.consumir()

            # Si el comando es de una sola palabra, lo añadimos y continuamos
            if verbo in ('GAME_OVER', 'STOP_MUSIC', 'RESET_SCORE'):
                acciones.append({'accion': verbo, 'objeto': None, 'params': []})
                continue

            # Si no, parseamos el resto de la acción
            objeto = self.consumir()
            params = []
            if self.ver() == 'AT':
                self.consumir('AT')
                if self.ver() == 'RANDOM':
                    params.append(self.consumir())
                else:
                    self.consumir('(')
                    x = self.consumir_numero()
                    self.consumir(',')
                    y = self.consumir_numero()
                    self.consumir(')')
                    params.append([x, y])
            elif self.ver() not in ['END', 'ON', 'DEFINE', 'SPAWN', 'MOVE', 'ROTATE', 'INCREASE_SCORE', 'DECREASE_SCORE', 'GRANT_INVULNERABILITY', 'SET_DIRECTION', 'GROW', 'GAME_OVER', 'PLAY_MUSIC', 'STOP_MUSIC', 'PLAY_EFFECT', 'RESET_SCORE', None]:
                params.append(self.consumir())
            
            # Validar acciones que requieren un número como parámetro principal
            if verbo in ('INCREASE_SCORE', 'DECREASE_SCORE', 'GRANT_INVULNERABILITY'):
                try:
                    int(objeto)
                except (ValueError, TypeError):
                    raise Exception("Error de sintaxis: La accion '" + verbo + "' necesita un numero, se encontro '" + str(objeto) + "'")
            elif verbo == 'GROW':
                if not params:
                    raise Exception("Error de sintaxis: GROW necesita un numero.")
                try:
                    int(params[0])
                except (ValueError, TypeError):
                    raise Exception("Error de sintaxis: La accion 'GROW' necesita un numero, se encontro '" + str(params[0]) + "'")
            
            acciones.append({'accion': verbo, 'objeto': objeto, 'params': params})
        self.consumir('END')
        self.ast['events'][nombre_evento] = acciones
        
def generar_codigo(ast, archivo_salida):
    with open(archivo_salida, 'w') as f:
        json.dump(ast, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python compiler.py <archivo_entrada.brick>")
        sys.exit(1)
    archivo_entrada = sys.argv[1]
    archivo_salida = archivo_entrada.replace('.brick', '.json')
    print("Compilando " + archivo_entrada + "...")
    try:
        with open(archivo_entrada, 'r') as f:
            codigo = f.read()
        tokens = lexer(codigo)
        parser = Parser(tokens)
        ast = parser.parse()
        generar_codigo(ast, archivo_salida)
        print("Compilacion exitosa! Archivo de juego creado en " + archivo_salida)
    except Exception as e:
        print("\n!!! ERROR DE COMPILACION !!!")
        print(str(e))
        sys.exit(1)
