from itertools import chain
from typing import TYPE_CHECKING

from lark.lexer import Token
from lark.visitors import Transformer

from . import *
from .error import ErrorStorage, Range
from .ir import *

if TYPE_CHECKING:
   from .I import I


def ternary_operation(operator: TernaryOperator):
   def f(self: "V", args: tuple[ExprT, ExprT, ExprT]):
      return Expr.TernaryOperation(operator, args[0], args[1], args[2])

   return f


def binary_operation(operator: BinaryOperator):
   def f(self: "V", args: tuple[ExprT, ExprT]):
      return Expr.BinaryOperation(operator, args[0], args[1])

   return f


def unary_operation(operator: UnaryOperator):
   def f(self: "V", args: tuple[ExprT]):
      return Expr.UnaryOperation(operator, args[0])

   return f


def flatten(self: "V", args: tuple[T]) -> T:
   return args[0]


class V(Transformer[Token, Block], ErrorStorage):
   functions = {
      "print": unary_operation(UnaryOperator.Print),
      "read": unary_operation(UnaryOperator.Read),
      "write": binary_operation(BinaryOperator.Write),
      "join": binary_operation(BinaryOperator.Join),
      "type": unary_operation(UnaryOperator.Type),
      "err": unary_operation(UnaryOperator.Err),
      "bool": unary_operation(UnaryOperator.Bool),
      "int": unary_operation(UnaryOperator.Int),
      "float": unary_operation(UnaryOperator.Float),
      "str": unary_operation(UnaryOperator.Str),
      "len": unary_operation(UnaryOperator.Len),
      "push": binary_operation(BinaryOperator.Push),
      "remove": binary_operation(BinaryOperator.Remove),
      "index": binary_operation(BinaryOperator.Index),
   }

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

   exec = flatten
   expr = flatten

   def NIL(self, token: Token):
      return Expr.Literal(Literal.Nil())

   def BOOL(self, token: Token):
      return Expr.Literal(Literal.Bool(token == "true"))

   def INT(self, token: Token):
      return Expr.Literal(Literal.Int(int(token)))

   def FLOAT(self, token: Token):
      return Expr.Literal(Literal.Float(float(token)))

   def block(self, args: list[Any]):
      return [Exec.Expr(i) if isinstance(i, ExprT) else i for i in args]

   def STRING(self, token: Token):
      return Expr.Literal(
         Literal.Str(str(token)[1:-1].replace(r"\"", '"').replace(r"\n", "\n").replace(r"\t", "\t").replace(r"\\", "\\"))
      )

   def var(self, args: tuple[Token]):
      name = args[0]
      if (variable := self.variables.get(name)) is not None:
         return Expr.Reference(Reference.Variable(variable))
      if (function := self.i.functions.get(name)) is not None:
         return Expr.Reference(Reference.Function(function[0]))
      self.add_error(f"Undefined variable `{name}`", range=Range.from_token(name), typo=typo(str(name), self.variables.keys()))
      return False

   def forloop(self, args: tuple[ReferenceT, ExprT, Block]):
      name = str(args[0])
      if (variable_id := self.variables.get(name)) is not None:
         variable = Reference.Variable(variable_id)
      else:
         variable = Reference.Variable(len(self.variables))
         self.variables[name] = variable._
      return Exec.ForLoop(variable, args[1], args[2])

   def execexpr(self, args: tuple[ExprT]):
      return Exec.Expr(args[0])

   def ret(self, args: tuple[ExprT]):
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
      return Exec.Branch(args[0], args[1], [self.elsegen(args[2:], otherwise)] if len(args) > 2 else (otherwise or []))

   def assign(self, args: tuple[Token, None, ExprT]):
      name = str(args[0])
      variable = self.variables.get(name)
      if variable is None:
         variable = len(self.variables)
         self.variables[name] = len(self.variables)
      return Expr.SetVar(Reference.Variable(variable), args[2])

   def neq(self, args: tuple[ExprT, ExprT]):
      return Expr.UnaryOperation(UnaryOperator.Not, self.eq(args))

   def gt(self, args: tuple[ExprT, ExprT]):
      return Expr.UnaryOperation(UnaryOperator.Not, self.leq(args))

   def geq(self, args: tuple[ExprT, ExprT]):
      return Expr.UnaryOperation(UnaryOperator.Not, self.lt(args))

   def call(self, args: list[Any]):
      name: Token = args[0]
      params: list[ExprT] = optional_list(args[1:])
      qualname = str(name)
      if generator := self.functions.get(qualname):
         return generator(self, params)  # type: ignore
      elif (variable := self.variables.get(name)) is not None:
         return Expr.Call(Expr.Reference(Reference.Variable(variable)), params)
      elif function := self.i.functions.get(name):
         return Expr.Call(Expr.Reference(Reference.Function(function[0])), params)
      else:
         self.add_error(
            f"Undefined function `{qualname}`",
            range=Range.from_token(name),
            typo=typo(qualname, chain(self.functions.keys(), self.i.functions.keys())),
         )

   def vcall(self, args: list[ExprT]):
      callable = args[0]
      params = optional_list(args[1:])
      return Expr.Call(callable, params)

   def struct(self, args: list[Any]):
      prototype_id, prototype = self.i.structs[str(args[0])]
      it = iter(args[1:])
      values = {}
      for field_name, field_expr in zip(it, it):
         field_qualname = str(field_name)
         values[prototype.field_map[self.i.ident_map[field_qualname]]] = field_expr
      return Expr.Struct(prototype_id, [values[field] for field in prototype.field_map.values()])

   def setfield(self, args: list[Any]):
      instance = args[0]
      field_name = args[1]
      value = args[2]
      field_qualname = str(field_name)
      return Expr.SetField(instance, self.i.ident_map[field_qualname], value)

   def getfield(self, args: list[Any]):
      instance = args[0]
      field_name = args[1]
      field_qualname = str(field_name)
      return Expr.GetField(instance, self.i.ident_map[field_qualname])

   def list(self, args: list[Any]):
      args = optional_list(args)
      return Expr.NaryOperation(NaryOperator.List, args)

   def __init__(self, i: "I", function: Function):
      ErrorStorage.__init__(self)
      self.i = i
      self.function = function
      self.variables: dict[str, int] = {}
