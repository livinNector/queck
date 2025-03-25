import css_inline
from jinja2 import Environment, PackageLoader, select_autoescape
from markdown_it import MarkdownIt
from mdit_py_plugins.container import container_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name


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
            margin-bottom:.5em;
            font-size: large;
            """,
            prestyles="padding:0px; margin:0px;",
        )

        highlighted_code = highlight(content, lexer, formatter)

        return highlighted_code

    md.add_render_rule("fence", render_code_block, fmt="html")


def css_inline_plugin(md):
    render = md.render
    md.render = lambda x: css_inline.inline(render(x))


def get_base_md():
    return (
        MarkdownIt("gfm-like")
        .use(tasklists_plugin, enabled=True)
        .use(container_plugin, name="no-break")
    )


md = {}
md["fast"] = get_base_md().render
md["compat"] = get_base_md().use(pygments_plugin).use(css_inline_plugin).render


def get_template_env(**filters):
    env = Environment(
        loader=PackageLoader("queck", "templates"), autoescape=select_autoescape()
    )
    env.filters["chr"] = chr
    env.filters.update(filters)
    return env


templates = {}
templates["md"] = get_template_env().get_template("queck_template.md.jinja")
templates["queck"] = get_template_env().get_template("queck_template.yaml.jinja")
templates["fast"] = get_template_env(md=md["fast"]).get_template(
    "queck_template.html.jinja", globals={"render_mode": "fast", "format": "html"}
)
templates["compat"] = get_template_env(md=md["compat"]).get_template(
    "queck_template.html.jinja", globals={"format": "html"}
)
