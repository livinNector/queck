import abc
from functools import cached_property
from typing import Annotated, Literal

from pydantic import (
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
    text: str


class Description(QuestionBase):
    type: QuestionType = "description"
    text: str = Field(
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

    text: str = Field(
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
    feedback: str | None = Field(
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
    text: str = Field(
        title="CommonData",
        description="The shared context or common data for the questions.",
    )
    questions: list[Question] = Field(
        title="ContextualQuestions",
        description="A list of questions related to the common data.",
    )


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
