import json
from importlib.resources import files

import mdformat
from jinja2 import Environment, PackageLoader, Template, select_autoescape
from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
from mdformat_gfm_alerts.mdit_plugins import gfm_alerts_plugin
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.tasklists import tasklists_plugin

from . import templates
from .mdit_plugins import css_inline_plugin, fence_default_lang_plugin, pygments_plugin


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


def get_base_mdit(math_renderer=None, default_code_lang=None):
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
mdit_renderers: dict[str, MarkdownIt] = {}
mdit_renderers["base"] = get_base_mdit()
mdit_renderers["inline"] = (
    get_base_mdit()
    .use(pygments_plugin)
    .use(css_inline_plugin, container="div", css=default_css)
)


def get_package_env():
    return Environment(
        loader=PackageLoader("queck", "templates"), autoescape=select_autoescape()
    )


def get_mdit_render_env(
    mdit: MarkdownIt | None = None,
    globals: dict | None = None,
    filters: dict | None = None,
):
    if mdit is None:
        mdit = mdit_renderers["base"]
    env = get_package_env()
    env.filters["mdformat"] = md_format
    env.filters["md"] = mdit.render
    if filters is not None:
        env.filters.update(filters)
    if globals is not None:
        env.globals.update(globals)
    return env


md_component_templates: dict[str, Template] = {}
md_base_env = get_mdit_render_env(mdit=mdit_renderers["base"])
md_component_templates["queck"] = md_base_env.get_template("components/queck.md.jinja")
md_component_templates["question"] = md_base_env.get_template(
    "components/question.md.jinja"
)
md_component_templates["common_data_question"] = md_base_env.get_template(
    "components/common_data_question.md.jinja"
)

html_export_base_env = get_mdit_render_env(
    mdit=mdit_renderers["base"], globals={"for_html_export": True}
)
html_export_inline_env = get_mdit_render_env(
    mdit=mdit_renderers["inline"], globals={"for_html_export": True}
)

html_export_templates: dict[str, Template] = {}
html_export_templates["fast"] = html_export_base_env.get_template(
    "export_templates/fast.html.jinja"
)

html_export_templates["latex"] = html_export_base_env.get_template(
    "export_templates/latex.html.jinja"
)
html_export_templates["inline"] = html_export_inline_env.get_template(
    "export_templates/inline.html.jinja"
)
