@echo off
REM --- Script para compilar y ejecutar juegos de BrickScript ---

REM Limpia la pantalla para una ejecucion limpia
cls

REM Verifica si se proporciono un nombre de juego.
:Menu
if "%1"=="" (
    goto Pedir
)
if not "%1"=="" (
set "Juego=%~1"
goto Validar
)
:Pedir
    echo.
    echo  Eliga un juego
    echo  snake
    echo  tetris
    echo.
    set /p Juego="Elige un juego (snake, tetris): "
    goto Validar
:Validar
    if /I "%Juego%"=="snake" goto Jugar
    if /I "%Juego%"=="tetris" goto Jugar
    goto Pedir


:Jugar
REM --- FASE 1: COMPILACION ---
echo Compilando el juego: %Juego%...
echo ----------------------------------


REM Ejecuta el compilador de Python.
C:\Python27\python.exe .\compiler.py .\games\%Juego%.brick

REM Verifica si el comando anterior (la compilacion) fallo.
if errorlevel 1 (
    echo.
    echo !!! Ocurrio un error durante la compilacion. !!!
    echo Revisa los mensajes de error de arriba.
    pause
    goto :eof
)

echo.
echo Compilacion exitosa. Iniciando el juego...
echo ----------------------------------
REM Se elimina la pausa para iniciar la GUI inmediatamente

REM --- FASE 2: EJECUCION ---
REM Ejecuta el motor del juego (runtime.py modificado con GUI).
C:\Python27\python.exe .\runtime.py .\games\%Juego%.json

REM Fin del script.
echo.
echo El juego se ha cerrado. Presiona cualquier tecla para cerrar esta ventana.
pause
