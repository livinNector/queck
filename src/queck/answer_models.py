import abc
import re
from dataclasses import dataclass
from typing import ClassVar, Literal

from pydantic import (
    Field,
    RootModel,
    SerializationInfo,
    TypeAdapter,
    ValidationInfo,
    model_serializer,
    model_validator,
)

from .model_utils import MDStrAdapter, NumberAdapter, T

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


class PatternStringBase(abc.ABC, RootModel):
    """Base class for regex parseable strings with named capture groups."""

    pattern: ClassVar[str]
    format: ClassVar[str] = ""
    parsed_attrs: ClassVar[list[str]]  # used when serialzed in parsed mode.

    @model_validator(mode="after")
    def cache_groups(self):
        self._groups = re.match(self.pattern, self.root).groupdict()
        self.postprocess_groups()
        self.cache_groups
        return self

    @model_serializer(mode="plain")
    def ser_parsed(self, info: SerializationInfo) -> str | dict:
        context = info.context
        if context is not None and context.get("parsed", False):
            return {attr: getattr(self, attr) for attr in self.parsed_attrs}
        else:
            return self.formatted

    @property
    def formatted(self):
        assert self.format, "Class Variable format should be defined."
        return self.format.format(**self._groups)

    def postprocess_groups(self):
        assert hasattr(self, "_groups"), (
            "postprocess_groups should be called after extracting the groups"
        )
        self.root = self.formatted

    def get_group(self, name):
        return self._groups[name]

    @staticmethod
    def group_getter(name):
        def inner(self):
            return self._groups[name]

        return inner

    @staticmethod
    def group_setter(name):
        def inner(self, value):
            self._groups[name] = value

        return inner

    @staticmethod
    def group_property(name):
        return property(
            PatternStringBase.group_getter(name), PatternStringBase.group_setter(name)
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
    return r"^ *\({}\) *(?P<text>(.|\r?\n)*?) *(/# *(?P<feedback>(.|\r?\n)*))?$".format(
        mark
    )


ChoiceType = Literal["single_select", "multiple_select"]


class ChoiceBase(PatternStringBase):
    is_correct: ClassVar[bool]
    mark: ClassVar[str]
    type: ClassVar[ChoiceType | None] = None
    parsed_attrs: ClassVar[list[str]] = ["is_correct", "text", "feedback", "type"]

    def postprocess_groups(self):
        self._groups["text"] = MDStrAdapter.validate_python(
            unescape_choice(self._groups["text"].strip())
        )
        if self._groups["feedback"] is not None:
            self._groups["feedback"] = MDStrAdapter.validate_python(
                unescape_choice(self._groups["feedback"].strip())
            )
        return super().postprocess_groups()

    @property
    def formatted(self):
        return format_choice(self.mark, self.text, self.feedback)

    text = PatternStringBase.group_property("text")
    feedback = PatternStringBase.group_property("feedback")


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
    parsed_attrs: ClassVar[list[str]] = ["low", "high"]
    root: str = PatternField(pattern=pattern)

    def postprocess_groups(self):
        self._groups["low"], self._groups["high"] = sorted(
            map(NumberAdapter.validate_python, self._groups.values())
        )

    low = PatternStringBase.group_property("low")
    high = PatternStringBase.group_property("high")


class NumRange(AnswerModel[NumRangeRoot]):
    type: ClassVar[str] = "num_range"
    root: NumRangeRoot


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
    parsed_attrs: ClassVar[list[str]] = ["value", "tolerance"]
    root: str = PatternField(pattern=pattern)

    def postprocess_groups(self):
        self._groups["value"] = NumberAdapter.validate_python(self._groups["value"])
        self._groups["tolerance"] = NumberAdapter.validate_python(
            self._groups["tolerance"]
        )

    value = PatternStringBase.group_property("value")
    tolerance = PatternStringBase.group_property("tolerance")


class NumTolerance(AnswerModel[NumToleranceRoot]):
    type: ClassVar[str] = "num_tolerance"
    root: NumToleranceRoot

    def to_num_range(self):
        value, tolerance = self.root.value, self.root.tolerance
        return NumRange(f"{value - tolerance}..{value + tolerance}")
