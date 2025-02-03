"""Processing components"""
# from .base import RecordFactoryEntry
from .csv import CsvToDataStoreProcessor
from .processing import Processor

register_list = [CsvToDataStoreProcessor]