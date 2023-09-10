import json
from dataclasses import dataclass
from enum import Enum, auto
from sys import stdin
from types import NoneType
from typing import Any, TypeAlias, TypeVar, cast

import lark
from lark import Token
from rich import print

T = TypeVar("T")


def to_json(o: Any) -> Any:
   if isinstance(o, list):
      return [to_json(i) for i in o]  # type: ignore
   if isinstance(o, dict):
      return {k: to_json(v) for k, v in o.items()}  # type: ignore
   if isinstance(o, (NoneType, int, float, str)):
      return o
   return o.to_json()


def dataclass_to_json(o: object) -> dict[str, Any]:
   return to_json(o.__dict__)


class struct:
   def to_json(self) -> Any:
      return dataclass_to_json(self)


class enum(Enum):
   def to_json(self) -> Any:
      return self.name


class internally_tagged_enum:
   def __init_subclass__(cls) -> None:
      for subcls in cls.__dict__.values():
         if isinstance(subcls, type) and issubclass(subcls, struct):

            def f(subcls: type):
               def to_json(self: struct):
                  return {"type": subcls.__name__, **dataclass_to_json(self)}

               return to_json

            subcls.to_json = f(subcls)


class externally_tagged_enum:
   subclasses: list[type]

   def __init_subclass__(cls) -> None:
      for subcls in cls.__dict__.values():
         if isinstance(subcls, type) and issubclass(subcls, struct):

            def to_json(self: struct):
               return {subcls.__name__: dataclass_to_json(self)}

            subcls.to_json = to_json


class enum_tag:
   def to_json(self):
      return self.__class__.__name__


class enum_container:
   _: Any

   def to_json(self):
      return {self.__class__.__name__: to_json(self._)}


class ExecT:
   ...


Block: TypeAlias = list[ExecT]


@dataclass
class Data(struct):
   functions: list["Function"]


@dataclass
class Function(struct):
   name: str
   parameters: list[str]
   variables: list[str]
   body: Block


class LiteralT:
   ...


class Literal(externally_tagged_enum):
   @dataclass
   class Nil(LiteralT, enum_container):
      _: None = None

   @dataclass
   class Bool(LiteralT, enum_container):
      _: bool

   @dataclass
   class Int(LiteralT, enum_container):
      _: int

   @dataclass
   class Float(LiteralT, enum_container):
      _: float

   @dataclass
   class Str(LiteralT, enum_container):
      _: str


class UnaryOperator(enum):
   Not = auto()
   BitNot = auto()
   Minus = auto()
   Type = auto()
   Bool = auto()
   Int = auto()
   Float = auto()
   Str = auto()
   Len = auto()
   Print = auto()


class BinaryOperator(enum):
   Add = auto()
   Sub = auto()
   Mul = auto()
   Div = auto()
   Modulo = auto()
   GetItem = auto()
   Eq = auto()
   Is = auto()
   Lt = auto()
   Leq = auto()
   BitAnd = auto()
   BitOr = auto()
   BitXor = auto()
   LeftShift = auto()
   RightShift = auto()
   And = auto()
   Or = auto()
   Push = auto()
   Remove = auto()
   Index = auto()
   Join = auto()


class TernaryOperator(enum):
   Branch = auto()
   SetItem = auto()


class NaryOperator(enum):
   Tuple = auto()
   List = auto()


class ReferenceT:
   ...


class Reference(externally_tagged_enum):
   @dataclass
   class Variable(ReferenceT, enum_container):
      _: int

   @dataclass
   class Function(ReferenceT, enum_container):
      _: int


class ExprT:
   ...


class Exec(internally_tagged_enum):
   @dataclass
   class While(ExecT, struct):
      condition: ExprT
      block: Block

   @dataclass
   class DoWhile(ExecT, struct):
      block: Block
      condition: ExprT

   @dataclass
   class Branch(ExecT, struct):
      condition: ExprT
      then: Block
      otherwise: Block

   @dataclass
   class Return(ExecT, struct):
      expr: ExprT

   @dataclass
   class Expr(ExecT, struct):
      expr: ExprT


class Expr(internally_tagged_enum):
   @dataclass
   class Literal(ExprT, struct):
      literal: LiteralT

   @dataclass
   class Reference(ExprT, struct):
      reference: ReferenceT

   @dataclass
   class UnaryOperation(ExprT, struct):
      operator: UnaryOperator
      expr: ExprT

   @dataclass
   class BinaryOperation(ExprT, struct):
      operator: BinaryOperator
      left: ExprT
      right: ExprT

   @dataclass
   class TernaryOperation(ExprT, struct):
      operator: TernaryOperator
      first: ExprT
      second: ExprT
      third: ExprT

   @dataclass
   class NaryOperation(ExprT, struct):
      operator: NaryOperator
      parameters: list[ExprT]

   @dataclass
   class Call(ExprT, struct):
      variable: ReferenceT
      parameters: list[ExprT]

   @dataclass
   class Dict(ExprT, struct):
      pairs: list[tuple[ExprT, ExprT]]

   @dataclass
   class SetVar(ExprT, struct):
      variable: ReferenceT
      expr: ExprT


# fmt:off
grammar = r'''
start: func*
func: IDENT "(" _identlist ")" block 
block: "{" exec* "}"
exec: assign | whilebranch | dowhile | call | ifblock | ifelse | ifelif | ifelifelse | execexpr | ret
ret: "return" expr
execexpr: "eval" expr
assign: IDENT "=" expr
whilebranch: "while" expr block 
dowhile: "do" block "while" expr
ifblock: "if" expr block 
ifelse: "if" expr block "else" block 
ifelif: "if" expr block ("elif" expr block)+ 
ifelifelse: "if" expr block ("elif" expr block)+ "else" block 
expr: NIL | BOOL | INT | FLOAT |  STRING
    | IDENT -> var
    | branch
    | orbranch
    | andbranch
    | neq
    | eq | identity
    | lt
    | gt
    | leq
    | geq
    | leftshift
    | rightshift
    | bitor
    | bitxor
    | bitand
    | add
    | sub
    | mul
    | div
    | modulo
    | bitnot
    | knot
    | minus
    | getitem
    | call
    | list
    | dict
  //  | tuple
    | "(" expr ")"
tuple: expr "," | expr ("," expr)+ | "(" ")"
list: "[" _exprlist "]"
dict: "{" (IDENT":" expr)* "}"
branch: "if" expr "then" expr "else" expr
orbranch: expr "or" expr
andbranch: expr "and" expr 
neq: expr "!=" expr
eq: expr "==" expr
identity: expr "is" expr
lt: expr "<" expr
gt: expr ">" expr
leq: expr "<=" expr
geq: expr ">=" expr
leftshift: expr "<<" expr
rightshift: expr ">>" expr
bitor: expr "|" expr
bitxor: expr "^" expr
bitand: expr "&" expr
add: expr "+" expr
sub: expr "-" expr
mul: expr "*" expr
div: expr "/" expr
modulo: expr "%" expr
bitnot: "~" expr
knot: "not" expr
minus: "-" expr
getitem: expr "[" expr "]" | expr "." expr
call: IDENT "(" _exprlist ")"
_exprlist: [expr ("," expr)*] 
_identlist: [IDENT ("," IDENT)*] 
NIL: "nil"
BOOL: "true" | "false"
CPP_COMMENT: ";" /[^\n]*/
C_COMMENT: "<!--" /(.|\n)*?/ "-->"
%import common.ESCAPED_STRING -> STRING
%import common.CNAME -> IDENT
%import common.SIGNED_INT -> INT
%import common.SIGNED_FLOAT -> FLOAT
%import common.WS
%ignore WS
%ignore C_COMMENT
%ignore CPP_COMMENT
'''
# fmt:on


Tree = lark.Tree[Token]
Node = Tree | Token


def optional_list(l: list[T] | list[None]) -> list[T]:
   if l[0] == None:
      return []
   return l  # type: ignore


class I(lark.visitors.Interpreter[Token, None]):
   def __init__(self, root: Tree):
      self.functions: dict[str, tuple[int, Function]] = {}
      self.visit_children(root)

   def start(self, node: Tree):
      self.visit_children(node)

   def func(self, node: Tree):
      name = str(node.children[0])
      parameters = [str(i) for i in optional_list(node.children[1:-1])]
      body = cast(Tree, node.children[-1])
      v = V(self)
      for i in parameters:
         v.variables[i] = len(v.variables)
      self.functions[name] = (
         len(self.functions),
         Function(name, parameters, [], []),
      )
      self.functions[name][1].body = v.transform(body)
      self.functions[name][1].variables = list(v.variables.keys())


def ternary_operation(operator: TernaryOperator):
   def f(self: Any, args: list[Any]) -> Any:
      return Expr.TernaryOperation(operator, args[0], args[1], args[2])

   return f


def binary_operation(operator: BinaryOperator):
   def f(self: Any, args: list[Any]) -> Any:
      return Expr.BinaryOperation(operator, args[0], args[1])

   return f


def unary_operation(operator: UnaryOperator):
   def f(self: Any, args: list[Any]) -> Any:
      return Expr.UnaryOperation(operator, args[0])

   return f


class V(lark.visitors.Transformer[Token, Block]):
   def __init__(self, i: I):
      self.i = i
      self.variables: dict[str, int] = {}

   def start(self, args: list[Any]):
      return args[0]

   def block(self, args: list[Any]):
      return [Exec.Expr(i) if isinstance(i, ExprT) else i for i in args]

   exec = start
   expr = start

   def NIL(self, token: Token):
      return Expr.Literal(Literal.Nil())

   def BOOL(self, token: Token):
      return Expr.Literal(Literal.Bool(token == "true"))

   def INT(self, token: Token):
      return Expr.Literal(Literal.Int(int(token)))

   def FLOAT(self, token: Token):
      return Expr.Literal(Literal.Float(float(token)))

   def STRING(self, token: Token):
      return Expr.Literal(
         Literal.Str(
            str(token)[1:-1]
            .replace(r"\"", '"')
            .replace(r"\n", "\n")
            .replace(r"\t", "\t")
            .replace(r"\\", "\\"),
         )
      )

   def var(self, args: list[Any]):
      name = str(args[0])
      if (variable := self.variables.get(name)) is not None:
         return Expr.Reference(Reference.Variable(variable))
      raise ValueError(name)

   def execexpr(self, args: list[Any]):
      return Exec.Expr(args[0])

   def ret(self, args: list[Any]):
      return Exec.Return(args[0])

   def whilebranch(self, args: list[Any]):
      return Exec.While(args[0], args[1])

   def dowhile(self, args: list[Any]):
      return Exec.DoWhile(args[0], args[1])

   def ifblock(self, args: list[Any]):
      return Exec.Branch(args[0], args[1], [])

   def ifelse(self, args: list[Any]):
      return Exec.Branch(args[0], args[1], args[2])

   def ifelif(self, args: list[Any]):
      return self.elsegen(args, None)

   def ifelifelse(self, args: list[Any]):
      return Exec.Branch(args[0], args[1], [self.elsegen(args[2:], args[-1])])

   def elsegen(self, args: list[Any], otherwise: list[Any] | None):
      return Exec.Branch(
         args[0],
         args[1],
         [self.elsegen(args[2:], otherwise)] if len(args) > 2 else (otherwise or []),
      )

   def assign(self, args: list[Any]):
      name = str(args[0])
      if variable := self.variables.get(name):
         return Exec.Expr(Expr.SetVar(Reference.Variable(variable), args[1]))
      else:
         self.variables[name] = len(self.variables)
         return Exec.Expr(
            Expr.SetVar(Reference.Variable(self.variables[name]), args[1])
         )

   branch = ternary_operation(TernaryOperator.Branch)
   orbranch = binary_operation(BinaryOperator.Or)
   andbranch = binary_operation(BinaryOperator.And)
   eq = binary_operation(BinaryOperator.Eq)
   lt = binary_operation(BinaryOperator.Lt)
   leq = binary_operation(BinaryOperator.Leq)
   leftshift = binary_operation(BinaryOperator.LeftShift)
   rightshift = binary_operation(BinaryOperator.RightShift)
   bitor = binary_operation(BinaryOperator.BitOr)
   bitxor = binary_operation(BinaryOperator.BitXor)
   bitand = binary_operation(BinaryOperator.BitAnd)
   add = binary_operation(BinaryOperator.Add)
   sub = binary_operation(BinaryOperator.Sub)
   mul = binary_operation(BinaryOperator.Mul)
   div = binary_operation(BinaryOperator.Div)
   modulo = binary_operation(BinaryOperator.Modulo)
   bitnot = unary_operation(UnaryOperator.BitNot)
   knot = unary_operation(UnaryOperator.Not)
   minus = unary_operation(UnaryOperator.Minus)
   getitem = binary_operation(BinaryOperator.GetItem)

   def neq(self, args: list[Any]):
      return Expr.UnaryOperation(UnaryOperator.Not, self.eq(args))

   def gt(self, args: list[Any]):
      return Expr.UnaryOperation(UnaryOperator.Not, self.leq(args))

   def geq(self, args: list[Any]):
      return Expr.UnaryOperation(UnaryOperator.Not, self.lt(args))

   def func(self, args: list[Any]):
      name = str(args[0])
      params = [str(i) for i in optional_list(args[1:-1])]
      return Function(name, params, [], args[-1])

   def call(self, args: list[Any]):
      name = str(args[0])
      params = optional_list(args[1:])
      if name == "print":
         return Expr.UnaryOperation(UnaryOperator.Print, args[1])
      elif name == "join":
         return Expr.BinaryOperation(BinaryOperator.Join, args[1], args[2])
      elif name == "bool":
         return Expr.UnaryOperation(UnaryOperator.Bool, args[1])
      elif name == "int":
         return Expr.UnaryOperation(UnaryOperator.Int, args[1])
      elif name == "float":
         return Expr.UnaryOperation(UnaryOperator.Float, args[1])
      elif name == "str":
         return Expr.UnaryOperation(UnaryOperator.Str, args[1])
      elif name == "len":
         return Expr.UnaryOperation(UnaryOperator.Len, args[1])
      elif name == "push":
         return Expr.BinaryOperation(BinaryOperator.Push, args[1], args[2])
      elif name == "remove":
         return Expr.BinaryOperation(BinaryOperator.Remove, args[1], args[2])
      elif name == "index":
         return Expr.BinaryOperation(BinaryOperator.Index, args[1], args[2])
      elif function := self.i.functions.get(name):
         return Expr.Call(Reference.Function(function[0]), params)
      else:
         raise ValueError(name)

   def tuple(self, args: list[Any]):
      return Expr.NaryOperation(NaryOperator.Tuple, args)

   def list(self, args: list[Any]):
      return Expr.NaryOperation(NaryOperator.List, args)


parser = lark.Lark(grammar, parser="earley", propagate_positions=True)

root = parser.parse(stdin.read())
i = I(root)
print(
   json.dumps(
      to_json(
         Data(
            [i[1] for i in i.functions.values()],
         )
      ),
      indent=3,
   )
)
