import pytest
from IPython.testing.globalipapp import get_ipython
from pydantic import BaseModel

import queck as qk

from .common import load_fixture

question_fixtures = load_fixture("question_fixtures.yaml")
question_fixtures = load_fixture("question_fixtures.yaml")


@pytest.mark.parametrize(
    "test_item", question_fixtures, ids=[f["title"] for f in question_fixtures]
)
def test_question(test_item):
    model: BaseModel = getattr(qk, test_item["model"])
    answer_constructed = model(**test_item["item"])
    answer_validated = model.model_validate(test_item["item"])

    assert answer_constructed == answer_validated
    parsed_dict = answer_constructed.model_dump(context={"parsed": True})
    assert test_item["parsed"] == parsed_dict

    rendered_dump_dict = answer_constructed.model_dump(context={"rendered": True})
    rendered_dict = answer_constructed.to_dict(rendered=True)
    assert test_item["rendered"] == rendered_dump_dict == rendered_dict

    parsed_rendered_dump_dict = answer_constructed.model_dump(
        context={"parsed": True, "rendered": True}
    )
    parsed_rendered_dict = answer_constructed.to_dict(parsed=True, rendered=True)
    assert (
        test_item["parsed_rendered"]
        == parsed_rendered_dump_dict
        == parsed_rendered_dict
    )

    assert answer_constructed.to_yaml() == test_item["yaml"]
    assert answer_constructed.to_md() == test_item["md"]

    formatted = test_item.get("formatted")
    if formatted:
        assert formatted == answer_constructed.model_dump()
        assert formatted == answer_constructed.model_dump(context={"formatted": True})
        assert formatted == answer_constructed.model_dump(context={"parsed": False})


ip = get_ipython()
ip.run_line_magic("load_ext", line="queck")


@pytest.mark.parametrize(
    "test_item",
    question_fixtures,
    ids=[f"{f['title']} - IPython Magic" for f in question_fixtures],
)
def test_ipython_magic(test_item):
    ip.run_cell_magic("queck", line=None, cell=test_item["yaml"]) == test_item["item"]
