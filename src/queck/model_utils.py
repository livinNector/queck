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
