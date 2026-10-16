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

def lexer(codigo_fuente):
    # Un '#' precedido por letra A-G no abre comentario: es el sostenido de una
    # nota (D#4). Si lo abriera, se comia el resto de la linea y con ella la
    # duracion de la nota.
    codigo_fuente = re.sub(r'(?<![A-G])#.*', '', codigo_fuente)
    # Un nombre de nota (E5, D#4) es un token propio: si no, el lexer
    # partia "E5" en "E" y "5" y la nota se colaba como texto no reconocido.
    # El grupo de decimales va pegado al de enteros: suelto, \d+ se comia el 0
    # de 0.15 y el punto caia en resto como caracter no reconocido.
    token_regex = r'\b[A-G]#?[0-9]+\b|\b[A-Z_]+\b|\d+(?:\.\d+)?|[\[\](),:]'
    tokens = re.findall(token_regex, codigo_fuente)
    resto = re.sub(token_regex, '', codigo_fuente)
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
                else:
                    self.parsear_shape()
            elif token_actual == 'LEVELS':
                self.parsear_niveles()
            elif token_actual == 'ON':
                self.parsear_evento()
            else:
                self.posicion += 1
        self.validar_musicas_de_niveles()
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

    def parsear_shape(self):
        self.consumir('DEFINE')
        self.consumir('SHAPE')
        nombre_shape = self.consumir()
        color_shape = "CYAN"
        chance_shape = 10
        if self.ver() == "COLOR":
            self.consumir("COLOR")
            color_shape = self.consumir()
        if self.ver() == "CHANCE":
            self.consumir("CHANCE")
            chance_shape = self.consumir_numero()
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
        self.ast['shapes'][nombre_shape] = {"estados": estados, "color": color_shape, "chance": chance_shape}

    # NIVELES
    # --------
    #
    # levels es una LISTA y no un diccionario a proposito: el menu se numera por
    # posicion y en Python 2.7 un dict no conserva el orden de declaracion, asi
    # que la tecla 2 elegiria un nivel arbitrario.

    MODIFICADORES_NIVEL = {'TICK': ('tick', 'real'), 'MUSIC': ('music', 'nombre')}

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
            else:
                if self.ver() is None or self.ver() == 'END':
                    raise Exception("Error de sintaxis: se esperaba el nombre de la "
                                    "cancion del nivel '" + nombre + "'")
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
        notas = self.leer_notas()
        self.consumir('END')
        self.ast['songs'][nombre] = {"notas": notas, "wave": onda}

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


    def parsear_evento(self):
        self.consumir('ON')
        nombre_evento = 'ON_' + self.consumir()
        self.consumir(':')
        acciones = []
        while self.ver() not in ('END', None):
            verbo = self.consumir()

            # Si el comando es de una sola palabra, lo anadimos y continuamos
            if verbo in ('GAME_OVER', 'STOP_MUSIC'):
                acciones.append({'accion': verbo, 'objeto': None, 'params': []})
                continue

            # Si no, parseamos el resto de la accion
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
            elif self.ver() not in ['END', 'ON', 'DEFINE', 'SPAWN', 'MOVE', 'ROTATE', 'INCREASE_SCORE', 'SET_DIRECTION', 'GROW', 'GAME_OVER', 'PLAY_MUSIC', 'STOP_MUSIC', 'PLAY_EFFECT', None]:
                params.append(self.consumir())
            if verbo == 'INCREASE_SCORE':
                try:
                    int(objeto)
                except (ValueError, TypeError):
                    raise Exception("Error de sintaxis: INCREASE_SCORE necesita un numero, se encontro '" + str(objeto) + "'")
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
