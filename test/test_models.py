import pytest

from queck.answer_models import (
    IncorrectChoice,
    Integer,
    MultipleSelectChoices,
    MultipleSelectCorrectChoice,
    NumRange,
    NumTolerance,
    ShortAnswer,
    SingleSelectChoices,
    SingleSelectCorrectChoice,
)
from queck.queck_models import (
    CommonDataQuestion,
    Description,
    Queck,
    Question,
)


@pytest.fixture
def question_fixture():
    return Question(
        text="What is 2 + 2?",
        answer=Integer(root=4),
        feedback="Correct answer is 4.",
        marks=1,
        tags=["math", "easy"],
    )


@pytest.fixture
def common_data_question_fixture():
    return CommonDataQuestion(
        text="Shared context for questions.",
        questions=[
            Question(
                text="Question 1",
                answer=Integer(root=5),
                marks=2,
            ),
            Question(
                text="Question 2",
                answer=ShortAnswer(root="Answer"),
                marks=3,
            ),
        ],
    )


@pytest.fixture
def queck_fixture():
    return Queck(
        title="Sample Quiz",
        questions=[
            Description(text="Introduction to the quiz."),
            Question(
                text="What is 5 + 5?",
                answer=Integer(root=10),
                marks=2,
            ),
        ],
    )


@pytest.mark.parametrize(
    "choice_str, expected_text, expected_feedback, is_correct",
    [
        ("(x) Correct Choice // Explanation", "Correct Choice", "Explanation", True),
        (
            "( ) Incorrect Choice // Explanation",
            "Incorrect Choice",
            "Explanation",
            False,
        ),
        (
            "(x) Correct Choice Line 1  \nLine 2 // Explanation Line 1  \nLine 2",
            "Correct Choice Line 1\\\nLine 2",
            "Explanation Line 1\\\nLine 2",
            True,
        ),
        ("( )\nCorrect Choice\n// Explanation", "Correct Choice", "Explanation", False),
        (
            "(x)\nCorrect Choice\n\n\n// \n\nExplanation\n\n",
            "Correct Choice",
            "Explanation",
            True,
        ),
    ],
)
def test_choices(choice_str, expected_text, expected_feedback, is_correct):
    instantiated = (
        MultipleSelectCorrectChoice(root=choice_str)
        if is_correct
        else IncorrectChoice(root=choice_str)
    )
    validated = (
        MultipleSelectCorrectChoice.model_validate(choice_str)
        if is_correct
        else IncorrectChoice.model_validate(choice_str)
    )

    assert instantiated == validated
    assert instantiated.text == expected_text
    assert instantiated.feedback == expected_feedback
    assert instantiated.is_correct == is_correct
    parsed = {
        "text": expected_text,
        "feedback": expected_feedback,
        "is_correct": is_correct,
        "type": instantiated.type,
    }

    assert instantiated.model_dump(context={"parsed": True}) == parsed


@pytest.mark.parametrize(
    ["range_str", "expected_low", "expected_high", "serialized"],
    [
        ("10..1", 1, 10, "1..10"),
        ("10  .. 1", 1, 10, "1..10"),
        ("-10..1.2", -10, 1.2, "-10..1.2"),
    ],
)
def test_num_range(range_str, expected_low, expected_high, serialized):
    num_range = NumRange(root=range_str)
    num_range_validated = NumRange.model_validate(range_str)
    assert num_range == num_range_validated
    assert num_range.value.low == expected_low
    assert num_range.value.high == expected_high
    assert num_range.model_dump() == serialized
    assert num_range.model_dump(context={"parsed": True}) == {
        "value": {
            "low": expected_low,
            "high": expected_high,
        },
        "type": "num_range",
    }


@pytest.mark.parametrize(
    "tolerance_str, expected_value, expected_tolerance, serialized",
    [
        (
            "100 |  5",
            100,
            5,
            "100|5",
        ),
        ("-100.5|0.03", -100.5, 0.03, "-100.5|0.03"),
    ],
)
def test_num_tolerance(tolerance_str, expected_value, expected_tolerance, serialized):
    num_tolerance = NumTolerance(root=tolerance_str)
    num_tolerance_validated = NumTolerance.model_validate(tolerance_str)

    assert num_tolerance == num_tolerance_validated
    assert num_tolerance.value.value == expected_value
    assert num_tolerance.value.tolerance == expected_tolerance
    assert num_tolerance_validated.model_dump() == serialized
    assert num_tolerance_validated.model_dump(context={"parsed": True}) == {
        "value": {
            "value": expected_value,
            "tolerance": expected_tolerance,
        },
        "type": "num_tolerance",
    }


@pytest.mark.parametrize(
    ["value", "model", "type"],
    [(4, Integer, "num_int"), ("answer", ShortAnswer, "short_answer")],
)
def test_value_models(value, model, type):
    instantiated = model(root=value)
    validated = model.model_validate(value)
    assert value == instantiated.value == validated.value
    assert value == instantiated.model_dump()
    assert {"value": value, "type": type} == instantiated.model_dump(
        context={"parsed": True}
    )


@pytest.mark.parametrize(
    "choices, n_correct, n_incorrect",
    [
        (
            [
                SingleSelectCorrectChoice(root="(o) Correct Answer"),
                IncorrectChoice(root="( ) Incorrect Answer"),
            ],
            1,
            1,
        ),
        (
            [
                MultipleSelectCorrectChoice(root="(x) Correct Answer"),
                MultipleSelectCorrectChoice(root="(x) Another Correct Answer"),
                IncorrectChoice(root="( ) Incorrect Answer"),
            ],
            2,
            1,
        ),
    ],
)
def test_choice_groups(choices, n_correct, n_incorrect):
    if n_correct == 1:
        single_choice = SingleSelectChoices(root=choices)
        assert single_choice.n_correct == n_correct
        assert single_choice.n_incorrect == n_incorrect
    else:
        multiple_choices = MultipleSelectChoices(root=choices)
        assert multiple_choices.n_correct == n_correct
        assert multiple_choices.n_incorrect == n_incorrect


@pytest.mark.parametrize(
    "model_fixture, expected_marks",
    [
        ("question_fixture", 1),
        ("common_data_question_fixture", 5),
    ],
)
def test_models(model_fixture, expected_marks, request):
    model = request.getfixturevalue(model_fixture)
    assert model.marks == expected_marks


def test_queck_serialization(queck_fixture):
    queck = queck_fixture
    assert queck.title == "Sample Quiz"
    assert len(queck.questions) == 2

    yaml_output = queck.to_queck()
    assert "Sample Quiz" in yaml_output

    json_output = queck.to_json()
    assert "Sample Quiz" in json_output


if __name__ == "__main__":
    pytest.main()
