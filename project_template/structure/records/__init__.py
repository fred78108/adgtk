"""data records
"""

from .simple import DataRecord, DataRecordGroup
from .loader import (
    load_record_store_from_csv_file,
    create_record,
    create_records)

register_list = [DataRecord, DataRecordGroup]