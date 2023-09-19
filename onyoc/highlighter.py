""" HTML Syntax Highlighter for onyo  """
from dataclasses import dataclass
from typing import IO, cast

import lark
from lark.lexer import Token

from . import *


@dataclass
class HighlightedToken:
   token: Token
   cls: str


class Visitor:
   def visit(self, node: Node):
      if node is None:  # type: ignore
         return
      if isinstance(node, lark.Tree):
         for child in node.children:
            self.visit(child)
         func = getattr(self, node.data, self._default_tree)
         return func(node)
      else:
         func = getattr(self, node.type, self._default_token)
         return func(node)

   def _default_tree(self, node: Node):
      ...

   def _default_token(self, token: Token):
      ...


class Highlighter(Visitor):
   def __init__(self, source: str, out: IO[str]):
      try:
         root = parser_keep_all_tokens.parse(source)
      except lark.exceptions.LarkError:
         try:
            root = parser_keep_all_tokens_raw_block.parse(source)
         except lark.exceptions.LarkError:
            root = parser_keep_all_tokens_expr.parse(source)
      self.tokens: list[HighlightedToken] = []
      self.source = source
      self.out = out
      self.i = 0
      self.line = 1
      self.column = 1
      self.visit(root)
      self.tokens.sort(key=lambda i: (i.token.line, i.token.column))
      for token in self.tokens:
         self.highlight_token(token.token, token.cls)
      self.write_until_end()

   def write_until_end(self):
      self.out.write(self.source[self.i :])

   def write_line(self):
      while self.i < len(self.source) and (c := self.source[self.i]) != "\n":
         self.out.write(c)
         self.i += 1
      self.out.write("\n")
      self.i += 1
      self.line += 1
      self.column = 1

   def write_until_token(self, token: Token):
      assert token.line is not None
      assert token.column is not None
      assert token.line >= self.line
      while self.line < token.line:
         self.write_line()
      delta = token.column - self.column
      self.out.write(self.source[self.i : self.i + delta])
      self.column += delta
      self.i += delta

   def write_token(self, token: Token):
      assert token.line is not None
      assert token.column is not None
      assert self.line == token.line
      assert self.column == token.column
      self.out.write(self.source[self.i : self.i + len(token)])
      self.column += len(token)
      self.i += len(token)

   def highlight_token(self, token: Token, cls: str):
      self.write_until_token(token)
      self.out.write(f'<span class="{cls}">')
      self.write_token(token)
      self.out.write("</span>")

   def add_token_for_highlighting(self, token: Token, cls: str):
      self.tokens.append(HighlightedToken(token, cls))

   def func(self, node: Tree):
      name = cast(Token, node.children[0])
      self.add_token_for_highlighting(name, cls="function")
      for token in optional_list(node.children[2:-2]):
         self.add_token_for_highlighting(token, cls="parameter")

   def structdef(self, node: Tree):
      children = iter(node.children)
      self.add_token_for_highlighting(cast(Token, next(children)), cls="struct")
      for child in children:
         if child is None or isinstance(child, lark.Tree):  # type: ignore
            break
         self.add_token_for_highlighting(child, cls="field")

   def ret(self, node: Tree):
      keyword = cast(Token, node.children[0])
      self.add_token_for_highlighting(keyword, cls="keyword")

   def eval(self, node: Tree):
      keyword = cast(Token, node.children[0])
      self.add_token_for_highlighting(keyword, cls="keyword")

   def whilebranch(self, node: Tree):
      keyword = cast(Token, node.children[0])
      self.add_token_for_highlighting(keyword, cls="keyword")

   def forloop(self, node: Tree):
      keyword = cast(Token, node.children[0])
      self.add_token_for_highlighting(keyword, cls="keyword")
      keyword = cast(Token, node.children[2])
      self.add_token_for_highlighting(keyword, cls="keyword")

   def dowhile(self, node: Tree):
      keyword = cast(Token, node.children[0])
      self.add_token_for_highlighting(keyword, cls="keyword")
      keyword = cast(Token, node.children[2])
      self.add_token_for_highlighting(keyword, cls="keyword")

   def ifblock(self, node: Tree):
      keyword = cast(Token, node.children[0])
      self.add_token_for_highlighting(keyword, cls="keyword")

   def ifelse(self, node: Tree):
      keyword = cast(Token, node.children[0])
      self.add_token_for_highlighting(keyword, cls="keyword")
      keyword = cast(Token, node.children[3])
      self.add_token_for_highlighting(keyword, cls="keyword")

   def ifelif(self, node: Tree):
      children = iter(node.children)
      for child in children:
         keyword = cast(Token, child)
         self.add_token_for_highlighting(keyword, cls="keyword")
         next(children)
         next(children)

   def ifelifelse(self, node: Tree):
      children = iter(node.children)
      for child in children:
         keyword = cast(Token, child)
         self.add_token_for_highlighting(keyword, cls="keyword")
         next(children)
         next(children, None)

   def struct(self, node: Tree):
      children = iter(node.children)
      keyword = cast(Token, next(children))
      self.add_token_for_highlighting(keyword, cls="struct")
      next(children)
      for child in children:
         if child == ",":
            continue
         if child == "}":
            break
         keyword = cast(Token, child)
         self.add_token_for_highlighting(keyword, cls="field")
         next(children)
         next(children)

   def branch(self, node: Tree):
      self.add_token_for_highlighting(cast(Token, node.children[0]), cls="keyword")
      self.add_token_for_highlighting(cast(Token, node.children[2]), cls="keyword")
      self.add_token_for_highlighting(cast(Token, node.children[4]), cls="keyword")

   def orbranch(self, node: Tree):
      self.add_token_for_highlighting(cast(Token, node.children[1]), cls="operator")

   def andbranch(self, node: Tree):
      self.add_token_for_highlighting(cast(Token, node.children[1]), cls="operator")

   def identity(self, node: Tree):
      self.add_token_for_highlighting(cast(Token, node.children[1]), cls="operator")

   def knot(self, node: Tree):
      self.add_token_for_highlighting(cast(Token, node.children[0]), cls="operator")

   def call(self, node: Tree):
      name = cast(Token, node.children[0])
      self.add_token_for_highlighting(name, cls="function")

   def setfield(self, node: Tree):
      self.add_token_for_highlighting(cast(Token, node.children[2]), cls="field")

   def getfield(self, node: Tree):
      name = cast(Token, node.children[2])
      self.add_token_for_highlighting(name, cls="field")

   def NIL(self, token: Token):
      self.add_token_for_highlighting(token, cls="nil")

   def ITEREND(self, token: Token):
      self.add_token_for_highlighting(token, cls="iterend")

   def BOOL(self, token: Token):
      self.add_token_for_highlighting(token, cls="bool")

   def STRING(self, token: Token):
      self.add_token_for_highlighting(token, cls="str")

   def INT(self, token: Token):
      self.add_token_for_highlighting(token, cls="int")

   def FLOAT(self, token: Token):
      self.add_token_for_highlighting(token, cls="float")


def collapse(node: Tree, data: str) -> Node:
   if node.data == data:
      return collapse(cast(Tree, node.children[0]), data)
   return node
