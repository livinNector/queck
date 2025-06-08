import css_inline
from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer


def pygments_plugin(
    md,
    cssstyles: str | None = None,
    prestyles: str | None = None,
    linenos: True = False,
    noclasses: bool = True,
    **kwargs,
):
    if prestyles is None:
        prestyles = "border:none;"
    if cssstyles is None:
        cssstyles = """
        padding:10px;
        border-radius:5px;
        border: thin solid #ddd;
        margin:.5rem 0;
        font-size:85%;
        """
    formatter = HtmlFormatter(
        cssstyles=cssstyles,
        prestyles=prestyles,
        linenos=linenos,
        noclasses=noclasses,
        **kwargs,
    )

    def render_code_block(self, tokens, idx, options, env):
        token = tokens[idx]
        content = token.content
        language = token.info.strip() if token.info else "text"
        try:
            lexer = get_lexer_by_name(language)
        except ValueError:
            lexer = guess_lexer(content)

        highlighted_code = highlight(content, lexer, formatter)

        return highlighted_code

    md.add_render_rule("fence", render_code_block, fmt="html")


def css_inline_plugin(md, css="", extra_css=None):
    render = md.render
    if extra_css is None:
        extra_css = css

    def inline_css(x):
        out = f"<main>{render(x)}</main>"
        return css_inline.inline_fragment(out, css=css, extra_css=extra_css)

    md.render = inline_css


def fence_default_lang_plugin(md: MarkdownIt, default_lang="text"):
    def update_codeblock_lang(state: StateCore, *args):
        for token in state.tokens:
            if token.type == "fence":
                info = token.info.strip()
                token.info = info or default_lang

    md.core.ruler.after("block", "fence_default_lang", update_codeblock_lang)

# TODO: Generalize this to collect image tokens, then do any operations on it.
def image_collector_plugin(
    md: MarkdownIt, rename_images: bool = False, prefix: str = ""
):
    """Counts and collects the image urls in env argument of MarkdownIt.

    Optionally renames the images and provides a mapping of old names to new names.
    If rename images is false returns a list of images.

    Args:
      md (MarkdownIt): The markdown it object.
      rename_images (bool): Whether to rename images
      prefix (str): Prefix to use while renaming.

    Example:
    >>> md = MarkdownIt().use(image_collector_plugin, rename_images=True, prefix="img")
    >>> env = {}
    >>> result = md.render("test 1 ![](apple.jpg) test 2 ![](ball.png)", env=env)
    >>> env
    {
      "n_image":2,
      "image_urls": {
          "apple.jpg":"img1.jpg",
          "ball.png":"img2.png"
      }
    }
    """

    def collect_images(state: StateCore, *args):
        for image_token in (
            inline_token
            for token in state.tokens
            if token.type == "inline"
            for inline_token in token.children
            if inline_token.type == "image"
        ):
            if "image_urls" not in state.env:
                state.env["n_images"] = 0
                if rename_images:
                    state.env["image_urls"] = {}
                else:
                    state.env["image_urls"] = []

            state.env["n_images"] += 1
            image_url = image_token.attrs["src"]
            ext = image_url.split(".")[-1]
            image_name = f"{prefix}{state.env['n_images']}.{ext}"
            if rename_images:
                state.env["image_urls"][image_url] = image_token.attrs["src"] = (
                    image_name
                )
            else:
                state.env["image_urls"].append(image_url)

    md.core.ruler.after("inline", "image_collect", collect_images)
