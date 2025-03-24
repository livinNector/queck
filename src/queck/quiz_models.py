import re
from typing import Annotated, Any, ClassVar, Literal

import mdformat
from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    TypeAdapter,
    model_serializer,
    model_validator,
)

from .answer_models import AnswerType, format_choice

MDStr = Annotated[
    str, AfterValidator(lambda x: mdformat.text(x, options={"wrap": 70}).rstrip())
]


class FormattedModel(BaseModel):
    format: ClassVar[str]

    @property
    def formatted(self) -> str:
        value = self.model_dump()
        if isinstance(value, dict):
            return self.format.format(**value)
        return value

    @model_serializer(mode="wrap")
    def ser_parsed(
        self,
        nxt: SerializerFunctionWrapHandler,
        info: SerializationInfo,
    ) -> str | Any:
        context = info.context
        if context is not None and context.get("formatted", False):
            return self.formatted
        return nxt(self)


class Choice(FormattedModel):
    text: MDStr
    is_correct: bool
    feedback: MDStr | None = ""
    choice_regex: ClassVar[str] = re.compile(
        r"\((x| )\) *(.*?) *(// *(.*))?$", re.DOTALL
    )

    @property
    def formatted(self):
        return format_choice(self.is_correct, self.text, self.feedback)

    @model_validator(mode="before")
    @classmethod
    def parse(cls, value):
        if isinstance(value, str):
            match = cls.choice_regex.match(value.strip())
            return {
                "text": match.group(2),
                "is_correct": match.group(1) == "x",
                "feedback": match.group(4),
            }
        elif isinstance(value, dict):
            return value
        else:
            raise ValueError("Choice not in correct format")


class Choices(RootModel):
    root: list[Choice]

    @property
    def n_correct(self):
        return len(list(filter(lambda x: x.is_correct, self.root)))

    @model_validator(mode="after")
    @classmethod
    def alteast_one_correct(cls, value):
        assert value.n_correct > 0, "Atleast one choice must be correct"
        assert value.n_correct < len(value.root), "All choices should not be correct"
        return value


Num = int | float
NumAdapter = TypeAdapter(Num)


class NumRange(FormattedModel):
    high: Num
    low: Num
    format: ClassVar[str] = "{low}..{high}"

    @model_validator(mode="before")
    @classmethod
    def parse(cls, value):
        if isinstance(value, str):
            low, high = sorted(map(NumAdapter.validate_python, value.split("..")))
            return {"high": high, "low": low}
        elif isinstance(value, dict):
            return value
        else:
            raise ValueError("Not a str or dict")  # improve error message


class NumTolerance(FormattedModel):
    value: Num
    tolerance: Num
    format: ClassVar[str] = "{value}|{tolerance}"

    @model_validator(mode="before")
    @classmethod
    def parse(cls, value):
        if isinstance(value, str):
            value, low = map(NumAdapter.validate_python, value.split("|"))
            return {"value": value, "tol": low}
        elif isinstance(value, dict):
            return value
        else:
            raise ValueError("Not a str or dict")


QuestionType = Literal["mcq", "msq", "nat", "sa", "desc"]


class Answer(BaseModel):
    value: Choices | bool | int | NumRange | NumTolerance | str | None = Field(
        union_mode="left_to_right", default=None
    )
    type: AnswerType

    @model_serializer(mode="wrap")
    def ser_parsed(
        self, nxt: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> str | Any:
        context = info.context
        if context is not None and context.get("formatted", False):
            return self.value
        return nxt(self)


class Question(BaseModel):
    text: MDStr
    answer: Answer
    feedback: str | None = ""
    marks: int | float | None = 0
    tags: list[str] | None = Field(default_factory=list)

    @property
    def answer_type(self) -> AnswerType:
        match self.answer.value:
            case Choices(n_correct=1):
                return "single_correct_choice"
            case Choices():
                return "multiple_correct_choices"
            case bool():
                return "true_false"
            case int():
                return "num_int"
            case NumRange():
                return "num_range"
            case NumTolerance():
                return "num_tolerance"
            case str():
                return "short_answer"

    @property
    def type(self) -> QuestionType:
        match self.answer:
            case Choices(n_correct=1) | bool():
                return "mcq"  # multiple choice question
            case Choices():
                return "msq"  # multiple select question
            case int() | NumRange() | NumTolerance():
                return "nat"  # numerical answer type
            case str():
                return "sa"  # short answer
            case None:
                return "desc"  # description


class QuestionGroup(BaseModel):
    """Base class for question containers."""

    questions: list[Question]

    @property
    def marks(self) -> int | None:
        return sum(
            question.marks for question in self.questions if hasattr(question, "marks")
        )


class CommonDataQuestion(QuestionGroup):
    # type: Literal["common_data"] = "common_data"
    text: MDStr


class Description(BaseModel):
    text: MDStr


class Quiz(QuestionGroup):
    title: str
    questions: list[Question | CommonDataQuestion | Description]
