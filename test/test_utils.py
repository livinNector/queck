import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Literal

import pytest

from queck.utils import Merger, get_literal_union_args, safe_write_file, write_file

from .common import load_fixture

merger_test_case = load_fixture("merger_fixture.yaml")


def get_literal_union_test_cases():
    plain_union = Literal["a"] | Literal["b"]
    union_with_literal = plain_union | Literal["c"]
    type union_type_alias = Literal["a"] | Literal["b"]
    union_with_type_alias = union_type_alias | Literal["c"]
    type nested_type_alias = union_type_alias | Literal["c"]
    type generic_type_alias[T] = union_type_alias | T
    type multi_arg_generic_type_alias[T, U] = union_type_alias | T | U
    union_with_generic_type_alias = generic_type_alias | Literal["d"]
    type nested_generic_type_alias[T] = generic_type_alias[T] | Literal["d"]
    return [
        (plain_union, ["a", "b"]),
        (union_with_literal, ["a", "b", "c"]),
        (union_type_alias, ["a", "b"]),
        (union_with_type_alias, ["a", "b", "c"]),
        (nested_type_alias, ["a", "b", "c"]),
        (generic_type_alias[Literal["c"]], ["a", "b", "c"]),
        (
            multi_arg_generic_type_alias[Literal["c"], Literal["d"]],
            ["a", "b", "c", "d"],
        ),
        (union_with_generic_type_alias[Literal["c"]], ["a", "b", "c", "d"]),
        (nested_generic_type_alias[Literal["c"]], ["a", "b", "c", "d"]),
    ]


literal_union_test_cases = get_literal_union_test_cases()


@pytest.mark.parametrize(
    "input,expected",
    literal_union_test_cases,
)
def test_get_union_literal_args(input, expected):
    assert get_literal_union_args(input) == expected


def test_merger():
    merger = Merger(extend_lists=False, extend_dicts=False)
    merger_extend_lists = Merger(extend_lists=True, extend_dicts=False)
    merger_extend_dicts = Merger(extend_lists=False, extend_dicts=True)
    merger_extend_both = Merger(extend_lists=True, extend_dicts=True)
    a, b = deepcopy(merger_test_case["a"]), merger_test_case["b"]
    merger.merge(a, b)
    assert a == merger_test_case["result"]

    a = deepcopy(merger_test_case["a"])
    merger_extend_lists.merge(a, b)
    assert a == merger_test_case["result_extend_lists"]

    a = deepcopy(merger_test_case["a"])
    merger_extend_dicts.merge(a, b)
    assert a == merger_test_case["result_extend_dicts"]

    a = deepcopy(merger_test_case["a"])
    merger_extend_both.merge(a, b)
    assert a == merger_test_case["result_extend_both"]


def test_write_functions():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Basic check
        file_path = tmpdir / "example.txt"
        safe_write_file(file_path, "Hello, world!")
        assert (file_path).read_text() == "Hello, world!"

        # Raises Error if exists
        with pytest.raises(FileExistsError):
            safe_write_file(file_path, "This should fail")

        # Overwrite using write_file
        write_file(file_path, "Overwritten content")
        assert (file_path).read_text() == "Overwritten content"

        md_file_path = tmpdir / "example.md"

        # Test extension argument
        safe_write_file(file_path, "With extension", extension="md")
        assert (md_file_path).read_text() == "With extension"
