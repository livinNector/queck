from pydantic import (
    BaseModel,
    Field,
    RootModel,
    computed_field,
    model_validator,
    TypeAdapter,
)
from typing import ClassVar, Literal
import re


class Choice(BaseModel):
    text: str
    is_correct: bool
    feedback: str | None = ""
    choice_regex: ClassVar[str] = re.compile(
        r"\((x| )\) *(.*?) *(// *(.*))?$", re.DOTALL
    )

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


class NumRange(BaseModel):
    high: Num
    low: Num

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


class NumTolerance(BaseModel):
    value: Num
    tol: Num

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


AnswerType = Literal[
    "single_correct",
    "multiple_correct",
    "num_int",
    "num_range",
    "num_tol",
    "sa",
    "none",
]
QuestionType = Literal["mcq", "msq", "nat", "sa", "desc"]


class Question(BaseModel):
    text: str
    answer: Choices | bool | int | NumRange | NumTolerance | str | None = Field(
        union_mode="left_to_right", default=None
    )
    feedback: str | None = ""
    marks: int | None = 0

    @computed_field
    @property
    def answer_type(self) -> AnswerType:
        match self.answer:
            case Choices(n_correct=1):
                return "single_correct"
            case Choices():
                return "multiple_correct"
            case bool():
                return "true_false"
            case int():
                return "num_int"
            case NumRange():
                return "num_range"
            case NumTolerance():
                return "num_tol"
            case str():
                return "sa"
            case None:
                return "none"

    @computed_field
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


class Comprehension(BaseModel):
    text: str
    questions: list[Question]
    type: Literal["comp"] = "comp"

    @computed_field
    @property
    def marks(self) -> int | None:
        return sum(question.marks for question in self.questions)


class Quiz(BaseModel):
    title: str
    questions: list[Question | Comprehension]

    @computed_field
    @property
    def marks(self) -> int | None:
        return sum(question.marks for question in self.questions)
