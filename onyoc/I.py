import json
from typing import IO, cast

from lark.lexer import Token
from lark.visitors import Interpreter

from . import *
from .error import ErrorStorage, Range
from .ir import *
from .V import V


class I(Interpreter[Token, None], ErrorStorage):
   def start(self, node: Tree):
      self.visit_children(node)

   def func(self, node: Tree, qualprefix: str | None = None) -> int:
      name = cast(Token, node.children[0])
      parameters = optional_list(node.children[1:-1])
      body = cast(Tree, node.children[-1])
      qualname = qualprefix + str(name) if qualprefix else str(name)
      qualparameters = [str(i) for i in parameters]
      if redeclaration := self.functions.get(name):
         self.add_error(f"Redeclration of function {redeclaration}")
      self.functions[qualname] = (len(self.functions), Function(qualname, qualparameters, [], []), body)
      return self.functions[qualname][0]

   def structdef(self, node: Tree):
      name = cast(Token, node.children[0])
      qualname = str(name)
      it = iter(node.children[1:])
      field_map = {}
      method_map = {}
      for current in it:
         if isinstance(current, lark.Tree) and current.data == "func":
            method_name = str(current.children[0])
            id = self.ident_map.get(method_name)
            if id is None:
               id = len(self.ident_map)
               self.ident_map[method_name] = id
            method_map[id] = self.func(current, qualname + ".")
         else:
            field_name = current
            if field_name is None:  # type: ignore
               continue
            field_qualname = str(field_name)
            id = self.ident_map.get(field_qualname)
            if id is None:
               id = len(self.ident_map)
               self.ident_map[field_qualname] = id
            field_map[id] = len(field_map)
      self.structs[name] = len(self.structs), Prototype(qualname, field_map, method_map)

   def package(self, output_file: IO[str]):
      reserved = ReservedIdents.from_ident_map(self.ident_map)
      data = Data(
         [i[1] for i in self.functions.values()],
         [i[1] for i in self.structs.values()],
         {v: k for k, v in self.ident_map.items()},
         reserved,
      )
      json.dump(to_json(data), output_file, indent=4)

   def __init__(self, root: Tree):
      ErrorStorage.__init__(self)
      self.ident_map: dict[str, int] = {}
      self.functions: dict[str, tuple[int, Function, Tree]] = {}
      self.structs: dict[str, tuple[int, Prototype]] = {}
      self.visit_children(root)
      if "main" not in self.functions:
         self.add_error("No main function", suggestion=("Consider adding a main function", Range(0, 0, 0), "main() {}"))
      for _, function, body in self.functions.values():
         v = V(self, function)
         for parameter in function.parameters:
            v.variables[parameter] = len(v.variables)
         function.body = v.transform(body)
         self.errors_from(v)
         function.variables = list(v.variables.keys())
