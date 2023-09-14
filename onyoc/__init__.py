from difflib import get_close_matches
from importlib.resources import files
from typing import Any, Iterable, TypeVar

import lark

from . import res

T = TypeVar("T")
Tree = lark.Tree[lark.lexer.Token]
Node = Tree | lark.lexer.Token

parser = lark.Lark((files(res) / "grammar.lark").read_text(), parser="earley", propagate_positions=True)


def optional_list(l: list[Any]):
   return [] if l == [None] else l


def typo(a: str, b: Iterable[str]):
   v = get_close_matches(a, b)
   if len(v) > 0:
      return v[0]
