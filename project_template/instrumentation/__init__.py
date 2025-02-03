from .comparisons  import (
    WordOverlap,
    DataKeyOverlap,
    DataValueOverlap,
    GroupDataKeyOverlap,
    GroupDataValueOverlap)

from .measurements import (
    MeasureItemCount,
    MeasureKeyLength,
    MeasureTextLength,
    MeasureUnusedKeys,
    MeasureWordCount)

register_list = [
    WordOverlap,
    DataKeyOverlap,
    DataValueOverlap,
    GroupDataKeyOverlap,
    GroupDataValueOverlap,
    MeasureItemCount,
    MeasureKeyLength,
    MeasureTextLength,
    MeasureUnusedKeys,
    MeasureWordCount
]