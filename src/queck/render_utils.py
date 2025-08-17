import json
from importlib.resources import files
from typing import Literal

import mdformat
from jinja2 import Environment, PackageLoader, Template, select_autoescape
from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
from markdown_it.renderer import RendererHTML
from mdformat.renderer import MDRenderer
from mdformat_gfm_alerts.mdit_plugins import gfm_alerts_plugin
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.tasklists import tasklists_plugin

from . import templates
from .mdit_plugins import (
    css_inline_plugin,
    fence_default_lang_plugin,
    image_embed_plugin,
    mdformat_plugin,
    pygments_plugin,
)


def md_format(text):
    return mdformat.text(
        text,
        options={"wrap": 80},
        extensions={"gfm", "gfm_alerts", "dollarmath", "simple_breaks"},
    ).strip()


def dollarmath_renderer(content, config=None):
    """Renders the math blocks as dollar math itself.

    This can be used with katex with delimeters set to dollars.
    """
    display_mode = config and config.get("display_mode", False)
    delimeter = "$$" if display_mode else "$"
    return f"{delimeter}{escapeHtml(content)}{delimeter}"


RENDERER_CLASSES = {"html": RendererHTML, "md": MDRenderer}


def get_base_mdit(
    target: Literal["html", "md"] = "html",
    default_code_lang=None,
    html_math_renderer=None,
):
    mdit = MarkdownIt("gfm-like", renderer_cls=RENDERER_CLASSES[target])

    if default_code_lang is None:
        default_code_lang = "text"

    match target:
        case "md":
            mdit.use(
                mdformat_plugin,
                options={"wrap": 80},
                extensions={"gfm", "gfm_alerts", "dollarmath", "simple_breaks"},
            )

        case "html":
            if html_math_renderer is None:
                html_math_renderer = dollarmath_renderer

            mdit.use(
                dollarmath_plugin, renderer=html_math_renderer, double_inline=True
            ).use(
                gfm_alerts_plugin,
                icons=json.loads(
                    files(templates).joinpath("gh_alerts.json").read_text()
                ),
            ).use(tasklists_plugin, enabled=True)

    mdit.use(fence_default_lang_plugin)

    return mdit


BASE_CSS = files(templates).joinpath("base.css").read_text()

DEFAULT_CSS = files(templates).joinpath("default.css").read_text()

MDIT_HTML_RENDERERS: dict[Literal["base", "inline"], MarkdownIt] = {
    "base": get_base_mdit("html"),
    "inline": (
        get_base_mdit("html")
        .use(pygments_plugin)
        .use(css_inline_plugin, container="div", css=BASE_CSS + DEFAULT_CSS)
    ),
}

MDIT_MD_RENDERERS: dict[Literal["base", "embedded"], MarkdownIt] = {
    "base": get_base_mdit("md"),
    "embedded": (get_base_mdit("md").use(image_embed_plugin)),
}


def get_jinja_package_env():
    return Environment(
        loader=PackageLoader("queck", "templates"), autoescape=select_autoescape()
    )


class JinjaPackageEnvBuilder:
    def __init__(self):
        self.env = get_jinja_package_env()

    def use_filter(self, name, filter):
        self.env.filters[name] = filter
        return self

    def with_global(self, name, value):
        self.env.globals[name] = value
        return self


_BASE_JINJA_ENV = JinjaPackageEnvBuilder().env

COMPONENT_VIEW_TEMPLATES: dict[str, Template] = {
    "queck": _BASE_JINJA_ENV.get_template("components/queck.md.jinja"),
    "question": _BASE_JINJA_ENV.get_template("components/question.md.jinja"),
    "common_data_question": _BASE_JINJA_ENV.get_template(
        "components/common_data_question.md.jinja"
    ),
}


_HTML_EXPORT_BASE_ENV = (
    JinjaPackageEnvBuilder()
    .use_filter("md", MDIT_HTML_RENDERERS["base"])
    .with_global("for_html_export", True)
    .env
)

_HTML_EXPORT_INILNE_ENV = (
    JinjaPackageEnvBuilder()
    .use_filter("md", MDIT_HTML_RENDERERS["inline"])
    .with_global("for_html_export", True)
    .env
)

HTML_EXPORT_TEMPLATES: dict[Literal["fast", "latex", "inline"], Template] = {
    "fast": _HTML_EXPORT_BASE_ENV.get_template("export_templates/fast.html.jinja"),
    "latex": _HTML_EXPORT_BASE_ENV.get_template("export_templates/latex.html.jinja"),
    "inline": _HTML_EXPORT_INILNE_ENV.get_template(
        "export_templates/inline.html.jinja"
    ),
}
