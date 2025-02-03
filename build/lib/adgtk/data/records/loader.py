"""Record loading functions. The goal is to simplify and standardize
record creation with creation and load function(s).
"""

import csv
from typing import List, Union, Any
from adgtk.factory.component import ObjectFactory
from adgtk.common import ComponentDef
from adgtk.data.presentation import YamlPresentation
from adgtk.data.records import PresentableRecord, DataRecord
from adgtk.data.store.base import RecordStore

# ----------------------------------------------------------------------
# DEFAULTS
# ----------------------------------------------------------------------
DEFAULT_GROUP = "record"
DEFAULT_TYPE = "data"


def create_component_def(
    data: dict,
    overrride_group_label: Union[str, None] = None,
    overrride_type_label: Union[str, None] = None
) -> ComponentDef:
    """Creates a definition to be used with the factory

    :param data: The record data
    :type data: dict
    :param overrride_group_label: If not using the blueprint, what group
        label should be used?, defaults to None
    :type overrride_group_label: Union[str, None], optional
    :param overrride_type_label: If not using the blueprint, what type
        label should be used?, defaults to None
    :type overrride_type_label: Union[str, None], optional
    :return: The definition for the record
    :rtype: ComponentDef
    """
    group_label = "record"
    type_label = "data"
    if overrride_group_label is not None:
        group_label = overrride_group_label
    if overrride_type_label is not None:
        type_label = overrride_type_label

    return {
        "group_label": group_label,
        "type_label": type_label,
        "arguments": {
            "presentation_def": {
                "group_label": "presentation",
                "type_label": "yaml",
                "arguments": {}
            },
            "data": data,
            "use_cached_str": True,
            "metadata": {}
        }
    }


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------

# Consider crafting direct and avoiding a factory creation for each
# record. Future use may benefit from this approach?
def create_record(
    data: dict,
    factory: Union[ObjectFactory, None] = None,
    overrride_group_label: Union[str, None] = None,
    overrride_type_label: Union[str, None] = None
) -> PresentableRecord:
    """Creates a record

    :param factory: The factory for record creation, defaults to None
    :type factory: ObjectFactory
    :param data: The source data
    :type data: dict
    :param overrride_group_label: If not using the blueprint, what group
        label should be used?, defaults to None
    :type overrride_group_label: Union[str, None], optional
    :param overrride_type_label: If not using the blueprint, what type
        label should be used?, defaults to None
    :type overrride_type_label: Union[str, None], optional
    :return: The new record
    :rtype: PresentableRecord
    """

    if factory is None:
        factory = ObjectFactory(journal=None)
        factory.register(YamlPresentation)
        factory.register(DataRecord)

    record_def = create_component_def(
        data=data,
        overrride_group_label=overrride_group_label,
        overrride_type_label=overrride_type_label)
    return factory.create(component_def=record_def)


# """Creates a set of records using data as the source for the records
def create_records(
    data: Union[List[dict], dict],
    factory: Union[ObjectFactory, None] = None,
    datastore: Union[RecordStore, None] = None
) -> List[PresentableRecord]:
    """Creates multiple records and if a datastore is set it also does a
    bulk insert into this store with the new records. With the exception
    of the datastore all other objects when not sent use the default
    setting of DataRecord with YamlPresentation and no metadata.

    :param data: The source data for the records
    :type data: Union[List[dict], dict]
    :param factory: The factory for record creation, defaults to None
    :type factory: ObjectFactory, optional
    :param datastore: The datastore to insert records, defaults to None
    :type datastore: RecordStore, optional
    :return: a list of created records
    :rtype: List[PresentableRecord]
    """

    if factory is None:
        factory = ObjectFactory(journal=None)
        factory.register(YamlPresentation)
        factory.register(DataRecord)

    records = []
    if isinstance(data, dict):
        records.append(create_record(factory=factory, data=data))
    else:
        for entry in data:
            records.append(create_record(factory=factory, data=entry))

    if datastore is not None:
        datastore.bulk_insert(records)

    return records


def load_record_store_from_csv_file(
    file_w_path: str,
    record_store: RecordStore
) -> int:
    """Loads a record store from a CSV file. 

    :param file_w_path: The path w/filename to the CSV file
    :type file_w_path: str
    :param record_store: The record store to insert into
    :type record_store: RecordStore
    :raises ValueError: Not a valid RecordStore
    :return: _the number of records processed
    :rtype: int
    """

    # Safety first!
    if not isinstance(record_store, RecordStore):
        raise ValueError('record_store must be an instance of RecordStore')

    cols: list[Any] = []
    records: list[Any] = []
    prepared_records: list[Any] = []
    
    with open(file_w_path, 'r', encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(cols) == 0:
                cols = row
            else:
                records.append(row)

    # now process/create records
    for record in records:
        new_record = {}
        for i, col in enumerate(cols):
            new_record[col] = record[i]
        prepared_records.append(new_record)

    create_records(prepared_records, datastore=record_store)

    return len(prepared_records)
