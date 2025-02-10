"""Similar to the Component factory, the Tool factory is responsible for
creating tools that can be used by Agents. The factory is designed to
make it easier to create new tools and to manage the tools that are
available to the Agent.
"""
from __future__ import annotations
import json
from typing import Any, Union, List
from adgtk.journals import ExperimentJournal
from adgtk.common import DuplicateFactoryRegistration, ToolFactoryImplementable

# py -m pytest -s test/factory/test_tool_factory.py

class ToolFactory:
    """The ToolFactory class is responsible for creating tools that can
    be used by Agents. The factory is designed to make it easier to
    create new tools and to manage the tools that are available to
    the Agent.
    """

    def __init__(
        self,
        journal: Union[ExperimentJournal, None] = None,
        factory_name: str = "Tool Factory"
    ) -> None:
        self.factory_name = factory_name
        self.journal = journal
        self._tools:dict[str, ToolFactoryImplementable] = {}

    def __len__(self) -> int:
        return len(self._tools)
    
    def __str__(self) -> str:
        """Basic report of the ToolFactory.

        :return: a report string of the ToolFactory.
        :rtype: str
        """
        title = "Tool Factory report"
        report = ""
        report += f"{title}\n"
        report += "---------------------\n"
        for key in sorted(self._tools.keys()):
            report += f"- {key}\n"    
        report += f"---------------------\n"
        return report

    def registry_listing(self) -> List[str]:
        """Lists the registered tools in the ToolFactory.

        :return: a list of usable tools.
        :rtype: List[str]
        """
        return list(self._tools.keys())
    
    def register(self, tool: ToolFactoryImplementable) -> None:
        tool_name = tool.definition["function"]["name"]
        if tool_name in self._tools:
            msg = f"Tool {tool_name} has already been registered "\
                  "with the ToolFactory."
            raise DuplicateFactoryRegistration(msg)
        
        if self.journal is not None:        
            self.journal.add_entry(
                entry_type="tool",
                entry_text=tool_name,
                component="tool_factory",
                include_timestamp=True)
        self._tools[tool_name] = tool

    def unregister(self, tool_name: str) -> None:
        if tool_name not in self._tools:
            msg = f"Tool {tool_name} has not been registered with "\
                  "the ToolFactory."
            raise KeyError(msg)

        del self._tools[tool_name]
        
    def get_tools_json(self) -> List[str]:
        """Returns a list of all the tools that have been registered
        with the ToolFactory. The primary purpose is to provide an easy
        method for creating a JSON representation of the tools for the
        language model to use (such as ollama via "tools").

        :return: The JSON representation of the tools.
        :rtype: List[str]
        """
        tool_list = []
        for key, tool in self._tools.items():
            tool_list.append(json.dumps(tool.definition))

        return tool_list
    
    def create(self, tool_name: str) -> Any:
        """Creates a new instance of the specified tool.

        :param tool_name: The name of the tool to create.
        :type tool_name: str
        :return: The new instance of the tool.
        :rtype: Any
        """
        if tool_name not in self._tools:
            msg = f"Tool {tool_name} has not been registered with the "\
                  "ToolFactory."
            raise KeyError(msg)

        tool = self._tools[tool_name]
        if isinstance(tool, ToolFactoryImplementable):            
            new_tool = tool()
            return new_tool
        
        raise TypeError("Tool is not a ToolFactoryImplementable object.")