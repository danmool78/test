#!/usr/bin/env bash
set -euo pipefail

# Clean previous builds
rm -rf build dist tetris.spec

# Build a single-file, windowed executable
pyinstaller --name tetris --onefile --noconsole tetris.py

echo "Executable created in dist/"
