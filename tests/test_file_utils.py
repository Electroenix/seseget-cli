import os

from seseget.utils.file_utils import (
    get_file_basename,
    make_diff_dir_name,
    make_filename_valid,
)


def test_make_filename_valid_removes_illegal_characters():
    filename = 'a/b\\c:d*e?f"g<h>i|j'

    result = make_filename_valid(filename)

    for char in '\\/*?:<>"|':
        assert char not in result
    assert result == "a b c d e f g h i j"


def test_make_filename_valid_normalizes_whitespace_and_trailing_dots():
    assert make_filename_valid("  a\t\nb   c  ") == "a b c"
    assert make_filename_valid("name...") == "name"
    assert make_filename_valid("\x00hidden\x1f") == "hidden"


def test_make_diff_dir_name_adds_and_increments_suffix(tmp_path):
    path = str(tmp_path / "comic")
    os.makedirs(path)

    assert make_diff_dir_name(path) == f"{path}_[1]"
    os.makedirs(f"{path}_[1]")
    assert make_diff_dir_name(path) == f"{path}_[2]"

    os.makedirs(f"{path}_[2]")
    assert make_diff_dir_name(path) == f"{path}_[3]"


def test_make_diff_dir_name_returns_original_when_unused(tmp_path):
    path = str(tmp_path / "unused")

    assert make_diff_dir_name(path) == path


def test_get_file_basename():
    assert get_file_basename("/tmp/a/b/c.jpg") == "c.jpg"
    assert get_file_basename("c.jpg") == "c.jpg"
