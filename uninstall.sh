#!/bin/bash
set -e

PREFIX=/usr/local
sudo rm $PREFIX/bin/onyo

python3 -m pip uninstall onyoc --break-system-packages
