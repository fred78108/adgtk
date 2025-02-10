===========================
Reinforcement Learning APIs
===========================
The core of the toolkit is the the Reinforcement learning APIs. This consists of an Environment, and Agent, and the common buiding blocks (state, action, etc).

Building blocks
===============

For Reinforcement Learning Core API, we have the following core objects:

.. code-block:: python

    # found in adgtk.components.base

    class StateType(Enum):
        """What type of state is it?"""
        TENSOR = auto()
        ARRAY = auto()
        STRING = auto()
        PRESENTABLE_RECORD = auto()
        PRESENTABLE_GROUP = auto()
        DICT = auto()
        OTHER = auto()


    class ActionType(Enum):
        """What type of action is it?"""
        INT = auto()
        STRING = auto()
        TENSOR = auto()
        ARRAY = auto()
        OTHER = auto()

    @dataclass
    class State:
        """A state object"""
        state_type: StateType         # The type of the state
        value: Any              # The value of the state
        label: Any = None       # A label for the state if one exists


    @dataclass
    class Action:
        """An action object"""
        value: Any              # The value of the action
        action_type: ActionType        # The type of the action

Protocols
=========

Agent
-----

.. automodule:: adgtk.components.agent
    :members:
    :exclude-members: blueprint, description
    :undoc-members:
    :show-inheritance:

Policy
------

.. automodule:: adgtk.components.policy
    :members:
    :exclude-members: blueprint, description
    :undoc-members:
    :show-inheritance:

Environment
-----------

.. automodule:: adgtk.components.environment
    :members:
    :exclude-members: blueprint, description
    :undoc-members:
    :show-inheritance:
