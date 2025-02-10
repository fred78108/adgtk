"""Tests the impairment engine"""

import pytest
from typing import Union
from adgtk.impairment import ImpairmentEngine, Impairment
from adgtk.components import PresentableGroup, PresentableRecord
from adgtk.common import (
    DuplicateFactoryRegistration,
    InvalidConfigException,
    FactoryBlueprint)    
from adgtk.impairment.processing import drop_random_value


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/impairment/test_engine.py

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture(name="impairment_engine")
def fixture_impairment_engine():
    """Fixture for the impairment engine"""
    return ImpairmentEngine()





# ----------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------

class MyRecordType:
    """My Record Type"""

    def __init__(self):
        self.data = {
            "key": "value"
        }
    def __str__(self):
        return str(self.data)
    
    def create_copy_of_data(self) -> dict:
        return self.data.copy()

    def copy(self):
        return MyRecordType()

class MyGroupType:
    """My Group Type"""
    blueprint: FactoryBlueprint = {
        "group_label": "my-group-type",
        "type_label": "data",
    }
    def __init__(self):
        self.metadata = {}
        self.records = [
            MyRecordType(),
            MyRecordType()
        ]
    def __str__(self):
        return str(self.data)
    
    def copy(self):
        return MyGroupType()

# instances of the data types    
mock_record_one = MyRecordType()
group_one = MyGroupType()

# ----------------------------------------------------------------------
# Mock Impairments
# ----------------------------------------------------------------------

class MockImpairmentOne(Impairment):
    """Mock Impairment One"""

    impairs = ["dict"]
    label = "mock-impairment-one"

    def impair(
        self,
        data: Union[PresentableGroup, PresentableRecord, dict, str],
        key: str = None,
        idx: int = None
    ) -> dict:
        """Mock impairment.

        :param data: The data to impair
        :type data: PresentableGroup
        :param key: If a specific key is requested to impair, defaults to None
        :type key: str, optional
        :param idx: If a group then the record to impair, defaults to None
        :type idx: int, optional
        :return: the data impaired
        :rtype: dict
        """
        if not isinstance(data, dict):
            raise InvalidConfigException("Data must be a dict")
        
        return drop_random_value(data=data)
    
class NotValidImpairment:
    """Not a valid impairment"""

    impairs = ["dict"]
    label = "not-valid-impairment"

    # does not implement the protocol correctly.
    def impair_data(
        self,
        data: Union[PresentableGroup, PresentableRecord, dict, str],
        key: str = None,
        idx: int = None
    ) -> dict:
        """Mock impairment.

        :param data: The data to impair
        :type data: PresentableGroup
        :param key: If a specific key is requested to impair, defaults to None
        :type key: str, optional
        :param idx: If a group then the record to impair, defaults to None
        :type idx: int, optional
        :return: the data impaired
        :rtype: dict
        """
        return drop_random_value(data=data)
    

def test_impairment_engine_add_impairment(impairment_engine):
    """Tests adding an impairment to the engine"""
    impairment_engine.add_impairment(MockImpairmentOne())
    assert len(impairment_engine) == 1

def test_impairment_engine_add_impairment_duplicate(impairment_engine):
    """Tests adding an impairment to the engine"""
    impairment_engine.add_impairment(MockImpairmentOne())
    with pytest.raises(DuplicateFactoryRegistration):
        impairment_engine.add_impairment(MockImpairmentOne())
    assert len(impairment_engine) == 1

def test_impairment_engine_add_impairment_invalid(impairment_engine):
    """Tests adding an impairment to the engine"""
    with pytest.raises(ValueError):
        impairment_engine.add_impairment(NotValidImpairment())
    assert len(impairment_engine) == 0

def test_impairment_engine_impair(impairment_engine):
    """Tests impairing data"""
    impairment_engine.add_impairment(MockImpairmentOne())
    data = {
        "key": "value",
        "key2": "value2"
        }
    impaired_data = impairment_engine.impair("mock-impairment-one", data)
    assert data != impaired_data

def test_check_type_dict(impairment_engine):
    """Tests impairing data with dict"""
    impairment_engine._check_type(impairs="dict", data={})

def test_check_type_str(impairment_engine):
    """Tests impairing data with str"""
    impairment_engine._check_type(impairs="str", data="")

def test_check_type_presentable_group(impairment_engine):
    """Tests impairing data with PresentableGroup"""
    impairment_engine._check_type(impairs="PresentableGroup", data=group_one)

def test_check_type_presentable_record(impairment_engine):
    """Tests impairing data with PresentableRecord"""
    impairment_engine._check_type(impairs="PresentableRecord", data=mock_record_one)
