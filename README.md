# Actividades y Proyectos Grupo 24 TLP 2026-2 UNAL MED
Repositorio para el desarrollo colaborativo de actividades y proyectos para la materia Teoría de Lenguajes de Programación (Profesor: Fernan Alonso Villa)

## Avance del Proyecto Final
- [x] Actividad 1: Equipo (13 sep)
- [x] Actividad 2: Entorno (22 sep)
- [ ] Actividad 3: Tetris+ (06 oct)
- [ ] Actividad 4: Snake+ (27 oct)
- [ ] Actividad 5: Tanks (17 nov)
- [ ] Actividad 6: Integración (07 dic)

## Estructura del repositorio
```
├── compiler.py      Compilador: traduce un .brick a .json
├── runtime.py       Carga el .json y arranca el juego correspondiente
├── jugar.bat        Compila y juega (Windows)
├── jugar.sh         Compila y juega (Linux)
├── games/           Código BrickScript (.brick) de cada juego y sus variantes
├── engine/          Lógica en Python de cada tipo de juego (Tetris, Snake, ...)
│                   más apoyos internos (audio, tracker, utilidades)
├── grammars/        Gramáticas BNF del lenguaje
├── docs/            Documentación (índice en docs/README.md: guía del
│                   lenguaje, instalación, registro de cambios)
├── tests/           Tests automáticos
├── .githooks/       Hook de pre-commit (corre los tests)
```

## Documentación (`docs/`, en orden de lectura)
1. Este índice (`README.md`): panorama del proyecto.
2. [`Guia-BrickScript.txt`](Guia-BrickScript.txt): guía del lenguaje (sintaxis de Tetris y Snake, colores, CHANCE, eventos extendidos).
3. [`Instalacion.txt`](Instalacion.txt): requisitos (Python 2.7), estructura y solución de problemas.
4. [`Musica-BrickScript.md`](Musica-BrickScript.md): cómo funciona la música programada en el `.brick`.
5. [`cambios/`](cambios/): registro de cambios de la Actividad 3 (formas, motor, scripts `jugar`).

## Tests
Cada PR hacia `main` corre [`../.github/workflows/tests.yml`](../.github/workflows/tests.yml), que verifica:
1. Que todo el código Python compila (y pasa pyflakes).
2. Que todos los `.brick` de `games/` compilan.
3. **Retrocompatibilidad:** los juegos clásicos (los `.brick` sin *reborn* ni *remake* en el nombre) siguen funcionando con el compilador y el motor actuales.
4. Todos los tests unitarios y de integración.

Para correrlos en local (desde la raíz del repo):
```
python2 -m unittest discover -s tests -t . -v
```

## Pre-commit (una sola vez por clon)
Antes de cada commit se corren los tests y, si alguno falla, el commit se cancela. Se activa con:
```
git config core.hooksPath .githooks
```
Si no lo activas, igual el PR no se puede mezclar con los checks en rojo. No uses `--no-verify` para saltarte el hook.
