# Errores conocidos del runtime (todos corregidos)

Errores que ya existian en el `runtime.py` original y que se mantuvieron a
proposito durante el rework a `engine/` (antes `juegos/`; la primera iteracion solo movio y
ordeno codigo, sin cambiar comportamiento).

Se confirmaron comparando el runtime original contra el nuevo con las mismas
semillas y teclas: ambos fallaban exactamente igual. Los 7 se corrigieron
despues (ver **Solucion aplicada** en cada seccion).

| # | Juego | Error | Gravedad | Estado |
|---|-------|-------|----------|--------|
| 1 | Tetris | `KeyError` al limpiar lineas en `tetris.brick` | Alta (cerraba el juego) | Corregido |
| 2 | Tetris | Los limites exactos del sorteo no daban power up | Baja | Corregido |
| 3 | Tetris | Una pieza `COLOR WHITE` se dibujaba como arcoiris | Baja (hoy no ocurre) | Corregido |
| 4 | Tetris | Power up con 1 linea (modo de prueba) | Pendiente entrega | Corregido (`>= 3`) |
| 5 | Snake | `SET_DIRECTION` en el `.brick` no hacia nada | Media | Corregido |
| 6 | Snake | `GROW PLAYER N` ignoraba la cantidad | Media | Corregido |
| 7 | Tetris | Codigo repetido y variable sin uso | Limpieza | Corregido |

---

## 1. `KeyError` al limpiar lineas en `tetris.brick`

**Donde:** `engine/tetris.py`, `tetris_limpiar_lineas()` (linea 234) y
`tetris_spawn_pieza()`.

**Que pasa:** al limpiar una linea se sortea un power up y se guarda en
`siguiente_powerup` (`'POWERUP'`, `'CLEAR_LINE_PIECE'`, `'SUPERBOMBA'` o
`'CLEAR_THREE_PIECE'`). En el siguiente spawn se busca esa forma en
`datos_juego['shapes']`, pero `games/tetris.brick` no define ninguna de esas
formas (solo `tetris_reborn.brick` las tiene).

**Como reproducirlo:** jugar `tetris` y completar una linea. Con un 80% de
probabilidad el juego se cierra con:

```
KeyError: 'SUPERBOMBA'
```

**Posible arreglo:** sortear solo power ups que existan en `shapes`, o no
sortear nada si el juego no define ninguno.

**Solucion aplicada:** en `tetris_limpiar_lineas()` se sortea a `candidato` y
solo se guarda/notifica si `candidato in datos_juego['shapes']`; si no, queda
`None` y el siguiente spawn es una pieza normal. Test:
`test_retrocompatibilidad.py::test_limpiar_linea_con_cualquier_sorteo` (antes
`@expectedFailure`, ahora pasa sin el decorador).

---

## 2. Los limites exactos del sorteo no dan power up

**Donde:** `engine/tetris.py`, lineas 247-260.

**Que pasa:** los rangos usan `<` y `>` estrictos:

```python
if eleccion < 0.25: ...
elif eleccion > 0.25 and eleccion < 0.45: ...
elif eleccion > 0.45 and eleccion < 0.65: ...
elif eleccion > 0.65 and eleccion < 0.80: ...
else: self.siguiente_powerup = None
```

Si `random.random()` devuelve exactamente `0.25`, `0.45` o `0.65`, cae en el
`else` y no hay premio. La probabilidad real es casi nula, pero la intencion
del codigo es otra.

**Test que lo documenta:** `tests/test_tetris.py`, `test_limite_025_no_da_powerup`
(habra que cambiarlo cuando se arregle).

**Posible arreglo:** usar `elif eleccion < 0.45:`, `elif eleccion < 0.65:`, etc.

**Solucion aplicada:** cadena en `<` (`< 0.25`, `< 0.45`, `< 0.65`, `< 0.80`);
`0.25 -> CLEAR_LINE_PIECE`, `0.45 -> SUPERBOMBA`, `0.65 -> CLEAR_THREE_PIECE`.
Test: `test_tetris.py::test_sorteo_de_power_up` cubre los 3 limites.

---

## 3. Una pieza `COLOR WHITE` se dibuja como arcoiris

**Donde:** `engine/utilidades.py` (lineas 15 y 17) y
`engine/tetris.py`, `dibujar_elementos()`.

**Que pasa:** `WHITE` y `RAINBOW` tienen el mismo valor (`#FFFFFF`), y para
saber si una pieza es arcoiris se compara el color:

```python
if self.pieza_color == Colores.get("RAINBOW", "#FFFFFF"):
```

Una pieza definida con `COLOR WHITE` se dibujaria con los colores del arcoiris.
Hoy ningun `.brick` usa `WHITE`, por eso no se nota.

**Posible arreglo:** decidir si es arcoiris por el nombre del color
(`Datos.get("color") == "RAINBOW"`) y no por su valor hexadecimal.

**Solucion aplicada:** `tetris_spawn_pieza()` guarda
`pieza_es_arcoiris = (Datos.get("color") == "RAINBOW")` y
`dibujar_elementos()` usa ese flag en vez de comparar el hex.

---

## 4. Power up con 1 linea (modo de prueba)

**Donde:** `engine/tetris.py`, `tetris_limpiar_lineas()`.

**Que pasa:** el propio codigo lo marca como pendiente:

```python
# TESTING: con 1 linea ya da premio (para entrega volver a >= 3 = triple).
if lineas_limpias >= 1:
```

Antes de la entrega hay que cambiarlo a `>= 3`.

**Solucion aplicada:** cambiado a `if lineas_limpias >= 3:` (simple/doble solo
dan puntaje). Tests de `test_sorteo_de_power_up` usan triple y hay chequeo
explicito de que con 1-2 lineas no hay premio.

---

## 5. `SET_DIRECTION` en el `.brick` no hace nada

**Donde:** `engine/snake.py`, `manejar_tecla()` (linea 24) y
`ejecutar_accion()`.

**Que pasa:** `snake.brick` y `snake_remake.brick` definen los controles con
eventos:

```
ON KEY_UP:
  SET_DIRECTION UP
END
```

Pero en Snake las flechas llaman directo a `snake_cambiar_direccion()` y nunca
se ejecutan los eventos `ON_KEY_*`. Ademas `ejecutar_accion()` no reconoce el
verbo `SET_DIRECTION`. Resultado: cambiar o borrar esos bloques en el `.brick`
no tiene ningun efecto; los controles estan fijos en el codigo.

**Posible arreglo:** que `manejar_tecla()` dispare `ON_KEY_*` (como hace Tetris)
y que `ejecutar_accion()` maneje `SET_DIRECTION` llamando a
`snake_cambiar_direccion(objeto)`.

**Solucion aplicada:** tal cual; `manejar_tecla()` hace
`ejecutar_evento('ON_KEY_*')` y `ejecutar_accion()` traduce
`SET_DIRECTION` a `snake_cambiar_direccion(objeto)`. Borrar un bloque
`ON KEY_*` del `.brick` ahora si desactiva esa flecha. Test:
`test_snake.py::test_direccion` (incluye caso sin `ON_KEY_LEFT`).

---

## 6. `GROW PLAYER N` ignora la cantidad

**Donde:** `engine/snake.py`, `snake_crecer()` (linea 95) y
`snake_mover_jugador()`.

**Que pasa:** `snake_crecer()` esta vacio (`pass`). La serpiente crece porque
`snake_mover_jugador()` no quita la cola cuando come, asi que siempre crece
exactamente 1. Escribir `GROW PLAYER 3` en el `.brick` da el mismo resultado
que `GROW PLAYER 1`, y quitar `GROW` tampoco evita que crezca.

**Posible arreglo:** guardar en `snake_crecer()` cuantos segmentos faltan por
crecer y que `snake_mover_jugador()` no quite la cola mientras queden.

**Solucion aplicada:** `crecimiento_pendiente` (init `0`);
`snake_crecer(objeto, accion)` suma `int(params[0])` y `snake_mover_jugador()`
no hace `pop` mientras haya pendiente (vale para el tick donde se come y los
siguientes). Sin `GROW` en el `.brick`, comer ya no hace crecer. Test:
`test_snake.py::test_crecer_cantidad` (`GROW 3` -> +3 total; sin `GROW` -> +0).

---

## 7. Codigo repetido y variable sin uso

**Donde:** `engine/tetris.py`.

- `tetris_spawn_pieza()`: el bloque que coloca la pieza y revisa la colision
  esta repetido dos veces (lineas 116 y 120). La segunda vez no cambia nada.
- `inicializar_estado()`: `self.powerup_pendiente` (linea 21) se crea pero
  nunca se usa; el power up real se maneja con `self.siguiente_powerup`.
- `siguiente_powerup` no se inicializa en `inicializar_estado()`; por eso
  `tetris_spawn_pieza()` necesita `hasattr(self, 'siguiente_powerup')`.

**Posible arreglo:** borrar el bloque repetido y `powerup_pendiente`, e
inicializar `self.siguiente_powerup = None` junto con el resto del estado.

**Solucion aplicada:** tal cual; `tetris_spawn_pieza()` quedo con un solo
bloque de colocacion/colision y chequeo directo `if self.siguiente_powerup:`
(sin `hasattr`).

---

# Problemas extra (hallados al revisar, todos corregidos)

Se ignora a proposito el `import Tkinter` (solo Py2): el proyecto es Py2 por
decision (`jugar.bat/sh`, CI en `python:2.7`).

| # | Donde | Problema | Solucion |
|---|-------|----------|----------|
| E2 | `engine/tetris.py`, `engine/snake.py` | Division `/` en spawns (float en Py3) | `//` (en Py2 identico) |
| E3 | `engine/tetris.py`, `games/tetris_reborn.brick` | Sistema arcoiris residual (bonus sin powerup que lo diera; la ficha powerup ahora es bomba) | Eliminado: fuera `rainbow_grid`, `Bonus`/`ON_RAINBOW_LINE_CLEAR` y su bloque en `reborn`; la pieza cayendo sigue viendose arcoiris |
| E4 | `games/tetris_reborn.brick` | Bloque `ON PIECE_LAND` con `IF/EXPLODE_RADIUS` (sintaxis inexistente, compilaba a basura que el engine ignoraba) | Bloque borrado (la explosion ya la hace `tetris_fijar_pieza()`); `.json` regenerado |
| E5 | `games/*.json` | `snake.json` desactualizado (sin `GROW PLAYER 1`) | `.json` regenerados con `compiler.py` (son artefactos gitignored: `TLP/games/*.json`) |
| E6 | `engine/snake.py` `snake_spawn_comida()` | `while True` colgaba con tablero lleno | Si `len(cuerpo) >= ancho*alto`: `juego_terminado = True` |
| E7 | `engine/game.py`, `compiler.py` | `INCREASE_SCORE` con texto crasheaba (`ValueError`) | Compilador lo rechaza (error de sintaxis); runtime lo ignora sin romper |
| E8 | `engine/snake.py` `snake_mover_jugador()` | Entrar a la cola era legal aun con crecimiento pendiente (duplicaba cabeza==cola) | La cola solo se excluye si `crecimiento_pendiente == 0` |
| E9 | `engine/tetris.py` `mostrar_notificacion_powerup()` | Sin `else`: powerup desconocido -> `UnboundLocalError` | `else: return` (sin notificacion) |
| E10 | `compiler.py` | Lexer tragaba minusculas/negativos en silencio; parser daba `IndexError` en truncados | `lexer` rechaza caracteres no reconocidos; `ver()` + `consumir_numero()` dan error de sintaxis |
| E11 | `engine/snake.py` | Doble giro rapido mataba: 2 teclas en un tick sumaban un 180 contra el cuerpo | Un giro por tick (`direccion_pendiente`, se aplica al moverse; valen cambios de opinion antes del tick) |
