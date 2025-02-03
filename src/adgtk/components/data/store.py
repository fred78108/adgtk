# pylint: disable=pointless-string-statement
"""The primary purpose of this module is to support the built-in
components. Secondarly the framework itself can use this for processing.
The overall concept is not to fully implement a database but rather
provide a Protocol for any implementation of a wrapper for a database.

By using a consistent wrapper it enables ease of extensibility as well
as code maintenance as it allows for loose coupling across Modules.

Implementations can opt to inherit the DataStore class or implement the
prootocl directly.
"""

# pylint: disable=unused-argument
from __future__ import annotations
from enum import Enum, auto
from typing import (
    Union,
    Protocol,
    runtime_checkable,
    Any,
    Iterable)
from adgtk.components.data.records import PresentableRecord

# ----------------------------------------------------------------------
# Types and Protocols
# ----------------------------------------------------------------------


class SearchOption(Enum):
    """Search capabilities for a data store"""
    NONE = auto()


@runtime_checkable
class RecordStore(Protocol):
    """Provides a consistent way for the built-in objects to interact
    with a data store such as vector database. As most database systems
    differ in their implementations this protocol provides a wrapper
    pattern for any potential use when built-in components are used."""

    # -----------------------------------------------------------------
    # Required methods
    # -----------------------------------------------------------------

    def insert(self, record: PresentableRecord) -> None:
        """Insert a single record

        :param record: _description_
        :type record: PresentableRecord
        """

    def bulk_insert(self, records: Iterable[PresentableRecord]) -> None:
        """insert several records at once

        :param records: _description_
        :type records: Iterable[PresentableRecord]
        """

    def clear_all_records(self) -> None:
        """Clears all records from the system        
        """

    def __len__(self) -> int:
        """The number of the records in the store

        :return: The count of records
        :rtype: int
        """


@runtime_checkable
class CanFindRandomRecord(Protocol):
    """Can find random record"""

    def find_random_record(
        self,
        search_filters: Union[dict, None] = None,
        not_record: Union[PresentableRecord, None] = None,
        **kwargs
    ) -> list:
        """Finds a single record. If a search cannot use a filter
        then at most it should log the issue but not stop as long
        as it can return a record.

        Feature flag: can_get_random_record

        :param near_record: The record to compare against,
            defaults to None
        :type not_record: PresentableRecord
        :param search_filters: the search guidance
        :type search_filters: Union[dict, None]
        :return: a single random record if sufficient records exist
        :rtype: list
        """


@runtime_checkable
class CanRebuildFromDisk(Protocol):
    """Can rebuild from disk"""

    def rebuild_from_disk(self, filename: str) -> bool:
        """Replaces any current records with ones loaded from disk.

        :param filename: The filename with path
        :type filename: str
        :return: Success loading.
        :rtype: bool
        """


@runtime_checkable
class CanSaveToDisk(Protocol):
    """Can use the save_to_disk method w/filename"""

    def save_to_disk(self, filename: str) -> None:
        """Saves to disk all records. For wrapper classes this method
        should export from the database into a common format if the db
        itself does not implement this capability.

        :param filename: The filename with path
        :type filename: str
        """


@runtime_checkable
class CanShuffleRecords(Protocol):
    """Can use the shuffle method to shuffle records"""

    def shuffle(self) -> None:
        """Shuffles the order of records.
        Feature Flag: can_shuffle
        """


@runtime_checkable
class CanExportRecordsToDict(Protocol):
    """Can export records to Dict"""

    def export_to_dict(self, filters: Union[dict, None]) -> dict:
        """Exports the data based on the filters

        Feature Flag: can_export_to_dict

        :param filters: what if any should be used to filter the records
        :type filters: Union[dict, None]
        :return: a dict with requested data
        :rtype: dict
        """


@runtime_checkable
class CanImportRecordsToDict(Protocol):
    """Can import records to Dict"""

    def import_from_dict(
        self,
        data: dict,
        metadata: Union[dict[str, Any], None] = None
    ) -> bool:
        """Imports records from disk.

        Feature Flag: can_import_from_dict

        :param data: _description_
        :type data: dict
        :param metadata: _description_, defaults to None
        :type metadata: dict, optional
        :return: _description_
        :rtype: bool
        """


@runtime_checkable
class CanGetAllRecords(Protocol):
    """Can export records to Dict"""

    def get_all_records(self, as_copy: bool = True) -> list:
        """Exports all records in the store.

        feature flag: can_export_all_records_to_list

        :param as_copy: export as a new object, defaults to True
        :type as_copy: bool, optional
        :return: a list of all records
        :rtype: list
        """


@runtime_checkable
class CanSearchForSimilar(Protocol):
    """Can search for similar"""

    def search_for_similar(
        self,
        near_record: PresentableRecord,
        search_filters: Union[dict, None],
        **kwargs
    ) -> list:
        """Searches for a similar record. If a search cannot use a
        filter then at most it should log the issue but not stop as long
        as it can return one or more records.

        feature Flag: can_search_by_proximity

        :param near_record: The record to compare against
        :type near_record: PresentableRecord
        :param search_filters: the search guidance
        :type search_filters: Union[dict, None]
        :return: a list of one or more records.
        :rtype: list
        """


@runtime_checkable
class CanFindByTerm(Protocol):
    """Can find by term"""

    def find_by_term(self, term: str) -> list:
        """Searches not by record but by term.

        Feature Flag: can_search_by_term

        :param term: the term to search for
        :type term: str
        :return: a list of Records
        :rtype: list
        """
