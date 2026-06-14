# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false

"""test_data_utils.py is focused on testing the data.utils module.

Testing
=======
py -m pytest -s test/data/test_utils.py

note: initial test cases generated via a model. modified code to meet
      needs and fix bugs, etc.
"""

import json
import pandas as pd
import adgtk.data.utils as utils
from adgtk.data.structure import FileDefinition, FileDataDefinition


def test_valid_dict_of_lists():
    """valid_dict_of_lists returns True only when all lists share the same
    length.
    """
    valid = {"a": [1, 2], "b": [3, 4]}
    invalid = {"a": [1], "b": [2, 3]}
    assert utils.valid_dict_of_lists(valid)
    assert not utils.valid_dict_of_lists(invalid)


def test_inspect_current_orientation():
    """inspect_current_orientation identifies the container type of the
    input data.
    """
    assert utils.inspect_current_orientation(pd.DataFrame()) == "pandas"
    assert utils.inspect_current_orientation([{"a": 1}]) == "list_contains_dict"
    assert utils.inspect_current_orientation(["a", "b"]) == "list_contains_string"
    assert utils.inspect_current_orientation({"a": [1, 2]}) == "dict_contains_list"
    assert utils.inspect_current_orientation({"a": 1}) == "dict"


def test_flip_from_list_to_dict_and_back():
    """flip_from_list_to_dict and flip_from_dict_to_list are inverse
    operations.
    """
    list_data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    dict_data = utils.flip_from_list_to_dict(list_data)
    expected_dict = {"a": [1, 3], "b": [2, 4]}
    assert dict_data == expected_dict

    reverted = utils.flip_from_dict_to_list(dict_data)
    assert reverted == list_data


def test_remap_data():
    """remap_data renames keys for both list-of-dicts and DataFrame inputs."""
    data = [{"old": 1}, {"old": 2}]
    key_map = {"old": "new"}
    result = utils.remap_data(data, key_map)
    assert result == [{"new": 1}, {"new": 2}]

    df = pd.DataFrame([{"old": 1}, {"old": 2}])
    remapped_df = utils.remap_data(df, key_map)
    assert "new" in remapped_df.columns
    assert "old" not in remapped_df.columns


def test_shuffle_dict_of_lists():
    """shuffle_dict_of_lists reorders rows without losing any values."""
    data = {"a": list(range(10)), "b": list(range(10))}
    shuffled = utils.shuffle_dict_of_lists(data)
    assert sorted(shuffled["a"]) == list(range(10))


def test_shuffle_data_with_dataframe():
    """shuffle_data returns a DataFrame with the same values in a different
    order.
    """
    df = pd.DataFrame({"a": list(range(10))})
    shuffled_df = utils.shuffle_data(df)
    assert isinstance(shuffled_df, pd.DataFrame)
    assert set(shuffled_df["a"]) == set(df["a"])


def test_split_dict():
    """split_dict partitions a dict into keys not in the list and keys in the
    list.
    """
    data = {"a": 1, "b": 2, "c": 3}
    left, right = utils.split_dict(data, ["a", "c"])
    assert left == {"b": 2}
    assert right == {"a": 1, "c": 3}


def test_split_data_into_left_right_list():
    """split_data_into_left_right separates selected keys from remaining keys
    across all rows.
    """
    data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    left, right = utils.split_data_into_left_right(data, ["a"])
    assert left == [{"b": 2}, {"b": 4}]
    assert right == [{"a": 1}, {"a": 3}]


def test_load_data_from_csv_with_remap_and_shuffle(tmp_path):
    """load_data applies key renaming and shuffle when loading a CSV via
    FileDataDefinition.
    """
    csv_content = "old1,old2\n1,2\n3,4\n"
    file_path = tmp_path / "test.csv"
    file_path.write_text(csv_content)

    file_def = FileDefinition(
        file_id="file123456",
        path=str(tmp_path),
        filename="test.csv",
        encoding="csv"
    )
    data_def = FileDataDefinition(
        file_definition=file_def,
        key_rename_map={"old1": "new1", "old2": "new2"},
        shuffle_on_load=True
    )

    data = utils.load_data(data_def)
    assert isinstance(data, list)
    for row in data:
        assert "new1" in row and "new2" in row


def test_load_data_from_json(tmp_path):
    """load_data returns the original list when loading a JSON-encoded file."""
    json_data = [{"a": 1}, {"a": 2}]
    file_path = tmp_path / "test.json"
    file_path.write_text(json.dumps(json_data))

    file_def = FileDefinition(
        file_id="file1235",
        path=str(tmp_path),
        filename="test.json",
        encoding="json"
    )
    data_def = FileDataDefinition(file_definition=file_def)

    data = utils.load_data(data_def)
    assert data == json_data


def test_load_data_from_pickle(tmp_path):
    """load_data returns a DataFrame when loading a pandas-encoded
    pickle file.
    """
    df = pd.DataFrame([{"x": 10, "y": 20}, {"x": 30, "y": 40}])
    file_path = tmp_path / "test.pkl"
    df.to_pickle(file_path)

    file_def = FileDefinition(
        file_id="file1234",
        path=str(tmp_path),
        filename="test.pkl",
        encoding="pandas"
    )
    data_def = FileDataDefinition(file_definition=file_def)

    data = utils.load_data(data_def)
    assert isinstance(data, pd.DataFrame)
    assert set(data.columns) == {"x", "y"}


def test_file_definition_with_optional_fields(tmp_path):
    """FileDefinition accepts tags and extended_metadata without affecting
    data loading.
    """
    csv_content = "col1,col2\n10,20\n30,40\n"
    file_path = tmp_path / "optional.csv"
    file_path.write_text(csv_content)

    file_def = FileDefinition(
        file_id="file123",
        path=str(tmp_path),
        filename="optional.csv",
        encoding="csv",
        extended_metadata={"metadata_file": "optional.meta.json"},
        tags=["example", "test"]
    )
    data_def = FileDataDefinition(file_definition=file_def)

    data = utils.load_data(data_def)
    assert isinstance(data, list)
    assert len(data) == 2
    assert all("col1" in row and "col2" in row for row in data)
