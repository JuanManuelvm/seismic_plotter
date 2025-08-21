#!/bin/bash
# 🧪 Verificar e instalar python3-venv si no está disponible
if ! python3 -m venv --help > /dev/null 2>&1; then
    echo "❌ 'python3-venv' no está instalado. Instalando..."
    sudo apt-get update
    sudo apt-get install -y python3-venv
else
    echo "✅ 'python3-venv' disponible."
fi

# 🧪 Verificar e instalar tkinter
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "❌ 'tkinter' no está disponible. Instalando..."
    sudo apt-get update
    sudo apt-get install -y python3-tk
else
    echo "✅ 'tkinter' disponible."
fi

if [ ! -d "$VENV_DIR" ]; then
	python3 -m venv venv
else
	echo "✅ Entorno virtual '$VENV_DIR' ya existe."
fi
source venv/bin/activate
pip install -r requirements.txt

# Verificar si slinktool ya está instalado
if ! command -v slinktool &> /dev/null; then
    echo "❌ 'slinktool' no está instalado. Procediendo a descargar y compilarlo..."

    # Instalar dependencias de compilación (solo la primera vez)
    sudo apt-get update
    sudo apt-get install -y build-essential curl unzip autoconf automake libtool

    # Descargar y compilar slinktool desde EarthScope/slinktool sin usar git
    if [ ! -d "slinktool" ]; then
        echo "🔽 Descargando slinktool desde GitHub (sin git)..."
        curl -L -o slinktool.zip https://github.com/EarthScope/slinktool/archive/refs/heads/main.zip
        unzip slinktool.zip
        mv slinktool-main slinktool
        rm slinktool.zip
    fi

    cd slinktool
    make clean || true
    make

    if [ -f "slinktool" ]; then
        sudo cp slinktool /usr/local/bin/
        echo "✅ 'slinktool' compilado e instalado en /usr/local/bin"
    else
        echo "❌ Falló la compilación de 'slinktool'."
        exit 1
    fi
    cd ..
else
    echo "✅ 'slinktool' ya está disponible en el sistema."
fi

python3 LecturaSeedlink.py