import css_inline
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer

PYGMENTS_LINENOS_STYLES = """
.highlighttable,
.highlighttable tbody,
.highlighttable thead,
.highlighttable tr,
.highlighttable th,
.highlighttable td,
{
    all: revert;
}

.linenodiv pre {
    line-height: 125%;
    border: none;
    border-radius: 0;
    border-right: #bbb thin solid;
    margin: 0;
    margin-right: .5em;
    margin-top: 0;
    margin-bottom: 0;
}
"""


def pygments_plugin(
    md: MarkdownIt,
    style: str | None = "default",
    font_size: str | int | None = None,
    cssstyles: str | None = None,
    prestyles: str | None = None,
    linenos: bool = False,
    noclasses: bool = True,
    **kwargs,
):
    if prestyles is None:
        prestyles = "border:none; margin:0; padding:0;font-family: monospace;"
    if cssstyles is None:
        cssstyles = (
            "border-radius:5px;border: thin solid #ddd;margin: 1em 0;padding: 1em;"
        )
    if font_size is not None:
        cssstyles += f"font-size:{font_size};"
    formatter = HtmlFormatter(
        cssstyles=cssstyles,
        prestyles=prestyles,
        style=style,
        linenos=linenos and "table",
        noclasses=noclasses,
        **kwargs,
    )

    def render_code_block(self, tokens, idx, options, env):
        token = tokens[idx]
        content = token.content.strip()
        language = token.info.strip() if token.info else "text"
        try:
            lexer = get_lexer_by_name(language)
        except ValueError:
            lexer = guess_lexer(content)

        highlighted_code = highlight(content, lexer, formatter)

        inlined_code = css_inline.inline_fragment(
            highlighted_code, css=PYGMENTS_LINENOS_STYLES
        )

        return inlined_code

    md.add_render_rule("fence", render_code_block)
