import argparse
import subprocess
from pathlib import Path

from . import compile
from . import term as t

argparser = argparse.ArgumentParser(
    prog="onyoc",
    description="Compiler for the onyo programming language.",
    epilog="<https://github.com/aspizu/onyo>",
)

argparser.add_argument(
    "-input",
    help="Source file to compile.",
)

argparser.add_argument(
    "-output",
    default=None,
    help="Path to output file. If not given, onyo will be executed.",
)

argparser.add_argument(
    "--onyo-path",
    default="/usr/local/bin/onyo",
    help="Path to the onyo interpreter executable.",
)

args = argparser.parse_args()
input: Path = Path(args.input)
output: Path | None = Path(args.output) if args.output else None
onyo_path: Path = Path(args.onyo_path)


if output:
    errors = compile(input, output)
    for error in errors:
        error.print()
else:
    output = Path("/tmp/onyoc")
    errors = compile(input, output)
    for error in errors:
        error.print()
    if errors:
        t.w(f"{t.brred}--> Too many errors, cannot proceed.{t.reset}\n")
        exit(1)
    subprocess.run([onyo_path.absolute().as_posix(), output.absolute().as_posix()])
    output.unlink()
