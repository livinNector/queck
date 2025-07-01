import os
import tomllib
from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict

from pydantic import BaseModel, Field

from queck.answer_models import AnswerTypes
from queck.model_utils import DecimalNumber
from queck.utils import Merger


class NormalizeConfig(TypedDict):
    bool_to_choice: bool
    num_type: AnswerTypes.numerical_range | AnswerTypes.numerical_tolerance | None


class QueckConfig(BaseModel):
    type_labels: dict[str, str] = Field(default_factory=dict)
    normalize_config: NormalizeConfig = Field(
        default_factory=lambda: NormalizeConfig(bool_to_choice=False, num_type=None)
    )


queck_config = QueckConfig(
    type_labels={
        "common_data_question": "Common Data",
        "description": "Description",
        "single_select_choices": "Single Select",
        "multiple_select_choices": "Multiple Select",
        "numerical_integer": "Numerical",
        "numerical_range": "Numerical",
        "numerical_tolerance": "Numerical",
        "short_answer": "Short Answer",
        "true_or_false": "True/False",
    }
)
if os.path.isfile("queck.toml"):
    with open("queck.toml", "rb") as f:
        queck_config = Merger(extend_dicts=True, extend_lists=True).merge_models(
            queck_config, QueckConfig.model_validate(tomllib.load(f))
        )


@dataclass
class OverviewGroupStats:
    label: str
    marks: DecimalNumber = Decimal(0)
    count: int = 0


@dataclass(kw_only=True)
class OverviewCommonDataStats(OverviewGroupStats):
    common_data_stats: list["OverviewGroupStats"]


@dataclass
class Overview:
    title: str
    total_marks: DecimalNumber
    overview: list[OverviewGroupStats] | list["Overview"]
