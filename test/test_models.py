import pytest
from pydantic import ValidationError

# Importing all the necessary components from the provided code
from queck.answer_models import (
    CorrectChoice,
    IncorrectChoice,
    Integer,
    MultipleCorrectChoices,
    NumRange,
    NumTolerance,
    ShortAnswer,
    SingleCorrectChoice,
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


# Parameterized tests for choices
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
            "(x) Correct Choice Line 1\nLine 2 // Explanation Line 1\nLine 2",
            "Correct Choice Line 1\nLine 2",
            "Explanation Line 1\nLine 2",
            True,
        ),
    ],
)
def test_choices(choice_str, expected_text, expected_feedback, is_correct):
    choice = (
        CorrectChoice(root=choice_str)
        if is_correct
        else IncorrectChoice(root=choice_str)
    )
    assert choice.text == expected_text
    assert choice.feedback == expected_feedback
    assert choice.is_correct == is_correct


@pytest.mark.parametrize(
    "choice_str, expected_text, expected_feedback",
    [
        ("(x) Correct Choice // Explanation", "Correct Choice", "Explanation"),
        (
            "(x) Correct Choice Line 1\nLine 2 // Explanation Line 1\nLine 2",
            "Correct Choice Line 1\nLine 2",
            "Explanation Line 1\nLine 2",
        ),
        ("(x)\nCorrect Choice\n// Explanation", "Correct Choice", "Explanation"),
        (
            "(x)\nCorrect Choice\n\n\n// \n\nExplanation\n\n",
            "Correct Choice",
            "Explanation",
        ),
    ],
)
def test_correct_choice(choice_str, expected_text, expected_feedback):
    validated = CorrectChoice.model_validate(choice_str)
    assert validated.text == expected_text
    assert validated.feedback == expected_feedback
    validated = CorrectChoice(root=choice_str)
    assert validated.text == expected_text
    assert validated.feedback == expected_feedback


@pytest.mark.parametrize(
    "choice_str, expected_text, expected_feedback",
    [
        ("( ) Incorrect Choice // Explanation", "Incorrect Choice", "Explanation"),
        (
            "( ) Incorrect Choice Line 1\nLine 2 // Explanation Line 1\nLine 2",
            "Incorrect Choice Line 1\nLine 2",
            "Explanation Line 1\nLine 2",
        ),
        ("( )\nIncorrect Choice\n// Explanation", "Incorrect Choice", "Explanation"),
        (
            "( )\nIncorrect Choice\n\n\n// \n\nExplanation\n\n",
            "Incorrect Choice",
            "Explanation",
        ),
    ],
)
def test_incorrect_choice(choice_str, expected_text, expected_feedback):
    validated = IncorrectChoice.model_validate(choice_str)
    assert validated.text == expected_text
    assert validated.feedback == expected_feedback
    validated = IncorrectChoice(root=choice_str)
    assert validated.text == expected_text
    assert validated.feedback == expected_feedback


# Parameterized tests for numerical ranges and tolerances
@pytest.mark.parametrize(
    "range_str, expected_low, expected_high",
    [
        ("10..1", 1, 10),
        ("-10..1.0", -10, 1.0),
    ],
)
def test_num_range(range_str, expected_low, expected_high):
    num_range = NumRange(root=range_str)
    assert num_range.low == expected_low
    assert num_range.high == expected_high
    num_range = NumRange.model_validate(range_str)
    assert num_range.low == expected_low
    assert num_range.high == expected_high


@pytest.mark.parametrize(
    "tolerance_str, expected_value, expected_tolerance",
    [
        ("100|5", 100, 5),
        ("-100.5|0.03", -100.5, 0.03),
    ],
)
def test_num_tolerance(tolerance_str, expected_value, expected_tolerance):
    num_tolerance = NumTolerance(root=tolerance_str)
    assert num_tolerance.value == expected_value
    assert num_tolerance.tolerance == expected_tolerance
    num_range = NumTolerance.model_validate(tolerance_str)
    assert num_range.value == expected_value
    assert num_range.tolerance == expected_tolerance


def test_integer():
    value = 42
    assert value == Integer(root=value).value
    assert value == Integer.model_validate(value).value
    assert value == Integer.model_validate(value).model_dump()


def test_short_answer():
    value = "This is a short answer"
    assert value == ShortAnswer(root=value).value
    assert value == ShortAnswer.model_validate(value).value
    assert value == ShortAnswer.model_validate(value).model_dump()


# Parameterized tests for single and multiple correct choices
@pytest.mark.parametrize(
    "choices, n_correct, n_incorrect",
    [
        (
            [
                CorrectChoice(root="(x) Correct Answer"),
                IncorrectChoice(root="( ) Incorrect Answer"),
            ],
            1,
            1,
        ),
        (
            [
                CorrectChoice(root="(x) Correct Answer"),
                CorrectChoice(root="(x) Another Correct Answer"),
                IncorrectChoice(root="( ) Incorrect Answer"),
            ],
            2,
            1,
        ),
    ],
)
def test_choice_groups(choices, n_correct, n_incorrect):
    if n_correct == 1:
        single_choice = SingleCorrectChoice(root=choices)
        assert single_choice.n_correct == n_correct
        assert single_choice.n_incorrect == n_incorrect
    else:
        multiple_choices = MultipleCorrectChoices(root=choices)
        assert multiple_choices.n_correct == n_correct
        assert multiple_choices.n_incorrect == n_incorrect


# Tests for other models
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


# Test serialization of Queck
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
