# -*- coding: utf-8 -*-
# tk_falso.py --- Reemplazo de Tkinter para los tests.
#
# No abre ventanas: solo guarda lo que el juego le pide (rectangulos
# dibujados, textos, callbacks de after, etc.) para poder revisarlo.

import sys
import types

LEFT = 'left'
RIGHT = 'right'
Y = 'y'


class WidgetFalso(object):
    def __init__(self, master=None, **opciones):
        self.master = master
        self.opciones = dict(opciones)
        self.hijos = []
        self.destruido = False
        if master is not None:
            master.hijos.append(self)

    def pack(self, **opciones): pass
    def place(self, **opciones): self.opciones_place = opciones
    def config(self, **opciones): self.opciones.update(opciones)
    configure = config
    def destroy(self): self.destruido = True
    def title(self, texto): self.titulo = texto
    def geometry(self, texto): pass
    def resizable(self, ancho, alto): pass
    def transient(self, master): pass


class Tk(WidgetFalso):
    def __init__(self):
        WidgetFalso.__init__(self)
        self.afters = []
        self.cancelados = []
        self.binds = {}
        self.protocolos = {}

    def after(self, ms, funcion):
        self.afters.append((ms, funcion))
        return 'after#%d' % len(self.afters)

    def after_cancel(self, timer_id): self.cancelados.append(timer_id)
    def bind(self, secuencia, funcion): self.binds[secuencia] = funcion
    def protocol(self, nombre, funcion): self.protocolos[nombre] = funcion
    def mainloop(self): pass


class Canvas(WidgetFalso):
    def __init__(self, master=None, **opciones):
        WidgetFalso.__init__(self, master, **opciones)
        self.rectangulos = []

    def create_rectangle(self, x1, y1, x2, y2, **opciones):
        self.rectangulos.append(((x1, y1, x2, y2), opciones.get('fill')))

    def delete(self, que):
        if que == "all":
            self.rectangulos = []


class Frame(WidgetFalso): pass
class Label(WidgetFalso): pass
class Button(WidgetFalso): pass
class Toplevel(WidgetFalso): pass


def instalar():
    # Registra este modulo como 'Tkinter' antes de importar los juegos
    modulo = types.ModuleType('Tkinter')
    for nombre in ('LEFT', 'RIGHT', 'Y', 'Tk', 'Canvas', 'Frame', 'Label', 'Button', 'Toplevel'):
        setattr(modulo, nombre, globals()[nombre])
    sys.modules['Tkinter'] = modulo


class EventoFalso(object):
    # Imita el evento de teclado de Tkinter (solo usamos keysym)
    def __init__(self, keysym):
        self.keysym = keysym
