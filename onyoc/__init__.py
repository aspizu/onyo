from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Union, cast

from lark import Lark, Token, Tree, UnexpectedCharacters
from lark.visitors import Visitor
from rich import print

from . import res

parser = Lark(
    (files(res) / "grammar.lark").read_text(),
    parser="earley",
    propagate_positions=True,
)
from . import term as t


class TypeEnum:
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TypeEnum):
            return self.name == other.name
        return False

    def __str__(self):
        return self.name


class Type:
    T = Union[TypeEnum, "UNION"]

    ANY = TypeEnum("any")
    NULL = TypeEnum("null")
    BOOL = TypeEnum("bool")
    INT = TypeEnum("int")
    FLOAT = TypeEnum("float")
    STR = TypeEnum("str")

    class UNION:
        def __init__(self, *types: "Type.T"):
            self.types: list["Type.T"] = []
            for type in types:
                self.add_type(type)

        def add_type(self, type: "Type.T"):
            if type in self.types:
                return
            if isinstance(type, Type.UNION):
                for subtype in type.types:
                    self.add_type(subtype)

        def __eq__(self, other: object) -> bool:
            return other in self.types

        def without(self, type: "Type.T"):
            try:
                self.types.remove(type)
            except ValueError:
                pass
            return self.unwrap()

        def unwrap(self):
            if len(self.types) == 1:
                return self.types[0]
            return self


type: Type.T = Type.UNION(Type.NULL, Type.BOOL)


@dataclass
class Range:
    line: int
    column: int
    length: int

    @classmethod
    def new(cls, token: Tree[Token] | Token) -> "Range":
        if isinstance(token, Token):
            assert token.line is not None
            assert token.column is not None
            return cls(
                token.line - 1,
                token.column - 1,
                len(token),
            )
        else:
            return cls(
                token.meta.line - 1,
                token.meta.column - 1,
                token.meta.end_column - token.meta.column,
            )


@dataclass
class Error:
    error: str
    range: Range
    help: str = ""
    source: str | None = None
    file: Path | None = None

    def print(self):
        assert self.source is not None
        t.w(f"{t.red}Error: {self.error}{t.reset}\n")
        for line_no, line in enumerate(self.source.splitlines()):
            if abs(line_no - self.range.line - 1) <= 3:
                t.w(
                    t.brblack
                    + str(line_no + 1).rjust(5, " ")
                    + t.reset
                    + " "
                    + line
                    + "\n"
                )
            if line_no == self.range.line:
                t.w(
                    t.blue
                    + " " * (7 + self.range.column)
                    + "^" * self.range.length
                    + " "
                    + self.help
                    + t.reset
                    + "\n"
                )


class ErrorStorage:
    errors: list[Error]
    source: str
    file: Path

    def __init__(self, source: str, file: Path):
        self.errors = []
        self.source = source
        self.file = file

    def add_error(self, error: Error):
        error.source = self.source
        error.file = self.file
        self.errors.append(error)


class Interpreter:
    def visit(self, node: Tree[Token] | Token):
        if isinstance(node, Token):
            if func := getattr(self, node.type, None):
                func(node)
        elif node:
            if func := getattr(self, node.data, None):
                func(node)

    def visitchildren(self, node: Tree[Token]):
        for i in node.children:
            self.visit(i)


@dataclass
class Function:
    name: Token
    arguments: list[Token]
    body: Tree[Token]
    variables: dict[str, "Variable"]


@dataclass
class Variable:
    name: Token
    type: Type.T


class DefinitionCollector(Interpreter, ErrorStorage):
    def __init__(self, source: str, file: Path, root: Tree[Token]):
        super().__init__(source, file)
        self.functions: dict[str, Function] = {}
        self.current_function: Function | None = None
        self.onyo = False
        self.visitchildren(root)

    def function(self, node: Tree[Token]):
        if node.children[0] == "def":
            if self.onyo:
                self.add_error(
                    Error(
                        error="Not using a heavy onyo.",
                        help="Use a 🧅 here.",
                        range=Range.new(node.children[0]),
                    )
                )
        else:
            self.onyo = True

        name = cast(Token, node.children[1])
        arguments = cast(list[Token], node.children[2:-1])
        if arguments == [None]:
            arguments = []
        body = cast(Tree[Token], node.children[-1])
        self.functions[str(name)] = Function(name, arguments, body, {})
        self.current_function = self.functions[str(name)]
        self.visitchildren(node)
        self.current_function = None

    block = Interpreter.visitchildren
    ifx = block
    ifelse = block
    ifelif = block
    ifelifelse = block
    whilex = block
    forx = block

    def set(self, node: Tree[Token]):
        if self.current_function:
            name = cast(Token, node.children[0])
            if str(name) not in self.current_function.variables:
                self.current_function.variables[str(name)] = Variable(name, Type.ANY)


class TypeCheckerVisitor:
    def _call_userfunc(self, tree: Tree[Token] | Token, types: list[Type.T]) -> Type.T:
        if isinstance(tree, Token):
            return getattr(
                self,
                tree.type,
                self.__default__,
            )(tree)
        else:
            return getattr(
                self,
                tree.data if tree is not None else "",  # type: ignore
                self.__default__,
            )(tree, types)

    def __default__(
        self, tree: Tree[Token] | Token, types: list[Type.T] | None = None
    ) -> Type.T:
        ...

    def __class_getitem__(cls, _):
        return cls

    def visit(self, tree: Tree[Token] | Token) -> Type.T:
        "Visits the tree, starting with the leaves and finally the root (bottom-up)"
        types: list[Type.T] = []
        if isinstance(tree, Tree):
            for child in tree.children:
                types.append(self.visit(child))
        return self._call_userfunc(tree, types)


Node = Tree[Token] | Token


class TypeCheck(TypeCheckerVisitor, ErrorStorage):
    def __init__(
        self,
        source: str,
        file: Path,
        defcol: DefinitionCollector,
        node: Tree[Token],
    ):
        ErrorStorage.__init__(self, source, file)
        self.defcol = defcol
        self.visit(node)

    def NULL(self, token: Token):
        return Type.NULL

    def INT(self, token: Token):
        return Type.INT

    def FLOAT(self, token: Token):
        return Type.FLOAT

    def STRING(self, token: Token):
        return Type.STR

    def NAME(self, token: Token):
        ...

    def expr(self, node: Tree[Token], types: list[Type.T]):
        return types[0]

    def add(self, node: Tree[Token], types: list[Type.T]):
        def aux(right: Node, left_type: Type.T, right_type: Type.T):
            if left_type == Type.INT:
                if right_type in (Type.INT, Type.FLOAT):
                    return right_type
                self.add_error(
                    Error(
                        f"expected int|float but got {right_type}.",
                        Range.new(right),
                        help="Try using float().",
                    )
                )
                return Type.INT
            if left_type == Type.FLOAT:
                if right_type not in (Type.INT, Type.FLOAT):
                    self.add_error(
                        Error(
                            f"expected int|float but got {right_type}.",
                            Range.new(right),
                            help="Try using float().",
                        )
                    )
                return Type.FLOAT
            if left_type == Type.STR:
                if right_type != Type.STR:
                    self.add_error(
                        Error(
                            f"expected str but got {right_type}.",
                            Range.new(right),
                            help="Try using str().",
                        )
                    )
                return Type.STR

        if ok := aux(node.children[1], types[0], types[1]):
            return ok
        if ok := aux(node.children[0], types[1], types[0]):
            return ok
        self.add_error(
            Error(
                f"expected int|float|str but got {types[0]}",
                Range.new(node.children[0]),
            )
        )
        return Type.FLOAT

    def __binary(self, node: Tree[Token], types: list[Type.T]):
        def aux(right: Node, left_type: Type.T, right_type: Type.T):
            if left_type == Type.INT:
                if right_type in (Type.INT, Type.FLOAT):
                    return right_type
                self.add_error(
                    Error(
                        f"expected int|float but got {right_type}.",
                        Range.new(right),
                        help="Try using float().",
                    )
                )
                return Type.INT
            if left_type == Type.FLOAT:
                if right_type not in (Type.INT, Type.FLOAT):
                    self.add_error(
                        Error(
                            f"expected int|float but got {right_type}.",
                            Range.new(right),
                            help="Try using float().",
                        )
                    )
                return Type.FLOAT

        if ok := aux(node.children[1], types[0], types[1]):
            return ok
        if ok := aux(node.children[0], types[1], types[0]):
            return ok
        self.add_error(
            Error(
                f"expected int|float but got {types[0]}",
                Range.new(node.children[0]),
            )
        )
        return Type.FLOAT

    sub = __binary
    mul = __binary
    div = __binary
    mod = __binary

    def orx(self, node: Tree[Token], types: list[Type.T]):
        return Type.UNION(types[0], types[1]).without(Type.NULL)

    def andx(self, node: Tree[Token], types: list[Type.T]):
        return Type.UNION(types[0], types[1]).without(Type.NULL)

    def set(self, node: Tree[Token], types: list[Type.T]):
        print(node)
        print(types)


class Linter(Visitor[Token], ErrorStorage):
    def __init__(
        self, source: str, file: Path, defcol: DefinitionCollector, node: Tree[Token]
    ):
        super().__init__(source, file)
        self.defcol = defcol
        self.visit(node)

    def call(self, node: Tree[Token]):
        name = cast(Token, node.children[0])
        arguments = cast(list[Tree[Token]], node.children[1:])
        if arguments == [None]:
            arguments = []
        if function := self.defcol.functions.get(str(name)):
            if len(arguments) < len(function.arguments):
                missing = function.arguments[len(arguments) :]
                self.add_error(
                    Error(
                        error=f"Too few arguments.",
                        help=f"Missing: {', '.join(missing)}",
                        range=Range.new(node),
                    )
                )
            elif len(arguments) > len(function.arguments):
                self.add_error(
                    Error(
                        error="Too many arguments.",
                        help=f"Foo takes {len(function.arguments)} arguments.",
                        range=Range.new(node),
                    )
                )
        else:
            self.add_error(Error(error="Undefined function.", range=Range.new(name)))


def builtin(name: str):
    def foo(self: "Compiler", node: Tree[Token]):
        self.write(f"({name} ")
        for i in node.children:
            if i is None:  # type:ignore
                continue
            self.write(" ")
            self.visit(i)
        self.write(")")

    return foo


class Compiler(Interpreter, ErrorStorage):
    def __init__(self, source: str, file: Path, output: Path, root: Tree[Token]):
        super().__init__(source, file)
        self.output = output.open("w")
        self.visit(root)
        self.write("\n")
        # closing stdout is safe and does nothing.
        # <https://docs.python.org/3/faq/library.html#why-doesn-t-closing-sys-stdout-stdin-stderr-really-close-it>
        self.output.close()

    start = Interpreter.visitchildren
    expr = Interpreter.visitchildren

    def write(self, s: str):
        self.output.write(s)

    def INT(self, t: Token):
        self.write(t)

    NAME = INT
    NULL = NAME
    BOOL = NAME
    STRING = NAME
    FLOAT = NAME

    def function(self, node: Tree[Token]):
        name = node.children[1]
        args = node.children[2:-1]
        if args == [None]:
            args = []
        self.write(f"(defun ({name} {' '.join(map(str,args))})")
        self.visit(node.children[-1])
        self.write(")")

    def block(self, node: Tree[Token]):
        self.write("(")
        for i in node.children:
            if i is None:  # type:ignore
                continue
            self.visit(i)
            self.write(" ")
        self.write(")")

    def set(self, node: Tree[Token]):
        name = node.children[0]
        op = cast(Token, node.children[1])
        self.write(f"(set {name} ")
        if op == "=":
            self.visit(node.children[2])
        elif op == "+=":
            self.write(f"(+ {name} ")
            self.visit(node.children[2])
            self.write(")")
        elif op == "-=":
            self.write(f"(- {name} ")
            self.visit(node.children[2])
            self.write(")")
        elif op == "*=":
            self.write(f"(* {name} ")
            self.visit(node.children[2])
            self.write(")")
        elif op == "/=":
            self.write(f"(/ {name} ")
            self.visit(node.children[2])
            self.write(")")
        elif op == "%=":
            self.write(f"(% {name} ")
            self.visit(node.children[2])
            self.write(")")
        self.write(")")

    def ifelse(self, node: Tree[Token]):
        self.write("(if ")
        self.visit(node.children[0])
        self.write(" ")
        self.visit(node.children[1])
        self.write(" else ")
        self.visit(node.children[2])
        self.write(")")

    def ifelif(self, node: Tree[Token]):
        self.write("(if ")
        self.visit(node.children[0])
        self.write(" ")
        self.visit(node.children[1])
        self.write(" else ")
        self._elif(node.children[2:])
        self.write(")")

    def ifelifelse(self, node: Tree[Token]):
        self.write("(if ")
        self.visit(node.children[0])
        self.write(" ")
        self.visit(node.children[1])
        self.write(" else ")
        self._elif(node.children[2:])
        self.write(")")

    def _elif(self, args: list[Tree[Token] | Token]):
        self.write("(if ")
        self.visit(args[0])
        self.write(" ")
        self.visit(args[1])
        if len(args) == 3:
            self.write(" else ")
            self.visit(args[-1])
        elif len(args) > 2:
            self.write(" else ")
            self._elif(args[2:])
        self.write(")")

    def table(self, node: Tree[Token]):
        self.write("(table ")
        it = iter(node.children)
        for a, b in zip(it, it):
            self.write(repr(str(a)).replace('"', '\\"').replace("'", '"'))
            self.write(" ")
            self.visit(b)
            self.write(" ")
        self.write(")")

    def tableitem(self, node: Tree[Token]):
        self.write("(item ")
        self.visit(node.children[0])
        self.write(" ")
        self.write(repr(str(node.children[1])).replace('"', '\\"').replace("'", '"'))
        self.write(")")

    def settableitem(self, node: Tree[Token]):
        self.write("(setitem ")
        self.visit(node.children[0])
        self.write(" ")
        self.write(repr(str(node.children[1])).replace('"', '\\"').replace("'", '"'))
        self.write(" ")
        self.visit(node.children[2])
        self.write(")")

    ternary = builtin("ternary")
    walrus = builtin("set")
    list = builtin("list")
    tuple = builtin("tuple")
    print = builtin("print")
    add = builtin("+")
    sub = builtin("-")
    mul = builtin("*")
    div = builtin("/")
    mod = builtin("%")
    minus = builtin("-")
    andx = builtin("&")
    orx = builtin("|")
    notx = builtin("!")
    index = builtin("index")
    len = builtin("len")
    setitem = builtin("setitem")
    getitem = builtin("item")
    returnx = builtin("return")
    ifx = builtin("if")
    whilex = builtin("while")
    bool = builtin("bool")
    int = builtin("int")
    float = builtin("float")
    str = builtin("str")
    eq = builtin("=")
    lt = builtin("<")
    gt = builtin(">")
    forx = builtin("for")
    push = builtin("push")
    remove = builtin("remove")
    type = builtin("type")
    call = block

    def neq(self, node: Tree[Token]):
        self.write("(! (= ")
        self.visit(node.children[0])
        self.write(" ")
        self.visit(node.children[1])
        self.write("))")

    def lteq(self, node: Tree[Token]):
        self.write("(! (> ")
        self.visit(node.children[0])
        self.write(" ")
        self.visit(node.children[1])
        self.write("))")

    def gteq(self, node: Tree[Token]):
        self.write("(! (< ")
        self.visit(node.children[0])
        self.write(" ")
        self.visit(node.children[1])
        self.write("))")


def compile(input: Path, output: Path):
    errors: list[Error] = []
    source = input.read_text()
    try:
        root = parser.parse(source)
    except UnexpectedCharacters as err:
        help = ""
        if "SEMICOLON" in err.allowed:
            help = "Perhaps your missing a semicolon."
        errors.append(
            Error(
                error="Unexpected Character",
                range=Range(err.line - 1, err.column - 1, 1),
                source=source,
                help=help,
                file=input,
            )
        )
        return errors
    defcol = DefinitionCollector(source, input, root)
    errors.extend(defcol.errors)
    linter = Linter(source, input, defcol, root)
    errors.extend(linter.errors)
    # typechecker = TypeCheck(source, input, defcol, root)
    # errors.extend(typechecker.errors)
    compiler = Compiler(source, input, output, root)
    errors.extend(compiler.errors)
    return errors
