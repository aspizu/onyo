# onyo 🧅

onyo 🧅 is an interpreted programming language.

[**Language Reference**](./wiki/language-reference.md)

```py
🧅 fact(n) {
    if n <= 1 {
        return 1;
    } else {
        return n * fact(n - 1);
    }
}

🧅 main() {
    print fact(5);
}
```

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

The onyo interpreter is written in C. onyo uses reference counting to automatically
manage memory and is dynamically typed. onyo uses a lisp-like syntax but the optional
compiler [`onyoc`](./onyoc) (Written in python) provides a "sane" alternative syntax and
error-checking.

## Usage

Use `onyoc` to compile and run your programs.

Running `onyoc -i heavy.onyo` will compile and execute your program.

Running `onyoc -i heavy.onyo -o heavy.onyoc` will compile your program into a file.
Which can be executed by the interpreter by running `onyo heavy.onyoc`.

## Install (From source)

### Dependencies
- `clang` <https://clang.llvm.org/> (>= 16.0.6)
- `python` <https://python.org/> (>= 3.11.5)

Run [`install.sh`](./install.sh) to install under `/usr/local/bin`.

### Uninstall

Run [`uninstall.sh`](./uninstall.sh) to uninstall.

## Install (From binary)

Grab [`onyo`](./onyo) and put it inside `/usr/local/bin` or `~/.local/bin`.
Run `pip install -e . --break-system-packages` to install `onyoc`.

## Develop

Run [`build.sh`](./build.sh) to build everything.
