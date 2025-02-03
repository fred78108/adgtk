"""Simple built-in record structure. This is the default Record type
but the framework is not limited to using just this type. If your
research has a need for a different type this is easily replaceable.

This record type by design is using an Object Factory for creation of
each instance. The trade-off in increased compute time is only at
creation of a record and provides an easy method for allowing the
creation of records and record definitions are part of a larger
blueprint. i.e. user ease and flexiblity.
"""

__version__ = "0.1.1"


import copy
import logging
from typing import Union, Any, List
from adgtk.common import (
    FactoryBlueprint,
    ArgumentSetting,
    ArgumentType,
    ComponentDef)
from adgtk.factory.component import ObjectFactory
from adgtk.factory.base import InvalidBlueprint
from adgtk.components.data import PresentationFormat, PresentableRecord, PresentableGroup
from structure.presentation.simple import YamlPresentation


# ---------------------------------------------------------------------
# Single
# ---------------------------------------------------------------------


class DataRecord:
    """Provides a consistent internal data structure for a record. It
    uses a modular plugin for presentation."""

    description = "Basic Data Record"
    blueprint: FactoryBlueprint = {
        "group_label": "record",
        "type_label": "data",
        "arguments": {
            "presentation_def": ArgumentSetting(
                help_str="The presentation blueprint",
                argument_type=ArgumentType.BLUEPRINT,
                default_value="presentation"),
            "data": ArgumentSetting(
                help_str="The data to represent",
                default_value={},
                argument_type=ArgumentType.DICT),
            "use_cached_str": ArgumentSetting(
                help_str="Use a cached string or generate every time?",
                default_value=True,
                argument_type=ArgumentType.BOOL),
            "metadata": ArgumentSetting(
                help_str="The metadata of the record",
                default_value={},
                argument_type=ArgumentType.DICT),
        }
    }

    def __init__(
        self,
        data: dict[str, Any],
        factory: Union[ObjectFactory, None] = None,
        presentation_def: Union[ComponentDef, None] = None,
        use_cached_str: bool = True,
        metadata: Union[dict[str, Any], None] = None
    ):
        """A Data record is a base Class for the internal data storage.

        :param factory: The factory if needed for init, defaults to None
        :type factory: ObjectFactory
        :param presentation_def: presentation blueprint,
            defaults to None
        :type presentation_def: PresentationFormat
        :param data: the data for the record
        :type data: dict
        :param use_cached_str: generate str once, defaults to True
        :type use_cached_str: bool, optional
        :param metadata: metadata for the record, defaults to None
        :raises InvalidBlueprint: Presentation_blueprint defined w/out factory

        """
        super().__init__()
        self.use_cached_str = use_cached_str
        if presentation_def is not None and factory is not None:
            self.presentation: Union[
                PresentationFormat,
                YamlPresentation] = factory.create(presentation_def)
        elif presentation_def is not None and factory is None:
            msg = "Presentation_blueprint defined without factory"
            raise InvalidBlueprint(msg)
        else:
            # default to Yaml
            self.presentation = YamlPresentation()

        self.data = data
        if use_cached_str:
            self._string_rep_cached = self.presentation.present(self.data)

        if metadata is None:
            self.metadata = {}
        else:
            self.metadata = metadata

    def __str__(self) -> str:
        """Presents the string representation using the cached

        :return: String representation of the data
        :rtype: str
        """
        if self.use_cached_str:
            return self._string_rep_cached

        return self.presentation.present(self.data)

    def create_copy_of_data(self) -> dict[str, Any]:
        """Creates a copy of the internal data for this record. this
        protects against accidental updating of the data if needed to
        manipulate the values or keys.

        :return: a deep copy of the data
        :rtype: dict
        """
        new_data = {}
        if not isinstance(self.data, dict):
            # in the event self.data is overwritten to a non-dict type.
            logging.error(
                f"record corruption. unexpected data type {type(self.data)}")
            return new_data
        
        for key, value in self.data.items():
            new_data[key] = copy.deepcopy(value)

        return new_data

    def get_data_keys(self) -> List[str]:
        """Lists the keys for a record's internal data.

        :return: a list of keys
        :rtype: list
        """

        # to protect against caller modifing the list.
        tmp_data = self.create_copy_of_data()
        return list(tmp_data.keys())

    def copy(self):
        """provides a mapping to __copy__ method. Main benefit is
        readability. no other processing occurs in this method.

        :return: a copy of the record
        :rtype: DataRecord
        """
        return self.__copy__()

    def __copy__(self):
        """copies the record. Maps to __deepcopy__ and performs no other
        operation.

        :return: a copy of the record
        :rtype: DataRecord
        """
        return self.__deepcopy__(memo=None)

    def __deepcopy__(self, memo: Any):
        """copies the record

        :return: a copy of the record
        :rtype: DataRecord
        """
        cls = self.__class__
        new_record = cls.__new__(cls)
        for key, value in self.__dict__.items():
            setattr(new_record, key, copy.deepcopy(value))
        return new_record

# ---------------------------------------------------------------------
# grouping of records
# ---------------------------------------------------------------------
# TODO: add testing of the copy and interactions


class DataRecordGroup:
    """One or more PresentableRecords that act together."""

    description = "Group of data records"
    blueprint: FactoryBlueprint = {
        "group_label": "record-group",
        "type_label": "data-record-group",
        "arguments": {
            "data_records": ArgumentSetting(
                argument_type=ArgumentType.LIST,
                help_str="The records to create with",
                default_value=[])
        }
    }

    def __init__(
        self,
        records: List[PresentableRecord | None],
        metadata: Union[dict, None] = None
    ) -> None:
        self.records = []
        self.metadata = {}

        # and do we override the default?
        if metadata is not None:
            self.metadata = metadata
        if records is not None:
            self.records = records

    def __len__(self) -> int:
        """The number of records in the group"""
        return len(self.records)

    def __getitem__(self, index: Union[int, slice]):
        """Get a single entry or a slice

        :param index: the record(s) to return
        :type index: Union[int, slice]
        """
        # passing through to the records since using a List
        return self.records[index]

    def copy(self):
        """provides a mapping to __copy__ method. Main benefit is
        readability. no other processing occurs in this method.

        :return: a copy of the record group
        :rtype: DataRecordGroup
        """
        return self.__copy__()

    def __copy__(self):
        """copies the record group. Maps to __deepcopy__ and performs no other
        operation.

        :return: a copy of the record
        :rtype: DataRecordGroup
        """
        return self.__deepcopy__(memo=None)

    def __deepcopy__(self, memo: Any):
        """copies the record

        :return: a copy of the record
        :rtype: DataRecordGroup
        """
        cls = self.__class__
        new_record = cls.__new__(cls)
        for key, value in self.__dict__.items():
            setattr(new_record, key, copy.deepcopy(value))
        return new_record

    def create_copy_of_data(self) -> dict[str, Any]:
        """Creates a copy of the internal data for this record. this
        protects against accidental updating of the data if needed to
        manipulate the values or keys.

        :return: a deep copy of the data
        :rtype: dict
        """
        new_data: dict[str, list[dict]] = {
            "records": []
        }

        for record in self.records:
            if isinstance(record, PresentableRecord):
                new_data["records"].append(record.create_copy_of_data())
            elif isinstance(record, PresentableGroup):
                new_data["records"].append(record.create_copy_of_data())
        return new_data

    def add_record(self, record: PresentableRecord) -> None:
        """Adds a record to the group

        :param record: _description_
        :type record: PresentableRecord
        """
        self.records.append(record)
