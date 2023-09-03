#!/bin/bash
# This script uninstalls the onyo interpreter, python package and the python package
# wrapper. It will automatically what python program to use for uninstalling the
# package. The script supports both a global and local uninstallation, but will
# prioritise a global uninstallation (although the install script does not support
# both global and local installations).
#
# MIT License
# 
# Copyright (c) 2023 polybit
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

warn() {
    local MESSAGE=$1
    echo "$MESSAGE" >&2
}

return() {
    local VALUE=$1
    echo "$VALUE" >&1
}

is_installation_global() {
    local GLOBAL=false
    if [[ -e /usr/local/bin/onyoc ]]; then
      GLOBAL=true
    elif [[ -e ~/.local/bin/onyoc ]]; then
      GLOBAL=false
    fi

    return $GLOBAL
}

abort_if_needs_sudo() {
    local GLOBAL=$1

    if $GLOBAL; then
        sudo ls 2>/dev/null 1>/dev/null
        if [ $? -gt 0 ]; then
            warn "onyo cannot be uninstalled globally without sudo"
            exit 1
        fi
    fi
}

abort_if_not_installed() {
    if ! [[ -e /usr/local/bin/onyoc ]] && ! [[ -e ~/.local/bin/onyoc ]]; then
        warn "onyo is not installed"
        exit 1
    fi
}

remove_c_program() {
    local GLOBAL=$1

    if $GLOBAL; then
        sudo rm /usr/local/bin/onyo
    else
        rm ~/.local/bin/onyo
    fi
}

remove_python_package() {
    local GLOBAL=$1

    local REGEX='2s/^\([^[:space:]]*\).*$/\1/p'
    if $GLOBAL; then
        PYTHON=$(
            cat /usr/local/bin/onyoc \
                | sed -n "$REGEX"
        )
        sudo rm /usr/local/bin/onyoc
    else
        PYTHON=$(
            cat ~/.local/bin/onyoc \
                | sed -n "$REGEX"
        )
        rm ~/.local/bin/onyoc
    fi
    
    "$PYTHON" -m pip uninstall onyoc -y 1>/dev/null 
}

main() {
    abort_if_not_installed

    local GLOBAL=$(is_installation_global)

    abort_if_needs_sudo $GLOBAL

    warn "Uninstalling onyo"

    remove_c_program $GLOBAL
    remove_python_package $GLOBAL

    warn "Uninstallation finished"
    warn
}

main "$@"

