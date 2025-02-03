"""Utilities to ease record processing. 
"""

import logging
from typing import Literal, Any
from typing import (
    Literal,
    Final,
    Any,
    Sequence)
from adgtk.components.data import (
    RecordStore,
    CanFindRandomRecord,
    CanGetAllRecords,
    PresentableRecord,
    PresentableGroup)
from adgtk.instrumentation.base import (
    RecordAs,
    MeasInputType,
    SupportsMeasDef,
    InvalidMeasurementConfiguration)

# ----------------------------------------------------------------------
# Module Constants
# ----------------------------------------------------------------------

DEFAULT_MAX_IN_GROUP: Final[int] = 1000000  # for min/max checks if None


def convert_record_as(
    record_as: Literal["sum", "avg", "latest", "raw"]
) -> RecordAs:
    """Converts the string into an Enum

    :param record_as: the text mapping to RecordAs
    :type record_as: Literal[&quot;sum&quot;, &quot;avg&quot;, &quot;latest&quot;, &quot;raw&quot;]
    :raises InvalidMeasurementConfiguration: Unknown record_as value
    :return: The converted value
    :rtype: RecordAs
    """
    if record_as == "sum":
        return RecordAs.SUM
    elif record_as == "avg":
        return RecordAs.AVG
    elif record_as == "latest":
        return RecordAs.LATEST
    elif record_as == "raw":
        return RecordAs.RAW
    else:
        msg = f"Unknown record_as: {record_as} setting."
        raise InvalidMeasurementConfiguration(msg)


def process_as(data: Any) -> tuple:
    """Seeks to provide data

    :param data: The data to inspect
    :type data: Any
    :return: a tuple (process data, if iterable the items as)
    :rtype: Tuple[MeasInputType]
    """
    if isinstance(data, PresentableGroup):
        # A presentable group by design only has presentable records
        return (
            MeasInputType.PRESENTABLE_GROUP,
            MeasInputType.PRESENTABLE_RECORD)
    elif isinstance(data, PresentableRecord):
        return (MeasInputType.PRESENTABLE_RECORD,
                MeasInputType.NOOP)
    elif isinstance(data, str):
        return (MeasInputType.STRING, MeasInputType.NOOP)
    elif isinstance(data, dict):
        return (MeasInputType.DICTIONARY, MeasInputType.NOOP)
    elif isinstance(data, RecordStore):
        a = MeasInputType.UNKNOWN
        if len(data) == 0:
            return (MeasInputType.EMPTY, None)
        # get a sample
        elif isinstance(data, CanFindRandomRecord):
            random_record = data.find_random_record()
        elif isinstance(data, CanGetAllRecords):
            # lot slower, but better than unable to match
            random_record = data.get_all_records()
        else:
            logging.error("Unable to determine protocol for process_as")

        a, _ = process_as(random_record[0])
        return (MeasInputType.RECORD_STORE, a)

    elif isinstance(data, list):
        if len(data) == 0:
            return (MeasInputType.EMPTY, MeasInputType.NOOP)

        a, _ = process_as(data[0])

        if len(data) == 2:
            return (MeasInputType.PAIR_AS_LIST, a)

        return (MeasInputType.LIST, a)

    elif isinstance(data, Sequence):
        if len(data) == 0:
            return (MeasInputType.EMPTY, MeasInputType.NOOP)
        sample = data[0]
        a, _ = process_as(sample)
        if a is not MeasInputType.UNKNOWN:
            return (MeasInputType.ITERABLE, a)

        return (MeasInputType.ITERABLE, MeasInputType.NOOP)

    return (MeasInputType.UNKNOWN, MeasInputType.UNKNOWN)


def min_max_group_check(meas: SupportsMeasDef, data: PresentableGroup) -> bool:
    """checking for the director the different combinations makes the
    method is_measurable_with a bit too long. breaking out this code
    into a function for readability. This function validates whether
    the data and measurement requirements are met.

    :param meas: The measurement to check
    :type meas: SupportsMeasDef
    :type data: PresentableGroup
    :return: True if valid measurement for this group, else False
    :rtype: bool
    """
    min_val = meas.features.count_min
    max_val = meas.features.count_max

    if min_val is None:
        min_val = 0
    if max_val is None:
        max_val = DEFAULT_MAX_IN_GROUP

    record_count = len(data)

    if min_val <= record_count <= max_val:
        return True

    return False
