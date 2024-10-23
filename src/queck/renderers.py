from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin
from mdit_py_plugins.container import container_plugin

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

from jinja2 import Environment, PackageLoader, select_autoescape

# Initialize the Jinja2 environment with package loader and autoescaping
package_env = Environment(
    loader=PackageLoader("queck", "templates"), autoescape=select_autoescape()
)

from typing import Literal
from .quiz_models import Quiz


def pygments_plugin(md):
    def render_code_block(self, tokens, idx, options, env):
        token = tokens[idx]
        content = token.content
        language = token.info.strip() if token.info else "text"
        try:
            lexer = get_lexer_by_name(language)
        except ValueError:
            lexer = get_lexer_by_name("text")

        formatter = HtmlFormatter(
            noclasses=True,
            cssstyles="padding:10px; border-radius:5px;border: thin solid #ddd;margin-bottom:.5em;",
            prestyles="padding:0px; margin:0px;",
        )

        highlighted_code = highlight(content, lexer, formatter)

        return highlighted_code

    md.add_render_rule("fence", render_code_block, fmt="html")


fast = (
    MarkdownIt("gfm-like").use(tasklists_plugin).use(container_plugin, name="no-break")
)

compat = (
    MarkdownIt("gfm-like")
    .use(tasklists_plugin)
    .use(container_plugin, name="no-break")
    .use(pygments_plugin)
)


def render_quiz(
    quiz: Quiz,
    format: Literal["html", "md"] = "html",
    render_mode: Literal["fast", "compat"] = "fast",
):
    # Set the rendering mode
    match render_mode:
        case "fast":
            package_env.filters["md"] = fast.render
        case "compat":
            package_env.filters["md"] = compat.render
        case _:
            raise ValueError(f'render_mode must be one of "fast" or "compat" ')

    # Choose the template based on the format (html or md)
    match format:
        case "html":
            template = package_env.get_template("quiz_template.html.jinja")
        case "md":
            template = package_env.get_template("quiz_template.md.jinja")
        case _:
            raise ValueError(f'format must be one of "html" or "md"')

    # Render the template with the quiz data
    return template.render(quiz=quiz, format=format, render_mode=render_mode)
