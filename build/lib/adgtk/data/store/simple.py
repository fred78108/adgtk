"""Simple Record Stores
"""

from __future__ import annotations
import os
import logging
import random
import pickle
from typing import Iterable, List, Union, Any
from adgtk.data.records import PresentableRecord, DataRecord, PresentableGroup
from adgtk.common import FactoryBlueprint, ArgumentSetting, ArgumentType
from .base import DataStoreFeatureFlags


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/data/test_simple_store.py

# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------

LOG_ON_TYPE_FAILURE = True      # can get noisy. good for dev only.


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------

class NoRecordsFound(Exception):
    """Used to signal unable to complete request"""

    default_msg = "Registration exists. Unregister first."

    def __init__(self, message: str = default_msg):
        super().__init__(message)


class SimpleRecordStore:
    """More a proof of concept Store. Useful for demonstration as well
    as supporting testing.
    """
    # provide the consumer a consistent understanding of capability
    description = "A simple record store that uses a list."
    features = DataStoreFeatureFlags(
        search_options=[],
        can_measure_size_directly=False,
        can_search_by_proximity=False,
        can_iterate=True,
        can_filter_searches=False,
        object_factory=False,
        experiment_journal=False)

    blueprint: FactoryBlueprint = {
        "group_label": "datastore",
        "type_label": "simple",
        "arguments": {
            "filename": ArgumentSetting(
                argument_type=ArgumentType.STRING,
                help_str="The filename and or folder for the datastore",
                default_value="insert/path/here"),
            "load_from_disk_on_launch": ArgumentSetting(
                default_value=False,
                help_str="Load from disk when created?",
                argument_type=ArgumentType.BOOL)
        }
    }

    def __init__(
        self,
        filename: Union[str, None] = None,
        load_from_disk_on_launch: bool = False
    ) -> None:
        super().__init__()
        self._records: list[Union[PresentableRecord, PresentableGroup]] = []
        # self._records = []
        self.idx = 0            # for iteration

        if load_from_disk_on_launch:
            if filename is None:
                msg = "Unable to load on init due to filename missing"
                logging.error(msg)
                raise FileNotFoundError(msg)

            self.rebuild_from_disk(filename=filename)

    def __len__(self) -> int:
        """The number of the records in the store

        :return: The count of records
        :rtype: int
        """
        return len(self._records)

    def __iter__(self) -> SimpleRecordStore:
        """Return self

        :return: return self
        :rtype: SupportRecordStore
        """
        return self

    def __next__(self) -> Union[PresentableRecord, PresentableGroup]:
        """gets next record for an interation
        """
        if self.idx < len(self._records):
            self.idx += 1
            return self._records[(self.idx-1)]
        else:
            # reset for the next time we iterate
            self.idx = 0
            raise StopIteration

    def __getitem__(
        self,
        index: int
    ) -> Union[PresentableRecord, PresentableGroup]:
        """Returns an item at index

        :param index: The index of the item to get
        :type index: int
        :return: The record
        :rtype: PresentableRecord | PresentableGroup
        """
        return self._records[index]

    def insert(
        self,
        record: Union[PresentableRecord, PresentableGroup, dict]
    ) -> None:
        """Insert a single record

        :param record: The record to insert
        :type record: PresentableRecord | PresentableGroup | dict
        """
        if isinstance(record, PresentableRecord):
            self._records.append(record)
        elif isinstance(record, PresentableGroup):
            self._records.append(record)
        else:
            self._records.append(DataRecord(data=record))

    def clear_all_records(self) -> None:
        """Clears all records from the system
        """
        self._records = []

    def bulk_insert(self, records: Iterable[PresentableRecord]) -> None:
        """insert several records at once

        :param records: The records to insert
        :type records: Iterable[PresentableRecord]
        """
        for record in records:
            self.insert(record)

    def shuffle(self) -> None:
        """Shuffles the order of records.
        """
        random.shuffle(self._records)

    def export_to_dict(self, filters: Union[dict, None]) -> dict:
        """Exports the data based on the filters

        :param filters: what if any should be used to filter the records
        :type filters: Union[dict, None]
        :return: a dict with requested data
        :rtype: dict
        """
        data: list[dict] = []

        string_rep = []
        for record in self._records:
            if isinstance(record, PresentableRecord):
                data.append(record.create_copy_of_data())
            elif isinstance(record, PresentableGroup):
                data.append(record.create_copy_of_data())
            elif LOG_ON_TYPE_FAILURE:
                logging.warning("Failed to determine record type")

            string_rep.append(f"{record}")
        return {
            "data": data,
            "string_rep": string_rep
        }

    def import_from_dict(
        self,
        data: dict,
        metadata: Union[dict[str, Any], None] = None
    ) -> bool:
        """_summary_

        :param data: _description_
        :type data: dict
        :param metadata: _description_, defaults to None
        :type metadata: dict, optional
        :return: _description_
        :rtype: bool
        """
        return False

    def rebuild_from_disk(self, filename: str) -> bool:
        """Replaces the current records with those from disk

        :param filename: The filename with path
        :type filename: str
        :return: Success in replacing records
        :rtype: bool
        """
        if not os.path.exists(filename):
            msg = f"Attempted to load a file that does not exist: {filename}"
            logging.error(msg)
            return False

        with open(file=filename, mode="rb") as infile:
            self._records = pickle.load(infile)
            return True

        return False

    def save_to_disk(self, filename: str) -> None:
        """saves the current records to disk

        :param filename: the filename with path
        :type filename: str
        """
        with open(file=filename, mode="wb") as outfile:
            pickle.dump(self._records, outfile)

    def get_all_records(self, as_copy: bool = True) -> list:
        """Exports all records in the store.

        feature flag: can_export_all_records_to_list

        :param as_copy: export as a new object, defaults to True
        :type as_copy: bool, optional
        :return: a list of all records
        :rtype: list
        """
        record: Union[PresentableRecord, PresentableGroup]

        if as_copy:
            new_list = []
            for record in self._records:
                new_list.append(record.copy())

            return new_list

        return self._records

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
        return NotImplemented

    def find_by_term(self, term: str) -> list:
        """Searches not by record but by term.

        Feature Flag: can_search_by_term

        :param term: the term to search for
        :type term: str
        :return: a list of Records
        :rtype: list
        """
        return NotImplemented

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
        if not_record is None and self.__len__() > 0:
            idx = random.randint(0, len(self._records)-1)
            record = self._records[idx]
            return [record]

        if len(self._records) < 3:
            return []
        for _ in range(10):
            choice = random.choice(self._records)
            if str(choice) != str(not_record):
                return [choice]

        return []
