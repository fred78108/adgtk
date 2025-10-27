"""Built-in measurements

"""
from .factory import register_to_measurement_factory

__all__ = [
    "dict_total_str_length",
    "key_overlap",
    "string_length",    
]
# ----------------------------------------------------------------------
# String measurements
# ----------------------------------------------------------------------

@register_to_measurement_factory(tags=["string", "built-in"])
def string_length(a:str) -> int:
    """Wraps built-in python len.

    Args:
        a (str): The text to measure

    Returns:
        int: The number of characters
    """
    return len(a)


# ----------------------------------------------------------------------
# Dictionary measurements
# ----------------------------------------------------------------------

@register_to_measurement_factory(tags=["dict", "built-in"])
def dict_total_str_length(a:dict) -> int:
    """Iterates through a single dictionary and for every string it
    finds it adds that length to the overall text. if its a number it
    converts to a string in order to measure it as a string. If a value
    is a list or a dict, it also processes
    Args:
        a (dict): The dictionary to measure

    Returns:
        int: the number of characters
    """
    total = 0
    for _, item in a.items():
        try:
            if isinstance(item, str) or isinstance(item, (int, float)):
                total += len(str(item))
            elif isinstance(item, dict):
                total += dict_total_str_length(item)
            elif isinstance(item, list):
                for entry in item:
                    if isinstance(entry, str) or \
                        isinstance(entry, (int, float)):
                        total += len(str(entry))
        except (TypeError, ValueError):
            pass
    return total


# ----------------------------------------------------------------------
# String comparisons
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Dict comparisons
# ----------------------------------------------------------------------
def key_overlap(a:dict, b:dict) -> float:
    """Calculates the key overlap percentage

    Args:
        a (dict): The first entry
        b (dict): The second entry

    Returns:
        float: The ratio of overlap (with longest key set as denominator)
    """
    if not isinstance(a, dict) or not isinstance(b, dict):
        raise TypeError("Both inputs must be dictionaries")
        
    a_keys = set(a.keys())
    b_keys = set(b.keys())
    longest = max(len(a_keys), len(b_keys))    
    if longest == 0:
        return 0
    overlap = a_keys & b_keys
    return len(overlap) / longest