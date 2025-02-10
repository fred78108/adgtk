"""Processing functions for impairment of data."""

import random
from typing import Union

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
EMPTY_PLACEHOLDER = "EMPTY_RECORD"
REPLACE_EMPTY_STRING_IN_DICT_WITH_PLACEHOLDER = True
RANDOM_CAN_SELECT_EMPTY = False

# ----------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------

def get_random_key(
    data:dict,
    can_select_empty:bool=False,
    empty_placeholder:str="EMPTY_RECORD"
) -> Union[str, None]:
    """Returns a random key based on a dict. If it cannot then it will
    return None.

    :param data: The source data
    :type data: dict
    :param can_select_empty: ok to select an empty?, defaults to False
    :type can_select_empty: bool, optional
    :param empty_placeholder: empty data string, defaults to "EMPTY_RECORD"
    :type empty_placeholder: str, optional
    :return: A random key from the dict
    :rtype: str|None    
    """
    
    keys = list(data.keys())
    random.shuffle(keys)
    if can_select_empty:
        return random.choice(keys)

    # additional protections needed. Can return None now.
    for key in keys:
        if data[key] != empty_placeholder:
            return key
    # there is not a key that meets the criteria
    return None


def already_has_dropped(
    data:dict,
    empty_placeholder:str="EMPTY_RECORD"
) -> bool:
    """Checks to see if the dict already has a key is empty. True if the
    values contain the empty_placeholder.

    :param data: The source data
    :type data: dict
    :param empty_placeholder: empty data string, defaults to "EMPTY_RECORD"
    :type empty_placeholder: str, optional
    :return: T: that the dict has a key thats value is empty
    :rtype: bool
    """
    
    for _, value in data.items():
        if value == empty_placeholder:
            return True

    return False

def get_longest_string(
    data:dict,
    empty_placeholder:str="EMPTY_RECORD"
) -> Union[str, None]:
    """This function compares the different values and returns the key
    of the longest value.

    :param data: The source data
    :type data: dict
    :return: Key of the longest string
    :rtype: str|None
    """
    
    longest = None
    length = 0

    for key, item in data.items():
        if isinstance(item, str):
            if len(item) > length and item != empty_placeholder:
                longest = key
                length = len(item)

    return longest

# ----------------------------------------------------------------------
# Impairment helpers
# ----------------------------------------------------------------------


def drop_random_value(
    data:dict,
    can_select_empty:bool=False,
    empty_placeholder:str="EMPTY_RECORD"
    ) -> dict:
    """Impairs a dict by dropping a random value from the dict. If the
    data already has a dropped value, then it will not drop another.

    :param data: The source data
    :type data: dict
    :param can_select_empty: ok to select an empty?, defaults to False
    :type can_select_empty: bool, optional
    :param empty_placeholder: empty data string, defaults to "EMPTY_RECORD"
    :type empty_placeholder: str, optional
    :return: The updated dict
    :rtype: dict
    """
    
    if already_has_dropped(data=data, empty_placeholder=empty_placeholder):
        return data

    key = get_random_key(
        data=data, 
        can_select_empty=can_select_empty,
        empty_placeholder=empty_placeholder)
    
    if key is not None:
        data[key] = empty_placeholder        

    return data
