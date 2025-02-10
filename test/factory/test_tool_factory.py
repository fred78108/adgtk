"""Tests the tool factory."""

import logging
import os
import pytest
import json
from adgtk.common.structure import (
    ToolDefinition,
    FunctionDefinition,
    ToolFactoryImplementable,
    ParameterDefinition,
    AttributeDefinition)
from adgtk.common.exceptions import DuplicateFactoryRegistration
from adgtk.journals import ExperimentJournal
from adgtk.factory.tool import ToolFactory


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/factory/test_tool_factory.py


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------
DO_CLEANUP = True
CLEAN_BEFORE_RUN = True


# So we can surpress the intended exceptions/logging messages to
# console
logging.disable(logging.CRITICAL)



# ----------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------
class HelloTool:
    """Used for testing the use method w/out arguments"""
    definition = ToolDefinition(
        type="function",
        function=FunctionDefinition(
            name="hello",
            description="Returns a greeting.",
            parameters={}
        )
    )
    def __init__(self):
        self.name = "hello"

    def use(self):
        return "Hello, world!"


class AddingTool:
    """Used for testing the use method with arguments"""
    definition = ToolDefinition(
        type="function",
        function=FunctionDefinition(
            name="hello",
            description="Returns a greeting.",
            parameters={}
        )
    )
    def __init__(self):
        self.name = "hello"

    def use(self, a:int, b:int):
        return f"Hello, world! = {a+b}"


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture(name="tool_factory")
def tool_factory_fixture():
    """Fixture for the ToolFactory class"""
    return ToolFactory()



# ----------------------------------------------------------------------
# Testing
# ----------------------------------------------------------------------

def test_is_valid_tool_factory_implementable():
    """Validates the ToolFactoryImplementable protocol with basic def is
    runtime checkable.
    """
    assert isinstance(HelloTool, ToolFactoryImplementable)

def test_is_valid_tool_factory_implementable_w_args():
    """Validates the ToolFactoryImplementable protocol with args is 
    runtime checkable.
    """
    assert isinstance(AddingTool, ToolFactoryImplementable)

def test_register_tool(tool_factory):
    """Tests the register method of the ToolFactory class.
    """
    tool_factory.register(HelloTool)
    assert "hello" in tool_factory._tools

def test_unregister_tool(tool_factory):
    """Tests the unregister method of the ToolFactory class.
    """
    tool_factory.register(HelloTool)
    tool_factory.unregister("hello")
    assert "hello" not in tool_factory._tools

def test_register_duplicate(tool_factory):
    """Tests the register method of the ToolFactory class with a duplicate.
    """
    tool_factory.register(HelloTool)
    with pytest.raises(DuplicateFactoryRegistration):
        tool_factory.register(HelloTool)

def test_get_tools_json(tool_factory):
    """Tests the get_tools_json method of the ToolFactory class.
    """
    tool_factory.register(HelloTool)
    tools = tool_factory.get_tools_json()
    assert tools[0] == json.dumps(HelloTool.definition)

def test_create_tool(tool_factory):
    """Tests the create method of the ToolFactory class.
    """
    tool_factory.register(HelloTool)
    tool = tool_factory.create("hello")
    assert tool.use() == "Hello, world!"

def test_length(tool_factory):
    """Tests the __len__ method of the ToolFactory class.
    """
    assert len(tool_factory) == 0
    tool_factory.register(HelloTool)
    assert len(tool_factory) == 1

def test_registry_listing(tool_factory):
    """Tests the registry_listing method of the ToolFactory class.
    """
    tool_factory.register(HelloTool)
    assert tool_factory.registry_listing() == ["hello"]

def test_str(tool_factory):
    """Tests the __str__ method of the ToolFactory class.
    """
    tool_factory.register(HelloTool)
    assert str(tool_factory) == "Tool Factory report\n---------------------\n"\
                                "- hello\n---------------------\n"