import mimetypes
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Literal
from urllib.parse import urlparse

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from markdown_it.token import Token


@dataclass
class ImageInfo:
    token: Token
    type: Literal["url", "path", "data"]
    filename: str | None
    extension: str
    extra: dict = field(default_factory=dict)  # for other application specific info

    @property
    def src(self):
        return self.token.attrGet("src")

    @src.setter
    def src(self, value):
        self.token.attrSet("src", value)

    @property
    def alt(self):
        return self.token.children and self.token.children[0].content


def extract_image_info(token: "Token") -> ImageInfo:
    src = token.attrGet("src")
    if not isinstance(src, str):
        src = ""
    alt = token.attrGet("alt") or token.children and token.children[0].content
    if src.startswith("data:"):
        # Handle data URI
        match = re.match(r"data:([^;]+);base64", src)
        mime_type = match.group(1).lower() if match else "application/octet-stream"
        ext = mimetypes.guess_extension(mime_type)
        if ext:
            ext = ext.lstrip(".")
        else:
            ext = mime_type.split("/")[-1].split("+")[0]  # fallback

        filename = f"{alt}.{ext}" or None
        return ImageInfo(token=token, type="data", filename=filename, extension=ext)

    parsed = urlparse(src)
    path = PurePosixPath(parsed.path)  # Handles URLs and POSIX paths

    ext = path.suffix.lstrip(".").lower()
    filename = path.name

    if parsed.scheme in ("http", "https"):
        return ImageInfo(token=token, type="url", filename=filename, extension=ext)

    # Local/relative file path
    return ImageInfo(token=token, type="path", filename=filename, extension=ext)


def image_collector_plugin(md: MarkdownIt):
    """Collects the image urls in "images" key of the env argument of MarkdownIt.

    Args:
      md (MarkdownIt): The markdown it object.
    """

    def collect_images(state: StateCore, *args):
        for image_token in (
            inline_token
            for token in state.tokens
            if token.children and token.type == "inline"
            for inline_token in token.children
            if inline_token.type == "image"
        ):
            if "images" not in state.env:
                state.env["images"] = []

            state.env["images"].append(extract_image_info(image_token))

    md.core.ruler.before("text_join", "image_collect", collect_images)
