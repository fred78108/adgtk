"""Exceptions for Scenarios"""


class InvalidScenarioState(Exception):
    """Used for any scenario state that is invalid"""

    default_msg = "Invalid Scenario state."

    def __init__(self, message: str = default_msg):
        super().__init__(message)


class InsufficientData(Exception):
    """Used when there is insufficient data to perform an operation"""

    default_msg = "Insufficient data."

    def __init__(self, message: str = default_msg):
        super().__init__(message)
