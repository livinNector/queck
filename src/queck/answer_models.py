import re
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar, Literal

from pydantic import (
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    TypeAdapter,
    ValidationInfo,
    model_serializer,
    model_validator,
)

from .model_utils import (
    DecimalNumber,
    MDStr,
    PatternField,
    PatternParsedModel,
    PatternString,
)


class AnswerTypes:
    single_select_choices = Literal["single_select_choices"]
    multiple_select_choices = Literal["multiple_select_choices"]
    short_answer = Literal["short_answer"]
    numerical_integer = Literal["numerical_integer"]
    numerical_range = Literal["numerical_range"]
    numerical_tolerance = Literal["numerical_tolerance"]
    true_or_false = Literal["true_or_false"]


@dataclass
class AnswerData[T]:
    value: T
    type: str


class AnswerModel[RootT](RootModel[RootT]):
    """Wrapper for Root Model with value as alias for root and parsed serialization."""

    root: RootT
    type: ClassVar[str]

    @property
    def value(self) -> RootT:
        """Alias for root."""
        return self.root

    @value.setter
    def value(self, value: RootT):
        self.root = value

    @model_serializer(mode="plain")
    def ser_parsed(self, info: SerializationInfo) -> RootT | AnswerData[RootT]:
        context = info.context
        if context is not None and context.get("parsed", False):
            return AnswerData(value=self.value, type=self.type)
        else:
            return self.root


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
    return (
        r"^\s*\({}\)\s*(?P<text>(.|\r?\n)*?)\s*"
        r"(/#\s*(?P<feedback>(.|\r?\n)*?))?\s*$".format(mark)
    )


ChoiceType = Literal["single_select", "multiple_select"]


class Choice(PatternParsedModel):
    """Choice with markdown text and optional feedback."""

    text: MDStr
    is_correct: bool
    feedback: MDStr | None = None
    type: ChoiceType | None = None

    @model_validator(mode="after")
    def unescape(self):
        self.text = unescape_choice(self.text)
        if self.feedback is not None:
            self.feedback = unescape_choice(self.feedback)
        return self

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

    @model_serializer(mode="wrap")
    def ser_formatted(
        self,
        handler: SerializerFunctionWrapHandler,
        info: SerializationInfo,
    ) -> str | dict[str, Any]:
        context = info.context
        if context is not None and context.get("formatted", False):
            result = handler(self)
            return format_choice(self.mark, result["text"], result.get("feedback"))
        return handler(self)


class ChoiceBase(PatternString[Choice]):
    is_correct: ClassVar[bool]
    type: ClassVar[ChoiceType | None] = None
    parsed_extra = ["is_correct", "type"]
    parsed_type: ClassVar = Choice

    text = PatternString.parsed_property("text")
    feedback = PatternString.parsed_property("feedback")


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
    root: Annotated[str, PatternField(pattern=pattern)]


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
    root: Annotated[str, PatternField(pattern=pattern)]


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
    root: Annotated[str, PatternField(pattern=pattern)]


correct_choice_adapter = TypeAdapter(MultipleSelectCorrectChoice)
incorrect_choice_adapter = TypeAdapter(IncorrectChoice)


class ChoicesBase[ItemT](AnswerModel[list[ItemT]]):
    def __getitem__(self, item):
        return self.root[item]

    def __setitem__(self, item, value):
        self.root[item] = value

    def __iter__(self):
        return iter(self.root)

    def __len__(self):
        return len(self.root)

    @property
    def n_correct(self):
        return sum(1 for choice in self if choice.is_correct)

    @property
    def n_incorrect(self):
        return len(self) - self.n_correct


# manually defining json schema as contians is not included in pydantic yet.
class SingleSelectChoices(ChoicesBase):
    """List of choices with only one choice selectable and correct."""

    type: ClassVar[AnswerTypes.single_select_choices] = "single_select_choices"
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


class MultipleSelectChoices(ChoicesBase):
    """List of choices with one or more choices selectable and correct."""

    type: ClassVar[AnswerTypes.multiple_select_choices] = "multiple_select_choices"
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

    type: ClassVar[AnswerTypes.short_answer] = "short_answer"


class TrueOrFalse(AnswerModel[bool]):
    """True or false answer."""

    type: ClassVar[AnswerTypes.true_or_false] = "true_or_false"

    def __bool__(self):
        return self.root

    def to_single_select(self):
        return SingleSelectChoices.model_validate(
            [
                format_choice("o" if self.root else " ", "True"),
                format_choice("o" if not self.root else " ", "False"),
            ]
        )


class Integer(AnswerModel[int]):
    """Numerical integer answer."""

    type: ClassVar[AnswerTypes.numerical_integer] = "numerical_integer"


class NumRangeParsed(PatternParsedModel, title="NumRange"):
    format: ClassVar[str] = "{low}..{high}"
    high: DecimalNumber
    low: DecimalNumber

    @model_validator(mode="after")
    def parse(self):
        self.low, self.high = sorted([self.low, self.high])
        return self


class NumRangeStr(PatternString[NumRangeParsed]):
    """Numerical range based answer.

    Format: `{low}..{high}`.

        - `low` and `high` are numerical values representing the
        range boundaries.

    Both `low` and `high` can be integer or floating point types.
    """

    pattern: ClassVar[str] = (
        r"^\s*(?P<low>-?\d*\.?\d*)\s*\.\.\s*(?P<high>-?\d*\.?\d*)\s*"
    )
    parsed_type = NumRangeParsed
    root: Annotated[str, PatternField(pattern=pattern)]

    low = PatternString.parsed_property("low")
    high = PatternString.parsed_property("high")


class NumRange(AnswerModel[NumRangeStr]):
    type: ClassVar[AnswerTypes.numerical_range] = "numerical_range"

    def to_num_tolerance(self):
        low, high = self.value.low, self.value.high
        return NumRange(f"{(high + low) / 2}|{(high - low) / 2}")


class NumToleranceParsed(PatternParsedModel, title="NumTolerance"):
    value: DecimalNumber
    tolerance: DecimalNumber
    format: ClassVar[str] = "{value}|{tolerance}"


class NumToleranceStr(PatternString[NumToleranceParsed]):
    """Numerical answer with tolerance.

    Format: `{val}|{tolerance}`

        - `val` is the base value.
        - `tolerance` specifies the allowable deviation.

    Both `val` and `tolerance` can be integer or floating point types.
    """

    pattern: ClassVar[str] = (
        r"^\s*(?P<value>-?\d*\.?\d*)\s*\|\s*(?P<tolerance>-?\d*\.?\d*)$"
    )
    parsed_type = NumToleranceParsed
    root: Annotated[str, PatternField(pattern=pattern)]

    value = PatternString.parsed_property("value")
    tolerance = PatternString.parsed_property("tolerance")


class NumTolerance(AnswerModel[NumToleranceStr]):
    type: ClassVar[AnswerTypes.numerical_tolerance] = "numerical_tolerance"

    def to_num_range(self):
        value, tolerance = self.root.value, self.root.tolerance
        return NumRange(f"{value - tolerance}..{value + tolerance}")


type Answer = (
    SingleSelectChoices
    | MultipleSelectChoices
    | TrueOrFalse
    | Integer
    | NumRange
    | NumTolerance
    | ShortAnswer
)

type AnswerType = (
    AnswerTypes.single_select_choices
    | AnswerTypes.multiple_select_choices
    | AnswerTypes.true_or_false
    | AnswerTypes.numerical_integer
    | AnswerTypes.numerical_range
    | AnswerTypes.numerical_tolerance
    | AnswerTypes.short_answer
)
