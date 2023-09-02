#!/bin/bash
set -e

PREFIX=/usr/local
./build.sh
sudo mv onyo $PREFIX/bin/onyo

python3 -m pip install -e . --break-system-packages
