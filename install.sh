#!/bin/bash
set -e

PREFIX=/usr/local
./build.sh
mv onyo $PREFIX/bin/onyo

python3 -m pip install -e . --break-system-packages
