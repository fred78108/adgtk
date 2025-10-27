"""Functions for the factory"""

# ----------------------------------------------------------------------
# Demo functions
# ----------------------------------------------------------------------

def point_five_function(s1:str, s2:str) -> float:
    """An extremely basic function for validation of factory. Primary
    used for demonstration and testing. Limited to no utility.
    
    Returns 1 if both strings are the same, else .5

    :param s1: first string
    :type s1: str
    :param s2: second string
    :type s2: str
    :return: either 1 or .5
    :rtype: float
    """
    if s1 == s2:
        return 1
    return 0.5

def point_two_function(s1:str, s2:str) -> float:
    """An extremely basic function for validation of factory. Primary
    used for demonstration and testing. Limited to no utility.
    
    Returns 1 if both strings are the same, else .2

    :param s1: first string
    :type s1: str
    :param s2: second string
    :type s2: str
    :return: either 1 or .2
    :rtype: float
    """
    if s1 == s2:
        return 1
    return 0.2