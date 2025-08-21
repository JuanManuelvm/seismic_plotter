#!/bin/bash
if [ ! -d "$VENV_DIR" ]; then
	python3 -m venv venv
else
	echo "✅ Entorno virtual '$VENV_DIR' ya existe."
fi
source venv/bin/activate
pip install -r requirements.txt

if ! command -v slinktool &> /dev/null; then
    echo "❌ 'slinktool' no está instalado. Procediendo a compilarlo desde libslink..."

    # Dependencias de compilación
    sudo apt-get update
    sudo apt-get install -y build-essential git autoconf automake libtool

    # Descargar y compilar libslink
    if [ ! -d "libslink" ]; then
        git clone https://github.com/iris-edu/libslink.git
    fi
    cd libslink
    make clean || true
    make
    sudo cp slinktool /usr/local/bin/
    cd ..

    echo "✅ 'slinktool' compilado e instalado en /usr/local/bin"
else
    echo "✅ 'slinktool' encontrado en el sistema."
fi

python3 LecturaSeedlink.py