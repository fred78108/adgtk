"""File operations utility functions


"""

import logging
import csv
import json
import os
import pickle
import random
from typing import cast, Any, Iterable, Optional, Union
import pandas as pd
from pydantic import ValidationError
from adgtk.data.structure import(
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

def valid_dict_of_lists(data:dict) -> bool:
    """Verifies a dict is valid for actions such as shuffling/flipping.

    :param data: The data to inspect
    :type data: dict
    :return: True if a candidate for shuffling or flipping
    :rtype: bool
    """
    keys = list(data.keys())
    list_lengths = [len(data[k]) for k in keys]
    
    if len(set(list_lengths)) != 1:
        return False
    return True


def inspect_current_orientation(data:ReturnDataTypes) -> OrientationTypes:
    """Based on the data returns the orientation type.

    :param data: The data to inspect
    :type data: ReturnDataTypes
    :return: the orientation of the data
    :rtype: OrientationTypes
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

def load_data_from_csv_file(filename:str) -> list:
      """Loads a CSV file into a list of dictionaries.

      :param filename: The name of the file to load
      :type filename: str
      :return: The data from the file
      :rtype: list
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
    """Loads data from file

    :param file_def: _description_
    :type file_def: FileDefinition
    :raises ValueError: Unexpected value
    :return: _description_
    :rtype: ReturnDataTypes
    """
    file_w_path = os.path.join(file_def.path, file_def.filename)
    encoding = file_def.encoding

    # --------- load the data from file ---------
    # First, load the data for the types that can transform
    df:Optional[pd.DataFrame] = None
    data:Optional[Union[pd.DataFrame, dict, list]] = None

    if encoding == "csv":
        data = load_data_from_csv_file(file_w_path)

    elif encoding == "json":
        with open(file_w_path, encoding="utf-8", mode="r") as infile:
             data = json.load(infile)
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
    data:ReturnDataTypes,
    target_orientation: OrientationTypes
) -> ReturnDataTypes:
    """This function changes the orientation of data to align with a
    target. 

    :param data: The data to transform
    :type data: _type_
    :param orientation: The target data format
    :type orientation: OrientationTypes
    :raises RuntimeError: failed to transform

    :return: The data modified into the new orientation
    :rtype: ReturnDataTypes
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
            return flip_from_dict_to_list(data.to_dict())            
        elif target_orientation == "dict_contains_list":
            return data.to_dict()
        else:
            logging.warning(f"Unexpected target_orientation {target_orientation} for pandas source")
            return data.to_dict()
    elif found_orientation == "list_contains_dict":
        data = cast(list, dict)
        if target_orientation == "list_contains_dict":
            return data
        elif target_orientation =="dict_contains_list":
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


def flip_from_list_to_dict(data:list) -> dict:
    """Flips a list of data into a dict

    :param data: The data to transform
    :type data: list
    :raises ValueError: No data, malformed data for flipping
    :raises RuntimeError: general error with method
    :return: a list transformed into a dict with lists
    :rtype: dict
    """

    if len(data) == 0:
        raise ValueError("No data to flip")
    
    # initialize
    flipped:dict[str,list] = {}

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

def flip_from_dict_to_list(data:dict) -> list:
    """Converts a dict of lists into a list of dicts

    :param data: The data to transform
    :type data: dict
    :raises ValueError: Data is not properly formatted for flipping.
    :return: A list of dicts containing the same data elements
    :rtype: list
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
    data:ReturnDataTypes,
    key_map:dict[str,str]
) -> ReturnDataTypes:
    """Remaps data keys

    :param data: The data to remap
    :type data: ReturnDataTypes
    :param key_map: The mapping {from:to}
    :type key_map: dict[str,str]
    :raises TypeError: Unknown data type
    :return: The updated data with the new keys/columns
    :rtype: ReturnDataTypes
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
    """Shuffles a dict containing lists

    :param data: The data to shuffle
    :type data: dict
    :raises ValueError: Unexpected list length within dict
    :return: A shuffled dict of lists
    :rtype: dict
    """

    if not valid_dict_of_lists(data):
        msg = "Invalid dict type for shuffling. Lists are different lengths"
        raise ValueError(msg)
    
    keys = list(data.keys())
    list_lengths = [len(data[k]) for k in keys]
    indices = list(range(list_lengths[0]))
    random.shuffle(indices)

    return {k: [data[k][i] for i in indices] for k in keys}


def shuffle_data(data:ReturnDataTypes) -> ReturnDataTypes:
    """Shuffles the data by inspecting then shuffling based on the
    data type found.

    :param data: The data to shuffle
    :type data: ReturnDataTypes
    :return: The shuffled data
    :rtype: ReturnDataTypes
    """
    if isinstance(data, list):
        random.shuffle(data)
        return data # random.shuffle is in-place but return=consistent
    elif isinstance(data, dict):
        return shuffle_dict_of_lists(data)
    elif isinstance(data, pd.DataFrame):
        return data.sample(frac=1).reset_index(drop=True)
    raise ValueError("Unexpected data type")

def split_dict(data:dict, keys:list) -> tuple:
    """Splits a dictionary into left/right based on keys. If a string is
    the the key in the data element and in the keys list then it is sent
    to the right record, else the left. This allows therefore an easy to
    use function for splitting left/right records. Note, this works
    regardless of what the values are, float, str, list, etc.

    :param data: The data to split.
    :type data: dict
    :param keys: a list of strings that mark what maps to right
    :type keys: list
    :return: two dicts (left, right)
    :rtype: tuple
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
    keys:list
) -> tuple:
    """Splits data into left/right elements.

    :param data: The data to split
    :type data: Union[list, dict, pd.DataFrame]
    :param keys: a list of strings that mark what maps to right
    :type keys: list
    :return: a left and right of the same type as before
    :rtype: tuple
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
    """Loads the data and performs the requested data wrangling such as
    remapping of keys, format, and shuffle.

    :param data_def: The definition to load based on
    :type data_def: Union[
        InMemoryDataDefinition, FileDataDefinition. FileDefinition, dict]
    :raises ValueError: Invalid data_def.
    :return: The loaded and transformed data
    :rtype: ReturnDataTypes
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
