import abc
from decimal import Decimal
from typing import (
    Annotated,
    ClassVar,
    Iterable,
    Literal,
    Protocol,
    Self,
    runtime_checkable,
)

import yaml
from IPython.core.magic import Magics, cell_magic, magics_class
from IPython.core.magic_arguments import magic_arguments
from jinja2 import Template
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    computed_field,
)

from .answer_models import (
    Answer,
    AnswerType,
    NumRange,
    NumTolerance,
    TrueOrFalse,
)
from .model_utils import DataViewModel, DecimalNumber, MDStr
from .render_utils import html_export_templates, md_component_templates


class QueckItemModel(abc.ABC, DataViewModel):
    model_config = ConfigDict(extra="forbid")
    text: MDStr


@runtime_checkable
class MarkedItem(Protocol):
    marks: DecimalNumber | None


class QuestionContainer(abc.ABC):
    questions: list

    @property
    def marks(self):
        return sum(
            (
                question.marks or Decimal()
                for question in self.questions
                if isinstance(question, MarkedItem)
            ),
            Decimal(),
        )


class Description(QueckItemModel):
    view_template: ClassVar[Template] = md_component_templates["question"]
    type: Literal["description"] = "description"
    text: MDStr = Field(
        title="Description",
        description="Text only content used for holding instructions "
        "or reference information.",
    )


class Question(QueckItemModel):
    """Question with an answer.

    Attributes:
        - text (MDStr): The statement or body of the question.

        - answer (AnswerUnion) : The expected answer, which can be:
            - A list of choices.
            - A numerical value (integer, range, or tolerance).
            - A text response (string).
            - A boolean (True/False).

        - feedback (MDStr | None) : Optional feedback or explanation about the question or its solution.

        - marks (DecimalNumber | None) : The marks allotted for the question (default is 0).

        - tags (list[str]) : A list of tags categorizing the question. Tags are stored in lowercase.
    """  # noqa: E501

    view_template: ClassVar[Template] = md_component_templates["question"]

    text: MDStr = Field(
        title="Question",
        default="Question statement",
        description="The statement or body of the question.",
    )
    answer: Answer
    feedback: MDStr | None = Field(
        default="",
        description="Optional feedback or explanation for the question. "
        "Can include solutions, hints, or clarifications.",
    )
    marks: DecimalNumber | None = Field(
        default=Decimal(0),
        description="The marks assigned to this question. Defaults to 0.",
    )

    tags: list[Annotated[str, StringConstraints(to_lower=True)]] | None = Field(
        default_factory=list, description="A list of tags categorizing the question."
    )


class QueckQuestionContainer(QuestionContainer, BaseModel):
    questions: list

    @staticmethod
    def _answer_normalize(
        questions,
        num_type: AnswerTypes.numerical_range
        | AnswerTypes.numerical_tolerance
        | None = None,
        bool_to_choice: bool = False,
    ):
        for question in questions:
            match question:
                case Question():
                    match question.answer:
                        case NumRange():
                            if num_type == "numerical_tolerance":
                                question.answer = question.answer.to_num_tolerance()
                        case NumTolerance():
                            if num_type == "numerical_range":
                                question.answer = question.answer.to_num_range()
                        case TrueOrFalse():
                            if bool_to_choice:
                                question.answer = question.answer.to_single_select()
                case QueckQuestionContainer():
                    QueckQuestionContainer._answer_normalize(
                        question.questions,
                        num_type=num_type,
                        bool_to_choice=bool_to_choice,
                    )

    def normalize_answers(
        self,
        num_type: AnswerTypes.numerical_range
        | AnswerTypes.numerical_tolerance
        | None = None,
        bool_to_choice: bool = False,
        copy: bool = False,
    ) -> Self:
        """Normalizes the answer types.

        Args:
            num_type (Literal['numerical_range','numerical_tolerance']|None):
                Type of numeric interval to use.
                If set to `None`, num_types remains unchanged.
            bool_to_choice (bool):
                Whether to change TrueOrFalse to SingleSelectChoices
            copy (bool):
                Whether to return a new object instead of modifying the original.

        Returns:
            Self: The normalized QueckQuestionContainer object.
        """
        if copy:
            question_container = self.model_copy(deep=True)
        else:
            question_container = self
        QueckQuestionContainer._answer_normalize(
            question_container.questions,
            num_type=num_type,
            bool_to_choice=bool_to_choice,
        )
        return question_container


class CommonDataQuestion(QueckItemModel, QueckQuestionContainer):
    """Represents a set of questions that share a common context or data.

    Attributes:
        - `text`: The shared context or data for the questions.
        - `questions`: A list of questions based on the common context.
    """

    view_template: ClassVar[Template] = md_component_templates["common_data_question"]
    type: Literal["common_data_question"] = "common_data_question"
    text: MDStr = Field(
        title="CommonData",
        description="The shared context or common data for the questions.",
    )
    questions: list[Question] = Field(
        title="ContextualQuestions",
        description="A list of questions related to the common data.",
        min_length=2,
    )


OutputFormat = Literal["queck", "html", "md", "json"]

QueckItem = Description | Question | CommonDataQuestion


class Queck(DataViewModel, QueckQuestionContainer):
    """Represents a YAML-based quiz format.

    Contains a title and questions.

    Attributes:
        - title (str): The title of the quiz.
        - questions (list[Question]): A list of questions, which can be standalone \
            or grouped under a common context.
    """

    view_template: ClassVar[Template] = md_component_templates["queck"]
    title: str = Field(default="Queck Title", description="The title of the quiz.")
    questions: list[QueckItem] = Field(
        description="A collection of questions, "
        "which may include standalone questions or common-data questions.",
    )

    @staticmethod
    def _answer_normalize(
        questions,
        num_type: Literal["num_range", "num_tolerance"] | None = None,
        bool_to_choice: bool = False,
    ):
        for question in questions:
            match question:
                case Question():
                    match question.answer:
                        case NumRange():
                            if num_type == "num_tolerance":
                                question.answer = question.answer.to_num_tolerance()
                        case NumTolerance():
                            if num_type == "num_range":
                                question.answer = question.answer.to_num_range()
                        case TrueOrFalse():
                            if bool_to_choice:
                                question.answer = question.answer.to_single_select()
                case CommonDataQuestion():
                    Queck._answer_normalize(
                        question.questions,
                        num_type=num_type,
                        bool_to_choice=bool_to_choice,
                    )

    def normalize_answers(
        self,
        num_type: Literal["num_range", "num_tolerance"] | None = None,
        bool_to_choice: bool = False,
        copy=False,
    ) -> Self:
        """Normalizes the answer types.

        Args:
            num_type (Literal['num_range','num_tolerance']|None):
                Type of numeric interval to use consistently.
                If set to `None`, num_types remains unchanged.
            bool_to_choice (bool):
                Whether to change true of false to Single Select Choices.
            copy (bool):
                Whether to return a new queck instead of modifying the original.

        Returns:
            Queck: The normalized Queck object.
        """
        if copy:
            queck = self.model_copy(deep=True)
        else:
            queck = self
        Queck._answer_normalize(
            queck.questions, num_type=num_type, bool_to_choice=bool_to_choice
        )
        return queck

    @classmethod
    def from_queck(cls, queck_str: str, format_md: bool = False, round_trip=False):
        """Loads and validates the queck YAML string.

        Args:
            queck_str(str): the queck YAML string.
            format_md(bool): Format the MDStr fields using mdformat.
            round_trip (bool):
                Whether to enable round trip parsing, preserving comments.
                If enabled ruamel parser is used, else pyyaml is used.

        Returns:
            Queck: Validated Queck object if successful.

        Raises:
            ValidationError: if validation is not successfull
        """
        return cls.from_yaml(
            yaml_str=queck_str, format_md=format_md, round_trip=round_trip
        )

    @classmethod
    def read_queck(cls, queck_file, format_md: bool = False, round_trip=False):
        """Loads and validates the queck YAML file.

        Args:
            queck_file (str): Path to the queck YAML file.
            format_md(bool): Format the MDStr fields using mdformat.
            round_trip (bool):
                Whether to enable round trip parsing, preserving comments.
                If enabled ruamel parser is used, else pyyaml is used.

        Returns:
            Queck: Validated Queck object if successful.

        Raises:
            ValidationError: if validation is not successfull
        """
        return cls.read_yaml(
            yaml_file=queck_file, format_md=format_md, round_trip=round_trip
        )

    def to_queck(self, file_name: str | None = None):
        return self.to_yaml(
            file_name=file_name,
            extension="qk",
            exclude_defaults=True,
            exclude_none=True,
            exclude_unset=True,
        )

    def to_json(
        self,
        file_name=None,
        extension="json",
        *,
        parsed=False,
        rendered=False,
        format_md=False,
        renderer=None,
        render_env=None,
        **kwargs,
    ):
        if parsed:
            extension = "json"
        else:
            extension = "qk.json"

        return super().to_json(
            file_name,
            extension,
            parsed=parsed,
            rendered=rendered,
            format_md=format_md,
            renderer=renderer,
            render_env=render_env,
            **kwargs,
        )

    def to_md(
        self,
        file_name=None,
        extension="md",
        *,
        format=False,
        overview: bool = False,
        **kwargs,
    ):
        return super().to_md(
            file_name, extension, format=format, overview=overview, **kwargs
        )

    def export_html(
        self,
        file_name: str | None = None,
        render_mode: Literal["fast", "latex", "inline"] = "fast",
        overview=False,
    ):
        assert render_mode in [
            "fast",
            "latex",
            "inline",
        ], 'render_mode must be one of "fast", "latex" or "inline"'
        return self.to_file_or_str(
            html_export_templates[render_mode].render(
                data=self.normalize_answers(bool_to_choice=True, copy=True),
                overview=overview,
            ),
            file_name,
            "html",
        )

    def export(
        self,
        output_file: str | None = None,
        format: OutputFormat = "html",
        render_mode: Literal["fast", "latex", "inline"] = "fast",
        overview: bool = False,
        parsed: bool = False,
        render_json: bool = False,
        **kwargs,
    ):
        """Export queck (YAML) files into the specified .

        Args:
            output_file (str) : Output file name
            format (OutputFormat): Output format
            render_mode : Rendering mode
            overview (bool): Whether to add overview section
            render_json (bool): Whether to render markdown to html in json
            parsed (bool): Whether to add parsed choices
            kwargs : Passed to model_dump
        """
        match format:
            case "queck":
                self.to_queck(output_file)
            case "html":
                self.export_html(
                    output_file, render_mode=render_mode, overview=overview
                )
            case "md":
                self.to_md(output_file, format=True, overview=overview)
            case "json":
                self.to_json(output_file, rendered=render_json, parsed=parsed, **kwargs)
        print(f"Quiz successfully exported to {output_file}")


QueckAnyAdapter: TypeAdapter = TypeAdapter(QueckItem | Queck)


@magics_class
class QueckMagic(Magics):
    @magic_arguments()
    @cell_magic
    def queck(self, line, cell):
        return QueckAnyAdapter.validate_python(yaml.safe_load(cell))
