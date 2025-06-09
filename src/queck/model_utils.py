import io
from decimal import Decimal
from typing import Annotated, Any

import yaml
from markdown_it import MarkdownIt
from pydantic import (
    AfterValidator,
    BaseModel,
    Json,
    PlainSerializer,
    TypeAdapter,
    ValidationInfo,
)
from pydantic.json_schema import GenerateJsonSchema
from ruamel.yaml import YAML

from .render_utils import md_format, mdit_renderers
from .utils import Merger, write_file

ru_yaml = YAML(typ="rt", plug_ins=[])
ru_yaml.default_flow_style = False
ru_yaml.indent(mapping=2, sequence=4, offset=2)


def _str_presenter(dumper, data):
    """Preserve multiline strings when dumping yaml.

    https://github.com/yaml/pyyaml/issues/240
    """
    if "\n" in data:
        # Remove trailing spaces messing out the output.
        block = "\n".join([line.rstrip() for line in data.splitlines()])
        if data.endswith("\n"):
            block += "\n"
        return dumper.represent_scalar("tag:yaml.org,2002:str", block, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


ru_yaml.representer.add_representer(str, _str_presenter)


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


def _md_render_serializer(value, info):
    if info.context and info.context.get("rendered", False):
        renderer: MarkdownIt = info.context.get("renderer", mdit_renderers["fast"])
        env = info.context.get("render_env")
        return renderer.render(value, env)
    return value


def _md_format_validator(x, info: ValidationInfo):
    if info.context and info.context.get("format_md", False):
        return md_format(x)
    return x


MDStr = Annotated[
    str,
    AfterValidator(_md_format_validator),
    PlainSerializer(_md_render_serializer),
]

MDStrAdapter = TypeAdapter(MDStr)


def dec_to_num(d: Decimal):
    d = str(d)
    try:
        return int(d)
    except ValueError:
        return float(d)


def non_exponent_normalize(d: Decimal):
    # decimal normalize turns multiples of 10 to scientific notation.
    if d % 10 == 0:
        return Decimal(int(d))
    else:
        return d.normalize()


DecimalNumber = Annotated[
    Decimal,
    AfterValidator(non_exponent_normalize),
    PlainSerializer(dec_to_num, return_type=int | float),
]

DecimalNumberAdapter = TypeAdapter(DecimalNumber)


# TODO: Add to md and html seamlessly with this model
class YamlJsonIOModel(BaseModel):
    _yaml_content: Any | None = None  # Only used for round trip parsing.

    @classmethod
    def from_yaml(cls, yaml_str: str, format_md: bool = False, round_trip=False):
        if round_trip:
            yaml_content = ru_yaml.load(yaml_str)
        else:
            yaml_content = yaml.safe_load(yaml_str)
        result = cls.model_validate(yaml_content, context={"format_md": format_md})
        if round_trip:
            result._yaml_content = yaml_content
        return result

    @classmethod
    def read_yaml(cls, yaml_file, format_md: bool = False, round_trip=False):
        with open(yaml_file, "r") as f:
            return cls.from_yaml(f.read(), format_md=format_md, round_trip=round_trip)

    @staticmethod
    def to_file_or_str(content, file_name: str = None, extension: str = None):
        if file_name:
            write_file(file_name, content, extension=extension)
        else:
            return content

    def to_yaml(self, file_name: str = None, extension="yaml"):
        result = io.StringIO()
        if self._yaml_content is None:
            ru_yaml.dump(self.model_dump(exclude_defaults=True), result)
        else:
            Merger(extend_lists=True, extend_dicts=True).merge(
                self._yaml_content, self.model_dump(exclude_defaults=True)
            )
            ru_yaml.dump(self._yaml_content, result)
        return self.to_file_or_str(result.getvalue(), file_name=file_name, extension=extension)

    def to_json(
        self,
        file_name: str = None,
        parsed: bool = False,
        rendered: bool = False,
        extension="json",
    ):
        return self.to_file_or_str(
            self.model_dump_json(
                indent=2, context={"parsed": parsed, "rendered": rendered}
            ),
            file_name=file_name,
            extension=extension,
        )
