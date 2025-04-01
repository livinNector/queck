from importlib.resources import files

import css_inline
import mdformat
from jinja2 import Environment, PackageLoader, select_autoescape
from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
from mdit_py_plugins.amsmath import amsmath_plugin
from mdit_py_plugins.container import container_plugin
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from . import templates
from .gh_alert_mdit import md_it_github_alerts


def md_format(text):
    return mdformat.text(
        text,
        options={"wrap": 80},
        extensions={"gfm", "gfm_alerts", "dollarmath", "simple_breaks"},
    ).strip()


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
            cssstyles="""
            padding:10px;
            border-radius:5px;
            border: thin solid #ddd;
            margin:.5rem 0;
            font-size:85%;
            """,
            prestyles="border:none;",
        )

        highlighted_code = highlight(content, lexer, formatter)

        return highlighted_code

    md.add_render_rule("fence", render_code_block, fmt="html")


def css_inline_plugin(md, css=""):
    render = md.render

    def inline_css(x):
        out = f"<main>{render(x)}</main>"
        return css_inline.inline_fragment(out, css=css)

    md.render = inline_css


def dollor_math_renderer(content, config):
    display_mode = config["display_mode"]
    delimeter = "$$" if display_mode else "$"
    return f"{delimeter}{escapeHtml(content)}{delimeter}"


def get_base_md():
    return (
        MarkdownIt("gfm-like")
        .use(tasklists_plugin, enabled=True)
        .use(container_plugin, name="no-break")
        .use(md_it_github_alerts)
    )


def get_fast_md():
    return (
        get_base_md()
        .use(dollarmath_plugin, renderer=dollor_math_renderer, double_inline=True)
        .use(amsmath_plugin)
    )


default_css = (
    files(templates).joinpath("base.css").read_text()
    + files(templates).joinpath("default.css").read_text()
)
md = {}
md["base"] = get_base_md()
md["fast"] = get_fast_md()
md["compat"] = (
    get_fast_md().use(pygments_plugin).use(css_inline_plugin, css=default_css)
)


def get_template_env(**filters):
    env = Environment(
        loader=PackageLoader("queck", "templates"), autoescape=select_autoescape()
    )
    env.filters["chr"] = chr
    env.filters.update(filters)
    return env


templates = {}
templates["md"] = get_template_env(mdformat=md_format).get_template(
    "queck_template.md.jinja"
)
templates["queck"] = get_template_env().get_template("queck_template.yaml.jinja")
templates["fast"] = get_template_env(
    md=md["fast"].render, mdformat=md_format
).get_template(
    "queck_template.html.jinja", globals={"render_mode": "fast", "format": "html"}
)
templates["latex"] = get_template_env(
    md=md["fast"].render, mdformat=md_format
).get_template(
    "queck_template.html.jinja", globals={"render_mode": "latex", "format": "html"}
)
templates["compat"] = get_template_env(
    md=md["compat"].render, mdformat=md_format
).get_template("queck_template.html.jinja", globals={"format": "html"})
