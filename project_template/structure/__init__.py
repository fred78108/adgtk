"""By design exposed data
"""
from .store import SimpleRecordStore
from .presentation import YamlPresentation
from .records import (
    load_record_store_from_csv_file,
    DataRecord,
    create_record,
    create_records,
    DataRecordGroup)

# ----------------------------------------------------------------------
# Built-in object support
# ----------------------------------------------------------------------

# the ScenarioLoader is looking for register_list. update here to add
# more built-in objects to the factory. MVP uses the ScenarioManager to
# invoke but in the future other runners and managers can use this list.

register_list = [
    DataRecord,
    YamlPresentation,
    SimpleRecordStore
]
