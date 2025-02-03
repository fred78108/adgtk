"""
Used for dealing with formatting and parsing of strings.
"""

import datetime
import yaml
import re

# py -m pytest -s test/utils/test_formatting.py


# ----------------------------------------------------------------------
# Module Configurations
# ----------------------------------------------------------------------
DEBUG = False


# ----------------------------------------------------------------------
# Exceptions
# ----------------------------------------------------------------------

class UnableToProcess(Exception):
    """Used for failing to process and wanting to degrade gracefully"""

    default_msg = "Unable to process."

    def __init__(self, message: str = default_msg):
        super().__init__(message)



# ----------------------------------------------------------------------
# Common data representations
# ----------------------------------------------------------------------


def get_timestamp_now(include_time: bool = True) -> str:
    """Generates a string with a timestamp. The goal is to have a
    consistent data and date/time format across the different reports,
    etc.

    Args:
        include_time (bool, optional): Include time?.
            Defaults to True.

    Returns:
        str: A timestamp string formatted for reports, etc.
    """
    now = datetime.datetime.now()
    if include_time:
        return now.strftime("%d/%m/%y at %H:%M:%S")
    else:
        return now.strftime("%d/%m/%y")

# ---------------------------------------------------------------------
# YAML
# ---------------------------------------------------------------------

def llm_output_to_dict(text:str) -> dict:
    """Assumes a single entry

    :param text: The text to process
    :type text: str
    :raises UnableToProcess: Unable to convert into a dict
    :return: The text transformed into a dict
    :rtype: dict
    """
    start_idx = 0
    last_idx = 0
    if "{" in text:
        start_idx = text.index("{")
    if "}" in text:
        last_idx = text.rfind("}")
    if last_idx > 0:
        candidate = text[start_idx:last_idx+1]
        try:
            # attempt to process
            data = yaml.safe_load(candidate)
            return data
        except Exception as e:
            raise UnableToProcess
    # when all else fails, raise Exception
    raise UnableToProcess

def llm_output_to_list(text:str) -> list:
    """Considers more than one entry and attempt to locate and process
    the individual records.

    :param text: The text to process
    :type text: str
    :return: The text transformed into a dict
    :rtype: dict
    """
    data_list = []
    
    # going to attempt splitting
    start_indices_object = re.finditer(pattern='{', string=text)
    start_indices = [index.start() for index in start_indices_object]
    end_indices_object = re.finditer(pattern='}', string=text)
    end_indices = [index.start() for index in end_indices_object]

    for start_idx, end_idx in zip(start_indices, end_indices):
        if start_idx < end_idx:
            sample = text[start_idx:end_idx+1]
            try: 
                data = llm_output_to_dict(sample)
                # if we make it here, then its a single record
                data_list.append(data)
            except UnableToProcess:
                pass

    return data_list