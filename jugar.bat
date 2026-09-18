@echo off
REM jugar.bat --- Compila y ejecuta juegos de BrickScript
REM Uso: jugar.bat [numero|juego]   (los nombres se descubren de games\*.brick)
setlocal EnableDelayedExpansion

REM Limpia la pantalla para una ejecucion limpia
cls

REM Descubre los juegos disponibles a partir de games\*.brick (nada hardcodeado).
dir /b "games\*.brick" >nul 2>&1
if errorlevel 1 (
    echo No hay juegos en games\ (falta *.brick^). Abortando.
    pause
    goto :eof
)

set Count=0
for %%f in (games\*.brick) do (
    set /A Count+=1
    set "Game_!Count!=%%~nf"
    set "File_!Count!=%%f"
)

if "%~1"=="" (
    call :Pedir
) else (
    set "Juego=%~1"
)

call :Resolver
if not defined Brick (
    echo Juego invalido: %Juego%
    call :Pedir
    call :Resolver
    if not defined Brick (
        echo Juego invalido. Abortando.
        pause
        goto :eof
    )
)
set "Json=!Brick:.brick=.json!"

REM --- FASE 1: COMPILACION ---
echo Compilando el juego: %Brick%...
echo ----------------------------------

REM Ejecuta el compilador de Python.
C:\Python27\python.exe .\compiler.py "%Brick%"

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
C:\Python27\python.exe .\runtime.py "%Json%"

REM Fin del script.
echo.
echo El juego se ha cerrado. Presiona cualquier tecla para cerrar esta ventana.
pause
goto :eof

:Pedir
echo.
echo  Menu de Juegos:
for /L %%i in (1,1,!Count!) do (
    echo  %%i^) !Game_%%i!
)
echo.
set "Juego="
set /p Juego="Selecciona un Numero o Nombre: "
goto :eof

REM Resuelve el .brick real a partir de un numero (1-N) o nombre (case-insensitive).
REM Usa la variable Juego y deja el resultado en Brick (vacia si no existe).
:Resolver
set "Brick="
if not defined Juego goto :eof
echo %Juego%| findstr /R "^[0-9][0-9]*$" >nul
if not errorlevel 1 (
    if %Juego% GEQ 1 if %Juego% LEQ !Count! (
        call set "Brick=%%File_%Juego%%%"
        goto :eof
    )
)
for /L %%i in (1,1,!Count!) do (
    if /I "!Game_%%i!"=="%Juego%" (
        set "Brick=!File_%%i!"
        goto :eof
    )
)
goto :eof
