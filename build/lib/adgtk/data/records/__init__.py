"""data records
"""

from .base import PresentableRecord, SupportsFiltering, PresentableGroup
from .simple import DataRecord, DataRecordGroup
from .loader import (
    load_record_store_from_csv_file,
    create_record,
    create_records)
