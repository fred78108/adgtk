"""Built-in measurements

"""
import json as _json
from .factory import register_to_measurement_factory

__all__ = [
    "dict_schema_match",
    "dict_total_str_length",
    "exact_match",
    "json_valid",
    "key_overlap",
    "list_item_type_consistency",
    "schema_key_depth",
    "string_length",
    "token_f1",
]
# ----------------------------------------------------------------------
# String measurements
# ----------------------------------------------------------------------


@register_to_measurement_factory(tags=["string", "built-in"])
def string_length(a: str) -> int:
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
def dict_total_str_length(a: dict) -> int:
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
                    if isinstance(entry, (str, int, float)):
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
def key_overlap(a: dict, b: dict) -> float:
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


# ----------------------------------------------------------------------
# String comparisons (agentic)
# ----------------------------------------------------------------------


@register_to_measurement_factory(tags=["string", "comparison", "built-in"])
def exact_match(a: str, b: str) -> float:
    """Returns 1.0 if both strings are identical, 0.0 otherwise."""
    return 1.0 if a == b else 0.0


@register_to_measurement_factory(tags=["string", "comparison", "built-in"])
def token_f1(a: str, b: str) -> float:
    """Word-overlap F1 score between two strings (whitespace-tokenized,
    case-insensitive).

    Useful as a lightweight similarity metric when exact match is too strict.
    """
    pred = set(a.lower().split())
    gold = set(b.lower().split())
    if not pred or not gold:
        return 0.0
    overlap = pred & gold
    if not overlap:
        return 0.0
    precision = len(overlap) / len(pred)
    recall = len(overlap) / len(gold)
    return 2 * precision * recall / (precision + recall)


# ----------------------------------------------------------------------
# String measurements (agentic)
# ----------------------------------------------------------------------


@register_to_measurement_factory(tags=["string", "built-in"])
def json_valid(a: str) -> float:
    """Returns 1.0 if the string is valid JSON, 0.0 otherwise."""
    try:
        _json.loads(a)
        return 1.0
    except (_json.JSONDecodeError, TypeError):
        return 0.0


# ----------------------------------------------------------------------
# Dict measurements (agentic)
# ----------------------------------------------------------------------


def _dict_depth(d: dict, current: int = 1) -> int:
    if not isinstance(d, dict) or not d:
        return current
    return max(
        _dict_depth(v, current + 1) if isinstance(v, dict) else current
        for v in d.values()
    )


@register_to_measurement_factory(tags=["dict", "built-in"])
def schema_key_depth(a: dict) -> int:
    """Maximum nesting depth of a dictionary (root = 1)."""
    return _dict_depth(a)


def _key_paths(d: dict, prefix: str = "") -> set:
    paths: set = set()
    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else k
        paths.add(path)
        if isinstance(v, dict):
            paths |= _key_paths(v, path)
    return paths


@register_to_measurement_factory(tags=["dict", "comparison", "built-in"])
def dict_schema_match(a: dict, b: dict) -> float:
    """Recursive key-path overlap between two dicts, ignoring values.

    Returns the ratio of shared key paths to the larger key-path set.
    Useful for checking whether an agent output matches an expected schema.
    """
    if not isinstance(a, dict) or not isinstance(b, dict):
        raise TypeError("Both inputs must be dictionaries")
    paths_a = _key_paths(a)
    paths_b = _key_paths(b)
    if not paths_a and not paths_b:
        return 1.0
    longest = max(len(paths_a), len(paths_b))
    return len(paths_a & paths_b) / longest


# ----------------------------------------------------------------------
# List measurements (agentic)
# ----------------------------------------------------------------------


@register_to_measurement_factory(tags=["list", "built-in"])
def list_item_type_consistency(a: list) -> float:
    """Proportion of items in a list that share the most common type.

    Returns 1.0 for a uniform list, lower values indicate mixed types.
    """
    if not a:
        return 0.0
    counts: dict[str, int] = {}
    for item in a:
        t = type(item).__name__
        counts[t] = counts.get(t, 0) + 1
    return max(counts.values()) / len(a)
