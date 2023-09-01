#!/bin/bash
set -e

PREFIX=/usr/local
./build.sh
mv onyo $PREFIX/bin/onyo
