"""Functions for the factory"""

# ----------------------------------------------------------------------
# Demo functions
# ----------------------------------------------------------------------


def point_five_function(s1: str, s2: str) -> float:
    """An extremely basic function for validation of factory.

    Primarily used for demonstration and testing. Limited to no utility.
    Returns 1 if both strings are the same, else 0.5.

    Args:
        s1 (str): First string.
        s2 (str): Second string.

    Returns:
        float: Either 1.0 or 0.5.
    """
    if s1 == s2:
        return 1
    return 0.5


def point_two_function(s1: str, s2: str) -> float:
    """An extremely basic function for validation of factory.

    Primarily used for demonstration and testing. Limited to no utility.
    Returns 1 if both strings are the same, else 0.2.

    Args:
        s1 (str): First string.
        s2 (str): Second string.

    Returns:
        float: Either 1.0 or 0.2.
    """
    if s1 == s2:
        return 1
    return 0.2
