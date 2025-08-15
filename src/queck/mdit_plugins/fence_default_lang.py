from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore


def fence_default_lang_plugin(md: MarkdownIt, default_lang="text"):
    def update_codeblock_lang(state: StateCore, *args):
        for token in state.tokens:
            if token.type == "fence":
                info = token.info.strip()
                token.info = info or default_lang

    md.core.ruler.after("block", "fence_default_lang", update_codeblock_lang)
