"""By design exposed data
"""
from .store import (
    SimpleRecordStore,
    DataStoreFeatureFlags,
    RecordStore,
    CanExportRecordsToDict,
    CanFindByTerm,
    CanFindRandomRecord,
    CanGetAllRecords,
    CanImportRecordsToDict,
    CanRebuildFromDisk,
    CanSaveToDisk,
    CanSearchForSimilar,
    CanShuffleRecords,
    ComponentFeatures)
from .presentation import PresentationFormat, YamlPresentation
from .records import (
    load_record_store_from_csv_file,
    PresentableRecord,
    DataRecord,
    SupportsFiltering,
    PresentableGroup,
    DataRecordGroup)

# ----------------------------------------------------------------------
# Built-in object support
# ----------------------------------------------------------------------

# the ScenarioLoader is looking for register_list. update here to add
# more built-in objects to the factory. MVP uses the ScenarioManager to
# invoke but in the future other runners and managers can use this list.

data_register_list = [
    DataRecord,
    YamlPresentation,
    SimpleRecordStore
]
