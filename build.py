from pathlib import Path
from subprocess import PIPE, run
from typing import Sequence

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict


class Renderer(RendererHTML):
   def fence(self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType) -> str:
      content = tokens[idx].content
      if tokens[idx].info == "onyo":
         content = run(
            ["onyoc", "--syntax-highlight", "-i", "/dev/stdin"], stdout=PIPE, input=content.encode("utf-8")
         ).stdout.decode("utf-8")
      return "<pre><code>" + content + "</code></pre>"


md = MarkdownIt("gfm-like", renderer_cls=Renderer)


template = (
   """
<!DOCTYPE html>
<html lang="en-US">
<head>
<meta charset="utf-8" />
<title>README</title>
<style>
"""
   + Path("docs/style.css").read_text()
   + """
</style>
</head>
<body>
"""
)

template_end = """
</body>
</html>
"""

with Path("docs/README.html").open("w") as f:
   src = Path("README.md").read_text()
   f.write(template)
   f.write(md.render(src))
   f.write(template_end)
