"""Base for Records.
"""

from typing import (
    Protocol,
    Union,
    runtime_checkable,
    Iterable,
    Any)
from adgtk.common import FactoryBlueprint

# ----------------------------------------------------------------------
# Types and Protocols
# ----------------------------------------------------------------------


@runtime_checkable
class PresentableRecord(Protocol):
    """A record that is presentable"""

    def __str__(self) -> str:
        """Generates a string representation

        :return: A string representation of the Record 
        :rtype: str
        """

    def create_copy_of_data(self) -> dict:
        """Creates a copy of the internal data for this record. this
        protects against accidental updating of the data if needed to
        manipulate the values or keys.

        :return: a deep copy of the data
        :rtype: dict
        """

    def copy(self):
        """provides a mapping to __copy__ method. Main benefit is
        readability. no other processing occurs in this method.

        :return: a copy of the record
        :rtype: DataRecord
        """


@runtime_checkable
class SupportsFiltering(Protocol):
    """Provides a consistent definition of a filter for use across modules."""
    blueprint: FactoryBlueprint

    def is_included(self, a: Any) -> bool:
        """Filters a single objec. Intended to use as part of filtering
        an iterable object such a list or data store. Implementations
        can opt to use this when they need to define via Factory

        :param record: _description_
        :type record: Any
        :return: _description_
        :rtype: bool
        """


@runtime_checkable
class PresentableGroup(Protocol):
    """One or more PresentableRecords that act together."""
    blueprint: FactoryBlueprint
    records: Iterable[PresentableRecord]
    metadata: dict

    def __len__(self) -> int:
        """The number of records in the group"""

    def __getitem__(self, index: Union[int, slice]):
        """Get an item or a slice

        :param index: The index or slice
        :type index: Union[int, slice]
        """

    def add_record(self, record: PresentableRecord) -> None:
        """Adds a record to the group

        :param record: _description_
        :type record: PresentableRecord
        """

    def create_copy_of_data(self) -> dict:
        """Creates a copy of the internal data for this record. this
        protects against accidental updating of the data if needed to
        manipulate the values or keys.

        :return: a deep copy of the data
        :rtype: dict
        """

    def copy(self):
        """provides a mapping to __copy__ method. Main benefit is
        readability. no other processing occurs in this method.

        :return: a copy of the record group
        :rtype: DataRecordGroup
        """
