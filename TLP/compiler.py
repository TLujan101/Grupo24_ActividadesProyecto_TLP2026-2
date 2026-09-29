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
    token_regex = r'\b[A-Z_]+\b|\d+|[\[\](),:]'
    tokens = re.findall(token_regex, codigo_fuente)
    resto = re.sub(token_regex, '', codigo_fuente)
    if resto.strip():
        raise Exception("Caracteres no reconocidos: '" + resto.strip()[:40] + "'")
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.posicion = 0
        self.ast = {"tipo_juego": None, "config": {}, "shapes": {}, "events": {}}

    def parse(self):
        while self.posicion < len(self.tokens):
            token_actual = self.tokens[self.posicion]
            if token_actual == 'GAME_TYPE':
                self.parsear_tipo_juego()
            elif token_actual == 'GAME_GRID':
                self.parsear_grid()
            elif token_actual == 'DEFINE':
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

    def ver(self):
        # Proximo token o None si se acabo (evita IndexError en .brick truncados)
        if self.posicion < len(self.tokens):
            return self.tokens[self.posicion]
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


    def parsear_evento(self):
        self.consumir('ON')
        nombre_evento = 'ON_' + self.consumir()
        self.consumir(':')
        acciones = []
        while self.ver() not in ('END', None):
            verbo = self.consumir()

            # Si el comando es de una sola palabra, lo anadimos y continuamos
            if verbo == 'GAME_OVER':
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
            elif self.ver() not in ['END', 'ON', 'DEFINE', 'SPAWN', 'MOVE', 'ROTATE', 'INCREASE_SCORE', 'SET_DIRECTION', 'GROW', 'GAME_OVER', None]:
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
