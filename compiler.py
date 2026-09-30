#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# compiler.py
# Compilador universal para BrickScript
# Uso: python compiler.py <archivo_entrada.brick>

import sys
import re
import json

def lexer(codigo_fuente):
    codigo_fuente = re.sub(r'#.*', '', codigo_fuente)
    # Un nombre de nota (E5, A4, G3) es un token propio: si no, el lexer
    # partia "E5" en "E" y "5" y la nota se colaba como texto no reconocido.
    token_regex = r'\b[A-G][0-9]+\b|\b[A-Z_]+\b|\d+|[\[\](),:]'
    tokens = re.findall(token_regex, codigo_fuente)
    resto = re.sub(token_regex, '', codigo_fuente)
    if resto.strip():
        raise Exception("Caracteres no reconocidos: '" + resto.strip()[:40] + "'")
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.posicion = 0
        self.ast = {"tipo_juego": None, "config": {}, "shapes": {},
                    "songs": {}, "effects": {}, "events": {}}

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
            elif token_actual == 'ON':
                self.parsear_evento()
            else:
                self.posicion += 1
        return self.ast

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


    # AUDIO DECLARADO EN EL .BRICK
    # -----------------------------
    #
    # Una cancion o un efecto es una lista de notas; cada nota es un par
    # [frecuencia en Hz, duracion en ms]. El .brick escribe el nombre de la
    # nota (E5, A4) y el compilador lo traduce a Hercios con la afinacion
    # estandar, de modo que el runtime solo recibe numeros.

    NOTAS_SEMITONO = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

    def nota_a_hz(self, letra, octava):
        midi = 12 * (octava + 1) + self.NOTAS_SEMITONO[letra]
        return round(440.0 * (2.0 ** ((midi - 69) / 12.0)), 1)

    def parsear_cancion(self):
        self.consumir('DEFINE')
        self.consumir('SONG')
        nombre = self.consumir()
        self.consumir(':')
        notas = self.leer_notas()
        self.consumir('END')
        self.ast['songs'][nombre] = {"notas": notas}

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
            letra, octava = token_nota[0], token_nota[1:]
            if letra not in self.NOTAS_SEMITONO or not octava.isdigit():
                raise Exception("Error de sintaxis: nota '" + token_nota +
                                "' no valida (use A-G mas octava, ej. E5)")
            ms = self.consumir_numero()
            notas.append([self.nota_a_hz(letra, int(octava)), ms])
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
