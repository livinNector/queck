import abc
import re
from typing import Annotated, ClassVar, Literal

from pydantic import (
    Field,
    RootModel,
    TypeAdapter,
    model_validator,
)

AnswerType = Literal[
    "single_correct_choice",
    "multiple_correct_choices",
    "num_int",
    "num_range",
    "num_tolerance",
    "short_answer",
    "true_false",
    "none",
]


def PatternField(*args, pattern=None, **kwargs):  # noqa: N802
    # return Field(default="", pattern=re.sub(r"\?P<.*?>", "", pattern), **kwargs)
    return Field(default="", pattern=re.sub(r"\?P", "?", pattern), **kwargs)


class PatternStringBase(abc.ABC, RootModel):
    """Base class for regex parseable strings with named capture groups."""

    pattern: ClassVar[str]

    @model_validator(mode="after")
    def cache_groups(self):
        self._groups = re.match(self.pattern, self.root).groupdict()
        if hasattr(self, "reformat"):
            self.root = self.reformat(**self._groups)
            return self
        return self

    def get_group(self, name):
        return self._groups[name]


class ChoiceBase(PatternStringBase):
    @property
    def text(self):
        return self.get_group("text")

    @property
    def feedback(self):
        return self.get_group("feedback")


class CorrectChoice(ChoiceBase):
    """Correct Choice in a multiple choice question.

    Format: `(x) {text} // {feedback}`
        - `text` is the choice content
        - `feedback` is optional and explains the correctness or
        details about the choice

    Both text and feedback can span multiple lines.

    Examples:
        - (x) correct choice // This is the correct answer
        - (x) another correct choice
        - |
          (x) This is another correct choice
          That can span muliple lines.
          // This is going to be a multiline feedback
          and this is the second line of the feedback
    """

    is_correct: ClassVar[bool] = True
    pattern: ClassVar[str] = (
        r"\(x\) *(?P<text>(.|\r?\n)*?) *(// *(?P<feedback>(.|\r?\n)*))?$"
    )
    root: str = PatternField(pattern=pattern)


class IncorrectChoice(ChoiceBase):
    """Incorrect Choice in a multiple choice question.

    Format: `( ) {text} // {feedback}`
        - `text` is the choice content
        - `feedback` is optional and explains the correctness or
        details about the choice

    Both text and feedback can span multiple lines.

    Examples:
        - ( ) incorrect choice // This is the incorrect answer
        - ( ) another incorrect choice
        - |
          ( ) This is another incorrect choice
          That can span muliple lines.
          // This is going to be a multiline feedback
          and this is the second line of the feedback.
    """

    is_correct: ClassVar[bool] = False
    pattern: ClassVar[str] = (
        r"\( \) *(?P<text>(.|\r?\n)*?) *(// *(?P<feedback>(.|\r?\n)*))?$"
    )
    root: str = PatternField(pattern=pattern)


correct_choice_adapter = TypeAdapter(CorrectChoice)
incorrect_choice_adapter = TypeAdapter(IncorrectChoice)


class ChoicesBase(RootModel):
    def __getitem__(self, item):
        return self.root[item]

    @property
    def n_correct(self):
        return sum(1 for choice in self.root if isinstance(choice, CorrectChoice))

    @property
    def n_incorrect(self):
        return len(self.root) - self.n_correct


# manually defining json schema as contians is not included in pydantic yet.
class SingleCorrectChoice(ChoicesBase):
    """List of choices with one correct choice."""

    type: ClassVar[AnswerType] = "single_correct_choice"
    root: list[CorrectChoice | IncorrectChoice] = Field(
        json_schema_extra={
            "allOf": [
                {
                    "contains": {"ref": "#/$defs/CorrectChoice"},
                    "minContains": 1,
                    "maxContains": 1,
                    "errorMessage": "SingleCorrectChoice: Should contain "
                    "exactly one correct choice.",
                },
            ]
        },
    )

    @model_validator(mode="after")
    def check(self):
        assert self.n_correct == 1 and self.n_incorrect > 0
        return self


class MultipleCorrectChoices(ChoicesBase):
    """List of choices with multiple correct choices."""

    type: ClassVar[AnswerType] = "multiple_correct_choices"
    root: list[CorrectChoice | IncorrectChoice] = Field(
        json_schema_extra={
            "allOf": [
                {
                    "contains": {"ref": "#/$defs/CorrectChoice"},
                    "minContains": 2,
                    "errorMessage": "MultipleCorrectChoice: Should contain "
                    "atleast two correct choices.",
                },
            ]
        },
    )

    @model_validator(mode="after")
    def check(self):
        assert self.n_correct > 1 and self.n_incorrect > 0
        return self


MultipleChoiceAnswer = Annotated[
    SingleCorrectChoice | MultipleCorrectChoices,
    Field(
        title="MultipleChoiceAnswer",
        json_schema_extra={
            "allOf": [
                {
                    "contains": {"ref": "#/$defs/IncorrectChoice"},
                    "minContains": 1,
                    "errorMessage": "Should contain atleast one incorrect choice.",
                },
                {
                    "contains": {"ref": "#/$defs/CorrectChoice"},
                    "minContains": 1,
                    "errorMessage": "Should contain atleast one correct choice.",
                },
            ]
        },
    ),
]


class ShortAnswer(RootModel):
    """Text based answer."""

    type: ClassVar[AnswerType] = "short_answer"
    root: str


class TrueOrFalse(RootModel):
    """True or false answer."""

    type: ClassVar[AnswerType] = "true_false"
    root: bool


class Integer(RootModel):
    """Numerical integer answer."""

    type: ClassVar[AnswerType] = "num_int"
    root: int


class NumRange(PatternStringBase):
    """Numerical range based answer.

    Format: `{low}..{high}`.

        - `low` and `high` are numerical values representing the
        range boundaries.

    Both `low` and `high` can be integer or floating point types.
    """

    type: ClassVar[str] = "num_range"
    format: ClassVar[str] = "{low}..{high}"
    pattern: ClassVar[str] = (
        r"^\s*(?P<low>-?\d*\.?\d*)\s*\.\.\s*(?P<high>-?\d*\.?\d*)\s*"
    )
    root: str = PatternField(pattern=pattern)

    @property
    def low(self):
        return self.get_group("low")

    @property
    def high(self):
        return self.get_group("high")


class NumTolerance(PatternStringBase):
    """Numerical answer with tolerance.

    Format: `{val}|{tolerance}`

        - `val` is the base value.
        - `tolerance` specifies the allowable deviation.

    Both `val` and `tolerance` can be integer or floating point types.
    """

    type: ClassVar[str] = "num_tolerance"
    pattern: ClassVar[str] = (
        r"^\s*(?P<value>-?\d*\.?\d*)\s*\|\s*(?P<tolerance>-?\d*\.?\d*)$"
    )
    root: str = PatternField(pattern=pattern)

    @property
    def value(self):
        return self.get_group("value")

    @property
    def tolerance(self):
        return self.get_group("tolerance")
