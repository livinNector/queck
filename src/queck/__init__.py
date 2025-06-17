from .answer_models import (
    Answer,
    AnswerModel,
    AnswerType,
    Integer,
    MultipleSelectChoices,
    NumRange,
    NumTolerance,
    ShortAnswer,
    SingleSelectChoices,
    TrueOrFalse,
)
from .genai_utils import extract_queck, prompt_queck
from .model_utils import (
    DataViewModel,
    DecimalNumber,
    MDStr,
    PatternParsedModel,
    PatternString,
)
from .queck_models import CommonDataQuestion, Description, Queck, QueckMagic, Question
from .quiz_models import Quiz
from .render_utils import get_base_mdit, mdit_renderers

from_queck = Queck.from_queck
read_queck = Queck.read_queck
use_mdit = DataViewModel.use_mdit
reset_mdit = DataViewModel.reset_mdit


def load_ipython_extension(ipython):
    ipython.register_magics(QueckMagic)


__all__ = [
    "Queck",
    "Question",
    "CommonDataQuestion",
    "Description",
    "Quiz",
    "SingleSelectChoices",
    "MultipleSelectChoices",
    "Integer",
    "NumRange",
    "NumTolerance",
    "ShortAnswer",
    "TrueOrFalse",
    "Answer",
    "AnswerType",
    "AnswerModel",
    "PatternString",
    "PatternParsedModel",
    "MDStr",
    "DecimalNumber",
    "from_queck",
    "read_queck",
    "use_mdit",
    "reset_mdit",
    "get_base_mdit",
    "mdit_renderers",
    "extract_queck",
    "prompt_queck",
]
