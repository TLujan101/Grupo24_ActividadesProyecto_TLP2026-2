@echo off
REM --- Script para compilar y ejecutar juegos de BrickScript ---

REM Limpia la pantalla para una ejecucion limpia
cls

REM Verifica si se proporciono un nombre de juego.
if "%1"=="" (
    echo.
    echo  Uso: jugar [nombre_del_juego]
    echo  Ejemplo: jugar snake
    echo  Ejemplo: jugar tetris
    echo.
    goto :eof
)

REM --- FASE 1: COMPILACION ---
echo Compilando el juego: %1...
echo ----------------------------------

REM Ejecuta el compilador de Python.
C:\Python27\python.exe .\compiler.py .\games\%1.brick

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
C:\Python27\python.exe .\runtime.py .\games\%1.json

REM Fin del script.
echo.
echo El juego se ha cerrado. Presiona cualquier tecla para cerrar esta ventana.
pause