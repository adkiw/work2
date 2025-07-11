#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ ! -f venv/pyvenv.cfg ]; then
    rm -rf venv
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
    if [ -f fastapi_app/requirements.txt ]; then
        ./venv/bin/pip install -r fastapi_app/requirements.txt
    fi
fi

./venv/bin/python -m web_app
