import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, RootModel, StringConstraints


class Choice(RootModel):
    """Represents a choice option with a specific format and optional feedback.

    Format: `(x| ) {text} // {feedback}`

    - `(x)` denotes the option is correct.
    - `( )` denotes the option is incorrect.
    - `text` is the choice content (can span multiple lines).
    - `feedback` is optional and explains the correctness or details about the choice (can span multiple lines).

    Examples:
        - `( ) incorrect choice // This choice is incorrect`
        - `(x) correct choice // This is the correct answer`
        - `( ) another incorrect choice`
    """  # noqa: E501

    root: str = Field(
        pattern=re.compile(r"\((x| )\) *((.|\r?\n)*?) *(// *((.|\r?\n)*))?$"),
    )


class NumRange(RootModel):
    """Represents a numerical range in the format `{low}..{high}`.

    `low` and `high` are numerical values representing the range boundaries.
    """

    root: str = Field(
        pattern=re.compile(r"\s*\d*\.?\d*\s*\.\.\s*\d*\.?\d*"),
    )


class NumTolerance(RootModel):
    """Represents a numerical value with tolerance in the format `{val}|{tolerance}`.

    - `val` is the base value.
    - `tolerance` specifies the allowable deviation.
    """

    root: str = Field(
        pattern=re.compile(r"\s*\d*\.?\d*\s*\|\s*\d*\.?\d*"),
    )


class Question(BaseModel):
    """Defines a single question with various types of answers.

    Attributes:
        - `text` : The statement or body of the question.

        - `answer` : The expected answer, which can be:
            - A list of choices (e.g., `Choice`).
            - A numerical value (integer, range, or tolerance).
            - A text response (string).
            - A boolean (True/False).
            - None (if the question is descriptive or rhetorical).

        - `feedback` : Optional feedback or explanation about the question or its solution.

        - `marks` : The marks allotted for the question (default is 0).

        - `tags` : A list of tags categorizing the question. Tags are stored in lowercase.
    """  # noqa: E501

    text: str = Field(
        default="Question statement",
        description="The statement or body of the question.",
    )
    answer: list[Choice] | str | bool | int | NumRange | NumTolerance | None = Field(
        default=None,
        description=(
            "The expected answer to the question. Can be one of:\n"
            "- A list of choices (e.g., multiple-choice options).\n"
            "- A numerical value (integer, range, or tolerance).\n"
            "- A textual response (string).\n"
            "- A boolean (true/false).\n"
            "- None (if the question is descriptive)."
        ),
    )
    feedback: str | None = Field(
        default="",
        description="Optional feedback or explanation for the question. "
        "Can include solutions, hints, or clarifications.",
    )
    marks: int | float | None = Field(
        default=0, description="The marks assigned to this question. Defaults to 0."
    )
    tags: list[Annotated[str, StringConstraints(to_lower=True)]] | None = Field(
        default_factory=list, description="A list of tags categorizing the question."
    )
    model_config = ConfigDict(extra="forbid")


class CommonDataQuestion(BaseModel):
    """Represents a set of questions that share a common context or data.

    Attributes:
        - `text`: The shared context or data for the questions.
        - `questions`: A list of questions based on the common context.
    """

    text: str = Field(
        description="The shared context or common data for the questions.",
    )
    questions: list[Question] = Field(
        description="A list of questions related to the common data."
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
    questions: list[Question | CommonDataQuestion] = Field(
        description="A collection of questions, "
        "which may include standalone questions or common-data questions.",
    )
