"""Utility functions for file operations and data transformation."""


import logging
import csv
import json
import os
import pickle
import random
from typing import cast, Any, Iterable, Optional, Union
from datasets import load_dataset
import pandas as pd
from pydantic import ValidationError
from adgtk.data.structure import (
    OrientationTypes,
    FileDataDefinition,
    FileDefinition,
    InMemoryDataDefinition
)

# ----------------------------------------------------------------------
# Constants and types
# ----------------------------------------------------------------------

ReturnDataTypes = Union[dict, list, pd.DataFrame, None]

# ----------------------------------------------------------------------
# Inspection Functions
# ----------------------------------------------------------------------


def valid_dict_of_lists(data: dict) -> bool:
    """Verifies a dict is valid for actions such as shuffling/flipping.

    Args:
        data: The dictionary to inspect.

    Returns:
        True if all lists in the dictionary have the same length.
    """
    keys = list(data.keys())
    list_lengths = [len(data[k]) for k in keys]

    if len(set(list_lengths)) != 1:
        return False
    return True


def inspect_current_orientation(data: ReturnDataTypes) -> OrientationTypes:
    """Determines the orientation type of the provided data.

    Args:
        data: The data to inspect.

    Returns:
        The detected orientation type of the data.
    """
    found_orientation = "other"
    if isinstance(data, pd.DataFrame):
        found_orientation = "pandas"
    elif isinstance(data, list):
        if isinstance(data[0], dict):
            found_orientation = "list_contains_dict"
        elif isinstance(data[0], str):
            found_orientation = "list_contains_string"
    elif isinstance(data, dict):
        # assumption:
        found_orientation = "dict_contains_list"
        for key, value in data.items():
            if not isinstance(value, list):
                # reduced precision
                found_orientation = "dict"
    # pylance/tox is complaining about str instead of literal
    return found_orientation        # type: ignore


# ----------------------------------------------------------------------
# Loading Functions
# ----------------------------------------------------------------------

def load_data_from_csv_file(filename: str) -> list:
    """Loads a CSV file into a list of dictionaries.

    Args:
        filename: The path to the CSV file.

    Returns:
        A list of dictionaries representing the CSV rows.
    """
    columns: list[str] = []
    records: list[dict] = []

    with open(filename, "r") as infile:
        csv_reader = csv.reader(infile)
        for row in csv_reader:
            # we are on the first row when len == 0
            if len(columns) == 0:
                columns = row
            else:
                data: dict[Any, Any] = {}
                for idx, col in enumerate(columns):
                    data[col] = row[idx]
                records.append(data)
    return records


def load_data_from_file(
    file_def: FileDefinition
) -> ReturnDataTypes:
    """Loads data from disk based on a FileDefinition.

    Args:
        file_def: The definition of the file to load.

    Raises:
        ValueError: If the file extension is unexpected or encoding is
            unsupported.

    Returns:
        The loaded data in its native or requested format.
    """
    file_w_path = os.path.join(file_def.path, file_def.filename)
    encoding = file_def.encoding

    # --------- load the data from file ---------
    # First, load the data for the types that can transform
    data: Optional[Union[pd.DataFrame, dict, list]] = None

    if encoding == "csv":
        data = load_data_from_csv_file(file_w_path)
    elif encoding == "hf-json":
        data = load_dataset("json", data_files=file_w_path)
    elif encoding == "json":
        with open(file_w_path, encoding="utf-8", mode="r") as infile:
            try:
                data = json.load(infile)
            except json.decoder.JSONDecodeError:
                raise ValueError("JSON error opening file %s", file_w_path)
    elif encoding == "pickle":
        with open(file_w_path, mode="rb") as infile:
            data = pickle.load(infile)
    elif encoding == "pandas":
        if file_w_path.endswith(".csv"):
            data = pd.read_csv(file_w_path)
        elif file_w_path.endswith(".pkl"):
            data = pd.read_pickle(file_w_path)
        else:
            raise ValueError("Unexpected file extension")
    else:
        logging.warning(
            f"Unknown encoding defined for {file_def}")
        raise ValueError("Unsupported encoding")

    if data is None:
        ValueError("Data is None after load.")
    return data


def change_orientation(
    data: ReturnDataTypes,
    target_orientation: OrientationTypes
) -> ReturnDataTypes:
    """Changes the orientation of data to align with a target format.

    Args:
        data: The data to transform.
        target_orientation: The desired target data orientation.

    Raises:
        RuntimeError: If the transformation fails.

    Returns:
        The data transformed into the target orientation.
    """

    # ------- identify source orientation ------
    found_orientation = inspect_current_orientation(data)
    if found_orientation == target_orientation:
        return data

    # ------- target transformations -------
    if found_orientation == "list_contains_string":
        if target_orientation == "list_contains_string":
            return data
    elif found_orientation == "pandas":
        # only way here is if found is pandas
        data = cast(pd.DataFrame, data)

        if target_orientation == "pandas":
            return data
        elif target_orientation == "list_contains_dict":
            return flip_from_dict_to_list(data.to_dict())   # type: ignore
        elif target_orientation == "dict_contains_list":
            return data.to_dict()   # type: ignore
        else:
            logging.warning(
                "Unexpected target_orientation %s for pandas source",
                target_orientation)
            return data.to_dict()   # type: ignore
    elif found_orientation == "list_contains_dict":
        data = cast(list, dict)
        if target_orientation == "list_contains_dict":
            return data
        elif target_orientation == "dict_contains_list":
            return flip_from_list_to_dict(data)
        elif target_orientation == "pandas":
            return pd.DataFrame(data)
    elif found_orientation == "dict_contains_list":
        data = cast(dict, data)
        if target_orientation == "dict_contains_list":
            return data
        elif target_orientation == "list_contains_dict":
            return flip_from_dict_to_list(data)

    raise RuntimeError("Failed to transform.")


# ----------------------------------------------------------------------
# Transformation functions
# ----------------------------------------------------------------------


def flip_from_list_to_dict(data: list) -> dict:
    """Transforms a list of dictionaries into a dictionary of lists.

    Args:
        data: The list of dictionaries to transform.

    Raises:
        ValueError: If the list is empty or malformed.
        RuntimeError: If the resulting dictionary fails validation.

    Returns:
        A dictionary where each key maps to a list of values.
    """

    if len(data) == 0:
        raise ValueError("No data to flip")

    # initialize
    flipped: dict[str, list] = {}

    # process
    for row in data:
        try:
            for key, value in row.items():
                if key not in flipped.keys():
                    # add a list
                    flipped[key] = []
                # now append
                flipped[key].append(value)
        except IndexError:
            raise ValueError("Unable to flip_from_list_to_dict")
    # safety check
    if valid_dict_of_lists(flipped):
        return flipped

    raise RuntimeError("Error flipping data from list to dict")


def flip_from_dict_to_list(data: dict) -> list:
    """Transforms a dictionary of lists into a list of dictionaries.

    Args:
        data: The dictionary of lists to transform.

    Raises:
        ValueError: If list lengths are inconsistent.

    Returns:
        A list of dictionaries, one for each index in the source lists.
    """
    dest = []
    if not valid_dict_of_lists(data):
        msg = "Invalid dict type for flipping. Lists are different lengths"
        raise ValueError(msg)

    keys = list(data.keys())
    for idx in range(len(data[keys[0]])):
        to_insert = {}
        for key in keys:
            to_insert[key] = data[key][idx]
        dest.append(to_insert)
    return dest


def remap_data(
    data: ReturnDataTypes,
    key_map: dict[str, str]
) -> ReturnDataTypes:
    """Remaps keys or columns in the data using a provided mapping.

    Args:
        data: The data object to remap.
        key_map: A dictionary mapping old keys to new keys.

    Raises:
        TypeError: If the data type is not supported for remapping.

    Returns:
        The data with updated keys or columns.
    """

    if isinstance(data, pd.DataFrame):
        return data.rename(columns=key_map)
    elif isinstance(data, dict):
        for old_key, new_key in key_map.items():
            if old_key in data.keys():
                data[new_key] = data.pop(old_key)
    elif isinstance(data, Iterable):
        for row in data:
            for old_key, new_key in key_map.items():
                if old_key in row.keys():
                    row[new_key] = row.pop(old_key)
    else:
        raise TypeError(f"Unexpected Data type {type(data)} for remap_data")
    return data


def shuffle_dict_of_lists(data: dict) -> dict:
    """Shuffles a dictionary containing lists synchronously.

    Args:
        data: The dictionary of lists to shuffle.

    Raises:
        ValueError: If list lengths are inconsistent.

    Returns:
        A dictionary with all lists shuffled using the same random indices.
    """

    if not valid_dict_of_lists(data):
        msg = "Invalid dict type for shuffling. Lists are different lengths"
        raise ValueError(msg)

    keys = list(data.keys())
    list_lengths = [len(data[k]) for k in keys]
    indices = list(range(list_lengths[0]))
    random.shuffle(indices)

    return {k: [data[k][i] for i in indices] for k in keys}


def shuffle_data(data: ReturnDataTypes) -> ReturnDataTypes:
    """Shuffles data based on its detected type.

    Args:
        data: The data to shuffle.

    Returns:
        The shuffled data object.
    """
    if isinstance(data, list):
        random.shuffle(data)
        return data     # random.shuffle is in-place but return=consistent
    elif isinstance(data, dict):
        return shuffle_dict_of_lists(data)
    elif isinstance(data, pd.DataFrame):
        return data.sample(frac=1).reset_index(drop=True)
    raise ValueError("Unexpected data type")


def split_dict(data: dict, keys: list) -> tuple:
    """Splits a dictionary into two based on a list of keys.

    Keys found in the 'keys' list are moved to the 'right' dictionary,
    while all others remain in the 'left' dictionary.

    Args:
        data: The dictionary to split.
        keys: The list of keys to assign to the right dictionary.

    Returns:
        A tuple containing (left_dict, right_dict).
    """
    left = {}
    right = {}

    for key, value in data.items():
        if key in keys:
            right[key] = value
        else:
            left[key] = value
    return left, right


def split_data_into_left_right(
    data: Union[list, dict, pd.DataFrame],
    keys: list
) -> tuple:
    """Splits a data structure into left and right components.

    Args:
        data: The data structure (list, dict, or DataFrame) to split.
        keys: The keys or columns to move to the right component.

    Returns:
        A tuple of (left, right) preserving the original data type.
    """

    if isinstance(data, dict):
        return split_dict(data=data, keys=keys)
    elif isinstance(data, pd.DataFrame):
        left = data.drop(columns=keys, errors="ignore")
        right = data[keys].copy()
    elif isinstance(data, list):
        left = []
        right = []
        for row in data:
            if isinstance(row, dict):
                l_row, r_row = split_dict(data=row, keys=keys)
                left.append(l_row)
                right.append(r_row)
    return left, right


# ----------------------------------------------------------------------
# Orchestration functions
# ----------------------------------------------------------------------

def load_data(
    data_def: Union[
        InMemoryDataDefinition,
        FileDataDefinition,
        FileDefinition,
        dict]
) -> ReturnDataTypes:
    """Loads and transforms data according to a definition.

    Handles loading from disk or memory, followed by shuffling,
    orientation changes, and key remapping as specified.

    Args:
        data_def: The definition specifying how to load and process data.

    Raises:
        ValueError: If the definition type is unrecognized or invalid.

    Returns:
        The fully processed data, or None if no data was found.
    """
    # --------- loading of data -----------
    data = None
    if isinstance(data_def, dict):
        # Try FileDataDefinition
        try:
            data_def = FileDataDefinition(**data_def)
        except ValidationError:
            pass
        # file def not file data def?
        try:
            data_def = FileDefinition(**data_def)   # type: ignore

        except ValidationError:
            pass
        # inMemory?
        try:
            data_def = InMemoryDataDefinition(**data_def)   # type: ignore
        except ValidationError:
            raise ValueError("Unexpected data definition. Unable to load")

    # now processing
    if isinstance(data_def, FileDataDefinition):
        data = load_data_from_file(file_def=data_def.file_definition)
    elif isinstance(data_def, InMemoryDataDefinition):
        data = data_def.data
    elif isinstance(data_def, FileDefinition):
        data_def = FileDataDefinition(
            shuffle_on_load=False,
            key_rename_map=None,
            target_orientation=None,
            file_definition=data_def
        )
        load_data_from_file(file_def=data_def.file_definition)

    # confirm load? None is acceptable to return.
    if data is None:
        return None

    # --------- processing of data -----------
    if data_def.shuffle_on_load is not None:
        if data_def.shuffle_on_load:
            data = shuffle_data(data)

    # change orientation?
    target_orientation = data_def.target_orientation
    if target_orientation is not None:
        data = change_orientation(
            data=data, target_orientation=target_orientation)

    # remapping requested?
    if data_def.key_rename_map is not None:
        data = remap_data(data=data, key_map=data_def.key_rename_map)

    # and return
    return data
