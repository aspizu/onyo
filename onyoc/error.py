from dataclasses import dataclass
from pathlib import Path

from lark.lexer import Token

from . import term as t


@dataclass
class Range:
   line: int
   column: int
   length: int

   @staticmethod
   def from_token(token: Token):
      assert token.line is not None
      assert token.column is not None
      return Range(token.line - 1, token.column - 1, len(token))


class ErrorStorage:
   def add_error(
      self,
      msg: str,
      range: Range | None = None,
      suggestion: tuple[str, Range, str] | None = None,
      typo: str | None = None,
   ):
      self.errors.append(Error(msg, range, suggestion, typo))

   def errors_from(self, storage: "ErrorStorage"):
      self.errors.extend(storage.errors)

   def summary(self, path: Path, source: str):
      for error in self.errors:
         error.print(path, source)
      t.w(f"\n{t.bold}{t.brred}generated {len(self.errors)} errors{t.reset}\n")

   def __init__(self):
      self.errors: list[Error] = []


@dataclass
class Error:
   msg: str
   range: Range | None
   suggestion: tuple[str, Range, str] | None
   typo: str | None = None

   def print(self, path: Path, source: str):
      t.w(f"{t.bold}{t.brred}error: {t.reset}{t.bold}{self.msg}{t.reset}\n")
      t.w(f"{t.brcyan}->{t.reset} {path}")
      if self.range:
         t.w(f":{self.range.line+1}:{self.range.column+1}")
      t.w("\n")

      if range := self.range:
         pager = Pager(source, range.line - 1)
         pager.advance(2)

         t.w("     | " + " " * range.column + t.bold + t.brcyan + "^" * range.length + t.reset)
         if self.typo:
            t.w(f"{t.bryellow} Did you mean `{self.typo}`?{t.reset}")
         t.w("\n")

         pager.advance(2)

      if self.suggestion:
         suggestion_msg, suggestion_range, suggestion = self.suggestion
         t.w(f"{t.brgreen}{suggestion_msg}{t.reset}\n")
         pager = Pager(source, suggestion_range.line - 2)
         pager.advance_until(suggestion_range.line)
         for line in suggestion.splitlines():
            t.w(f"{t.bold}{t.brgreen} +++ | {line}{t.reset}\n")
         pager.advance(1)


class Pager:
   def __init__(self, source: str, start: int):
      self.line = -1
      self.source = iter(source.splitlines())
      for _ in range(start):
         if next(self, None) is None:
            break

   def __next__(self) -> str:
      self.line += 1
      return next(self.source)

   def advance_until(self, line: int):
      while self.line < line - 1:
         self.advance(1)

   def advance(self, lines: int):
      if lines < 0:
         return
      for _ in range(lines):
         if (line := next(self, None)) is not None:
            t.w(f" {self.line+1: 3} | {line}\n")
         else:
            break
