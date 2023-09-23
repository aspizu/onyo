import argparse
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

from . import parser
from .highlighter import Highlighter
from .I import I
from .preprocessor import preprocessor

argparser = argparse.ArgumentParser(
   prog="onyoc",
   description="Text-based compiler front-end for the onyo programming language.",
   epilog="Homepage: <https://github.com/aspizu/onyo>",
)


def type_input(argument: str):
   path = Path(argument)
   if not path.exists():
      raise argparse.ArgumentTypeError(f"{path}: No such file or directory.")
   if path.is_dir():
      raise argparse.ArgumentTypeError(f"{path}: Is a directory.")
   return path


def type_output(argument: str):
   path = Path(argument)
   if path.is_dir():
      raise argparse.ArgumentTypeError(f"{path}: Is a directory.")
   return path


def type_interpreter_path(argument: str):
   path = Path(argument)
   if not path.exists():
      raise argparse.ArgumentTypeError(f"{path}: No such file or directory.")
   if path.is_dir():
      raise argparse.ArgumentTypeError(f"{path}: Is a directory.")
   return path


argparser.add_argument("--syntax-highlight", action=argparse.BooleanOptionalAction, default=False)
argparser.add_argument("-i", "--input", help="Source file.", type=type_input, required=True)
argparser.add_argument("-o", "--output", help="Output json file. Leave empty to run onyo.", type=type_output)
argparser.add_argument("-p", "--interpreter-path", help="Path to the interpreter executable.", type=type_interpreter_path)
argparser.add_argument("args", nargs="*", help="Arguments to be passed to the program. Will be ignored if --output is given.")
args = argparser.parse_args()
syntax_highlight: bool = args.syntax_highlight
input_path: Path = args.input
output_path: Path | None = args.output
interpreter_path: Path = args.interpreter_path or Path("onyo-rs")
program_args: list[str] = args.args
if syntax_highlight:
   if output_path is None:
      output_path = Path("/dev/stdout")
   source = input_path.read_text()
   highlighter = Highlighter(source, output_path.open("w"))
elif output_path is None:
   tempfile = NamedTemporaryFile("w", delete=False)
   tempfile_path = Path(tempfile.name)
   source = input_path.read_text()
   root = parser.parse(preprocessor(source))
   i = I(root)
   if 0 < len(i.errors):
      i.summary(input_path, source)
      exit(1)
   i.package(input_path.as_posix(), tempfile)
   tempfile.close()
   subprocess.run([interpreter_path.as_posix(), tempfile_path.as_posix(), *program_args])
   tempfile_path.unlink()
else:
   source = input_path.read_text()
   root = parser.parse(source)
   i = I(root)
   i.package(input_path.as_posix(), output_path.open("w"))
