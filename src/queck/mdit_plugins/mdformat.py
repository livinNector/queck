import mdformat
import mdformat.plugins
from markdown_it import MarkdownIt
from mdformat.plugins import ParserExtensionInterface


def mdformat_plugin(
    mdit: MarkdownIt,
    options: dict | None = None,
    extensions: list[str | ParserExtensionInterface] | None = None,
    codeformatters: list | None = None,
):
    """MarkdownIt plugin to configure mdformat when MDRenderer renderer_cls is used.

    This plugin can be used multiple times to update the options or
    to add more mdformat extensions.

    Ad-hoc plugins that are created using mdformat.plugins.ParserExtensionInterface
    can be also added.

    Refer `mdformat.text` for more details about the arguments.

    Args:
        mdit (MarkdownIt): markdownit instance.
        options (dict|None): mdformat options
        extensions (list|None): mdformat extensions
        codeformatters (list|None): mdformat codeformatters
    """
    mdit.options["store_labels"] = mdit.options.get(
        "store_labels", True
    )  # used in build_mdit in mdformat

    mdit.options["mdformat"] = mdit.options.get("mdformat", {})
    mdit.options["mdformat"] |= options

    mdit.options["parser_extension"] = mdit.options.get("parser_extension", [])
    for extension in extensions or []:
        if isinstance(extension, str):
            plugin: ParserExtensionInterface = mdformat.plugins.PARSER_EXTENSIONS[
                extension
            ]
        else:
            plugin = extension
        if plugin not in mdit.options["parser_extension"]:
            mdit.options["parser_extension"].append(plugin)
            plugin.update_mdit(mdit)

    mdit.options["codeformatters"] = mdit.options.get("codeformatters", {})
    mdit.options["codeformatters"] |= {
        lang: mdformat.plugins.CODEFORMATTERS[lang] for lang in codeformatters or []
    }
