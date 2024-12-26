#!/bin/bash

set -e

REPO_DIR="$(dirname $(realpath $0))"
PYTHON_SCRIPT="$REPO_DIR/src/bot.py"
REQUIREMENTS_FILE="$REPO_DIR/requirements.txt"

apt update
apt upgrade -y

if [ -d "$REPO_DIR" ]; then
    cd "$REPO_DIR"
    git config --global --add safe.directory "$REPO_DIR"
    git fetch
    git pull

    if [ -f "$REQUIREMENTS_FILE" ]; then
        pip install -r "$REQUIREMENTS_FILE" --break-system-packages
    fi
fi

python3 "$PYTHON_SCRIPT"
