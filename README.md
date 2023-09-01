# onyo 🧅

onyo 🧅 is an interpreted programming language.

```lisp
(defun (fact n) (
    (if (! (> n 1)) (
        (return 1)
    ) else (
        (return (* n (fact (- n 1))))
    ))
))

(defun (main) (
    (print (fact 5))
))
```

onyo uses reference counting to automatically manage memory. onyo is dynamically typed. onyo uses a lisp-like syntax. The optional pre-compiler (Written in python) provides a "sane" alternative syntax.

## Install (From source)

### Dependencies
- `clang` <https://clang.llvm.org/> (>= 16.0.6)
- `python` <https://python.org/> (>= 3.11.5)

Run [`install.sh`](./install.sh) to install under `/usr/local/bin`.

### Uninstall

Run [`uninstall.sh`](./uninstall.sh) to uninstall.

## Install (From binary)

Grab [`onyo`](./onyo) and put it inside `/usr/local/bin` or `~/.local/bin`.

## Develop

Run [`build.sh`](./build.sh) to build everything.
