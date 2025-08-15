import base64
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore

from .image_collector import ImageInfo, image_collector_plugin


def img_src_to_base64(src: str, base_path: str):
    if not src or bool(urlparse(src).netloc):
        return src
    img_path = Path(base_path) / src
    mime_type = mimetypes.guess_type(img_path)[0]
    try:
        file_content = img_path.read_bytes()
        base64_data = base64.b64encode(file_content).decode("utf-8")
        data_url = f"data:{mime_type};base64,{base64_data}"
        return data_url
    except Exception as e:
        print(f"Failed to convert {src}: {e}")
        return src


def image_embed_plugin(md: MarkdownIt):
    def embed_images(state: StateCore, *args):
        images: list[ImageInfo] = state.env.get("images")
        for image in images:
            if image.type == "path":
                image.src = img_src_to_base64(
                    image.src,
                    state.env.get("base_path")
                    or md.options.get("base_path")
                    or Path.cwd(),
                )
                image.type = "data"

    if "image_collect" not in md.core.ruler.get_active_rules():
        md.use(image_collector_plugin)

    md.core.ruler.after("image_collect", "image_embed", embed_images)
    return md
