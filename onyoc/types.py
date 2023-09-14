from dataclasses import dataclass
from enum import auto

from .serde import *


class ExecT:
   ...


class LiteralT:
   ...


Block = list[ExecT]


@dataclass
class Data(Struct):
   functions: list["Function"]


@dataclass
class Function(Struct):
   name: str
   parameters: list[str]
   variables: list[str]
   body: Block


class Literal(ExternallyTaggedEnum):
   @dataclass
   class Nil(LiteralT, ValueEnum):
      _: None = None

   @dataclass
   class Bool(LiteralT, ValueEnum):
      _: bool

   @dataclass
   class Int(LiteralT, ValueEnum):
      _: int

   @dataclass
   class Float(LiteralT, ValueEnum):
      _: float

   @dataclass
   class Str(LiteralT, ValueEnum):
      _: str


class UnaryOperator(Enum):
   Not = auto()
   BitNot = auto()
   Minus = auto()
   Type = auto()
   Err = auto()
   Bool = auto()
   Int = auto()
   Float = auto()
   Str = auto()
   Len = auto()
   Print = auto()
   Read = auto()


class BinaryOperator(Enum):
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
   Write = auto()


class TernaryOperator(Enum):
   Branch = auto()
   SetItem = auto()


class NaryOperator(Enum):
   Tuple = auto()
   List = auto()


class ReferenceT:
   ...


class Reference(ExternallyTaggedEnum):
   @dataclass
   class Variable(ReferenceT, ValueEnum):
      _: int

   @dataclass
   class Function(ReferenceT, ValueEnum):
      _: int


class ExprT:
   ...


class Exec(InternallyTaggedEnum):
   @dataclass
   class While(ExecT, Struct):
      condition: ExprT
      block: Block

   @dataclass
   class DoWhile(ExecT, Struct):
      block: Block
      condition: ExprT

   @dataclass
   class Branch(ExecT, Struct):
      condition: ExprT
      then: Block
      otherwise: Block

   @dataclass
   class Return(ExecT, Struct):
      expr: ExprT

   @dataclass
   class Expr(ExecT, Struct):
      expr: ExprT


class Expr(InternallyTaggedEnum):
   @dataclass
   class Literal(ExprT, Struct):
      literal: LiteralT

   @dataclass
   class Reference(ExprT, Struct):
      reference: ReferenceT

   @dataclass
   class UnaryOperation(ExprT, Struct):
      operator: UnaryOperator
      expr: ExprT

   @dataclass
   class BinaryOperation(ExprT, Struct):
      operator: BinaryOperator
      left: ExprT
      right: ExprT

   @dataclass
   class TernaryOperation(ExprT, Struct):
      operator: TernaryOperator
      first: ExprT
      second: ExprT
      third: ExprT

   @dataclass
   class NaryOperation(ExprT, Struct):
      operator: NaryOperator
      parameters: list[ExprT]

   @dataclass
   class Call(ExprT, Struct):
      variable: ReferenceT
      parameters: list[ExprT]

   @dataclass
   class Dict(ExprT, Struct):
      pairs: list[tuple[ExprT, ExprT]]

   @dataclass
   class SetVar(ExprT, Struct):
      variable: ReferenceT
      expr: ExprT
