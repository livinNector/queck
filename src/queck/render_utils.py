import json
from importlib.resources import files

import css_inline
import mdformat
from jinja2 import Environment, PackageLoader, Template, select_autoescape
from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
from mdformat_gfm_alerts.mdit_plugins import gfm_alerts_plugin
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer

from . import templates
from .mdit_plugins import css_inline_plugin, fence_default_lang_plugin, pygments_plugin


def md_format(text):
    return mdformat.text(
        text,
        options={"wrap": 80},
        extensions={"gfm", "gfm_alerts", "dollarmath", "simple_breaks"},
    ).strip()


def dollarmath_renderer(content, config=None):
    display_mode = config and config.get("display_mode", False)
    delimeter = "$$" if display_mode else "$"
    return f"{delimeter}{escapeHtml(content)}{delimeter}"


def get_base_md(math_renderer=None, default_code_lang=None):
    if math_renderer is None:
        math_renderer = dollarmath_renderer
    if default_code_lang is None:
        default_code_lang = "text"
    return (
        MarkdownIt("gfm-like")
        .use(fence_default_lang_plugin, default_lang=default_code_lang)
        .use(dollarmath_plugin, renderer=math_renderer, double_inline=True)
        .use(tasklists_plugin, enabled=True)
        .use(
            gfm_alerts_plugin,
            icons=json.loads(files(templates).joinpath("gh_alerts.json").read_text()),
        )
    )


default_css = (
    files(templates).joinpath("base.css").read_text()
    + files(templates).joinpath("default.css").read_text()
)
md = {}
md["fast"] = get_base_md()
md["compat"] = (
    get_base_md().use(pygments_plugin).use(css_inline_plugin, css=default_css)
)


def get_template_env(**filters):
    env = Environment(
        loader=PackageLoader("queck", "templates"), autoescape=select_autoescape()
    )
    env.filters.update(filters)
    return env


templates = {}
templates["md"] = get_template_env(mdformat=md_format).get_template(
    "queck_template.md.jinja", globals={"format": "md"}
)
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
