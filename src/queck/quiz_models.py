import functools
import io
import re
from typing import Annotated, ClassVar, Literal

import mdformat
import yaml
from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    RootModel,
    TypeAdapter,
    computed_field,
    model_validator,
)

from .render_utils import templates
from .utils import write_file

MDStr = Annotated[
    str, AfterValidator(lambda x: mdformat.text(x, options={"wrap": 70}).rstrip())
]


class Choice(BaseModel):
    text: MDStr
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
    "true_false",
    "none",
]
QuestionType = Literal["mcq", "msq", "nat", "sa", "desc"]


class Question(BaseModel):
    text: MDStr
    answer: Choices | bool | int | NumRange | NumTolerance | str | None = Field(
        union_mode="left_to_right", default=None
    )
    feedback: str | None = ""
    marks: int | None = 0
    tags: list[str] | None = Field(default_factory=list)

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

    @computed_field
    @property
    def marks(self) -> int | None:
        return sum(question.marks for question in self.questions)


class Comprehension(QuestionGroup):
    type: Literal["comp"] = "comp"
    text: MDStr


class Quiz(QuestionGroup):
    title: str
    questions: list[Question | Comprehension]

    @classmethod
    def read_queck(cls, queck_file):
        """Loads and validates the queck YAML file.

        Args:
            queck_file (str): Path to the queck YAML file.

        Returns:
            Quiz: Validated Quiz object if successful.

        Raises:
            ValidationError: if validation is not successfull
        """
        with open(queck_file, "r") as f:
            return cls.model_validate(yaml.safe_load(f))

    @classmethod
    def from_queck(cls, queck_str: str):
        """Loads and validates the queck YAML string.

        Args:
            queck_str(str): the queck YAML string.

        Returns:
            Quiz: Validated Quiz object if successful.

        Raises:
            ValidationError: if validation is not successfull
        """
        return cls.model_validate(yaml.safe_load(io.StringIO(queck_str)))

    @staticmethod
    def write_file_wrapper(format):
        def wrapper(func):
            @functools.wraps(func)
            def inner(self, file_name: str = None, *args, **kwargs) -> None:
                if file_name:
                    write_file(file_name, func(self, *args, **kwargs), format)
                    return
                return func(self)

            return inner

        return wrapper

    @write_file_wrapper("yaml")
    def to_queck(self):
        return templates["queck"].render(quiz=self)

    @write_file_wrapper("json")
    def to_json(self):
        return self.model_dump_json(indent=2)

    @write_file_wrapper("md")
    def to_md(self):
        return templates["md"].render(quiz=self)

    @write_file_wrapper("html")
    def to_html(self, render_mode: Literal["fast", "compat"] = "fast"):
        assert render_mode in [
            "fast",
            "compat",
        ], 'render_mode must be one of "fast" or "compat"'
        return templates[render_mode].render(quiz=self)

    def export(
        self,
        output_file=None,
        format: Literal["queck", "html", "md", "json"] = "html",
        render_mode: Literal["fast", "compat"] = "fast",
    ):
        """Exports the quiz file to the required format."""
        match format:
            case "queck":
                self.to_queck(output_file)
            case "html":
                self.to_html(output_file, render_mode=render_mode)
            case "md":
                self.to_md(output_file)
            case "json":
                self.to_json(output_file)
        print(f"Quiz successfully exported to {output_file}")
