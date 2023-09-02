# Language Reference

## Contents

- [Data Types](#data-types)
  - [Tuples](#tuples)
  - [Lists](#lists)
- [Language Features](#language-features)
  - [Comments](#comments)
  - [Functions](#functions)
    - [Main Function](#main-function)
  - [Variables](#variables)
  - [Conditions](#conditions)
  - [Loops](#loops)
- [Operators](#operators)
- [Builtin Functions](#builtin-functions)

# Data Types

| Name    | Description                                               |
| ------- | --------------------------------------------------------- |
| `null`  | The null type has the only value `null`.                  |
| `bool`  | The bool type has two values, `true` or `false`.          |
| `int`   | Signed integers, equal to `int` in C.                     |
| `float` | Double precession floating point, equal to `double` in C. |
| `str`   | Immutable string.                                         |
| `tuple` | Immutable array of values.                                |
| `list`  | Mutable dynamic array of values.                          |

## Tuples

```py
tup = {1, 2, 3};
print tup[0];
print len(tup);
print index(tup, 2);
for i in a {
    print i;
}
```

## Lists

```py
a = [1, 2, 3];
push a, 4;
a[2] = "Hello";
print a[2];
remove a, len(a)-1;
print index(a, 2);
for i in a {
    print i;
}
```

# Language Features

## Comments

```c
// Single-line comments.

/*------------*
 * Multi-line *
 * Comments   *
 *------------*/
```

## Functions

Functions are defined using the `🧅` keyword. (`def` can be used as an alternative.)

```py
🧅 function_name(arguments, etc) {
  /* ... */
}
```

### Calling functions

```py
result = function();
```

```py
function();
```

### Returning values

```py
return value;
```

Functions implicitly return `null`.

### Main function

Must be present in every program. Takes no arguments.

```py
🧅 main() {
  /* ... */
}
```

## Variables

Uninitialized variables are set to null. There are no global variables.

```py
name = value;
name += value;
name -= value;
name -= value;
name /= value;
name %= value;
```

## Conditions

```py
if condition {
  /* ... */
} elif condition {
  /* ... */
} else {
  /* ... */
}
```

## Loops

```py
while condition {
  /* ... */
}
```

```py
for item in [1, 2, 3] {
  print item;
}
```

# Operators

| Operator          | Description                                       |
| ----------------- | ------------------------------------------------- |
| `a + b`           | Adds numbers, concats strings.                    |
| `a - b`           | Subtracts numbers.                                |
| `-a`              | Subtract number from 0.                           |
| `a * b`           | Multiplies numbers.                               |
| `a / b`           | Divides numbers.                                  |
| `a % b`           | Mod operator.                                     |
| `a == b`          | Equality operator.                                |
| `a != b`          | Not equals operator.                              |
| `a < b`           | Less than operator. Compares numbers and strings. |
| `a > b`           | Greater than operator. ditto.                     |
| `a <= b`          | Less than equal to operator. ditto.               |
| `a >= b`          | Greater than equal to operator. ditto.            |
| `a \|\| b`        | Logical or operator. Does not short circuit.      |
| `a && b`          | Logical and operator. ditto.                      |
| `!a`              | Logical not operator.                             |
| `iterable[index]` | Get element at index in iterable.                 |

For the arithmetic operators, if any one of the operands is a float, the result will
be a float.

## Type Errors

All operators return `null` on type errors. Operators do not coerce types.

# Builtin functions

| Function                   | Description                               |
| -------------------------- | ----------------------------------------- |
| `bool(a)`                  | Converts to bool.                         |
| `int(a)`                   | Converts to int.                          |
| `float(a)`                 | Converts to float.                        |
| `str(a)`                   | Converts to str.                          |
| `type(a)`                  | Returns the type name as a str.           |
| `index(iterable, element)` | Returns the index of element in iterable. |
| `len(iterable)`            | Returns the length of iterable.           |
| `push list, element;`      | Add element to the end of list.           |
| `remove list, index;`      | Remove element at index in list.          |
| `list[index] = value;`     | Set element at index in list.             |
| `print value;`             | Prints value to stdout.                   |

Iterable means either a str, a tuple or a list.

The type conversion functions return `null` if the value cannot be converted.

## `print`

If value is a str, it will be written to stdout without a newline.
Otherwise, the equivalent of `print str(value) + "\n";` will result.
