from typing import Any, ClassVar

from pydantic import (
    BaseModel,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    ValidationInfo,
    model_serializer,
    model_validator,
)

from .answer_models import AnswerType, ChoiceType, format_choice
from .model_utils import MDStr, Number, NumberAdapter


class FormattedModel(BaseModel):
    format: ClassVar[str]

    @property
    def formatted(self) -> str:
        value = self.model_dump()
        if isinstance(value, dict):
            return self.format.format(**value)
        return value

    @model_serializer(mode="wrap")
    def ser_formatted(
        self,
        nxt: SerializerFunctionWrapHandler,
        info: SerializationInfo,
    ) -> str | Any:
        context = info.context
        if context is not None and context.get("formatted", False):
            return self.formatted
        return nxt(self)


class Choice(BaseModel):
    text: MDStr
    is_correct: bool
    feedback: MDStr | None = None
    type: ChoiceType | None = None

    @model_serializer(mode="wrap")
    def ser_formatted(
        self,
        nxt: SerializerFunctionWrapHandler,
        info: SerializationInfo,
    ) -> str | Any:
        context = info.context
        if not self.is_correct:
            mark = " "
        elif self.type == "multiple_select":
            mark = "x"
        else:
            mark = "o"
        if context is not None and context.get("formatted", False):
            return format_choice(mark, self.text, self.feedback)
        return nxt(self)


class Choices(RootModel):
    root: list[Choice]

    def __getitem__(self, item):
        return self.root[item]

    def __setitem__(self, item, value):
        self.root[item] = value

    def __iter__(self):
        return iter(self.root)

    @property
    def n_correct(self):
        return len(list(filter(lambda x: x.is_correct, self.root)))

    @model_validator(mode="after")
    @classmethod
    def alteast_one_correct(cls, value, info: ValidationInfo):
        if info.context and info.context.get("ignore_n_correct"):
            return value
        assert value.n_correct > 0, "Atleast one choice must be correct"
        assert value.n_correct < len(value.root), "All choices should not be correct"
        return value


class NumRange(FormattedModel):
    high: Number
    low: Number
    format: ClassVar[str] = "{low}..{high}"

    @model_validator(mode="before")
    @classmethod
    def parse(cls, value):
        if isinstance(value, str):
            low, high = sorted(map(NumberAdapter.validate_python, value.split("..")))
            return {"high": high, "low": low}
        elif isinstance(value, dict):
            return value
        else:
            raise ValueError("Not a str or dict")  # improve error message


class NumTolerance(FormattedModel):
    value: Number
    tolerance: Number
    format: ClassVar[str] = "{value}|{tolerance}"

    @model_validator(mode="before")
    @classmethod
    def parse(cls, value):
        if isinstance(value, str):
            value, low = map(NumberAdapter.validate_python, value.split("|"))
            return {"value": value, "tol": low}
        elif isinstance(value, dict):
            return value
        else:
            raise ValueError("Not a str or dict")


class Answer(BaseModel):
    value: Choices | bool | int | NumRange | NumTolerance | str | None = Field(
        union_mode="left_to_right", default=None
    )
    type: AnswerType

    @model_validator(mode="after")
    def choice_type_handle(self, info: ValidationInfo):
        # Change to multi select if more than one correct option is there

        if info.context:
            match value := self.value:
                case Choices():
                    if value.n_correct > 1 and info.context.get("fix_multiple_select"):
                        self.type = "multiple_select_choices"
                        for choice in iter(value):
                            if choice.is_correct:
                                choice.type = "multiple_select"

                    if value.n_correct == 1 and info.context.get("force_single_select"):
                        self.type = "single_select_choices"
                        for choice in iter(value):
                            if choice.is_correct:
                                choice.type = "single_select"

        return self

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
