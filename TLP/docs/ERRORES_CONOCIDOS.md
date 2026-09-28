# Errores conocidos del runtime

Errores que ya existian en el `runtime.py` original y que se mantuvieron a
proposito durante el rework a `engine/` (antes `juegos/`; la primera iteracion solo movio y
ordeno codigo, sin cambiar comportamiento).

Se confirmaron comparando el runtime original contra el nuevo con las mismas
semillas y teclas: ambos fallan exactamente igual.

| # | Juego | Error | Gravedad |
|---|-------|-------|----------|
| 1 | Tetris | `KeyError` al limpiar lineas en `tetris.brick` | Alta (cierra el juego) |
| 2 | Tetris | Los limites exactos del sorteo no dan power up | Baja |
| 3 | Tetris | Una pieza `COLOR WHITE` se dibuja como arcoiris | Baja (hoy no ocurre) |
| 4 | Tetris | Power up con 1 linea (modo de prueba) | Pendiente |
| 5 | Snake | `SET_DIRECTION` en el `.brick` no hace nada | Media |
| 6 | Snake | `GROW PLAYER N` ignora la cantidad | Media |
| 7 | Tetris | Codigo repetido y variable sin uso | Limpieza |

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

---

## 4. Power up con 1 linea (modo de prueba)

**Donde:** `engine/tetris.py`, `tetris_limpiar_lineas()`.

**Que pasa:** el propio codigo lo marca como pendiente:

```python
# TESTING: con 1 linea ya da premio (para entrega volver a >= 3 = triple).
if lineas_limpias >= 1:
```

Antes de la entrega hay que cambiarlo a `>= 3`.

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
