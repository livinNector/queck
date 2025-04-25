import abc
import io
from functools import cached_property
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)
from ruamel.yaml import YAML

from .answer_models import (
    Integer,
    MultipleSelectChoices,
    NumRange,
    NumTolerance,
    ShortAnswer,
    SingleSelectChoices,
    TrueOrFalse,
)
from .model_utils import MDStr
from .render_utils import templates
from .utils import Merger, write_file

yaml = YAML(typ="rt", plug_ins=[])
yaml.default_flow_style = False
yaml.indent(mapping=2, sequence=4, offset=2)


def _str_presenter(dumper, data):
    """Preserve multiline strings when dumping yaml.

    https://github.com/yaml/pyyaml/issues/240
    """
    if "\n" in data:
        # Remove trailing spaces messing out the output.
        block = "\n".join([line.rstrip() for line in data.splitlines()])
        if data.endswith("\n"):
            block += "\n"
        return dumper.represent_scalar("tag:yaml.org,2002:str", block, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.representer.add_representer(str, _str_presenter)


def load_yaml(content):
    return yaml.load(content)


QuestionType = Literal[
    "single_select",
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
        SingleSelectChoices
        | MultipleSelectChoices
        | TrueOrFalse
        | Integer
        | NumRange
        | NumTolerance
        | ShortAnswer
    )
    feedback: MDStr | None = Field(
        default="",
        description="Optional feedback or explanation for the question. "
        "Can include solutions, hints, or clarifications.",
    )
    marks: int | float | None = Field(
        default=0,
        description="The marks assigned to this question. Defaults to 0.",
    )
    tags: list[Annotated[str, StringConstraints(to_lower=True)]] | None = Field(
        default_factory=list, description="A list of tags categorizing the question."
    )

    @cached_property
    def type(self) -> QuestionType:
        match self.answer:
            case SingleSelectChoices() | TrueOrFalse():
                return "single_select"
            case MultipleSelectChoices():
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
        min_length=2,
    )

    @property
    def marks(self) -> int:
        m = sum(
            question.marks for question in self.questions if hasattr(question, "marks")
        )
        if int(m) == m:
            return int(m)
        return m


QueckItem = Description | Question | CommonDataQuestion


class Queck(BaseModel):
    """Represents a YAML-based quiz format.

    Contains a title and questions.

    Attributes:
        - `title`: The title of the quiz.
        - `questions`: A list of questions, which can be standalone \
            or grouped under a common context.
    """

    title: str = Field(default="Queck Title", description="The title of the quiz.")
    questions: list[QueckItem] = Field(
        description="A collection of questions, "
        "which may include standalone questions or common-data questions.",
    )
    _yaml_content: Any | None = None

    @property
    def marks(self) -> int:
        m = sum(
            question.marks for question in self.questions if hasattr(question, "marks")
        )
        if int(m) == m:
            return int(m)
        return m

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
        yaml_content = load_yaml(queck_str)
        result = cls.model_validate(yaml_content)
        result._yaml_content = yaml_content
        return result

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
            return cls.from_queck(f.read())

    def to_queck(self, file_name: str = None):
        result = io.StringIO()
        if self._yaml_content is None:
            yaml.dump(self.model_dump(exclude_defaults=True), result)
        else:
            Merger(extend_lists=True, extend_dicts=False).merge(
                self._yaml_content, self.model_dump(exclude_defaults=True)
            )
            yaml.dump(self._yaml_content, result)
        result = result.getvalue()
        if file_name:
            write_file(file_name, result, format="queck")
        else:
            return result

    def to_json(
        self,
        file_name: str = None,
        parsed: bool = False,
    ):
        result = self.model_dump_json(indent=2, context={"parsed": parsed})
        if file_name:
            write_file(file_name, result, format="json")
        else:
            return result

    def to_md(self, file_name: str = None):
        result = templates["md"].render(quiz=self)
        if file_name:
            write_file(file_name, result, format="md")
        else:
            return result

    def to_html(
        self,
        file_name: str = None,
        render_mode: Literal["fast", "latex", "compat"] = "fast",
    ):
        assert render_mode in [
            "fast",
            "latex",
            "compat",
        ], 'render_mode must be one of "fast", "latex" or "compat"'
        result = templates[render_mode].render(quiz=self)
        if file_name:
            write_file(file_name, result, format="html")
        else:
            return result

    def export(
        self,
        output_file=None,
        format: Literal["queck", "html", "md", "json"] = "html",
        render_mode: Literal["fast", "latex", "compat"] = "fast",
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
