import abc
import io
import json
import re
from decimal import Decimal
from typing import (
    Annotated,
    Any,
    ClassVar,
)

import yaml
from jinja2 import Template
from markdown_it import MarkdownIt
from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    Json,
    PlainSerializer,
    PrivateAttr,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    TypeAdapter,
    ValidationError,
    ValidationInfo,
    WithJsonSchema,
    model_serializer,
    model_validator,
)
from pydantic.json_schema import GenerateJsonSchema
from ruamel.yaml import YAML

from .render_utils import md_format, mdit_renderers
from .utils import Merger, write_file

ru_yaml = YAML(typ="rt", plug_ins=[])
ru_yaml.default_flow_style = False
ru_yaml.width = 100
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


def to_file_or_str(content, file_name: str | None = None, extension: str | None = None):
    if file_name:
        write_file(file_name, content, extension=extension)
    else:
        return content


def yaml_dump(content, file_name=None, extension="yaml"):
    stream = io.StringIO()
    ru_yaml.dump(content, stream=stream)
    return to_file_or_str(stream.getvalue(), file_name=file_name, extension=extension)


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


def _md_str_serializer(value: str, info: SerializationInfo):
    if info.context:
        if info.context.get("rendered", False):
            renderer: MarkdownIt = info.context.get("renderer", mdit_renderers["base"])
            env = info.context.get("render_env")
            result = renderer.render(value, env=env)
            return result
        elif info.context.get("format_md", False):
            return md_format(value)
    return value


def _md_str_validator(x, info: ValidationInfo):
    if info.context and info.context.get("format_md", False):
        return md_format(x)
    return x


MDStr = Annotated[
    str,
    AfterValidator(_md_str_validator),
    PlainSerializer(_md_str_serializer),
]

MDStrAdapter = TypeAdapter(MDStr)


def dec_to_num(d: Decimal):
    sd = str(d)
    try:
        return int(sd)
    except ValueError:
        return float(sd)


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
    WithJsonSchema({"type": "number"}),
]

DecimalNumberAdapter = TypeAdapter(DecimalNumber)


def PatternField(*args, pattern=None, **kwargs):  # noqa: N802
    return Field(
        default="",
        pattern=pattern.replace(
            "?P",
            "?",
        ).replace("/", "\\/"),
        **kwargs,
    )


class PatternParsedModel(BaseModel):
    format: ClassVar[str]

    @property
    def formatted(self) -> str:
        value = self.model_dump()
        if isinstance(value, dict):
            return self.format.format(**value)
        return value

    @model_serializer(mode="wrap")
    def ser_formatted(
        self,
        handler: SerializerFunctionWrapHandler,
        info: SerializationInfo,
    ) -> str | dict[str, Any]:
        context = info.context
        if context is not None and context.get("formatted", False):
            return self.format.format(**handler(self))
        return handler(self)


class PatternString[T: PatternParsedModel](abc.ABC, RootModel[str]):
    """Base class for regex parseable strings with named capture groups.

    Attributes:
        pattern: The regex pattern to parse the string.
        parsed_type: The pydantic model to parse the captured groups into.
        parsed_extra: A list of attribute names from the `PatternString` instance
            that should be passed to the `parsed_type` model during validation.
            This is useful for passing context from the parent model to the parsed model.
    """

    pattern: ClassVar[str]
    parsed_type: ClassVar  # used when serialzed in parsed mode.
    _parsed: T  # used when serialzed in parsed mode.
    parsed_extra: ClassVar[list] = []  # additional attributes passed to parsed type

    @property
    def parsed(self) -> T:
        return self._parsed

    @model_validator(mode="wrap")
    @classmethod
    def cache_parsed(cls, value, handler, info: ValidationInfo):
        if info.context is not None and info.context.get("from_parsed"):
            parsed = cls.parsed_type.model_validate(
                value,
                context=info.context,
            )
            value = handler(parsed.formatted)
            value._parsed = parsed
        else:
            value = handler(value)
            match = re.match(cls.pattern, value.root)
            if match is None:
                raise ValueError(f"Does not match the pattern '{cls.pattern}'")
            value._parsed = cls.parsed_type.model_validate(
                match.groupdict()
                | {attr: getattr(value, attr) for attr in value.parsed_extra},
                context=info.context,
            )
            value.root = value.parsed.formatted
        return value

    @model_serializer(mode="plain")
    def ser_parsed(self, info: SerializationInfo) -> str | dict:
        """Serialize the parsed model.

        This serializer passes the serialization options from the parent model
        to the parsed model.
        """
        dump_kwargs = {
            "mode": info.mode,
            "include": info.include,
            "exclude": info.exclude,
            "by_alias": info.by_alias,
            "exclude_unset": info.exclude_unset,
            "exclude_defaults": info.exclude_defaults,
            "exclude_none": info.exclude_none,
            "round_trip": info.round_trip,
            "serialize_as_any": info.serialize_as_any,
        }
        context = info.context or {}
        parsed = context.get("parsed", False)
        inner_context = context.copy()
        inner_context["formatted"] = not parsed
        dump_kwargs["context"] = inner_context
        return self.parsed.model_dump(**dump_kwargs)

    @staticmethod
    def parsed_property(name):
        return property(
            lambda self: getattr(self.parsed, name),
            lambda self, v: setattr(self.parsed, name, v),
        )


class DataViewModel(BaseModel):
    _yaml_content: Any | None = PrivateAttr(None)  # Only used for round trip parsing.
    view_template: ClassVar[Template]
    mdit_renderer: ClassVar[MarkdownIt] = mdit_renderers["base"]

    @classmethod
    def use_mdit(cls, mdit: MarkdownIt):
        """Sets the shared MarkdownIt renderer."""
        cls.mdit_renderer = mdit

    @classmethod
    def reset_mdit(cls):
        """Resets the shared MarkdownIt renderer to the base renderer."""
        cls.mdit_renderer = mdit_renderers["base"]

    @classmethod
    def from_python(cls, content, format_md=False, context: dict | None = None):
        """Loads from python object."""
        context = context or {}
        return cls.model_validate(content, context={"format_md": format_md} | context)

    @classmethod
    def from_yaml(
        cls,
        yaml_str: str,
        format_md: bool = False,
        round_trip=False,
        context: dict | None = None,
    ):
        if round_trip:
            yaml_content = ru_yaml.load(yaml_str)
        else:
            yaml_content = yaml.safe_load(yaml_str)
        result = cls.from_python(yaml_content, format_md=format_md, context=context)
        if round_trip:
            result._yaml_content = yaml_content
        return result

    @classmethod
    def read_yaml(
        cls,
        yaml_file,
        format_md: bool = False,
        round_trip=False,
        context: dict | None = None,
    ):
        with open(yaml_file, "r") as f:
            return cls.from_yaml(
                f.read(), format_md=format_md, round_trip=round_trip, context=context
            )

    @classmethod
    def from_json(
        cls,
        json_str: str,
        format_md: bool = False,
        context: dict | None = None,
    ):
        return cls.from_python(
            json.loads(json_str), format_md=format_md, context=context
        )

    @classmethod
    def read_json(
        cls,
        json_file,
        format_md: bool = False,
        context: dict | None = None,
    ):
        with open(json_file) as f:
            content = json.load(f)
        return cls.from_python(content, format_md=format_md, context=context)

    to_file_or_str = staticmethod(to_file_or_str)

    def to_python(
        self,
        *,
        parsed: bool = False,
        rendered: bool = False,
        format_md: bool = False,
        renderer: MarkdownIt | None = None,
        render_env: dict | None = None,
        context: dict | None = None,
        **kwargs,
    ):
        context = context or {}
        return self.model_dump(
            context={
                "parsed": parsed,
                "rendered": rendered,
                "renderer": renderer or self.mdit_renderer,
                "format_md": format_md,
                "render_env": render_env,
            }
            | context,
            **kwargs,
        )

    def to_json(
        self,
        file_name: str | None = None,
        extension="json",
        *,
        indent: int | None = 2,
        parsed: bool = False,
        rendered: bool = False,
        format_md: bool = False,
        renderer: MarkdownIt | None = None,
        render_env: dict | None = None,
        context: dict | None = None,
        **kwargs,
    ):
        context = context or {}
        return self.to_file_or_str(
            self.model_dump_json(
                indent=indent,
                context={
                    "parsed": parsed,
                    "rendered": rendered,
                    "renderer": renderer or self.mdit_renderer,
                    "format_md": format_md,
                    "render_env": render_env,
                }
                | context,
                **kwargs,
            ),
            file_name=file_name,
            extension=extension,
        )

    def to_yaml(
        self,
        file_name: str | None = None,
        extension="yaml",
        *,
        parsed: bool = False,
        rendered: bool = False,
        format_md: bool = False,
        renderer: MarkdownIt | None = None,
        render_env: dict | None = None,
        **kwargs,
    ):
        result = self.to_python(
            parsed=parsed,
            rendered=rendered,
            format_md=format_md,
            renderer=renderer,
            render_env=render_env,
            **kwargs,
        )
        # merging is not possible during a parsed dump.
        if self._yaml_content is not None and not parsed:
            Merger(extend_lists=True, extend_dicts=True).merge(
                self._yaml_content, result
            )
            result = self._yaml_content
        return yaml_dump(result, file_name=file_name, extension=extension)

    def to_md(
        self,
        file_name: str | None = None,
        extension="md",
        *,
        format: bool = False,
        **kwargs,
    ):
        result = self.view_template.render(data=self, **kwargs)
        if format:
            result = md_format(result)
        return self.to_file_or_str(
            result,
            file_name=file_name,
            extension=extension,
        )

    def _repr_markdown_(self):
        return self.to_md()

    def to_html(
        self,
        file_name: str | None = None,
        extension="html",
        *,
        renderer: MarkdownIt | None = None,
        render_env: dict | None = None,
        **kwargs,
    ):
        renderer = renderer or self.mdit_renderer
        return self.to_file_or_str(
            renderer.render(self.to_md(format=False, **kwargs), env=render_env),
            file_name=file_name,
            extension=extension,
        )
