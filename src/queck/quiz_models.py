from decimal import Decimal
from typing import Any, Literal

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

from queck.queck_models import MarkedQuestionContainer

from .answer_models import (
    AnswerType,
    Choice,
    NumRangeParsed,
    NumToleranceParsed,
)
from .model_utils import DecimalNumber, MDStr

type NumRange = NumRangeParsed
type NumTolerance = NumToleranceParsed


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
    def alteast_one_correct(self, info: ValidationInfo):
        if info.context and info.context.get("ignore_n_correct"):
            return self
        assert self.n_correct > 0, "Atleast one choice must be correct"
        assert self.n_correct < len(self.root), "All choices should not be correct"
        return self


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
    """A Question Model."""

    text: MDStr = Field(description="The statement of the question.")
    answer: Answer
    feedback: str | None = ""
    marks: DecimalNumber | None = Decimal()
    tags: list[str] | None = Field(default_factory=list)


class CommonDataQuestion(BaseModel, MarkedQuestionContainer):
    """A set of questions based on a common data."""

    type: Literal["common_data"] = "common_data"
    text: MDStr = Field(description="The common data associated with the questions.")
    questions: list[Question] = Field(description="Questions based on the common data.")


class Description(BaseModel):
    """Informational entity which is not a question."""

    text: MDStr


class Quiz(BaseModel, MarkedQuestionContainer):
    """A Set of questions with a title."""

    title: str
    questions: list[Question | CommonDataQuestion | Description]
