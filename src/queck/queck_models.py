import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, RootModel, StringConstraints


class CorrectChoice(RootModel):
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

    root: str = Field(
        pattern=re.compile(r"\(x\) *((.|\r?\n)*?) *(// *((.|\r?\n)*))?$"),
    )


class IncorrectChoice(RootModel):
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

    root: str = Field(
        pattern=re.compile(r"\( \) *((.|\r?\n)*?) *(// *((.|\r?\n)*))?$"),
    )


Choices = Annotated[
    list[CorrectChoice | IncorrectChoice],
    Field(
        title="Choices", description="List of choices for a multiple choice question."
    ),
]

ShortAnswer = Annotated[
    str, Field(title="ShortAnswer", description="Text based answer.")
]
TrueOrFalse = Annotated[
    bool, Field(title="TrueOrFalse", description="True or false answer.")
]
Integer = Annotated[
    int, Field(title="Integer", description="Numerical integer answer.")
]


class NumRange(RootModel):
    """Numerical range based answer.

    Format: `{low}..{high}`.

        - `low` and `high` are numerical values representing the
        range boundaries.

    Both `low` and `high` can be integer or floating point types.
    """

    root: str = Field(pattern=re.compile(r"\s*\d*\.?\d*\s*\.\.\s*\d*\.?\d*"))


class NumTolerance(RootModel):
    """Numerical answer with tolerance.

    Format: `{val}|{tolerance}`

        - `val` is the base value.
        - `tolerance` specifies the allowable deviation.

    Both `val` and `tolerance` can be integer or floating point types.
    """

    root: str = Field(
        pattern=re.compile(r"\s*\d*\.?\d*\s*\|\s*\d*\.?\d*"),
    )


class TextContainerBase(BaseModel):
    text: str
    model_config = ConfigDict(extra="forbid")


class Description(TextContainerBase):
    text: str = Field(
        title="Description",
        description="Text only container that can be used for holding "
        "instructions or reference information.",
    )


class Question(TextContainerBase):
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
    answer: Choices | TrueOrFalse | Integer | NumRange | NumTolerance | ShortAnswer
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


class CommonDataQuestion(TextContainerBase):
    """Represents a set of questions that share a common context or data.

    Attributes:
        - `text`: The shared context or data for the questions.
        - `questions`: A list of questions based on the common context.
    """

    text: str = Field(
        title="Common Data",
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
    questions: list[Description | Question | CommonDataQuestion] = Field(
        description="A collection of questions, "
        "which may include standalone questions or common-data questions.",
    )
