#!/bin/bash
# jugar.sh --- Compila y ejecuta juegos de BrickScript (equivalente Linux de jugar.bat)
# Uso: ./jugar.sh [numero|juego]   (los nombres se descubren de games/*.brick)
# Requiere: python2 con Tkinter (ej: paru -S --needed tk python2)

PYTHON2="${PYTHON2:-python2}"

# Descubre los juegos disponibles a partir de games/*.brick (nada hardcodeado).
shopt -s nullglob
Archivos=(games/*.brick)
if [ ${#Archivos[@]} -eq 0 ]; then
    echo "No hay juegos en games/ (falta *.brick). Abortando."
    exit 1
fi

Pedir() {
    echo ""
    echo " Menu de Juegos:"
    local i=1 f
    for f in "${Archivos[@]}"; do
        echo " $i) $(basename "$f" .brick)"
        i=$((i + 1))
    done
    echo ""
    read -p "Seleciona un Numero o Nombre: " Juego
}

# Resuelve el .brick real a partir de un numero (1-N) o nombre (case-insensitive).
# Imprime la ruta y retorna 0 si existe; si no, retorna 1.
Resolver() {
    local n="$1" f base i
    if [[ "$n" =~ ^[0-9]+$ ]] && [ "$n" -ge 1 ] && [ "$n" -le ${#Archivos[@]} ]; then
        echo "${Archivos[$((n - 1))]}"
        return 0
    fi
    n=$(echo "$n" | tr '[:upper:]' '[:lower:]')
    for f in "${Archivos[@]}"; do
        base=$(basename "$f" .brick)
        if [ "$(echo "$base" | tr '[:upper:]' '[:lower:]')" = "$n" ]; then
            echo "$f"
            return 0
        fi
    done
    return 1
}

if [ -n "$1" ]; then
    Juego="$1"
else
    Pedir
fi

Brick=$(Resolver "$Juego")
if [ -z "$Brick" ]; then
    echo "Juego Invalido: $Juego"
    Pedir
    Brick=$(Resolver "$Juego")
    if [ -z "$Brick" ]; then
        echo "Juego Invalido. Abortando."
        exit 1
    fi
fi
Json="${Brick%.brick}.json"

# --- FASE 1: COMPILACION ---
echo "Compilando el Juego: $Brick..."
echo "----------------------------------"
"$PYTHON2" ./compiler.py "$Brick"
if [ $? -ne 0 ]; then
    echo ""
    echo "!!! Ocurrio un Error Durante la Compilacion. !!!"
    echo "Revisa los Mensajes de Error de Arriba."
    exit 1
fi

echo ""
echo "Compilacion exitosa. Iniciando el juego..."
echo "----------------------------------"

# --- FASE 2: EJECUCION ---
"$PYTHON2" ./runtime.py "$Json"

echo ""
echo "El Juego se ha Cerrado."
