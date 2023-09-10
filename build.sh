#!/bin/bash
set -e

CFLAGS="-Werror
        -Weverything
        -Wno-unknown-warning-option
        -Wno-declaration-after-statement
        -Wno-padded
        -Wno-switch-enum
        -Wno-shadow
        -Wno-unused-parameter
        -Wno-disabled-macro-expansion
        -Wno-unsafe-buffer-usage
        -Wno-float-equal
        -Ofast
        -std=c11
        -lm"
clang $CFLAGS src/onyo.c -o onyo

        #-pg
