# Brick Tanks (Actividad 5A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar el juego `GAME_TYPE TANKS` jugable completo (jugador único con HP, enemigos con color/HP/velocidad, balas, muros de nivel y martillo curativo) sobre la gramática y el motor que ya existen, sin romper Tetris ni Snake.

**Architecture:** Se extiende el parser compartido (`compiler.py`) con atributos de forma (`TYPE`, `HP`, `DAMAGE`, `SPEED`, `FIRE_RATE`, `HEAL`, `OWNER`), el modificador de nivel `WALLS` y una validación semántica que solo corre para `GAME_TYPE TANKS`. El motor nuevo es `engine/tanks.py`, una clase `Tanks(Game)` que guarda jugador, enemigos, balas y martillo en atributos propios, usa `self.grid` como capa de muros y se engancha en `ejecutar_evento('ON_TICK')` para avanzar el mundo antes de correr el `ON TICK` del `.brick`. El `.brick` solo declara contenidos (formas, valores, eventos); el motor nunca compara nombres de forma ni de nivel.

**Tech Stack:** Python 2.7 (sin f-strings, sin dicts ordenados, solo stdlib), Tkinter, `unittest`, `random`.

**Spec:** `docs/superpowers/specs/2026-11-03-brick-tanks-design.md`

## Global Constraints

- Intérprete de referencia: `C:\Python27\python.exe`. Nada de f-strings, anotaciones de tipo, `dict` ordenados ni `items()` como vista.
- Suite de referencia (verificada el 2026-11-03 sobre `6eee213`): `cmd /c "C:\Python27\python.exe -u -m unittest discover -s tests -t . -v"` → **149 tests, OK**. Los 2 fallos que mencionan `AGENTS.md` y el spec ya se corrigieron en `7ba6ca0`: la entrega termina con la suite completa en verde, no con fallos "preexistentes".
- Retrocompatibilidad dura: **no** se editan `games/snake.brick`, `games/tetris.brick`, `tests/test_retrocompatibilidad.py` ni el md5 dorado de `TEMA_NYAN` (`b5c00a9d824a221678215ea6ca64c173`). `games/tanks.brick` declara `GAME_TYPE TANKS`, así que el filtro `('reborn','remake')` y `juegos_clasicos('TETRIS'/'SNAKE')` lo ignoran.
- El lexer solo tokeniza MAYÚSCULAS (`compiler.py:30-35`) y `#` abre comentario (`compiler.py:38`). Todo identificador del `.brick` va en `A-Z_0-9`; la paleta vive en `engine/utilidades.py`.
- Defaults del motor, nunca guardados en el AST: `HP` jugador **3**, enemigo **1**; `DAMAGE` **1**; `SPEED` **2**; `FIRE_RATE` **3**; `HEAL` **1**; `COLOR` `CYAN`; `CHANCE` 10; `GEOMETRY` `RECT`; `TICK` por defecto **0.12**; cooldown de disparo **0.3 s**; martillo dibujado a 1 celda.
- La validación semántica corre **solo** si `tipo_juego == 'TANKS'`; Snake y Tetris no pasan por ella.
- Colores nuevos: `GRAY = "#808080"` en `engine/utilidades.py`.
- Sin ventanas nuevas: todo se dibuja sobre `self.canvas` y el panel `self.marco_score` que ya crea `Game`.
- Determinismo: nada de `while True` esperando azar. Todo sorteo es `random.randint` sobre una lista de candidatas con *fallback* determinista a `candidatas[0]` (patrón de `Snake._obtener_posicion_libre`).
- Orden de formas: en Python 2.7 un `dict` no conserva el orden de declaración. Compilador y motor iteran `sorted(shapes.items())`; ese es el orden estable que reemplaza "primera declarada" (con una sola forma `PICKUP` es indistinto).
- Commits frecuentes, uno por tarea, con el hook pre-commit activo (corre la suite).

## Review Focus

1. **`SPAWN PLAYER AT (x, y)` en el borde del tablero** (matriz 3×3 en `(7,7)` sobre 8×8): el spec dice que un spawn que no cabe "se ignora", pero un jugador inexistente deja la partida muda. Se recorta el ancla al tablero y el jugador debe quedar dentro y controlable. → test en Task 3.
2. **Enemigo en un callejón sin salida** (muros en las cuatro direcciones): gira cuatro veces y se queda quieto ese tick; no cuelga ni atraviesa muros. → test en Task 4.
3. **Martillo en un tablero sin celdas libres**: no debe entrar en bucle de reaparición; se cura una sola vez y el martillo queda en `None`. → test en Task 4.
4. **Disparo con el cañón apuntando fuera del tablero**: no crea bala, no revienta y el cooldown igual se aplica (si no, se podría disparar en ráfaga contra el borde). → test en Task 3.
5. **Nivel con `WALLS` mayor que las celdas del tablero**: los muros se cortan en el total de celdas y la partida arranca igual. → test en Task 4.

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `compiler.py` | Tabla `ATRIBUTOS_SHAPE`, parseo de atributos en `parsear_shape`, `WALLS` en `MODIFICADORES_NIVEL`, `validar_tanques()` al final de `parse()` |
| `grammars/tanks.bnf` | Gramática de la Actividad 5A (misma producción compartida + atributos + `WALLS`) |
| `games/tanks.brick` | Contenido del juego: formas, tema, tres efectos, dos niveles, eventos |
| `engine/tanks.py` | Clase `Tanks(Game)`: estado, `ON_TICK` (balas → enemigos → disparo), acciones `SPAWN`/`MOVE`/`SHOOT`/`HEAL`, muros, martillo, dibujo |
| `engine/__init__.py` | Registro `'TANKS': Tanks` |
| `engine/game.py` | `manejar_tecla`: `SPACE → ON_KEY_SHOOT` |
| `engine/utilidades.py` | `GRAY` |
| `tests/test_compiler.py` | Atributos, `WALLS`, validación TANKS |
| `tests/test_game.py` | Mapeo de la tecla Espacio |
| `tests/test_juegos.py` | `crear_juego` registra TANKS |
| `tests/test_tanks.py` | `.brick` real + motor completo (10 puntos del spec §7) |
| `docs/Guia-BrickScript.txt` | Sección TANKS |
| `docs/cambios/tanks_changes.txt` | Registro de cambios + `APORTES POR INTEGRANTE` |
| `docs/README.md` | Checkbox Actividad 5 + enlace al changelog |
| `.github/workflows/tests.yml` | Grupo `tests.test_tanks` en la matriz (el encabezado del archivo lo exige) |

---

### Task 1: Compilador — atributos de forma, `WALLS` y validación TANKS

**Files:**
- Modify: `compiler.py` (`parsear_shape` ~línea 162, `MODIFICADORES_NIVEL` ~línea 211, `parse()` ~línea 73)
- Test: `tests/test_compiler.py` (agregar al final, antes de `if __name__`)

**Interfaces:**
- Consumes: nada.
- Produces: `Parser.ATRIBUTOS_SHAPE`, `Parser.TIPOS_ENTIDAD`, `Parser.BANDOS`, `Parser.validar_tanques()`; en el AST, `ast['shapes'][NOMBRE]` gana las claves `type`, `hp`, `damage`, `speed`, `fire_rate`, `heal`, `owner` solo cuando están presentes, y `ast['levels'][i]` gana `walls` (int).

- [ ] **Step 1: Escribir los tests que fallan**

Añadir al final de `tests/test_compiler.py` (antes del `if __name__`). El helper `compilar(fuente)` ya existe en el archivo.

```python
def fuente_tanks(jugador='DEFINE SHAPE JUGADOR TYPE PLAYER HP 3 COLOR GREEN: STATE 1: [1] END',
                 enemigo='DEFINE SHAPE ENEMIGO TYPE ENEMY HP 1 SPEED 2 FIRE_RATE 3 COLOR RED: STATE 1: [1] END',
                 balas=('DEFINE SHAPE BALA_JUGADOR TYPE BULLET OWNER PLAYER DAMAGE 1: STATE 1: [1] END\n'
                        'DEFINE SHAPE BALA_ENEMIGA TYPE: BULLET OWNER: ENEMY DAMAGE 1: STATE 1: [1] END'),
                 extra=''):
    return ('GAME_TYPE TANKS\nGAME_GRID (8, 8)\n' + jugador + '\n' + enemigo + '\n' +
            balas + '\n' + extra)


class TestAtributosShapeTanks(unittest.TestCase):

    def test_type_hp_y_color(self):
        jugador = compilar(fuente_tanks())['shapes']['JUGADOR']
        self.assertEqual(jugador['type'], 'PLAYER')
        self.assertEqual(jugador['hp'], 3)
        self.assertEqual(jugador['color'], 'GREEN')

    def test_type_y_owner_admiten_dos_puntos(self):
        bala = compilar(fuente_tanks())['shapes']['BALA_ENEMIGA']
        self.assertEqual(bala['type'], 'BULLET')
        self.assertEqual(bala['owner'], 'ENEMY')
        self.assertEqual(bala['damage'], 1)

    def test_atributos_numericos_del_enemigo(self):
        enemigo = compilar(fuente_tanks())['shapes']['ENEMIGO']
        self.assertEqual((enemigo['hp'], enemigo['speed'], enemigo['fire_rate']), (1, 2, 3))

    def test_heal_del_pickup(self):
        ast = compilar(fuente_tanks(extra='DEFINE SHAPE MARTILLO TYPE PICKUP HEAL 1: STATE 1: [1] END'))
        self.assertEqual(ast['shapes']['MARTILLO']['heal'], 1)

    def test_los_atributos_ausentes_no_se_guardan(self):
        muro = compilar(fuente_tanks(extra='DEFINE SHAPE MURO TYPE WALL: STATE 1: [1] END'))['shapes']['MURO']
        self.assertEqual(muro['type'], 'WALL')
        for clave in ('hp', 'damage', 'speed', 'fire_rate', 'heal', 'owner'):
            self.assertNotIn(clave, muro)

    def test_walls_es_un_modificador_de_nivel(self):
        ast = compilar(fuente_tanks(extra='LEVELS:\n  START: PATRULLA\n'
                                          '  LEVEL PATRULLA:\n    TICK 0.12\n    WALLS 6\n  END\nEND\n'))
        self.assertEqual(ast['levels'][0]['walls'], 6)
        self.assertEqual(ast['levels'][0]['tick'], 0.12)


class TestValidacionTanks(unittest.TestCase):

    def test_otro_juego_no_pasa_por_la_validacion(self):
        # Snake no declara TYPE PLAYER y aun asi compila: la validacion es solo TANKS.
        ast = compilar('GAME_TYPE SNAKE\nGAME_GRID (5, 5)\nLEVELS:\n  LEVEL BABY:\n    TICK 0.15\n  END\nEND\n')
        self.assertEqual(ast['tipo_juego'], 'SNAKE')

    def test_errores_de_validacion(self):
        casos = [
            (fuente_tanks(jugador=''),
             'exactamente una forma con TYPE PLAYER (hay 0)'),
            (fuente_tanks(jugador='DEFINE SHAPE JUGADOR TYPE PLAYER: STATE 1: [1] END\n'
                                  'DEFINE SHAPE OTRO TYPE PLAYER: STATE 1: [1] END'),
             'exactamente una forma con TYPE PLAYER (hay 2)'),
            (fuente_tanks(enemigo=''),
             'al menos una forma con TYPE ENEMY'),
            (fuente_tanks(balas='DEFINE SHAPE BALA_ENEMIGA TYPE BULLET OWNER ENEMY: STATE 1: [1] END'),
             'una bala con TYPE BULLET OWNER PLAYER'),
            (fuente_tanks(balas='DEFINE SHAPE BALA_JUGADOR TYPE BULLET OWNER PLAYER: STATE 1: [1] END'),
             'una bala con TYPE BULLET OWNER ENEMY'),
            (fuente_tanks(extra='DEFINE SHAPE SINDUENO TYPE BULLET: STATE 1: [1] END'),
             "la bala 'SINDUENO' necesita OWNER PLAYER o OWNER ENEMY"),
            (fuente_tanks(extra='DEFINE SHAPE PAREDON TYPE WALL: STATE 1: [1, 1, 1] [1, 0, 0] END'),
             "la forma 'PAREDON' con TYPE WALL necesita una matriz cuadrada"),
            (fuente_tanks(extra='DEFINE SHAPE RARO TYPE WALL: STATE 1: [1, 1] [1] END'),
             "la forma 'RARO' tiene filas de distinto ancho"),
            (fuente_tanks(extra='DEFINE SHAPE VACIO TYPE WALL: STATE 1: END'),
             "la forma 'VACIO' tiene la matriz sin celdas encendidas"),
            (fuente_tanks(extra='DEFINE SHAPE APAGADO TYPE WALL: STATE 1: [0, 0] [0, 0] END'),
             "la forma 'APAGADO' tiene la matriz sin celdas encendidas"),
            (fuente_tanks(extra='DEFINE SHAPE DURO TYPE ENEMY HP 0: STATE 1: [1] END'),
             "el atributo HP de la forma 'DURO' debe ser mayor o igual a 1"),
            (fuente_tanks(extra='DEFINE SHAPE X TYPE NAVE: STATE 1: [1] END'),
             "TYPE 'NAVE' no valido"),
            (fuente_tanks(extra='DEFINE SHAPE Y TYPE BULLET OWNER NADIE: STATE 1: [1] END'),
             "OWNER 'NADIE' no valido"),
        ]
        for fuente, esperado in casos:
            with self.assertRaises(Exception) as contexto:
                compilar(fuente)
            self.assertIn(esperado, str(contexto.exception))
```

- [ ] **Step 2: Correr los tests y verlos fallar**

Run: `cmd /c "C:\Python27\python.exe -u -m unittest -v tests.test_compiler.TestAtributosShapeTanks tests.test_compiler.TestValidacionTanks"`
Expected: FAIL — `KeyError: 'type'` en el primero y `Exception` no lanzada en la validación.

- [ ] **Step 3: Implementar la tabla de atributos y el parseo**

En `compiler.py`, dentro de `class Parser` (junto a `MODIFICADORES_NIVEL`), agregar:

```python
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
```

Reemplazar el cuerpo de `parsear_shape` (desde `nombre_shape = self.consumir()` hasta `self.ast['shapes'][nombre_shape] = {...}`) por:

```python
    def parsear_shape(self):
            self.consumir('DEFINE')
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
            self.ast['shapes'][nombre_shape] = datos
```

Agregar `WALLS` a `MODIFICADORES_NIVEL`:

```python
    MODIFICADORES_NIVEL = {... existentes ...,
                            'WALLS': ('walls', 'numero')}
```

- [ ] **Step 4: Implementar `validar_tanques()` y llamarla desde `parse()`**

En `parse()`, después de `self.validar_musicas_de_niveles()`:

```python
        if self.ast['tipo_juego'] == 'TANKS':
            self.validar_tanques()
        return self.ast
```

Y el método (después de `validar_musicas_de_niveles`):

```python
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
```

- [ ] **Step 5: Correr los tests hasta verde**

Run: `cmd /c "C:\Python27\python.exe -u -m unittest -v tests.test_compiler"`
Expected: OK, con los tests previos intactos.

- [ ] **Step 6: Commit**

```bash
git add compiler.py tests/test_compiler.py
git commit -m "compilador: atributos de forma, WALLS y validacion semantica de TANKS"
```

---

### Task 2: Gramática `tanks.bnf` y el `.brick` jugable

**Files:**
- Create: `grammars/tanks.bnf`, `games/tanks.brick`, `tests/test_tanks.py`

**Interfaces:**
- Consumes: `TYPE`/`HP`/`DAMAGE`/`SPEED`/`FIRE_RATE`/`HEAL`/`OWNER` y `WALLS` de Task 1.
- Produces: `games/tanks.brick` compilable con `tipo_juego == 'TANKS'`, `grid_size == [15, 15]`, formas `JUGADOR` (3×3, `hp 3`), `ENEMIGO_BASICO`/`ENEMIGO_RAPIDO`/`ENEMIGO_DURO` (3×3), `BALA_JUGADOR`, `BALA_ENEMIGA`, `MURO`, `MARTILLO`; niveles `['PATRULLA', 'ASEDIO']` con `walls` 6 y 10; `songs` con `TANK_TEMA`; `effects` con `DISPARO`, `IMPACTO`, `MORIR`.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_tanks.py` con el encabezado y la primera clase (el resto de la clase se agrega en Task 3):

```python
# -*- coding: utf-8 -*-
# Tests del juego Tanks (GAME_TYPE TANKS): el .brick real y el motor
# (jugador, balas, enemigos, muros y martillo).

import os
import unittest

import compiler

CARPETA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestBrickTanks(unittest.TestCase):

    def compilar(self):
        with open(os.path.join(CARPETA_RAIZ, 'games', 'tanks.brick')) as f:
            return compiler.Parser(compiler.lexer(f.read())).parse()

    def test_declara_el_juego_y_las_formas(self):
        datos = self.compilar()
        self.assertEqual(datos['tipo_juego'], 'TANKS')
        self.assertEqual(datos['config']['grid_size'], [15, 15])
        self.assertEqual(datos['shapes']['JUGADOR']['type'], 'PLAYER')
        self.assertEqual(datos['shapes']['JUGADOR']['hp'], 3)
        self.assertEqual(datos['shapes']['ENEMIGO_RAPIDO']['speed'], 4)
        self.assertEqual(datos['shapes']['BALA_JUGADOR']['owner'], 'PLAYER')
        self.assertEqual(datos['shapes']['BALA_ENEMIGA']['owner'], 'ENEMY')
        self.assertEqual(datos['shapes']['MURO']['type'], 'WALL')
        self.assertEqual(datos['shapes']['MARTILLO']['heal'], 1)

    def test_niveles_y_muros(self):
        datos = self.compilar()
        self.assertEqual([n['nombre'] for n in datos['levels']], ['PATRULLA', 'ASEDIO'])
        self.assertEqual(datos['config']['start_level'], 'PATRULLA')
        self.assertEqual([n.get('walls') for n in datos['levels']], [6, 10])

    def test_audio_y_eventos(self):
        datos = self.compilar()
        self.assertIn('TANK_TEMA', datos['songs'])
        for efecto in ('DISPARO', 'IMPACTO', 'MORIR'):
            self.assertIn(efecto, datos['effects'])
        for evento in ('ON_START', 'ON_KEY_SHOOT', 'ON_ENEMY_DEFEATED',
                       'ON_EAT_HAMMER', 'ON_BULLET_HIT_WALL', 'ON_GAME_OVER'):
            self.assertIn(evento, datos['events'])
```

- [ ] **Step 2: Correrlo y verlo fallar**

Run: `cmd /c "C:\Python27\python.exe -u -m unittest -v tests.test_tanks"`
Expected: ERROR `IOError: ... games\tanks.brick` (el archivo todavía no existe).

- [ ] **Step 3: Escribir `grammars/tanks.bnf`**

Copiar las producciones del spec §4.1 completas (programa, grid, definiciones, shape con `<atributos>`, niveles con `WALLS`, eventos y acciones) más el pie `<identificador>/<numero>/<real>/<letra>/<digito>` que usa `grammars/tetris.bnf`, y una nota al final:

```
* --- Diferencias con tetris.bnf / snake.bnf ---
*
* - DEFINE SHAPE acepta los atributos de la Actividad 5: TYPE, HP, DAMAGE,
*   SPEED, FIRE_RATE, HEAL y OWNER, ademas de COLOR, CHANCE y GEOMETRY.
* - <tipo_entidad> es PLAYER | ENEMY | BULLET | WALL | PICKUP | BOSS y
*   <bando> es PLAYER | ENEMY. TYPE y OWNER admiten ":" opcional.
* - LEVELS agrega el modificador WALLS <numero> (celdas de muro del nivel).
* - ON TARGET_SCORE se parsea desde ya, pero nada lo emite: es de la 5B.
* - La validacion de estas reglas (una sola forma PLAYER, al menos una ENEMY,
*   bala de cada bando, matrices cuadradas) vive en el compilador y solo se
*   aplica a GAME_TYPE TANKS.
```

- [ ] **Step 4: Escribir `games/tanks.brick`**

Contenido exacto (los comentarios con `#` son válidos; todo identificador en mayúsculas):

```
GAME_TYPE TANKS

GAME_GRID (15, 15)

# --- Tanque del jugador: verde, 3 de resistencia ---
DEFINE SHAPE JUGADOR TYPE PLAYER HP 3 COLOR GREEN:
  STATE 1:
    [0, 1, 0]
    [1, 1, 1]
    [0, 1, 0]
END

# --- Enemigos: color, vida, celdas por segundo y cadencia de disparo ---
DEFINE SHAPE ENEMIGO_BASICO TYPE ENEMY HP 1 SPEED 2 FIRE_RATE 3 COLOR RED:
  STATE 1: [0,1,0] [1,1,1] [0,1,0] END

DEFINE SHAPE ENEMIGO_RAPIDO TYPE ENEMY HP 1 SPEED 4 FIRE_RATE 2 COLOR ORANGE:
  STATE 1: [0,1,0] [1,1,1] [0,1,0] END

DEFINE SHAPE ENEMIGO_DURO TYPE ENEMY HP 2 SPEED 1 FIRE_RATE 4 COLOR PURPLE:
  STATE 1: [0,1,0] [1,1,1] [0,1,0] END

# --- Municion: el dano viaja en la bala, no en el tanque ---
DEFINE SHAPE BALA_JUGADOR TYPE BULLET OWNER PLAYER DAMAGE 1 COLOR CYAN:
  STATE 1: [1] END
DEFINE SHAPE BALA_ENEMIGA TYPE BULLET OWNER ENEMY DAMAGE 1 COLOR YELLOW:
  STATE 1: [1] END

DEFINE SHAPE MURO     TYPE WALL   COLOR GRAY:   STATE 1: [1] END
DEFINE SHAPE MARTILLO TYPE PICKUP HEAL 1 COLOR YELLOW: STATE 1: [1] END

# --- Musica y efectos (misma tecnica que Tetris y Snake) ---
DEFINE SONG TANK_TEMA WAVE SQUARE:
  NOTE C4 300
  NOTE C4 150
  NOTE G3 150
  NOTE A#3 300
  NOTE A#3 150
  NOTE G3 150
  NOTE A3 300
  NOTE A3 150
  NOTE F3 150
  NOTE G3 600
  NOTE C4 300
  NOTE C4 150
  NOTE D#4 150
  NOTE D4 300
  NOTE C4 150
  NOTE A#3 150
  NOTE G3 600
END

DEFINE EFFECT DISPARO:
  NOTE E5 60
  NOTE B4 60
END

DEFINE EFFECT IMPACTO:
  NOTE G3 100
  NOTE C3 150
END

DEFINE EFFECT MORIR:
  NOTE E4 150
  NOTE C4 150
  NOTE A3 400
END

LEVELS:
  START: PATRULLA
  LEVEL PATRULLA:
    TICK 0.12
    WALLS 6
  END
  LEVEL ASEDIO:
    TICK 0.08
    WALLS 10
  END
END

ON START:
  SPAWN PLAYER AT (6, 12)
  SPAWN ENEMIGO_BASICO AT (2, 2)
  SPAWN ENEMIGO_RAPIDO AT (12, 2)
  SPAWN MARTILLO AT RANDOM
  PLAY_MUSIC TANK_TEMA
END

ON KEY_UP:    MOVE PLAYER UP    END
ON KEY_DOWN:  MOVE PLAYER DOWN  END
ON KEY_LEFT:  MOVE PLAYER LEFT  END
ON KEY_RIGHT: MOVE PLAYER RIGHT END
ON KEY_SHOOT:
  SHOOT PLAYER
  PLAY_EFFECT DISPARO
END

ON ENEMY_DEFEATED:
  INCREASE_SCORE 100
  SPAWN ENEMIGO_BASICO AT RANDOM
  PLAY_EFFECT IMPACTO
END

ON BULLET_HIT_WALL:
  PLAY_EFFECT IMPACTO
END

ON PLAYER_HIT:
  PLAY_EFFECT IMPACTO
END

ON EAT_HAMMER:
  HEAL PLAYER
  SPAWN MARTILLO AT RANDOM
END

ON GAME_OVER:
  STOP_MUSIC
  PLAY_EFFECT MORIR
END
```

Nota: `(6, 12)` con una matriz de 3 filas cae en las filas 12–14 de un tablero de 15, así que el jugador cabe entero. No mover ese spawn a la fila 14.

- [ ] **Step 5: Correr los tests hasta verde**

Run: `cmd /c "C:\Python27\python.exe -u -m unittest -v tests.test_tanks tests.test_compiler"`
Expected: OK (esta tarea no toca el motor: `tests.test_tanks` solo compila el `.brick`). Para validar el `.brick` sin el motor:

Run: `cmd /c "C:\Python27\python.exe .\compiler.py games\tanks.brick"`
Expected: `Compilacion exitosa! Archivo de juego creado en games/tanks.json` (el `.json` está en `.gitignore`: no se versiona).

- [ ] **Step 6: Commit**

```bash
git add grammars/tanks.bnf games/tanks.brick tests/test_tanks.py
git commit -m "tanks: gramatica, .brick jugable y test del contenido"
```

---

### Task 3: Motor I — jugador, teclas, disparo, balas y dibujo

**Files:**
- Create: `engine/tanks.py`
- Modify: `engine/__init__.py`, `engine/game.py` (`manejar_tecla` ~línea 365), `engine/utilidades.py`
- Test: `tests/test_tanks.py` (clase `TestTanks`), `tests/test_game.py` (`test_eventos_y_teclas`), `tests/test_juegos.py` (`test_crear_juego_por_tipo`)

**Interfaces:**
- Consumes: formas con `type`/`hp`/`damage`/`owner`/`heal`/`speed`/`fire_rate` del AST; `env['events']` con acciones ya parseadas.
- Produces (lo usa Task 4): `Tanks.jugador` (`dict` con `nombre, x, y, hp, max_hp, orientacion, cooldown`), `Tanks.enemigos` (lista), `Tanks.balas` (lista), `Tanks.martillo` (tupla o `None`), `Tanks.avanzar_mundo(delta)`, `Tanks.color_celda_grid(x, y)`, y los helpers `_forma(nombre)`, `_formas_de_tipo(tipo, bando=None)`, `_matriz(datos)`, `_rotar_matriz(matriz, direccion)`, `_celdas(matriz, x, y)`, `_dentro(celda)`, `_puede_ocupar(matriz, x, y, ignorar_muros=False, sin_jugador=False, sin_enemigo=None)`, `_borrar_muros(matriz, x, y)`, `_celda_frente(matriz, x, y, direccion)`, `_bala_de_bando(bando)`, `_celdas_jugador()`, `_jugador_en(x, y)`, `_enemigo_en(x, y)`, `_spawn_forma(nombre, accion)`, `_ancla_libre(matriz)`.

- [ ] **Step 1: Escribir los tests que fallan**

Primero completar el encabezado de `tests/test_tanks.py` (en Task 2 solo se importaba `os`, `unittest` y `compiler`):

```python
import os
import random
import unittest

import compiler
from engine import crear_juego
from engine.tanks import Tanks
from engine.utilidades import Colores

CARPETA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def accion(verbo, objeto=None, params=None):
    return {'accion': verbo, 'objeto': objeto, 'params': params or []}
```

Y añadir al final de `TestBrickTanks`:

```python
    def test_el_registro_crea_la_clase(self):
        self.assertIsInstance(crear_juego(self.compilar()), Tanks)
```

Después de `TestBrickTanks`, agregar:

```python
def datos_tanks(inicio=(2, 4)):
    # Tablero 8x8 y eventos equivalentes a games/tanks.brick, en pequeño.
    eventos = {
        'ON_START': [accion('SPAWN', 'JUGADOR', [list(inicio)] if inicio else [])],
        'ON_KEY_UP': [accion('MOVE', 'PLAYER', ['UP'])],
        'ON_KEY_DOWN': [accion('MOVE', 'PLAYER', ['DOWN'])],
        'ON_KEY_LEFT': [accion('MOVE', 'PLAYER', ['LEFT'])],
        'ON_KEY_RIGHT': [accion('MOVE', 'PLAYER', ['RIGHT'])],
        'ON_KEY_SHOOT': [accion('SHOOT', 'PLAYER')],
        'ON_ENEMY_DEFEATED': [accion('INCREASE_SCORE', '100'),
                              accion('SPAWN', 'ENEMIGO', ['RANDOM'])],
        'ON_EAT_HAMMER': [accion('HEAL', 'PLAYER')],
        'ON_PLAYER_HIT': [accion('INCREASE_SCORE', '1')],
        'ON_BULLET_HIT_WALL': [accion('INCREASE_SCORE', '7')],
        'ON_GAME_OVER': [accion('INCREASE_SCORE', '1')],
    }
    return {
        'tipo_juego': 'TANKS',
        'config': {'grid_size': [8, 8]},
        'shapes': {
            'JUGADOR': {'type': 'PLAYER', 'hp': 3, 'color': 'GREEN',
                        'estados': [[[0, 1, 0], [1, 1, 1], [0, 1, 0]]]},
            'ENEMIGO': {'type': 'ENEMY', 'hp': 1, 'speed': 2, 'fire_rate': 3,
                        'color': 'RED', 'estados': [[[1]]]},
            'BALA_JUGADOR': {'type': 'BULLET', 'owner': 'PLAYER', 'damage': 1,
                             'color': 'CYAN', 'estados': [[[1]]]},
            'BALA_ENEMIGA': {'type': 'BULLET', 'owner': 'ENEMY', 'damage': 1,
                             'color': 'YELLOW', 'estados': [[[1]]]},
            'MURO': {'type': 'WALL', 'color': 'GRAY', 'estados': [[[1]]]},
            'MARTILLO': {'type': 'PICKUP', 'heal': 1, 'color': 'YELLOW',
                         'estados': [[[1]]]},
        },
        'events': eventos,
    }


def agregar_enemigo(juego, x, y, direccion=(1, 0), hp=1, nombre='ENEMIGO'):
    juego.enemigos.append({'nombre': nombre, 'x': x, 'y': y, 'hp': hp, 'max_hp': hp,
                           'direccion': direccion,
                           'tiempo_movimiento': 0.0, 'tiempo_disparo': 0.0})
    return juego.enemigos[-1]


class TestTanks(unittest.TestCase):

    def setUp(self):
        random.seed(1234)

    def test_spawn_jugador_teclas_y_hp(self):
        juego = Tanks(datos_tanks())
        self.assertEqual(juego.jugador['hp'], 3)
        self.assertEqual(juego.jugador['max_hp'], 3)
        self.assertEqual((juego.jugador['x'], juego.jugador['y']), (2, 4))
        self.assertEqual(juego.jugador['orientacion'], (0, -1))
        juego.dibujar()
        self.assertEqual(juego.label_vida.opciones['text'], 'VIDA 3/3')
        self.assertEqual(len(juego.canvas.rectangulos), 5)      # la cruz del jugador
        self.assertEqual(set(c[1] for c in juego.canvas.rectangulos),
                         set([Colores['GREEN']]))

        juego.manejar_tecla('RIGHT')
        self.assertEqual(juego.jugador['orientacion'], (1, 0))
        self.assertEqual((juego.jugador['x'], juego.jugador['y']), (3, 4))

    def test_disparo_avanza_y_respeta_cooldown(self):
        juego = Tanks(datos_tanks())
        juego.jugador['orientacion'] = (1, 0)
        juego.manejar_tecla('SPACE')
        self.assertEqual(len(juego.balas), 1)
        bala = juego.balas[0]
        self.assertEqual((bala['x'], bala['y'], bala['dx'], bala['dy']), (5, 5, 1, 0))
        self.assertEqual(bala['dueno'], 'PLAYER')
        self.assertEqual((bala['dano'], bala['color']), (1, Colores['CYAN']))
        self.assertEqual(juego.jugador['cooldown'], 0.3)

        juego.manejar_tecla('SPACE')          # cooldown activo: no sale otra
        self.assertEqual(len(juego.balas), 1)

        juego.ejecutar_evento('ON_TICK')      # la bala avanza sola
        self.assertEqual((juego.balas[0]['x'], juego.balas[0]['y']), (6, 5))

    def test_el_jugador_no_atraviesa_muros_ni_bordes(self):
        juego = Tanks(datos_tanks())
        juego.grid[5][5] = 1                  # (5,5) esta en la huella del paso a la derecha
        juego.manejar_tecla('RIGHT')
        self.assertEqual(juego.jugador['x'], 2)
        self.assertEqual(juego.jugador['orientacion'], (1, 0))   # igual apunta

        juego.jugador['x'] = 6                # pegado al borde derecho (8 columnas)
        juego.manejar_tecla('RIGHT')
        self.assertEqual(juego.jugador['x'], 6)

    def test_la_bala_destruye_el_muro(self):
        juego = Tanks(datos_tanks())
        juego.jugador['orientacion'] = (1, 0)
        juego.grid[5][6] = 1
        juego.manejar_tecla('SPACE')
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.balas, [])
        self.assertEqual(juego.grid[5][6], 0)
        self.assertEqual(juego.puntuacion, 7)          # ON_BULLET_HIT_WALL corrio

    def test_bala_del_jugador_dana_y_mata(self):
        juego = Tanks(datos_tanks())
        juego.jugador['orientacion'] = (1, 0)
        enemigo = agregar_enemigo(juego, 6, 5, hp=2)
        juego.manejar_tecla('SPACE')
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(enemigo['hp'], 1)
        self.assertEqual(juego.balas, [])
        self.assertIn(enemigo, juego.enemigos)

        juego.jugador['cooldown'] = 0
        juego.manejar_tecla('SPACE')
        juego.ejecutar_evento('ON_TICK')
        self.assertNotIn(enemigo, juego.enemigos)
        self.assertEqual(juego.puntuacion, 100)        # ON_ENEMY_DEFEATED
        self.assertEqual(len(juego.enemigos), 1)       # el .brick lo respawneo

    def test_bala_enemiga_baja_la_vida_y_termina(self):
        juego = Tanks(datos_tanks())
        bala = {'x': 3, 'y': 7, 'dx': 0, 'dy': -1, 'dueno': 'ENEMY',
                'dano': 1, 'color': Colores['YELLOW']}
        juego.balas = [dict(bala)]
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.jugador['hp'], 2)
        self.assertEqual(juego.balas, [])
        self.assertEqual(juego.puntuacion, 1)          # ON_PLAYER_HIT

        juego.jugador['hp'] = 1
        juego.balas = [dict(bala)]
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.jugador['hp'], 0)
        self.assertTrue(juego.juego_terminado)

        juego.game_loop()      # emite ON_GAME_OVER una vez
        juego.game_loop()      # y no lo repite
        self.assertEqual(juego.puntuacion, 3)

    def test_spawn_del_jugador_en_el_borde_se_recorta(self):
        # Review Focus 1: un spawn que no cabe dejaria la partida sin jugador.
        juego = Tanks(datos_tanks(inicio=(7, 7)))
        self.assertEqual((juego.jugador['x'], juego.jugador['y']), (5, 5))
        juego.dibujar()
        for (x1, y1, x2, y2), _ in juego.canvas.rectangulos:
            self.assertTrue(0 <= x1 < juego.ancho_canvas and 0 <= y1 < juego.alto_canvas)

    def test_disparo_contra_el_borde_no_crea_bala(self):
        # Review Focus 4: sin cooldown, apuntar afuera permitiria rafagas.
        juego = Tanks(datos_tanks())
        juego.jugador['y'] = 0                # el cañon apunta arriba, fuera del tablero
        juego.manejar_tecla('SPACE')
        self.assertEqual(juego.balas, [])
        self.assertEqual(juego.jugador['cooldown'], 0.3)
```

En `tests/test_game.py`, al final de `test_eventos_y_teclas`, agregar:

```python
        # Espacio dispara ON_KEY_SHOOT: es la tecla de Tanks. Los juegos
        # clasicos no declaran el evento y la tecla no hace nada.
        juego = JuegoPrueba(datos({'ON_KEY_SHOOT': [{'accion': 'SHOOT', 'objeto': 'PLAYER',
                                                     'params': []}]}))
        juego.manejar_input_gui(EventoFalso('space'))
        self.assertEqual(juego.acciones, [('SHOOT', 'PLAYER')])
        otro = JuegoPrueba(datos())
        otro.manejar_input_gui(EventoFalso('space'))
        self.assertEqual(otro.acciones, [])
```

En `tests/test_juegos.py`, `test_crear_juego_por_tipo`: agregar `Tanks` al import de `engine` y, al final del test:

```python
        self.assertIn('TANKS', JUEGOS)
        vacio['tipo_juego'] = 'TANKS'
        vacio['shapes'] = {}
        self.assertIsInstance(crear_juego(vacio), Tanks)
```

- [ ] **Step 2: Correr los tests y verlos fallar**

Run: `cmd /c "C:\Python27\python.exe -u -m unittest -v tests.test_tanks tests.test_game tests.test_juegos"`
Expected: `ImportError: cannot import name tanks` / `Tanks`.

- [ ] **Step 3: Agregar `GRAY`, mapear Espacio y registrar la clase**

`engine/utilidades.py`, en `Colores`:

```python
    "GRAY": "#808080",
```

`engine/game.py`, en `manejar_tecla` (después del bloque de flechas):

```python
        if key in ('UP', 'DOWN', 'LEFT', 'RIGHT'):
            self.ejecutar_evento('ON_KEY_' + key)
        elif key == 'SPACE':
            # Tanks dispara con espacio; los juegos viejos no declaran
            # ON_KEY_SHOOT y el evento simplemente no existe.
            self.ejecutar_evento('ON_KEY_SHOOT')
```

`engine/__init__.py`: `from .tanks import Tanks`, agregar `'Tanks'` a `__all__` y `'TANKS': Tanks` a `JUEGOS`.

- [ ] **Step 4: Escribir `engine/tanks.py` (parte 1: estado, formas, spawn y disparo)**

```python
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
```

- [ ] **Step 5: Escribir `engine/tanks.py` (parte 2: tick, balas, dibujo)**

```python
    # TICK
    # ----

    def ejecutar_evento(self, nombre_evento):
        # Game.ejecutar_evento despacha las acciones del .brick; Tanks adelanta
        # el mundo ANTES, para que el ON TICK del .brick vea el estado del tick.
        if nombre_evento == 'ON_TICK':
            self.avanzar_mundo(self.velocidad_gravedad)
        super(Tanks, self).ejecutar_evento(nombre_evento)

    def avanzar_mundo(self, delta):
        self._avanzar_balas()
        if self.jugador and self.jugador['cooldown'] > 0:
            self.jugador['cooldown'] = max(0.0, self.jugador['cooldown'] - delta)

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
```

`color_celda_grid` solo se llama para celdas con valor 1 (Game.dibujar ya filtró `grid[y][x] == 1`), así que no hace falta `COLOR_GRID_FIJA`.

- [ ] **Step 6: Correr los tests hasta verde**

Run: `cmd /c "C:\Python27\python.exe -u -m unittest -v tests.test_tanks tests.test_game tests.test_juegos"`
Expected: OK.

- [ ] **Step 7: Commit**

```bash
git add engine/tanks.py engine/__init__.py engine/game.py engine/utilidades.py tests/test_tanks.py tests/test_game.py tests/test_juegos.py
git commit -m "tanks: jugador, disparo, balas, colisiones y dibujo"
```

---

### Task 4: Motor II — muros del nivel, IA de enemigos y martillo

**Files:**
- Modify: `engine/tanks.py`
- Test: `tests/test_tanks.py` (nueva clase `TestTanksMundo`)

**Interfaces:**
- Consumes: todo lo de Task 3.
- Produces: `Tanks.iniciar_partida()` (muros + reset de entidades), `avanzar_mundo(delta)` completo (balas → enemigos se mueven → enemigos disparan → martillo → cooldown), `_generar_muros()`, `_mover_enemigos(delta)`, `_disparar_enemigos(delta)`, `_recoger_martillo()`, `_spawn_martillo()`.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_tanks.py`:

```python
class TestTanksMundo(unittest.TestCase):

    def setUp(self):
        random.seed(1234)

    def test_martillo_sana_y_reaparece(self):
        juego = Tanks(datos_tanks())
        juego.jugador['hp'] = 1
        juego.martillo = (3, 5)          # dentro de la cruz del jugador
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.jugador['hp'], 2)
        self.assertIsNotNone(juego.martillo)
        self.assertNotEqual(juego.martillo, (3, 5))

    def test_el_evento_puede_reubicar_el_martillo_sin_duplicarlo(self):
        datos = datos_tanks()
        datos['events']['ON_EAT_HAMMER'] = [accion('HEAL', 'PLAYER'),
                                            accion('SPAWN', 'MARTILLO', [[7, 7]])]
        juego = Tanks(datos)
        juego.jugador['hp'] = 2
        juego.martillo = (3, 5)
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.jugador['hp'], 3)
        self.assertEqual(juego.martillo, (7, 7))   # el motor no lo movio otra vez

    def test_martillo_sin_celda_libre_no_repite_el_evento(self):
        # Review Focus 3: tablero lleno de muros salvo la huella del jugador.
        # El martillo se cura una vez y queda en None; no hay bucle.
        juego = Tanks(datos_tanks())
        juego.jugador['hp'] = 1
        for y in range(juego.alto):
            for x in range(juego.ancho):
                juego.grid[y][x] = 1
        for x, y in juego._celdas_jugador():
            juego.grid[y][x] = 0
        juego.martillo = (3, 5)          # dentro de la cruz del jugador
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.jugador['hp'], 2)
        self.assertIsNone(juego.martillo)
        juego.ejecutar_evento('ON_TICK')
        self.assertEqual(juego.jugador['hp'], 2)

    def test_enemigo_se_mueve_solo(self):
        juego = Tanks(datos_tanks())
        enemigo = agregar_enemigo(juego, 0, 0)
        juego.avanzar_mundo(0.5)                   # SPEED 2 => un paso cada 0.5 s
        self.assertEqual((enemigo['x'], enemigo['y']), (1, 0))

    def test_enemigo_gira_al_chocar(self):
        juego = Tanks(datos_tanks())
        enemigo = agregar_enemigo(juego, 0, 0)
        juego.grid[0][1] = 1
        juego.avanzar_mundo(0.5)
        self.assertEqual(enemigo['direccion'], (0, 1))
        self.assertEqual((enemigo['x'], enemigo['y']), (0, 1))

    def test_enemigo_rodeado_se_queda_quieto(self):
        # Review Focus 2: cuatro muros alrededor; ni bucle ni atravesarlos.
        juego = Tanks(datos_tanks())
        enemigo = agregar_enemigo(juego, 1, 1)
        for x, y in ((2, 1), (0, 1), (1, 0), (1, 2)):
            juego.grid[y][x] = 1
        juego.avanzar_mundo(0.5)
        self.assertEqual((enemigo['x'], enemigo['y']), (1, 1))
        self.assertEqual(enemigo['direccion'], (1, 0))   # cuatro giros, vuelve al inicio

    def test_enemigo_dispara_apuntado(self):
        juego = Tanks(datos_tanks())     # jugador 3x3 en (2,4): centro (3,5)
        # Misma columna que el centro del jugador y baja por ella (si apuntara
        # a la derecha, el primer paso lo sacaria de la columna).
        agregar_enemigo(juego, 3, 0, direccion=(0, 1))
        juego.avanzar_mundo(3.0)         # FIRE_RATE 3
        balas = [b for b in juego.balas if b['dueno'] == 'ENEMY']
        self.assertEqual(len(balas), 1)
        self.assertEqual((balas[0]['dx'], balas[0]['dy']), (0, 1))

    def test_enemigo_desalineado_dispara_al_frente(self):
        juego = Tanks(datos_tanks())
        agregar_enemigo(juego, 0, 0)
        juego.avanzar_mundo(3.0)
        balas = [b for b in juego.balas if b['dueno'] == 'ENEMY']
        self.assertEqual(len(balas), 1)
        self.assertEqual((balas[0]['dx'], balas[0]['dy']), (1, 0))

    def test_los_muros_del_nivel_se_generan_al_iniciar(self):
        datos = datos_tanks()
        datos['levels'] = [{'nombre': 'BABY', 'walls': 6}]
        # Sin ON_START: los spawns borran muros bajo su matriz y el conteo
        # exacto dejaria de ser 6.
        datos['events'].pop('ON_START')
        juego = Tanks(datos)
        self.assertEqual(sum(fila.count(1) for fila in juego.grid), 6)

    def test_muros_se_limitan_a_las_celdas_del_tablero(self):
        # Review Focus 5: WALLS 100 en 8x8 = 64 celdas; no cuelga y se corta.
        datos = datos_tanks()
        datos['levels'] = [{'nombre': 'BABY', 'walls': 100}]
        datos['events'].pop('ON_START')          # sin jugador, el tablero queda lleno
        juego = Tanks(datos)
        self.assertEqual(sum(fila.count(1) for fila in juego.grid), 64)

    def test_dos_niveles_no_dejan_muros_sobre_el_menu(self):
        datos = datos_tanks()
        datos['levels'] = [{'nombre': 'PATRULLA', 'tick': 0.12, 'walls': 6},
                           {'nombre': 'ASEDIO', 'tick': 0.08, 'walls': 10}]
        datos['config']['start_level'] = 'PATRULLA'
        datos['events'].pop('ON_START')          # spawns no borran muros
        juego = Tanks(datos)
        self.assertFalse(juego.iniciado)
        self.assertEqual(sum(fila.count(1) for fila in juego.grid), 0)

        juego.run()
        juego.botones_nivel[1].opciones['command']()
        self.assertTrue(juego.iniciado)
        self.assertEqual(juego.velocidad_gravedad, 0.08)
        self.assertEqual(sum(fila.count(1) for fila in juego.grid), 10)

    def test_fuzz_cinco_teclas_trescientas_veces(self):
        juego = Tanks(datos_tanks())
        teclas = ['UP', 'DOWN', 'LEFT', 'RIGHT', 'SPACE']
        for _ in range(300):
            if juego.juego_terminado:
                break
            juego.manejar_tecla(random.choice(teclas))
            juego.game_loop()
        self.assertGreater(juego.frame, 0)
```

- [ ] **Step 2: Correr los tests y verlos fallar**

Run: `cmd /c "C:\Python27\python.exe -u -m unittest -v tests.test_tanks.TestTanksMundo"`
Expected: FAIL — no hay muros, los enemigos no se mueven ni disparan.

- [ ] **Step 3: Implementar muros de nivel y arranque de partida**

Agregar a `Tanks`:

```python
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
```

- [ ] **Step 4: Implementar el movimiento y el disparo de los enemigos**

Reemplazar `avanzar_mundo` de Task 3 por esta versión y agregar los métodos:

```python
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
```

- [ ] **Step 5: Implementar el martillo**

```python
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
```

- [ ] **Step 6: Correr los tests hasta verde**

Run: `cmd /c "C:\Python27\python.exe -u -m unittest -v tests.test_tanks"`
Expected: OK.

- [ ] **Step 7: Commit**

```bash
git add engine/tanks.py tests/test_tanks.py
git commit -m "tanks: muros por nivel, IA de enemigos y martillo"
```

---

### Task 5: Documentación, changelog de la actividad y grupo de CI

**Files:**
- Modify: `docs/Guia-BrickScript.txt` (después de la sección Snake), `docs/README.md`, `.github/workflows/tests.yml`
- Create: `docs/cambios/tanks_changes.txt`

**Interfaces:**
- Consumes: nombres finales de atributos, acciones y eventos de Tasks 1–4.
- Produces: guía del lenguaje con TANKS, changelog con `APORTES POR INTEGRANTE` para los 4 integrantes (huecos marcados `(pendiente)`), CI que corre `tests.test_tanks`.

- [ ] **Step 1: Agregar la sección TANKS a `docs/Guia-BrickScript.txt`**

Después de la sección `--- SINTAXIS PARA SNAKE ---` (final del archivo), agregar:

```
--- SINTAXIS PARA TANKS (Actividad 5A) ---

GAME_TYPE TANKS. El jugador es unico y tiene puntos de vida; los enemigos
declaran color, vida, velocidad y cadencia; las balas llevan su propio dano.

Eventos disponibles: ON START, ON TICK, ON KEY_UP, ON KEY_DOWN, ON KEY_LEFT,
ON KEY_RIGHT, ON KEY_SHOOT, ON PLAYER_HIT, ON EAT_HAMMER, ON ENEMY_DEFEATED,
ON BULLET_HIT_WALL, ON GAME_OVER. ON TARGET_SCORE se acepta pero todavia no se
emite (es de la Actividad 5B).

Atributos de DEFINE SHAPE (todos opcionales salvo TYPE):
    TYPE PLAYER|ENEMY|BULLET|WALL|PICKUP|BOSS   rol de la forma
    HP <n>          impactos que aguanta (jugador 3, enemigo 1 por defecto)
    DAMAGE <n>      vida que quita la bala por impacto (1 por defecto)
    SPEED <n>       celdas por segundo del enemigo (2 por defecto)
    FIRE_RATE <n>   segundos entre disparos (3 por defecto)
    HEAL <n>        vida que recupera el martillo (1 por defecto)
    OWNER PLAYER|ENEMY   quien dispara la bala (obligatorio en BULLET)
    COLOR <color>   color de la matriz (CYAN por defecto)
TYPE y OWNER aceptan tambien la forma TYPE: PLAYER.

Acciones:
* SPAWN <FORMA> AT (X, Y) | SPAWN <FORMA> AT RANDOM
* MOVE PLAYER [UP | DOWN | LEFT | RIGHT]   orienta el cañon y avanza 1 celda
* SHOOT PLAYER            dispara si el cañon no esta en enfriamiento (0.3 s)
* HEAL PLAYER             cura con el HEAL de la forma TYPE PICKUP
* INCREASE_SCORE / DECREASE_SCORE / RESET_SCORE / GAME_OVER
* PLAY_MUSIC / PLAY_EFFECT / STOP_MUSIC

Modificador de nivel: WALLS <numero> genera esa cantidad de muros al empezar
la partida. Los muros son celdas del tablero: las balas los destruyen y los
tanques no los atraviesan.

El motor emite ON PLAYER_HIT, ON ENEMY_DEFEATED, ON EAT_HAMMER,
ON BULLET_HIT_WALL y ON GAME_OVER (una sola vez). Las flechas mueven y
Espacio dispara; en Snake y Tetris Espacio no hace nada.

Reglas que el compilador verifica (solo para GAME_TYPE TANKS): exactamente una
forma TYPE PLAYER, al menos una TYPE ENEMY, una bala OWNER PLAYER y otra
OWNER ENEMY, matrices cuadradas para PLAYER/ENEMY/BOSS/WALL, filas del mismo
ancho, al menos una celda encendida y HP/DAMAGE/SPEED/FIRE_RATE/HEAL >= 1.
```

- [ ] **Step 2: Escribir `docs/cambios/tanks_changes.txt`**

Estructura (misma que `tetris_reborn_changes.txt`):

```
---------------------------------------  CAMBIOS CON RESPECTO A SNAKE_REMAKE  ---------------------------------------

RESUMEN DE APORTES POR INTEGRANTE (según rúbrica de la Actividad 5)
- Miguel Angel Echeverri Isaza: (pendiente)
- Tomas Lujan Colorado: (pendiente)
- Nixon Daniel Lizcano Santana: (pendiente)
- Andrés Felipe Bustamante López: (pendiente)

------------------------------ NUEVA GRAMÁTICA (compiler.py, grammars/tanks.bnf) ------------------------------

>>>>>> DEFINE SHAPE acepta atributos de entidad.
[tabla TYPE/HP/DAMAGE/SPEED/FIRE_RATE/HEAL/OWNER con sus defaults]

>>>>>> LEVELS acepta WALLS <numero>.
[ejemplo comentado]

>>>>>> Validación semántica solo para GAME_TYPE TANKS.
[lista de las 6 reglas del spec §4.3 y un ejemplo de mensaje de error]

------------------------------ NUEVO JUEGO (games/tanks.brick) ------------------------------

>>>>>> Formas, niveles PATRULLA y ASEDIO, tema y tres efectos.

------------------------------ NUEVO MOTOR (engine/tanks.py) ------------------------------

>>>>>> Orden de un tick: balas, movimiento de enemigos, disparo de enemigos,
ON TICK del .brick.
>>>>>> Muros como celdas de self.grid.
>>>>>> IA: patrulla, giro de 90° al chocar y disparo apuntado por fila/columna.
>>>>>> Martillo: HEAL + reaparición con la guarda del evento.
>>>>>> Entrada: SPACE -> ON_KEY_SHOOT en engine/game.py.

------------------------------ CALIDAD ------------------------------

>>>>>> tests/test_tanks.py (10 puntos del spec §7) y grupo propio en el CI.
>>>>>> Retrocompatibilidad: Snake y Tetris sin cambios; TEMA_NYAN intacto.
```

Rellenar cada `>>>>>>` con 2–4 líneas de explicación real (no dejar corchetes ni `(pendiente)` fuera de la sección de aportes).

- [ ] **Step 3: Actualizar `docs/README.md`**

- Marcar el avance: `- [x] Actividad 5: Tanks (17 nov)`. De paso marcar también las
  Actividades 3 y 4 (`- [x]`), que siguen sin tachar aunque sus changelogs ya
  existen en `docs/cambios/`: así el checklist no queda con la 5 marcada y las
  dos anteriores no.
- En la lista de documentación, extender el punto 5:

```
5. [`cambios/`](cambios/): registro de cambios de las actividades 3, 4 y 5
   ([Tetris+](cambios/tetris_reborn_changes.txt), [Snake+](cambios/snake_evolved_changes.txt),
   [Tanks](cambios/tanks_changes.txt)).
```

- [ ] **Step 4: Agregar el grupo de tests al CI**

En `.github/workflows/tests.yml`, dentro de `matrix.include`, después del grupo de Snake:

```yaml
          - grupo: Tanks
            modulo: tests.test_tanks
```

- [ ] **Step 5: Verificar documentación y CI**

Run: `cmd /c "C:\Python27\python.exe -u -m unittest -v tests.test_tanks"` → OK.
Run: `git diff --stat` → solo `docs/` y `.github/workflows/tests.yml`.
Run: `Select-String -Path docs/Guia-BrickScript.txt -Pattern "SINTAXIS PARA TANKS"` → una coincidencia.
Run: `Select-String -Path .github/workflows/tests.yml -Pattern "tests.test_tanks"` → una coincidencia.

- [ ] **Step 6: Commit**

```bash
git add docs/Guia-BrickScript.txt docs/cambios/tanks_changes.txt docs/README.md .github/workflows/tests.yml
git commit -m "docs: guia, changelog de la Actividad 5 y grupo de CI para Tanks"
```

---

### Task 6: Verificación end-to-end de la entrega

**Files:** ninguno (solo verificación; si algo falla, se corrige en el archivo que corresponda con un commit aparte).

- [ ] **Step 1: Suite completa**

Run: `cmd /c "C:\Python27\python.exe -u -m unittest discover -s tests -t . -v" > %TEMP%\tanks_suite.log 2>&1` y luego revisar el final del log.
Expected: `Ran <149 + N> tests` y `OK` (sin fallos; N = tests nuevos, alrededor de 40).

- [ ] **Step 2: Todos los `.brick` compilan y pasan pyflakes**

```bash
for %f in (games\*.brick) do @C:\Python27\python.exe .\compiler.py %f
cmd /c "C:\Python27\python.exe -m pyflakes compiler.py runtime.py engine tests"
```
Expected: una línea `Compilacion exitosa!` por cada `.brick` y pyflakes sin salida. Si pyflakes no está instalado: `C:\Python27\python.exe -m pip install pyflakes==2.0.0`.

- [ ] **Step 3: Partida real**

Run: `cmd /c "jugar.bat tanks"` (elige `1. Patrulla` en el menú).
Expected: se abre la ventana, el tema suena, el jugador se mueve con flechas, dispara con Espacio, los enemigos patrullan y disparan, los muros se rompen, el martillo cura y el game over suena con `MORIR`.

- [ ] **Step 4: Retrocompatibilidad explícita**

Run: `cmd /c "C:\Python27\python.exe -u -m unittest -v tests.test_retrocompatibilidad tests.test_juegos"`
Expected: OK (Snake y Tetris clásicos intactos; `games/tanks.brick` se compila pero no entra en `juegos_clasicos` porque su `tipo_juego` es TANKS).

- [ ] **Step 5: Commit final (solo si hubo correcciones)**

```bash
git add -A
git commit -m "tanks: correcciones de la verificacion end-to-end"
```
