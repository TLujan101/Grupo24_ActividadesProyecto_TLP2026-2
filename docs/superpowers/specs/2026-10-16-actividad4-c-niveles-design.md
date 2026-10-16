# Actividad 4 — Sección C: Niveles de dificultad desde la gramática

**Fecha:** 2026-10-16
**Alcance:** solo la sección C de la Actividad 4. Las secciones A, B y D se
construyen encima de esta y se detallan al final.

## 1. Por qué C va primero

La Actividad 4 tiene cuatro secciones y tres de ellas dependen de esta:

| Sección | Depende de C |
|---------|--------------|
| A. Personalización geométrica | Sí — el enunciado dice "Cabeza Especial (**Nivel Nyan Cat**)", y el nivel tiene que poder *elegir* la geometría |
| B. Frutas y obstáculos | Sí — "No existen frutas venenosas ni obstáculos" (Baby), "se activan" (Entusiasta), "incluye nubes" (Nyan). B es una tabla de qué habilita cada nivel |
| D. Retrocompatibilidad | Sí — "asignar el nivel Baby por defecto si no se encuentra la etiqueta de niveles" es una regla de esta sección |

Además hay un acoplamiento concreto: si el bloque `LEVELS` no puede *nombrar*
una configuración, la sección A quedaría con una geometría global única y el
nivel Nyan no podría tener cabeza de gato mientras Baby conserva el rectángulo.

## 2. Decisiones tomadas

| Decisión | Alternativas descartadas | Motivo |
|----------|--------------------------|--------|
| Orden: C → A → B → D | A primero | A se implementaría dos veces: primero estática y luego por nivel |
| El `.brick` elige el nivel inicial + el jugador puede cambiarlo con teclas | progresión por puntuación; un archivo por nivel | "Multinivel" aquí significa *elegir*, no *subir solo*. La progresión metería reglas de balance en la gramática |
| Menú dibujado en el canvas, **solo si hay 2+ niveles** | menú siempre; selector por consola | Sin menú, `snake.brick` recorre el flujo de hoy sin ramas especiales. El menú no bloquea los tests |
| El `.brick` declara el comportamiento; el motor no conoce nombres de nivel | perfiles hardcodeados (`if nivel == 'NYAN_CAT'`) | El punto D se cumple por construcción: sin `LEVELS` la configuración queda vacía y cada modificador ausente toma su default |
| `TICK` en segundos con decimales | `TICK_MS` en milisegundos | Una sola unidad en todo el lenguaje: `velocidad_gravedad` ya está en segundos |

## 3. Restricciones del lenguaje actual (verificadas)

Tres cosas del compilador actual condicionan el diseño. No son suposiciones:
están comprobadas contra el código.

1. **El lexer solo tokeniza identificadores en mayúsculas.**
   `token_regex = r'\b[A-G][0-9]+\b|\b[A-Z_]+\b|\d+|[\[\](),:]'` (`compiler.py:15`).
   `LEVEL Enthusiasta:` falla con *"Caracteres no reconocidos"*. Los nombres de
   nivel deben ser `BABY`, `ENTUSIASTA`, `NYAN_CAT` (el `_` sí está en la clase).

2. **El lexer no acepta decimales.** `\d+` no captura el punto, así que
   `TICK 0.15` falla con *"Caracteres no reconocidos: '.'"*. Todo el lenguaje
   hoy es entero (`GAME_GRID (18, 18)`, `CHANCE 10`, duraciones de nota).
   Se extiende el lexer (sección 5).

3. **`#` abre comentario** (`codigo_fuente = re.sub(r'#.*', '', ...)`).
   Por eso los colores hexadecimales no pueden vivir en el `.brick`; la paleta
   del nivel Nyan (sección A) irá en el motor.

## 4. Gramática

### 4.1 Sintaxis

```
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
```

### 4.2 Producciones BNF

Se agregan a `grammars/snake.bnf` y `grammars/tetris.bnf` (el parser es
compartido, así que la regla sirve para los dos juegos):

```
<programa>       ::= <tipo_juego> <grid> <definiciones> <opcional_niveles> <eventos>
<opcional_niveles> ::= "" | <niveles>
<niveles>          ::= "LEVELS" ":" <elegir_nivel> <definiciones_nivel> "END"
<elegir_nivel>     ::= "" | "START" ":" <identificador>
<definiciones_nivel> ::= <definicion_nivel> | <definicion_nivel> <definiciones_nivel>
<definicion_nivel> ::= "LEVEL" <identificador> ":" <modificadores_nivel> "END"
<modificadores_nivel> ::= <modificador_nivel> | <modificador_nivel> <modificadores_nivel>
<modificador_nivel> ::= "TICK" <real>
<real>    ::= <numero> | <numero> "." <numero>
```

`<opcional_niveles> ::= "" | ...` sigue el estilo de `<extras>` que ya usa
`tetris.bnf:10`.

**`<modificador_nivel>` es una unión que crece.** Hoy tiene un solo miembro
(`TICK`). La sección A le agrega `GEOMETRY` y la B, `POISON` / `CLOUDS` /
`INVULNERABLE`. Ninguna de las dos toca el esqueleto de la gramática.

`<real>` se escribe como `<numero> "." <numero>` por claridad de la regla, pero
el lexer entrega `0.15` como **un solo token**; por eso el parser usa un
consumidor de float, no el `consumir_numero()` entero que existe hoy.

**Arreglo de deriva:** `snake.bnf:8` documenta
`"DEFINE" "SHAPE" <identificador> ":" <estados> "END"`, pero el compilador ya
soporta `COLOR` y `CHANCE` desde la Actividad 3 (`tetris.bnf:9-10`). Se agrega
`<extras>` a `snake.bnf` para documentar lo que ya existe.

## 5. Compilador (`compiler.py`)

### 5.1 Lexer

Un solo cambio:

```python
token_regex = r'\b[A-G][0-9]+\b|\b[A-Z_]+\b|\d+(?:\.\d+)?|[\[\](),:]'
```

Los enteros de siempre no cambian. `GAME_GRID (18, 18)` seguiría dando dos
tokens `18`; `GAME_GRID (18.5, 18)` ahora da un token `18.5` y `consumir_numero()`
falla con el mensaje *"se esperaba un numero pero se encontro '18.5'"*, que es
mejor que *"Caracteres no reconocidos: '.'"*.

### 5.2 Parseo

`parse()` reconoce el token `LEVELS` a nivel superior y llama a
`parsear_niveles()`. Como el parser es un despachador de tokens, el bloque
funciona en cualquier posición del archivo; la BNF muestra el orden canónico,
igual que ya lo hace la gramática existente para `GAME_GRID` y `DEFINE`.

`parsear_niveles()`: consume `LEVELS` y `:`, luego `START : <nombre>` si está
(primero, según la gramática), luego la secuencia de `LEVEL ... END` hasta el
`END` del bloque.

### 5.3 AST producido

`levels` es una **lista**, no un diccionario. La razón es el orden: el menú
numerado depende del orden de declaración, y en **Python 2.7 —el intérprete
que declara el proyecto— un diccionario no lo conserva**.

```
Declarado en el .brick:  NYAN_CAT, BABY, ENTUSIASTA
json.load en py2.7   ->  [BABY, NYAN_CAT, ENTUSIASTA]   <- desordenado
json.load en py3.14  ->  [NYAN_CAT, BABY, ENTUSIASTA]   <- correcto
```

Con un diccionario, el menú mostraría los niveles en un orden que el autor del
`.brick` no puede predecir y la tecla `2` elegiría un nivel arbitrario. Como
array JSON, el orden sobrevive en las dos versiones de Python.

```json
"config": { "grid_size": [18, 18], "start_level": "NYAN_CAT" },
"levels": [
  {"nombre": "BABY", "tick": 0.15},
  {"nombre": "ENTUSIASTA", "tick": 0.10},
  {"nombre": "NYAN_CAT", "tick": 0.06}
]
```

`start_level` va en `config` porque es configuración de la partida, igual que
`grid_size`. `levels` es una clave nueva al nivel del AST, **siempre presente**.
El precio de usar lista es que el motor tiene que buscar por nombre en vez de
indexar; son tres o cuatro niveles, un recorrido lineal no tiene costo.

### 5.4 Nivel por defecto (punto D)

Cuando el `.brick` no declara `LEVELS`, el compilador emite igualmente:

```json
"config": { "grid_size": [18, 18], "start_level": "BABY" },
"levels": [ {"nombre": "BABY"} ]
```

El nivel existe y es el inicial. Esto **materializa el nombre, no los valores**:
el compilador es un solo programa para Tetris y Snake, y sus ticks por defecto
son distintos (0.4 y 0.15), así que un `tick`materializado en el compilador
haría que Tetris arrancara a 0.15. El default de un modificador vive en el
juego, no en la gramática.

### 5.5 Validaciones

Fallar temprano y con mensaje claro, nunca ignorar en silencio:

| Caso | Mensaje |
|------|---------|
| `START: X` sin `LEVEL X` declarado | `el nivel inicial 'X' no esta definido` |
| Nombre de nivel repetido | `el nivel 'X' esta definido dos veces` |
| `LEVELS:` sin ningún nivel | `LEVELS no declara ningun nivel` |
| `TICK` con valor <= 0 | `TICK del nivel 'X' debe ser mayor que 0` |
| Modificador desconocido | `modificador desconocido 'TIC' en el nivel 'X'` |

La última es la más importante: sin ella un typo pasa desapercibido y el nivel
arranca con el default sin que nadie entienda por qué.

## 6. Motor (`engine/game.py`)

El motor **nunca compara contra un nombre de nivel**. Solo lee el diccionario
de configuración del nivel activo.

### 6.1 Un solo camino

```python
def aplicar_nivel(self):
    if 'tick' in self.nivel_config:
        self.velocidad_gravedad = self.nivel_config['tick']
```

El juego deja su valor por defecto en `inicializar_estado()`; el nivel lo pisa
solo si lo declara. Tetris conserva 0.4, Snake conserva 0.15, y
`NYAN_CAT TICK 0.06` pisa el que sea. Los modificadores que no tengan un
default natural en el juego (la geometría de la sección A) se leerán con
`self.nivel_config.get('geometry', 'RECT')`.

### 6.2 Estado nuevo en `Game`

| Atributo | Valor |
|----------|-------|
| `self.niveles` | `datos_juego.get('levels') or []` — **lista** de dicts con `nombre` (ver 5.3) |
| `self.nivel_actual` | `config.get('start_level') or NIVEL_POR_DEFECTO`, un nombre |
| `self.nivel_config` | el dict del nivel activo, `{}` si no está |
| `self.iniciado` | `True` cuando `ON_START` ya corrió |

`NIVEL_POR_DEFECTO = 'BABY'` es **solo una etiqueta** para la interfaz: no lleva
comportamiento asociado.

Como `levels` es una lista, el motor no indexa por nombre: `Game` expone
`config_de_nivel(nombre) -> dict`, que recorre la lista y devuelve `{}` si no
encuentra el nombre. El menú, en cambio, la recorre en orden, que es justo lo
que se necesita para numerar `1..N`.

**Duplicación conocida:** la cadena `'BABY'` aparece en `compiler.py` (el
nombre que el compilador inventa cuando el `.brick` no dice nada) y en
`engine/game.py` (el nombre que el motor asume cuando el JSON no lo dice). Son
dos capas con dos preguntas distintas, y no hay un módulo compartido razonable:
el compilador no debe importar de `engine/` (arrastraría Tkinter al proceso de
compilación). Ambas constantes van comentadas como etiqueta, sin comportamiento.

### 6.3 Flujo de arranque

Hoy `__init__` dispara `ON_START` siempre (`game.py:76`). Con el menú hay que
separar "montar el juego" de "empezar la partida":

```
__init__        -> inicializar_estado()      cada juego deja sus defaults
                   aplicar_nivel()            el nivel inicial pisa los defaults
                   ¿hay 2+ niveles?
                       no -> iniciar_partida()   corre ON_START
                       si -> queda esperando el menú (todavía no corre ON_START)

run()           -> ¿menú abierto? dibuja el menú y NO programa el loop
                   ¿no?          after(50, game_loop)

manejar_tecla   -> ¿menú abierto? una tecla 1..N elige nivel, corre ON_START
                                y programa el loop. Las demás teclas se ignoran.
                   ¿no?          las flechas disparan ON_KEY_* como hoy
```

`snake.brick` (sin `LEVELS`) recorre exactamente el camino de hoy: un solo
nivel → sin menú → `ON_START` en `__init__` → `run()` programa el loop. Por eso
`tests/test_retrocompatibilidad.py` y `tests/test_game.py` no se rompen.

### 6.4 Lectura defensiva

El runtime usa `.get()`, no `[]`, aunque el compilador siempre emita la clave.
Dos motivos concretos, no paranoia:

- `games/*.json` está en `.gitignore` pero hay JSON compilados por la versión
  anterior del compilador en el disco (`games/tetris.json`,
  `games/tetris_reborn.json`). No tienen la clave `levels`.
- `tests/test_juegos.py:31` fabrica juegos a mano con
  `{'config': {}, 'shapes': ..., 'events': {}}`.

### 6.5 El menú

Textos sobre el canvas existente, sin ventana nueva:

```
   ELIGE NIVEL
   [1] BABY         TICK 0.15
   [2] ENTUSIASTA   TICK 0.10
   [3] NYAN_CAT     TICK 0.06   <- inicio
```

Las teclas `1`..`N` eligen por posición en el orden de declaración, que es el
orden de la lista del AST (5.3). Un `.brick` puede declarar más de nueve
niveles sin cambiar el motor, pero solo los primeros nueve son alcanzables con
una tecla.

Si un nivel no declara `TICK`, el menú **omite la línea del tick** en vez de
inventar un valor: el default lo aporta el juego, no el menú.

## 7. `games/snake_remake.brick`

`snake_remake.brick` y `snake.brick` son idénticos byte a byte hoy. El archivo
`snake_remake.brick` es la ranura de la versión nueva y ya está excluido de
`tests/test_retrocompatibilidad.py:15` (`VARIANTES_NUEVAS = ('reborn', 'remake')`).
La separación queda:

- `games/snake.brick` — **intocable**. Es la prueba viviente de que el `.brick`
  original sigue funcionando.
- `games/snake_remake.brick` — lleva el bloque `LEVELS`.

En esta sección los tres niveles se diferencian **solo en el tick**. Se
documenta con comentarios que las frutas, las nubes y la geometría llegan en B
y A, para que no parezca un bloque de adorno.

## 8. Tests (se escriben antes que el código)

| Archivo | Qué cubre |
|---------|-----------|
| `tests/test_compiler.py` *(nuevo)* | El lexer acepta `0.15` como un token y los enteros no cambian. `LEVELS` produce el AST esperado; `START` se lee primero. Sin `LEVELS` sale `[{'nombre': 'BABY'}]`. Las 5 validaciones con su mensaje. El bloque parsea en distintas posiciones del archivo |
| `tests/test_game.py` | `nivel_actual` / `nivel_config` salen de los datos; un dict **sin** `levels` no revienta. `aplicar_nivel()` solo pisa si hay `tick`. Con 2+ niveles `run()` dibuja el menú y no programa el loop; con menos, sí (el test de `game.py:88` sigue pasando sin tocarse). La tecla `2` elige nivel, corre `ON_START` y arranca el loop; con el menú abierto las flechas y los dígitos fuera de rango se ignoran |
| `tests/test_snake.py` | Snake con nivel `TICK 0.06` → `velocidad_gravedad == 0.06`; sin nivel → `0.15`. **`test_dibujar_comida_y_serpiente` no se toca**: es la prueba de que el camino por defecto quedó idéntico |
| `tests/test_retrocompatibilidad.py` | `snake.brick` compila a `start_level == 'BABY'` y `levels == [{'nombre': 'BABY'}]`, y su partida sigue igual. Un JSON viejo sin `levels` todavía arranca |
| `tests/test_juegos.py` | `snake_remake.brick`: sin elegir nivel la partida no arranca; al pulsar `2` aparecen la serpiente y la comida |

`tests/tk_falso.py` necesita `create_text` en el canvas falso para poder
afirmar el menú. La sección A necesitará además `create_oval` y
`create_polygon`, pero eso se agrega en A.

## 9. Fuera de alcance

- `GEOMETRY`, círculos, triángulos, cabeza de gato, cola multicolor → sección A
- Frutas venenosas, nubes, power-up de invulnerabilidad → sección B
- Cambiar de nivel a mitad de partida. El menú solo existe antes de empezar
- Progresión automática por puntuación
- Poner `LEVELS` en `tetris.brick`. Tetris no lo necesita en esta actividad

## 10. Archivos tocados y orden de los commits

Trabajo directo en `main`, un commit por paso:

1. `compiler.py` (lexer con decimales) + `tests/test_compiler.py`
2. `compiler.py` (`parsear_niveles` + validaciones) + tests
3. `grammars/snake.bnf` + `grammars/tetris.bnf`
4. `engine/game.py` (niveles + menú) + `tests/test_game.py` + `tests/tk_falso.py`
5. `engine/snake.py` (aplicar el tick del nivel) + `tests/test_snake.py`
6. `games/snake_remake.brick` + `tests/test_juegos.py` + `tests/test_retrocompatibilidad.py`
7. `docs/Guia-BrickScript.txt`

**Restricción de versión:** el repo declara Python 2.7 (`README.md:7`,
`compiler.py:1`). El código nuevo debe ser compatible con 2.7 *y* con 3.x:
`.format()` o `%`, sin f-strings, sin `super()` sin argumentos.

**No tocar:** `games/tetris_reborn.brick` tiene un cambio sin commitear
(estados 3 y 4 de la pieza I) que pertenece a otro trabajo. No debe entrar en
ningún commit de esta sección.

## 11. Cómo continues A, B y D sobre esta base

- **A.** `<modificador_nivel> ::= ... | "GEOMETRY" <identificador>` y el
  círculo/triángulo se dibujan leyendo `self.nivel_config.get('geometry', 'RECT')`.
  La paleta multicolor del Nyan vive en el motor (el `#` abre comentario en el
  `.brick`, sección 3.3) y se asigna por segmento con `i % len(paleta)`.
- **B.** `<modificador_nivel> ::= ... | "POISON" | "CLOUDS" | "INVULNERABLE" <real>`
  y las entidades se consultan con `.get()` sobre `self.nivel_config`.
- **D.** El análisis de retrocompatibilidad tiene su evidencia principal en
  `tests/test_retrocompatibilidad.py`, que ya se extiende en la sección 8.

## 12. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| El cambio del lexer rompe Tetris o las notas | Los enteros no cambian; `test_juegos.py` compila y corre los cuatro `.brick` de `games/` |
| La rama de Tetris tiene trabajo sin commitear | No se incluye en ningún commit (sección 10) |
| El menú deja el juego colgado si el jugador no pulsa nada | Las teclas 1..N son la única forma de avanzar; documentado en la guía |