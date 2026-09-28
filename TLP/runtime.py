# -*- coding: utf-8 -*-
# runtime.py (VERSION CON INTERFAZ GRAFICA USANDO Tkinter y caracteres ASCII unicamente)
# Carga el .json generado por compiler.py y ejecuta el juego que corresponda.
# La logica de cada juego vive en la carpeta engine/.

import sys
import json

from engine import crear_juego


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
    try:
        juego = crear_juego(datos_juego)
    except ValueError as e:
        print ("Error: " + str(e))
        sys.exit(1)
    juego.run()
