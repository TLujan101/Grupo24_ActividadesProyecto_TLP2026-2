#!/bin/bash
# jugar.sh --- Compila y ejecuta juegos de BrickScript (equivalente Linux de jugar.bat)
# Uso: ./jugar.sh [snake|tetris|tetris_reborn]
# Requiere: python2 con Tkinter (ej: paru -S --needed tk python2)

PYTHON2="${PYTHON2:-python2}"

Pedir() {
    echo ""
    echo " Elija un juego:"
    echo " snake"
    echo " tetris"
    echo " tetris_reborn"
    echo ""
    read -p "Elige un juego (snake, tetris, tetris_reborn): " Juego
}

if [ -n "$1" ]; then
    Juego="$1"
else
    Pedir
fi

# Validar (case-insensitive como el /I del .bat)
JuegoLower=$(echo "$Juego" | tr '[:upper:]' '[:lower:]')
case "$JuegoLower" in
    snake|tetris|tetris_reborn) Juego="$JuegoLower" ;;
    *) echo "Juego invalido: $Juego"; Pedir
       JuegoLower=$(echo "$Juego" | tr '[:upper:]' '[:lower:]')
       case "$JuegoLower" in
           snake|tetris|tetris_reborn) Juego="$JuegoLower" ;;
           *) echo "Juego invalido. Abortando."; exit 1 ;;
       esac ;;
esac

# --- FASE 1: COMPILACION ---
echo "Compilando el juego: $Juego..."
echo "----------------------------------"
"$PYTHON2" ./compiler.py "./games/$Juego.brick"
if [ $? -ne 0 ]; then
    echo ""
    echo "!!! Ocurrio un error durante la compilacion. !!!"
    echo "Revisa los mensajes de error de arriba."
    exit 1
fi

echo ""
echo "Compilacion exitosa. Iniciando el juego..."
echo "----------------------------------"

# --- FASE 2: EJECUCION ---
"$PYTHON2" ./runtime.py "./games/$Juego.json"

echo ""
echo "El juego se ha cerrado."
