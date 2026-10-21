# Memoria del proyecto — BrickScript (TLP2026-2)

## Intérprete: Python 2.7 obligatorio

El intérprete de referencia es `C:\Python27\python.exe` (ver `docs/Instalacion.txt`:
"NO es compatible con Python 3"; el CI usa la imagen `python:2.7.18`).

El `python` del PATH es 3.14 y con él la suite da **falsos fallos** (`test_tracker`,
`test_game` de audio, `import StringIO`, mensajes de error) y puede colgar.

```bat
cmd /c "C:\Python27\python.exe -u -m unittest discover -s tests -t . -v"
```

- En 2.7 los flags van **después** de `discover`; con nombres de módulo, antes
  (`-m unittest -v tests.test_snake`).
- Desde PowerShell el output se colinea hasta el final: si algo se cuelga, redirigir
  con `cmd /c ... > log 2>&1` y leer el log para ver en qué test va.

## Estado de la suite (117 tests, ~1.4 s)

4 fallos **preexistentes** en HEAD, de áreas ya distintas — no tocarlos sin pedir:

- `test_music_exige_nombre` (mensaje de error de `MUSIC`)
- `test_tema_nyan_es_la_melodia_fiel_de_una_voz` y
  `test_tema_nyan_sintetiza_la_melodia_completa` (el fixture y `TEMA_NYAN` del
  `.brick` no coinciden: 1712 vs 28080 ms)
- `test_snake_remake_abre_menu_y_arranca_al_elegir` (el `.brick` declara `START: BABY`)

## Gotchas de código

- `compiler.py` y `engine/snake.py` tienen **métodos duplicados**: gana siempre el
  último (`parsear_nivel` vive en la línea ~398, no en la 253). Al editar, verificar
  con grep cuál es el que corre.
- El spawn de comida/veneno/power-up se hace **dos veces**: lo dispara el evento
  (`SPAWN ... AT RANDOM`) y el motor lo forzaba también. Con `random` determinista
  eso era un bucle infinito; el motor ahora solo fuerza el respawn si el evento no
  lo hizo. Mantener esa guarda.
