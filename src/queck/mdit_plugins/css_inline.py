import css_inline
from markdown_it import MarkdownIt


def css_inline_plugin(md: MarkdownIt, container="main", css="", extra_css=None):
    if md.renderer.__output__ != "html":
        return
    render = md.render
    if extra_css is None:
        extra_css = css

    def inline_css(x, env=None):
        out = f"<{container}>{render(x)}</{container}>"
        return css_inline.inline_fragment(out, css=css, extra_css=extra_css)

    md.render = inline_css
