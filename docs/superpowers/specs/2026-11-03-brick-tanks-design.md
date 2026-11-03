# Actividad 5 — Sección A (+B base): Brick Tanks jugable

**Fecha:** 2026-11-03
**Alcance:** solo A de la Actividad 5 ("Especificación del Tanque Jugador y
Enemigos"), pero con combate completo (mover, disparar, colisiones, vida y
martillo) para que el juego sea jugable. B (Final Boss y transición por
puntaje) queda reservado en la gramática y describe el camino, no se
implementa. C queda acotado a lo estrictamente necesario para que A funcione.

**Restricción dura:** retrocompatibilidad con todos los juegos anteriores.
Los 121 tests actuales corren con los mismos 2 fallos preexistentes
(`test_music_exige_nombre`, `test_snake_remake_abre_menu_y_arranca_al_elegir`),
que no se tocan.

## 1. Por qué A primero

A es el núcleo del juego: define la entidad jugador (único, con puntos de
vida), los enemigos (varios tipos con color, HP y velocidad) y la munición.
B (final boss) y C (reglas de combate) se construyen encima de esa gramática:

| Sección | Depende de A |
|---------|--------------|
| B. Final Boss | Sí — el boss es un `TYPE BOSS` con más `HP`; el motor ya lo trata como enemigo grande cuando exista |
| C. Combate | Sí — sin jugador/enemigos/balas no hay qué colisionar |
| D. Elementos gramaticales | Sí — `TYPE`, `HP`, `BOSS` y `BULLET` viven en el `DEFINE SHAPE` aquí definido |

## 2. Decisiones tomadas

| Decisión | Alternativas descartadas | Motivo |
|----------|--------------------------|--------|
| Gramática extendida (`DEFINE SHAPE` con atributos) + motor nuevo | gramática TANKS dedicada con bloque `BOSS`; ECS genérico | Un solo parser para todos los juegos; Tetris/Snake no se tocan; B después es `TYPE BOSS` + `HP` |
| Jugabilidad por celdas, 1 celda por tecla + cañón por orientación | tiempo continuo | Encaja con el `game_loop` y la grilla que ya existen; no exige un motor de tiempo real |
| Resistencia en HP con números chicos (jugador 3, bala −1, martillo +1, enemigos 1–2, jefe 20) | vidas clásicas; HP 100 y daños 10 | Lo pidió el grupo: cifras legibles en el `.brick`; el jefe solo declara más `HP` |
| Daño en el atributo `DAMAGE` de la bala (no en el atacante) | daña igual cualquier bala | El jefe podrá hacer más daño con su propia bala, sin lógica especial |
| IA de enemigos: patrulla + giro al chocar, con disparo apuntado si el jugador queda alineado en fila/columna | persecución directa; torretas fijas | Sin pathfinding; previsible; usa `SPEED` y `FIRE_RATE` por tipo |
| La gramática define; el motor no compara nombres (`ENEMIGO_RAPIDO`, niveles, etc.) | perfiles hardcodeados | Mismo patrón que Snake y Tetris: los nombres del `.brick` son contenidos, no algoritmos |
| Muros como celdas de `self.grid` (valor ≠ 0) | capa de entidades separada | Reutiliza dibujo, colisión y borrar por bala que ya existen; `WALLS n` como modificador de nivel |
| Vidas/daño por fila de `DEFINE SHAPE`; matrices cuadradas | matrices por orientación | Rotar una matriz conjunta no cambia la huella; chocar se calcula con la matriz actual |
| Semántica TANKS validada en el compilador | parsear y que el motor descubra el error al jugar | "evitar ambigüedades en el motor" exige errores en compilación, no en el canvas |

## 3. Restricciones del lenguaje actual (verificadas contra el código)

1. **El lexer solo tokeniza MAYÚSCULAS** (`compiler.py:30-35`). Todo el
   `.brick` de Tanks usa identificadores `A-Z_` y dígitos. `TARGET_SCORE`
   y `KEY_SHOOT` son tokens válidos, así que `ON TARGET_SCORE` /
   `ON KEY_SHOOT` ya compilan hoy sin cambios de lexer.
2. **`#` abre comentario** (`compiler.py:38`): el `.brick` no puede llevar
   colores hex; la paleta vive en `Colores` (`engine/utilidades.py`).
   Se agrega `GRAY` (`#808080`) para los muros.
3. **Los eventos del parser son genéricos** (`parsear_evento`,
   `compiler.py:400`): cualquier `ON <PALABRA>` es válido, y el motor lo
   ignora si nadie lo emite. Por eso `ON TARGET_SCORE` se parsea ya y el
   motor no lo emite hasta B.
4. **`parsear_shape` es el único lugar que reconoce atributos**
   (`compiler.py:161`): `while self.ver() in ("GEOMETRY", "COLOR", "CHANCE")`.
   Ahí van `TYPE`, `HP`, `DAMAGE`, `SPEED`, `FIRE_RATE`, `HEAL` y `OWNER`.
5. **`MODIFICADORES_NIVEL` es una tabla clave→(clave, tipo)**
   (`compiler.py:211`): se agrega `'WALLS': ('walls', 'numero')`. Ningún
   otro modificador cambia de significado.
6. **`Game.manejar_tecla` solo atiende flechas** (`engine/game.py:365`):
   se agrega `SPACE → ON_KEY_SHOOT`. Los juegos viejos no declaran
   `ON_KEY_SHOOT` y no se ven afectados.
7. **`Game.ejecutar_evento`** (`engine/game.py:152`) ya maneja
   `INCREASE_SCORE`, `DECREASE_SCORE`, `RESET_SCORE` y `GAME_OVER` y luego
   delega en `ejecutar_accion`. Tanks usa ese gancho para las balas y los
   tanques.

## 4. Gramática (`grammars/tanks.bnf`)

### 4.1 Producciones

```bnf
<programa>         ::= <tipo_juego> <grid> <definiciones> <opcional_niveles> <eventos>
<tipo_juego>       ::= "GAME_TYPE" "TANKS"
<grid>             ::= "GAME_GRID" "(" <numero> "," <numero> ")"
<definiciones>     ::= <definicion> | <definicion> <definiciones>
<opcional_niveles> ::= "" | <niveles>
<definicion>       ::= <definicion_shape> | <definicion_cancion> | <definicion_efecto>

<definicion_shape> ::= "DEFINE" "SHAPE" <identificador> <atributos> ":" <estados> "END"
<atributos>        ::= "" | <atributo> <atributos>
<atributo>         ::= "TYPE" ":"? <tipo_entidad>
                     | "HP" <numero> | "DAMAGE" <numero>
                     | "SPEED" <numero> | "FIRE_RATE" <numero>
                     | "HEAL" <numero> | "OWNER" <bando>
                     | "COLOR" <identificador> | "CHANCE" <numero> | "GEOMETRY" <identificador>
<tipo_entidad>     ::= "PLAYER" | "ENEMY" | "BULLET" | "WALL" | "PICKUP" | "BOSS"
<bando>            ::= "PLAYER" | "ENEMY"
<estados>          ::= <estado> | <estado> <estados>
<estado>           ::= "STATE" <numero> ":" <matriz>
<matriz>           ::= <fila> | <fila> <matriz>
<fila>             ::= "[" <valores_fila> "]"
<valores_fila>     ::= <numero> | <numero> "," <valores_fila>

<niveles>           ::= "LEVELS" ":" <elegir_nivel> <definiciones_nivel> "END"
<elegir_nivel>      ::= "" | "START" ":" <identificador>
<definiciones_nivel>::= <definicion_nivel> | <definicion_nivel> <definiciones_nivel>
<definicion_nivel>  ::= "LEVEL" <identificador> ":" <modificadores_nivel> "END"
<modificadores_nivel>::= "" | <modificador_nivel> <modificadores_nivel>
<modificador_nivel> ::= "TICK" <real> | "MUSIC" <identificador> | "WALLS" <numero>

<eventos>          ::= <evento> | <evento> <eventos>
<evento>           ::= "ON" <nombre_evento> ":" <acciones_tanque> "END"
<nombre_evento>    ::= "START" | "TICK"
                     | "KEY_UP" | "KEY_DOWN" | "KEY_LEFT" | "KEY_RIGHT" | "KEY_SHOOT"
                     | "PLAYER_HIT" | "EAT_HAMMER" | "ENEMY_DEFEATED"
                     | "BULLET_HIT_WALL" | "GAME_OVER"
                     | "TARGET_SCORE"   # reservado para B, se parsea pero nadie lo emite aun

<acciones_tanque>  ::= "" | <accion_tanque> <acciones_tanque>
<accion_tanque>    ::= "SPAWN" <identificador> "AT" <destino>
                     | "MOVE" "PLAYER" <direccion>
                     | "SHOOT" "PLAYER" | "HEAL" "PLAYER"
                     | "INCREASE_SCORE" <numero> | "DECREASE_SCORE" <numero>
                     | "RESET_SCORE" | "GAME_OVER"
                     | "PLAY_MUSIC" <identificador> | "PLAY_EFFECT" <identificador>
                     | "STOP_MUSIC"
<destino>          ::= "RANDOM" | "(" <numero> "," <numero> ")"
<direccion>        ::= "UP" | "DOWN" | "LEFT" | "RIGHT"

<definicion_cancion>::= "DEFINE" "SONG" <identificador> <extras_musica> ":" <cuerpo_cancion> "END"
<definicion_efecto> ::= "DEFINE" "EFFECT" <identificador> ":" <notas> "END"
# ... las mismas reglas de cancion/efecto que tetris.bnf y snake.bnf;
# el parser las comparte.
```

### 4.2 Atributos y defaults del motor

| Atributo | Aplica a | Significado | Default |
|---|---|---|---|
| `TYPE` | todas | rol de la entidad | — (obligatorio) |
| `HP` | `PLAYER`, `ENEMY`, `BOSS` | impactos que aguanta | jugador 3, enemigo 1 |
| `DAMAGE` | `BULLET` | HP que quita por impacto | 1 |
| `SPEED` | `ENEMY`, `BOSS` | celdas por segundo | 2 |
| `FIRE_RATE` | `ENEMY`, `BOSS` | segundos entre disparos | 3 |
| `HEAL` | `PICKUP` | HP que recupera el martillo | 1 |
| `OWNER` | `BULLET` | quién la dispara | obligatorio (`PLAYER`/`ENEMY`) |
| `COLOR` | todas | color de la matriz | `CYAN` |
| `CHANCE` | todas | peso en sorteo (sin uso actual en TANKS) | 10 |
| `GEOMETRY` | todas | reservado | `RECT` |

`TYPE` acepta `TYPE PLAYER` y `TYPE: PLAYER`. Las matrices de `PLAYER`,
`ENEMY`, `BOSS` y `WALL` deben ser **cuadradas y con al menos una celda
encendida**; las filas deben tener todas el mismo ancho.

Las compilaciones del `.brick` **no** almacenan los defaults: igual que los
niveles en Snake, el motor aporta sus propios valores. Un `.json` compilado
con `TYPE`/`HP`/etc. es válido para siempre; un `.json` viejo sin esos
atributos arranca en silencio en `BABY` como cualquier juego clásico.

### 4.3 Validación semántica (solo `GAME_TYPE TANKS`)

El compilador, al terminar `parse()`, comprueba:

1. Exactamente **una** forma con `TYPE PLAYER`.
2. Al menos **una** forma con `TYPE ENEMY`.
3. Al menos **una** forma con `TYPE BULLET` y `OWNER PLAYER`, y una con
   `OWNER ENEMY`.
4. Toda forma con `TYPE` en `(PLAYER, ENEMY, BOSS, WALL)` tiene matriz
   cuadrada; todas las filas de toda matriz tienen el mismo ancho; toda
   matriz tiene al menos una celda ≠ 0.
5. `HP`, `DAMAGE`, `SPEED`, `FIRE_RATE`, `HEAL` ≥ 1 cuando están presentes.
6. `TYPE` solo acepta `PLAYER | ENEMY | BULLET | WALL | PICKUP | BOSS`;
   `OWNER` solo `PLAYER | ENEMY`.

Cualquier violación detiene la compilación con un mensaje que dice qué
forma y qué regla. Los juegos `SNAKE`/`TETRIS` no pasan por esta validación.

### 4.4 Ejemplo (`games/tanks.brick`)

```
GAME_TYPE TANKS

GAME_GRID (15, 15)

# --- Tanque del jugador: verde, 3 de resistencia, huella 1x1 ---
DEFINE SHAPE JUGADOR TYPE PLAYER HP 3 COLOR GREEN:
  STATE 1: [1] END

# --- Enemigos normales: mueren de un impacto ---
DEFINE SHAPE ENEMIGO_BASICO TYPE ENEMY HP 1 SPEED 2 FIRE_RATE 3 COLOR RED:
  STATE 1: [1] END

DEFINE SHAPE ENEMIGO_RAPIDO TYPE ENEMY HP 1 SPEED 4 FIRE_RATE 2 COLOR ORANGE:
  STATE 1: [1] END

DEFINE SHAPE ENEMIGO_DURO   TYPE ENEMY HP 2 SPEED 1 FIRE_RATE 4 COLOR PURPLE:
  STATE 1: [1] END

DEFINE SHAPE BALA_JUGADOR TYPE BULLET OWNER PLAYER DAMAGE 1 COLOR CYAN:
  STATE 1: [1] END
DEFINE SHAPE BALA_ENEMIGA TYPE BULLET OWNER ENEMY  DAMAGE 1 COLOR YELLOW:
  STATE 1: [1] END

DEFINE SHAPE MURO       TYPE WALL   COLOR GRAY:   STATE 1: [1] END
DEFINE SHAPE MARTILLO   TYPE PICKUP HEAL 1 COLOR YELLOW: STATE 1: [1] END

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
END

ON KEY_UP:    MOVE PLAYER UP    END
ON KEY_DOWN:  MOVE PLAYER DOWN  END
ON KEY_LEFT:  MOVE PLAYER LEFT  END
ON KEY_RIGHT: MOVE PLAYER RIGHT END
ON KEY_SHOOT: SHOOT PLAYER      END

ON ENEMY_DEFEATED:
  INCREASE_SCORE 100
  SPAWN ENEMIGO_BASICO AT RANDOM
END

ON EAT_HAMMER:
  HEAL PLAYER
  SPAWN MARTILLO AT RANDOM
END

ON GAME_OVER:
  PLAY_EFFECT MORIR
END
```

El `.brick` real incluye un tema corto (`DEFINE SONG TANK_TEMA`, sin voces
dobles) y tres efectos (`DEFINE EFFECT DISPARO`, `IMPACTO`, `MORIR`) sobre
el motor de audio que ya existe. Son la misma técnica que Tetris y Snake, no
algo nuevo del lenguaje.

## 5. Motor (`engine/tanks.py`)

Hereda de `Game` y no modifica su comportamiento para los demás juegos.

### 5.1 Estado inicial

`inicializar_estado()`:

- `jugador`: dict `{nombre, x, y, hp, max_hp, orientacion (dx,dy), cooldown}`.
  `x, y` = esquina superior izquierda; se crea en `SPAWN PLAYER`.
- `enemigos`: lista de dicts `{nombre, x, y, hp, max_hp, direccion (dx,dy),
  tiempo_movimiento, tiempo_disparo}`.
- `balas`: lista de dicts `{x, y, dx, dy, dueno, dano, color}`.
- `martillo`: posición `(x, y)` o `None`.
- `velocidad_gravedad = 0.12` (default si el nivel no trae `TICK`).
- `marco_score` recibe `label_vida` ("VIDA 3/3"), verde y rojo con 1.

### 5.2 Orden de un tick

`Tanks.ejecutar_evento` sobreescribe el de `Game`: cuando llega `ON_TICK`,
ejecuta `avanzar_mundo()` primero y luego el `ON_TICK` del `.brick`:

1. **Balas.** Cada bala avanza 1 celda. Si se sale del tablero se elimina.
   Si la celda destino es un muro, el muro se borra y la bala también;
   emite `ON_BULLET_HIT_WALL`. Si la celda destino ocupa al
   jugador (bala enemiga) o a un enemigo (bala del jugador), aplica
   `DAMAGE`; la bala se elimina.
2. **Enemigos — movimiento.** Cada enemigo acumula
   `tiempo_movimiento += tick`; al alcanzar `1 / SPEED` se descuenta y se
   intenta mover 1 celda en su dirección. Si el destino está ocupado por
   muro, borde, otro enemigo o el jugador, rota 90° a la derecha y lo
   intenta de nuevo en el mismo paso; si sigue bloqueado, rota otra vez;
   si no hay salida, se queda este tick. (Las celdas ocupadas se validan
   sobre la matriz completa, no sobre la esquina.)
3. **Enemigos — disparo.** Cada enemigo acumula
   `tiempo_disparo += tick`; al alcanzar `FIRE_RATE` se descuenta y se
   dispara. Si el jugador está en su misma fila o columna, la bala sale en
   ese eje; si no, en la dirección actual. Las balas enemigas también
   destruyen muros.
4. **`ON_TICK` del `.brick`**, que puede quedar vacío o usarse para otra cosa.

### 5.3 Acciones del `.brick`

`Tanks.ejecutar_accion` reconoce:

| Acción | Efecto |
|---|---|
| `SPAWN <FORMA> AT (x, y)` | coloca la forma del tipo correspondiente (jugador, enemigo, martillo, muro) con su matriz anclada en `(x, y)`. Si es un `PLAYER`/`ENEMY`, borra los muros bajo la matriz. Si no cabe o se superpone, se ignora |
| `SPAWN <FORMA> AT RANDOM` | igual, en celda libre sorteada con `random.randint` (sin modificar `random`) |
| `MOVE PLAYER <DIR>` | instancia o reutiliza al jugador; orienta el cañón a `<DIR>` y avanza 1 celda si la matriz completa cabe sin chocar con muro/borde/enemigo |
| `SHOOT PLAYER` | dispara si `cooldown == 0`; queda `cooldown = 0.3` s (descontado en cada tick). La bala del jugador aparece en la celda inmediatamente delante de la cara frontal de la matriz, centrada en ella; si esa celda es muro, lo destruye y la bala desaparece |
| `HEAL PLAYER` | `hp = min(max_hp, hp + HEAL de la forma TYPE PICKUP que existe (la primera declarada si hay varias)` |
| `SPAWN MARTILLO AT RANDOM` | coloca el martillo en una celda libre |

### 5.4 Muros

Al empezar la partida (`iniciar_partida`, no en `__init__`, para no flotar
sobre el selector de niveles) se generan `WALLS n` celdas de muro en
posiciones libres, `random.randint` + fallback determinista a la primera
libre si el azar insiste. Los muros son `grid[y][x] ≠ 0`, así que reutilizan
el dibujo y la colisión actuales. `color_celda_grid` devuelve el color de la
forma `TYPE WALL` (gris, `#808080`).

### 5.5 Martillo

Si la matriz del jugador cubre la celda del martillo: se heala, se emite
`ON_EAT_HAMMER` y, **solo si el evento no reapareció ya el martillo**, el
motor lo coloca en otra celda libre (mismo patrón que Snake con la comida).
Se dibuja como un icono 1 celda (mango + cabeza) en el color de la forma.

### 5.6 Eventos emitidos por el motor

| Evento | Cuándo |
|---|---|
| `ON_EAT_HAMMER` | el jugador recoge el martillo |
| `ON_PLAYER_HIT` | una bala enemiga baja la vida del jugador |
| `ON_ENEMY_DEFEATED` | una bala del jugador deja al enemigo en `HP 0` |
| `ON_BULLET_HIT_WALL` | cualquier bala destruye un muro |
| `ON_GAME_OVER` | una vez, cuando `hp ≤ 0` (lo dispara `game_loop` de `Game`) |

`ON_TARGET_SCORE` se declara en la gramática y el lexer ya la acepta, pero
nada la emite. Reservado para Actividad 5B.

### 5.7 Entrada

`Game.manejar_tecla` mapea `SPACE` a `ON_KEY_SHOOT`. Las flechas siguen
funcionando como antes en Snake y Tetris. En TANKS:

- Flechas: `MOVE PLAYER <DIR>` + orientan el cañón.
- Espacio: `SHOOT PLAYER`.

### 5.8 Dibujo

`dibujar_elementos`: hammer → enemigos (matriz rotada, su color) → balas
(rectángulo con núcleo brillante) → jugador (matriz rotada, su color). La
pantalla conserva el panel lateral, `label_score` y `label_vida`. Se
respeta `canvas` de la misma forma que Snake/Tetris; no hay ventana nueva.

## 6. Archivos

**Nuevos**

- `games/tanks.brick`
- `grammars/tanks.bnf`
- `engine/tanks.py`
- `tests/test_tanks.py`

**Editados (cambios quirúrgicos)**

- `compiler.py` — tabla `ATRIBUTOS_SHAPE` y función `validar_tanques()` (solo `GAME_TYPE TANKS`).
- `engine/__init__.py` — `from .tanks import Tanks`, registro `'TANKS': Tanks`, `__all__`.
- `engine/game.py` — `manejar_tecla` mapea `SPACE` a `ON_KEY_SHOOT`.
- `engine/utilidades.py` — color `GRAY = "#808080"`.
- `tests/test_compiler.py` — atributos y validación TANKS.
- `tests/test_juegos.py` — `crear_juego` registra TANKS.
- `docs/Guia-BrickScript.txt` — sección TANKS.
- `docs/cambios/tanks_changes.txt` — registro de cambios + `APORTES POR INTEGRANTE` (huecos para los 4).
- `docs/README.md` — checkbox Actividad 5 y enlace al `tanks_changes.txt`.

## 7. Tests y verificación

`tests/test_tanks.py` (tablero 8×8, `random.seed(1234)`):

1. Compila `games/tanks.brick`: `tipo_juego`, atributos de forma, niveles.
2. `SPAWN PLAYER` con HP 3 crea al jugador y las teclas orientan y mueven.
3. El jugador no atraviesa muros/bordes.
4. `SHOOT PLAYER` crea una bala delante; la bala avanza sola en `ON_TICK`;
   `cooldown` evita spam.
5. Bala del jugador destruye muro antes de morir.
6. Bala del jugador contra enemigo: baja `HP`, la bala desaparece; `HP 0`
   elimina al enemigo, emite `ON_ENEMY_DEFEATED` y aplica el `.brick`.
7. Bala enemiga contra jugador baja la vida; `HP 0` termina la partida y es
   `ON_GAME_OVER` una sola vez.
8. Martillo: heala hasta 3 y reaparece (guard del evento).
9. IA: enemigo se mueve solo; choca con muro y gira; con jugador alineado en
   la fila/columna dispara en ese eje; con jugador desalineado dispara en su
   dirección.
10. Cinco teclas aleatorias × 300 frames no cuelgan ni rompen (equivalente a
    `TestJuegosReales.test_games_brick`).

Más:

- `tests/test_compiler.py`: `TYPE`/`HP`/`DAMAGE`/`SPEED`/`FIRE_RATE`/`HEAL`/
  `OWNER` se parsean; `TYPE: PLAYER` y `TYPE PLAYER` funcionan; TANKS sin
  jugador, con dos jugadores, sin bala propia o con matriz no cuadrada fallan
  al compilar con el mensaje esperado.
- `tests/test_juegos.py`: `crear_juego({'tipo_juego': 'TANKS', ...})` es
  instancia de `Tanks` y `JUEGOS['TANKS']` existe.
- Verificación local:
  `cmd /c "C:\Python27\python.exe -u -m unittest discover -s tests -t . -v"`
  → mismos 2 fallos preexistentes, resto verde. En py2.7: sin f-strings,
  sin dicts ordenados (para el menú se usa la lista `levels`).
- Retrocompatibilidad: no se edita `games/snake.brick`, `games/tetris.brick`,
  `tests/test_retrocompatibilidad.py`, ni el md5 dorado de `TEMA_NYAN`;
  `tanks.brick` con `GAME_TYPE TANKS` no colisiona con el filtro
  `('reborn','remake')`.

## 8. Fuera de esta entrega

| Ítem | Entrega |
|---|---|
| Jefe final: `TYPE BOSS` grande, `HP 20`, más daño | 5B |
| Transición por puntaje (`ON TARGET_SCORE` → `SPAWN` jefe), pantalla de victoria | 5B |
| Balas del jefe y su resistencia | 5B |
| Vida extra / drops de enemigos | 5B+ |

## 9. Riesgos principales

- **IA que se atasca:** si cada paso falla y rota, tras 4 rotaciones siempre
  hay una dirección libre o se queda quieto — no hay bucle infinito.
- **Spawn aleatorio del martillo en bucle:** se usa el mismo patrón que Snake
  (lista de libres + muestreo acotado).
- **Muros que tapan al jugador:** los `SPAWN` borran los muros bajo la matriz.
- **`test_games_brick` más lento:** el fuzz corre 300 frames; Tanks mueve
  enemigos/balas por acumuladores de `SPEED`, no por buscar rutas, así que no
  se dispara el tiempo de test.
- **CI con `python:2.7.18`:** la validación TANKS vive en el parser, debe ser
  compatible con ella (nada de `dict` para seguir el orden de las formas: se
  itera la lista de tuplas).
