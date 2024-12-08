import abc
import functools
import io
from functools import cached_property
from typing import Annotated, Literal

import mdformat
import yaml
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
)

from .answer_models import (
    Integer,
    MultipleChoiceAnswer,
    MultipleCorrectChoices,
    NumRange,
    NumTolerance,
    ShortAnswer,
    SingleCorrectChoice,
    TrueOrFalse,
)
from .render_utils import templates
from .utils import write_file

MDStr = Annotated[
    str, AfterValidator(lambda x: mdformat.text(x, options={"wrap": 70}).rstrip())  # noqa: F821
]


QuestionType = Literal[
    "multiple_choice",
    "multiple_select",
    "numerical_answer",
    "short_answer",
    "description",
    "common_data",
]


class QuestionBase(abc.ABC, BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: MDStr


class Description(QuestionBase):
    type: QuestionType = "description"
    text: MDStr = Field(
        title="Description",
        description="Text only content used for holding instructions "
        "or reference information.",
    )


class Question(QuestionBase):
    """Question with an answer.

    Attributes:
        - `text` : The statement or body of the question.

        - `answer` : The expected answer, which can be:
            - A list of choices (e.g., `Choice`).
            - A numerical value (integer, range, or tolerance).
            - A text response (string).
            - A boolean (True/False).

        - `feedback` : Optional feedback or explanation about the question or its solution.

        - `marks` : The marks allotted for the question (default is 0).

        - `tags` : A list of tags categorizing the question. Tags are stored in lowercase.
    """  # noqa: E501

    text: MDStr = Field(
        title="Question",
        default="Question statement",
        description="The statement or body of the question.",
    )
    answer: (
        MultipleChoiceAnswer
        | TrueOrFalse
        | Integer
        | NumRange
        | NumTolerance
        | ShortAnswer
    )
    feedback: str = Field(
        default="",
        description="Optional feedback or explanation for the question. "
        "Can include solutions, hints, or clarifications.",
    )
    marks: int | float = Field(
        default=0,
        description="The marks assigned to this question. Defaults to 0.",
    )
    tags: list[Annotated[str, StringConstraints(to_lower=True)]] | None = Field(
        default_factory=list, description="A list of tags categorizing the question."
    )

    @computed_field
    @cached_property
    def type(self) -> QuestionType:
        match self.answer:
            case SingleCorrectChoice() | TrueOrFalse():
                return "multiple_choice"
            case MultipleCorrectChoices():
                return "multiple_select"
            case ShortAnswer():
                return "short_answer"
            case Integer() | NumRange() | NumTolerance():
                return "numerical_answer"


class CommonDataQuestion(QuestionBase):
    """Represents a set of questions that share a common context or data.

    Attributes:
        - `text`: The shared context or data for the questions.
        - `questions`: A list of questions based on the common context.
    """

    type: QuestionType = "common_data"
    text: MDStr = Field(
        title="CommonData",
        description="The shared context or common data for the questions.",
    )
    questions: list[Question] = Field(
        title="ContextualQuestions",
        description="A list of questions related to the common data.",
    )

    @computed_field
    @property
    def marks(self) -> int:
        return sum(question.marks for question in self.questions)


class Queck(BaseModel):
    """Represents a YAML-based quiz format.

    Contains a title and questions.

    Attributes:
        - `title`: The title of the quiz.
        - `questions`: A list of questions, which can be standalone \
            or grouped under a common context.
    """

    title: str = Field(default="Queck Title", description="The title of the quiz.")
    questions: list[Description | Question | CommonDataQuestion] = Field(
        description="A collection of questions, "
        "which may include standalone questions or common-data questions.",
    )

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
        return yaml.safe_dump(self.model_dump())

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
