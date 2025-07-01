from __future__ import annotations

import abc
from collections import defaultdict
from decimal import Decimal
from typing import (
    Annotated,
    ClassVar,
    Literal,
    Protocol,
    Self,
    Sequence,
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
)

from .answer_models import (
    Answer,
    AnswerType,
    AnswerTypes,
    NumRange,
    NumTolerance,
    TrueOrFalse,
)
from .model_utils import DataViewModel, DecimalNumber, MDStr
from .queck_utils import (
    Overview,
    OverviewCommonDataStats,
    OverviewGroupStats,
    queck_config,
)
from .render_utils import html_export_templates, md_component_templates
from .utils import get_literal_union_args


@runtime_checkable
class MarkedItem(Protocol):
    marks: DecimalNumber | None


class QuestionContainer[T](abc.ABC):
    questions: Sequence[T]

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


class QueckItemTypes:
    description = Literal["description"]
    question = Literal["question"]
    common_data_question = Literal["common_data_question"]


type QueckItemType = (
    QueckItemTypes.description
    | QueckItemTypes.question
    | QueckItemTypes.common_data_question
)


class QueckItemModel(abc.ABC, DataViewModel):
    type: str
    model_config = ConfigDict(extra="forbid")
    text: MDStr

    def to_md(
        self,
        file_name=None,
        extension="md",
        *,
        format=False,
        type_labels: dict[str, str] | None = None,
        **kwargs,
    ):
        type_labels = queck_config.type_labels | (type_labels or {})
        return super().to_md(
            file_name, extension, format=format, type_labels=type_labels or {}, **kwargs
        )


class Description(QueckItemModel):
    view_template: ClassVar[Template] = md_component_templates["question"]
    type: QueckItemTypes.description = "description"
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

    type: QueckItemTypes.question = "question"
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


class QueckQuestionContainer[T](QuestionContainer[T], BaseModel):
    questions: Sequence[T]

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
        if not (num_type or bool_to_choice):
            return question_container
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
    type: QueckItemTypes.common_data_question = "common_data_question"
    text: MDStr = Field(
        title="CommonData",
        description="The shared context or common data for the questions.",
    )
    questions: Sequence[Question] = Field(
        title="ContextualQuestions",
        description="A list of questions related to the common data.",
        min_length=2,
    )


OutputFormat = Literal["queck", "html", "md", "json"]

QueckItem = Description | Question | CommonDataQuestion


class Queck(DataViewModel, QueckQuestionContainer):
    """A set of questions or Quecks with a title.

    Contains a title and questions.

    Attributes:
        title (str): The title of the queck.
        questions (list[QueckItem]|list[Queck]):
            A list of questions, which can be standalone
            or grouped under a common context.
    """

    type: Literal["queck"] = "queck"
    view_template: ClassVar[Template] = md_component_templates["queck"]
    title: str = Field(description="The title of the queck.")
    questions: Sequence[QueckItem] | Sequence[Queck] = Field(
        description="A collection of questions, "
        "which may include standalone questions or common-data questions.",
    )

    @staticmethod
    def _overview(
        q: Queck | CommonDataQuestion | QueckQuestionContainer[Question],
        type_labels: dict[str, str],
    ):
        match q:
            case Queck(questions=[Queck(), *_] as questions):
                return [
                    Overview(
                        title=queck.title,
                        total_marks=queck.marks,
                        overview=Queck._overview(queck, type_labels=type_labels),
                    )
                    for queck in questions
                    if queck.type == "queck"
                ]
            case QueckQuestionContainer(questions=questions):
                question_group_dict: dict[str, list[Question]] = defaultdict(list)
                common_data_questions: list[CommonDataQuestion] = []

                for question in questions:
                    if question.type == "question":
                        question_group_dict[type_labels[question.answer.type]].append(
                            question
                        )
                    elif question.type == "common_data_question":
                        common_data_questions.append(question)
                overview_order = []
                for type_name in get_literal_union_args(AnswerType):
                    label = type_labels[type_name]
                    if label in question_group_dict and label not in overview_order:
                        overview_order.append(label)
                overview_list = [
                    OverviewGroupStats(
                        label=label,
                        marks=QueckQuestionContainer(
                            questions=(questions := question_group_dict[label])
                        ).marks,
                        count=len(questions),
                    )
                    for label in overview_order
                ]

                if common_data_questions:
                    common_data_combined = QueckQuestionContainer(
                        questions=[
                            inner_question
                            for question in common_data_questions
                            for inner_question in question.questions
                        ]
                    )
                    common_data_label = type_labels["common_data_question"]
                    overview_list += [
                        OverviewCommonDataStats(
                            label=common_data_label,
                            marks=common_data_combined.marks,
                            count=len(common_data_questions),
                            common_data_stats=Queck._overview(
                                common_data_combined,
                                type_labels=type_labels,
                            ),
                        )
                    ]

                return overview_list

    def overview(self, type_labels: dict[str, str] | None = None):
        return self._overview(self, type_labels=type_labels or queck_config.type_labels)

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
        type_labels: dict[str, str] | None = None,
        overview: bool = False,
        **kwargs,
    ):
        type_labels = queck_config.type_labels | (type_labels or {})

        return super().to_md(
            file_name,
            extension,
            format=format,
            type_labels=type_labels,
            overview=overview and self.overview(type_labels=type_labels),
            **kwargs,
        )

    def export_html(
        self,
        file_name: str | None = None,
        render_mode: Literal["fast", "latex", "inline"] = "fast",
        type_labels: dict[str, str] | None = None,
        overview=False,
    ):
        type_labels = queck_config.type_labels | (type_labels or {})
        assert render_mode in [
            "fast",
            "latex",
            "inline",
        ], 'render_mode must be one of "fast", "latex" or "inline"'
        return self.to_file_or_str(
            html_export_templates[render_mode].render(
                data=self.normalize_answers(bool_to_choice=True, copy=True),
                overview=overview and self.overview(type_labels=type_labels),
                type_labels=type_labels,
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
            parsed (bool): Whether to add parsed choices
            render_json (bool): Whether to render markdown to html in json
            kwargs : Passed to model_dump
        """
        q = self

        q = self.normalize_answers(**queck_config.normalize_config, copy=True)
        match format:
            case "queck":
                q.to_queck(output_file)
            case "html":
                q.export_html(output_file, render_mode=render_mode, overview=overview)
            case "md":
                q.to_md(output_file, format=True, overview=overview, **kwargs)
            case "json":
                q.to_json(output_file, rendered=render_json, parsed=parsed, **kwargs)
        print(f"Quiz successfully exported to {output_file}")


QueckAnyAdapter: TypeAdapter = TypeAdapter(QueckItem | Queck)


@magics_class
class QueckMagic(Magics):
    @magic_arguments()
    @cell_magic
    def queck(self, line, cell):
        return QueckAnyAdapter.validate_python(yaml.safe_load(cell))
