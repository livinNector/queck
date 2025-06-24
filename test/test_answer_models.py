from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel, ValidationError

import queck as qk

FIXTURE_ROOT = Path(__file__).parent
answer_fixtures = yaml.safe_load((FIXTURE_ROOT / "answer_fixtures.yaml").read_text())
answer_conversion_fixtures = yaml.safe_load(
    (FIXTURE_ROOT / "answer_conversion_fixtures.yaml").read_text()
)

answer_attr_check_fixtures = yaml.safe_load(
    (FIXTURE_ROOT / "answer_attr_check_fixtures.yaml").read_text()
)


@pytest.mark.parametrize(
    "test_item", answer_fixtures, ids=[f["title"] for f in answer_fixtures]
)
def test_answers(test_item):
    model: BaseModel = getattr(qk.answer_models, test_item["model"])
    answer_constructed = model(root=test_item["item"])
    answer_validated = model.model_validate(test_item["item"])

    assert answer_constructed == answer_validated
    parsed_dict = answer_constructed.model_dump(context={"parsed": True})
    assert test_item["parsed"] == parsed_dict
    formatted = test_item.get("formatted")
    if formatted:
        assert formatted == answer_constructed.model_dump()
        assert formatted == answer_constructed.model_dump(context={"formatted": True})
        assert formatted == answer_constructed.model_dump(context={"parsed": False})


@pytest.mark.parametrize(
    "test_item",
    answer_conversion_fixtures,
    ids=[f["title"] for f in answer_conversion_fixtures],
)
def test_conversion(test_item):
    source_model: BaseModel = getattr(qk.answer_models, test_item["source"]["model"])
    target_model: BaseModel = getattr(qk.answer_models, test_item["target"]["model"])

    source = source_model.model_validate(test_item["source"]["item"])
    target = target_model.model_validate(test_item["target"]["item"])

    assert target == getattr(source, test_item["method"])()


@pytest.mark.parametrize(
    "test_item",
    answer_attr_check_fixtures,
    ids=[f["title"] for f in answer_attr_check_fixtures],
)
def test_attrs(test_item):
    model: BaseModel = getattr(qk.answer_models, test_item["model"])

    item = model.model_validate(test_item["item"])

    for attr in test_item["attrs"]:
        assert getattr(item, attr["name"]) == attr["value"]


def test_dunder_methods():
    # True or False bool check
    tf_true, tf_false = qk.TrueOrFalse(True), qk.TrueOrFalse(False)
    assert (bool(tf_true), bool(tf_false)) == (True, False)

    # T/F Update Check
    tf_true.value = False
    assert tf_true == tf_false

    # choices update check
    choices = qk.SingleSelectChoices(["( ) Incorrect", "(o) Correct"])
    assert choices.root[0].text == choices[0].text == "Incorrect"
    choices[0] = "( ) Wrong"
    choices_updated = qk.SingleSelectChoices(["( ) Wrong", "(o) Correct"])
    assert choices.model_validate(choices) == choices_updated


def test_choice_validation():
    all_incorrect_choices = ["( ) incorrect", "( ) another incorrect"]
    all_incorrect = qk.SingleSelectChoices.model_validate(
        all_incorrect_choices, context={"ignore_n_correct": True}
    )
    assert all_incorrect.n_correct == 0
    with pytest.raises(ValidationError):
        qk.SingleSelectChoices.model_validate(all_incorrect_choices)

    all_correct_choices = ["(o) incorrect", "(o) another incorrect"]
    all_correct = qk.SingleSelectChoices.model_validate(
        all_correct_choices, context={"ignore_n_correct": True}
    )
    assert all_correct.n_incorrect == 0
    with pytest.raises(ValidationError):
        qk.SingleSelectChoices.model_validate(all_correct_choices)

    all_correct_multi_choices = ["(x) incorrect", "(x) another incorrect"]
    all_correct_multi = qk.MultipleSelectChoices.model_validate(
        all_correct_multi_choices, context={"ignore_n_correct": True}
    )
    with pytest.raises(ValidationError):
        qk.MultipleSelectChoices.model_validate(all_correct_multi_choices)
    assert all_correct_multi.n_incorrect == 0
