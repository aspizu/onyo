from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import cast

from lark import Lark, Token, Tree, UnexpectedCharacters
from lark.visitors import Visitor

from . import res

parser = Lark(
    (files(res) / "grammar.lark").read_text(),
    parser="earley",
    propagate_positions=True,
)
from . import term as t


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
            return cls(token.line - 1, token.column - 1, len(token))
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
                    + " " * (6 + self.range.column)
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
            if func := getattr(self, node.type):
                func(node)
        else:
            if func := getattr(self, node.data):
                func(node)

    def visitchildren(self, node: Tree[Token]):
        for i in node.children:
            self.visit(i)


@dataclass
class Function:
    name: Token
    arguments: list[Token]
    body: Tree[Token]


class DefinitionCollector(Interpreter, ErrorStorage):
    def __init__(self, source: str, file: Path, root: Tree[Token]):
        super().__init__(source, file)
        self.functions: dict[str, Function] = {}
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
        self.functions[str(name)] = Function(name, arguments, body)


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

    ternary = builtin("ternary")
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
    compiler = Compiler(source, input, output, root)
    errors.extend(compiler.errors)
    return errors
