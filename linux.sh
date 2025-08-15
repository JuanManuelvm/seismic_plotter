#!/bin/bash
if [ ! -d "$VENV_DIR" ]; then
	python3 -m venv venv
else
	echo "✅ Entorno virtual '$VENV_DIR' ya existe."
fi
source venv/bin/activate
pip install -r requirements.txt
python3 LecturaSeedlink.py
ls -la
