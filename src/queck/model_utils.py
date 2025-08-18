import abc
import io
import os
import re
from decimal import Decimal
from pathlib import Path
from typing import (
    Annotated,
    Any,
    ClassVar,
    Literal,
    Self,
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
    ValidationInfo,
    WithJsonSchema,
    model_serializer,
    model_validator,
)
from pydantic.json_schema import GenerateJsonSchema
from ruamel.yaml import YAML

from .render_utils import MDIT_HTML_RENDERERS, MDIT_MD_RENDERERS
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


def _md_str_renderer(value: str, info: SerializationInfo | ValidationInfo):
    if (context := info.context) and (renderer := context.get("md_renderer")):
        result = renderer.render(value, env=context.get("md_render_env"))
        return result
    return value


MDStr = Annotated[
    str,
    AfterValidator(_md_str_renderer),
    PlainSerializer(_md_str_renderer),
    Field(description="Markdown text field."),
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
    """Base model to be used for parsed models.

    Child models of this class can implement `format_value` method,
    which takes in the dumped value and returns the formatted string.
    By default uses the format class variable and passes the value as kwargs.

    Child models can also include a model_validator for validating the parsed value.
    """

    format: ClassVar[str]

    def format_value(self, value):
        if isinstance(value, dict):
            return self.format.format(**value)
        return value

    @property
    def formatted(self) -> str:
        return self.format_value(self.model_dump())

    @model_serializer(mode="wrap")
    def ser_formatted(
        self,
        handler: SerializerFunctionWrapHandler,
        info: SerializationInfo,
    ) -> str | dict[str, Any]:
        context = info.context
        if context is not None and context.get("formatted", False):
            return self.format_value(
                handler(
                    self,
                )
            )
        return handler(self)


class PatternString[T: PatternParsedModel](abc.ABC, RootModel[str]):
    r"""Base class for regex parseable strings with named capture groups.

    Eg. The pattern for the key value pair separated by colon is
    r'\s*(?P<key>)\s*:\s*(?P<value>)\s*'

    The `preprocess_groups` method can be implemented to process the capture
    groups to produce the final attributes to be passed to the parsed model.

    Attributes from the parsed model can be added to PatternString using
    `PatternString.parsed_property`.

    Attributes:
        pattern: The regex pattern to parse the string.
        parsed_type: The pydantic model to parse the captured groups into.
        parsed_extra: A list of additional attribute names from the
            `PatternString` instance that should be passed to the
            `parsed_type` model during validation. This is useful for passing properties
            or class attributes from  `PatternString` model to the parsed model.
    """

    pattern: ClassVar[str]
    parsed_type: ClassVar[type[T]]  # used when serialzed in parsed mode.
    _parsed: T  # used when serialzed in parsed mode.
    parsed_extra: ClassVar[list] = []  # additional attributes passed to parsed type

    @property
    def parsed(self) -> T:
        return self._parsed

    @classmethod
    def preprocess_groups(cls, groups):
        return groups

    @model_validator(mode="wrap")
    @classmethod
    def cache_parsed(cls, value, handler, info: ValidationInfo):
        if info.context is not None and info.context.get("from_parsed"):
            parsed: PatternParsedModel = cls.parsed_type.model_validate(
                value,
                context=info.context,
            )
            value: Self = handler(parsed.formatted)
            value._parsed = parsed
        else:
            value = handler(value)
            match = re.match(cls.pattern, value.root)
            if match is None:
                raise ValueError(f"Does not match the pattern '{cls.pattern}'")
            value._parsed = cls.parsed_type.model_validate(
                cls.preprocess_groups(match.groupdict())
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
        """Helper method to add an attribute from the parsed model."""
        return property(
            lambda self: getattr(self.parsed, name),
            lambda self, v: setattr(self.parsed, name, v),
        )


class DataViewModel(BaseModel):
    """Base class for a pydantic model with markdown renderable view.

    Also has support for PatternString and MDStr type fields.
    """

    _yaml_content: Any | None = PrivateAttr(None)  # Only used for round trip parsing.
    _filename: Path | None = PrivateAttr(None)  # to be used while loaded from a file
    view_template: ClassVar[Template]  # a markdown view template for the pydantic model
    md_renderer: ClassVar[MarkdownIt] = MDIT_HTML_RENDERERS["base"]
    md_formatter: ClassVar[MarkdownIt] = MDIT_MD_RENDERERS["base"]

    @classmethod
    def use_mdit(
        cls,
        md_renderer: MarkdownIt | None = None,
        md_formatter: MarkdownIt | None = None,
    ):
        """Sets the shared MarkdownIt instances for rendering and formatting."""
        cls.md_renderer = md_renderer or cls.md_renderer
        cls.md_formatter = md_formatter or cls.md_formatter

    @classmethod
    def reset_mdit(cls):
        """Resets the shared MarkdownIt renderer to the base renderer."""
        cls.use_mdit(
            md_renderer=MDIT_HTML_RENDERERS["base"],
            md_formatter=MDIT_MD_RENDERERS["base"],
        )

    @classmethod
    def get_validation_context(
        cls,
        from_parsed: bool | None = False,
        format_md: bool | None = False,
        md_formatter: MarkdownIt | None = None,
        env: dict | None = None,
        context: dict | None = None,
    ):
        return (
            (
                {
                    "md_renderer": md_formatter or cls.md_formatter,
                    "md_render_env": env,
                }
                if format_md
                else {}
            )
            | {"from_parsed": from_parsed}
            | (context or {})
        )

    @classmethod
    def from_python(
        cls,
        obj,
        from_parsed: bool | None = False,
        format_md: bool | None = False,
        md_formatter: MarkdownIt | None = None,
        env: dict | None = None,
        context: dict | None = None,
    ):
        """Loads the model from python object.

        Arguments:
            obj : The python object.
            from_parsed (bool|None): Whether to validate from parsed model.
            format_md (bool|None): Whether to format MDstr fields during validation.
            md_formatter (MarkdownIt|None): Markdown formatter to use.
            env (dict|None): Env to be passed to the formatters `render` method.
            context (dict|None): Additional context to be passed to the model_validate.
        """
        return cls.model_validate(
            obj,
            context=cls.get_validation_context(
                from_parsed=from_parsed,
                format_md=format_md,
                md_formatter=md_formatter,
                env=env,
                context=context,
            ),
        )

    @classmethod
    def from_yaml(
        cls,
        yaml_str: str,
        round_trip=False,
        from_parsed: bool | None = False,
        format_md: bool | None = False,
        md_formatter: MarkdownIt | None = None,
        env: dict | None = None,
        context: dict | None = None,
    ):
        """Loads the model from yaml string.

        Arguments:
            yaml_str (str): The yaml string.
            round_trip (bool|None): Whether to do round trip parsing using ruamel.
            from_parsed (bool|None): Whether to validate from parsed model.
            format_md (bool|None): Whether to format MDstr fields during validation.
            md_formatter (MarkdownIt|None): Markdown formatter to use.
            env (dict|None): Env to be passed to the formatters `render` method.
            context (dict|None): Additional context to be passed to the model_validate.
        """
        if round_trip:
            yaml_content = ru_yaml.load(yaml_str)
        else:
            yaml_content = yaml.safe_load(yaml_str)
        result = cls.from_python(
            yaml_content,
            from_parsed=from_parsed,
            format_md=format_md,
            md_formatter=md_formatter,
            env=env,
            context=context,
        )
        if round_trip:
            result._yaml_content = yaml_content
        return result

    @classmethod
    def read_yaml(
        cls,
        yaml_file: os.PathLike,
        from_parsed: bool | None = False,
        format_md: bool | None = False,
        md_formatter: MarkdownIt | None = None,
        env: dict | None = None,
        round_trip=False,
        context: dict | None = None,
    ):
        """Loads the model from yaml file.

        Arguments:
            yaml_file (PathLike): The yaml file.
            round_trip (bool|None): Whether to do round trip parsing using ruamel.
            from_parsed (bool|None): Whether to validate from parsed model.
            format_md (bool|None): Whether to format MDstr fields during validation.
            md_formatter (MarkdownIt|None): Markdown formatter to use.
            env (dict|None): Env to be passed to the formatters `render` method.
            context (dict|None): Additional context to be passed to the model_validate.
        """
        with open(yaml_file, "r") as f:
            path = Path(yaml_file)
            result = cls.from_yaml(
                f.read(),
                from_parsed=from_parsed,
                format_md=format_md,
                md_formatter=md_formatter,
                env=(env or {}) | {"base_path": path.parent},
                round_trip=round_trip,
                context=(context or {}) | {"base_path": path.parent},
            )
            result._filename = path
            return result

    @classmethod
    def from_json(
        cls,
        json_str: str,
        from_parsed: bool | None = False,
        format_md: bool | None = False,
        md_formatter: MarkdownIt | None = None,
        env: dict | None = None,
        context: dict | None = None,
    ):
        """Loads the model from json string.

        Arguments:
            json_str (str): The json string.
            from_parsed (bool|None): Whether to validate from parsed model.
            format_md (bool|None): Whether to format MDstr fields during validation.
            md_formatter (MarkdownIt|None): Markdown formatter to use.
            env (dict|None): Env to be passed to the formatters `render` method.
            context (dict|None): Additional context to be passed to the model_validate.
        """
        return cls.model_validate_json(
            json_str,
            context=cls.get_validation_context(
                from_parsed=from_parsed,
                format_md=format_md,
                md_formatter=md_formatter,
                env=env,
                context=context,
            ),
        )

    @classmethod
    def read_json(
        cls,
        json_file: os.PathLike,
        from_parsed: bool | None = False,
        format_md: bool | None = False,
        md_formatter: MarkdownIt | None = None,
        env: dict | None = None,
        context: dict | None = None,
    ):
        """Loads the model from json string.

        Arguments:
            json_file (PathLike): The json file.
            from_parsed (bool|None): Whether to validate from parsed model.
            format_md (bool|None): Whether to format MDstr fields during validation.
            md_formatter (MarkdownIt|None): Markdown formatter to use.
            env (dict|None): Env to be passed to the formatters `render` method.
            context (dict|None): Additional context to be passed to the model_validate.
        """
        with open(json_file) as f:
            path = Path(json_file)
            result = cls.from_json(
                json_str=f.read(),
                from_parsed=from_parsed,
                format_md=format_md,
                md_formatter=md_formatter,
                env=(env or {}) | {"base_path": path.parent},
                context=(context or {}) | {"base_path": path.parent},
            )
            result._filename = path
            return result

    to_file_or_str = staticmethod(to_file_or_str)

    @classmethod
    def get_serialization_context(
        cls,
        parsed: bool = False,
        md_render_as: Literal["html", "md"] | None = None,
        md_renderer: MarkdownIt | None = None,
        env: dict | None = None,
        context: dict | None = None,
    ):
        match md_render_as:
            case "html":
                renderer = md_renderer or cls.md_renderer
            case "md":
                renderer = md_renderer or cls.md_formatter
            case None:
                renderer = None
        return (
            (
                {
                    "md_renderer": renderer,
                    "md_render_env": env,
                }
                if md_render_as
                else {}
            )
            | {"parsed": parsed}
            | (context or {})
        )

    def to_python(
        self,
        *,
        parsed: bool = False,
        md_render_as: Literal["html", "md"] | None = None,
        md_renderer: MarkdownIt | None = None,
        env: dict | None = None,
        context: dict | None = None,
        **kwargs,
    ):
        return self.model_dump(
            context=self.get_serialization_context(
                parsed=parsed,
                md_render_as=md_render_as,
                md_renderer=md_renderer,
                env=(env or {})
                | {"base_path": self._filename and self._filename.parent},
                context=(context or {})
                | {"base_path": self._filename and self._filename.parent},
            ),
            **kwargs,
        )

    def to_json(
        self,
        file_name: str | None = None,
        extension="json",
        *,
        indent: int | None = 2,
        parsed: bool = False,
        md_render_as: Literal["html", "md"] | None = None,
        md_renderer: MarkdownIt | None = None,
        env: dict | None = None,
        context: dict | None = None,
        **kwargs,
    ):
        return self.to_file_or_str(
            self.model_dump_json(
                indent=indent,
                context=self.get_serialization_context(
                    parsed=parsed,
                    md_render_as=md_render_as,
                    md_renderer=md_renderer,
                    env=(env or {})
                    | {"base_path": self._filename and self._filename.parent},
                    context=(context or {})
                    | {"base_path": self._filename and self._filename.parent},
                ),
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
        md_render_as: Literal["html", "md"] | None = None,
        md_renderer: MarkdownIt | None = None,
        env: dict | None = None,
        context: dict | None = None,
        **kwargs,
    ):
        result = self.to_python(
            context=self.get_serialization_context(
                parsed=parsed,
                md_render_as=md_render_as,
                md_renderer=md_renderer,
                env=(env or {})
                | {"base_path": self._filename and self._filename.parent},
                context=(context or {})
                | {"base_path": self._filename and self._filename.parent},
            ),
            **kwargs,
        )
        if self._yaml_content is not None:
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
        format: bool | None = False,
        formatter: MarkdownIt | None = None,
        env: dict | None = None,
        **kwargs,
    ):
        result = self.view_template.render(data=self, **kwargs)
        if format:
            result = (formatter or self.md_formatter).render(
                result,
                env=(env or {})
                | {"base_path": self._filename and self._filename.parent},
            )
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
        md_renderer: MarkdownIt | None = None,
        env: dict | None = None,
        **kwargs,
    ):
        renderer = md_renderer or self.md_renderer
        return self.to_file_or_str(
            renderer.render(
                self.to_md(format=False, **kwargs),
                env=(env or {})
                | {"base_path": self._filename and self._filename.parent},
            ),
            file_name=file_name,
            extension=extension,
        )
