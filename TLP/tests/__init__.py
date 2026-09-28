# -*- coding: utf-8 -*-
# Los tests nunca usan el Tkinter real: se instala uno falso antes de
# que cualquier test importe la carpeta engine/.
#
# Ejecutar desde la carpeta TLP:
#   python2 -m unittest discover -s tests -t . -v

from tests import tk_falso

tk_falso.instalar()
