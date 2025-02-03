"""Summary goes here.

Versions:
v 0.1
- mvp

References:
-

TODO:

1.0

Defects:

1.0

Test
python -m unittest tests.
"""


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------


def camel_case_generation(label: str) -> str:
    """Creates a CamelCase from snake_case.

    Args:
        label (str): the string in snake case

    Returns:
        str: label converted to CamelCase
    """
    label = label.lower()
    words = label.split("_")
    updated = []
    for word in words:
        updated.append(word.title())

    return "".join(updated)
