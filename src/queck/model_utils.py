from typing import Annotated, TypeVar

import mdformat
from pydantic import AfterValidator, Json, TypeAdapter
from pydantic.json_schema import GenerateJsonSchema

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


MDStr = Annotated[
    str,
    AfterValidator(
        lambda x: mdformat.text(
            x, options={"wrap": 80}, extensions={"gfm", "gfm_alerts", "myst"}
        ).rstrip()
    ),
]

MDStrAdapter = TypeAdapter(MDStr)

T = TypeVar("T")


Number = int | float

NumberAdapter = TypeAdapter(Number)
