from dataclasses import dataclass
from enum import auto

from .serde import *


class ExecT:
   ...


class LiteralT:
   ...


Block = list[ExecT]


@dataclass
class Data(Struct_):
   functions: list["Function"]
   prototypes: list["Prototype"]
   ident_map: dict[int, str]
   reserved_idents: "ReservedIdents"


@dataclass
class ReservedIdents(Struct_):
   next: int

   @staticmethod
   def from_ident_map(ident_map: dict[str, int]):
      return ReservedIdents(next=ident_map["next"])


@dataclass
class Function(Struct_):
   name: str
   parameters: list[str]
   variables: list[str]
   body: Block


@dataclass
class Prototype(Struct_):
   name: str
   field_map: dict[int, int]
   method_map: dict[int, int]


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
   class While(ExecT, Struct_):
      condition: ExprT
      block: Block

   @dataclass
   class ForLoop(ExecT, Struct_):
      variable: ReferenceT
      iterator: ExprT
      block: Block

   @dataclass
   class DoWhile(ExecT, Struct_):
      block: Block
      condition: ExprT

   @dataclass
   class Branch(ExecT, Struct_):
      condition: ExprT
      then: Block
      otherwise: Block

   @dataclass
   class Return(ExecT, Struct_):
      expr: ExprT

   @dataclass
   class Expr(ExecT, Struct_):
      expr: ExprT


class Expr(InternallyTaggedEnum):
   @dataclass
   class Literal(ExprT, Struct_):
      literal: LiteralT

   @dataclass
   class Reference(ExprT, Struct_):
      reference: ReferenceT

   @dataclass
   class UnaryOperation(ExprT, Struct_):
      operator: UnaryOperator
      expr: ExprT

   @dataclass
   class BinaryOperation(ExprT, Struct_):
      operator: BinaryOperator
      left: ExprT
      right: ExprT

   @dataclass
   class TernaryOperation(ExprT, Struct_):
      operator: TernaryOperator
      first: ExprT
      second: ExprT
      third: ExprT

   @dataclass
   class NaryOperation(ExprT, Struct_):
      operator: NaryOperator
      parameters: list[ExprT]

   @dataclass
   class Call(ExprT, Struct_):
      callable: ExprT
      parameters: list[ExprT]

   @dataclass
   class Struct(ExprT, Struct_):
      prototype: int
      values: list[ExprT]

   @dataclass
   class SetVar(ExprT, Struct_):
      variable: ReferenceT
      expr: ExprT

   @dataclass
   class SetField(ExprT, Struct_):
      instance: ExprT
      field_id: int
      value: ExprT

   @dataclass
   class GetField(ExprT, Struct_):
      instance: ExprT
      field_id: int
