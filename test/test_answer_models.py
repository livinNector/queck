import pytest
from pydantic import BaseModel, ValidationError

import queck as qk

from .common import load_fixture

answer_fixtures = load_fixture("answer_fixtures.yaml")
answer_conversion_fixtures = load_fixture("answer_conversion_fixtures.yaml")
answer_attr_check_fixtures = load_fixture("answer_attr_check_fixtures.yaml")
answer_parsed_validation_fixtures = load_fixture(
    "answer_parsed_validation_fixtures.yaml"
)


@pytest.mark.parametrize(
    "test_item", answer_fixtures, ids=[f["title"] for f in answer_fixtures]
)
def test_answers(test_item):
    model: BaseModel = getattr(qk.answer_models, test_item["model"])
    answer_constructed = model(root=test_item["item"])
    answer_validated = model.model_validate(test_item["item"])
    answer_parsed_validated = model.model_validate(
        test_item["parsed"], context={"from_parsed": True}
    )

    assert answer_constructed == answer_validated
    assert answer_parsed_validated == answer_validated
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


# @pytest.mark.parametrize(
#     "test_item",
#     answer_parsed_validation_fixtures,
#     ids=[f["title"] for f in answer_parsed_validation_fixtures],
# )
# def test_parsed_validation(test_item):
#     model: BaseModel = getattr(qk.answer_models, test_item["model"])

#     formatted = model.model_validate(test_item["formatted"])
#     formatted = model.model_validate(test_item["formatted"])

#     for attr in test_item["attrs"]:
#         assert getattr(item, attr["name"]) == attr["value"]


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
