# Actividad 4 — Sección C: Niveles de dificultad — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar al lenguaje BrickScript un bloque `LEVELS` que permite a un `.brick` declarar varios niveles de dificultad, elegir con qué nivel arranca la partida y dejar que el jugador lo cambie con teclas antes de empezar.

**Architecture:** El compilador traduce el bloque `LEVELS` a una lista de niveles en el JSON y, si el `.brick` no lo declara, materializa un único nivel `BABY`. El motor lee la configuración del nivel activo y la aplica sobre los valores por defecto que cada juego dejó en `inicializar_estado()`. El motor nunca compara contra un nombre de nivel: si un `.brick` no declara nada, la configuración sale vacía y todo queda en los defaults.

**Tech Stack:** Python 2.7 (interprete declarado en `README.md:7` y `jugar.bat`), biblioteca estándar, Tkinter para la GUI, `unittest` para los tests. Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-10-16-actividad4-c-niveles-design.md`

## Global Constraints

- **Python 2.7 obligatorio.** `docs/Instalacion.txt` dice *"IMPORTANTE: El codigo NO es compatible con Python 3"*. Todo el código nuevo usa `.format()` o `%`, nunca f-strings, nunca `super()` sin argumentos. El intérprete de referencia es `C:\Python27\python.exe`.
- **Baseline verde antes de empezar:** `C:\Python27\python.exe -m unittest discover -s tests -t .` → **32 tests, OK**. Si al empezar un test falla, no es de esta sección: investigate antes de tocar código.
- **Suite completa en verde al final de cada tarea.** 32 tests hoy; cada tarea suma los suyos.
- **Sin dependencias nuevas.** Solo biblioteca estándar de Python 2.7.
- **Comentarios y mensajes en ASCII sin tildes** (`#` abre comentario en el `.brick` y el código existente es ASCII: `configuracion`, `sobreescribe`, `Se esperaba`).
- **NO tocar `games/snake.brick`** (byte a byte idéntico a su estado actual). Es la prueba viviente de retrocompatibilidad.
- **NO tocar ni commitear `games/tetris_reborn.brick`**: tiene un cambio sin commitear (estados 3 y 4 de la pieza I) que pertenece a otro trabajo. Verificar con `git status` antes de cada commit.
- **No agregar primitivas de dibujo nuevas a `tests/tk_falso.py`** salvo `create_text` (Task 4). `create_oval` y `create_polygon` son de la sección A.
- Orden de commits fijo, uno por tarea.

## Review Focus

Cinco modos de falla que el spec implica y que son los que más muerden:

1. **Un `.brick` sin `LEVELS` debe comportarse exactamente como antes**, byte a byte en su AST salvo las dos claves nuevas. Si `snake.brick` cambia de comportamiento, la sección D queda rota.
2. **JSON viejo sin la clave `levels`.** Ya hay dos en disco (`games/tetris.json`, `games/tetris_reborn.json`), y `tests/test_juegos.py:31` fabrica juegos a mano. Nada de `self.datos_juego['levels']`: siempre `.get()`.
3. **El orden de los niveles en el menú.** Si el menú los muestra desordenados, la tecla `2` elige el nivel equivocado y el autor del `.brick` no puede predecirlo. Es la razón de que `levels` sea lista (spec 5.3).
4. **Un `.brick` con 2+ niveles deja la partida sin arrancar** si nadie elige. Nadie debe poder jugar con el menú abierto, y las flechas no deben filtrarse al juego mientras se elige.
5. **`TICK` en un nivel que no lo declara no debe pisar el default del juego.** Tetris 0.4 y Snake 0.15 son distintos; un `TICK 0` materializado en el compilador arrancaría Tetris a 0.15.

---

## File Structure

| Archivo | Responsabilidad | Estado |
|---------|-----------------|--------|
| `compiler.py` | Compilador universal. Ganancia: el lexer tokeniza decimales y `parsear_niveles()` construye la lista de niveles con sus validaciones | Modificar |
| `tests/test_compiler.py` | Tests unitarios del lexer y del parser. Hoy el compilador no tiene archivo de tests propios: se cubre indirectamente desde `test_juegos.py` | Crear |
| `grammars/snake.bnf` | Gramática de Snake. Se le agrega el bloque `LEVELS` y el `<extras>` con `COLOR`/`CHANCE` que el compilador ya soporta pero no estaba documentado | Modificar |
| `grammars/tetris.bnf` | Gramática de Tetris. Se le agrega el mismo bloque `LEVELS` y `<real>`: el parser es compartido, la regla sirve para los dos juegos | Modificar |
| `engine/game.py` | Clase base. Ganancia: estado del nivel activo, `aplicar_nivel()`, `iniciar_partida()` y el menú de selección | Modificar |
| `engine/snake.py` | Lógica de Snake. **No cambia**: `aplicar_nivel()` vive en `Game` y pisa el `velocidad_gravedad = 0.15` que Snake deja en `inicializar_estado()` | Sin cambios |
| `tests/tk_falso.py` | Doble de Tkinter. Ganancia: `Canvas.create_text` para poder afirmar el menú | Modificar |
| `tests/test_game.py` | Tests de la clase base. Se le agregan los del nivel y el menú | Modificar |
| `tests/test_snake.py` | Tests de Snake. Se le agregan los del tick por nivel | Modificar |
| `tests/test_retrocompatibilidad.py` | Prueba de que los `.brick` clásicos siguen funcionando. Se le agregan las aserciones del nivel por defecto | Modificar |
| `tests/test_juegos.py` | Integración. Se le agrega la prueba de que `snake_remake.brick` arranca tras elegir nivel | Modificar |
| `games/snake_remake.brick` | El juego de la sección C: tres niveles declarados | Modificar |
| `docs/Guia-BrickScript.txt` | Guía del lenguaje. Se le documenta `LEVELS` | Modificar |

---

## Task 1: El lexer acepta decimales

`TICK 0.15` hoy no compila: el regex `token_regex` usa `\d+`, el punto cae en `resto` y el lexer lanza *"Caracteres no reconocidos: '.'"*. Sin esto no hay forma de declarar la velocidad de un nivel en segundos.

**Files:**
- Create: `tests/test_compiler.py`
- Modify: `compiler.py:15`

**Interfaces:**
- Consumes: nada (es la primera tarea).
- Produces: `lexer(codigo_fuente) -> list[str]`. Los decimales llegan como **un solo token** (`'0.15'`), no como `'0'` y `'15'`. Los enteros se comportan igual que antes.

- [ ] **Step 1: Write the failing test**

Crear `tests/test_compiler.py` con:

```python
# -*- coding: utf-8 -*-
# Tests del compilador: el lexer y el parser de BrickScript.

import unittest

import compiler


class TestLexer(unittest.TestCase):

    def test_decimales(self):
        # El punto decimal es un token entero, no dos numeros sueltos
        self.assertEqual(compiler.lexer('TICK 0.15'), ['TICK', '0.15'])
        self.assertEqual(compiler.lexer('TICK 0.06'), ['TICK', '0.06'])
        self.assertEqual(compiler.lexer('TICK 150'), ['TICK', '150'])

    def test_enteros_siguen_igual(self):
        # GAME_GRID, CHANCE y las notas no deben cambiar
        self.assertEqual(compiler.lexer('GAME_GRID (18, 18)'),
                         ['GAME_GRID', '(', '18', ',', '18', ')'])
        self.assertEqual(compiler.lexer('DEFINE SHAPE X COLOR CYAN CHANCE 10:'),
                         ['DEFINE', 'SHAPE', 'X', 'COLOR', 'CYAN', 'CHANCE', '10', ':'])
        self.assertEqual(compiler.lexer('DEFINE SONG C: NOTE E5 400'),
                         ['DEFINE', 'SONG', 'C', ':', 'NOTE', 'E5', '400'])

    def test_identificadores_en_mayusculas(self):
        # Un nombre de nivel en minúsculas o mezclado no es un token válido:
        # el lenguaje entero está en mayúsculas.
        self.assertEqual(compiler.lexer('LEVEL NYAN_CAT:'),
                         ['LEVEL', 'NYAN_CAT', ':'])
        self.assertRaises(Exception, compiler.lexer, 'LEVEL Enthusiasta:')

    def test_cadena_con_comentarios_y_decimales(self):
        fuente = '# velocidad\nLEVEL BABY:\n  TICK 0.15\nEND'
        self.assertEqual(compiler.lexer(fuente),
                         ['LEVEL', 'BABY', ':', 'TICK', '0.15', 'END'])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```
C:\Python27\python.exe -m unittest tests.test_compiler -v
```
Expected: `test_decimales` falla con `Exception: Caracteres no reconocidos: '.'`; los otros tres pasan.

- [ ] **Step 3: Implement the lexer change in `compiler.py:15`**

Cambiar solo la regex, dejando el comentario que ya tiene arriba:

```python
    # El grupo de decimales va pegado al de enteros: sin el parentesis, \d+
    # se comeria el 0 de 0.15 y el punto caeria en resto.
    token_regex = r'\b[A-G][0-9]+\b|\b[A-Z_]+\b|\d+(?:\.\d+)?|[\[\](),:]'
```

- [ ] **Step 4: Run test to verify it passes**

```
C:\Python27\python.exe -m unittest tests.test_compiler -v
```
Expected: 4 tests, OK.

- [ ] **Step 5: Run the full suite to confirm no regression**

```
C:\Python27\python.exe -m unittest discover -s tests -t .
```
Expected: 36 tests, OK. El lexer es compartido: si algo falla, es que el cambio tocó GAME_GRID, CHANCE o las notas.

- [ ] **Step 6: Commit**

```
git add compiler.py tests/test_compiler.py
git commit -m "compiler: el lexer acepta decimales (necesario para TICK)

El regex tokenizaba \d+ suelto, asi que TICK 0.15 fallaba con 'Caracteres
no reconocidos: .'. El grupo de decimales va pegado al de enteros.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: El parser entiende el bloque LEVELS

Agrega el bloque a la gramática y traduce las cinco validaciones del spec 5.5 en errores de compilación. El default retrocompatible (`BABY`) se materializa en el constructor del parser, que es el único lugar donde nace el AST.

**Files:**
- Modify: `compiler.py` (`Parser.__init__` línea 26-27, `parse()` línea 29-50, nuevo `parsear_niveles`, nuevo `consumir_decimal`)
- Modify: `tests/test_compiler.py` (agregar `TestParserNiveles`)
- Modify: `grammars/snake.bnf`, `grammars/tetris.bnf`

**Interfaces:**
- Consumes: `lexer()` de la Task 1.
- Produces:
  - `compiler.NIVEL_POR_DEFECTO` → `'BABY'`. Etiqueta del nivel que el compilador inventa cuando el `.brick` no declara `LEVELS`. No lleva comportamiento asociado.
  - El AST siempre trae `"levels"` (lista) y `"config"["start_level"]` (string):
    ```python
    "levels": [{"nombre": "BABY", "tick": 0.15}, ...]   # orden de declaracion
    "config": {"grid_size": [18,18], "start_level": "NYAN_CAT"}
    ```
  - `Parser.parse() -> dict` acepta `LEVELS` en cualquier posición del archivo.

- [ ] **Step 1: Write the failing tests**

Agregar a `tests/test_compiler.py`:

```python
BRICK_CON_NIVELES = """
GAME_TYPE SNAKE
GAME_GRID (18, 18)
LEVELS:
  START: NYAN_CAT
  LEVEL BABY:
    TICK 0.15
  END
  LEVEL ENTUSIASTA:
    TICK 0.10
  END
  LEVEL NYAN_CAT:
    TICK 0.06
  END
END
ON START:
  SPAWN PLAYER AT (9, 9)
END
"""


def compilar(fuente):
    return compiler.Parser(compiler.lexer(fuente)).parse()


class TestParserNiveles(unittest.TestCase):

    def test_bloque_niveles(self):
        ast = compilar(BRICK_CON_NIVELES)
        self.assertEqual(ast['config']['start_level'], 'NYAN_CAT')
        self.assertEqual(ast['levels'], [{'nombre': 'BABY', 'tick': 0.15},
                                         {'nombre': 'ENTUSIASTA', 'tick': 0.1},
                                         {'nombre': 'NYAN_CAT', 'tick': 0.06}])

    def test_sin_bloque_niveles_queda_baby(self):
        # Punto D: sin la etiqueta de niveles se asigna Baby por defecto.
        # El nivel existe y es el inicial, pero NO lleva valores: el default
        # de cada modificador lo aporta el juego, no el compilador.
        ast = compilar('GAME_TYPE SNAKE\nGAME_GRID (18, 18)\n')
        self.assertEqual(ast['levels'], [{'nombre': 'BABY'}])
        self.assertEqual(ast['config']['start_level'], 'BABY')

    def test_start_ausente_usa_el_primer_nivel(self):
        ast = compilar('LEVELS:\n  LEVEL ENTUSIASTA:\n    TICK 0.1\n  END\nEND\n')
        self.assertEqual(ast['config']['start_level'], 'ENTUSIASTA')

    def test_nivel_sin_modificadores(self):
        ast = compilar('LEVELS:\n  LEVEL BABY:\n  END\nEND\n')
        self.assertEqual(ast['levels'], [{'nombre': 'BABY'}])

    def test_el_bloque_va_en_cualquier_posicion(self):
        # El parser es un despachador de tokens: el bloque no depende del orden
        for fuente in ('LEVELS:\n  LEVEL BABY:\n  END\nEND\nGAME_TYPE SNAKE\n',
                       'GAME_TYPE SNAKE\nLEVELS:\n  LEVEL BABY:\n  END\nEND\n'):
            self.assertEqual(compilar(fuente)['config']['start_level'], 'BABY')

    def test_errores_de_validacion(self):
        casos = [
            # (fuente, fragmento del mensaje)
            ('LEVELS:\n  START: X\n  LEVEL BABY:\n  END\nEND\n',
             "el nivel inicial 'X' no esta definido"),
            ('LEVELS:\n  LEVEL BABY:\n  END\n  LEVEL BABY:\n  END\nEND\n',
             "el nivel 'BABY' esta definido dos veces"),
            ('LEVELS:\nEND\n', 'LEVELS no declara ningun nivel'),
            ('LEVELS:\n  LEVEL BABY:\n    TICK 0\n  END\nEND\n',
             "TICK del nivel 'BABY' debe ser mayor que 0"),
            ('LEVELS:\n  LEVEL BABY:\n    TIC 0.15\n  END\nEND\n',
             "modificador desconocido 'TIC' en el nivel 'BABY'"),
        ]
        for fuente, esperado in casos:
            try:
                compilar(fuente)
                self.fail('debio fallar: ' + esperado)
            except Exception as error:
                self.assertIn(esperado, str(error))
```

- [ ] **Step 2: Run tests to verify they fail**

```
C:\Python27\python.exe -m unittest tests.test_compiler -v
```
Expected: `test_bloque_niveles` falla con `KeyError: 'start_level'`; `test_sin_bloque_niveles_queda_baby` falla con `KeyError: 'levels'`.

- [ ] **Step 3: Implement the parser changes in `compiler.py`**

**(a) El default retrocompatible, en `Parser.__init__`** (líneas 26-27). El AST nace con `BABY` ya presente; `parsear_niveles()` lo sobrescribe cuando el `.brick` sí declara el bloque:

```python
    # El nivel por defecto existe siempre: si el .brick no declara LEVELS se
    # queda este. Solo es una etiqueta, no lleva comportamiento asociado; los
    # valores por defecto de cada modificador los aporta el juego.
    NIVEL_POR_DEFECTO = 'BABY'

    def __init__(self, tokens):
        self.tokens = tokens
        self.posicion = 0
        self.ast = {"tipo_juego": None,
                    "config": {"start_level": self.NIVEL_POR_DEFECTO},
                    "shapes": {}, "songs": {}, "effects": {}, "events": {},
                    "levels": [{"nombre": self.NIVEL_POR_DEFECTO}]}
```

**(b) El dispatch, en `parse()`** (después de la rama `elif token_actual == 'ON':`):

```python
            elif token_actual == 'LEVELS':
                self.parsear_niveles()
```

**(c) Un consumidor de decimales, junto a `consumir_numero()`** (línea 71):

```python
    def consumir_decimal(self):
        # El lexer entrega 0.15 como un solo token (ver token_regex).
        token = self.consumir()
        if token is None:
            raise Exception("Error de sintaxis: se esperaba un numero pero se llego al final del archivo.")
        try:
            return float(token)
        except ValueError:
            raise Exception("Error de sintaxis: se esperaba un numero pero se encontro '" + token + "'")
```

**(d) `parsear_niveles`, después de `parsear_shape()`** (línea 125):

```python
    MODIFICADORES_NIVEL = {'TICK': 'tick'}

    def parsear_niveles(self):
        # LEVELS: [START: NOMBRE] (LEVEL NOMBRE: mods END)+ END
        # levels es una LISTA y no un diccionario a proposito: el menu se
        # numera por posicion y en Python 2.7 un dict no conserva el orden de
        # declaracion (ver spec 5.3).
        self.consumir('LEVELS')
        self.consumir(':')

        inicio = self.NIVEL_POR_DEFECTO
        if self.ver() == 'START':
            self.consumir('START')
            self.consumir(':')
            inicio = self.consumir()

        niveles = []
        while self.ver() == 'LEVEL':
            niveles.append(self.parsear_nivel())
        if not niveles:
            raise Exception("Error de sintaxis: LEVELS no declara ningun nivel")
        self.consumir('END')

        nombres = [nivel['nombre'] for nivel in niveles]
        if inicio not in nombres:
            raise Exception("Error de sintaxis: el nivel inicial '" + str(inicio) +
                            "' no esta definido")
        # Sin START, arranca el primer nivel declarado (orden del .brick).
        self.ast['levels'] = niveles
        self.ast['config']['start_level'] = inicio

    def parsear_nivel(self):
        self.consumir('LEVEL')
        nombre = self.consumir()
        self.consumir(':')
        if nombre in [n['nombre'] for n in self.ast['levels']]:
            raise Exception("Error de sintaxis: el nivel '" + nombre +
                            "' esta definido dos veces")
        nivel = {'nombre': nombre}
        while self.ver() not in (':', 'END', None):
            clave = self.MODIFICADORES_NIVEL.get(self.ver())
            if clave is None:
                raise Exception("Error de sintaxis: modificador desconocido '" +
                                str(self.ver()) + "' en el nivel '" + nombre + "'")
            self.consumir()
            nivel[clave] = self.consumir_decimal()
        self.consumir('END')
        if 'tick' in nivel and nivel['tick'] <= 0:
            raise Exception("Error de sintaxis: TICK del nivel '" + nombre +
                            "' debe ser mayor que 0")
        return nivel
```

La comprobación de duplicados mira `self.ast['levels']` y no la lista local
`niveles`, para que funcione también cuando el `.brick` declara **dos bloques
`LEVELS`**: el segundo bloque arranca con la lista ya materializada y
`parsear_niveles` la reemplaza al final, pero los nombres repetidos entre
bloques se detectan igual.

- [ ] **Step 4: Run tests to verify they pass**

```
C:\Python27\python.exe -m unittest tests.test_compiler -v
```
Expected: 12 tests, OK (4 del lexer + 8 del parser de niveles).

- [ ] **Step 5: Run the full suite**

```
C:\Python27\python.exe -m unittest discover -s tests -t .
```
Expected: 44 tests, OK. Los 32 de la base más 12 nuevos.

- [ ] **Step 6: Document the grammar in both BNF files**

En `grammars/snake.bnf`, reemplazar la línea 5 y la línea 8 por:

```
<definiciones> ::= <definicion_shape> | <definicion_shape> <definiciones>
<opcional_niveles> ::= "" | <niveles>
```
y añadir el bloque del spec 4.2 más `<extras>` (que el compilador ya soporta
desde la Actividad 3 pero `snake.bnf` nunca documentó) y `<real>`:

```
<definicion_shape> ::= "DEFINE" "SHAPE" <identificador> <extras> ":" <estados> "END"
<extras> ::= "" | "COLOR" <identificador> | "CHANCE" <numero> | "COLOR" <identificador> "CHANCE" <numero>
<real>    ::= <numero> | <numero> "." <numero>

<niveles>          ::= "LEVELS" ":" <elegir_nivel> <definiciones_nivel> "END"
<elegir_nivel>     ::= "" | "START" ":" <identificador>
<definiciones_nivel> ::= <definicion_nivel> | <definicion_nivel> <definiciones_nivel>
<definicion_nivel> ::= "LEVEL" <identificador> ":" <modificadores_nivel> "END"
<modificadores_nivel> ::= <modificador_nivel> | <modificador_nivel> <modificadores_nivel>
<modificador_nivel> ::= "TICK" <real>
```

Actualizar la línea 1 de ambos archivos a:

```
<programa> ::= <tipo_juego> <grid> <definiciones> <opcional_niveles> <eventos>
```

En `grammars/tetris.bnf` agregar el mismo bloque `<niveles>` y `<real>`, y
actualizar su línea 1 igual. Comentar en `snake.bnf` que `<real>` llega al
parser como un solo token.

- [ ] **Step 7: Verify the BNF matches the implementation by hand**

```
C:\Python27\python.exe -c "import compiler; print(compiler.Parser(compiler.lexer(open('games/snake_remake.brick').read())).parse()['levels'])"
```
Expected antes de la Task 5: `[]` o un error claro. Este paso solo confirma que
el archivo `.brick` viejo sigue compilando; el bloque real llega en la Task 5.

- [ ] **Step 8: Commit**

```
git add compiler.py tests/test_compiler.py grammars/snake.bnf grammars/tetris.bnf
git commit -m "compiler: bloque LEVELS con niveles, tick y cinco validaciones

levels es una lista y no un dict: en py2.7 un dict no conserva el orden de
declaracion y el menu se numera por posicion. Sin el bloque, el AST nace con
un nivel BABY vacio (punto D): el nombre se materializa, los valores no, porque
Tetris y Snake tienen ticks por defecto distintos.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: El nivel activo sobrescribe la configuración del juego

El motor lee la configuración del nivel activo y la aplica sobre lo que el juego dejó en `inicializar_estado()`. Aquí **no aparece ningún menú**: es solo el estado y la aplicación. Tetris y Snake no cambian de código.

**Files:**
- Modify: `engine/game.py` (`__init__` líneas 30-33 y 72-77; nuevos `aplicar_nivel`, `config_de_nivel`, `hay_selector_nivel`, `iniciar_partida`; `run` línea 158)
- Modify: `tests/test_game.py`
- Modify: `tests/test_snake.py`
- Modify: `tests/test_retrocompatibilidad.py`

**Interfaces:**
- Consumes: el AST de la Task 2 — `"levels"` es una lista de dicts con `"nombre"`, y `config["start_level"]` es un string.
- Produces, en `Game`:
  - `NIVEL_POR_DEFECTO = 'BABY'` — constante de módulo, etiqueta sin comportamiento. Es la gemela de `compiler.NIVEL_POR_DEFECTO`; no comparten módulo porque el compilador no debe importar de `engine/` (arrastraría Tkinter).
  - `self.niveles` → `list` (vacia si el JSON no trae la clave)
  - `self.nivel_actual` → `str`
  - `self.nivel_config` → `dict` (vacio si el nivel no existe)
  - `self.iniciado` → `bool`
  - `config_de_nivel(nombre) -> dict` — recorre `self.niveles`, devuelve `{}` si no encuentra
  - `aplicar_nivel() -> None` — hoy solo pisa `velocidad_gravedad`
  - `hay_selector_nivel() -> bool` — `len(self.niveles) > 1`
  - `iniciar_partida() -> None` — aplica el nivel, corre `ON_START`, marca `iniciado`

- [ ] **Step 1: Write the failing tests**

Agregar a `tests/test_game.py` una clase nueva. Reutiliza el `JuegoPrueba` y el
helper `datos()` que ya están en ese archivo:

```python
def datos_niveles(niveles, inicio='BABY', eventos=None):
    datos_juego = datos(eventos)
    datos_juego['config']['start_level'] = inicio
    datos_juego['levels'] = niveles
    return datos_juego


NIVELES_TRES = [{'nombre': 'BABY', 'tick': 0.15},
                {'nombre': 'ENTUSIASTA', 'tick': 0.1},
                {'nombre': 'NYAN_CAT', 'tick': 0.06}]


class TestNiveles(unittest.TestCase):

    def test_estado_del_nivel_activo(self):
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'NYAN_CAT'))
        self.assertEqual(juego.nivel_actual, 'NYAN_CAT')
        self.assertEqual(juego.nivel_config['tick'], 0.06)
        # La partida arranco sola: un solo nivel no abre menu
        self.assertTrue(juego.iniciado)
        self.assertFalse(juego.hay_selector_nivel())

    def test_ticket_del_nivel_pisa_el_default_del_juego(self):
        # JuegoPrueba deja velocidad_gravedad = 0.1 (test_game.py:26)
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'NYAN_CAT'))
        self.assertEqual(juego.velocidad_gravedad, 0.06)

    def test_nivel_sin_tick_no_toca_el_default(self):
        # El default lo aporta el juego (Tetris 0.4, Snake 0.15), no el nivel
        juego = JuegoPrueba(datos_niveles([{'nombre': 'BABY'}], 'BABY'))
        self.assertEqual(juego.velocidad_gravedad, 0.1)

    def test_config_de_nivel(self):
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'ENTUSIASTA'))
        self.assertEqual(juego.config_de_nivel('BABY')['tick'], 0.15)
        self.assertEqual(juego.config_de_nivel('NO_EXISTE'), {})

    def test_json_sin_levels_no_revienta(self):
        # games/tetris.json y games/tetris_reborn.json fueron compilados por la
        # version anterior del compilador y no tienen la clave. Tambien
        # tests/test_juegos.py:31 fabrica juegos a mano.
        juego = JuegoPrueba(datos())            # sin 'levels' y sin 'start_level'
        self.assertEqual(juego.niveles, [])
        self.assertEqual(juego.nivel_actual, Game.NIVEL_POR_DEFECTO)
        self.assertEqual(juego.nivel_config, {})
        self.assertEqual(juego.velocidad_gravedad, 0.1)
        self.assertTrue(juego.iniciado)
        self.assertFalse(juego.hay_selector_nivel())

    def test_nivel_inicial_inexistente_cae_a_vacio(self):
        # Un start_level que no esta en la lista no debe romper el arranque
        juego = JuegoPrueba(datos_niveles([{'nombre': 'BABY'}], 'FANTASMA'))
        self.assertEqual(juego.nivel_config, {})
        self.assertEqual(juego.velocidad_gravedad, 0.1)
```

Agregar a `tests/test_snake.py`:

```python
    def test_tick_del_nivel(self):
        # snake.py no cambia: el nivel pisa el 0.15 que Snake deja en
        # inicializar_estado()
        datos = datos_snake()
        datos['config']['start_level'] = 'NYAN_CAT'
        datos['levels'] = [{'nombre': 'BABY'}, {'nombre': 'NYAN_CAT', 'tick': 0.06}]
        self.assertEqual(Snake(datos).velocidad_gravedad, 0.06)

        # Sin declararlo, Snake conserva su 0.15
        self.assertEqual(Snake(datos_snake()).velocidad_gravedad, 0.15)
```

Agregar a `tests/test_retrocompatibilidad.py`, dentro de `TestSnakeClasico`:

```python
    def test_nivel_por_defecto_en_los_clasicos(self):
        # Punto D: snake.brick no declara LEVELS, asi que debe compilar al
        # nivel Baby. El nombre se materializa; los valores no, porque cada
        # juego tiene su tick por defecto.
        for nombre, datos_juego in self.clasicos:
            self.assertEqual(datos_juego['config']['start_level'], 'BABY', nombre)
            self.assertEqual(datos_juego['levels'], [{'nombre': 'BABY'}], nombre)
            self.assertFalse(self.clasicos[0][1]['levels'][0].get('tick'), nombre)

    def test_json_viejo_sin_levels_arranca(self):
        # Un .json compilado por la version anterior del compilador
        # (no tiene 'levels') tiene que seguir arrancando
        for nombre, datos_juego in self.clasicos:
            viejo = {'tipo_juego': 'SNAKE', 'config': {'grid_size': [5, 5]},
                     'shapes': {}, 'events': datos_juego['events']}
            juego = crear_juego(viejo)
            self.assertEqual(juego.nivel_actual, Game.NIVEL_POR_DEFECTO, nombre)
            self.assertEqual(juego.nivel_config, {}, nombre)
```

Esa última prueba necesita `Game` importado en el archivo; agregar `Game` al
`from engine import crear_juego` que ya está en la línea 12.

- [ ] **Step 2: Run tests to verify they fail**

```
C:\Python27\python.exe -m unittest tests.test_game tests.test_snake tests.test_retrocompatibilidad
```
Expected: `AttributeError: 'JuegoPrueba' object has no attribute 'nivel_actual'`.

- [ ] **Step 3: Implement the level state in `engine/game.py`**

**(a) La constante, junto a `COLOR_GRID_FIJA`** (línea 21):

```python
COLOR_GRID_FIJA = '#343434' # Gris oscuro para las celdas fijadas

# Etiqueta del nivel cuando el JSON no trae start_level. Es la gemela de
# compiler.NIVEL_POR_DEFECTO; no comparten modulo porque el compilador no debe
# importar de engine/ (arrastraria Tkinter). Ni esta ni la del compilador
# llevan comportamiento asociado: son solo nombres.
NIVEL_POR_DEFECTO = 'BABY'
```

El test usa `Game.NIVEL_POR_DEFECTO`, así que **déjala también como atributo de
clase**: `NIVEL_POR_DEFECTO = NIVEL_POR_DEFECTO` dentro de la clase, después de
`class Game(object):`.

**(b) El estado, en `__init__`, justo después de leer `config`** (después de la
línea 31):

```python
        # Nivel activo. Todo con .get(): un .json compilado por la version
        # anterior del compilador no trae 'levels' ni 'start_level'.
        self.niveles = self.datos_juego.get('levels') or []
        self.nivel_actual = config.get('start_level') or NIVEL_POR_DEFECTO
        self.nivel_config = self.config_de_nivel(self.nivel_actual)
        self.iniciado = False
```

**(c) Los métodos, después de `avanzar_animacion_borrado()`** (línea 102):

```python
    # NIVELES
    # -------
    #
    # El .brick declara los niveles y el motor obedece lo que encuentra. El
    # motor nunca compara contra un nombre de nivel: si el .brick no declara
    # nada, nivel_config sale vacio y cada juego conserva su default.

    def config_de_nivel(self, nombre):
        for nivel in self.niveles:
            if nivel.get('nombre') == nombre:
                return nivel
        return {}

    def hay_selector_nivel(self):
        # Con un solo nivel no hay nada que elegir: el .brick no declaro
        # LEVELS y el juego arranca directo, como antes.
        return len(self.niveles) > 1

    def aplicar_nivel(self):
        # Cada juego dejo su default en inicializar_estado(); el nivel lo pisa
        # solo si lo declara. Tetris conserva 0.4 y Snake 0.15.
        if 'tick' in self.nivel_config:
            self.velocidad_gravedad = self.nivel_config['tick']

    def iniciar_partida(self):
        self.aplicar_nivel()
        self.ejecutar_evento('ON_START')
        self.iniciado = True
```

**(d) El arranque, reemplazando las líneas 74-77** de `__init__`:

```python
        self._game_over_emitido = False
        self.timer_gravedad = 0
        # Con 2+ niveles hay algo que preguntarle al jugador, asi que la
        # partida no arranca sola: esperar a que run() abra el menu.
        if not self.hay_selector_nivel():
            self.iniciar_partida()
        self.timer_id = None
```

**(e) `run()` (línea 158)**: por ahora sigue igual. El menú llega en la Task 4,
así que este paso **no** lo toca; el cambio de `run` es de la Task 4. Anotarlo
con un comentario para que la Task 4 sepa dónde tocar:

```python
    def run(self):
        self.root.after(50, self.game_loop)
        self.root.mainloop()
```

Dejarlo intacto. En esta Task el juego con 2+ niveles arranca con
`iniciar_partida()` omitido, y `run()` programa el loop igual: el test de
`game.py:88` sigue verde. La Task 4 agrega el menú.

- [ ] **Step 4: Run tests to verify they pass**

```
C:\Python27\python.exe -m unittest tests.test_game tests.test_snake tests.test_retrocompatibilidad
```
Expected: OK, sin errores nuevos.

- [ ] **Step 5: Run the full suite**

```
C:\Python27\python.exe -m unittest discover -s tests -t .
```
Expected: 53 tests, OK.

- [ ] **Step 6: Verify Tetris did not change behavior**

```
C:\Python27\python.exe -c "import compiler, engine; d=compiler.Parser(compiler.lexer(open('games/tetris.brick').read())).parse(); j=engine.crear_juego(d); print(j.velocidad_gravedad, j.nivel_actual, j.nivel_config)"
```
Expected: `0.4 BABY {}`. Tetris conserva su tick: es la prueba de que el
compilador no materializó valores (Review Focus #5).

- [ ] **Step 7: Commit**

```
git add engine/game.py tests/test_game.py tests/test_snake.py tests/test_retrocompatibilidad.py
git commit -m "engine: el nivel activo sobrescribe la configuracion del juego

aplicar_nivel() pisa velocidad_gravedad solo si el nivel declara TICK. Tetris
sigue en 0.4 y Snake en 0.15 sin tocar ninguno de los dos, porque el default
lo aporta el juego y el compilador solo materializa el nombre del nivel.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Menú de selección de nivel

Con 2+ niveles declarados, el juego pregunta antes de arrancar. El menú se dibuja en el canvas existente, sin ventana nueva, y las teclas `1..N` eligen por posición en el orden de declaración.

**Files:**
- Modify: `tests/tk_falso.py` (`Canvas`, línea 53-63)
- Modify: `engine/game.py` (`run` línea 158, `manejar_tecla` línea 206, nuevos `dibujar_menu_nivel` y `elegir_nivel`)
- Modify: `tests/test_game.py`

**Interfaces:**
- Consumes: `hay_selector_nivel()`, `self.niveles`, `self.nivel_config`, `iniciar_partida()` de la Task 3.
- Produces, en `Game`:
  - `dibujar_menu_nivel() -> None` — texto sobre el canvas, con `create_text`
  - `elegir_nivel(indice) -> None` — `indice` es 0-based; fija `nivel_actual`/`nivel_config`, llama `iniciar_partida()` y programa el loop
  - `run()` — con menú abierto dibuja el menú y **no** programa el loop
  - `manejar_tecla(key)` — con el menú abierto solo atiende dígitos `1..N`; cualquier otra tecla se ignora

- [ ] **Step 1: Write the failing tests**

Agregar a `tests/test_game.py`:

```python
class TestMenuNiveles(unittest.TestCase):

    def test_sin_menu_no_hay_textos(self):
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'BABY'))
        juego.run()
        self.assertEqual(juego.root.afters, [(50, juego.game_loop)])
        self.assertEqual(juego.canvas.textos, [])

    def test_menu_dibuja_los_niveles_en_orden(self):
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'NYAN_CAT'))
        self.assertFalse(juego.iniciado)          # la partida no arranca sola
        juego.run()
        self.assertEqual(juego.root.afters, [])   # el loop espera la eleccion
        textos = [t[0] for t in juego.canvas.textos]
        self.assertIn('ELIGE NIVEL', textos)
        # Orden de declaracion del .brick, no orden alfabetico
        i_baby = textos.index([t for t in textos if 'BABY' in t][0])
        i_nyan = textos.index([t for t in textos if 'NYAN_CAT' in t][0])
        self.assertTrue(i_baby < i_nyan)
        # El nivel inicial aparece marcado
        self.assertIn('NYAN_CAT', [t for t in textos if 'inicio' in t][0])

    def test_tecla_elige_nivel_y_arranca(self):
        eventos = {'ON_START': [{'accion': 'SPAWN', 'objeto': 'X', 'params': []}]}
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'BABY', eventos))
        juego.run()
        juego.manejar_input_gui(EventoFalso('3'))   # la tercera tecla = NYAN_CAT
        self.assertEqual(juego.nivel_actual, 'NYAN_CAT')
        self.assertEqual(juego.velocidad_gravedad, 0.06)
        self.assertEqual(juego.acciones, [('SPAWN', 'X')])   # ON_START corrio
        self.assertTrue(juego.iniciado)
        self.assertEqual(juego.root.afters[-1], (50, juego.game_loop))

    def test_con_el_menu_abierto_solo_sirven_los_digitos(self):
        eventos = {'ON_KEY_UP': [{'accion': 'MOVE', 'objeto': 'UP', 'params': []}]}
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'BABY', eventos))
        juego.run()
        juego.manejar_input_gui(EventoFalso('Up'))       # no debe filtrarse
        juego.manejar_input_gui(EventoFalso('7'))        # fuera de rango
        juego.manejar_input_gui(EventoFalso('a'))
        self.assertFalse(juego.iniciado)
        self.assertEqual(juego.acciones, [])
        self.assertEqual(juego.root.afters, [])

    def test_despues_de_elegir_las_flechas_vuelven_a_funcionar(self):
        eventos = {'ON_KEY_UP': [{'accion': 'MOVE', 'objeto': 'UP', 'params': []}]}
        juego = JuegoPrueba(datos_niveles(NIVELES_TRES, 'BABY', eventos))
        juego.run()
        juego.manejar_input_gui(EventoFalso('1'))
        juego.manejar_input_gui(EventoFalso('Up'))
        self.assertEqual(juego.acciones, [('MOVE', 'UP')])

    def test_nivel_sin_tick_no_muestra_tick(self):
        niveles = [{'nombre': 'BABY'}, {'nombre': 'NYAN_CAT', 'tick': 0.06}]
        juego = JuegoPrueba(datos_niveles(niveles, 'BABY'))
        juego.run()
        textos = [t[0] for t in juego.canvas.textos]
        linea_baby = [t for t in textos if 'BABY' in t][0]
        self.assertNotIn('TICK', linea_baby)
        linea_nyan = [t for t in textos if 'NYAN_CAT' in t][0]
        self.assertIn('TICK 0.06', linea_nyan)
```

- [ ] **Step 2: Run tests to verify they fail**

```
C:\Python27\python.exe -m unittest tests.test_game -v
```
Expected: `AttributeError: 'Canvas' object has no attribute 'textos'`.

- [ ] **Step 3: Add `create_text` to the fake canvas in `tests/tk_falso.py`**

En la clase `Canvas` (línea 53), reemplazar `__init__` para añadir la lista y
añadir el método:

```python
class Canvas(WidgetFalso):
    def __init__(self, master=None, **opciones):
        WidgetFalso.__init__(self, master, **opciones)
        self.rectangulos = []
        self.textos = []

    def create_rectangle(self, x1, y1, x2, y2, **opciones):
        self.rectangulos.append(((x1, y1, x2, y2), opciones.get('fill')))

    def create_text(self, x, y, texto='', **opciones):
        # El menu de niveles se dibuja con create_text; se guarda el texto y
        # las opciones para poder afirmar el contenido en los tests.
        self.textos.append((texto, x, y, opciones))

    def delete(self, que):
        if que == "all":
            self.rectangulos = []
            self.textos = []
```

- [ ] **Step 4: Run tests to verify the failure moved**

```
C:\Python27\python.exe -m unittest tests.test_game -v
```
Expected: los tests del menú ahora fallan por comportamiento
(`test_tecla_elige_nivel_y_arranca` falla con
`AssertionError: False is not True` en `juego.iniciado`), no por `AttributeError`.

- [ ] **Step 5: Implement the menu in `engine/game.py`**

**(a) `run()`, reemplazando las dos líneas de la cabecera:**

```python
    def run(self):
        # Con 2+ niveles hay que preguntar antes de jugar: se dibuja el menu y
        # NO se programa el loop. elegir_nivel() lo arranca.
        if not self.iniciado:
            self.dibujar_menu_nivel()
        else:
            self.root.after(50, self.game_loop)
        self.root.mainloop()
```

**(b) `dibujar_menu_nivel()` y `elegir_nivel()`, junto a los métodos de nivel
de la Task 3:**

```python
    def dibujar_menu_nivel(self):
        # Textos sobre el canvas existente: sin ventana ni Toplevel nuevo.
        centro_x = self.ancho_canvas / 2
        y = self.alto_canvas / 2 - self.taman_celda * (len(self.niveles) + 1)
        self.canvas.create_text(centro_x, y, texto='ELIGE NIVEL',
                                fill='#FFFFFF', font=('Consolas', 14, 'bold'))
        for i, nivel in enumerate(self.niveles):
            # La tecla elige por posicion: el orden es el del .brick, que es
            # el orden de la lista (en py2.7 un dict lo perderia).
            linea = '[%d] %s' % (i + 1, nivel.get('nombre'))
            if 'tick' in nivel:
                linea += '    TICK %s' % nivel['tick']
            if nivel.get('nombre') == self.nivel_actual:
                linea += '   <- inicio'
            y += self.taman_celda
            self.canvas.create_text(centro_x, y, texto=linea,
                                    fill='#03a80b', font=('Consolas', 11))

    def elegir_nivel(self, indice):
        self.nivel_actual = self.niveles[indice].get('nombre')
        self.nivel_config = self.niveles[indice]
        self.iniciar_partida()
        self.root.after(50, self.game_loop)
```

`self.alto_canvas / 2` usa división entera: en Python 2 `/` entre dos `int` ya
trunca, y en Python 3 también con operandos `int`. Es lo mismo que ya hace
`runtime.py:49` con `self.ancho // 2`.

**(c) `manejar_tecla()`, reemplazando el cuerpo (línea 206):**

```python
    def manejar_tecla(self, key):
        # Menu abierto: solo los digitos 1..N eligen nivel. El menu se traga el
        # resto, incluidas las flechas, para que mover la Serpiente antes de
        # empezar no dispare ON_KEY_*.
        if not self.iniciado:
            if key.isdigit() and 1 <= int(key) <= len(self.niveles):
                self.elegir_nivel(int(key) - 1)
            return
        # Las flechas disparan ON_KEY_*; cada juego decide la accion.
        if key in ('UP', 'DOWN', 'LEFT', 'RIGHT'):
            self.ejecutar_evento('ON_KEY_' + key)
```

- [ ] **Step 6: Run tests to verify they pass**

```
C:\Python27\python.exe -m unittest tests.test_game -v
```
Expected: todos OK, incluido `test_loop` (línea 88) que no se modificó.

- [ ] **Step 7: Run the full suite**

```
C:\Python27\python.exe -m unittest discover -s tests -t .
```
Expected: 59 tests, OK.

- [ ] **Step 8: Commit**

```
git add engine/game.py tests/tk_falso.py tests/test_game.py
git commit -m "engine: menu de seleccion de nivel con teclas 1..N

Con 2+ niveles declarados la partida no arranca sola: se dibuja el menu en el
canvas y se espera la tecla. El .brick clasico (un solo nivel) no ve cambio:
iniciar_partida() corre igual que antes desde __init__.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: El juego de la sección C, jugable de punta a punta

`snake_remake.brick` declara los tres niveles, la integración lo cubre de punta a punta, y la guía documenta la sintaxis nueva para quien lea el lenguaje.

**Files:**
- Modify: `games/snake_remake.brick`
- Modify: `tests/test_juegos.py`
- Modify: `docs/Guia-BrickScript.txt`

**Interfaces:**
- Consumes: `LEVELS` del parser (Task 2), `hay_selector_nivel()`/`elegir_nivel()` (Task 4).
- Produces: `games/snake_remake.brick` — un `.brick` jugable con tres niveles. Es la variante que `tests/test_retrocompatibilidad.py:15` ya excluye por nombre.

- [ ] **Step 1: Write the failing integration test**

Agregar a `tests/test_juegos.py`:

```python
    def test_snake_remake_abre_menu_y_arranca_al_elegir(self):
        # snake_remake.brick declara tres niveles: la partida no arranca sola y
        # el jugador elige con una tecla. snake.brick (clasico) no hace esto.
        random.seed(1234)
        datos_juego = compilar(os.path.join(CARPETA_RAIZ, 'games', 'snake_remake.brick'))
        self.assertEqual(datos_juego['config']['start_level'], 'NYAN_CAT')
        self.assertEqual([n['nombre'] for n in datos_juego['levels']],
                         ['BABY', 'ENTUSIASTA', 'NYAN_CAT'])

        juego = crear_juego(datos_juego)
        self.assertFalse(juego.iniciado)
        self.assertEqual(juego.serpiente_cuerpo, [])

        juego.manejar_tecla('2')            # ENTUSIASTA
        self.assertTrue(juego.iniciado)
        self.assertEqual(juego.nivel_actual, 'ENTUSIASTA')
        self.assertEqual(juego.velocidad_gravedad, 0.1)
        self.assertEqual(len(juego.serpiente_cuerpo), 1)   # ON_START corrio
        self.assertIsNotNone(juego.posicion_comida)

        # Y la partida corre normal desde ahi
        for _ in range(30):
            juego.manejar_tecla(random.choice(['UP', 'DOWN', 'LEFT', 'RIGHT']))
            juego.game_loop()

    def test_snake_clasico_no_abre_menu(self):
        datos_juego = compilar(os.path.join(CARPETA_RAIZ, 'games', 'snake.brick'))
        self.assertEqual(datos_juego['config']['start_level'], 'BABY')
        juego = crear_juego(datos_juego)
        self.assertTrue(juego.iniciado)      # arranca solo, como siempre
        self.assertEqual(juego.velocidad_gravedad, 0.15)
```

- [ ] **Step 2: Run the test to verify it fails**

```
C:\Python27\python.exe -m unittest tests.test_juegos.TestJuegosReales -v
```
Expected: `KeyError: 'start_level'` — `snake_remake.brick` todavía no declara
`LEVELS`, así que el compilador emite el default y la lista tiene un solo nivel.

- [ ] **Step 3: Write `games/snake_remake.brick`**

Reemplazar el contenido del archivo (dejando `GAME_GRID (18, 18)`, el bloque de
eventos y los comentarios de control exactamente como están):

```
# snake_remake.brick
# Actividad 4 - Seccion C: niveles de dificultad desde la gramática.
# Los tres niveles se diferencian solo en la velocidad del tick. Las frutas
# venenosas, las nubes y la geometría llegan en las secciones B y A.
GAME_TYPE SNAKE

GAME_GRID (18, 18)

# --- Definicion de Elementos ---
DEFINE SHAPE PIXEL:
  STATE 1:
    [1]
END

# --- Niveles ---
# START fija el nivel con el que arranca si el jugador no elige otro con las
# teclas 1..3. El motor no sabe que existe un nivel llamado NYAN_CAT: solo
# obedece lo que este bloque declara.
LEVELS:
  START: NYAN_CAT
  LEVEL BABY:
    TICK 0.15
  END
  LEVEL ENTUSIASTA:
    TICK 0.10
  END
  LEVEL NYAN_CAT:
    TICK 0.06
  END
END

# --- Logica y Reglas ---
ON START:
  SPAWN PLAYER AT (9, 9)
  SPAWN FOOD AT RANDOM
END

# ON_TICK es un evento que se ejecuta en cada ciclo del juego
ON TICK:
  MOVE PLAYER FORWARD
END

# Evento para cuando la serpiente come
ON EAT_FOOD:
  INCREASE_SCORE 10
  GROW PLAYER 1
  SPAWN FOOD AT RANDOM
END

# Eventos de fin de juego
ON COLLISION_WALL:
  GAME_OVER
END
ON COLLISION_SELF:
  GAME_OVER
END

# --- Controles ---
ON KEY_UP:
  SET_DIRECTION UP
END
ON KEY_DOWN:
  SET_DIRECTION DOWN
END
ON KEY_LEFT:
  SET_DIRECTION LEFT
END
ON KEY_RIGHT:
  SET_DIRECTION RIGHT
END
```

- [ ] **Step 4: Run the test to verify it passes**

```
C:\Python27\python.exe -m unittest tests.test_juegos -v
```
Expected: todos OK.

- [ ] **Step 5: Run the full suite**

```
C:\Python27\python.exe -m unittest discover -s tests -t .
```
Expected: 61 tests, OK.

- [ ] **Step 6: Verify the real compile-and-run path end to end**

```
C:\Python27\python.exe compiler.py games/snake_remake.brick
C:\Python27\python.exe -c "import json; d=json.load(open('games/snake_remake.json')); print(d['config']['start_level'], d['levels'])"
```
Expected: `Compilacion exitosa!` y luego
`NYAN_CAT [{'nombre': 'BABY', 'tick': 0.15}, {'nombre': 'ENTUSIASTA', 'tick': 0.1}, {'nombre': 'NYAN_CAT', 'tick': 0.06}]`.

Y lo mismo con el clásico, para ver que no cambió:

```
C:\Python27\python.exe compiler.py games/snake.brick
C:\Python27\python.exe -c "import json; d=json.load(open('games/snake.json')); print(d['config']['start_level'], d['levels'])"
```
Expected: `BABY [{'nombre': 'BABY'}]` — sin `tick`, porque el default lo
aporta el juego (Review Focus #1 y #5).

- [ ] **Step 7: Document LEVELS in `docs/Guia-BrickScript.txt`**

Agregar una sección siguiendo el formato de las existentes (la de
`DEFINE SHAPE` está alrededor de la línea 52). Contenido:

```
 * LEVELS: ... END
     Bloque opcional que declara los niveles de dificultad del juego.
     Cada nivel lleva sus modificadores; START indica con cual arranca.

     Ej: LEVELS:
           START: NYAN_CAT
           LEVEL BABY:
             TICK 0.15
           END
           LEVEL NYAN_CAT:
             TICK 0.06
           END
         END

     - TICK <real>: segundos entre cada tick del juego. Si un nivel no lo
       declara, el juego conserva su velocidad por defecto (Snake 0.15,
       Tetris 0.4).
     - START: <nombre>: nivel con el que arranca la partida. Sin START se
       usa el primer nivel declarado.
     - Si el archivo no declara LEVELS, el motor asume el nivel BABY con la
       configuracion por defecto del juego. Por eso los .brick clasicos
       siguen funcionando sin cambios.

     Cuando el archivo declara dos o mas niveles, el juego muestra un menu
     antes de empezar y el jugador elige con las teclas 1, 2, 3... en el
     orden en que estan declarados.
```

- [ ] **Step 8: Verify `games/*.json` is still ignored and nothing foreign slipped in**

```
git status --short
```
Expected: solo los archivos de esta tarea. `games/*.json` no debe aparecer
(está en `.gitignore`) y **`games/tetris_reborn.brick` debe seguir apareciendo
como modificado y sin stagear** — es trabajo de otro, no se toca.

- [ ] **Step 9: Commit**

```
git add games/snake_remake.brick tests/test_juegos.py docs/Guia-BrickScript.txt
git commit -m "snake_remake: declara tres niveles de dificultad

Agrega el bloque LEVELS al juego. START fija NYAN_CAT como nivel inicial y el
menu deja elegir con las teclas 1..3. Los tres niveles se diferencian solo en
el tick; las features de las secciones A y B llegan despues.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage.** Secciones del spec y quién las implementa:

| Sección del spec | Tarea |
|---|---|
| 3. Restricciones del lexer (verificadas) | Task 1 |
| 4.1 Sintaxis, 4.2 BNF | Task 2 |
| 4.3 AST, 5.3 lista y no diccionario | Task 2 (`test_bloque_niveles`) |
| 5.1 Lexer, 5.2 Parseo, 5.3 AST, 5.4 default Baby, 5.5 validaciones | Task 2 |
| 6.1 Un solo camino, 6.2 Estado, 6.4 Lectura defensiva | Task 3 |
| 6.3 Flujo de arranque | Task 3 + Task 4 |
| 6.5 El menú | Task 4 |
| 7. snake.brick / snake_remake.brick | Task 5 |
| 8. Tests | Task 1-5 |
| 9. Fuera de alcance | No implementado, a propósito |
| 10. Orden de commits, restricción de versión | Global Constraints + los 5 commits |
| 11. Cómo continúa A y B | Fuera de este plan |

Sin huecos.

**2. Step scan.** Cada paso deja una sola cosa razonable que escribir. El
Step 3 de la Task 3 trae el cuerpo de los métodos porque las firmas y los tests
no determinan los comentarios ni el orden exacto; los pasos de BNF (Task 2,
Step 6) traen el texto porque es copia exacta. No hay pasos tipo "manejar
casos borde".

**3. Type consistency.** `niveles` es lista en Task 2 (compilador) y en Task 3
(motor), coherente con el cambio del spec 5.3. `config_de_nivel` se nombra igual
en el Interfaces y en el código. `NIVEL_POR_DEFECTO` existe como constante de
módulo **y** como atributo de clase en `Game` porque el test lo referencia como
`Game.NIVEL_POR_DEFECTO`. `iniciar_partida` se llama desde `__init__` (Task 3) y
desde `elegir_nivel` (Task 4). `hay_selector_nivel` se usa en `__init__` y en
`run`.

Todos los nombres que cruzan tareas son identicos aqui, en el bloque de
Interfaces y en el codigo de cada tarea: `niveles`, `nivel_actual`,
`nivel_config`, `iniciado`, `config_de_nivel`, `hay_selector_nivel`,
`aplicar_nivel`, `iniciar_partida`, `dibujar_menu_nivel`, `elegir_nivel`.

**4. Review Focus.** Cada línea tiene su prueba:

1. `test_sin_bloque_niveles_queda_baby` (T2), `test_nivel_por_defecto_en_los_clasicos` (T3), `test_snake_clasico_no_abre_menu` (T5)
2. `test_json_sin_levels_no_revienta` (T3), `test_json_viejo_sin_levels_arranca` (T3)
3. `test_menu_dibuja_los_niveles_en_orden` (T4), `test_snake_remake_abre_menu_y_arranca_al_elegir` (T5)
4. `test_con_el_menu_abierto_solo_sirven_los_digitos` (T4), `test_snake_remake_abre_menu_y_arranca_al_elegir` (T5)
5. `test_nivel_sin_tick_no_toca_el_default` (T3), `test_config_de_nivel` (T3), Step 6 de T3

**5. Proportion.** El plan tiene ~5 tareas y 48 pasos; el spec tiene 12
secciones. Los bloques de código son de test (que sí hay que escribir tal cual)
y de las gramáticas (copia exacta). Los cuerpos de método vienen con su
firma y su comentario. La proporción es razonable para TDD.