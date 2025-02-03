"""Exceptions for Scenarios"""

class InvalidScenarioState(Exception):
    """Used for any scenario state that is invalid"""

    default_msg = "Invalid Scenario state."

    def __init__(self, message: str = default_msg):
        super().__init__(message)

