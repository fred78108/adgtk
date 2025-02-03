"""Processing. Think of Processing Classes as an Agent without a policy.
They will load and transform data based on their needs. For example,
taking a CSV file and loading into a datastore then saving the store to
disk. Another could be taking from one store to another.
"""


import os
from typing import Union, List
import logging
import csv
from adgtk.common import (
    FactoryBlueprint,
    ArgumentSetting,
    ArgumentType)
from adgtk.factory import ObjectFactory
from adgtk.journals import ExperimentJournal
from adgtk.components.data import RecordStore
from adgtk.common.exceptions import InvalidScenarioState
from structure.records import create_records
# py -m pytest test/processing/test_csv.py

# ----------------------------------------------------------------------
#  Flags
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Processors
# ----------------------------------------------------------------------

class CsvToDataStoreProcessor:
    """Loads a CSV file into a data store."""

    description = "creates a datastore and Loads a CSV file into it."

    blueprint: FactoryBlueprint = {
        "group_label": "processing",
        "type_label": "csv-to-datastore",
        "arguments": {
            "source_file": ArgumentSetting(
                help_str="your file with path goes here",
                default_value="data/example.csv",
                argument_type=ArgumentType.STRING),
            "exclude_columns": ArgumentSetting(
                argument_type=ArgumentType.LIST,
                help_str="Enter a column name if any to exclude",
                list_arg_type=ArgumentType.STRING),
            "include_columns": ArgumentSetting(
                argument_type=ArgumentType.LIST,
                help_str="Enter a column if any to include",
                list_arg_type=ArgumentType.STRING),
            "clean_whitespace": ArgumentSetting(
                default_value=True,
                help_str="Clean the white space on the data",
                argument_type=ArgumentType.BOOL)
        }
    }

    def __init__(
        self,
        factory: ObjectFactory,
        exclude_columns: Union[List[str], None] = None,
        include_columns: Union[List[str], None] = None,
        clean_whitespace: bool = True,
        source_file: Union[str, None] = None,
        datastore: Union[RecordStore, None] = None,
        journal: Union[ExperimentJournal, None] = None
    ) -> None:

        self.source_file = source_file
        self.datastore = datastore
        self.factory = factory
        self.journal = journal
        self.include_columns = include_columns
        self.clean_whitespace = clean_whitespace
        if exclude_columns is None:
            self.exclude_columns = []
        else:
            self.exclude_columns = exclude_columns

        self._check_filters()

    def _check_filters(self) -> None:
        """Does validation of the filter lists to ensure a column is not
        listed as both included and excluded.
        """

        if self.clean_whitespace and self.include_columns is not None:
            for a in self.include_columns:
                if a.startswith(" "):
                    msg = f"Filter mis-match. clean whitespace is set but {a}"\
                        " has leading whitespace. This process does not clean"\
                        " the filters."
                    logging.warning(msg)
                if a.endswith(" "):
                    msg = f"Filter mis-match. clean whitespace is set but {a}"\
                        " has trailing whitespace. This process does not "\
                        "clean the filters."
                    logging.warning(msg)

        if self.clean_whitespace:
            for a in self.exclude_columns:
                if a.startswith(" "):
                    msg = f"Filter mis-match. clean whitespace is set but {a}"\
                        " has leading whitespace. This process does not clean"\
                        " the filters."
                    logging.warning(msg)
                if a.endswith(" "):
                    msg = f"Filter mis-match. clean whitespace is set but {a}"\
                        " has trailing whitespace. This process does not "\
                        "clean the filters."
                    logging.warning(msg)

        # check one
        if self.include_columns is not None:
            for a in self.include_columns:
                if a in self.exclude_columns:
                    err_msg = f"{a} defined in include and exclude filters. "\
                        f"include_column overrides exclude_column for {a}."
                    logging.warning(err_msg)

    def process(self) -> None:
        """Executes the process of loading a CSV file, filtering the
        data (if asked) and then inserting into a datastore.
        """

        if self.source_file is None:
            msg = "Failed to set source file prior to a process request"
            logging.error(msg)
            raise InvalidScenarioState(msg)

        if self.datastore is None:
            msg = "Failed to set the datastore prior to a process request"
            logging.error(msg)
            raise InvalidScenarioState(msg)

        columns: List[str] = []

        if not os.path.exists(self.source_file):
            msg = f"Unable to load {self.source_file}"
            logging.error(msg)
            raise FileNotFoundError

        imported_data: List[dict] = []
        with open(self.source_file, mode="r", encoding="utf-8") as infile:
            csv_reader = csv.reader(infile)

            for row in csv_reader:
                # we are on the first row when len == 0
                if len(columns) == 0:
                    columns = row
                else:
                    data = {}
                    for col, entry in zip(columns, row):
                        if self.clean_whitespace:
                            col = col.strip()
                            if isinstance(entry, str):
                                entry = entry.strip()

                        if self.include_columns is not None:
                            if col in self.include_columns:
                                data[col] = entry
                        elif col not in self.exclude_columns:
                            data[col] = entry

                    imported_data.append(data)

        create_records(

            data=imported_data,
            factory=self.factory,
            datastore=self.datastore)

        msg = f"Loaded {len(imported_data)} records into datastore"
        logging.info(msg)
