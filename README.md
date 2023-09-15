# onyo

onyo is a interpreted, dynamically typed, automatic memory managed programming language. onyo was designed to have a simple
implementation while maintaining the user friendliness of dynamic programming languages such as Python, Javascript and Ruby.

#### Contents

- [C onyo Interpreter](#c-onyo-interpreter)
- [Rust onyo Interpreter](#rust-onyo-interpreter-onyo-rs)
- [Language Reference](#language-reference)

# C onyo Interpreter

The original onyo interpreter was written in C. I chose C because it let me implement all the constructs of the language such as
Dynamic arrays, Hash tables and Reference-counted pointers on my own. By implementing the interpreter in C, I learn't how these
constructs work behind the scenes of a dynamic programming language.

## Parsing

The first step in interpreting code is to parse it into a Abstract Syntax Tree. Using the recursive descent parsing method, it
is trivial to parse a lisp-like syntax.

- <https://iitd.github.io/col728/lec/parsing.html>
- <https://web.archive.org/web/20190307204217/https://www.engr.mun.ca/~theo/Misc/exp_parsing.htm>
- <https://en.wikipedia.org/wiki/S-expression>

```lisp
(+ A (* B C))
```

```
  +
 / \
a   *
   / \
  b   c
```

Though this syntax is easy to implement, its harder to write and format. Thus the Rust version of onyo does not use this syntax.

## Tree-walking interpreter

The interpreter works by walking the Abstract Syntax Tree and performing the operators and instructions.

## Memory Management

Programming languages such as Java, Python and Javascript automatically manage memory for the programmer using various
methods. onyo uses a method called Reference Counting.

In Reference Counting, each object contains a counter saying how many references to it there are. When you refer to an object,
you increment the counter. When you're done with it, you decrement the counter. When the counter reaches 0, the object can be
recycled.

Though this is a simple solution, it does not prevent the programmer from creating cyclic references, which creates a memory
leak. It also does not do any optimization for allocation and deallocation.

## Data types implementation

### Dynamic arrays

Dynamic arrays in C onyo were implemented in a similar way to how the `Vec` data structure works in Rust. The capacity of a
dynamic array will grow with a factor of 2 times the old capacity. onyo provides no way to shrink the capacity of a dynamic
array.

- <https://doc.rust-lang.org/nomicon/vec/vec.html>

### Hash maps

The `table` data type in C onyo was implemented using a placeholder implementation which uses linear search. The plan was to
later replace the linear search with a proper hash table implementation which was eventually ditched after switching to Rust.

# Rust onyo Interpreter (onyo-rs)

Though C taught me how to implement the constructs by my own, it was getting quite difficult to debug. Thus, I decided to
rewrite the interpreter in the Rust programming language. This lead to major design changes in the language. The rust version of
onyo uses a JSON format instead of S-expressions. A compiler written in Python is used to compile onyo code into a JSON file.

## Differences from C onyo

C onyo's compiler was optional, but the compiler is required in the Rust version. onyo-rs is much more stable than C onyo and
it is faster to develop features. Rust's features such as `Rc` for reference-counting, `Vec` for dynamic arrays and `HashMap`
for hash maps were helpful.

# Language Reference

## Contents

- [Data Types](#data-types)
  - [Tuples](#tuples)
  - [Lists](#lists)
- [Language Features](#language-features)
  - [Comments](#comments)
  - [Functions](#functions)
    - [Main Function](#main-function)
  - [Structs](#structs)
  - [Variables](#variables)
  - [Conditions](#conditions)
  - [Loops](#loops)
- [Operators](#operators)
- [Builtin Functions](#builtin-functions)

# Data Types

| Name    | Description                                               |
| ------- | --------------------------------------------------------- |
| `nil`   | The null type has the only value `null`.                  |
| `err`   | Err is used to return errors, it can contain any value.   |
| `bool`  | The bool type has two values, `true` or `false`.          |
| `int`   | Signed integers, equal to `i64` in Rust.                  |
| `float` | Double precession floating point, equal to `f64` in Rust. |
| `str`   | Immutable string.                                         |
| `tuple` | Immutable array of values.                                |
| `list`  | Mutable dynamic array of values.                          |
| `dict`  | Hash table with str keys.                                 |

## Tuples

```lua
tup = {1, 2, 3}
print(tup[0])
print(len(tup))
print(index(tup, 2))
i = 0
while i < len(tup) {
    print(tup[i])
    i += 1
}
```

## Lists

```py
a = [1, 2, 3]
push(a, 4)
a[2] = "Hello"
print(a[2])
value = remove(a, len(a) - 1)
print index(a, 2);
i = 0
while i < len(a) {
    print(a[i])
    i += 1
}
```

# Language Features

## Comments

```asm
; Single-line comments.
; There are no multi-line comments.
```

## Functions

Functions are defined using the `🧅` keyword (This keyword is optional and can be ommited).

```lua
🧅 function_name(arguments, etc) {
  ; ...
}

; Will work aswell
function_name(arguments, etc) {
  ; ...
}
```

### Calling functions

```py
result = function()
```

```py
function()
```

### Returning values

```lua
return value
```

Functions implicitly return `nil`.

### Main function

Must be present in every program. Takes no arguments.

```lua
main() {
  ; ...
}
```

## Structs

Struct fields are static, which means that you cannot add a new field to a struct instance at run-time like you could do in
Javascript.

```lua
Name {
  field1
  field2
}

Person { name, age }
```

```lua
bdfl = Person { name = "aspizu", 18 }
friend =
  Person {
    name = "friend"
    age = 17
  }
```

The commas in struct definitions and literals are optional.

```lua
print(bdfl.name)
```

## Variables

Uninitialized variables are set to null. There are no global variables.

```lua
name = value
name += value
name -= value
name -= value
name /= value
name %= value
```

## Conditions

```lua
if condition {
  ; ...
} elif condition {
  ; ...
} else {
  ; ...
}
```

## Loops

```py
while condition {
  ; ...
}
```

# Operators

| Operator             | Description                                                          |
| -------------------- | -------------------------------------------------------------------- |
| `a + b`              | Adds numbers, concats strings.                                       |
| `a - b`              | Subtracts numbers.                                                   |
| `-a`                 | Subtract number from 0.                                              |
| `a * b`              | Multiplies numbers.                                                  |
| `a / b`              | Divides numbers.                                                     |
| `a % b`              | Mod operator.                                                        |
| `a & b`              | Bitwise And operator.                                                |
| `a ^ b`              | Bitwise Xor operator.                                                |
| `a \| b`             | Bitwise Or operator.                                                 |
| `~a`                 | Bitwise Not operator.                                                |
| `a << b`             | Bitwise left shift operator.                                         |
| `a >> b`             | Bitwise right shift operator.                                        |
| `a == b`             | Equality operator.                                                   |
| `a is b`             | Identity operator. Returns true if both values point to same memory. |
| `a != b`             | Not equals operator.                                                 |
| `a < b`              | Less than operator. Compares numbers and strings.                    |
| `a > b`              | Greater than operator. ditto.                                        |
| `a <= b`             | Less than equal to operator. ditto.                                  |
| `a >= b`             | Greater than equal to operator. ditto.                               |
| `a or b`             | If a then b else a.                                                  |
| `a and b`            | If a then a else b.                                                  |
| `not a`              | Logical not operator.                                                |
| `iterable[index]`    | Get element at index in iterable.                                    |
| `if b then a else c` | If b then a else c.                                                  |
| `var := val`         | Set var to val and return val.                                       |

For the arithmetic operators, if any one of the operands is a float, the result will
be a float.

## Type Errors

All operators return `nil` on type errors. Operators do not coerce types.

# Builtin functions

| Function                    | Description                                                                                 |
| --------------------------- | ------------------------------------------------------------------------------------------- |
| `err(a)`                    | Wraps `a` in a err, if `a` is an `err` then returns the value inside it.                    |
| `bool(a)`                   | Converts to bool.                                                                           |
| `int(a)`                    | Converts to int.                                                                            |
| `float(a)`                  | Converts to float.                                                                          |
| `str(a)`                    | Converts to str.                                                                            |
| `type(a)`                   | Returns the type name as a str.                                                             |
| `index(iterable, element)`  | Returns the index of element in iterable.                                                   |
| `len(iterable)`             | Returns the length of iterable.                                                             |
| `push(list, element)`       | Add element to the end of list.                                                             |
| `remove(list, index)`       | Remove element at index in list and return it.                                              |
| `list[index] = value`       | Set element at index in list.                                                               |
| `print(value)`              | Prints value to stdout.                                                                     |
| `join(iterable, seperator)` | Join values in iterable by placing `seperator` between each element.                        |
| `read(file_path)`           | Return the contents of file at `file_path` as a `str`, returns a `err(str)` on failure.     |
| `write(file_path, data)`    | Writes `data` into file at `file_path`, returns a `err(str)`on failure or`true` on success. |

Iterable means either a str, tuple, list or dict's values.

The type conversion functions return `nil` if the value cannot be converted.
