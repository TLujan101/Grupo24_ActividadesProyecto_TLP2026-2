# Cómo funciona la música programada en el `.brick`

Este documento explica, sin dar por sentado nada, cómo una nota escrita en un
archivo `.brick` termina sonando por los parlantes. Está pensado para que
alguien que nunca vio el sistema pueda seguirlo de arriba abajo.

---

## 1. La idea en una frase

La música **no es un archivo de audio**: es código. Se escribe una partitura en
el `.brick`, el compilador la traduce a números y el sintetizador genera la onda
de sonido con matemáticas.

Por eso el juego no trae ningún `.mp3` ni ningún `.wav`: todo sale de ahí.

---

## 2. El flujo completo

```
  ┌──────────────────┐
  │ tetris_reborn    │   ← Lo escribe la persona
  │    .brick        │      DEFINE SONG ... NOTE E5 440 ...
  └────────┬─────────┘
           │  compiler.py
           ▼
  ┌──────────────────┐
  │ tetris_reborn    │   ← Notas ya en Hercios: [659.3, 440]
  │     .json        │      El runtime solo necesita números
  │  "songs": {...}  │
  └────────┬─────────┘
           │  tracker.py
           ▼
  ┌──────────────────┐
  │   PCM crudo      │   ← La onda, muestra por muestra, en RAM
  │  (620 KB)        │      NO es un archivo
  └────────┬─────────┘
           │  audio.py
           ▼
  ┌──────────────────┐
  │ parlantes 🔊     │   ← Por tubería en Linux, por MCI en Windows
  └──────────────────┘
```

Cada etapa tiene una sola responsabilidad. Las cuatro son:

| Archivo | De qué se ocupa |
|---|---|
| `compiler.py` | Traduce la notación musical a números |
| `tracker.py` | Genera la onda de sonido y la guarda en RAM |
| `audio.py` | Manda el audio a los parlantes |
| El `.brick` | Decide **cuándo** suena cada cosa |

---

## 3. Etapa 1: escribir la música

Dentro de un `.brick` las canciones se declaran con `DEFINE SONG` y cada nota
lleva **nombre** y **duración en milisegundos**:

```
DEFINE SONG TETRIS_TEMA_A:
    NOTE E5 440
    NOTE B4 220
    NOTE C5 220
    NOTE D5 440
END
```

Se lee así: *mi en mi (E5) durante 440 ms, si en si (B4) durante 220 ms...*

Los efectos son iguales pero con otra palabra clave, `DEFINE EFFECT`. La
diferencia es de comportamiento: una canción **suena en bucle**, un efecto
**suena una vez** y no corta la música:

```
DEFINE EFFECT BEEP_LINEA:
    NOTE A5 60
    NOTE E6 120
END
```

Y el `.brick` decide cuándo se dispara cada uno:

```
ON START:
  SPAWN RANDOM_SHAPE
  PLAY_MUSIC TETRIS_TEMA_A
END

ON LINE_CLEAR:
  INCREASE_SCORE 100
  PLAY_EFFECT BEEP_LINEA
END
```

Esto último es lo bonito del diseño: **el motor no sabe qué sonidos existen**.
Solo entiende `PLAY_MUSIC`, `PLAY_EFFECT` y `STOP_MUSIC`, igual que entiende
`MOVE` o `INCREASE_SCORE`. Si el `.brick` pide un sonido que no existe, el juego
no se rompe: simplemente suena mudo.

---

## 4. Etapa 2: el compilador traduce nota → Hercios

Aquí está la primera decisión de diseño. El `.brick` pide `E5`, que es un nombre
de nota musical. Pero un programa no entiende de música: entiende de números.
Entonces el compilador hace la traducción.

La cuenta es la afinación estándar (fórmula MIDI):

```python
NOTAS_SEMITONO = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

def nota_a_hz(self, letra, octava):
    midi = 12 * (octava + 1) + self.NOTAS_SEMITONO[letra]
    return round(440.0 * (2.0 ** ((midi - 69) / 12.0)), 1)
```

Y así queda:

| En el `.brick` | En el `.json` |
|---|---|
| `A4` | 440.0 Hz |
| `C5` | 523.3 Hz |
| `E5` | 659.3 Hz |
| `E6` | 1318.5 Hz |

(A4 = 440 Hz es la definición de afinación; de ahí sale toda la tabla.)

El `.json` resultante guarda cada nota como un par `[Hz, ms]`:

```json
"songs": {
  "TETRIS_TEMA_A": {
    "notas": [[659.3, 440], [493.9, 220], [523.3, 220]]
  }
}
```

Eso es **todo** lo que el runtime necesita saber. A partir de aquí nadie vuelve
a mirar el nombre de la nota.

### Un detalle del lexer

Para que `E5` llegue entero al parser hubo que tocar el lexer, porque `E5` no es
una palabra ni un número:

```python
token_regex = r'\b[A-G][0-9]+\b|\b[A-Z_]+\b|\d+|[\[\](),:]'
```

La primera alternativa, `\b[A-G][0-9]+\b`, existe **solo** para las notas.
Sin ella, `E5` se partía en `E` y `5`, y la nota se colaba como texto no
reconocido.

---

## 5. Etapa 3: el sintetizador (donde vive la música en RAM)

`tracker.py` recorre las notas y genera la onda. Dos decisiones importantes aquí.

### Decisión A: guardar en RAM, no en disco

La versión anterior de este proyecto (rama `experimento-audio-ram`) escribía un
`.wav` en la carpeta temporal del sistema y usaba ese archivo como caché. Lo
cambiamos por un diccionario en memoria:

```python
_CACHE = {}

def cancion_pcm(nombre, notas):
    firma = firma_partitura(notas)
    if firma in _CACHE:
        return _CACHE[firma]
    pcm = sintetizar(notas)
    _CACHE[firma] = pcm
    return pcm
```

La `firma` es el MD5 de la partitura. Eso da dos cosas gratis:

- Si editas una nota, cambia el MD5 y se sintetiza la canción nueva sola.
- Si dos canciones tienen exactamente las mismas notas, comparten el mismo
  bloque de memoria.

**¿Por qué es mejor que la caché en disco?** Porque la caché en disco existía
por una única razón técnica: el reproductor de Windows (MCI) solo sabe abrir
rutas de archivo. En Linux nunca hizo falta, y en Windows sigue siendo un
detalle del transporte, no del diseño. El audio es un dato computado, no un
recurso externo.

### Decisión B: sintetizar de golpe, no "en tiempo real"

Una idea que se nos ocurrió y **descartamos** era generar el sonido mientras
suena, nota a nota, sin esperarlo entero ("en tiempo real"). La medimos:

```
Canción: TETRIS_TEMA_A
  notas: 37 | duración: 14.08 s | muestras: 310464
  SÍNTESIS: 0.558 s
  CACHE HIT: 0.0130 s
```

**La síntesis es 25 veces más rápida que el tiempo que dura la música.** O sea,
sobra presupuesto de CPU de sobra. No hay ninguna presión que justifique
complicar el código para ahorrar medio segundo que nadie nota.

Y encima el streaming traería un problema extra. La normalización del volumen
necesita conocer **todas** las muestras antes de escalar:

```python
pico = max([abs(m) for m in muestras] + [1e-9])
factor = (32767.0 * PICO) / pico
```

Un sintetizador en streaming necesitaría dos pasadas o un WAV de antemano. O
sea: más código para un beneficio que ya teníamos gratis.

### Decisión C: `array('h')` en vez de lista de floats

 seemingly menor pero vale la pena. El primer versión acumulaba las muestras en
una lista normal de Python:

```python
muestras = []                    # lista de floats
muestras.append(onda * envolvente)
```

Con eso, una canción de 14 s ocupaba unos **7 MB**. Lo cambiamos por un
`array('h')` (enteros de 16 bits), que ocupa **620 KB**: doce veces menos
memoria, y es exactamente el formato que hay que entregarle al sistema de audio.

```python
muestras = array.array('h')      # 2 bytes por muestra
```

Además, para el volumen se usa un array y no un `list` porque el módulo `array`
guarda los números crudos, sin el objeto Python alrededor.

---

## 6. Etapa 4: reproducir (y por qué las dos plataformas son distintas)

`audio.py` recibe el PCM crudo y lo manda a los parlantes. Música y efectos van
en canales separados, así que un efecto nunca interrumpe la música.

### Linux: por tubería, sin tocar el disco

`paplay` y `aplay` saben leer audio crudo por la entrada estándar, así que el
PCM se escribe directamente:

```python
proc = subprocess.Popen(['paplay', '--raw', '--format=s16le', ...],
                        stdin=subprocess.PIPE)
proc.stdin.write(pcm)
```

El orden importa mucho aquí, y nos costó una tarde en Fedora:

- El proceso hijo tiene que **registrarse antes** de escribir el PCM.
- Escribir en la tubería **se bloquea** mientras el reproductor consume, y eso es
  a propósito: la tubería aplica contrapresión, así que el reproductor marca el
  ritmo real y la canción no adelanta.
- Pero si registraras el proceso *después* de escribir, durante los primeros 14 s
  el juego no tendría a quién matar, ni el botón de silencio ni el cierre
  funcionarían.

### Windows: MCI obliga a escribir un archivo

Aquí no hay opción. MCI (la API de audio de Windows) **solo sabe abrir rutas de
archivo**; no tiene forma de reproducir un buffer en memoria. Así que en Windows
sí se escribe un `.wav` temporal:

- La música usa **un solo archivo** que se reescribe al cambiar de tema.
- Cada efecto usa un archivo propio y se borra en cuanto termina de sonar.
- Todo vive en una carpeta que se elimina al cerrar el juego.

Esto no es un defecto del diseño, es una limitación del transporte. Y tiene una
consecuencia que hubo que defender: **MCI abre el archivo en exclusiva**, así que
no se puede reescribir mientras suena.

### Una carrera de hilos que sí importaba

Esa consecuenciaTheta-see generó un bug real: el hilo de la canción anterior
dejaba el archivo abierto, el siguiente intento de escritura fallaba con
`Permission denied`, y la música nueva se quedaba muda sin decir nada. El
`except Exception: pass` lo escondía.

La solución fue un contador de generación. Cada vez que se pide una canción
sube, y el hilo viejo se retira cuando lo nota:

```python
def _sigo_vivo(self, generacion):
    with self._lock:
        return (self.reproduciendo_musica
                and not self.silenciado
                and self._generacion == generacion)
```

Y antes de escribir el archivo nuevo, se espera a que el hilo viejo termine:

```python
self._esperar_hilo_musica()      # join del hilo anterior
self._escribir_wav(self._ruta_musica, pcm)
```

El orden importa igual que en Linux: primero se sube la generación (retira al
hilo viejo), después se espera a que se vaya, y solo entonces se escribe.

---

## 7. Cómo se extiende el lenguaje

El grammar formal está en `grammars/tetris.bnf`. Esto **no** lo usa el
compilador — el compilador es un parser escrito a mano — sino que documenta
formalmente qué acepta el lenguaje.

```
<programa>      ::= <tipo_juego> <grid> <definiciones> <canciones> <efectos> <eventos>
<canciones>     ::= "" | <cancion> <canciones>
<cancion>       ::= "DEFINE" "SONG" <identificador> ":" <notas> "END"
<notas>         ::= <nota> | <nota> <notas>
<nota>          ::= "NOTE" <nota_nombre> <numero>
<nota_nombre>   ::= <letra_nota> <digito>
<accion_musica> ::= "PLAY_MUSIC" <identificador>
                  | "STOP_MUSIC"
                  | "PLAY_EFFECT" <identificador>
```

Fíjate en dos cosas:

**`<canciones> ::= "" | ...` — las canciones son opcionales.** Un `.brick` viejo,
sin ningún `DEFINE SONG`, sigue compilando y funcionando: simplemente suena
mudo. Esto es retrocompatibilidad deliberada.

**`SONG` y `SHAPE` comparten estructura pero no cuerpo.** Los dos son
`DEFINE <palabra> <nombre> : <cosas> END`, pero `<cosas>` es distinto: `SHAPE`
lleva `STATE` y matrices, `SONG` lleva `NOTE`. Es el mismo esqueleto con dos
cuerpos distintos — el patrón clásico de gramática con sobrecarga.

---

## 8. El detalle que más preguntas genera: por qué milisegundos

La notación musical normal es **relativa**. Una "negra" no dura una cantidad fija
de tiempo: dura lo que marque el tempo. Si quieres compás, notas con puntillo o
síncopas, necesitas llevar la cuenta de un BPM y hacer conversiones.

Nosotros usamos **tiempo absoluto**: cada nota dura exactamente lo que dice su
número.

| Duración | Se parece a... |
|---|---|
| 40 ms | un clic muy corto |
| 60 ms | un beep corto (efecto de línea) |
| 220 ms | una nota rápida |
| 440 ms | una nota normal |
| 880 ms | una nota larga |

**Qué se gana:** el compilador no necesita conversiones ni BPM, la síntesis es
una cuenta simple, y es mucho más fácil de depurar (si una nota suena rare,
el número te lo dice).

**Qué se paga:** no hay notación armónica (música con acordes) ni compás. Para lo
que hace este juego — un tema y cuatro efectos — no se nota. Si quisiéramos
música más compleja, habría que decidir si Worth it meter BPM y media nota, y eso
ya es otro diseño.

---

## 9. Lo que el motor aprendió a hacer

Para que los `PLAY_EFFECT` del `.brick` no fueran código muerto, hubo que hacer
que el motor emitiera algunos eventos que antes no emitía. Estos son los eventos
de audio y **dónde los dispara**:

| Evento | Lo emite... | Ejemplo |
|---|---|---|
| `ON_ROTATE` | `engine/tetris.py`, al rotar bien | beep corto |
| `ON_EXPLOSION` | `engine/tetris.py`, en bomba y superbomba | explosion |
| `ON_PIECE_LAND` | `engine/tetris.py`, al fijar cualquier pieza | — |
| `ON_LINE_CLEAR` | `engine/tetris.py`, por cada línea | beep de línea |
| `ON_GAME_OVER` | `engine/game.py`, **una sola vez** | jingle de fin |

El de `ON_GAME_OVER` tiene un detalle: el loop del juego revisa cada 50 ms si se
terminó, así que hace falta una guarda para que el evento salga **una vez**, no
veces:

```python
if not self._game_over_emitido:
    self._game_over_emitido = True
    self.ejecutar_evento('ON_GAME_OVER')
```

---

## 10. Preguntas que podrían hacer (y las respuestas)

**¿Por qué no usan archivos MP3?**
Porque el objetivo es que la música venga del código. Si metiéramos un `.wav`,
la música dejaría de ser parte del lenguaje y pasaría a ser un recurso.

**¿Por qué onda senoidal y no cuadrada como la Game Boy?**
La senoidal suena más suave y no cansa el oído. Además se genera con `math.sin`,
que ya está en la biblioteca estándar de Python 2.7, sin instalar nada.

**¿Por qué el volumen está tan bajo (4%)?**
Para que sea música de fondo. El sintetizador normaliza el pico al 4% del máximo
(`PICO = 0.04`), así que no hay que subirle el volumen a nada en el sistema
operativo ni皖 los parlantes.

**¿Y si no hay notas en el `.brick`?**
El botón de audio ni siquiera aparece. `Game.tiene_audio()` revisa si el `.brick`
declaró `songs` o `effects`; si no, el motor arranca en silencio sin mostrar el
botón.

**¿Cuánto tarda la primera vez que suena una canción?**
0.558 s, y solo esa vez: las siguientes salen de la caché en RAM en 0.013 s. Y
como `PLAY_MUSIC` es idempotente (ver más abajo), en una partida normal se paga
una sola vez.

**¿Qué es "idempotente" aquí?**
Que `ON START` se dispara cada vez que se fija una pieza (porque ahí se pide la
pieza nueva). Si `PLAY_MUSIC` reiniciara la canción cada vez, la música se
cortaría a cada pieza. Por eso `musica_brick` compara la firma antes de tocar
nada:

```python
if firma == self.audio.musica_actual and self.audio.reproduciendo_musica:
    return    # ya está sonando, no tocar
```

**¿Puede sonar música y efecto a la vez?**
Sí. En Linux cada uno es un proceso distinto y el sistema los mezcla; en Windows
cada uno tiene su alias MCI. Resultado: un efecto no interrumpe la música.

**¿Y en un Linux sin `paplay` ni `aplay`?**
El juego sigue funcionando, solo que mudo. `audio.py` detecta qué reproductor hay
al arrancar y, si no encuentra ninguno, avisa por `stderr` y sigue sin sonido.

**¿Se pueden usar sostenidos (`C#4`)?**
No en esta versión. El lexer trata `#` como inicio de comentario, así que `C#4`
se leería como `C4`. Es una limitación conocida, deliberada por ahora.

---

*Documento del grupo 24 – Proyecto TLP 2026-2*
