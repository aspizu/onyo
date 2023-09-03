#!/bin/bash
# This is the installation script for onyo. It verifies that the system has a Python
# installation on version 3.11 or higher, parses command-line options, builds the onyo
# interpreter, installs the Python module requirements, installs the module locally,
# creates an executable script to easily run the module from path and installs the
# compiler.
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

usage() {
	cat <<-EOF
	usage: installer options
	
	This program installs and onyo and it's dependencies on your system. Everything is
	compiled from source, no precompiled programs are installed.
	
	If onyo is installed locally, ~/.local/bin/ will be used for the executables. If it
	is instead installed globally, /usr/local/bin/ will be used.
	
	The installer will place the onyo interpreter and an executable wrapper for the
	onyo compiler (onyoc) in the executable folder. 
	
	OPTIONS:
		-g --global     perform a global installation
		-h --help       shows this help message
	EOF
}

parse_args() {
    local ARGS="$@"

    options=$(getopt -o g,h -l global,help -- "$ARGS")
    eval set -- "$options"
    
    local GLOBAL=false
    local HELP=false
    
    while true; do
      case "$1" in
        -g | --global)
          GLOBAL=true
          shift
          ;;
        -h | --help)
          HELP=true
          shift
          ;;
        --)
          shift
          break
          ;;
        *)
          warn "Invalid option: \$1"
          exit 1
          ;;
      esac
    done

    return $GLOBAL
    return $HELP
}

warn() {
    local MESSAGE=$1
    echo "$MESSAGE" >&2
}

return() {
    local VALUE=$1
    echo "$VALUE" >&1
}

abort_if_installed() {
    if [[ -e /usr/local/bin/onyoc ]]; then
      warn "onyo has already been installed globally"
      warn "Please run ./uninstall before proceeding" 
      exit 1
    elif [[ -e ~/.local/bin/onyoc ]]; then
      warn "onyo has already been installed locally"
      warn "Please run ./uninstall before proceeding" 
      exit 1
    fi
}

abort_if_needs_sudo() {
    $GLOBAL = $1

    if $GLOBAL; then
        sudo ls 2>/dev/null 1>/dev/null
        if [ $? -gt 0 ]; then
            warn "onyo cannot be installed globally without sudo"
            exit 1
        fi
    fi
}

build_c_program() {
    local GLOBAL=$1

    warn "Building onyo"
    ./build.sh

    if $GLOBAL; then
        sudo mv onyo /usr/local/bin/onyo
    else
        mv onyo ~/.local/bin/onyo
    fi
}

find_python() {
    local PYTHON=""

    if command -v python3.11 &>/dev/null; then
      PYTHON="python3.11"
    elif command -v python &>/dev/null; then
      PYTHON="python"
    elif command -v python3 &>/dev/null; then
      PYTHON="python3"
    else
      warn "Python not found"
      exit 1
    fi
    
    local PYTHON_VERSION="$( \
        $PYTHON --version 2>&1
    )"
    local PYTHON_MAJOR="$( \
        echo "$PYTHON_VERSION" \
        | awk -v FS='.' '{print $2}' \
        | cut -d '.' -f1
    )"
    local PYTHON_MINOR="$( \
        echo "$PYTHON_VERSION" \
        | awk -v FS='.' '{print $2}' \
        | cut -d '.' -f2
    )"
    
    if [ "$PYTHON_MAJOR" -eq "3" ]; then
      warn "Python 3 on version 3.11 or above is required"
      exit 1
    elif [ "$PYTHON_MINOR" -lt "11" ]; then
      warn "Python 3.11 or higher is required"
      exit 1
    fi
    
    warn "Using $PYTHON"
    return "$PYTHON"
}

build_python_package() {
    local GLOBAL=$1
    local PYTHON=$2

    warn "Installing python package"
    "$PYTHON" -m pip install -r requirements.txt 1>/dev/null 
    "$PYTHON" -m pip install -e . 1>/dev/null 

    local COMMAND="#!/bin/bash\n$PYTHON -m onyoc \$@" 

    if $GLOBAL; then
        echo -e "$COMMAND" \
            | tee /usr/local/bin/onyoc 1>/dev/null 
        chmod +x /usr/local/bin/onyoc
    else
        echo -e "$COMMAND" \
            | tee ~/.local/bin/onyoc 1>/dev/null 
        chmod +x ~/.local/bin/onyoc
    fi
}

main() {
    local RAW_ARGS="$@"
    local ARGS=($(parse_args "$RAW_ARGS"))

    local GLOBAL=${ARGS[0]}
    local HELP=${ARGS[1]}

    if $HELP; then
        usage
        exit 0
    fi
    
    abort_if_installed
    abort_if_needs_sudo $GLOBAL

    build_c_program $GLOBAL
    build_python_package $GLOBAL $(find_python)
}

main "$@"

