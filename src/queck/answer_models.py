import abc
import re
from dataclasses import dataclass
from typing import Any, ClassVar, Literal

from pydantic import (
    BaseModel,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    TypeAdapter,
    ValidationInfo,
    model_serializer,
    model_validator,
)

from .model_utils import DecimalNumber, MDStr, T

AnswerType = Literal[
    "single_select_choices",
    "multiple_select_choices",
    "num_int",
    "num_range",
    "num_tolerance",
    "short_answer",
    "true_false",
    "none",
]


@dataclass
class Answer[T]:
    value: T
    type: AnswerType


class AnswerModel(RootModel[T]):
    """Same as RootModel but adds and alias value to root attribute of root model."""

    root: T
    type: ClassVar[str]

    @property
    def value(self) -> T:
        """Alias for root."""
        return self.root

    @value.setter
    def value(self, value: T):
        self.root = value

    @model_serializer(mode="plain")
    def ser_parsed(self, info: SerializationInfo) -> T | Answer[T]:
        context = info.context
        if context is not None and context.get("parsed", False):
            return Answer(value=self.value, type=self.type)
        else:
            return self.root


def PatternField(*args, pattern=None, **kwargs):  # noqa: N802
    return Field(default="", pattern=re.sub(r"\?P", "?", pattern), **kwargs)


class ParsedModelBase(BaseModel):
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
        nxt: SerializerFunctionWrapHandler,
        info: SerializationInfo,
    ) -> str | Any:
        context = info.context
        if context is not None and context.get("formatted", False):
            return self.formatted
        return nxt(self)


class PatternStringBase(abc.ABC, RootModel):
    """Base class for regex parseable strings with named capture groups."""

    pattern: ClassVar[str]
    parsed_type: ClassVar  # used when serialzed in parsed mode.
    parsed_extra: ClassVar[list] = []  # additional attributes passed to parsed type
    _parsed: ParsedModelBase  # used when serialzed in parsed mode.

    @property
    def parsed(self):
        return self._parsed

    @model_validator(mode="after")
    def cache_parsed(self):
        self._parsed = self.parsed_type(
            **re.match(self.pattern, self.root).groupdict(),
            **{attr: getattr(self, attr) for attr in self.parsed_extra},
        )
        self.root = self.parsed.formatted
        return self

    @model_serializer(mode="plain")
    def ser_parsed(self, info: SerializationInfo) -> str | dict:
        context = info.context
        parsed = context is not None and context.get("parsed", False)
        return self.parsed.model_dump(context={"formatted": not parsed})

    @staticmethod
    def parsed_property(name):
        return property(
            lambda self: getattr(self.parsed, name),
            lambda self, v: setattr(self.parsed, name, v),
        )


def escape_choice(text):
    return re.sub(r"/#", r"/&#35;", text)


def unescape_choice(text):
    return re.sub(r"(/&#35;|&#47;#|&#47;&#35;)", r"/#", text)


def format_choice(mark, text, feedback=None):
    text = escape_choice(text)
    result = "({mark}) {text}".format(mark=mark, text=text)
    if feedback:
        feedback = escape_choice(feedback)
        if "\n" in feedback or "\n" in text:
            result += "\n/# {}".format(feedback)
        else:
            result += " /# {}".format(feedback)
    return result


def choice_pattern(mark):
    return r"^\s*\({}\)\s*(?P<text>(.|\r?\n)*?)\s*(/# *(?P<feedback>(.|\r?\n)*))?\s*$".format(
        mark
    )


ChoiceType = Literal["single_select", "multiple_select"]


class Choice(ParsedModelBase):
    text: MDStr
    is_correct: bool
    feedback: MDStr | None = None
    type: ChoiceType | None = None

    @property
    def mark(self):
        if not self.is_correct:
            return " "
        if self.type == "multiple_select":
            return "x"
        return "o"

    @property
    def formatted(self) -> str:
        return format_choice(self.mark, self.text, self.feedback)


class ChoiceBase(PatternStringBase):
    type: ClassVar[ChoiceType | None] = None
    is_correct: ClassVar[bool]
    type: ClassVar[ChoiceType | None]
    parsed_type: ClassVar = Choice
    parsed_extra = ["is_correct", "type"]

    text = PatternStringBase.parsed_property("text")
    feedback = PatternStringBase.parsed_property("feedback")


class SingleSelectCorrectChoice(ChoiceBase):
    r"""Correct Choice in a single select question.

    The mark resembles (o) radio button.

    Format: `(o) {text} /# {feedback}`
        - `text` is the choice content
        - `feedback` is optional and explains the correctness or
        details about the choice

    Both text and feedback can span multiple lines.

    The sequence `/#` acts the feedback separater in chocies.
    To use the literal `/#`, use html code for / (&#47;) or # (&#35;) or both.

    Examples:
    ```yaml
    - (o) correct choice /# This is the correct answer
    - (o) another correct choice
    - |
        (o) This is another correct choice
        That can span muliple lines.
        /# This is going to be a multiline feedback
        and this is the second line of the feedback
    - (o) This has /&#35; separator in the text.
    ```
    """

    mark: ClassVar[str] = "o"
    is_correct: ClassVar[bool] = True
    type: ClassVar[ChoiceType | None] = "single_select"
    pattern: ClassVar[str] = choice_pattern(mark)
    root: str = PatternField(pattern=pattern)


class MultipleSelectCorrectChoice(ChoiceBase):
    r"""Correct Choice in a multiple select question.

    The mark resembles checkboxes (x).

    Format: `(x) {text} /# {feedback}`
        - `text` is the choice content
        - `feedback` is optional and explains the correctness or
        details about the choice

    Both text and feedback can span multiple lines.

    The sequence `/#` acts the feedback separater in chocies.
    To use the literal `/#`, use html code for / (&#47;) or # (&#35;) or both.

    Examples:
    ```yaml
    - (x) correct choice /# This is the correct answer
    - (x) another correct choice
    - |
        (x) This is another correct choice
        That can span muliple lines.
        /# This is going to be a multiline feedback
        and this is the second line of the feedback
    - (x) This has /&#35; separator in the text.
    ```
    """

    mark: ClassVar[str] = "x"
    is_correct: ClassVar[bool] = True
    type: ClassVar[ChoiceType | None] = "multiple_select"
    pattern: ClassVar[str] = choice_pattern(mark)
    root: str = PatternField(pattern=pattern)


class IncorrectChoice(ChoiceBase):
    r"""Incorrect Choice in a multiple choice question.

    Format: `( ) {text} /# {feedback}`
        - `text` is the choice content
        - `feedback` is optional and explains the correctness or
        details about the choice

    Both text and feedback can span multiple lines.

    The sequence `/#` acts the feedback separater in chocies.
    To use the literal `/#`, use html code for / (&#47;) or # (&#35;) or both.

    Examples:
    ```yaml
    - ( ) incorrect choice /# This is the incorrect answer
    - ( ) another incorrect choice
    - |
        ( ) This is another incorrect choice
        That can span muliple lines.
        /# This is going to be a multiline feedback
        and this is the second line of the feedback.
    - ( ) This has /&#35; separator in the text.
    ```
    """

    mark: ClassVar[str] = " "
    is_correct: ClassVar[bool] = False
    pattern: ClassVar[str] = choice_pattern(mark)
    root: str = PatternField(pattern=pattern)


correct_choice_adapter = TypeAdapter(MultipleSelectCorrectChoice)
incorrect_choice_adapter = TypeAdapter(IncorrectChoice)


class ChoicesBase(AnswerModel):
    root: list[
        MultipleSelectCorrectChoice | SingleSelectCorrectChoice | IncorrectChoice
    ]

    def __getitem__(self, item):
        return self.root[item]

    def __setitem__(self, item, value):
        self.root[item] = value

    def __iter__(self):
        return iter(self.root)

    @property
    def n_correct(self):
        return sum(
            1
            for choice in self.root
            if isinstance(
                choice, (SingleSelectCorrectChoice, MultipleSelectCorrectChoice)
            )
        )

    @property
    def n_incorrect(self):
        return len(self.root) - self.n_correct


# manually defining json schema as contians is not included in pydantic yet.
class SingleSelectChoices(
    ChoicesBase[list[SingleSelectCorrectChoice | IncorrectChoice]]
):
    """List of choices with only one choice selectable and correct."""

    type: ClassVar[AnswerType] = "single_select_choices"
    root: list[SingleSelectCorrectChoice | IncorrectChoice] = Field(
        json_schema_extra={
            "allOf": [
                {
                    "contains": {"ref": "#/$defs/SingleSelectCorrectChoice"},
                    "minContains": 1,
                    "maxContains": 1,
                    "errorMessage": "SingleCorrectChoices: Should contain "
                    "exactly one correct choice.",
                },
                {
                    "contains": {"ref": "#/$defs/IncorrectChoice"},
                    "minContains": 1,
                    "errorMessage": "SingleCorrectChoices: Should contain "
                    "atleast one incorrect choice.",
                },
            ]
        },
    )

    @model_validator(mode="after")
    def check(self, info: ValidationInfo):
        if info.context and info.context.get("ignore_n_correct"):
            return self
        assert self.n_correct == 1, (
            "Should have exactly one correct answer "
            f"but has {self.n_correct} correct answers."
        )
        assert self.n_incorrect > 0, "Should have one or more incorrect answers"
        return self


class MultipleSelectChoices(
    ChoicesBase[list[MultipleSelectCorrectChoice | IncorrectChoice]]
):
    """List of choices with one or more choices selectable and correct."""

    type: ClassVar[AnswerType] = "multiple_select_choices"
    root: list[MultipleSelectCorrectChoice | IncorrectChoice] = Field(
        json_schema_extra={
            "allOf": [
                {
                    "contains": {"ref": "#/$defs/MultipleSelectCorrectChoice"},
                    "minContains": 1,
                    "errorMessage": "MultipleSelectChoices: Should contain "
                    "atleast one correct choice.",
                },
                {
                    "contains": {"ref": "#/$defs/IncorrectChoice"},
                    "minContains": 1,
                    "errorMessage": "MultipleSelectChoices: Should contain "
                    "atleast one incorrect choice.",
                },
            ]
        },
    )

    @model_validator(mode="after")
    def check(self, info: ValidationInfo):
        if info.context and info.context.get("ignore_n_correct"):
            return self
        assert self.n_correct > 0, "Should have one or more correct answers."
        assert self.n_incorrect > 0, "Should have one or more incorrect answers."
        return self


class ShortAnswer(AnswerModel[str]):
    """Text based answer."""

    type: ClassVar[AnswerType] = "short_answer"
    root: str


class TrueOrFalse(AnswerModel[bool]):
    """True or false answer."""

    type: ClassVar[AnswerType] = "true_false"
    root: bool

    def to_single_select(self):
        return SingleSelectChoices.model_validate(
            [
                format_choice("o" if self.root else " ", "True"),
                format_choice("o" if not self.root else " ", "False"),
            ]
        )


class Integer(AnswerModel[int]):
    """Numerical integer answer."""

    type: ClassVar[AnswerType] = "num_int"
    root: int


class NumRangeParsed(ParsedModelBase, title="NumRange"):
    format: ClassVar[str] = "{low}..{high}"
    high: DecimalNumber
    low: DecimalNumber

    @model_validator(mode="after")
    def parse(self):
        self.low, self.high = sorted([self.low, self.high])
        return self


class NumRangeRoot(PatternStringBase):
    """Numerical range based answer.

    Format: `{low}..{high}`.

        - `low` and `high` are numerical values representing the
        range boundaries.

    Both `low` and `high` can be integer or floating point types.
    """

    format: ClassVar[str] = "{low}..{high}"
    pattern: ClassVar[str] = (
        r"^\s*(?P<low>-?\d*\.?\d*)\s*\.\.\s*(?P<high>-?\d*\.?\d*)\s*"
    )
    parsed_type = NumRangeParsed
    root: str = PatternField(pattern=pattern)

    low = PatternStringBase.parsed_property("low")
    high = PatternStringBase.parsed_property("high")


class NumRange(AnswerModel[NumRangeRoot]):
    type: ClassVar[str] = "num_range"
    root: NumRangeRoot

    def to_num_tolerance(self):
        low, high = self.value.low, self.value.high
        return NumRange(f"{(high + low) / 2}|{(high - low) / 2}")


class NumToleranceParsed(ParsedModelBase, title="NumTolerance"):
    value: DecimalNumber
    tolerance: DecimalNumber
    format: ClassVar[str] = "{value}|{tolerance}"


class NumToleranceRoot(PatternStringBase):
    """Numerical answer with tolerance.

    Format: `{val}|{tolerance}`

        - `val` is the base value.
        - `tolerance` specifies the allowable deviation.

    Both `val` and `tolerance` can be integer or floating point types.
    """

    format: ClassVar[str] = "{value}|{tolerance}"
    pattern: ClassVar[str] = (
        r"^\s*(?P<value>-?\d*\.?\d*)\s*\|\s*(?P<tolerance>-?\d*\.?\d*)$"
    )
    parsed_type = NumToleranceParsed
    root: str = PatternField(pattern=pattern)

    value = PatternStringBase.parsed_property("value")
    tolerance = PatternStringBase.parsed_property("tolerance")


class NumTolerance(AnswerModel[NumToleranceRoot]):
    type: ClassVar[str] = "num_tolerance"
    root: NumToleranceRoot

    def to_num_range(self):
        value, tolerance = self.root.value, self.root.tolerance
        return NumRange(f"{value - tolerance}..{value + tolerance}")
