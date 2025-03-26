from typing import Annotated, TypeVar

from pydantic import AfterValidator, Json, TypeAdapter, WrapSerializer
from pydantic.json_schema import GenerateJsonSchema

from .render_utils import md, md_format

JsonAdapter = TypeAdapter(Json)


class RefAdderJsonSchema(GenerateJsonSchema):
    def generate(self, schema, mode="validation"):
        json_schema = super().generate(schema, mode=mode)
        return JsonAdapter.validate_strings(
            JsonAdapter.dump_json(json_schema).decode().replace('"ref', '"$ref')
        )


def remove_defaults(json_obj):
    if isinstance(json_obj, dict):
        return {
            key: remove_defaults(value) if isinstance(value, (dict, list)) else value
            for key, value in json_obj.items()
            if key != "default"
        }
    if isinstance(json_obj, list):
        return [
            remove_defaults(value) if isinstance(value, (dict, list)) else value
            for value in json_obj
        ]


class NoDefaultJsonSchema(GenerateJsonSchema):
    def generate(self, schema, mode="validation"):
        schema = super().generate(schema, mode)
        return remove_defaults(schema)


def md_render(value, handler, info):
    if info.context and info.context.get("rendered", False):
        renderer = info.context.get("renderer") or md["fast"]
        return renderer.render(value)
    return value


MDStr = Annotated[
    str,
    AfterValidator(md_format),
    WrapSerializer(md_render),
]

MDStrAdapter = TypeAdapter(MDStr)

T = TypeVar("T")


Number = int | float

NumberAdapter = TypeAdapter(Number)
