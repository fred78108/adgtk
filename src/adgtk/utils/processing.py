"""Common, often used patterns. 
"""


from typing import Any, Iterator, Union


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/folder/.py


def get_sample_from_iterable(data: Iterator, default: Any = None) -> Any:
    """Gets a sample from an iterable.

    :param data: The iterable data
    :type data: Iterable
    :param default: if unable to get Next, defaults to None
    :type default: Any, optional
    :return: The first item
    :rtype: Any
    """
    return next(data, default)


def get_pair_from_iterable(data: Iterator, default: Any = None) -> tuple:
    """Gets first two entries

    :param data: The iterable data
    :type data: Iterable
    :param default: if unable to get Next, defaults to None
    :type default: Any, optional
    :return: The first and second item
    :rtype: Any
    """
    a = next(data, default)
    b = next(data, default)
    return (a, b)


def string_to_bool(source: Union[str, bool]) -> bool:
    """Converts a string into a boolean. also considers when a bool
    is passed. this keeps the invoking code cleaner.

    :param source: the source string
    :type source: Union[str, bool]
    :raises ValueError: Unable to transform
    :return: the boolean value T/F.
    :rtype: bool
    """
    if isinstance(source, bool):
        return source

    source = source.upper()
    if source == "TRUE":
        return True
    elif source == "FALSE":
        return False
    elif source == "T":
        return True
    elif source == "F":
        return False
    else:
        raise ValueError
